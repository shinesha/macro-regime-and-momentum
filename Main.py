import sys
import os
import pandas as pd
import yfinance as yf

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from regimes.macro_filter import MacroRegimeEngine
from confirmation.relative_strength import BroadUniverseRSScanner
from setups.demand_zones import SetupScanner
from risk.exposure_manager import RiskExposureManager
from narrative.catalyst_filter import NarrativeFilter

def run_pipeline():
    print("==================================================")
    print("   INSTITUTIONAL EQUITY PIPELINE: EXECUTION START ")
    print("==================================================\n")

    # --- LAYER 1: MACRO REGIME CHECK ---
    print("[*] Executing Layer 1: Macro Regime Classification...")
    macro_engine = MacroRegimeEngine()
    raw_macro_data = macro_engine.fetch_data()
    clean_macro_data, sane = macro_engine.layer_0_sanity_check(raw_macro_data)
    
    if not sane:
        print("[!] Layer 0/1 Data Integrity FAILED. Halting Pipeline Execution.")
        return
        
    active_regime = macro_engine.layer_1_classify_regime(clean_macro_data)
    print(f"    -> Macro Regime Status: {active_regime}")
    
    if active_regime == "BEAR_TREND":
        print("[!] Bear Regime Detected. Long exposure authorization denied. Exiting.")
        return

    # --- LAYER 2: STRICT RELATIVE STRENGTH GATING ---
    print("\n[*] Executing Layer 2: Strict Relative Strength Gating (Top 5%)...")
    rs_scanner = BroadUniverseRSScanner()
    raw_universe_data = rs_scanner.fetch_bulk_data()
    
    # Enforce strict top 5% gate
    all_ranks, top_leaders = rs_scanner.layer_2_broad_filter(raw_universe_data, top_pct=0.05)
    leader_tickers = top_leaders.index.tolist()
    print(f"    -> Elite Gated Leaders Identified: {leader_tickers}")

    # --- LAYER 3: DEMAND ZONE & PULLBACK SCANNING ---
    print("\n[*] Executing Layer 3: Institutional Demand Zone Setup Detection...")
    setup_scanner = SetupScanner(tickers=leader_tickers)
    active_setups = []
    
    for t in leader_tickers:
        data = setup_scanner.fetch_historical_data(t)
        if not data.empty:
            res = setup_scanner.layer_3_detect_demand_zones(data, t)
            print(f"    -> Ticker: {res['ticker']} | Price: ${res['current_price']:.2f} | Setup Active: {res['setup_active']}")
            if res['setup_active']:
                active_setups.append(res)

    if not active_setups:
        print("\n[!] No elite gated assets currently meeting structural demand zone criteria. Pipeline complete.")
        return

    # --- LAYER 4 & 5: RISK SIZING & NARRATIVE VALIDATION ---
    print("\n[*] Executing Layer 4 & 5: Risk Sizing & Narrative Catalyst Verification...")
    risk_manager = RiskExposureManager(account_size=100000.0, max_risk_pct=0.01)
    narrative_filter = NarrativeFilter(tickers=[s['ticker'] for s in active_setups])
    
    print("\n==================================================")
    print("          FINAL ACTIONABLE TRADE SIGNALS          ")
    print("==================================================")

    for setup in active_setups:
        t = setup['ticker']
        current_price = setup['current_price']
        zone_low = setup['demand_zone_range'][0]
        
        stop_loss = round(zone_low * 0.99, 2)
        narrative_res = narrative_filter.layer_5_check_narrative(t)
        
        if not narrative_res['narrative_approved']:
            print(f"[-] {t}: Rejected by Layer 5 Narrative Filter ({narrative_res['notes']})")
            continue
            
        risk_res = risk_manager.calculate_position(
            ticker=t,
            entry_price=current_price,
            stop_loss_price=stop_loss,
            regime_state=active_regime
        )
        
        if risk_res['shares'] > 0:
            print(f" [V] SIGNAL APPROVED: {t}")
            print(f"     * Entry Price: ${current_price:.2f}")
            print(f"     * Stop-Loss:   ${stop_loss:.2f}")
            print(f"     * Allocation:  {risk_res['shares']} shares (${risk_res['position_value']:,.2f})")
            print(f"     * Risk Capital: ${risk_res['risk_amount']:,.2f} (1.0% limit)")
            print(f"     * Notes:       {narrative_res['notes']}")
            print("-" * 50)

    print("\n[=] Pipeline Execution Completed Successfully.")

if __name__ == "__main__":
    run_pipeline()