# import os
# import sys
# import pandas as pd
# import numpy as np

# # Force project root into sys.path
# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)

# from src.utils.config_loader import CONFIG


# class StrictMultiAssetBacktester:
#     def __init__(self, initial_capital_per_asset=100000.0, max_risk_pct=0.01, top_pct=0.05, use_short_term_filter=False, roc_window=5, cache_dir=None):
#         self.initial_capital_per_asset = initial_capital_per_asset
#         self.max_risk_pct = max_risk_pct
#         self.top_pct = top_pct
#         self.use_short_term_filter = use_short_term_filter
#         self.roc_window = roc_window
        
#         # Anchor cache_dir to absolute project root
#         project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
#         self.cache_dir = cache_dir or os.path.join(project_root, "data", "cache")
        
#         self.benchmark = "SPY"
        
#         # Pull parameters dynamically from config.yaml
#         params = CONFIG.get("parameters", {})
#         universe_cfg = CONFIG.get("universe", {})
        
#         self.window = params.get("relative_strength_window", 63)
#         self.universe = universe_cfg.get("tickers", [
#             "NVDA", "AMD", "AVGO", "TSM", "MRVL", "QCOM", "INTC", "MU", "AMAT", "LRCX", "KLAC", "ARM",
#             "MSFT", "AAPL", "GOOGL", "AMZN", "META", "TSLA", "NFLX", "PLTR", "CRM", "ADBE", "NOW", "SNOW", "UBER",
#             "JPM", "BAC", "GS", "V", "MA"
#         ])

#     def _get_path(self, ticker: str) -> str:
#         safe_ticker = ticker.replace("^", "")
#         return os.path.join(self.cache_dir, f"{safe_ticker}.parquet")

#     def run_backtest(self):
#         tickers = list(set(self.universe + [self.benchmark]))
        
#         close_dict, open_dict, high_dict, low_dict, volume_dict = {}, {}, {}, {}, {}
        
#         for ticker in tickers:
#             file_path = self._get_path(ticker)
#             if os.path.exists(file_path):
#                 try:
#                     df = pd.read_parquet(file_path)
#                     # Ensure DatetimeIndex is clean and timezone-naive
#                     df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
                    
#                     if "Close" in df.columns: close_dict[ticker] = df["Close"]
#                     if "Open" in df.columns: open_dict[ticker] = df["Open"]
#                     if "High" in df.columns: high_dict[ticker] = df["High"]
#                     if "Low" in df.columns: low_dict[ticker] = df["Low"]
#                     if "Volume" in df.columns: volume_dict[ticker] = df["Volume"]
#                 except Exception as e:
#                     print(f"[!] Error loading cache for {ticker}: {e}")

#         if not close_dict:
#             raise FileNotFoundError("No cached data found. Please run your cache manager first.")

#         # Align DataFrames across dates
#         close_df = pd.DataFrame(close_dict).dropna(how="all")
#         open_df = pd.DataFrame(open_dict).reindex(close_df.index)
#         high_df = pd.DataFrame(high_dict).reindex(close_df.index)
#         low_df = pd.DataFrame(low_dict).reindex(close_df.index)
#         volume_df = pd.DataFrame(volume_dict).reindex(close_df.index)

#         if self.benchmark not in close_df.columns:
#             raise ValueError(f"Benchmark '{self.benchmark}' is missing from the local cache.")

#         asset_universe = [t for t in self.universe if t in close_df.columns]

#         # --- PRE-COMPUTE VECTORIZED METRICS ---
#         # 1. Rolling 63-day ROC for Relative Strength
#         roc_df = close_df.pct_change(self.window)
#         benchmark_roc = roc_df[self.benchmark]
#         excess_return_df = roc_df[asset_universe].sub(benchmark_roc, axis=0)

#         # 2. Short-term ROC Matrix for Momentum Filter Check
#         roc_short_df = close_df[asset_universe].pct_change(self.roc_window)

#         # 3. Shifted Rolling Volume Metrics (Strictly Excludes Current Bar Volume)
#         vol_mean_df = volume_df[asset_universe].shift(1).rolling(window=20).mean()
#         vol_std_df = volume_df[asset_universe].shift(1).rolling(window=20).std()
#         vol_threshold_df = vol_mean_df + (1.5 * vol_std_df)
        
