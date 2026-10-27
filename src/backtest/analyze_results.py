
# import os
# import sys
# import matplotlib.pyplot as plt
# import pandas as pd
# import openpyxl

# # Force project root into sys.path
# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)


# def analyze_sweep_excel(excel_path: str):
#     if not os.path.exists(excel_path):
#         print(f"[!] File not found: {excel_path}")
#         print("    Run `python -m src.backtest.engine` first to generate sweep_analytics.xlsx.")
#         return

#     print(f"[*] Loading backtest sweep data from:\n    {excel_path}\n")
#     summary_df = pd.read_excel(excel_path, sheet_name="Sweep Summary")

#     # 1. Calculate Per-Trade Efficiency Metrics
#     summary_df["efficiency_per_trade"] = (
#         summary_df["aggregate_net_pnl"] / summary_df["total_trades"]
#     )

#     # 2. Capital Efficiency Selection Logic
#     valid_candidates = summary_df[
#         (summary_df["overall_win_rate"] >= 47.0)
#         & (summary_df["efficiency_per_trade"] >= 400.0)
#     ].copy()

#     if not valid_candidates.empty:
#         valid_candidates["composite_score"] = (
#             valid_candidates["aggregate_net_pnl"] * valid_candidates["efficiency_per_trade"]
#         )
#         optimal_row = valid_candidates.sort_values(
#             by="composite_score", ascending=False
#         ).iloc[0]
#     else:
#         optimal_row = summary_df.sort_values(
#             by="aggregate_net_pnl", ascending=False
#         ).iloc[0]

#     optimal_pct = optimal_row["top_pct"]
#     optimal_label = optimal_row["top_pct_label"]

#     # 3. Formatted Single Output Print
#     display_df = summary_df[
#         [
#             "top_pct_label",
#             "total_trades",
#             "overall_win_rate",
#             "aggregate_net_pnl",
#             "efficiency_per_trade",
#             "trades_per_mo_avg",
#         ]
#     ].copy()

#     display_df["aggregate_net_pnl"] = display_df["aggregate_net_pnl"].apply(
#         lambda x: f"${x:,.2f}"
#     )
#     display_df["efficiency_per_trade"] = display_df["efficiency_per_trade"].apply(
#         lambda x: f"${x:,.2f}"
#     )
#     display_df["overall_win_rate"] = display_df["overall_win_rate"].apply(
#         lambda x: f"{x:.1f}%"
#     )

#     print("==========================================================================================")
#     print("                              SWEEP ANALYTICS & RANKING                                   ")
#     print("==========================================================================================")
#     print(display_df.to_string(index=False))
#     print("==========================================================================================")
#     print(f"🏆 CAPITAL-EFFICIENT OPTIMAL THRESHOLD: top_pct = {optimal_pct:.2f} ({optimal_label})")
#     print(f"   • Aggregate Net PnL   : ${optimal_row['aggregate_net_pnl']:,.2f}")
#     print(f"   • Overall Win Rate    : {optimal_row['overall_win_rate']:.1f}%")
#     print(f"   • Total Trades        : {int(optimal_row['total_trades'])}")
#     print(f"   • Avg Trades / Month  : {optimal_row['trades_per_mo_avg']:.2f}")
#     print(f"   • Profit / Trade      : ${optimal_row['efficiency_per_trade']:,.2f}")
#     print("==========================================================================================\n")

#     # 4. Single-Canvas Diagnostic Plotting
#     fig, axes = plt.subplots(1, 2, figsize=(16, 6))

#     # Chart 1: System Robustness (Net PnL vs top_pct)
#     axes[0].plot(
#         summary_df["aggregate_net_pnl"],
#         summary_df["top_pct"],
#         marker="o",
#         linewidth=2.5,
#         markersize=8,
#         color="#1f77b4",
#         label="System Trajectory",
#     )
#     axes[0].scatter(
#         optimal_row["aggregate_net_pnl"],
#         optimal_row["top_pct"],
#         color="gold",
#         s=200,
#         edgecolors="black",
#         zorder=5,
#         label=f"Optimal ({optimal_label})",
#     )

#     for _, row in summary_df.iterrows():
#         axes[0].annotate(
#             f"{row['top_pct_label']}",
#             (row["aggregate_net_pnl"], row["top_pct"]),
#             xytext=(8, -3),
#             textcoords="offset points",
#             fontsize=9,
#             fontweight="bold",
#         )

#     axes[0].axvline(0, color="red", linestyle="--", alpha=0.6, linewidth=1.5)
#     axes[0].set_xlabel("Aggregate Net PnL ($)", fontsize=11, fontweight="bold")
#     axes[0].set_ylabel("RS Filter Threshold (top_pct)", fontsize=11, fontweight="bold")
#     axes[0].set_title("1. System Robustness & Decay Curve", fontsize=12, fontweight="bold")
#     axes[0].grid(True, linestyle=":", alpha=0.6)
#     axes[0].legend(loc="upper left")

