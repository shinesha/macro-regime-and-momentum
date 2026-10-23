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


if __name__ == "__main__":
    excel_file = os.path.join(
        project_root, "data", "backtest_results", "sweep_analytics.xlsx"
    )
    analyze_sweep_excel(excel_file)