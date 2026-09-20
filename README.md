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
- **Configurable Parameters**: Easy-to-modify thresholds, fees, and trading rules via `config.py`
- **Resume Capability**: Automatically pause and resume evaluations
- **Detailed Logging**: App-level and per-package logging controls for debugging without overwhelming output
- **Clean State Management**: File-based state tracking with automatic cleanup
- **Analyzer Support**: Automatic structured-event analysis, CSV exports, and discrepancy checks against totals files

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
python main.py --eval --stock AAPL
```

If the stock directory does not exist, this starts a new evaluation. If the
directory already contains that stock's `Stock.txt` file, the evaluator
automatically resumes the existing session.

There are no separate `--new` or `--resume` flags. This avoids accidentally
resetting a session or selecting the wrong resume mode.

To explicitly delete a session and start over on the next run:

```bash
python main.py --clean --stock AAPL
```

### Evaluating 20 Large S&P 500 Stocks

The repository includes a sequential batch script with a manually maintained
list of 20 large S&P 500 companies:

```bash
chmod +x run_top_20_snp500.sh
./run_top_20_snp500.sh
```

Each stock gets its own directory and is analyzed after its evaluation. The
script automatically starts new sessions for missing stock folders and
resumes existing stock folders. It continues to the next stock if one
evaluation fails, then exits with a failure status and prints the failed
symbols.

The list is not fetched dynamically from the index. Market-cap rankings
change, so update the `STOCKS` list in `run_top_20_snp500.sh` when a different
ranking date or stock universe is required.

### Live Runner

Runner mode watches one stock continuously and prints a notification when the
current price reaches a buy or sell condition for the selected SMA window. It
uses the configured `TRADE_MODE`, `BUY_THRESHOLD`, and `SELL_THRESHOLD`
values. It does not place orders.

Start a runner for a 20-day SMA:

```bash
python main.py --run --stock AAPL --sma 20
```

Other examples:

```bash
# Watch Microsoft using a 50-day SMA
python main.py --run --stock MSFT --sma 50

# Check Tesla every 30 seconds using a 10-day SMA
python main.py --run --stock TSLA --sma 10 --poll-seconds 30

# Use detailed application logging while watching Nvidia
python main.py --run --stock NVDA --sma 20 --log-level DEBUG
```

The default runner checks Yahoo Finance every 60 seconds. Override the
polling delay when needed:

```bash
python main.py --run --stock AAPL --sma 20 --poll-seconds 30
```

The command stays active and checks repeatedly. Press `Ctrl+C` once to stop
the runner cleanly. A notification is printed only when the simulated
position changes:

```text
2026-09-20 10:15:00 | AAPL | BUY | price=182.4200 | SMA(20)=184.0100
2026-09-20 11:02:00 | AAPL | SELL | price=185.1100 | SMA(20)=184.2200
```

`BUY` and `SELL` are notifications, not real orders. The runner remembers its
simulated position only while that process is running. Starting it again
starts with no open simulated position. The runner uses daily closing prices
to calculate the selected SMA and the latest configured intraday interval for
the current price.

Runner notifications are also appended to
`output/AAPL/AAPL_RunnerLog.txt`. Stop the runner with `Ctrl+C`. The runner
requires `--sma` and only produces notifications; it never executes trades or
submits broker orders.

### Logging Levels

The app supports separate log levels for the project itself and for third-party libraries.

```bash
# Set application log level only
python main.py --eval --stock AAPL --log-level DEBUG

# Set all package loggers to a single override level
python main.py --eval --stock AAPL --log-level INFO --log-level-packages WARNING

# Override individual packages; repeat the option as needed
python main.py --eval --stock AAPL --log-level DEBUG \
  --log-level-package yfinance=INFO \
  --log-level-package pandas=WARNING