#     # Chart 2: Capital Efficiency (Net PnL vs Total Trades)
#     axes[1].scatter(
#         summary_df["aggregate_net_pnl"],
#         summary_df["total_trades"],
#         c=summary_df["top_pct"],
#         cmap="viridis",
#         s=120,
#         edgecolors="black",
#         alpha=0.9,
#     )
#     axes[1].scatter(
#         optimal_row["aggregate_net_pnl"],
#         optimal_row["total_trades"],
#         color="gold",
#         s=220,
#         edgecolors="black",
#         zorder=5,
#         label=f"Optimal ({optimal_label})",
#     )

#     for _, row in summary_df.iterrows():
#         axes[1].annotate(
#             f"{row['top_pct_label']} (${row['efficiency_per_trade']:.0f}/tr)",
#             (row["aggregate_net_pnl"], row["total_trades"]),
#             xytext=(8, -3),
#             textcoords="offset points",
#             fontsize=8.5,
#         )

#     axes[1].axvline(0, color="red", linestyle="--", alpha=0.6, linewidth=1.5)
#     axes[1].set_xlabel("Aggregate Net PnL ($)", fontsize=11, fontweight="bold")
#     axes[1].set_ylabel("Total Executed Trades", fontsize=11, fontweight="bold")
#     axes[1].set_title("2. Capital Efficiency: Net PnL vs. Trade Volume", fontsize=12, fontweight="bold")
#     axes[1].grid(True, linestyle=":", alpha=0.6)
#     axes[1].legend(loc="upper left")

#     plt.suptitle("Portfolio Parameter Sweep Analytics (5% to 80% RS)", fontsize=14, fontweight="bold", y=0.98)
#     plt.tight_layout()
#     plt.show()


# def generate_per_stock_trade_analytics(excel_path: str):
#     """
#     1. Identifies optimal top_pct from 'Sweep Summary'.
#     2. Filters trades from 'Trade Log' matching optimal top_pct.
#     3. Formats open_date, close_date, and holding_period (days).
#     4. Sorts trades by close_date descending (most recent first).
#     5. Creates/updates an individual Excel tab for each unique stock ticker.
#     """
#     if not os.path.exists(excel_path):
#         return

#     summary_df = pd.read_excel(excel_path, sheet_name="Sweep Summary")
#     trades_df = pd.read_excel(excel_path, sheet_name="Trade Log")

#     summary_df["efficiency_per_trade"] = (
#         summary_df["aggregate_net_pnl"] / summary_df["total_trades"]
#     )
#     valid_candidates = summary_df[
#         (summary_df["overall_win_rate"] >= 47.0)
#         & (summary_df["efficiency_per_trade"] >= 400.0)
#     ].copy()

#     if not valid_candidates.empty:
#         valid_candidates["composite_score"] = (
#             valid_candidates["aggregate_net_pnl"] * valid_candidates["efficiency_per_trade"]
#         )
#         optimal_row = valid_candidates.sort_values(
#             by="composite_score", ascending=False
#         ).iloc[0]
#     else:
#         optimal_row = summary_df.sort_values(
#             by="aggregate_net_pnl", ascending=False
#         ).iloc[0]

#     optimal_pct = optimal_row["top_pct"]
#     filtered_trades = trades_df[trades_df["top_pct"] == optimal_pct].copy()

#     if filtered_trades.empty:
#         return

#     filtered_trades["entry_date"] = pd.to_datetime(filtered_trades["entry_date"])
#     filtered_trades["exit_date"] = pd.to_datetime(filtered_trades["exit_date"])

#     filtered_trades["open_date"] = filtered_trades["entry_date"].dt.strftime("%Y-%m-%d")
#     filtered_trades["close_date"] = filtered_trades["exit_date"].dt.strftime("%Y-%m-%d")
#     filtered_trades["holding_period"] = (filtered_trades["exit_date"] - filtered_trades["entry_date"]).dt.days

#     output_columns = [
#         "ticker",
#         "open_date",
#         "close_date",
#         "holding_period",
#         "entry_price",
#         "stop_loss",
#         "target_price",
#         "shares",
#         "status",
#         "pnl",
#         "exit_price",
#         "top_pct"
#     ]

#     with pd.ExcelWriter(excel_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
#         tickers = filtered_trades["ticker"].unique()
#         for ticker in tickers:
#             stock_df = filtered_trades[filtered_trades["ticker"] == ticker].copy()
#             stock_df = stock_df.sort_values(by="exit_date", ascending=False)
            
#             stock_analytics_df = stock_df[output_columns]
#             sheet_name = str(ticker).upper()[:31]
#             stock_analytics_df.to_excel(writer, sheet_name=sheet_name, index=False)
#             print(f"✅ Added per-stock tab '{sheet_name}' with {len(stock_analytics_df)} trades.")


# def plot_stock_equity_curve(excel_path: str, ticker: str = "QCOM"):
#     """
#     Loads trade logs, plots a step-wise equity curve, and adds interactive 
#     hover tooltips showing Entry Date, Exit Date, Trade PnL, and Cumulative PnL.
#     """
#     try:
#         xls = pd.ExcelFile(excel_path)
#         target_sheet = next((s for s in [ticker.upper(), "Trade Log", "Trades"] if s in xls.sheet_names), xls.sheet_names[0])
#         trades_df = pd.read_excel(excel_path, sheet_name=target_sheet)
#     except Exception as e:
#         print(f"[!] Could not load trade log sheet: {e}")
#         return

