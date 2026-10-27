import os
import sys
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# Correct path for src/data/ (one level up to project root)
# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)

# Correct path for src/data/ (two levels up to project root)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.data.enums import Adjustment
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False


def fetch_and_cache_intraday_bars():
    excel_file = os.path.join(project_root, "data", "backtest_results", "sweep_analytics.xlsx")
    if not os.path.exists(excel_file):
        print(f"[!] Excel file not found: {excel_file}")
        return

    cache_dir = os.path.join(project_root, "data", "intraday_cache")
    os.makedirs(cache_dir, exist_ok=True)

    xls = pd.ExcelFile(excel_file)
    exclude_sheets = {"Sweep Summary", "Trade Log"}
    ticker_sheets = [s for s in xls.sheet_names if s not in exclude_sheets]

    api_key = os.environ.get("APCA_API_KEY_ID") or os.environ.get("ALPACA_API_KEY")
    api_secret = os.environ.get("APCA_API_SECRET_KEY") or os.environ.get("ALPACA_SECRET_KEY")
    client = StockHistoricalDataClient(api_key, api_secret) if (ALPACA_AVAILABLE and api_key and api_secret) else None

    for sheet in ticker_sheets:
        df = pd.read_excel(excel_file, sheet_name=sheet)
        print(f"[*] Processing intraday cache downloads for: {sheet} ({len(df)} trades)")

        for _, row in df.iterrows():
            ticker = row.get("ticker", sheet).upper()
            open_date_str = row.get("open_date")
            if pd.isna(open_date_str):
                continue

            open_date = pd.to_datetime(open_date_str).normalize()
            date_str = open_date.strftime("%Y-%m-%d")
            cache_file = os.path.join(cache_dir, f"{ticker}_{date_str}.parquet")

            if os.path.exists(cache_file):
                continue

            start_dt = open_date.tz_localize("America/New_York")
            end_dt = (open_date + pd.Timedelta(days=1)).replace(hour=10, minute=0).tz_localize("America/New_York")

            day_df = None
            if client:
                try:
                    request_params = StockBarsRequest(
                        symbol_or_symbols=[ticker],
                        timeframe=TimeFrame.Minute,
                        start=start_dt,
                        end=end_dt,
                        adjustment=Adjustment.SPLIT
                    )
                    bars = client.get_stock_bars(request_params)
                    day_df = bars.df
                    if not day_df.empty and ticker in day_df.index.get_level_values(0):
                        day_df = day_df.loc[ticker]
                except Exception as e:
                    print(f"[!] Alpaca fetch error for {ticker} on {date_str}: {e}")

            if day_df is None or day_df.empty:
                try:
                    import yfinance as yf
                    tk = yf.Ticker(ticker)
                    yf_df = tk.history(start=date_str, end=(open_date + pd.Timedelta(days=2)).strftime('%Y-%m-%d'), interval="1m")
                    if not yf_df.empty:
                        day_df = yf_df
                except Exception:
                    pass

            if day_df is not None and not day_df.empty:
                if day_df.index.tz is not None:
                    day_df.index = day_df.index.tz_convert("America/New_York")
                else:
                    day_df.index = pd.to_datetime(day_df.index).tz_localize("America/New_York", ambiguous='NaT', nonexistent='shift_forward')
                
                day_df.to_parquet(cache_file)
                print(f"[+] Cached intraday bars -> {ticker} ({date_str})")

    print("\n[✓] Intraday data fetching and local caching complete!")


if __name__ == "__main__":
    fetch_and_cache_intraday_bars()