#         # Boolean Matrix: True if bar volume exceeds historical 20-day mean + 1.5 std dev
#         vol_signal_df = volume_df[asset_universe] > vol_threshold_df

#         portfolio_trades = {t: [] for t in asset_universe}
#         capital_tracker = {t: self.initial_capital_per_asset for t in asset_universe}
#         pending_orders = {t: None for t in asset_universe}

#         start_idx = max(self.window, self.roc_window) + 20
#         if len(close_df) <= start_idx:
#             print("[!] Insufficient historical data in cache for lookback window.")
#             return portfolio_trades, capital_tracker

#         dates = close_df.index[start_idx:]

#         for current_date in dates:
#             idx_loc = close_df.index.get_loc(current_date)
            
#             # Layer 2: Relative Strength Ranking at Close of Day T
#             ranked_today = excess_return_df.loc[current_date].dropna().sort_values(ascending=False)
#             cutoff = max(1, int(len(ranked_today) * self.top_pct))
#             gated_leaders = set(ranked_today.iloc[:cutoff].index.tolist())

#             for t in asset_universe:
#                 trades_for_t = portfolio_trades[t]
                
#                 # 1. EVALUATE EXISTING OPEN POSITION (INTRADAY HIGH/LOW EXECUTION)
#                 if len(trades_for_t) > 0 and trades_for_t[-1]['status'] == 'OPEN':
#                     open_trade = trades_for_t[-1]
#                     bar_high = float(high_df[t].iloc[idx_loc]) if t in high_df else float(close_df[t].iloc[idx_loc])
#                     bar_low = float(low_df[t].iloc[idx_loc]) if t in low_df else float(close_df[t].iloc[idx_loc])
#                     bar_open = float(open_df[t].iloc[idx_loc]) if t in open_df else float(close_df[t].iloc[idx_loc])

#                     stop_hit = bar_low <= open_trade['stop_loss']
#                     target_hit = bar_high >= open_trade['target_price']

#                     if stop_hit and target_hit:
#                         if abs(bar_open - open_trade['stop_loss']) < abs(bar_open - open_trade['target_price']):
#                             exit_price = open_trade['stop_loss']
#                             status = 'CLOSED_STOP'
#                         else:
#                             exit_price = open_trade['target_price']
#                             status = 'CLOSED_TARGET'
#                     elif stop_hit:
#                         exit_price = open_trade['stop_loss']
#                         status = 'CLOSED_STOP'
#                     elif target_hit:
#                         exit_price = open_trade['target_price']
#                         status = 'CLOSED_TARGET'
#                     else:
#                         status = None

#                     if status:
#                         pnl = (exit_price - open_trade['entry_price']) * open_trade['shares']
#                         capital_tracker[t] += pnl
#                         open_trade['status'] = status
#                         open_trade['exit_date'] = current_date
#                         open_trade['pnl'] = pnl
#                         open_trade['exit_price'] = exit_price

#                 # 2. EXECUTE PENDING ORDERS FROM PREVIOUS CLOSE (DAY T+1 ENTRY AT OPEN)
#                 elif pending_orders[t] is not None:
#                     setup = pending_orders[t]
#                     pending_orders[t] = None  # Clear pending order
                    
#                     entry_price = float(open_df[t].iloc[idx_loc]) if t in open_df else float(close_df[t].iloc[idx_loc])
#                     stop_loss = setup['stop_loss']
#                     risk_per_share = entry_price - stop_loss
                    
#                     if risk_per_share > 0:
#                         risk_capital = capital_tracker[t] * self.max_risk_pct
#                         shares = int(risk_capital / risk_per_share)
                        
#                         if shares > 0:
#                             target_price = round(entry_price + (2.0 * risk_per_share), 2)
#                             portfolio_trades[t].append({
#                                 "entry_date": current_date,
#                                 "entry_price": entry_price,
#                                 "stop_loss": stop_loss,
#                                 "target_price": target_price,
#                                 "shares": shares,
#                                 "status": "OPEN",
#                                 "pnl": 0.0
#                             })

