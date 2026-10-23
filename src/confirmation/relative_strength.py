import os
import pandas as pd
import numpy as np
from src.utils.config_loader import CONFIG

class BroadUniverseRSScanner:
    def __init__(self, benchmark="SPY", window=None, cache_dir=None):
        self.benchmark = benchmark
        self.window = window or CONFIG.get("parameters", {}).get("relative_strength_window", 63)
        self.cache_dir = cache_dir or "data/cache"
        
        # Pull universe dynamically from config.yaml if available, else fallback
        self.universe = CONFIG.get("universe", {}).get("tickers", [
            "NVDA", "AMD", "AVGO", "TSM", "MRVL", "QCOM", "INTC", "MU", "AMAT", "LRCX", "KLAC", "ARM",
            "MSFT", "AAPL", "GOOGL", "AMZN", "META", "TSLA", "NFLX", "PLTR", "CRM", "ADBE", "NOW", "SNOW", "UBER",
            "JPM", "BAC", "GS", "V", "MA"
        ])

    def fetch_cached_data(self):
        """Loads historical close prices from local Parquet cache instead of API calls."""
        tickers = self.universe + [self.benchmark]
        data_frames = {}
        
        for ticker in tickers:
            file_path = os.path.join(self.cache_dir, f"{ticker}.parquet")
            if os.path.exists(file_path):
                try:
                    df = pd.read_parquet(file_path)
                    if "Close" in df.columns:
                        data_frames[ticker] = df["Close"]
                except Exception as e:
                    print(f"[!] Error reading cache for {ticker}: {e}")
            else:
                print(f"[!] Warning: Cache file missing for {ticker}. Run cache initialization.")
                
        if not data_frames:
            raise FileNotFoundError("No cached data found. Please run your cache manager script first.")
            
        return pd.DataFrame(data_frames).dropna(how="all")

    def layer_2_broad_filter(self, df: pd.DataFrame = None, top_pct=0.05):
        """
        Layer 2 Gating: Isolates elite relative strength leaders 
        based on strict top percentage threshold using local storage.
        """
        if df is None:
            df = self.fetch_cached_data()
            
        if self.benchmark not in df.columns:
            raise ValueError(f"Benchmark '{self.benchmark}' data is missing from the dataset.")
            
        roc = df.pct_change(self.window).iloc[-1]
        benchmark_roc = roc[self.benchmark]
        
        excess_return = roc.drop(self.benchmark) - benchmark_roc
        ranked = excess_return.dropna().sort_values(ascending=False)
        
        # Apply strict top tier gate
        cutoff_index = max(1, int(len(ranked) * top_pct))
        leaders = ranked.iloc[:cutoff_index]
        
        return ranked, leaders

if __name__ == "__main__":
    scanner = BroadUniverseRSScanner()
    ranked_universe, top_leaders = scanner.layer_2_broad_filter()
    
    print("\n--- LAYER 2 RELATIVE STRENGTH RANKINGS ---")
    print(ranked_universe.head(10) * 100)
    print("\n--- ELITE LEADERS (Top 5%) ---")
    print(top_leaders * 100)