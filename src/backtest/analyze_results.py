import os
import sys
import matplotlib.pyplot as plt
import pandas as pd

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
    # Requires Win Rate >= 47.0% and Profit per Trade >= $400.00 to avoid over-trading drag
    valid_candidates = summary_df[
        (summary_df["overall_win_rate"] >= 47.0)
        & (summary_df["efficiency_per_trade"] >= 400.0)
    ].copy()

    if not valid_candidates.empty:
        # Score candidates by balancing aggregate returns with per-trade efficiency
        valid_candidates["composite_score"] = (
            valid_candidates["aggregate_net_pnl"] * valid_candidates["efficiency_per_trade"]
        )
        optimal_row = valid_candidates.sort_values(
            by="composite_score", ascending=False
        ).iloc[0]
    else:
        # Fallback to highest net PnL if no candidates meet strict criteria
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
    print("                                SWEEP ANALYTICS & RANKING                                 ")
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


def plot_stock_equity_curve(excel_path: str, ticker: str = "QCOM"):
    """
    Loads trade logs, plots a step-wise equity curve, and adds interactive 
    hover tooltips showing Entry Date, Exit Date, Trade PnL, and Cumulative PnL.
    """
    try:
        xls = pd.ExcelFile(excel_path)
        target_sheet = next((s for s in ["Trade Log", "Trades", "Trade_Log"] if s in xls.sheet_names), xls.sheet_names[0])
        trades_df = pd.read_excel(excel_path, sheet_name=target_sheet)
    except Exception as e:
        print(f"[!] Could not load trade log sheet: {e}")
        return

    # Flexible column mapping
    ticker_col = next((col for col in ["ticker", "symbol", "stock"] if col in trades_df.columns), None)
    exit_date_col = next((col for col in ["exit_date", "date", "sell_date", "close_date"] if col in trades_df.columns), None)
    entry_date_col = next((col for col in ["entry_date", "open_date", "start_date", "buy_date"] if col in trades_df.columns), None)
    pnl_col = next((col for col in ["net_pnl", "pnl", "profit", "gain"] if col in trades_df.columns), None)

    if not ticker_col or not exit_date_col or not pnl_col:
        print("[!] Error: Could not automatically detect required columns.")
        return

    # Filter and sort data chronologically
    stock_trades = trades_df[trades_df[ticker_col].astype(str).str.upper() == ticker.upper()].copy()
    if stock_trades.empty:
        print(f"[!] No trades found for ticker: {ticker.upper()}")
        return

    stock_trades[exit_date_col] = pd.to_datetime(stock_trades[exit_date_col])
    if entry_date_col:
        stock_trades[entry_date_col] = pd.to_datetime(stock_trades[entry_date_col])

    stock_trades = stock_trades.sort_values(exit_date_col)

    # Calculate metrics
    stock_trades["cumulative_pnl"] = stock_trades[pnl_col].cumsum()
    stock_trades["dot_color"] = stock_trades[pnl_col].apply(lambda x: "#2ca02c" if x >= 0 else "#d62728")

    total_pnl = stock_trades["cumulative_pnl"].iloc[-1]
    total_trades = len(stock_trades)
    win_count = len(stock_trades[stock_trades[pnl_col] > 0])
    win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0

    # Plotting
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

    # Add interactive hover tooltips using mplcursors
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
# def plot_stock_equity_curve(excel_path: str, ticker: str = "QCOM"):
#     """
#     Loads trade logs, filters for a specific stock, and plots a clear step-wise 
#     equity curve with color-coded winning (green) and losing (red) trades.
#     """
#     try:
#         xls = pd.ExcelFile(excel_path)
#         target_sheet = next((s for s in ["Trade Log", "Trades", "Trade_Log"] if s in xls.sheet_names), xls.sheet_names[0])
#         trades_df = pd.read_excel(excel_path, sheet_name=target_sheet)
#     except Exception as e:
#         print(f"[!] Could not load trade log sheet: {e}")
#         return

#     # Flexible column mapping
#     ticker_col = next((col for col in ["ticker", "symbol", "stock"] if col in trades_df.columns), None)
#     date_col = next((col for col in ["exit_date", "date", "sell_date", "close_date"] if col in trades_df.columns), None)
#     pnl_col = next((col for col in ["net_pnl", "pnl", "profit", "gain"] if col in trades_df.columns), None)

#     if not ticker_col or not date_col or not pnl_col:
#         print("[!] Error: Could not automatically detect required columns.")
#         return

#     # Filter and sort data chronologically
#     stock_trades = trades_df[trades_df[ticker_col].astype(str).str.upper() == ticker.upper()].copy()
#     if stock_trades.empty:
#         print(f"[!] No trades found for ticker: {ticker.upper()}")
#         return

#     stock_trades[date_col] = pd.to_datetime(stock_trades[date_col])
#     stock_trades = stock_trades.sort_values(date_col)

#     # Calculate cumulative PnL & assign colors (Green for win, Red for loss)
#     stock_trades["cumulative_pnl"] = stock_trades[pnl_col].cumsum()
#     stock_trades["dot_color"] = stock_trades[pnl_col].apply(lambda x: "#2ca02c" if x >= 0 else "#d62728")

#     total_pnl = stock_trades["cumulative_pnl"].iloc[-1]
#     total_trades = len(stock_trades)
#     win_count = len(stock_trades[stock_trades[pnl_col] > 0])
#     win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0

#     # Plotting
#     plt.figure(figsize=(12, 6))
    
#     # Step plot for accurate discrete equity changes
#     plt.plot(
#         stock_trades[date_col],
#         stock_trades["cumulative_pnl"],
#         drawstyle="steps-post",
#         color="#1f77b4",
#         linewidth=2,
#         alpha=0.8,
#         label="Equity Path"
#     )

#     # Scatter overlay for individual trades (Green = Win, Red = Loss)
#     plt.scatter(
#         stock_trades[date_col],
#         stock_trades["cumulative_pnl"],
#         c=stock_trades["dot_color"],
#         s=60,
#         zorder=5,
#         edgecolors="black",
#         linewidths=0.8,
#         label="Executed Trades (Green=Win, Red=Loss)"
#     )

#     # Styling and formatting
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
#     plt.tight_layout()
#     plt.show()

if __name__ == "__main__":
    excel_file = os.path.join(
        project_root, "data", "backtest_results", "sweep_analytics.xlsx"
    )
    analyze_sweep_excel(excel_file)


    # 2. Plot equity curve for a specific individual stock (e.g., Apple / AAPL)
    plot_stock_equity_curve(excel_file, ticker="QCOM")