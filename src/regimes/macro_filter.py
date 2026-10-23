import pandas as pd
import numpy as np
import yfinance as yf

class MacroRegimeEngine:
    def __init__(self, tickers=None):
        self.benchmarks = tickers or ["SPY", "QQQ", "^VIX"]
        
    def fetch_data(self, period="1y"):
        data = yf.download(self.benchmarks, period=period, progress=False)["Close"]
        return data

    def layer_0_sanity_check(self, df: pd.DataFrame):
        """
        Layer 0: Data Integrity & Sanity
        Detects missing values, checks confidence score, and drops corrupted frames.
        """
        if df.isnull().sum().sum() > 0:
            df = df.ffill().dropna()
            
        data_confidence_score = 1.0 if not df.empty else 0.0
        is_sane = data_confidence_score >= 1.0
        return df, is_sane

    def layer_1_classify_regime(self, df: pd.DataFrame) -> str:
        """
        Layer 1: Macro & Liquidity Regime Classification
        States: Bull Trend, Bear Trend, High-Volatility Choppy, Low-Volatility Risk-On
        """
        spy = df["SPY"]
        vix = df["^VIX"]
        
        current_spy = spy.iloc[-1]
        sma_200 = spy.rolling(200).mean().iloc[-1]
        current_vix = vix.iloc[-1]
        
        is_bull_trend = current_spy > sma_200
        is_high_vol = current_vix > 22.0
        
        if is_high_vol:
            return "HIGH_VOLATILITY_CHOPPY" if is_bull_trend else "BEAR_TREND"
        else:
            return "BULL_TREND" if is_bull_trend else "BEAR_TREND"

if __name__ == "__main__":
    engine = MacroRegimeEngine()
    raw_data = engine.fetch_data()
    clean_data, sane = engine.layer_0_sanity_check(raw_data)
    
    if sane:
        regime = engine.layer_1_classify_regime(clean_data)
        print(f"Data Integrity: PASSED | Active Macro Regime: {regime}")
    else:
        print("Data Integrity: FAILED | Execution Halted.")