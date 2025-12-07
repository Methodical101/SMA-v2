# SMA-v2: Simple Moving Average Trading Strategy Evaluator

A Python-based backtesting system for evaluating multiple SMA (Simple Moving Average) trading strategies simultaneously across historical stock data.

## Overview

This tool allows you to simulate and evaluate up to 200 different SMA trading strategies in parallel to find optimal moving average windows for a given stock. It uses real historical intraday data from Yahoo Finance to test buy/sell signals based on price crossovers with various SMA periods.

## Features

- **Multi-Strategy Evaluation**: Test 200 SMA strategies simultaneously (configurable via `SMA_MIN`, `SMA_MAX`, `SMA_STEP`)
- **Flexible Time Intervals**: Support for multiple intraday intervals (1m, 2m, 5m, 15m, 30m, 60m, etc.)
- **Two Trading Modes**:
  - **Momentum**: Buy when price > SMA, sell when price < SMA
  - **Mean Reversion**: Buy when price < SMA, sell when price > SMA
- **Configurable Parameters**: Easy-to-modify thresholds, fees, and trading rules via `Config.py`
- **Resume Capability**: Pause and resume evaluations
- **Detailed Logging**: Debug logs and evaluation timelines for analysis
- **Clean State Management**: File-based state tracking with automatic cleanup

## Installation

### Prerequisites
- Python 3.7+
- pip

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd SMA-v2
```

2. Run the setup script:
```bash
./setup.sh
```

Or for a fresh installation:
```bash
./setup.sh --fresh
```

3. Activate the virtual environment:
```bash
source .venv/bin/activate
```

## Usage

### Starting a New Evaluation

Evaluate a stock symbol (e.g., AAPL) with default settings:
```bash
python Main.py --new --eval --stock AAPL
```

### Resuming an Evaluation

Resume a previously started evaluation (now requires the stock symbol):
```bash
python Main.py --resume --eval --stock TSLA
```

### Cleaning Up Logs

Delete all logs for a specific stock:
```bash
python Main.py --clean --stock AAPL
```

## Configuration

All trading parameters are centralized in `Config.py`:

### SMA Configuration
```python
SMA_MIN = 1           # Smallest SMA window (days)
SMA_MAX = 200         # Largest SMA window (days)
SMA_STEP = 1          # Increment between windows (1 = test every day)
```

### Evaluation Settings
```python
EVAL_DAYS = 60                    # Number of trading days to simulate
EVAL_INTRADAY_INTERVAL = "2m"     # Data interval (1m, 2m, 5m, 15m, etc.)
```

### Trading Rules
```python
BUY_THRESHOLD = 1.00   # Price must be this much above/below SMA to trigger
SELL_THRESHOLD = 1.00  # Price must cross SMA by this amount to sell
TRADING_FEE = 0.1      # Transaction fee per trade
DOWNTIME_DAYS = 2      # Cooldown period after selling before buying again
TRADE_MODE = 'mean_reversion'  # 'momentum' or 'mean_reversion'
```

### Logging Configuration
```python
LOG_PRICE_INTERVAL = 100    # Log price every N ticks to debug.log
LOG_INDEX_INTERVAL = 100    # Log index info every N ticks to debug.log
EVALLOG_INTERVAL = 100      # Write to EvaluationLog.txt every N ticks
```

## Output files and layout

When you start a new evaluation the tool creates a per-stock folder named after the symbol and places most state and output files there. The project root keeps `Debug.log` so all debug records are consolidated in one place.

- `./<STOCK>/<STOCK>_EvaluationLog.txt`: Detailed timeline of all buy/sell and forced-liquidation actions
- `./<STOCK>/<STOCK>_Totals.txt`: Daily profit totals for each SMA strategy
- `./<STOCK>/Stock.txt`: Per-stock pointer and local state files (DayIndex.txt, PriceIndex.txt, SMA.txt, Price.txt)
- `Debug.log` (root): Detailed debug information (rotated/cleared per run by `Main.py`)
- `StockData.csv` (per-stock folder): Cached intraday price data used for simulation

Note: `--clean` will remove artifacts from the per-stock folder (and legacy root-level files if present).

## Analyzer examples and CSV truncation

The built-in analyzer (`tools/Analyze.py`) inspects the evaluation log and summarizes realized sells per SMA. Here are common usages and notes about CSV output truncation when using `--top`:

- Analyze a specific log file and write a full CSV:
```bash
python3 tools/Analyze.py --log-file EH/EH_EvaluationLog.txt --csv EH/EH_Analysis_full.csv --compare-totals --totals-file EH/EH_Totals.txt
```

- Analyze from inside a per-stock folder (mirrors how `Main.py` invokes it):
```bash
cd TSLA
python3 ../tools/Analyze.py --stock TSLA --csv TSLA_Analysis.csv --compare-totals
```

- Quick summary only (no CSV):
```bash
python3 tools/Analyze.py --log-file EH/EH_EvaluationLog.txt --top 3
```

CSV truncation behavior:
- When you pass `--top N` together with `--csv PATH`, the analyzer will write a truncated CSV that contains only the printed Top N worst SMAs followed by the Top N best SMAs (duplicates removed). This keeps the CSV focused on the most relevant strategies when you only want a short list.
- If you want the full per-SMA table, omit `--top` and provide only `--csv PATH` to write the complete results.

If you'd prefer a different truncation behaviour (for example "Top N overall" rather than worst+best, or preserving the printed order in the CSV), tell me and I can add a flag to control that.

## How It Works

1. **Data Collection**: Downloads historical intraday data for the specified evaluation period using yfinance
2. **SMA Calculation**: Computes daily SMAs for all configured window sizes (e.g., 1-day through 200-day)
3. **Simulation**: Iterates through each trading day tick-by-tick:
   - Checks each SMA bot's buy/sell conditions
   - Executes trades based on price crossovers
   - Tracks profit/loss for each strategy
   - Applies trading fees and downtime penalties
4. **Reporting**: Generates daily totals and evaluation logs showing performance of each SMA period

The analyzer (`tools/Analyze.py`) now also recognizes forced-liquidation log entries (marked by `FORCE-LIQUIDATED`) and includes those final forced closes in the per-SMA aggregates.

## Trading Logic

### Momentum Mode
- **Buy Signal**: Price crosses above (SMA + BUY_THRESHOLD)
- **Sell Signal**: Price crosses below (SMA - SELL_THRESHOLD)

### Mean Reversion Mode
- **Buy Signal**: Price crosses below (SMA - BUY_THRESHOLD)
- **Sell Signal**: Price crosses above (SMA + SELL_THRESHOLD)

After each sale, the bot enters a cooldown period (`DOWNTIME_DAYS`) before it can trade again.

## Example Workflow

```bash
# 1. Configure your parameters in Config.py
# Edit SMA_MIN, SMA_MAX, EVAL_DAYS, etc.

