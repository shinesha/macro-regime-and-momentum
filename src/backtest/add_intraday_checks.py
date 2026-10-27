

# import os
# import sys
# import numpy as np
# import pandas as pd
# import openpyxl
# from openpyxl.formatting.rule import CellIsRule
# from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
# from openpyxl.chart import BarChart, Reference

# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)


# def get_price_at_time(day_df, time_str):
#     target_time = pd.to_datetime(time_str).time()
#     close_col = next((c for c in day_df.columns if str(c).lower() == "close"), None)
#     if not close_col:
#         return None

#     exact_match = day_df[day_df.index.time == target_time]
#     if not exact_match.empty:
#         return float(exact_match.iloc[0][close_col])
    
#     later_trades = day_df[day_df.index.time >= target_time]
#     if not later_trades.empty:
#         return float(later_trades.iloc[0][close_col])
#     return None


# def load_cached_intraday_prices(ticker: str, open_date_str: str):
#     open_date = pd.to_datetime(open_date_str).normalize()
#     date_str = open_date.strftime("%Y-%m-%d")
#     cache_file = os.path.join(project_root, "data", "intraday_cache", f"{ticker.upper()}_{date_str}.parquet")

#     if not os.path.exists(cache_file):
#         return None, None, None

#     try:
#         day_data = pd.read_parquet(cache_file)
#     except Exception:
#         return None, None, None

#     p1 = get_price_at_time(day_data, "09:31")
#     p5 = get_price_at_time(day_data, "09:35")
#     p10 = get_price_at_time(day_data, "09:40")
    
#     return p1, p5, p10


# def calculate_iqr(series):
#     if len(series) < 2:
#         return 0.0
#     q75, q25 = np.percentile(series, [75, 25])
#     return float(q75 - q25)


# def process_excel_analytics(excel_path: str):
#     if not os.path.exists(excel_path):
#         print(f"[!] File not found: {excel_path}")
#         return

#     print(f"[*] Processing analytics & distributional breakdown on: {excel_path}\n")
    
#     xls = pd.ExcelFile(excel_path)
#     exclude_sheets = {"Sweep Summary", "Trade Log"}
#     ticker_sheets = [s for s in xls.sheet_names if s not in exclude_sheets]

#     total_trades_count = 0
#     all_1m_pnls = []
#     stock_summary_stats = []

#     with pd.ExcelWriter(excel_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
#         trade_log_df = pd.read_excel(excel_path, sheet_name="Trade Log")
#         trade_log_df.to_excel(writer, sheet_name="Trade Log", index=False)

#         for sheet in ticker_sheets:
#             df = pd.read_excel(excel_path, sheet_name=sheet)
            
#             prices_1m, prices_5m, prices_10m = [], [], []
#             print(f"[*] Analyzing sheet: {sheet} ({len(df)} trades)...")
            
#             for _, row in df.iterrows():
#                 ticker = row.get("ticker", sheet)
#                 open_date_str = row.get("open_date")
                
#                 p1, p5, p10 = load_cached_intraday_prices(ticker, open_date_str)
#                 prices_1m.append(p1)
#                 prices_5m.append(p5)
#                 prices_10m.append(p10)

#             df["price_1m"] = prices_1m
#             df["price_5m"] = prices_5m
#             df["price_10m"] = prices_10m

#             sheet_1m_pnls = []
#             for _, row in df.iterrows():
#                 orig_pnl = row.get("pnl", 0)
#                 entry = row.get("entry_price")
#                 shares = row.get("shares", 0)
#                 p1 = row.get("price_1m")

#                 if pd.notna(p1) and pd.notna(entry) and pd.notna(shares) and entry > 0:
#                     price_diff = p1 - entry
#                     adjusted_pnl = orig_pnl - (price_diff * shares)
#                 else:
#                     adjusted_pnl = orig_pnl

#                 sheet_1m_pnls.append(adjusted_pnl)
#                 all_1m_pnls.append(adjusted_pnl)
#                 total_trades_count += 1

