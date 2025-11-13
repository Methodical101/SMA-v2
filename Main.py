import argparse
from html import parser
import os
import time
import urllib.request
import logging


class Main:
    """Entry point for running evaluation or live runner flows.

    Flags:
        --new | --resume  (mutually exclusive, required)    Start a new session or resume existing
        --eval | --run    (mutually exclusive, required)    Run evaluator or live runner mode
        --stock SYMBOL    (required for --new)              Stock symbol
        --days N          (required for --new with --run)   Number of days for live runner
               
        --clean           (alternative, run with --stock)   Delete <stock>_EvaluationLog.txt and <stock>_Totals.txt
    """

    def start(self) -> None:
        """Parse CLI flags, ensure connectivity, and dispatch actions."""
        # configure single unified log file
        logging.basicConfig(
            filename="Debug.log",
            filemode="w",
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(message)s"
        )
        # Allow all third-party library logs (DEBUG includes INFO, WARNING, ERROR, CRITICAL)
        logging.getLogger("yfinance").setLevel(logging.DEBUG)
        logging.getLogger("urllib3").setLevel(logging.DEBUG)
        logging.getLogger("pandas").setLevel(logging.DEBUG)
        logging.getLogger("numpy").setLevel(logging.DEBUG)
        
        parser = argparse.ArgumentParser(
            description="SMA Evaluator/Runner - Simulate or evaluate SMA trading strategies",
            epilog="Example: python Main.py --new --eval --stock AAPL"
        )
        sessionGroup = parser.add_mutually_exclusive_group(required=True)
        sessionGroup.add_argument("--new", action="store_true", help="Start a new session")
        sessionGroup.add_argument("--resume", action="store_true", help="Resume an existing session")
        sessionGroup.add_argument("--clean", dest="cleanLogs", action="store_true", help="Delete existing evaluation and totals logs for the stock")

        modeGroup = parser.add_mutually_exclusive_group(required=False)
        modeGroup.add_argument("--eval", dest="mode", action="store_const", const="eval", help="Run evaluator mode")
        modeGroup.add_argument("--run", dest="mode", action="store_const", const="run", help="Run live runner mode")

        parser.add_argument("--stock", help="Stock symbol (required for --new and --clean)")
        parser.add_argument("--days", type=int, help="Number of days (required for --new with --run)")
        parser.add_argument("--no-analyze", dest="no_analyze", action="store_true", help="Do not run the analyzer after evaluation completes")

        args = parser.parse_args()

        # if --clean: run cleaning and exit immediately
        if args.cleanLogs:
            if not args.stock:
                parser.error("--stock is required when using --clean")
            deletedCount = 0
            for path in (f"{args.stock}_EvaluationLog.txt", f"{args.stock}_Totals.txt", f"{args.stock}_Analysis.csv"):
                if os.path.exists(path):
                    os.remove(path)
                    deletedCount += 1
                    print(f"Deleted {path}")
                    logging.info(f"Deleted {path}")
            if deletedCount == 0:
                print(f"No existing logs found for {args.stock} (nothing to clean)")
                logging.info(f"No existing logs found for {args.stock}")
            else:
                print(f"Cleaned logs for {args.stock} ({deletedCount} file(s) deleted)")
                logging.info(f"Cleaned logs for {args.stock} ({deletedCount} file(s) deleted)")
            os._exit(0)

        # validate required arguments
        if args.new and not args.stock:
            parser.error("--stock is required when using --new")

        # make sure a mode is selected
        if not args.mode:
            parser.error("A mode (--eval or --run) is required.")

        # connectivity check loop
        connected = False
        retries = 0
        maxRetries = 5
        while not connected and retries < maxRetries:
            try:
                urllib.request.urlopen("http://google.com", timeout=5)
                connected = True
                logging.info("Internet connectivity confirmed")
            except Exception as e:
                retries += 1
                print(f"Please connect to the internet. Retrying in 5 seconds... (attempt {retries}/{maxRetries})")
                logging.warning(f"No internet connection (attempt {retries}/{maxRetries}): {e}")
                time.sleep(5)
        
        if not connected:
            print("Error: Cannot connect to the internet after multiple attempts. Exiting.")
            logging.error("Failed to connect to internet after maximum retries")
            os._exit(1)

        # resume existing session
        if args.resume:
            # read stock symbol from Stock.txt
            try:
                file = open("Stock.txt", "r")
                stockSymbol = file.read().strip()
                file.close()
                
                if stockSymbol == "":
                    print("Error: Stock.txt is empty, cannot resume.")
                    logging.error("Stock.txt is empty")
                    os._exit(1)
                
                print(f"Resuming session for {stockSymbol}")
                logging.info(f"Resuming session for {stockSymbol}")
                
            except FileNotFoundError:
                print("Error: Stock.txt not found. Cannot resume session without a previous session.")
                logging.error("Stock.txt not found")
                os._exit(1)

            if args.mode == "eval":
                try:
                    from evaluate.Evaluator import Evaluater
                except ImportError as e:
                    print("Required dependencies are missing. Please install packages from requirements.txt and try again.")
                    logging.error(f"Import failed for Evaluater: {e}")
                    os._exit(1)
                evaluator = Evaluater(stockSymbol)
                evaluator.start()
                # After evaluation finishes, optionally run the analyzer to summarize results
                if not args.no_analyze:
                    try:
                        import subprocess
                        analyze_cmd = ["python3", "tools/Analyze.py", "--stock", stockSymbol, "--top", "10", "--csv", f"{stockSymbol}_Analysis.csv", "--compare-totals"]
                        logging.info(f"Running analyzer: {' '.join(analyze_cmd)}")
                        proc = subprocess.run(analyze_cmd, capture_output=True, text=True)
                        logging.info(f"Analyzer stdout:\n{proc.stdout}")
                        if proc.stderr:
                            logging.error(f"Analyzer stderr:\n{proc.stderr}")
                        print(proc.stdout)
                    except Exception as e:
                        print(f"Failed to run analyzer: {e}")
                        logging.error(f"Failed to run analyzer: {e}")
            elif args.mode == "run":
                try:
                    file2 = open("RunnerDays.txt", "r")
                    days = int(file2.read())
                    file2.close()
                    print(f"Runner mode not yet implemented (would run for {days} days)")
                    logging.info(f"Runner mode requested but not implemented")
                except FileNotFoundError:
                    print("Error: RunnerDays.txt not found")
                    logging.error("RunnerDays.txt not found")
                    os._exit(1)
            return

        # new session setup
        stockSymbol = args.stock
        print(f"Starting new session for {stockSymbol}")
        logging.info(f"Starting new session for {stockSymbol}")

        file3 = open("Stock.txt", "w")
        file3.write(stockSymbol)
        file3.close()
        file4 = open(f"{stockSymbol}_Totals.txt", "w")
        file4.write("")
        file4.close()

        # reset indexes
        for path in ("PriceIndex.txt", "DayIndex.txt"):
            file5 = open(path, "w")
            file5.write("1")
            file5.close()

        if args.mode == "eval":
            file6 = open(f"{stockSymbol}_EvaluationLog.txt", "w")
            file6.write("")
            file6.close()
            print(f"Starting evaluation for {stockSymbol}")
            logging.info(f"Starting evaluation for {stockSymbol}")
            try:
                from evaluate.Evaluator import Evaluater
            except ImportError as e:
                print("Required dependencies are missing. Please install packages from requirements.txt and try again.")
                logging.error(f"Import failed for Evaluater: {e}")
                os._exit(1)
            evaluator = Evaluater(stockSymbol)
            evaluator.start()
            # After evaluation completes, run the analyzer unless explicitly disabled
            if not args.no_analyze:
                try:
                    import subprocess
                    analyze_cmd = ["python3", "tools/Analyze.py", "--stock", stockSymbol, "--top", "10", "--csv", f"{stockSymbol}_Analysis.csv", "--compare-totals"]
                    logging.info(f"Running analyzer: {' '.join(analyze_cmd)}")
                    proc = subprocess.run(analyze_cmd, capture_output=True, text=True)
                    logging.info(f"Analyzer stdout:\n{proc.stdout}")
                    if proc.stderr:
                        logging.error(f"Analyzer stderr:\n{proc.stderr}")
                    print(proc.stdout)
                except Exception as e:
                    print(f"Failed to run analyzer: {e}")
                    logging.error(f"Failed to run analyzer: {e}")
        elif args.mode == "run":
            if args.days is None:
                parser.error("--days is required when using --new with --run")
            file7 = open(f"{stockSymbol}_RunnerLog.txt", "w")
            file7.write("")
            file7.close()
            file8 = open("RunnerDays.txt", "w")
            file8.write(str(args.days))
            file8.close()
            print(f"Runner mode not yet implemented (would run for {args.days} days)")
            logging.info(f"Runner mode requested but not implemented")
            # runner = Runner(stockSymbol, args.days)
            # runner.start()


if __name__ == "__main__":
    Main().start()