#                 # 3. SCAN FOR NEW SETUPS AT CLOSE (TRIGGER FOR NEXT DAY T+1)
#                 has_open_trade = len(trades_for_t) > 0 and trades_for_t[-1]['status'] == 'OPEN'
#                 if not has_open_trade and pending_orders[t] is None:
#                     is_leader = t in gated_leaders and vol_signal_df.loc[current_date, t]
                    
#                     # Optional Short-Term Momentum Filter Check
#                     if self.use_short_term_filter:
#                         roc_val = roc_short_df.loc[current_date, t]
#                         passes_momentum = not pd.isna(roc_val) and roc_val > 0
#                     else:
#                         passes_momentum = True

#                     if is_leader and passes_momentum:
#                         prior_bar_low = float(low_df[t].iloc[idx_loc - 1]) if t in low_df else float(close_df[t].iloc[idx_loc - 1])
#                         base_low = prior_bar_low * 0.99
#                         stop_loss = round(base_low * 0.99, 2)
                        
#                         pending_orders[t] = {
#                             "trigger_date": current_date,
#                             "stop_loss": stop_loss
#                         }

#         # --- FORCE MARK-TO-MARKET CLOSE ON FINAL DATE FOR OPEN POSITIONS ---
#         last_date = dates[-1]
#         last_idx = close_df.index.get_loc(last_date)
#         for t in asset_universe:
#             trades_for_t = portfolio_trades[t]
#             if len(trades_for_t) > 0 and trades_for_t[-1]['status'] == 'OPEN':
#                 open_trade = trades_for_t[-1]
#                 close_price = float(close_df[t].iloc[last_idx])
#                 pnl = (close_price - open_trade['entry_price']) * open_trade['shares']
#                 capital_tracker[t] += pnl
#                 open_trade['status'] = 'CLOSED_MTM'
#                 open_trade['exit_date'] = last_date
#                 open_trade['pnl'] = pnl
#                 open_trade['exit_price'] = close_price

#         return portfolio_trades, capital_tracker


# if __name__ == "__main__":
#     from src.backtest.backtest_analytics import BacktestAnalytics

#     print("\n==================================================")
#     print("     COMPARATIVE BACKTEST: BASELINE VS FILTERED      ")
#     print("==================================================")

#     USE_FILTER = False  

#     # 1. RUN THE SWEEP LOOP
#     for pct in range(5, 85, 5):
#         top_pct = pct / 100.0
        
#         print(f"\n>>> RUNNING BACKTEST (Filter Enabled: {USE_FILTER}) FOR top_pct = {top_pct:.2f} ({pct}%) <<<")
#         print("--------------------------------------------------")
        
#         tester = StrictMultiAssetBacktester(top_pct=top_pct, use_short_term_filter=USE_FILTER)
#         trades_dict, capital_dict = tester.run_backtest()
        
#         grand_total_pnl = 0.0
#         total_trades_all = 0
#         total_wins_all = 0
        
#         all_closed_trades = [] # Collect all closed trades across the portfolio
        
#         for t in tester.universe:
#             trades = trades_dict.get(t, [])
#             closed_trades = [tr for tr in trades if tr['status'] != 'OPEN']
            
#             if closed_trades:
#                 wins = [tr for tr in closed_trades if tr['status'] == 'CLOSED_TARGET']
#                 total_pnl = sum([tr['pnl'] for tr in closed_trades])
#                 win_rate = (len(wins) / len(closed_trades)) * 100 if len(closed_trades) > 0 else 0
                
#                 grand_total_pnl += total_pnl
#                 total_trades_all += len(closed_trades)
#                 total_wins_all += len(wins)
#                 all_closed_trades.extend(closed_trades)
                
#                 print(f"Ticker: {t:<5} | Trades: {len(closed_trades):<2} | Win Rate: {win_rate:5.1f}% | Net PnL: ${total_pnl:,.2f}")
#             else:
#                 print(f"Ticker: {t:<5} | Trades: 0  | Win Rate:    0.0% | Net PnL: $0.00")

