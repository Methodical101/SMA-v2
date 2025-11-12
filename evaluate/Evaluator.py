from numpy import double

from data import LogManager, StockUpdater
from evaluate.SMA import SMA


class Evaluater:
    """Coordinates evaluation across multiple SMA strategies."""

    stock = ""

    def __init__(self, stock):
        self.stock = stock

    def start(self):
        updater = StockUpdater.StockUpdater()
        logger = LogManager.LogManager(self.stock)

        smaList = [SMA(i) for i in range(1, 201)]  # create 200 SMAs

        print("-Initializing SMA Evaluator-")
        logger.appendToEvalLog("---------------------------------")  # separator

        # initialize SMAs from totals and get current SMA marks
        for sma in smaList:
            logger.updateSMAFromTotals(sma)
            sma.smaUpdate(updater)

        file = open("DayIndex.txt", "r")
        currentDay = file.readline()
        file.close()

        print("Day " + currentDay)
        logger.appendToEvalLog("Day " + currentDay)

        # trade loop
        while True:
            # get price
            try:
                updater.historicalUpdate()
            except Exception as e:
                print("Error grabbing stock data for given ticker.")
                raise e

            file1 = open("Price.txt", "r")
            priceMessage = file1.readline()
            file1.close()

            logger.appendToEvalLog("Price: " + priceMessage)

            if priceMessage == "":
                print("Error reading price data.")
                raise Exception("Error: No price data found.")
            elif priceMessage == "DONEALL":
                print("Evaluation Complete!")
                logger.appendToEvalLog("Evaluation Complete!")
                break
            elif priceMessage == "DONE":
                # update day index
                file2 = open("DayIndex.txt", "r")
                currentIndex = int(file2.readline())
                file2.close()

                file3 = open("DayIndex.txt", "w")
                file3.write(str(currentIndex + 1))
                file3.close()

                # reset price index to 1
                file4 = open("PriceIndex.txt", "w")
                file4.write("1")
                file4.close()

                print("Day " + str(currentIndex + 1))
                logger.appendToEvalLog("Day " + str(currentIndex + 1))

                for sma in smaList:  # each day updates
                    sma.report(logger)
                    sma.smaDowntimeUpdate()
                    sma.smaUpdate(updater)

            else:
                # decide to buy or sell or hold
                for sma in smaList:
                    sma.smaAction(double(priceMessage), logger)

            # update price index
            file5 = open("PriceIndex.txt", "r")
            currentPriceIndex = int(file5.readline())
            file5.close()

            logger.appendToEvalLog("Price Index: " + str(currentPriceIndex))

            file6 = open("PriceIndex.txt", "w")
            file6.write(str(currentPriceIndex + 1))
            file6.close()