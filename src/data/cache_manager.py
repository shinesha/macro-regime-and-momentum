import os
import pandas as pd
import yfinance as yf

from src.utils.config_loader import CONFIG


NY_TZ_NAME = "America/New_York"


# ============================================================
# GENERAL CLEANING
# ============================================================

def _clean_yf_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Flatten yfinance MultiIndex columns and return a clean dataframe.
    """
    if df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        if "Close" in df.columns.get_level_values(0):
            df = df.xs(
                df.columns.get_level_values(1)[0],
                axis=1,
                level=1
            )
        else:
            df.columns = df.columns.get_level_values(0)

    return df


def _normalise_daily_index(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert dataframe index to naïve New York calendar dates.

    We deliberately use the timezone string rather than ZoneInfo
    objects in pandas/yfinance operations.
    """
    if df.empty:
        return df

    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    if df.index.tz is not None:
        df.index = (
            df.index
            .tz_convert(NY_TZ_NAME)
            .tz_localize(None)
        )

    df.index = df.index.normalize()

    df = df[
        ~df.index.duplicated(keep="last")
    ]

    return df.sort_index()


# ============================================================
# PROCESS ONE TICKER
# ============================================================

def process_350_update(
    ticker: str,
    cache_dir: str
):
    """
    Update one ticker's cache with strictly COMPLETED daily bars.

    CACHE LOGIC
    -----------
    1. Determine current New York calendar date and session status.
    2. Download official daily history.
    3. Filter out any live/forming candle for 'today' if run during 
       regular trading hours (before 4:00 PM ET).
    4. Save only finalized, completed market close candles to Parquet.
    """

    safe_t = ticker.replace("^", "")
    path = os.path.join(cache_dir, f"{safe_t}.parquet")

    # --------------------------------------------------------
    # CURRENT NEW YORK DATE/TIME & MARKET CLOSE EVALUATION
    # --------------------------------------------------------

    try:
        now_ny = pd.Timestamp.now(tz=NY_TZ_NAME)
    except Exception as e:
        print(
            f"[!] Failed determining NY time "
            f"for {ticker}: {e}"
        )
        return

    today_ny = now_ny.normalize()
    today_date = today_ny.date()
    naive_today = pd.Timestamp(today_date)
    today_str = today_date.strftime("%Y-%m-%d")

    # Regular Trading Hours close at 16:00:00 NY time
    market_close_time = pd.to_datetime("16:00:00").time()
    is_post_market = now_ny.time() >= market_close_time

    print(f"\n--- {ticker} ---")
    print(f"[*] NY date: {today_str}")
    print(f"[*] NY time: {now_ny.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # --------------------------------------------------------
    # FETCH OFFICIAL DAILY DATA
    # --------------------------------------------------------

    print(
        f"[*] Fetching daily history "
        f"for {ticker}..."
    )

    existing_df = pd.DataFrame()

    try:
        official_history = yf.download(
            ticker,
            period="3y",
            interval="1d",
            progress=False,
            auto_adjust=False
        )

        if not official_history.empty:
            official_history = _clean_yf_dataframe(official_history)
            existing_df = _normalise_daily_index(official_history)

    except Exception as e:
        print(
            f"[!] Official daily refresh failed "
            f"for {ticker}: {e}"
        )

    # --------------------------------------------------------
    # STRICT COMPLETED CANDLE ENFORCEMENT
    # --------------------------------------------------------

    if not existing_df.empty:
        # If run BEFORE 4:00 PM ET on a weekday, drop today's active/live bar.
        # If run AFTER 4:00 PM ET (or on a weekend), today's bar is finalized.
        if not is_post_market:
            existing_df = existing_df[existing_df.index < naive_today]
            print(
                f"[*] Live session in progress — excluded forming bar "
                f"for {today_str}."
            )
        else:
            print(
                f"[*] Post-market hours — including finalized bar "
                f"for {today_str} if available."
            )

    # --------------------------------------------------------
    # CLEAN & SAVE CACHE
    # --------------------------------------------------------

    if not existing_df.empty:
        existing_df = existing_df[
            ~existing_df.index.duplicated(keep="last")
        ]
        existing_df = existing_df.sort_index()

        existing_df.to_parquet(path)

        latest_date = existing_df.index[-1]
        latest_close = float(existing_df.iloc[-1]["Close"])
        latest_volume = float(existing_df.iloc[-1]["Volume"])

        print(
            f"[+] MOST RECENT COMPLETED CLOSE: "
            f"{latest_date.strftime('%Y-%m-%d')}"
        )
        print(f"[+] LATEST CLOSE:  ${latest_close:.2f}")
        print(f"[+] LATEST VOLUME: {latest_volume:,.0f}")
        print(f"[+] Total cached rows saved: {len(existing_df)}")
    else:
        print(
            f"[!] WARNING: Unable to fetch or save completed daily data "
            f"for {ticker}"
        )


# ============================================================
# RUN ALL ASSETS
# ============================================================

def run_cache_update():

    project_root = os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        )
    )

    cache_dir = os.path.join(
        project_root,
        "data",
        "cache"
    )

    os.makedirs(
        cache_dir,
        exist_ok=True
    )

    universe_cfg = CONFIG.get("universe", {})
    tickers = universe_cfg.get("tickers", [])
    benchmarks = universe_cfg.get("benchmarks", ["SPY"])

    # Preserve config order and remove duplicates.
    all_assets = list(
        dict.fromkeys(tickers + benchmarks)
    )

    print(
        "--- Starting Completed Daily Close Cache Update Run for "
        f"{len(all_assets)} Assets ---"
    )

    successful = 0
    failed = 0

    for ticker in all_assets:
        try:
            process_350_update(ticker, cache_dir)
            successful += 1
        except Exception as e:
            failed += 1
            print(
                f"[!] Failed processing "
                f"{ticker}: {e}"
            )

    print("\n========================================")
    print("CACHE UPDATE COMPLETE")
    print("========================================")
    print(f"Successful: {successful}")
    print(f"Failed:     {failed}")
    print(f"Total:      {len(all_assets)}")
    print("========================================")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    run_cache_update()