#     ticker_col = next((col for col in ["ticker", "symbol", "stock"] if col in trades_df.columns), None)
#     exit_date_col = next((col for col in ["exit_date", "close_date", "date", "sell_date"] if col in trades_df.columns), None)
#     entry_date_col = next((col for col in ["entry_date", "open_date", "start_date", "buy_date"] if col in trades_df.columns), None)
#     pnl_col = next((col for col in ["pnl", "net_pnl", "profit", "gain"] if col in trades_df.columns), None)

#     if not exit_date_col or not pnl_col:
#         print("[!] Error: Could not automatically detect required columns.")
#         return

#     if ticker_col:
#         stock_trades = trades_df[trades_df[ticker_col].astype(str).str.upper() == ticker.upper()].copy()
#     else:
#         stock_trades = trades_df.copy()

#     if stock_trades.empty:
#         print(f"[!] No trades found for ticker: {ticker.upper()}")
#         return

#     stock_trades[exit_date_col] = pd.to_datetime(stock_trades[exit_date_col])
#     if entry_date_col:
#         stock_trades[entry_date_col] = pd.to_datetime(stock_trades[entry_date_col])

#     stock_trades = stock_trades.sort_values(exit_date_col)

#     stock_trades["cumulative_pnl"] = stock_trades[pnl_col].cumsum()
#     stock_trades["dot_color"] = stock_trades[pnl_col].apply(lambda x: "#2ca02c" if x >= 0 else "#d62728")

#     total_pnl = stock_trades["cumulative_pnl"].iloc[-1]
#     total_trades = len(stock_trades)
#     win_count = len(stock_trades[stock_trades[pnl_col] > 0])
#     win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0

#     plt.figure(figsize=(12, 6))
    
#     plt.plot(
#         stock_trades[exit_date_col],
#         stock_trades["cumulative_pnl"],
#         drawstyle="steps-post",
#         color="#1f77b4",
#         linewidth=2,
#         alpha=0.8,
#         label="Equity Path"
#     )

#     scatter = plt.scatter(
#         stock_trades[exit_date_col],
#         stock_trades["cumulative_pnl"],
#         c=stock_trades["dot_color"],
#         s=60,
#         zorder=5,
#         edgecolors="black",
#         linewidths=0.8,
#         label="Executed Trades (Green=Win, Red=Loss)"
#     )

#     plt.axhline(0, color="gray", linestyle="--", alpha=0.7, linewidth=1)
#     plt.title(
#         f"{ticker.upper()} Equity Curve | Net PnL: ${total_pnl:,.2f} | Trades: {total_trades} | Win Rate: {win_rate:.1f}%", 
#         fontsize=12, 
#         fontweight="bold"
#     )
#     plt.xlabel("Trade Exit Date", fontsize=11, fontweight="bold")
#     plt.ylabel("Cumulative Net PnL ($)", fontsize=11, fontweight="bold")
#     plt.grid(True, linestyle=":", alpha=0.6)
#     plt.legend(loc="upper left")

#     try:
#         import mplcursors
#         cursor = mplcursors.cursor(scatter, hover=True)
#         @cursor.connect("add")
#         def on_add(sel):
#             idx = sel.index
#             row = stock_trades.iloc[idx]
#             entry_str = row[entry_date_col].strftime('%Y-%m-%d') if entry_date_col and pd.notnull(row[entry_date_col]) else "N/A"
#             exit_str = row[exit_date_col].strftime('%Y-%m-%d') if pd.notnull(row[exit_date_col]) else "N/A"
#             pnl_val = row[pnl_col]
#             cum_pnl = row["cumulative_pnl"]
            
#             sel.annotation.set_text(
#                 f"Trade #{idx + 1}\n"
#                 f"• Entry: {entry_str}\n"
#                 f"• Exit:  {exit_str}\n"
#                 f"• PnL:   ${pnl_val:,.2f}\n"
#                 f"• Total: ${cum_pnl:,.2f}"
#             )
#             sel.annotation.get_bbox_box().set(alpha=0.9, fc="white", ec="black")
#     except ImportError:
#         print("[!] Note: Install `mplcursors` via pip to enable interactive hover tooltips.")

#     plt.tight_layout()
#     plt.show()


# if __name__ == "__main__":
#     excel_file = os.path.join(
#         project_root, "data", "backtest_results", "sweep_analytics.xlsx"
#     )
    
#     # 1. Run sweep analytics printouts and summary charts
#     analyze_sweep_excel(excel_file)

#     # 2. Generate the individual per-stock tabs with open_date, close_date, holding_period
#     generate_per_stock_trade_analytics(excel_file)

#     # 3. Plot equity curve for a specific individual stock
#     plot_stock_equity_curve(excel_file, ticker="QCOM")

