from numpy import double
import logging

from Config import SMA_MIN, SMA_MAX, SMA_STEP, EVALLOG_INTERVAL
from data import LogManager, StockUpdater
from evaluate.SMA import SMA


class Evaluater:
    """Coordinates evaluation across multiple SMA strategies."""

    def __init__(self, stock):
        self.stock = stock
        logging.info(f"Evaluator initialized for {stock}")

    def start(self):
        updater = StockUpdater.StockUpdater()
        logger = LogManager.LogManager(self.stock)
        smaList = [SMA(i) for i in range(SMA_MIN, SMA_MAX + 1, SMA_STEP)]
        print("Initializing SMA Evaluator...")
        logger.appendToEvalLog("---------------------------------")

        try:
            updater.smaUpdate() # start with getting current SMA marks
        except Exception as e:
            logging.error(f"Initial SMA file update failed: {e}")
            raise
        for sma in smaList:
            logger.updateSMAFromTotals(sma)
            sma.smaUpdate(updater)

        with open("DayIndex.txt", "r") as f:
            currentDay = f.readline().strip()
        logger.appendToEvalLog("Day " + currentDay)

        # trade loop
        while True:
            # get price
            try:
                updater.historicalUpdate()
            except Exception as e:
                logging.error(f"historicalUpdate failed: {e}", exc_info=True)
                raise

            with open("Price.txt", "r") as pf:
                priceMessage = pf.readline().strip()
            
            # Read current price index to determine if we should log
            with open("PriceIndex.txt", "r") as rpf:
                currentPriceIndex = int(rpf.readline())
            
            # Log to EvaluationLog based on config interval
            if EVALLOG_INTERVAL > 0 and (currentPriceIndex % EVALLOG_INTERVAL == 0 or currentPriceIndex == 1):
                logger.appendToEvalLog("Price: " + priceMessage)
                logger.appendToEvalLog("Price Index: " + str(currentPriceIndex))
            elif EVALLOG_INTERVAL == 0:
                logger.appendToEvalLog("Price: " + priceMessage)
                logger.appendToEvalLog("Price Index: " + str(currentPriceIndex))

            if priceMessage == "":
                logging.error("Empty price message")
                raise Exception("Error: No price data found.")
            if priceMessage == "DONEALL":
                logger.appendToEvalLog("Evaluation Complete!")
                print("Evaluation Complete!")
                try:
                    with open("Stock.txt", "w") as sf:
                        sf.write("")
                except Exception as cerr:
                    logging.error(f"Failed clearing Stock.txt on DONEALL: {cerr}")
                logging.info("Evaluation completed successfully")
                break
            if priceMessage == "DONE":
                logger.clearTotals()
                with open("DayIndex.txt", "r") as df:
                    currentIndex = int(df.readline())
                with open("DayIndex.txt", "w") as dfw:
                    dfw.write(str(currentIndex + 1))
                with open("PriceIndex.txt", "w") as pif:
                    pif.write("1")
                logger.appendToEvalLog("Day " + str(currentIndex + 1))
                print(f"Day {currentIndex + 1}")
                logging.info(f"Moving to day {currentIndex + 1}")
                try:
                    updater.smaUpdate()
                except Exception as e:
                    logging.error(f"Daily SMA file update failed: {e}")
                    raise
                for sma in smaList:
                    sma.report(logger)
                    sma.smaDowntimeUpdate()
                    sma.smaUpdate(updater)
                continue

            try:
                priceValue = double(priceMessage)
            except ValueError as e:
                logging.error(f"Invalid price value '{priceMessage}': {e}")
                continue
            for sma in smaList:
                sma.smaAction(priceValue, logger)

            with open("PriceIndex.txt", "w") as wpf:
                wpf.write(str(currentPriceIndex + 1))