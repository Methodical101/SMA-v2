"""Command-line entry point for the SMA evaluator.

Program flow:

1. Read and validate command-line arguments.
2. Configure logging.
3. Clean, resume, or create a stock session.
4. Start the evaluator.
5. Run the analyzer when evaluation finishes.

The runner mode is intentionally left as a future feature.
"""

import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from logging.handlers import RotatingFileHandler

from config import APP_LOG_LEVEL, PACKAGE_LOG_LEVELS, LOG_LEVELS, validate_configuration


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def configure_logging(app_level, package_levels):
    """Create the rotating application log and set package log levels."""
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVELS[app_level])
    root_logger.handlers.clear()

    file_handler = RotatingFileHandler(
        "Debug.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root_logger.addHandler(file_handler)

    for package_name, level_name in package_levels.items():
        logging.getLogger(package_name).setLevel(LOG_LEVELS[level_name])


def parse_package_log_overrides(values):
    """Read repeatable NAME=LEVEL command-line package overrides."""
    package_levels = dict(PACKAGE_LOG_LEVELS)

    for value in values or []:
        parts = value.split("=", 1)
        if len(parts) != 2:
            raise ValueError(f"Package log override must use NAME=LEVEL: {value}")

        package_name, level_name = parts
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", package_name):
            raise ValueError(f"Invalid package logger name: {package_name}")

        level_name = level_name.upper()
        if level_name not in LOG_LEVELS:
            raise ValueError(f"Invalid package log level: {level_name}")

        package_levels[package_name] = level_name

    return package_levels


# ---------------------------------------------------------------------------
# Command-line parser and validation
# ---------------------------------------------------------------------------

def create_argument_parser():
    """Build the command-line parser in one easy-to-find place."""
    parser = argparse.ArgumentParser(
        description="SMA Evaluator/Runner - Simulate SMA trading strategies",
        epilog="Example: python main.py --new --eval --stock AAPL",
    )

    session_group = parser.add_mutually_exclusive_group(required=True)
    session_group.add_argument("--new", action="store_true", help="Start a new session")
    session_group.add_argument("--resume", action="store_true", help="Resume a session")
    session_group.add_argument(
        "--clean",
        dest="clean_logs",
        action="store_true",
        help="Delete files for one stock",
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--eval",
        dest="mode",
        action="store_const",
        const="eval",
        help="Run evaluation mode",
    )
    mode_group.add_argument(
        "--run",
        dest="mode",
        action="store_const",
        const="run",
        help="Run mode (not implemented)",
    )

    parser.add_argument("--stock", help="Stock symbol")
    parser.add_argument("--days", type=int, help="Number of runner days")
    parser.add_argument(
        "--log-level",
        choices=list(LOG_LEVELS.keys()),
        default=APP_LOG_LEVEL.upper(),
        help="Application log level",
    )
    parser.add_argument(
        "--log-level-packages",
        choices=list(LOG_LEVELS.keys()),
        help="Apply one level to every configured package",
    )
    parser.add_argument(
        "--log-level-package",
        action="append",
        metavar="NAME=LEVEL",
        help="Override one package logger; repeat this option when needed",
    )
    parser.add_argument(
        "--no-analyze",
        action="store_true",
        help="Skip the analyzer after evaluation",
    )
    return parser


def validate_arguments(parser, args):
    """Validate arguments that argparse cannot express by itself."""
    if args.clean_logs or args.new or args.resume:
        if not args.stock:
            parser.error("--stock is required for --new, --resume, and --clean")

    if args.stock and not re.fullmatch(r"[A-Za-z0-9.^_-]+", args.stock):
        parser.error("--stock contains invalid characters")

    if args.days is not None and args.days < 1:
        parser.error("--days must be positive")

    # Cleaning does not need a mode, but evaluation and resume do.
    if not args.clean_logs and not args.mode:
        parser.error("A mode (--eval or --run) is required")


# ---------------------------------------------------------------------------
# Small file and network helpers
# ---------------------------------------------------------------------------

def write_text(path, text):
    """Write one small state file using UTF-8."""
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)


def check_internet_connection():
    """Check the same Yahoo service used by the evaluator."""
    for attempt in range(1, 6):
        try:
            with urllib.request.urlopen(
                "https://query1.finance.yahoo.com/v8/finance/chart/AAPL",
                timeout=5,
            ):
                return True
        except Exception as error:
            print(f"Internet unavailable; retry {attempt}/5 in 5 seconds...")
            logging.warning("Internet check failed: %s", error)
            time.sleep(5)

    return False


