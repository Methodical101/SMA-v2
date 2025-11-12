import datetime
import os

import pandas as pd
import yfinance as yf


class StockUpdater:
    """Provides methods to update price and SMA data via yfinance.

    historicalUpdate: updates intra-day price for evaluation simulation across days.
    liveUpdate: grabs the latest 1m close price and writes to Price.txt.
    smaUpdate: computes rolling SMAs (1..200) from daily close data and writes snapshot to SMA.txt.
    """

    def __init__(self):
        pass

    def historicalUpdate(self):  # TODO: refine logic & handle weekends explicitly
        stockSymbol = open("Stock.txt", "r").readline()

        file1 = open("DayIndex.txt", "r")
        dateIndexRaw = file1.readline()
        file1.close()
        dateIndex = int(dateIndexRaw) - 1  # convert to 0-based

        if dateIndex == 59:  # all days processed
            file2 = open("Price.txt", "w")
            file2.write("DONEALL")
            file2.close()
            os._exit(1)

        assert 0 <= dateIndex <= 58

        endDate = (datetime.datetime.now() - datetime.timedelta(days=58 - dateIndex)).strftime("%Y-%m-%d")
        startDate = (datetime.datetime.now() - datetime.timedelta(days=59 - dateIndex)).strftime("%Y-%m-%d")

        data = yf.download(stockSymbol, interval="2m", start=startDate, end=endDate)["Close"]
        data.to_csv("StockData.csv")

        # count data rows (exclude header)
        maxIndex = -1
        fileHandle = open("StockData.csv", "r")
        for line in fileHandle:
            if line.strip():
                maxIndex += 1
        fileHandle.close()
        print(maxIndex)

        fileHandle2 = open("PriceIndex.txt", "r")
        priceIndex = int(fileHandle2.readline()) - 1  # 0-based
        fileHandle2.close()
        print(priceIndex)

        assert priceIndex >= 0

        if priceIndex > maxIndex or maxIndex == 0:  # finished the day's data
            file = open("Price.txt", "w")
            file.write("DONE")
            file.close()
        else:
            closePrice = data.iloc[priceIndex]
            file = open("Price.txt", "w")
            file.write(str(closePrice))
            file.close()

    def liveUpdate(self):
        stockSymbol = open("Stock.txt", "r").readline()

        endDate = datetime.datetime.now().strftime("%Y-%m-%d")
        startDate = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        data = yf.download(stockSymbol, interval="1m", start=startDate, end=endDate)["Close"]
        closePrice = data.iloc[-1]

        file = open("Price.txt", "w")
        file.write(str(closePrice))
        file.close()

    def smaUpdate(self):
        stockSymbol = open("Stock.txt", "r").readline()

        maxDays = 59  # evaluation period
        file1 = open("DayIndex.txt", "r")
        indexRaw = file1.readline()
        file1.close()
        dayIndex = int(indexRaw) - 1
        assert 0 <= dayIndex <= maxDays

        endDate = datetime.datetime.now().strftime("%Y-%m-%d")
        startDate = (datetime.datetime.now() - datetime.timedelta(days=1000)).strftime("%Y-%m-%d")

        data = yf.download(stockSymbol, interval="1d", start=startDate, end=endDate)

        for i in range(1, 201):
            data[f"SMA_{i}"] = data["Close"].rolling(window=i).mean()

        file2 = open("SMA.txt", "w")
        bufferOffset = len(data) - 60  # TODO: verify buffer logic vs expected data length
        for i in range(1, 201):
            file2.write(str(data[f"SMA_{i}"].iloc[bufferOffset + dayIndex]))
            if i != 200:
                file2.write("\n")
        file2.close()
