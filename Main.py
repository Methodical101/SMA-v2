import argparse
import os
import time
import urllib

from evaluate.Evaluator import Evaluater


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
        parser = argparse.ArgumentParser(description="SMA Evaluator/Runner")
        sessionGroup = parser.add_mutually_exclusive_group(required=True)
        sessionGroup.add_argument("--new", action="store_true", help="Start a new session")
        sessionGroup.add_argument("--resume", action="store_true", help="Resume an existing session")
        sessionGroup.add_argument("--clean", dest="cleanLogs", action="store_true", help="Delete existing evaluation and totals logs for the stock")

        modeGroup = parser.add_mutually_exclusive_group(required=False)
        modeGroup.add_argument("--eval", dest="mode", action="store_const", const="eval", help="Run evaluator mode")
        modeGroup.add_argument("--run", dest="mode", action="store_const", const="run", help="Run live runner mode")

        parser.add_argument("--stock", help="Stock symbol (required for --new and --clean)")
        parser.add_argument("--days", type=int, help="Number of days (required for --new with --run)")

        args = parser.parse_args()

        # if --clean: run cleaning and exit immediately
        if args.cleanLogs:
            if not args.stock:
                parser.error("--stock is required when using --clean")
            for path in (f"{args.stock}_EvaluationLog.txt", f"{args.stock}_Totals.txt"):
                if os.path.exists(path):
                    os.remove(path)
            print(f"Cleaned logs for {args.stock}")
            os._exit(1)

        # validate required arguments
        if args.new and not args.stock:
            parser.error("--stock is required when using --new")

        # make sure a mode is selected
        if not args.mode:
            parser.error("A mode (--eval or --run) is required.")

        # connectivity check loop
        connected = False
        while not connected:
            try:
                urllib.request.urlopen("http://google.com", timeout=5)
                connected = True
            except Exception:
                print("Please connect to the internet. Retrying in 5 seconds...")
                time.sleep(5)

        # resume existing session
        if args.resume:
            # read stock symbol from Stock.txt
            file = open("Stock.txt", "r")
            stockSymbol = file.read().strip()
            file.close()

            # optionally clean logs before starting
            if args.cleanLogs:
                for path in (f"{stockSymbol}_EvaluationLog.txt", f"{stockSymbol}_Totals.txt"):
                    if os.path.exists(path):
                        os.remove(path)
            
            if args.mode == "eval":
                evaluator = Evaluater(stockSymbol)
                evaluator.start()
            elif args.mode == "run":
                file2 = open("RunnerDays.txt", "r")
                days = int(file2.read())
                file2.close()
                # runner = Runner(stockSymbol, days)
                # runner.start()
            return

        # new session setup
        stockSymbol = args.stock

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
            evaluator = Evaluater(stockSymbol)
            evaluator.start()
        elif args.mode == "run":
            if args.days is None:
                parser.error("--days is required when using --new with --run")
            file7 = open(f"{stockSymbol}_RunnerLog.txt", "w")
            file7.write("")
            file7.close()
            file8 = open("RunnerDays.txt", "w")
            file8.write(str(args.days))
            file8.close()
            # runner = Runner(stockSymbol, args.days)
            # runner.start()


if __name__ == "__main__":
    Main().start()
