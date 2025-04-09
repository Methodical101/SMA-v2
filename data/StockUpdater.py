import yfinance as yf
import datetime
import os
import pandas as pd

class StockUpdater:
    def __init__(self):
        pass
    def historicalUpdate(self): #TODO fix

        stock = open("Stock.txt", "r").readline()

        dateIndex = open("DayIndex.txt", "r").readline()
        dateIndex = int(dateIndex)
        dateIndex = dateIndex - 1  # -1 bc first index is at 0

        if dateIndex == 59:  # done with all days
            file = open("Price.txt", "w")
            file.write("DONEALL")
            file.close()
            os._exit(1)

        assert dateIndex >= 0
        assert dateIndex <= 58  # from now on should not be at end (59)

        endDate = (datetime.datetime.now() - datetime.timedelta(days=58 - dateIndex)).strftime('%Y-%m-%d')
        startDate = (datetime.datetime.now() - datetime.timedelta(days=59 - dateIndex)).strftime('%Y-%m-%d')

        data = yf.download(stock, interval='2m', start=startDate, end=endDate)['Close']

        data.to_csv("StockData.csv")

        #set max to the number of lines in the file
        max = -1  # -1 because the first line is the header
        with open("StockData.csv", 'r') as file:
            for line in file:
                if line.strip():  # strip() checks for lines that are not just whitespace
                    max += 1
        print(max)

        file = open("PriceIndex.txt", "r")
        index = int(file.readline()) - 1  # -1 bc first index is at 0. when at max it will be done
        print(index)

        #assert index <= max
        assert index >= 0

        if index > max or max == 0:  # done with all times in day
            file = open("Price.txt", "w")
            file.write("DONE")
            file.close()
        else:
            close = data.iloc[index]

            file = open("Price.txt", "w")
            file.write(str(close))
            file.close()

    def liveUpdate(self):

        stock = open("Stock.txt", "r").readline()

        endDate = datetime.datetime.now().strftime('%Y-%m-%d')
        startDate = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        data = yf.download(stock, interval='1m', start=startDate, end=endDate)['Close']

        #   data.to_csv(os.getcwd().removesuffix("/python") + "/data/PriceLive.csv")

        close = data.iloc[-1]

        file = open("Price.txt", "w")
        file.write(str(close))
        file.close()

    def smaUpdate(self):

        stock = open("Stock.txt", "r").readline()

        max = 59  # index will get 59 days of eval time

        index = open("DayIndex.txt", "r").readline()
        index = int(index) - 1  # -1 bc first index is at 0
        assert index >= 0
        assert index <= max

        endDate = datetime.datetime.now().strftime('%Y-%m-%d')
        startDate = (datetime.datetime.now() - datetime.timedelta(days=1000)).strftime(
            '%Y-%m-%d')  # 100 for a large buffer bc of weekends and holidays or error

        data = yf.download(stock, interval='1d', start=startDate, end=endDate)

        i = 1
        while i <= 200:
            data[f'SMA_{i}'] = data['Close'].rolling(window=i).mean()
            # sma_series = [data['Close'].rolling(window=i).mean().rename(f'SMA_{i}') for i in range(1, 201)]
            # data = pd.concat([data] + sma_series, axis=1)
            i = i + 1

        #data.to_csv("StockData.csv")

        file = open("SMA.txt", "w")

        buffer = data.__len__() - 60 #TODO is 60 right? chcek (also does len work)

        i = 1
        while i <= 200:
            file.write(str(
                data[f'SMA_{i}'].iloc[buffer + index]))  #buffer so it starts backwards from the end of the data
            if i != 200:
                file.write("\n")
            i = i + 1

        file.close()