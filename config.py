"""
Configuration settings for SMA evaluation.
Modify these values to change the evaluation parameters.
"""

import logging
import re

# ---------------------------------------------------------------------------
# Logging defaults
# ---------------------------------------------------------------------------
# Logging levels for the application and library noise.
# Use INFO by default to keep regular output readable.
# Use DEBUG only when you want verbose internal tracing.
APP_LOG_LEVEL = "INFO"
PACKAGE_LOG_LEVELS = {
    "yfinance": "WARNING",
    "urllib3": "WARNING",
    "pandas": "WARNING",
    "numpy": "WARNING",
}

# ---------------------------------------------------------------------------
# Strategy and evaluation configuration
# ---------------------------------------------------------------------------
# These values are imported by the evaluator. Changing them changes the next
# evaluation; existing output folders keep their own state files.
SMA_MIN = 1           # Smallest SMA window (days)
SMA_MAX = 200         # Largest SMA window (days)
SMA_STEP = 1          # Step size between SMA windows (e.g., 1 = every day, 10 = every 10 days)

# Evaluation Configuration
EVAL_DAYS = 60        # Number of trading days to simulate (max 60 for 2m, min 2m for daily)
EVAL_INTRADAY_INTERVAL = "2m"  # Intraday data interval for simulation

# ---------------------------------------------------------------------------
# Trading configuration
# ---------------------------------------------------------------------------
BUY_THRESHOLD = .5 # Price must be this much above SMA to buy
SELL_THRESHOLD = .5 # Price must be this much below SMA to sell
TRADING_FEE = 0.1    # Fee per trade
DOWNTIME_DAYS = 4     # Days to wait after selling before buying again

# Trading mode: 'momentum' (buy when price > SMA, sell when price < SMA)
# or 'mean_reversion' (buy when price < SMA, sell when price > SMA)
# Set to 'mean_reversion' to buy low / sell high behavior.
TRADE_MODE = 'mean_reversion'

# ---------------------------------------------------------------------------
# How often detailed progress is written
# ---------------------------------------------------------------------------
LOG_PRICE_INTERVAL = 100  # Log price values every N ticks (0 = log all, set high to disable)
LOG_INDEX_INTERVAL = 100  # Log DayIndex/PriceIndex/MaxIndex every N ticks (0 = log all, set high to disable)
EVALLOG_INTERVAL = 100    # Write to EvaluationLog.txt every N ticks (0 = log all, set high to disable)

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def validate_configuration():
    """Check settings before any network request or file is changed."""
    if SMA_MIN < 1 or SMA_MAX < SMA_MIN or SMA_STEP < 1:
        raise ValueError("SMA_MIN, SMA_MAX, and SMA_STEP must define a positive range")
    if EVAL_DAYS < 1:
        raise ValueError("EVAL_DAYS must be positive")
    if BUY_THRESHOLD < 0 or SELL_THRESHOLD < 0 or TRADING_FEE < 0 or DOWNTIME_DAYS < 0:
        raise ValueError("Trading thresholds, fees, and downtime must not be negative")
    if TRADE_MODE not in {"momentum", "mean_reversion"}:
        raise ValueError("TRADE_MODE must be 'momentum' or 'mean_reversion'")
    if APP_LOG_LEVEL.upper() not in LOG_LEVELS:
        raise ValueError(f"Unsupported APP_LOG_LEVEL: {APP_LOG_LEVEL}")
    for package_name, level in PACKAGE_LOG_LEVELS.items():
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", package_name):
            raise ValueError(f"Invalid package logger name: {package_name}")
        if level.upper() not in LOG_LEVELS:
            raise ValueError(f"Unsupported log level for {package_name}: {level}")