#             df["adjusted_pnl_1m"] = sheet_1m_pnls

#             # Calculate Per-Stock Distributional Metrics
#             n_trades = len(sheet_1m_pnls)
#             wins = [p for p in sheet_1m_pnls if p > 0]
#             win_rate = (len(wins) / n_trades * 100) if n_trades > 0 else 0
#             agg_pnl = sum(sheet_1m_pnls)
#             med_pnl = float(np.median(sheet_1m_pnls)) if n_trades > 0 else 0
#             win_iqr = calculate_iqr(wins) if wins else 0.0

#             stock_summary_stats.append({
#                 "Ticker": sheet,
#                 "Trades": n_trades,
#                 "Win Rate (%)": round(win_rate, 1),
#                 "Aggregate Net PnL ($)": round(agg_pnl, 2),
#                 "Median PnL ($)": round(med_pnl, 2),
#                 "Winning Trade IQR ($)": round(win_iqr, 2)
#             })

#             df.to_excel(writer, sheet_name=sheet, index=False)

#         # Build Per-Stock & Distribution Summary Table for Sweep Summary Sheet
#         summary_stats_df = pd.DataFrame(stock_summary_stats)
        
#         # Combine original Sweep Summary metrics with the new per-stock distribution breakdown table
#         base_summary_df = pd.read_excel(excel_path, sheet_name="Sweep Summary")
        
#         # Write back Sweep Summary
#         base_summary_df.to_excel(writer, sheet_name="Sweep Summary", index=False, startrow=0)
        
#         # Write Stock Distribution Table below it
#         start_row_for_dist = len(base_summary_df) + 3
#         summary_stats_df.to_excel(writer, sheet_name="Sweep Summary", index=False, startrow=start_row_for_dist)
#         print(f"✅ Added per-stock IQR and distribution breakdown to 'Sweep Summary'.")

#     # Apply Conditional Formatting & Embed Visual Chart via openpyxl
#     wb = openpyxl.load_workbook(excel_path)
#     blue_font = Font(color="0000FF", bold=True)
#     red_font = Font(color="FF0000", bold=True)

#     for sheet in ticker_sheets:
#         ws = wb[sheet]
#         header_row = [cell.value for cell in ws[1]]
#         try:
#             entry_col_idx = header_row.index("entry_price") + 1
#             p1_idx = header_row.index("price_1m") + 1
#             p5_idx = header_row.index("price_5m") + 1
#             p10_idx = header_row.index("price_10m") + 1
#         except ValueError:
#             continue
        
#         entry_col_letter = openpyxl.utils.get_column_letter(entry_col_idx)
#         max_row = ws.max_row
#         if max_row < 2:
#             continue

#         for col_idx in [p1_idx, p5_idx, p10_idx]:
#             col_letter = openpyxl.utils.get_column_letter(col_idx)
#             cell_range = f"{col_letter}2:{col_letter}{max_row}"
            
#             ws.conditional_formatting.add(
#                 cell_range,
#                 CellIsRule(operator='lessThan', formula=[f"{entry_col_letter}2"], stopIfTrue=True, font=blue_font)
#             )
#             ws.conditional_formatting.add(
#                 cell_range,
#                 CellIsRule(operator='greaterThan', formula=[f"{entry_col_letter}2"], stopIfTrue=True, font=red_font)
#             )

#     # Embed Graphical Chart on Sweep Summary Sheet
#     summary_ws = wb["Sweep Summary"]
#     chart = BarChart()
#     chart.type = "col"
#     chart.style = 10
#     chart.title = "Per-Stock 1-Minute Execution Net PnL"
#     chart.y_axis.title = "Net PnL ($)"
#     chart.x_axis.title = "Ticker"

#     # Reference data from the appended distribution table
#     # Columns: Ticker (col 1), Trades (col 2), Win Rate (col 3), Agg PnL (col 4)
#     num_stocks = len(stock_summary_stats)
#     data_min_row = start_row_for_dist + 1
#     data_max_row = start_row_for_dist + num_stocks
    
