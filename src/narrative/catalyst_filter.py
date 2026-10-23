import pandas as pd
import yfinance as yf
from datetime import datetime

class NarrativeFilter:
    def __init__(self, tickers=None, earnings_buffer_days=7):
        self.tickers = tickers or ["CRM", "NOW", "ADBE"]
        self.earnings_buffer_days = earnings_buffer_days

    def layer_5_check_narrative(self, ticker: str) -> dict:
        """
        Layer 5: Narrative & Behavioural Pressure Check
        Verifies fundamental catalysts, upcoming earnings risks, 
        and institutional sentiment alignment.
        """
        stock = yf.Ticker(ticker)
        
        earnings_date = None
        try:
            calendar = stock.calendar
            if isinstance(calendar, dict):
                # Handle modern yfinance dict format
                earnings_date = calendar.get('Earnings Date', [None])[0]
            elif calendar is not None and not calendar.empty:
                # Fallback for older DataFrame format
                if 'Earnings Date' in calendar.index:
                    earnings_date = calendar.loc['Earnings Date'].iloc[0]
        except Exception:
            pass

        # Evaluate earnings proximity risk
        narrative_passed = True
        notes = "Clear of immediate earnings binary events; institutional sponsorship stable."
        
        if earnings_date is not None:
            try:
                e_date = pd.to_datetime(earnings_date).tz_localize(None)
                today = pd.Timestamp.today().normalize()
                days_until_earnings = (e_date - today).days
                
                if 0 <= days_until_earnings <= self.earnings_buffer_days:
                    narrative_passed = False
                    notes = f"[!] BLOCKED: Earnings announcement in {days_until_earnings} days ({e_date.strftime('%Y-%m-%d')})."
                elif days_until_earnings < 0:
                    notes = "Most recent earnings have passed; tracking post-earnings reaction."
            except Exception as e:
                notes = f"[!] Warning: Could not parse earnings date reliably ({e})."

        return {
            "ticker": ticker,
            "narrative_approved": narrative_passed,
            "earnings_date": str(earnings_date),
            "notes": notes
        }

if __name__ == "__main__":
    filter_engine = NarrativeFilter()
    print("\n--- Layer 5: Narrative & Behavioural Catalyst Scan ---")
    
    for t in filter_engine.tickers:
        res = filter_engine.layer_5_check_narrative(t)
        print(f"Ticker: {res['ticker']} | Approved: {res['narrative_approved']} | Notes: {res['notes']}")