#         # Calculate Min, Max, and Average trades per month across portfolio
#         if all_closed_trades:
#             trades_df = pd.DataFrame(all_closed_trades)
#             trades_df['entry_date'] = pd.to_datetime(trades_df['entry_date'])
#             monthly_counts = trades_df.groupby(trades_df['entry_date'].dt.to_period('M')).size().values
#             min_trades_mo = int(monthly_counts.min())
#             max_trades_mo = int(monthly_counts.max())
#             avg_trades_mo = float(monthly_counts.mean())
#         else:
#             min_trades_mo = 0
#             max_trades_mo = 0
#             avg_trades_mo = 0.0

#         overall_win_rate = (total_wins_all / total_trades_all * 100) if total_trades_all > 0 else 0
        
#         print("--------------------------------------------------")
#         print(f"CONSOLIDATED SUMMARY (top_pct = {top_pct:.2f}, Filter={USE_FILTER}):")
#         print(f"   Total Trades Executed:   {total_trades_all}")
#         print(f"   Trades per Month (Min):  {min_trades_mo}")
#         print(f"   Trades per Month (Max):  {max_trades_mo}")
#         print(f"   Trades per Month (Avg):  {avg_trades_mo:.2f}")
#         print(f"   Overall Win Rate:        {overall_win_rate:.1f}%")
#         print(f"   Aggregate Net PnL:       ${grand_total_pnl:,.2f}")
#         print("==================================================")

#     # ------------------------------------------------------------------
#     # 2. GENERATE EQUITY CURVE PLOT FOR OPTIMAL THRESHOLD (e.g., 0.80)
#     # ------------------------------------------------------------------
#     print("\n\n==================================================")
#     print("   GENERATING EQUITY CURVE PLOT FOR USER SELECTED  ")
#     print("==================================================")

#     optimal_pct = 0.80
#     final_tester = StrictMultiAssetBacktester(top_pct=optimal_pct, use_short_term_filter=USE_FILTER)
#     opt_trades, opt_capital = final_tester.run_backtest()

#     analytics = BacktestAnalytics(
#         trades_dict=opt_trades,
#         initial_capital_per_asset=final_tester.initial_capital_per_asset
#     )

#     equity_df = analytics.generate_equity_curves()
#     analytics.plot_individual_curves(equity_df)

#     if 'MU' in equity_df.columns:
#         adi_df = equity_df[['ADI']] if 'ADI' in equity_df.columns else equity_df[['MU']]
#         analytics.plot_individual_curves(adi_df)

import os
import sys
import numpy as np
import pandas as pd

# Force project root into sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils.config_loader import CONFIG