# Use package defaults but increase app verbosity
python main.py --eval --stock AAPL --log-level DEBUG
```

Defaults live in `config.py`:
```python
APP_LOG_LEVEL = "INFO"
PACKAGE_LOG_LEVELS = {
    "yfinance": "WARNING",
    "urllib3": "WARNING",
    "pandas": "WARNING",
    "numpy": "WARNING",
}
```

`--log-level` controls application logging. `--log-level-packages` applies one level to every configured package. The repeatable `--log-level-package NAME=LEVEL` option overrides individual package loggers. Package defaults are used unless a command-line override is supplied.

`Debug.log` uses a rotating file handler with three 5 MB backups, so verbose debugging does not grow without bound. The normal default keeps third-party libraries at WARNING and avoids the excessive output and performance problems caused by enabling DEBUG logging globally.

If the analyzer finds a mismatch between realized trade profits and the
reported totals file, it prints the discrepancy and continues normally. Use
`--fix` to automatically delete that stock's saved session, run the evaluation
once from the beginning, and analyze it again:

```bash
python main.py --eval --stock AAPL --fix
```

The retry is limited to one clean rerun. If the totals still disagree, a
warning is printed and the command continues instead of repeatedly rerunning
or stopping the batch. `--fix` has no effect when `--no-analyze` is used.

During an evaluation, the console reports progress in the form
`Day 3: 128 trades`. This is the number of buy, sell, and forced-liquidation
events generated by all configured SMA strategies for that day. Detailed
per-SMA profit totals remain available in the stock totals file and evaluation
log.

### Cleaning Up Logs

Delete all logs for a specific stock:
```bash
python main.py --clean --stock AAPL
```

## Configuration

All trading parameters are centralized in `config.py`:

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
APP_LOG_LEVEL = "INFO"      # Root app log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
PACKAGE_LOG_LEVELS = {      # Third-party package noise suppression
    "yfinance": "WARNING",
    "urllib3": "WARNING",
    "pandas": "WARNING",
    "numpy": "WARNING",
}
LOG_PRICE_INTERVAL = 100    # Log price every N ticks to debug.log
LOG_INDEX_INTERVAL = 100    # Log index info every N ticks to debug.log
EVALLOG_INTERVAL = 100      # Write to EvaluationLog.txt every N ticks
```

## Output files and layout

When you start an evaluation the tool creates an `output/` directory and a
per-stock folder inside it. Generated state and analysis files are kept there,
while source code and configuration remain in the project root. The project
root keeps `Debug.log` so all debug records are consolidated in one place.

For example:

```text
output/
├── AAPL/
│   ├── AAPL_Events.jsonl
│   ├── AAPL_EvaluationLog.txt
│   ├── AAPL_Totals.txt
│   └── AAPL_Analysis.csv
└── MSFT/
    └── ...
```

- `output/<STOCK>/<STOCK>_EvaluationLog.txt`: Detailed timeline of all buy/sell and forced-liquidation actions
- `output/<STOCK>/<STOCK>_Totals.txt`: Daily profit totals for each SMA strategy
- `output/<STOCK>/Stock.txt`: Per-stock pointer and local state files (DayIndex.txt, PriceIndex.txt, SMA.txt, Price.txt)
- `Debug.log` (root): Detailed debug information with automatic size-based rotation
- `output/<STOCK>/StockData.csv`: Cached intraday price data used for simulation
- `output/<STOCK>/<STOCK>_Events.jsonl`: Structured machine-readable buy, sell, and forced-liquidation events

Note: `--clean` will remove artifacts from the per-stock folder (and legacy root-level files if present).

## Analyzer integration and CSV output

Every evaluation writes both a human-readable evaluation log and a structured `<STOCK>_Events.jsonl` file. After evaluation completes, `main.py` automatically runs the analyzer unless `--no-analyze` is supplied.

When invoked with `--stock`, the analyzer automatically prefers a non-empty `<STOCK>_Events.jsonl` file. If no structured event file exists, it falls back to the legacy `<STOCK>_EvaluationLog.txt` parser. This keeps older evaluation folders compatible.

If both files exist, the analyzer merges them. Legacy trades are retained and matching structured events are deduplicated by event type, SMA, and profit. This supports evaluations that were started before structured events were introduced and later resumed with the new code.

- Analyze a stock from the project root:
```bash
python3 tools/analyze.py --events-file output/EH/EH_Events.jsonl --csv output/EH/EH_Analysis.csv --compare-totals --totals-file output/EH/EH_Totals.txt
```

- Analyze a specific structured event file:
```bash
python3 tools/analyze.py --events-file output/EH/EH_Events.jsonl --csv output/EH/EH_Analysis.csv --compare-totals --totals-file output/EH/EH_Totals.txt
```

- Analyze a legacy text log explicitly:
```bash
python3 tools/analyze.py --log-file output/EH/EH_EvaluationLog.txt --csv output/EH/EH_Analysis_full.csv --compare-totals --totals-file output/EH/EH_Totals.txt
```

- Quick summary only:
```bash
python3 tools/analyze.py --stock EH --top 3
```

CSV truncation behavior:
- When you pass `--top N` together with `--csv PATH`, the analyzer will write a truncated CSV that contains only the printed Top N worst SMAs followed by the Top N best SMAs (duplicates removed). This keeps the CSV focused on the most relevant strategies when you only want a short list.
- If you want the full per-SMA table, omit `--top` and provide only `--csv PATH` to write the complete results.

