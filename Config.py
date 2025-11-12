"""
Configuration settings for SMA evaluation.
Modify these values to change the evaluation parameters.
"""

# SMA Configuration
SMA_MIN = 1           # Smallest SMA window (days)
SMA_MAX = 200         # Largest SMA window (days)
SMA_STEP = 1          # Step size between SMA windows (e.g., 1 = every day, 10 = every 10 days)

# Evaluation Configuration
EVAL_DAYS = 60        # Number of trading days to simulate (max 60 for 2m, min 2m for daily)
EVAL_INTRADAY_INTERVAL = "2m"  # Intraday data interval for simulation

# Trading Configuration
BUY_THRESHOLD = 1  # Price must be this much above SMA to buy
SELL_THRESHOLD = 1 # Price must be this much below SMA to sell
TRADING_FEE = 0.1    # Fee per trade
DOWNTIME_DAYS = 2     # Days to wait after selling before buying again

# Trading mode: 'momentum' (buy when price > SMA, sell when price < SMA)
# or 'mean_reversion' (buy when price < SMA, sell when price > SMA)
# Set to 'mean_reversion' to buy low / sell high behavior.
TRADE_MODE = 'mean_reversion'

# Logging Configuration
LOG_PRICE_INTERVAL = 100  # Log price values every N ticks (0 = log all, set high to disable)
LOG_INDEX_INTERVAL = 100  # Log DayIndex/PriceIndex/MaxIndex every N ticks (0 = log all, set high to disable)
EVALLOG_INTERVAL = 100    # Write to EvaluationLog.txt every N ticks (0 = log all, set high to disable)