class StrictMultiAssetBacktester:

    def __init__(
        self,
        initial_capital_per_asset=100000.0,
        max_risk_pct=0.01,
        top_pct=0.05,
        use_short_term_filter=False,
        roc_window=5,
        cache_dir=None,
    ):
        self.initial_capital_per_asset = initial_capital_per_asset
        self.max_risk_pct = max_risk_pct
        self.top_pct = top_pct
        self.use_short_term_filter = use_short_term_filter
        self.roc_window = roc_window

        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.cache_dir = cache_dir or os.path.join(
            project_root, "data", "cache"
        )
        self.benchmark = "SPY"

        params = CONFIG.get("parameters", {})
        universe_cfg = CONFIG.get("universe", {})

        self.window = params.get("relative_strength_window", 63)
        self.universe = universe_cfg.get(
            "tickers",
            [
                "NVDA",
                "AMD",
                "AVGO",
                "TSM",
                "MRVL",
                "QCOM",
                "INTC",
                "MU",
                "AMAT",
                "LRCX",
                "KLAC",
                "ARM",
                "MSFT",
                "AAPL",
                "GOOGL",
                "AMZN",
                "META",
                "TSLA",
                "NFLX",
                "PLTR",
                "CRM",
                "ADBE",
                "NOW",
                "SNOW",
                "UBER",
                "JPM",
                "BAC",
                "GS",
                "V",
                "MA",
            ],
        )

    def _get_path(self, ticker: str) -> str:
        safe_ticker = ticker.replace("^", "")
        return os.path.join(self.cache_dir, f"{safe_ticker}.parquet")

    def run_backtest(self):
        tickers = list(set(self.universe + [self.benchmark]))
        close_dict, open_dict, high_dict, low_dict, volume_dict = (
            {},
            {},
            {},
            {},
            {},
        )

        for ticker in tickers:
            file_path = self._get_path(ticker)
            if os.path.exists(file_path):
                try:
                    df = pd.read_parquet(file_path)
                    df.index = (
                        pd.to_datetime(df.index)
                        .tz_localize(None)
                        .normalize()
                    )
                    if "Close" in df.columns:
                        close_dict[ticker] = df["Close"]
                    if "Open" in df.columns:
                        open_dict[ticker] = df["Open"]
                    if "High" in df.columns:
                        high_dict[ticker] = df["High"]
                    if "Low" in df.columns:
                        low_dict[ticker] = df["Low"]
                    if "Volume" in df.columns:
                        volume_dict[ticker] = df["Volume"]
                except Exception as e:
                    print(f"[!] Error loading cache for {ticker}: {e}")

        if not close_dict:
            raise FileNotFoundError(
                "No cached data found. Please run your cache manager first."
            )

        close_df = pd.DataFrame(close_dict).dropna(how="all")
        open_df = pd.DataFrame(open_dict).reindex(close_df.index)
        high_df = pd.DataFrame(high_dict).reindex(close_df.index)
        low_df = pd.DataFrame(low_dict).reindex(close_df.index)
        volume_df = pd.DataFrame(volume_dict).reindex(close_df.index)

        if self.benchmark not in close_df.columns:
            raise ValueError(
                f"Benchmark '{self.benchmark}' is missing from local cache."
            )

        asset_universe = [t for t in self.universe if t in close_df.columns]

        roc_df = close_df.pct_change(self.window)
        benchmark_roc = roc_df[self.benchmark]
        excess_return_df = roc_df[asset_universe].sub(benchmark_roc, axis=0)

        roc_short_df = close_df[asset_universe].pct_change(self.roc_window)

        vol_mean_df = (
            volume_df[asset_universe].shift(1).rolling(window=20).mean()
        )
        vol_std_df = (
            volume_df[asset_universe].shift(1).rolling(window=20).std()
        )
        vol_threshold_df = vol_mean_df + (1.5 * vol_std_df)
        vol_signal_df = volume_df[asset_universe] > vol_threshold_df

        portfolio_trades = {t: [] for t in asset_universe}
        capital_tracker = {
            t: self.initial_capital_per_asset for t in asset_universe
        }
        pending_orders = {t: None for t in asset_universe}

        start_idx = max(self.window, self.roc_window) + 20
        if len(close_df) <= start_idx:
            print(
                "[!] Insufficient historical data in cache for lookback window."
            )
            return portfolio_trades, capital_tracker

        dates = close_df.index[start_idx:]

        for current_date in dates:
            idx_loc = close_df.index.get_loc(current_date)
            ranked_today = (
                excess_return_df.loc[current_date]
                .dropna()
                .sort_values(ascending=False)
            )
            cutoff = max(1, int(len(ranked_today) * self.top_pct))
            gated_leaders = set(ranked_today.iloc[:cutoff].index.tolist())

            for t in asset_universe:
                trades_for_t = portfolio_trades[t]

                # 1. EVALUATE EXISTING OPEN POSITION
                if len(trades_for_t) > 0 and trades_for_t[-1]["status"] == "OPEN":
                    open_trade = trades_for_t[-1]
                    bar_high = (
                        float(high_df[t].iloc[idx_loc])
                        if t in high_df
                        else float(close_df[t].iloc[idx_loc])
                    )
                    bar_low = (
                        float(low_df[t].iloc[idx_loc])
                        if t in low_df
                        else float(close_df[t].iloc[idx_loc])
                    )
                    bar_open = (
                        float(open_df[t].iloc[idx_loc])
                        if t in open_df
                        else float(close_df[t].iloc[idx_loc])
                    )

                    stop_hit = bar_low <= open_trade["stop_loss"]
                    target_hit = bar_high >= open_trade["target_price"]

                    if stop_hit and target_hit:
                        if abs(bar_open - open_trade["stop_loss"]) < abs(
                            bar_open - open_trade["target_price"]
                        ):
                            exit_price = open_trade["stop_loss"]
                            status = "CLOSED_STOP"
                        else:
                            exit_price = open_trade["target_price"]
                            status = "CLOSED_TARGET"
                    elif stop_hit:
                        exit_price = open_trade["stop_loss"]
                        status = "CLOSED_STOP"
                    elif target_hit:
                        exit_price = open_trade["target_price"]
                        status = "CLOSED_TARGET"
                    else:
                        status = None

                    if status:
                        pnl = (
                            exit_price - open_trade["entry_price"]
                        ) * open_trade["shares"]
                        capital_tracker[t] += pnl
                        open_trade["status"] = status
                        open_trade["exit_date"] = current_date
                        open_trade["pnl"] = pnl
                        open_trade["exit_price"] = exit_price

                # 2. EXECUTE PENDING ORDERS
                elif pending_orders[t] is not None:
                    setup = pending_orders[t]
                    pending_orders[t] = None

                    entry_price = (
                        float(open_df[t].iloc[idx_loc])
                        if t in open_df
                        else float(close_df[t].iloc[idx_loc])
                    )
                    stop_loss = setup["stop_loss"]
                    # risk_per_share = entry_price - stop_loss

                    # if risk_per_share > 0:
                    #     risk_capital = (
                    #         capital_tracker[t] * self.max_risk_pct
                    #     )
                    #     shares = int(risk_capital / risk_per_share)
                    risk_per_share = entry_price - stop_loss

                    if risk_per_share > 0:
                        # FIXED $1,000 RISK ALLOCATION PER TRADE
                        risk_capital = 1000.0
                        shares = int(risk_capital / risk_per_share)

                        if shares > 0:
                            target_price = round(
                                entry_price + (2.0 * risk_per_share), 2
                            )
                            portfolio_trades[t].append({
                                "ticker": t,
                                "entry_date": current_date,
                                "entry_price": entry_price,
                                "stop_loss": stop_loss,
                                "target_price": target_price,
                                "shares": shares,
                                "status": "OPEN",
                                "pnl": 0.0,
                            })

                # 3. SCAN FOR NEW SETUPS
                has_open_trade = (
                    len(trades_for_t) > 0
                    and trades_for_t[-1]["status"] == "OPEN"
                )
                if not has_open_trade and pending_orders[t] is None:
                    is_leader = (
                        t in gated_leaders
                        and vol_signal_df.loc[current_date, t]
                    )

                    if self.use_short_term_filter:
                        roc_val = roc_short_df.loc[current_date, t]
                        passes_momentum = (
                            not pd.isna(roc_val) and roc_val > 0
                        )
                    else:
                        passes_momentum = True

                    if is_leader and passes_momentum:
                        prior_bar_low = (
                            float(low_df[t].iloc[idx_loc - 1])
                            if t in low_df
                            else float(close_df[t].iloc[idx_loc - 1])
                        )
                        base_low = prior_bar_low * 0.99
                        stop_loss = round(base_low * 0.99, 2)

                        pending_orders[t] = {
                            "trigger_date": current_date,
                            "stop_loss": stop_loss,
                        }

        # MARK-TO-MARKET CLOSE ON FINAL DATE
        last_date = dates[-1]
        last_idx = close_df.index.get_loc(last_date)
        for t in asset_universe:
            trades_for_t = portfolio_trades[t]
            if len(trades_for_t) > 0 and trades_for_t[-1]["status"] == "OPEN":
                open_trade = trades_for_t[-1]
                close_price = float(close_df[t].iloc[last_idx])
                pnl = (
                    close_price - open_trade["entry_price"]
                ) * open_trade["shares"]
                capital_tracker[t] += pnl
                open_trade["status"] = "CLOSED_MTM"
                open_trade["exit_date"] = last_date
                open_trade["pnl"] = pnl
                open_trade["exit_price"] = close_price

        return portfolio_trades, capital_tracker