If you'd prefer a different truncation behaviour (for example "Top N overall" rather than worst+best, or preserving the printed order in the CSV), tell me and I can add a flag to control that.

The analyzer counts `sell` and `force_liquidate` events as realized trades and ignores `buy` events when calculating profit totals. Malformed structured-event records fail with a line-specific error instead of silently producing incomplete results.

### Tests

Run the focused unit tests from the repository root:
```bash
python -m unittest discover -s tests -v
```

## How It Works

1. **Data Collection**: Downloads historical intraday data for the specified evaluation period using yfinance
2. **SMA Calculation**: Computes daily SMAs for all configured window sizes (e.g., 1-day through 200-day)
3. **Simulation**: Iterates through each trading day tick-by-tick:
   - Checks each SMA bot's buy/sell conditions
   - Executes trades based on price crossovers
   - Tracks profit/loss for each strategy
   - Applies trading fees and downtime penalties
4. **Reporting**: Generates daily totals and evaluation logs showing performance of each SMA period

The analyzer (`tools/analyze.py`) now also recognizes forced-liquidation log entries (marked by `FORCE-LIQUIDATED`) and includes those final forced closes in the per-SMA aggregates.

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
# 1. Configure your parameters in config.py
# Edit SMA_MIN, SMA_MAX, EVAL_DAYS, etc.

# 2. Start a new evaluation
python main.py --eval --stock TSLA

# 3. Monitor progress in the console
# Day 1
# Day 2
# ...

# 4. Review results (files are inside the per-stock folder)
cat output/TSLA/TSLA_Totals.txt        # See final profits for each SMA
cat output/TSLA/TSLA_EvaluationLog.txt # See detailed trade history (includes FORCE-LIQUIDATED lines)
cat output/TSLA/TSLA_Events.jsonl      # See structured trade events
cat output/TSLA/TSLA_Analysis.csv      # See analyzer output
cat Debug.log                    # See technical/debug details (root)
```

## Project Structure

```
SMA-v2/
â”œâ”€â”€ config.py              # Configuration settings
â”œâ”€â”€ main.py                # CLI entry point
â”œâ”€â”€ requirements.txt       # Python dependencies
â”œâ”€â”€ setup.sh              # Setup script
â”œâ”€â”€ data/
â”‚   â”œâ”€â”€ log_manager.py     # File-based logging
â”‚   â””â”€â”€ stock_updater.py   # Data fetching and SMA calculation
â”œâ”€â”€ evaluate/
â”‚   â”œâ”€â”€ evaluator.py      # Evaluation orchestrator
â”‚   â””â”€â”€ sma.py            # Individual SMA bot logic
â”œâ”€â”€ tests/
â”‚   â””â”€â”€ test_core.py      # Focused unit tests
â””â”€â”€ run/                  # Live SMA notification runner
```

### Code map

- `main.py` reads command-line options, creates stock folders, configures logging, and starts the other parts.
- `config.py` contains the values that control the evaluation.
- `evaluate/evaluator.py` runs the day-by-day evaluation loop.
- `evaluate/sma.py` contains the buy, sell, cooldown, and profit rules for one SMA strategy.
- `data/stock_updater.py` downloads Yahoo Finance data and writes the small state files used for resume support.
- `data/log_manager.py` writes readable logs, totals, and structured trade events.
- `tools/analyze.py` reads structured events or old text logs and creates summaries and CSV files.
- `tests/test_core.py` contains small examples of the expected strategy and analyzer behavior.

The Python files are organized into sections with comments. Functions and methods use standard Python `snake_case` names, such as `stock_directory`, `price_message`, and `sma_list`, so the data flow can be followed without learning a framework.

Names that begin with one underscore, such as `_path()` or `_aggregate()`, are
internal helper functions. Python does not enforce privacy for a single
underscore; it is a clear convention that other modules should normally use
the public functions instead. Double underscores have special name-mangling
behavior and are not used for ordinary helpers in this project.

The renamed public methods use snake_case throughout. A few old camelCase
method names remain as compatibility aliases only, so existing external
scripts can continue running while new code uses the standardized names.

The same convention is used for the rest of the code:

- Module filenames use lowercase `snake_case`, such as `stock_updater.py`.
- Class names use `PascalCase`, such as `StockUpdater` and `LogManager`.
- Variables, attributes, and objects use `snake_case`, such as
  `stock_directory` and `total_profit`.
- Configuration constants intentionally use uppercase names, such as
  `SMA_MIN` and `TRADING_FEE`.

The original title-case module filenames remain as small compatibility
wrappers (`Main.py`, `Config.py`, and similar) for older commands and imports.

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

- Live runner mode: Monitor one SMA and print buy/sell notifications
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