# 2. Start a new evaluation
python Main.py --new --eval --stock TSLA

# 3. Monitor progress in the console
# maxIndex: 6238, priceIndex: 123
# Day 1
# Day 2
# ...

# 4. Review results (files are inside the per-stock folder)
cat TSLA/TSLA_Totals.txt        # See final profits for each SMA
cat TSLA/TSLA_EvaluationLog.txt # See detailed trade history (includes FORCE-LIQUIDATED lines)
cat Debug.log                    # See technical/debug details (root)
```

## Project Structure

```
SMA-v2/
├── Config.py              # Configuration settings
├── Main.py                # CLI entry point
├── requirements.txt       # Python dependencies
├── setup.sh              # Setup script
├── data/
│   ├── LogManager.py     # File-based logging
│   └── StockUpdater.py   # Data fetching and SMA calculation
├── evaluate/
│   ├── Evaluator.py      # Evaluation orchestrator
│   └── SMA.py            # Individual SMA bot logic
└── run/                  # (Future: live trading mode)
```

## Dependencies

- **yfinance**: Stock data retrieval
- **pandas**: Data manipulation
- **numpy**: Numerical operations

## Limitations

- Intraday data availability depends on yfinance/Yahoo Finance limits:
  - `1m`, `2m`, `5m`: Last 60 days only
  - `15m`, `30m`, `60m`: Last 60 days
  - Daily and higher: Years of historical data
- Does not account for market hours, holidays, or after-hours trading (yfinance handles this automatically)
- Assumes immediate order execution at displayed prices

## Future Enhancements

- Live trading mode (`--run` flag, currently unimplemented)
- Support for additional technical indicators
- Multi-stock batch evaluation
- Advanced position sizing strategies
- Performance visualization and reporting

## License

TBD

## Contributing

TBD

## Support

For issues or questions, please open a Github issue.
