import os
import pandas as pd
import numpy as np

from src.utils.config_loader import CONFIG
from src.narrative.catalyst_filter import NarrativeFilter
from src.risk.exposure_manager import RiskExposureManager


class SetupScanner:
    def __init__(self, top_pct=None, exclude_tickers=None, use_short_term_filter=False, roc_window=5):
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.cache_dir = os.path.join(project_root, "data", "cache")

        universe_cfg = CONFIG.get("universe", {})
        raw_tickers = universe_cfg.get("tickers", [])

        # Exclude specific non-performing or low-efficiency drag assets
        self.exclude_tickers = set(exclude_tickers) if exclude_tickers else set()
        self.tickers = [t for t in raw_tickers if t not in self.exclude_tickers]

        self.benchmark = universe_cfg.get("benchmarks", ["SPY"])[0]
        self.window = CONFIG.get("parameters", {}).get(
            "relative_strength_window", 63
        )

        if top_pct is not None:
            self.top_pct = top_pct
        else:
            self.top_pct = CONFIG.get("parameters", {}).get(
                "relative_strength_top_pct", 0.05
            )

        # Short-term momentum filter configuration
        self.use_short_term_filter = use_short_term_filter
        self.roc_window = roc_window

    def get_gated_leaders(self) -> list:
        """
        Layer 1 & 2: Filters universe by relative strength vs benchmark.
        """
        close_dict = {}
        all_assets = list(set(self.tickers + [self.benchmark]))

        for ticker in all_assets:
            safe_t = ticker.replace("^", "")
            path = os.path.join(self.cache_dir, f"{safe_t}.parquet")
            if os.path.exists(path):
                df = pd.read_parquet(path)
                if "Close" in df.columns:
                    df.index = pd.to_datetime(df.index).tz_localize(None)
                    close_dict[ticker] = df["Close"]

        if not close_dict:
            print("[!] No cached data found in directory.")
            return self.tickers

        close_data = pd.DataFrame(close_dict).dropna(how="all").sort_index()

        if len(close_data) <= self.window or self.benchmark not in close_data.columns:
            print(
                f"[!] Insufficient rows ({len(close_data)}) for relative strength calculation."
            )
            return self.tickers

        historical_slice = close_data.iloc[-(self.window + 1):]
        roc = historical_slice.pct_change(self.window).iloc[-1]
        benchmark_roc = roc[self.benchmark]

        excess_return = roc.drop(self.benchmark, errors="ignore") - benchmark_roc
        ranked = excess_return.dropna().sort_values(ascending=False)

        cutoff = max(1, int(len(ranked) * self.top_pct))
        gated_leaders = ranked.iloc[:cutoff].index.tolist()

        # Enforce exclusion filter on output
        gated_leaders = [t for t in gated_leaders if t not in self.exclude_tickers]

        print(
            f"[*] Gated Universe: Top {self.top_pct * 100:.1f}% RS Leaders ({len(gated_leaders)} assets selected out of {len(ranked)})"
        )
        return gated_leaders

    def fetch_historical_data(self, ticker: str) -> pd.DataFrame:
        safe_ticker = ticker.replace("^", "")
        file_path = os.path.join(self.cache_dir, f"{safe_ticker}.parquet")

        if os.path.exists(file_path):
            try:
                df = pd.read_parquet(file_path)
                df.index = pd.to_datetime(df.index).tz_localize(None)
                return df
            except Exception as e:
                print(f"[!] Error loading cache for {ticker}: {e}")
        return pd.DataFrame()

    def layer_3_detect_demand_zones(self, df: pd.DataFrame, ticker: str) -> dict:
        """
        Layer 3: Demand Zone / Setup Detection.

        Evaluates the most recent closed daily candle against a 21-day historical volume baseline
        and optionally verifies short-term momentum (ROC).
        """

        def empty_result(current_price=0.0, target_bar_date=None):
            return {
                "ticker": ticker,
                "execution_mode": "EOD_DAILY_CLOSE",
                "target_bar_date": target_bar_date,
                "current_price": float(current_price),
                "stop_loss": 0.0,
                "target_price": 0.0,
                "risk_per_share": 0.0,
                "setup_active": False,
            }

        # ---------------------------------------------------------
        # Clean dataframe
        # ---------------------------------------------------------

        if df is None or df.empty:
            return empty_result()

        df = df.copy()

        try:
            df.index = pd.to_datetime(df.index)
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            df.index = df.index.normalize()
        except Exception:
            return empty_result()

        # Deduplicate indices and sort
        df = df[~df.index.duplicated(keep="last")].sort_index()

        required_columns = {"Close", "Volume"}
        if not required_columns.issubset(set(df.columns)):
            return empty_result()

        # Require enough bars for volume baseline and short-term ROC check
        min_required = max(22, self.roc_window + 1)
        if len(df) < min_required:
            return empty_result()

        # ---------------------------------------------------------
        # Extract Target Bar & Baseline Slice
        # ---------------------------------------------------------

        target_bar = df.iloc[-1]
        target_date_str = df.index[-1].strftime("%Y-%m-%d")

        evaluated_close = float(target_bar["Close"])
        evaluated_vol = float(target_bar["Volume"])

        # Baseline: 21 completed daily sessions prior to the target bar
        baseline_slice = df.iloc[-22:-1]

        # ---------------------------------------------------------
        # Volume Threshold Evaluation
        # ---------------------------------------------------------

        vol_mean = float(baseline_slice["Volume"].mean())
        vol_std = float(baseline_slice["Volume"].std())
        volume_threshold = vol_mean + (1.5 * vol_std)

        # ---------------------------------------------------------
        # Short-Term Momentum Filter Evaluation
        # ---------------------------------------------------------

        passes_momentum = True
        if self.use_short_term_filter:
            # Calculate short-term ROC on the series up to the target bar
            roc_series = df["Close"].pct_change(self.roc_window)
            current_roc = roc_series.iloc[-1]
            passes_momentum = not pd.isna(current_roc) and current_roc > 0

        # ---------------------------------------------------------
        # Demand-Zone Trigger Logic
        # ---------------------------------------------------------

        if evaluated_vol > volume_threshold and passes_momentum:
            if "Low" in baseline_slice.columns:
                prior_low = float(baseline_slice["Low"].iloc[-1])
            else:
                prior_low = float(baseline_slice["Close"].iloc[-1])

            # CLEAN SINGLE 1.0% BUFFER BELOW PRIOR BAR LOW
            # stop_loss = round(prior_low * 0.99, 2)
            # entry_price = evaluated_close
            # risk_per_share = entry_price - stop_loss
            
            # DOUBLE BUFFER (MATCHING BACKTESTER)
            base_low = prior_low * 0.99
            stop_loss = round(base_low * 0.99, 2)
            entry_price = evaluated_close
            risk_per_share = entry_price - stop_loss

            if risk_per_share > 0:
                target_price = round(entry_price + (2.0 * risk_per_share), 2)

                return {
                    "ticker": ticker,
                    "execution_mode": "EOD_DAILY_CLOSE",
                    "target_bar_date": target_date_str,
                    "current_price": entry_price,
                    "stop_loss": stop_loss,
                    "target_price": target_price,
                    "risk_per_share": round(risk_per_share, 2),
                    "setup_active": True,
                }

        return empty_result(
            current_price=evaluated_close, target_bar_date=target_date_str
        )


