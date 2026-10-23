# This is the backtesre with new checker but needs subscriptio to FMP. 
import os
import sys
import argparse
import requests
import pandas as pd
import numpy as np
from datetime import timedelta

# Force project root into sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils.config_loader import CONFIG


class StrictMultiAssetBacktester:
    def __init__(self, initial_capital_per_asset=100000.0, max_risk_pct=0.01, top_pct=0.05, use_short_term_filter=False, roc_window=5, fmp_api_key=None, cache_dir=None):
        self.initial_capital_per_asset = initial_capital_per_asset
        self.max_risk_pct = max_risk_pct
        self.top_pct = top_pct
        self.use_short_term_filter = use_short_term_filter
        self.roc_window = roc_window
        self.fmp_api_key = fmp_api_key or os.getenv("FMP_API_KEY", "")
        
        # Anchor cache_dir to absolute project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.cache_dir = cache_dir or os.path.join(project_root, "data", "cache")
        
        self.benchmark = "SPY"
        
        # Pull parameters dynamically from config.yaml
        params = CONFIG.get("parameters", {})
        universe_cfg = CONFIG.get("universe", {})
        
        self.window = params.get("relative_strength_window", 63)
        self.universe = universe_cfg.get("tickers", [
            "NVDA", "AMD", "AVGO", "TSM", "MRVL", "QCOM", "INTC", "MU", "AMAT", "LRCX", "KLAC", "ARM",
            "MSFT", "AAPL", "GOOGL", "AMZN", "META", "TSLA", "NFLX", "PLTR", "CRM", "ADBE", "NOW", "SNOW", "UBER",
            "JPM", "BAC", "GS", "V", "MA"
        ])

    def _get_path(self, ticker: str) -> str:
        safe_ticker = ticker.replace("^", "")
        return os.path.join(self.cache_dir, f"{safe_ticker}.parquet")

    def fetch_ticker_news_fmp(self, ticker: str, start_date, end_date):
        """Fetch historical news headlines within a date window using Financial Modeling Prep (FMP)."""
        if not self.fmp_api_key:
            return ["[!] FMP API key missing. Set FMP_API_KEY environment variable or pass --fmp_key."]
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        url = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={ticker}&from={start_str}&to={end_str}&limit=10&apikey={self.fmp_api_key}"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                filtered_news = []
                for item in data:
                    pub_date = item.get('publishedDate', '')[:10]
                    title = item.get('title', 'No Title')
                    filtered_news.append(f"[{pub_date}] {title}")
                return filtered_news if filtered_news else ["No headlines found in this window."]
            else:
                return [f"FMP API returned status code {response.status_code}"]
        except Exception as e:
            return [f"News fetch error: {str(e)}"]

    def run_backtest(self):
        tickers = list(set(self.universe + [self.benchmark]))
        
        close_dict, open_dict, high_dict, low_dict, volume_dict = {}, {}, {}, {}, {}
        
        for ticker in tickers:
            file_path = self._get_path(ticker)
            if os.path.exists(file_path):
                try:
                    df = pd.read_parquet(file_path)
                    # Ensure DatetimeIndex is clean and timezone-naive
                    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
                    
                    if "Close" in df.columns: close_dict[ticker] = df["Close"]
                    if "Open" in df.columns: open_dict[ticker] = df["Open"]
                    if "High" in df.columns: high_dict[ticker] = df["High"]
                    if "Low" in df.columns: low_dict[ticker] = df["Low"]
                    if "Volume" in df.columns: volume_dict[ticker] = df["Volume"]
                except Exception as e:
                    print(f"[!] Error loading cache for {ticker}: {e}")

        if not close_dict:
            raise FileNotFoundError("No cached data found. Please run your cache manager first.")

        # Align DataFrames across dates
        close_df = pd.DataFrame(close_dict).dropna(how="all")
        open_df = pd.DataFrame(open_dict).reindex(close_df.index)
        high_df = pd.DataFrame(high_dict).reindex(close_df.index)
        low_df = pd.DataFrame(low_dict).reindex(close_df.index)
        volume_df = pd.DataFrame(volume_dict).reindex(close_df.index)

        if self.benchmark not in close_df.columns:
            raise ValueError(f"Benchmark '{self.benchmark}' is missing from the local cache.")

        asset_universe = [t for t in self.universe if t in close_df.columns]

        # --- PRE-COMPUTE VECTORIZED METRICS ---
        # 1. Rolling 63-day ROC for Relative Strength
        roc_df = close_df.pct_change(self.window)
        benchmark_roc = roc_df[self.benchmark]
        excess_return_df = roc_df[asset_universe].sub(benchmark_roc, axis=0)

        # 2. Short-term ROC Matrix for Momentum Filter Check
        roc_short_df = close_df[asset_universe].pct_change(self.roc_window)

        # 3. Shifted Rolling Volume Metrics (Strictly Excludes Current Bar Volume)
        vol_mean_df = volume_df[asset_universe].shift(1).rolling(window=20).mean()
        vol_std_df = volume_df[asset_universe].shift(1).rolling(window=20).std()
        vol_threshold_df = vol_mean_df + (1.5 * vol_std_df)
        
        # Boolean Matrix: True if bar volume exceeds historical 20-day mean + 1.5 std dev
        vol_signal_df = volume_df[asset_universe] > vol_threshold_df

        portfolio_trades = {t: [] for t in asset_universe}
        capital_tracker = {t: self.initial_capital_per_asset for t in asset_universe}
        pending_orders = {t: None for t in asset_universe}

        start_idx = max(self.window, self.roc_window) + 20
        if len(close_df) <= start_idx:
            print("[!] Insufficient historical data in cache for lookback window.")
            return portfolio_trades, capital_tracker

        dates = close_df.index[start_idx:]

        for current_date in dates:
            idx_loc = close_df.index.get_loc(current_date)
            
            # Layer 2: Relative Strength Ranking at Close of Day T
            ranked_today = excess_return_df.loc[current_date].dropna().sort_values(ascending=False)
            cutoff = max(1, int(len(ranked_today) * self.top_pct))
            gated_leaders = set(ranked_today.iloc[:cutoff].index.tolist())

            for t in asset_universe:
                trades_for_t = portfolio_trades[t]
                
                # 1. EVALUATE EXISTING OPEN POSITION (INTRADAY HIGH/LOW EXECUTION)
                if len(trades_for_t) > 0 and trades_for_t[-1]['status'] == 'OPEN':
                    open_trade = trades_for_t[-1]
                    bar_high = float(high_df[t].iloc[idx_loc]) if t in high_df else float(close_df[t].iloc[idx_loc])
                    bar_low = float(low_df[t].iloc[idx_loc]) if t in low_df else float(close_df[t].iloc[idx_loc])
                    bar_open = float(open_df[t].iloc[idx_loc]) if t in open_df else float(close_df[t].iloc[idx_loc])

                    stop_hit = bar_low <= open_trade['stop_loss']
                    target_hit = bar_high >= open_trade['target_price']

                    if stop_hit and target_hit:
                        if abs(bar_open - open_trade['stop_loss']) < abs(bar_open - open_trade['target_price']):
                            exit_price = open_trade['stop_loss']
                            status = 'CLOSED_STOP'
                        else:
                            exit_price = open_trade['target_price']
                            status = 'CLOSED_TARGET'
                    elif stop_hit:
                        exit_price = open_trade['stop_loss']
                        status = 'CLOSED_STOP'
                    elif target_hit:
                        exit_price = open_trade['target_price']
                        status = 'CLOSED_TARGET'
                    else:
                        status = None

                    if status:
                        pnl = (exit_price - open_trade['entry_price']) * open_trade['shares']
                        capital_tracker[t] += pnl
                        open_trade['status'] = status
                        open_trade['exit_date'] = current_date
                        open_trade['pnl'] = pnl
                        open_trade['exit_price'] = exit_price

                # 2. EXECUTE PENDING ORDERS FROM PREVIOUS CLOSE (DAY T+1 ENTRY AT OPEN)
                elif pending_orders[t] is not None:
                    setup = pending_orders[t]
                    pending_orders[t] = None  # Clear pending order
                    
                    entry_price = float(open_df[t].iloc[idx_loc]) if t in open_df else float(close_df[t].iloc[idx_loc])
                    stop_loss = setup['stop_loss']
                    risk_per_share = entry_price - stop_loss
                    
                    if risk_per_share > 0:
                        risk_capital = capital_tracker[t] * self.max_risk_pct
                        shares = int(risk_capital / risk_per_share)
                        
                        if shares > 0:
                            target_price = round(entry_price + (2.0 * risk_per_share), 2)
                            portfolio_trades[t].append({
                                "ticker": t,
                                "trigger_date": setup['trigger_date'],
                                "entry_date": current_date,
                                "entry_price": entry_price,
                                "stop_loss": stop_loss,
                                "target_price": target_price,
                                "shares": shares,
                                "status": "OPEN",
                                "pnl": 0.0
                            })

                # 3. SCAN FOR NEW SETUPS AT CLOSE (TRIGGER FOR NEXT DAY T+1)
                has_open_trade = len(trades_for_t) > 0 and trades_for_t[-1]['status'] == 'OPEN'
                if not has_open_trade and pending_orders[t] is None:
                    is_leader = t in gated_leaders and vol_signal_df.loc[current_date, t]
                    
                    # Optional Short-Term Momentum Filter Check
                    if self.use_short_term_filter:
                        roc_val = roc_short_df.loc[current_date, t]
                        passes_momentum = not pd.isna(roc_val) and roc_val > 0
                    else:
                        passes_momentum = True

                    if is_leader and passes_momentum:
                        prior_bar_low = float(low_df[t].iloc[idx_loc - 1]) if t in low_df else float(close_df[t].iloc[idx_loc - 1])
                        base_low = prior_bar_low * 0.99
                        stop_loss = round(base_low * 0.99, 2)
                        
                        pending_orders[t] = {
                            "trigger_date": current_date,
                            "stop_loss": stop_loss
                        }

        # --- FORCE MARK-TO-MARKET CLOSE ON FINAL DATE FOR OPEN POSITIONS ---
        last_date = dates[-1]
        last_idx = close_df.index.get_loc(last_date)
        for t in asset_universe:
            trades_for_t = portfolio_trades[t]
            if len(trades_for_t) > 0 and trades_for_t[-1]['status'] == 'OPEN':
                open_trade = trades_for_t[-1]
                close_price = float(close_df[t].iloc[last_idx])
                pnl = (close_price - open_trade['entry_price']) * open_trade['shares']
                capital_tracker[t] += pnl
                open_trade['status'] = 'CLOSED_MTM'
                open_trade['exit_date'] = last_date
                open_trade['pnl'] = pnl
                open_trade['exit_price'] = close_price

        return portfolio_trades, capital_tracker


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Strict Multi-Asset Backtester with FMP News Checker")
    parser.add_argument("--fmp_key", type=str, default=None, help="Financial Modeling Prep API Key")
    args = parser.parse_args()

    # FMP API key handling
    fmp_key = args.fmp_key or os.getenv("FMP_API_KEY", "")
    if not fmp_key:
        fmp_key = input("Enter FMP API Key (press Enter to skip news fetch): ").strip()

    print("\n==================================================")
    print("   BACKTESTING WITH FMP HISTORICAL NEWS INSPECTION")
    print("==================================================")

    USE_FILTER = False
    optimal_pct = 0.80

    print(f"\n>>> Running backtest for optimal threshold (top_pct = {optimal_pct:.2f}) <<<")
    tester = StrictMultiAssetBacktester(top_pct=optimal_pct, use_short_term_filter=USE_FILTER, fmp_api_key=fmp_key)
    trades_dict, capital_dict = tester.run_backtest()

    # Flatten and inspect trades
    all_trades = []
    for ticker, trades in trades_dict.items():
        for tr in trades:
            all_trades.append(tr)

    print(f"\n[+] Total Trades Found: {len(all_trades)}\n")

    if not all_trades:
        print("[!] No trades generated.")
    else:
        for idx, tr in enumerate(all_trades, 1):
            entry_dt = tr['entry_date']
            start_window = entry_dt - timedelta(days=7)
            end_window = entry_dt + timedelta(days=7)
            
            # Fetch historical news headlines using FMP API
            news_items = tester.fetch_ticker_news_fmp(tr['ticker'], start_window, end_window)

            print(f"--- Trade #{idx}: {tr['ticker']} ---")
            print(f"  * Trigger Date:          {tr.get('trigger_date', entry_dt).strftime('%Y-%m-%d')}")
            print(f"  * Entry Date & Price:    {entry_dt.strftime('%Y-%m-%d')} @ ${tr['entry_price']:.2f}")
            print(f"  * Stop Loss / Target:    ${tr['stop_loss']:.2f} / ${tr['target_price']:.2f}")
            print(f"  * Status / Realized PnL: {tr['status']} | ${tr['pnl']:,.2f}")
            print(f"  * News Window (±7 Days): {start_window.strftime('%Y-%m-%d')} to {end_window.strftime('%Y-%m-%d')}")
            
            print("  * Historical Headlines (FMP):")
            for headline in news_items[:5]:
                print(f"    - {headline}")
            print("-" * 60)