#     data = Reference(summary_ws, min_col=4, min_row=data_min_row, max_row=data_max_row)
#     cats = Reference(summary_ws, min_col=1, min_row=data_min_row, max_row=data_max_row)
    
#     chart.add_data(data, titles_from_data=True)
#     chart.set_categories(cats)
#     chart.legend = None  # No legend needed for single series

#     # Place chart next to the summary table
#     summary_ws.add_chart(chart, f"H{start_row_for_dist}")

#     wb.save(excel_path)
#     print("\n[✓] Excel update, IQR metrics, and embedded chart complete!")

#     # Terminal Output Metrics
#     agg_pnl_1m = sum(all_1m_pnls)
#     winning_trades_1m = sum(1 for p in all_1m_pnls if p > 0)
#     win_rate_1m = (winning_trades_1m / total_trades_count * 100) if total_trades_count > 0 else 0
#     profit_per_trade_1m = (agg_pnl_1m / total_trades_count) if total_trades_count > 0 else 0

#     print("\nCAPITAL-EFFICIENT OPTIMAL THRESHOLD (1-MINUTE EXECUTION SIMULATION): top_pct = 0.55 (55%)")
#     print(f"   • Aggregate Net PnL   : ${agg_pnl_1m:,.2f}")
#     print(f"   • Overall Win Rate    : {win_rate_1m:.1f}%")
#     print(f"   • Total Trades        : {total_trades_count}")
#     print(f"   • Profit / Trade      : ${profit_per_trade_1m:,.2f}")


# if __name__ == "__main__":
#     excel_file = os.path.join(
#         project_root, "data", "backtest_results", "sweep_analytics.xlsx"
#     )
#     process_excel_analytics(excel_file)

import os
import sys
import numpy as np
import pandas as pd
import openpyxl
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Font
from openpyxl.chart import BarChart, Reference

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def get_price_at_time(day_df, time_str):
    target_time = pd.to_datetime(time_str).time()
    close_col = next((c for c in day_df.columns if str(c).lower() == "close"), None)
    if not close_col:
        return None

    exact_match = day_df[day_df.index.time == target_time]
    if not exact_match.empty:
        return float(exact_match.iloc[0][close_col])
    
    later_trades = day_df[day_df.index.time >= target_time]
    if not later_trades.empty:
        return float(later_trades.iloc[0][close_col])
    return None


def load_cached_intraday_prices(ticker: str, open_date_str: str):
    open_date = pd.to_datetime(open_date_str).normalize()
    date_str = open_date.strftime("%Y-%m-%d")
    cache_file = os.path.join(project_root, "data", "intraday_cache", f"{ticker.upper()}_{date_str}.parquet")

    if not os.path.exists(cache_file):
        return None, None, None

    try:
        day_data = pd.read_parquet(cache_file)
    except Exception:
        return None, None, None

    p1 = get_price_at_time(day_data, "09:31")
    p5 = get_price_at_time(day_data, "09:35")
    p10 = get_price_at_time(day_data, "09:40")
    
    return p1, p5, p10


def analyze_winning_distribution(pnls):
    wins = sorted([p for p in pnls if p > 0])
    n_wins = len(wins)
    if n_wins == 0:
        return {
            "Total Wins": 0, "Q1 ($)": 0, "Q3 ($)": 0, "IQR ($)": 0,
            "Trades in IQR": 0, "Extreme Winners": 0
        }
    
    q25, q75 = np.percentile(wins, [25, 75])
    iqr = q75 - q25
    
    # Trades falling strictly inside the IQR (between Q1 and Q3)
    trades_in_iqr = sum(1 for p in wins if q25 <= p <= q75)
    
    # Extreme winners (Outliers above Q3 + 1.5 * IQR)
    upper_fence = q75 + (1.5 * iqr)
    extreme_winners = sum(1 for p in wins if p > upper_fence)
    
    return {
        "Total Wins": n_wins,
        "Q1 ($)": round(float(q25), 2),
        "Q3 ($)": round(float(q75), 2),
        "IQR ($)": round(float(iqr), 2),
        "Trades in IQR": trades_in_iqr,
        "Extreme Winners": extreme_winners
    }