if __name__ == "__main__":
    EXCLUDE_LIST = []

    # Initialize SetupScanner with optimal 50% percentile threshold
    PCT_PARAM = 0.50
    USE_FILTER = False  # Toggle to True to test short-term momentum guardrail live/locally
    
    scanner = SetupScanner(
        top_pct=PCT_PARAM, 
        exclude_tickers=EXCLUDE_LIST, 
        use_short_term_filter=USE_FILTER
    )
    gated_tickers = scanner.get_gated_leaders()

    narrative_filter = NarrativeFilter(tickers=gated_tickers)
    risk_manager = RiskExposureManager(
        account_size=100000.0, max_risk_pct=0.01
    )
    current_regime = "BULL_TREND"

    print(f"\n--- Running Setup Scan (EOD Daily Close | Short-Term Filter: {USE_FILTER}) ---")

    for t in gated_tickers:
        narrative_res = narrative_filter.layer_5_check_narrative(t)
        if not narrative_res["narrative_approved"]:
            print(
                f"Ticker: {t:<5} | [!] SKIPPED BY LAYER 5: {narrative_res['notes']}"
            )
            continue

        data = scanner.fetch_historical_data(t)
        if data.empty:
            continue

        result = scanner.layer_3_detect_demand_zones(data, t)

        if result["setup_active"]:
            price = result["current_price"]
            stop_loss = result["stop_loss"]
            target_price = result["target_price"]
            risk_per_share = result["risk_per_share"]

            risk_res = risk_manager.calculate_position(
                ticker=t,
                entry_price=price,
                stop_loss_price=stop_loss,
                regime_state=current_regime,
            )

            print(
                f"\n[+] Setup Active: {t} Date: {result['target_bar_date']}"
            )
            print(f"    - Entry Price:         ${price:.2f}")
            print(f"    - Stop Loss:           ${stop_loss:.2f}")
            print(f"    - Target Price (2.0x):  ${target_price:.2f}")
            print(f"    - Risk Per Share:       ${risk_per_share:.2f}")
            print(
                f"    - Position Size:        {risk_res['shares']} Shares (${risk_res['position_value']:,.2f})"
            )
            print(
                f"    - Capital At Risk:      ${risk_res['risk_amount']:,.2f} (1%)"
            )
        else:
            print(
                f"Ticker: {t:<5} | Date: {result['target_bar_date']} | Price: ${result['current_price']:<8.2f} | Setup Active: False"
            )