import os
import sys
import matplotlib.pyplot as plt
import pandas as pd
import openpyxl

# Force project root into sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def analyze_sweep_excel(excel_path: str):
    if not os.path.exists(excel_path):
        print(f"[!] File not found: {excel_path}")
        print("    Run `python -m src.backtest.engine` first to generate sweep_analytics.xlsx.")
        return

    print(f"[*] Loading backtest sweep data from:\n    {excel_path}\n")
    summary_df = pd.read_excel(excel_path, sheet_name="Sweep Summary")

    # 1. Calculate Per-Trade Efficiency Metrics
    summary_df["efficiency_per_trade"] = (
        summary_df["aggregate_net_pnl"] / summary_df["total_trades"]
    )

    # 2. Capital Efficiency Selection Logic
    valid_candidates = summary_df[
        (summary_df["overall_win_rate"] >= 47.0)
        & (summary_df["efficiency_per_trade"] >= 400.0)
    ].copy()

    if not valid_candidates.empty:
        valid_candidates["composite_score"] = (
            valid_candidates["aggregate_net_pnl"] * valid_candidates["efficiency_per_trade"]
        )
        optimal_row = valid_candidates.sort_values(
            by="composite_score", ascending=False
        ).iloc[0]
    else:
        optimal_row = summary_df.sort_values(
            by="aggregate_net_pnl", ascending=False
        ).iloc[0]

    optimal_pct = optimal_row["top_pct"]
    optimal_label = optimal_row["top_pct_label"]

    # 3. Formatted Single Output Print
    display_df = summary_df[
        [
            "top_pct_label",
            "total_trades",
            "overall_win_rate",
            "aggregate_net_pnl",
            "efficiency_per_trade",
            "trades_per_mo_avg",
        ]
    ].copy()

    display_df["aggregate_net_pnl"] = display_df["aggregate_net_pnl"].apply(
        lambda x: f"${x:,.2f}"
    )
    display_df["efficiency_per_trade"] = display_df["efficiency_per_trade"].apply(
        lambda x: f"${x:,.2f}"
    )
    display_df["overall_win_rate"] = display_df["overall_win_rate"].apply(
        lambda x: f"{x:.1f}%"
    )

    print("==========================================================================================")
    print("                              SWEEP ANALYTICS & RANKING                                   ")
    print("==========================================================================================")
    print(display_df.to_string(index=False))
    print("==========================================================================================")
    print(f"🏆 CAPITAL-EFFICIENT OPTIMAL THRESHOLD: top_pct = {optimal_pct:.2f} ({optimal_label})")
    print(f"   • Aggregate Net PnL   : ${optimal_row['aggregate_net_pnl']:,.2f}")
    print(f"   • Overall Win Rate    : {optimal_row['overall_win_rate']:.1f}%")
    print(f"   • Total Trades        : {int(optimal_row['total_trades'])}")
    print(f"   • Avg Trades / Month  : {optimal_row['trades_per_mo_avg']:.2f}")
    print(f"   • Profit / Trade      : ${optimal_row['efficiency_per_trade']:,.2f}")
    print("==========================================================================================\n")

    # 4. Single-Canvas Diagnostic Plotting
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Chart 1: System Robustness (Net PnL vs top_pct)
    axes[0].plot(
        summary_df["aggregate_net_pnl"],
        summary_df["top_pct"],
        marker="o",
        linewidth=2.5,
        markersize=8,
        color="#1f77b4",
        label="System Trajectory",
    )
    axes[0].scatter(
        optimal_row["aggregate_net_pnl"],
        optimal_row["top_pct"],
        color="gold",
        s=200,
        edgecolors="black",
        zorder=5,
        label=f"Optimal ({optimal_label})",
    )

    for _, row in summary_df.iterrows():
        axes[0].annotate(
            f"{row['top_pct_label']}",
            (row["aggregate_net_pnl"], row["top_pct"]),
            xytext=(8, -3),
            textcoords="offset points",
            fontsize=9,
            fontweight="bold",
        )

    axes[0].axvline(0, color="red", linestyle="--", alpha=0.6, linewidth=1.5)
    axes[0].set_xlabel("Aggregate Net PnL ($)", fontsize=11, fontweight="bold")
    axes[0].set_ylabel("RS Filter Threshold (top_pct)", fontsize=11, fontweight="bold")
    axes[0].set_title("1. System Robustness & Decay Curve", fontsize=12, fontweight="bold")
    axes[0].grid(True, linestyle=":", alpha=0.6)
    axes[0].legend(loc="upper left")

    # Chart 2: Capital Efficiency (Net PnL vs Total Trades)
    axes[1].scatter(
        summary_df["aggregate_net_pnl"],
        summary_df["total_trades"],
        c=summary_df["top_pct"],
        cmap="viridis",
        s=120,
        edgecolors="black",
        alpha=0.9,
    )
    axes[1].scatter(
        optimal_row["aggregate_net_pnl"],
        optimal_row["total_trades"],
        color="gold",
        s=220,
        edgecolors="black",
        zorder=5,
        label=f"Optimal ({optimal_label})",
    )

    for _, row in summary_df.iterrows():
        axes[1].annotate(
            f"{row['top_pct_label']} (${row['efficiency_per_trade']:.0f}/tr)",
            (row["aggregate_net_pnl"], row["total_trades"]),
            xytext=(8, -3),
            textcoords="offset points",
            fontsize=8.5,
        )

    axes[1].axvline(0, color="red", linestyle="--", alpha=0.6, linewidth=1.5)
    axes[1].set_xlabel("Aggregate Net PnL ($)", fontsize=11, fontweight="bold")
    axes[1].set_ylabel("Total Executed Trades", fontsize=11, fontweight="bold")
    axes[1].set_title("2. Capital Efficiency: Net PnL vs. Trade Volume", fontsize=12, fontweight="bold")
    axes[1].grid(True, linestyle=":", alpha=0.6)
    axes[1].legend(loc="upper left")

    plt.suptitle("Portfolio Parameter Sweep Analytics (5% to 80% RS)", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout()
    plt.show()

def load_stock_price_on_date(ticker: str, target_date: pd.Timestamp) -> float:
    """
    Looks up the historical price for a given ticker on a specific date 
    from your local parquet data cache using 'Close'.
    """
    parquet_path = os.path.join(project_root, "data", "cache", f"{ticker.upper()}.parquet")
    
    if not os.path.exists(parquet_path):
        return None

    try:
        df = pd.read_parquet(parquet_path)
        
        # Handle date index or column capitalization
        date_col = next((c for c in df.columns if str(c).lower() == "date"), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.set_index(date_col)
        
        # Explicitly look for 'Close' with uppercase C, or fallback variants
        price_col = next((col for col in ["Close", "close", "Adj Close", "price", "Open"] if col in df.columns), None)
        if not price_col:
            print(f"[!] Warning: No price column found in parquet for {ticker}. Columns: {list(df.columns)}")
            return None

        available_dates = df.index
        matching_dates = available_dates[available_dates >= target_date]
        
        if len(matching_dates) > 0:
            exact_date = matching_dates[0]
            return float(df.loc[exact_date, price_col])
    except Exception as e:
        print(f"[!] Error reading price cache for {ticker}: {e}")
        
    return None

# def load_stock_price_on_date(ticker: str, target_date: pd.Timestamp) -> float:
#     """
#     Looks up the historical price for a given ticker on a specific date 
#     from your local parquet data cache.
#     """
#     parquet_path = os.path.join(project_root, "data", "cache", f"{ticker.upper()}.parquet")
    
#     if not os.path.exists(parquet_path):
#         return None

#     try:
#         df = pd.read_parquet(parquet_path)
#         if "date" in df.columns:
#             df["date"] = pd.to_datetime(df["date"])
#             df = df.set_index("date")
        
#         available_dates = df.index
#         matching_dates = available_dates[available_dates >= target_date]
        
#         if len(matching_dates) > 0:
#             exact_date = matching_dates[0]
#             return float(df.loc[exact_date, "close"])
#     except Exception as e:
#         print(f"[!] Error reading price cache for {ticker}: {e}")
        
#     return None

import os
import sys
import matplotlib.pyplot as plt
import pandas as pd
import openpyxl

# Force project root into sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def analyze_sweep_excel(excel_path: str):
    if not os.path.exists(excel_path):
        print(f"[!] File not found: {excel_path}")
        print("    Run `python -m src.backtest.engine` first to generate sweep_analytics.xlsx.")
        return

    print(f"[*] Loading backtest sweep data from:\n    {excel_path}\n")
    summary_df = pd.read_excel(excel_path, sheet_name="Sweep Summary")

    # 1. Calculate Per-Trade Efficiency Metrics
    summary_df["efficiency_per_trade"] = (
        summary_df["aggregate_net_pnl"] / summary_df["total_trades"]
    )

    # 2. Capital Efficiency Selection Logic
    valid_candidates = summary_df[
        (summary_df["overall_win_rate"] >= 47.0)
        & (summary_df["efficiency_per_trade"] >= 400.0)
    ].copy()

    if not valid_candidates.empty:
        valid_candidates["composite_score"] = (
            valid_candidates["aggregate_net_pnl"] * valid_candidates["efficiency_per_trade"]
        )
        optimal_row = valid_candidates.sort_values(
            by="composite_score", ascending=False
        ).iloc[0]
    else:
        optimal_row = summary_df.sort_values(
            by="aggregate_net_pnl", ascending=False
        ).iloc[0]

    optimal_pct = optimal_row["top_pct"]
    optimal_label = optimal_row["top_pct_label"]

    # 3. Formatted Single Output Print
    display_df = summary_df[
        [
            "top_pct_label",
            "total_trades",
            "overall_win_rate",
            "aggregate_net_pnl",
            "efficiency_per_trade",
            "trades_per_mo_avg",
        ]
    ].copy()

    display_df["aggregate_net_pnl"] = display_df["aggregate_net_pnl"].apply(
        lambda x: f"${x:,.2f}"
    )
    display_df["efficiency_per_trade"] = display_df["efficiency_per_trade"].apply(
        lambda x: f"${x:,.2f}"
    )
    display_df["overall_win_rate"] = display_df["overall_win_rate"].apply(
        lambda x: f"{x:.1f}%"
    )

    print("==========================================================================================")
    print("                              SWEEP ANALYTICS & RANKING                                   ")
    print("==========================================================================================")
    print(display_df.to_string(index=False))
    print("==========================================================================================")
    print(f"🏆 INITIAL OPTIMAL THRESHOLD (Pre-Time Stop): top_pct = {optimal_pct:.2f} ({optimal_label})")
    print(f"   • Aggregate Net PnL   : ${optimal_row['aggregate_net_pnl']:,.2f}")
    print(f"   • Overall Win Rate    : {optimal_row['overall_win_rate']:.1f}%")
    print(f"   • Total Trades        : {int(optimal_row['total_trades'])}")
    print(f"   • Avg Trades / Month  : {optimal_row['trades_per_mo_avg']:.2f}")
    print(f"   • Profit / Trade      : ${optimal_row['efficiency_per_trade']:,.2f}")
    print("==========================================================================================\n")

    # 4. Single-Canvas Diagnostic Plotting
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    axes[0].plot(
        summary_df["aggregate_net_pnl"],
        summary_df["top_pct"],
        marker="o",
        linewidth=2.5,
        markersize=8,
        color="#1f77b4",
        label="System Trajectory",
    )
    axes[0].scatter(
        optimal_row["aggregate_net_pnl"],
        optimal_row["top_pct"],
        color="gold",
        s=200,
        edgecolors="black",
        zorder=5,
        label=f"Optimal ({optimal_label})",
    )

    for _, row in summary_df.iterrows():
        axes[0].annotate(
            f"{row['top_pct_label']}",
            (row["aggregate_net_pnl"], row["top_pct"]),
            xytext=(8, -3),
            textcoords="offset points",
            fontsize=9,
            fontweight="bold",
        )

    axes[0].axvline(0, color="red", linestyle="--", alpha=0.6, linewidth=1.5)
    axes[0].set_xlabel("Aggregate Net PnL ($)", fontsize=11, fontweight="bold")
    axes[0].set_ylabel("RS Filter Threshold (top_pct)", fontsize=11, fontweight="bold")
    axes[0].set_title("1. System Robustness & Decay Curve", fontsize=12, fontweight="bold")
    axes[0].grid(True, linestyle=":", alpha=0.6)
    axes[0].legend(loc="upper left")

    axes[1].scatter(
        summary_df["aggregate_net_pnl"],
        summary_df["total_trades"],
        c=summary_df["top_pct"],
        cmap="viridis",
        s=120,
        edgecolors="black",
        alpha=0.9,
    )
    axes[1].scatter(
        optimal_row["aggregate_net_pnl"],
        optimal_row["total_trades"],
        color="gold",
        s=220,
        edgecolors="black",
        zorder=5,
        label=f"Optimal ({optimal_label})",
    )

    for _, row in summary_df.iterrows():
        axes[1].annotate(
            f"{row['top_pct_label']} (${row['efficiency_per_trade']:.0f}/tr)",
            (row["aggregate_net_pnl"], row["total_trades"]),
            xytext=(8, -3),
            textcoords="offset points",
            fontsize=8.5,
        )

    axes[1].axvline(0, color="red", linestyle="--", alpha=0.6, linewidth=1.5)
    axes[1].set_xlabel("Aggregate Net PnL ($)", fontsize=11, fontweight="bold")
    axes[1].set_ylabel("Total Executed Trades", fontsize=11, fontweight="bold")
    axes[1].set_title("2. Capital Efficiency: Net PnL vs. Trade Volume", fontsize=12, fontweight="bold")
    axes[1].grid(True, linestyle=":", alpha=0.6)
    axes[1].legend(loc="upper left")

    plt.suptitle("Portfolio Parameter Sweep Analytics (5% to 80% RS)", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout()
    plt.show()


def load_stock_price_on_date(ticker: str, target_date: pd.Timestamp) -> float:
    """
    Looks up the historical price for a given ticker on a specific date 
    from your local parquet data cache using 'Close'.
    """
    parquet_path = os.path.join(project_root, "data", "cache", f"{ticker.upper()}.parquet")
    
    if not os.path.exists(parquet_path):
        return None

    try:
        df = pd.read_parquet(parquet_path)
        
        date_col = next((c for c in df.columns if str(c).lower() == "date"), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.set_index(date_col)
        
        price_col = next((col for col in ["Close", "close", "Adj Close", "price", "Open"] if col in df.columns), None)
        if not price_col:
            return None

        available_dates = df.index
        matching_dates = available_dates[available_dates >= target_date]
        
        if len(matching_dates) > 0:
            exact_date = matching_dates[0]
            return float(df.loc[exact_date, price_col])
    except Exception as e:
        print(f"[!] Error reading price cache for {ticker}: {e}")
        
    return None


def generate_per_stock_trade_analytics_with_timestop(excel_path: str, max_days: int = 60):
    """
    1. Identifies optimal top_pct from 'Sweep Summary'.
    2. Filters trades matching optimal top_pct.
    3. Applies 60-day Time Stop and recalculates portfolio stats post-adjustment.
    4. Outputs individual ticker tabs.
    """
    if not os.path.exists(excel_path):
        return

    summary_df = pd.read_excel(excel_path, sheet_name="Sweep Summary")
    trades_df = pd.read_excel(excel_path, sheet_name="Trade Log")

    summary_df["efficiency_per_trade"] = (
        summary_df["aggregate_net_pnl"] / summary_df["total_trades"]
    )
    valid_candidates = summary_df[
        (summary_df["overall_win_rate"] >= 47.0)
        & (summary_df["efficiency_per_trade"] >= 400.0)
    ].copy()

    if not valid_candidates.empty:
        valid_candidates["composite_score"] = (
            valid_candidates["aggregate_net_pnl"] * valid_candidates["efficiency_per_trade"]
        )
        optimal_row = valid_candidates.sort_values(by="composite_score", ascending=False).iloc[0]
    else:
        optimal_row = summary_df.sort_values(by="aggregate_net_pnl", ascending=False).iloc[0]

    optimal_pct = optimal_row["top_pct"]
    optimal_label = optimal_row["top_pct_label"]
    filtered_trades = trades_df[trades_df["top_pct"] == optimal_pct].copy()

    if filtered_trades.empty:
        return

    filtered_trades["entry_date"] = pd.to_datetime(filtered_trades["entry_date"])
    filtered_trades["exit_date"] = pd.to_datetime(filtered_trades["exit_date"])

    processed_trades = []

    for _, row in filtered_trades.iterrows():
        entry_date = row["entry_date"]
        exit_date = row["exit_date"]
        ticker = row["ticker"]
        entry_price = row["entry_price"]
        shares = row["shares"]
        
        natural_holding_days = (exit_date - entry_date).days

        if natural_holding_days > max_days:
            target_exit_date = entry_date + pd.Timedelta(days=max_days)
            lookup_price = load_stock_price_on_date(ticker, target_exit_date)
            
            if lookup_price is not None:
                row["exit_date"] = target_exit_date
                row["exit_price"] = lookup_price
                row["holding_period"] = max_days
                row["status"] = "CLOSED_TIME_STOP"
                row["pnl"] = (lookup_price - entry_price) * shares
            else:
                row["holding_period"] = natural_holding_days
        else:
            row["holding_period"] = natural_holding_days

        row["open_date"] = entry_date.strftime("%Y-%m-%d")
        row["close_date"] = pd.to_datetime(row["exit_date"]).strftime("%Y-%m-%d")
        processed_trades.append(row)

    final_trades_df = pd.DataFrame(processed_trades)

    # --- RECALCULATE PORTFOLIO METRICS POST-TIME STOP ---
    post_total_trades = len(final_trades_df)
    post_aggregate_pnl = final_trades_df["pnl"].sum()
    post_wins = len(final_trades_df[final_trades_df["pnl"] > 0])
    post_win_rate = (post_wins / post_total_trades) * 100 if post_total_trades > 0 else 0
    post_profit_per_trade = post_aggregate_pnl / post_total_trades if post_total_trades > 0 else 0
    
    # Calculate month span for average trades per month
    min_date = final_trades_df["entry_date"].min()
    max_date = final_trades_df["exit_date"].max()
    total_months = max(1.0, (max_date - min_date).days / 30.44)
    post_trades_per_mo = post_total_trades / total_months

    print("==========================================================================================")
    print(f"🏆 CAPITAL-EFFICIENT OPTIMAL THRESHOLD (POST-TIME STOP 60-DAY): top_pct = {optimal_pct:.2f} ({optimal_label})")
    print(f"   • Aggregate Net PnL   : ${post_aggregate_pnl:,.2f}")
    print(f"   • Overall Win Rate    : {post_win_rate:.1f}%")
    print(f"   • Total Trades        : {post_total_trades}")
    print(f"   • Avg Trades / Month  : {post_trades_per_mo:.2f}")
    print(f"   • Profit / Trade      : ${post_profit_per_trade:,.2f}")
    print("==========================================================================================")

    output_columns = [
        "ticker",
        "open_date",
        "close_date",
        "holding_period",
        "entry_price",
        "stop_loss",
        "target_price",
        "shares",
        "status",
        "pnl",
        "exit_price",
        "top_pct"
    ]

    with pd.ExcelWriter(excel_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        tickers = final_trades_df["ticker"].unique()
        for ticker in tickers:
            stock_df = final_trades_df[final_trades_df["ticker"] == ticker].copy()
            stock_df = stock_df.sort_values(by="exit_date", ascending=False)
            
            stock_analytics_df = stock_df[output_columns]
            sheet_name = str(ticker).upper()[:31]
            stock_analytics_df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"✅ Updated tab '{sheet_name}' with 60-day time-stop adjustments.")


def plot_stock_equity_curve(excel_path: str, ticker: str = "QCOM"):
    """
    Loads trade logs, plots a step-wise equity curve, and adds interactive 
    hover tooltips showing Entry Date, Exit Date, Trade PnL, and Cumulative PnL.
    """
    try:
        xls = pd.ExcelFile(excel_path)
        target_sheet = next((s for s in [ticker.upper(), "Trade Log", "Trades"] if s in xls.sheet_names), xls.sheet_names[0])
        trades_df = pd.read_excel(excel_path, sheet_name=target_sheet)
    except Exception as e:
        print(f"[!] Could not load trade log sheet: {e}")
        return

    ticker_col = next((col for col in ["ticker", "symbol", "stock"] if col in trades_df.columns), None)
    exit_date_col = next((col for col in ["exit_date", "close_date", "date", "sell_date"] if col in trades_df.columns), None)
    entry_date_col = next((col for col in ["entry_date", "open_date", "start_date", "buy_date"] if col in trades_df.columns), None)
    pnl_col = next((col for col in ["pnl", "net_pnl", "profit", "gain"] if col in trades_df.columns), None)

    if not exit_date_col or not pnl_col:
        print("[!] Error: Could not automatically detect required columns.")
        return

    if ticker_col:
        stock_trades = trades_df[trades_df[ticker_col].astype(str).str.upper() == ticker.upper()].copy()
    else:
        stock_trades = trades_df.copy()

    if stock_trades.empty:
        print(f"[!] No trades found for ticker: {ticker.upper()}")
        return

    stock_trades[exit_date_col] = pd.to_datetime(stock_trades[exit_date_col])
    if entry_date_col:
        stock_trades[entry_date_col] = pd.to_datetime(stock_trades[entry_date_col])

    stock_trades = stock_trades.sort_values(exit_date_col)

    stock_trades["cumulative_pnl"] = stock_trades[pnl_col].cumsum()
    stock_trades["dot_color"] = stock_trades[pnl_col].apply(lambda x: "#2ca02c" if x >= 0 else "#d62728")

    total_pnl = stock_trades["cumulative_pnl"].iloc[-1]
    total_trades = len(stock_trades)
    win_count = len(stock_trades[stock_trades[pnl_col] > 0])
    win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0

    plt.figure(figsize=(12, 6))
    
    plt.plot(
        stock_trades[exit_date_col],
        stock_trades["cumulative_pnl"],
        drawstyle="steps-post",
        color="#1f77b4",
        linewidth=2,
        alpha=0.8,
        label="Equity Path"
    )

    scatter = plt.scatter(
        stock_trades[exit_date_col],
        stock_trades["cumulative_pnl"],
        c=stock_trades["dot_color"],
        s=60,
        zorder=5,
        edgecolors="black",
        linewidths=0.8,
        label="Executed Trades (Green=Win, Red=Loss)"
    )

    plt.axhline(0, color="gray", linestyle="--", alpha=0.7, linewidth=1)
    plt.title(
        f"{ticker.upper()} Equity Curve | Net PnL: ${total_pnl:,.2f} | Trades: {total_trades} | Win Rate: {win_rate:.1f}%", 
        fontsize=12, 
        fontweight="bold"
    )
    plt.xlabel("Trade Exit Date", fontsize=11, fontweight="bold")
    plt.ylabel("Cumulative Net PnL ($)", fontsize=11, fontweight="bold")
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(loc="upper left")

    try:
        import mplcursors
        cursor = mplcursors.cursor(scatter, hover=True)
        @cursor.connect("add")
        def on_add(sel):
            idx = sel.index
            row = stock_trades.iloc[idx]
            entry_str = row[entry_date_col].strftime('%Y-%m-%d') if entry_date_col and pd.notnull(row[entry_date_col]) else "N/A"
            exit_str = row[exit_date_col].strftime('%Y-%m-%d') if pd.notnull(row[exit_date_col]) else "N/A"
            pnl_val = row[pnl_col]
            cum_pnl = row["cumulative_pnl"]
            
            sel.annotation.set_text(
                f"Trade #{idx + 1}\n"
                f"• Entry: {entry_str}\n"
                f"• Exit:  {exit_str}\n"
                f"• PnL:   ${pnl_val:,.2f}\n"
                f"• Total: ${cum_pnl:,.2f}"
            )
            sel.annotation.get_bbox_box().set(alpha=0.9, fc="white", ec="black")
    except ImportError:
        print("[!] Note: Install `mplcursors` via pip to enable interactive hover tooltips.")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    excel_file = os.path.join(
        project_root, "data", "backtest_results", "sweep_analytics.xlsx"
    )
    
    # 1. Run sweep analytics printouts and summary charts
    analyze_sweep_excel(excel_file)

    # 2. Run time-stop adjustments, calculate post-time-stop metrics, and generate individual tabs
    generate_per_stock_trade_analytics_with_timestop(excel_file, max_days=60)

    # 3. Plot equity curve for a specific individual stock
    plot_stock_equity_curve(excel_file, ticker="QCOM")