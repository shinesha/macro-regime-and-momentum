import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class BacktestAnalytics:
    def __init__(self, trades_dict: dict, initial_capital_per_asset: float = 100000.0):
        self.trades_dict = trades_dict
        self.initial_capital = initial_capital_per_asset

    # def generate_equity_curves(self, dates_index: pd.DatetimeIndex) -> pd.DataFrame:
    #     """
    #     Reconstructs daily cumulative equity curves for each individual asset.
    #     """
    #     equity_dict = {}

    #     for ticker, trades in self.trades_dict.items():
    #         # Create a daily series initialized at zero PnL change
    #         daily_pnl = pd.Series(0.0, index=dates_index, name=ticker)
            
    #         # Map realized PnL to trade exit dates
    #         closed_trades = [t for t in trades if t['status'] in ['CLOSED_STOP', 'CLOSED_TARGET']]
    #         for trade in closed_trades:
    #             exit_date = pd.to_datetime(trade['exit_date'])
    #             if exit_date in daily_pnl.index:
    #                 daily_pnl.loc[exit_date] += trade['pnl']

    #         # Cumulative sum added to starting capital base
    #         equity_dict[ticker] = self.initial_capital + daily_pnl.cumsum()

    #     return pd.DataFrame(equity_dict)
    
    def generate_equity_curves(self, dates_index=None) -> pd.DataFrame:
        """
        Reconstructs daily cumulative equity curves for each asset.
        """
        # If no dates_index is supplied, auto-extract unique dates from trades
        if dates_index is None:
            all_dates = set()
            for trades in self.trades_dict.values():
                for t in trades:
                    if 'exit_date' in t and t['exit_date']:
                        all_dates.add(pd.to_datetime(t['exit_date']))
                    if 'entry_date' in t and t['entry_date']:
                        all_dates.add(pd.to_datetime(t['entry_date']))
            
            if not all_dates:
                raise ValueError("No trade dates found in trades_dict.")
                
            dates_index = pd.DatetimeIndex(sorted(all_dates))

        equity_dict = {}

        for ticker, trades in self.trades_dict.items():
            daily_pnl = pd.Series(0.0, index=dates_index, name=ticker)
            
            closed_trades = [t for t in trades if t['status'] in ['CLOSED_STOP', 'CLOSED_TARGET']]
            for trade in closed_trades:
                exit_date = pd.to_datetime(trade['exit_date'])
                if exit_date in daily_pnl.index:
                    daily_pnl.loc[exit_date] += trade['pnl']

            equity_dict[ticker] = self.initial_capital + daily_pnl.cumsum()

        return pd.DataFrame(equity_dict)

    def plot_individual_curves(self, equity_df: pd.DataFrame, top_n: int = 20):
        """
        Plots individual asset equity curves over time.
        """
        plt.figure(figsize=(12, 6))
        for col in equity_df.columns[:top_n]:
            plt.plot(equity_df.index, equity_df[col], label=f"{col}")
        
        plt.title("Individual Asset Equity Curves (Top Allocations)")
        plt.xlabel("Date")
        plt.ylabel("Portfolio Value ($)")
        plt.legend(loc="upper left")
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()
        plt.show()

# --- Example Usage ---
# from backtest_analytics import BacktestAnalytics
# tester = StrictMultiAssetBacktester(top_pct=0.50)
# trades_dict, _ = tester.run_backtest()
# analytics = BacktestAnalytics(trades_dict)
# equity_df = analytics.generate_equity_curves(dates_index)
# analytics.plot_individual_curves(equity_df)