def clean_stock(stock_symbol):
    """Delete the current stock directory and old root-level output files."""
    deleted_count = 0
    stock_directory = os.path.join(os.getcwd(), stock_symbol)

    if os.path.isdir(stock_directory):
        shutil.rmtree(stock_directory)
        deleted_count += 1
        print(f"Deleted directory {stock_directory}")

    old_files = [
        f"{stock_symbol}_EvaluationLog.txt",
        f"{stock_symbol}_Totals.txt",
        f"{stock_symbol}_RunnerLog.txt",
        f"{stock_symbol}_Analysis.csv",
        f"{stock_symbol}_Events.jsonl",
    ]
    for file_name in old_files:
        if os.path.exists(file_name):
            os.remove(file_name)
            deleted_count += 1
            print(f"Deleted {file_name}")

    if deleted_count == 0:
        print(f"No files found for {stock_symbol}")
    else:
        print(f"Cleaned {stock_symbol}: {deleted_count} item(s) removed")


def create_stock_directory(stock_symbol, reset_files):
    """Create a stock directory and initialize its small state files."""
    stock_directory = os.path.join(os.getcwd(), stock_symbol)
    os.makedirs(stock_directory, exist_ok=True)
    write_text(os.path.join(stock_directory, "Stock.txt"), stock_symbol)

    if reset_files:
        write_text(os.path.join(stock_directory, f"{stock_symbol}_Totals.txt"), "")
        write_text(os.path.join(stock_directory, "DayIndex.txt"), "1")
        write_text(os.path.join(stock_directory, "PriceIndex.txt"), "1")
        write_text(os.path.join(stock_directory, f"{stock_symbol}_EvaluationLog.txt"), "")

    # This file is append-only, so creating it does not erase resume history.
    open(
        os.path.join(stock_directory, f"{stock_symbol}_Events.jsonl"),
        "a",
        encoding="utf-8",
    ).close()
    return stock_directory


# ---------------------------------------------------------------------------
# Evaluation and analyzer integration
# ---------------------------------------------------------------------------

def run_analyzer(stock_symbol, stock_directory):
    """Run the analyzer from the stock directory after evaluation."""
    analyzer_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "tools", "analyze.py")
    )
    command = [
        sys.executable,
        analyzer_path,
        "--stock",
        stock_symbol,
        "--top",
        "10",
        "--csv",
        f"{stock_symbol}_Analysis.csv",
        "--compare-totals",
    ]
    logging.info("Running analyzer: %s", " ".join(command))
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=stock_directory,
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        logging.error("Analyzer stderr:\n%s", result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Analyzer failed with exit code {result.returncode}")


def run_evaluation(stock_symbol, stock_directory, skip_analyzer):
    """Import and run the evaluator, then optionally analyze its output."""
    try:
        from evaluate.evaluator import Evaluator
    except ImportError as error:
        raise RuntimeError(
            "Required dependencies are missing. Install requirements.txt and retry."
        ) from error

    evaluator = Evaluator(stock_symbol, stock_directory)
    evaluator.start()

    if not skip_analyzer:
        run_analyzer(stock_symbol, stock_directory)


# ---------------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------------

class Main:
    """Coordinates command-line parsing and session startup."""

    def start(self):
        parser = create_argument_parser()
        args = parser.parse_args()

        try:
            validate_configuration()
            package_levels = parse_package_log_overrides(args.log_level_package)
        except ValueError as error:
            parser.error(str(error))

        if args.log_level_packages:
            for package_name in package_levels:
                package_levels[package_name] = args.log_level_packages
        configure_logging(args.log_level, package_levels)
        validate_arguments(parser, args)

        if args.clean_logs:
            clean_stock(args.stock)
            return

        if not check_internet_connection():
            print("Error: Cannot connect to Yahoo Finance. Exiting.")
            return

        try:
            if args.resume:
                stock_directory = create_stock_directory(args.stock, reset_files=False)
                print(f"Resuming session for {args.stock}")
            else:
                stock_directory = create_stock_directory(args.stock, reset_files=True)
                print(f"Starting new session for {args.stock}")

            if args.mode == "run":
                print("Runner mode is not implemented yet.")
                return

            print(f"Starting evaluation for {args.stock}")
            run_evaluation(args.stock, stock_directory, args.no_analyze)
        except Exception as error:
            logging.exception("Session failed")
            print(f"Error: {error}")


if __name__ == "__main__":
    Main().start()
