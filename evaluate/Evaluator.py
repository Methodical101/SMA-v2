from numpy import double

from data import StockUpdater, LogManager
from evaluate.SMA import SMA


class Evaluater:

    stock = ""

    def __init__(self,stock):
        self.stock = stock

    def start(self):

        Updater = StockUpdater.StockUpdater()
        Logger = LogManager.LogManager(self.stock)

        smaList = [SMA(i) for i in range(1, 201)] #Create 200 SMAs

        print("-Initializing SMA Evaluator-")
        Logger.appendToEvalLog("---------------------------------") #Separator

        for sma in smaList: #Get all SMAs to start off of and update profits from previous (autoresume)
            Logger.updateSMAFromTotals(sma)
            sma.smaUpdate(Updater)

        file = open("DayIndex.txt", "r")

        day = file.readline()
        file.close()

        print("Day " + day)
        Logger.appendToEvalLog("Day " + day)

        #TradeTime
        while True:

            #get price
            try:
                Updater.historicalUpdate()
            except Exception as e:
                print("Error grabbing stock data for given ticker.")
                raise e

            file1 = open("Price.txt", "r")
            message = file1.readline()
            file1.close()

            Logger.appendToEvalLog("Price: " + message)

            if message == "":
                print("Error reading price data.")
                raise Exception("Error: No price data found.")
            elif message == "DONEALL":
                print("Evaluation Complete!");
                Logger.appendToEvalLog("Evaluation Complete!");
                break
            elif message == "DONE":
                #update day index

                file2 = open("DayIndex.txt", "r")

                tempIndex = int(file2.readline())

                file2.close()

                file3 = open("DayIndex.txt", "w")

                file3.write(str(tempIndex + 1))

                file3.close()

                #make price index 1
                file4 = open("PriceIndex.txt", "w")

                file4.write("1")

                file4.close()

                print("Day " + str(tempIndex + 1))
                Logger.appendToEvalLog("Day " + str(tempIndex + 1))

                for sma in smaList: #each day updates
                    sma.report(Logger)
                    sma.smaDowntimeUpdate()
                    sma.smaUpdate(Updater)


            else:
                #decide to buy or sell or hold
                for sma in smaList:
                    sma.smaAction(double(message), Logger)

            #update price index
            file5 = open("PriceIndex.txt", "r")

            tempPrice = int(file5.readline())

            file5.close()

            Logger.appendToEvalLog("Price Index: " + str(tempPrice))

            file6 = open("PriceIndex.txt", "w")

            file6.write(str(tempPrice + 1))

            file6.close()