if __name__ == "__main__":
    from src.backtest.backtest_analytics import BacktestAnalytics

    USE_FILTER = False
    output_dir = os.path.join(project_root, "data", "backtest_results")
    os.makedirs(output_dir, exist_ok=True)
    excel_path = os.path.join(output_dir, "sweep_analytics.xlsx")

    sweep_summary_list = []
    all_trade_records = []

    print("[*] Running Parameter Sweep across RS Thresholds (5% - 80%)...")

    for pct in range(5, 85, 5):
        top_pct = pct / 100.0

        tester = StrictMultiAssetBacktester(
            top_pct=top_pct, use_short_term_filter=USE_FILTER
        )
        trades_dict, capital_dict = tester.run_backtest()

        grand_total_pnl = 0.0
        total_trades_all = 0
        total_wins_all = 0
        all_closed_trades = []

        for t in tester.universe:
            trades = trades_dict.get(t, [])
            closed_trades = [tr for tr in trades if tr["status"] != "OPEN"]

            if closed_trades:
                wins = [
                    tr for tr in closed_trades if tr["status"] == "CLOSED_TARGET"
                ]
                total_pnl = sum([tr["pnl"] for tr in closed_trades])
                win_rate = (
                    (len(wins) / len(closed_trades)) * 100
                    if len(closed_trades) > 0
                    else 0
                )

                grand_total_pnl += total_pnl
                total_trades_all += len(closed_trades)
                total_wins_all += len(wins)

                for tr in closed_trades:
                    tr_copy = tr.copy()
                    tr_copy["top_pct"] = top_pct
                    all_closed_trades.append(tr_copy)

        if all_closed_trades:
            trades_df = pd.DataFrame(all_closed_trades)
            trades_df["entry_date"] = pd.to_datetime(trades_df["entry_date"])
            monthly_counts = (
                trades_df.groupby(trades_df["entry_date"].dt.to_period("M"))
                .size()
                .values
            )
            min_trades_mo = int(monthly_counts.min())
            max_trades_mo = int(monthly_counts.max())
            avg_trades_mo = float(monthly_counts.mean())
        else:
            min_trades_mo, max_trades_mo, avg_trades_mo = 0, 0, 0.0

        overall_win_rate = (
            (total_wins_all / total_trades_all * 100)
            if total_trades_all > 0
            else 0
        )

        sweep_summary_list.append({
            "top_pct": top_pct,
            "top_pct_label": f"{pct}%",
            "filter_enabled": USE_FILTER,
            "total_trades": total_trades_all,
            "overall_win_rate": round(overall_win_rate, 2),
            "aggregate_net_pnl": round(grand_total_pnl, 2),
            "trades_per_mo_min": min_trades_mo,
            "trades_per_mo_max": max_trades_mo,
            "trades_per_mo_avg": round(avg_trades_mo, 2),
        })

        all_trade_records.extend(all_closed_trades)

    # Convert to DataFrames
    summary_df = pd.DataFrame(sweep_summary_list)
    trades_log_df = pd.DataFrame(all_trade_records)

    # Save cleanly to multi-tab Excel
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Sweep Summary", index=False)
        trades_log_df.to_excel(writer, sheet_name="Trade Log", index=False)

    print(f"[✓] Sweep Complete! Results saved cleanly to:\n    {excel_path}")

    # Display clean condensed summary directly in console
    print("\n==================================================")
    print("           CONSOLIDATED SWEEP SUMMARY             ")
    print("==================================================")
    print(
        summary_df[
            [
                "top_pct_label",
                "total_trades",
                "overall_win_rate",
                "aggregate_net_pnl",
                "trades_per_mo_avg",
            ]
        ].to_string(index=False)
    )
    print("==================================================")

    # Optional plot generation for optimal top_pct (e.g., 0.50 or 0.80)
    optimal_pct = 0.50
    final_tester = StrictMultiAssetBacktester(
        top_pct=optimal_pct, use_short_term_filter=USE_FILTER
    )
    opt_trades, opt_capital = final_tester.run_backtest()

    analytics = BacktestAnalytics(
        trades_dict=opt_trades,
        initial_capital_per_asset=final_tester.initial_capital_per_asset,
    )
    equity_df = analytics.generate_equity_curves()
    analytics.plot_individual_curves(equity_df)