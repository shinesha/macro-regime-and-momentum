WORKFLOW
A/ run data.cache_manager, backtest.engine, run backtest.analyze_results -> outputs optimal relative strength parameter
B/ input optimal relative strength parameter to and run setups.demand_zones after US market close each day to decide what to buy at U.S. open the following day.
[Make sure you run data.cache_manager everyday before setups.demand_zones so you have latest data.] 
[I look at the win loss of the indvidual stock at that relative strength parameter before doing the trade.]  

EXPLANATION OF RELEVANT SCRIPTS
1/Activate VM
.  venv  Scripts  Activate.ps1    
2/ Update Data 
python -m src.data.cache_manager 

3/ Get setups after US close each day. 
python -m src.setups.demand_zones  
Set PCT_PARAM to same value as optimal releative strength value found by the backtest engine and backtest analytics.

4/ Run backtest
python -m src.backtest.engine   - test values of relative strength to find the optimal for the trading period. 
You have to manually choose optimal_pct variable for it to display equity curve for each individual asset using that relative strength value.  - Outputs equity curve regards a user chosen rs value. 

 CAPITAL-EFFICIENT OPTIMAL THRESHOLD: top_pct = 0.55 (55%)
   • Aggregate Net PnL   : $100,959.14
   • Overall Win Rate    : 49.2%
   • Total Trades        : 193
   • Avg Trades / Month  : 5.85

   NOTE: it only wins 49.2% of the time but when it wins, it wins 3x what it loses. 

5/ Analyse the backtest results spreadsheet
python -m src.backtest.analyze_results - - outputs the optimal relative strength parameter. Displays a graph showing this. 


6/ SLIPPAGE DATA
Run fetch_intraday_data.py - downloads the 1m, 5m, and 10m price on the date of entry for the trades in the backtest.
Previous, backtest assumes we can enter at the reported open.
This data tells us what prices the stock trade at. 

7/ SLIPPAGE ANALYSIS
Updates the Excel Workbook: Injects these intraday price columns into each individual ticker tab within sweep_analytics.xlsx.

Applies Conditional Formatting: Automatically color-codes the intraday price cells. (blue font if the intraday price is below your entry price, red font if it is above).

Simulates 1-Minute Execution PnL: Dynamically recalculates trade PnLs, overall win rates, and profit per trade based on the actual 1-minute execution price (price_1m) instead of the theoretical daily open, effectively stress-testing the strategy against opening slippage.

Outputs Terminal Metrics: Prints the audited performance metrics block directly to your terminal.

Outputs Sweep Summary table regards on the sweep summary table of excel.