def process_excel_analytics(excel_path: str):
    if not os.path.exists(excel_path):
        print(f"[!] File not found: {excel_path}")
        return

    print(f"[*] Processing analytics & winner distribution breakdown on: {excel_path}\n")
    
    xls = pd.ExcelFile(excel_path)
    exclude_sheets = {"Sweep Summary", "Trade Log"}
    ticker_sheets = [s for s in xls.sheet_names if s not in exclude_sheets]

    total_trades_count = 0
    all_1m_pnls = []
    stock_summary_stats = []

    with pd.ExcelWriter(excel_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        trade_log_df = pd.read_excel(excel_path, sheet_name="Trade Log")
        trade_log_df.to_excel(writer, sheet_name="Trade Log", index=False)

        for sheet in ticker_sheets:
            df = pd.read_excel(excel_path, sheet_name=sheet)
            
            prices_1m, prices_5m, prices_10m = [], [], []
            print(f"[*] Analyzing sheet: {sheet} ({len(df)} trades)...")
            
            for _, row in df.iterrows():
                ticker = row.get("ticker", sheet)
                open_date_str = row.get("open_date")
                
                p1, p5, p10 = load_cached_intraday_prices(ticker, open_date_str)
                prices_1m.append(p1)
                prices_5m.append(p5)
                prices_10m.append(p10)

            df["price_1m"] = prices_1m
            df["price_5m"] = prices_5m
            df["price_10m"] = prices_10m

            sheet_1m_pnls = []
            for _, row in df.iterrows():
                orig_pnl = row.get("pnl", 0)
                entry = row.get("entry_price")
                shares = row.get("shares", 0)
                p1 = row.get("price_1m")

                if pd.notna(p1) and pd.notna(entry) and pd.notna(shares) and entry > 0:
                    price_diff = p1 - entry
                    adjusted_pnl = orig_pnl - (price_diff * shares)
                else:
                    adjusted_pnl = orig_pnl

                sheet_1m_pnls.append(adjusted_pnl)
                all_1m_pnls.append(adjusted_pnl)
                total_trades_count += 1

            df["adjusted_pnl_1m"] = sheet_1m_pnls

            # Calculate Per-Stock Metrics & Winner Distribution
            n_trades = len(sheet_1m_pnls)
            wins = [p for p in sheet_1m_pnls if p > 0]
            win_rate = (len(wins) / n_trades * 100) if n_trades > 0 else 0
            agg_pnl = sum(sheet_1m_pnls)
            med_pnl = float(np.median(sheet_1m_pnls)) if n_trades > 0 else 0
            
            dist_stats = analyze_winning_distribution(sheet_1m_pnls)

            stock_summary_stats.append({
                "Ticker": sheet,
                "Trades": n_trades,
                "Win Rate (%)": round(win_rate, 1),
                "Aggregate Net PnL ($)": round(agg_pnl, 2),
                "Median PnL ($)": round(med_pnl, 2),
                "Winning Q1 ($)": dist_stats["Q1 ($)"],
                "Winning Q3 ($)": dist_stats["Q3 ($)"],
                "Winning IQR ($)": dist_stats["IQR ($)"],
                "Trades in IQR": dist_stats["Trades in IQR"],
                "Extreme Winners": dist_stats["Extreme Winners"]
            })

            df.to_excel(writer, sheet_name=sheet, index=False)

        # Write Summary Table to Sweep Summary Sheet
        summary_stats_df = pd.DataFrame(stock_summary_stats)
        base_summary_df = pd.read_excel(excel_path, sheet_name="Sweep Summary")
        
        base_summary_df.to_excel(writer, sheet_name="Sweep Summary", index=False, startrow=0)
        
        start_row_for_dist = len(base_summary_df) + 3
        summary_stats_df.to_excel(writer, sheet_name="Sweep Summary", index=False, startrow=start_row_for_dist)
        print(f"✅ Added per-stock winner IQR and distribution breakdown to 'Sweep Summary'.")

    # Apply Conditional Formatting & Charting via openpyxl
    wb = openpyxl.load_workbook(excel_path)
    blue_font = Font(color="0000FF", bold=True)
    red_font = Font(color="FF0000", bold=True)

    for sheet in ticker_sheets:
        ws = wb[sheet]
        header_row = [cell.value for cell in ws[1]]
        try:
            entry_col_idx = header_row.index("entry_price") + 1
            p1_idx = header_row.index("price_1m") + 1
            p5_idx = header_row.index("price_5m") + 1
            p10_idx = header_row.index("price_10m") + 1
        except ValueError:
            continue
        
        entry_col_letter = openpyxl.utils.get_column_letter(entry_col_idx)
        max_row = ws.max_row
        if max_row < 2:
            continue

        for col_idx in [p1_idx, p5_idx, p10_idx]:
            col_letter = openpyxl.utils.get_column_letter(col_idx)
            cell_range = f"{col_letter}2:{col_letter}{max_row}"
            
            ws.conditional_formatting.add(
                cell_range,
                CellIsRule(operator='lessThan', formula=[f"{entry_col_letter}2"], stopIfTrue=True, font=blue_font)
            )
            ws.conditional_formatting.add(
                cell_range,
                CellIsRule(operator='greaterThan', formula=[f"{entry_col_letter}2"], stopIfTrue=True, font=red_font)
            )

    # Embed Graphical Chart on Sweep Summary Sheet
    summary_ws = wb["Sweep Summary"]
    chart = BarChart()
    chart.type = "col"
    chart.style = 10
    chart.title = "Per-Stock 1-Minute Execution Net PnL"
    chart.y_axis.title = "Net PnL ($)"
    chart.x_axis.title = "Ticker"

    num_stocks = len(stock_summary_stats)
    data_min_row = start_row_for_dist + 1
    data_max_row = start_row_for_dist + num_stocks
    
    data = Reference(summary_ws, min_col=4, min_row=data_min_row, max_row=data_max_row)
    cats = Reference(summary_ws, min_col=1, min_row=data_min_row, max_row=data_max_row)
    
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.legend = None

    summary_ws.add_chart(chart, f"K{start_row_for_dist}")
    wb.save(excel_path)
    print("\n[✓] Excel update, IQR winner breakdown, and embedded chart complete!")

    # Calculate Overall Portfolio Winning Distribution
    overall_dist = analyze_winning_distribution(all_1m_pnls)
    agg_pnl_1m = sum(all_1m_pnls)
    winning_trades_1m = sum(1 for p in all_1m_pnls if p > 0)
    win_rate_1m = (winning_trades_1m / total_trades_count * 100) if total_trades_count > 0 else 0
    profit_per_trade_1m = (agg_pnl_1m / total_trades_count) if total_trades_count > 0 else 0

    print("\n==================================================")
    print("PORTFOLIO WINNING TRADE DISTRIBUTION (1-MIN EXECUTION)")
    print("==================================================")
    print(f" • Aggregate Net PnL   : ${agg_pnl_1m:,.2f}")
    print(f" • Overall Win Rate    : {win_rate_1m:.1f}% ({winning_trades_1m} / {total_trades_count} trades)")
    print(f" • Winning Trade Q1    : ${overall_dist['Q1 ($)']:,.2f}")
    print(f" • Winning Trade Q3    : ${overall_dist['Q3 ($)']:,.2f}")
    print(f" • Winning Trade IQR   : ${overall_dist['IQR ($)']:,.2f}")
    print(f" • Trades in IQR       : {overall_dist['Trades in IQR']} winning trades")
    print(f" • Extreme Winners     : {overall_dist['Extreme Winners']} winning trades (Outliers)")
    print("==================================================")


if __name__ == "__main__":
    excel_file = os.path.join(
        project_root, "data", "backtest_results", "sweep_analytics.xlsx"
    )
    process_excel_analytics(excel_file)