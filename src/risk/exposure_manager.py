import numpy as np

class RiskExposureManager:
    def __init__(self, account_size: float = 100000.0, max_risk_pct: float = 0.01):
        self.account_size = account_size
        self.max_risk_pct = max_risk_pct

    
    def calculate_position(self, ticker: str, entry_price: float, stop_loss_price: float, regime_state: str = "BULL_TREND") -> dict:
        risk_per_share = abs(entry_price - stop_loss_price)
        
        if risk_per_share <= 0 or entry_price <= 0:
            return {
                "ticker": ticker,
                "shares": 0,
                "position_value": 0.0,
                "risk_amount": 0.0,
                "risk_per_share": 0.0,
                "regime_multiplier": 1.0
            }

        regime_multipliers = {
            "BULL_TREND": 1.0,
            "NEUTRAL": 0.5,
            "BEAR_TREND": 0.0
        }
        regime_mult = regime_multipliers.get(regime_state, 1.0)
        
        # FIXED $1,000 BASE RISK (MULTIPLIED BY REGIME STATE)
        risk_amount = 1000.0 * regime_mult
        
        shares = int(risk_amount / risk_per_share)
        position_value = round(shares * entry_price, 2)
        actual_risk_dollars = round(shares * risk_per_share, 2)

        return {
            "ticker": ticker,
            "shares": shares,
            "position_value": position_value,
            "risk_amount": actual_risk_dollars,
            "risk_per_share": round(risk_per_share, 2),
            "regime_multiplier": regime_mult
        }

if __name__ == "__main__":
    rm = RiskExposureManager(account_size=100000.0, max_risk_pct=0.01)
    # Example execution matching updated demand_zones.py setup output
    sample_setup = {
        "ticker": "NVDA",
        "current_price": 125.50,
        "stop_loss": 121.25,
        "target_price": 134.00,
        "risk_per_share": 4.25
    }
    
    pos = rm.calculate_position(
        ticker=sample_setup["ticker"],
        entry_price=sample_setup["current_price"],
        stop_loss_price=sample_setup["stop_loss"],
        regime_state="BULL_TREND"
    )
    
    print(f"Position Calculation for {pos['ticker']}:")
    print(f" - Shares:         {pos['shares']}")
    print(f" - Total Value:    ${pos['position_value']:,.2f}")
    print(f" - Capital at Risk: ${pos['risk_amount']:,.2f}")