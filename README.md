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
python -m src.backtest.engine   - test values of releative strength to find the optimal for the trading period. 
You have to manually choose optimal_pct variable for it to display equity curve for each indidviaul asset using that releative strength value.  - Outputs equity curve regards a user chosen rs value. 

 CAPITAL-EFFICIENT OPTIMAL THRESHOLD: top_pct = 0.55 (55%)
   • Aggregate Net PnL   : $100,959.14
   • Overall Win Rate    : 49.2%
   • Total Trades        : 193
   • Avg Trades / Month  : 5.85

   NOTE: it only wins 49.2% of the time but when it wins, it wins 3x what it loses. 

5/ Analyse the backtest results spreadsheet
python -m src.backtest.analyze_results - - outputs the optimal relative strength parameter. Displays a graph showing this. 
