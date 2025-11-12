"""Utility script to fetch intra-day historical close data and update price state files.

This script appears to be invoked repeatedly for each time slice of a simulated/evaluation day.
It writes to `Price.txt` either the latest close price, DONE (day complete), or DONEALL (all days complete).
"""
import datetime
import os

import yfinance as yf

stockSymbol = open("Stock.txt", "r").readline()

# day index handling (0-based internally)
file1 = open("DayIndex.txt", "r")
dateIndexRaw = file1.readline()
file1.close()
dateIndex = int(dateIndexRaw) - 1  # -1 because first logical index starts at 0

if dateIndex == 59:  # finished processing all days
    file2 = open("Price.txt", "w")
    file2.write("DONEALL")
    file2.close()
    os._exit(1)

assert 0 <= dateIndex <= 58  # valid in-progress day range

endDate = (datetime.datetime.now() - datetime.timedelta(days=58 - dateIndex)).strftime("%Y-%m-%d")
startDate = (datetime.datetime.now() - datetime.timedelta(days=59 - dateIndex)).strftime("%Y-%m-%d")

# download close prices at 2m interval for the single-day window
data = yf.download(stockSymbol, interval="2m", start=startDate, end=endDate)["Close"]

data.to_csv("StockData.csv")

# determine max data index (exclude header)
maxIndex = -1  # starts at -1 so first data line becomes 0
fileHandle = open("StockData.csv", "r")
for line in fileHandle:
    if line.strip():
        maxIndex += 1
fileHandle.close()
print(maxIndex)

fileHandle2 = open("PriceIndex.txt", "r")
priceIndex = int(fileHandle2.readline()) - 1  # internal 0-based
fileHandle2.close()
print(priceIndex)

assert priceIndex >= 0

if priceIndex > maxIndex or maxIndex == 0:  # day finished or no data
    fileHandle3 = open("Price.txt", "w")
    fileHandle3.write("DONE")
    fileHandle3.close()
else:
    closePrice = data.iloc[priceIndex]
    fileHandle4 = open("Price.txt", "w")
    fileHandle4.write(str(closePrice))
    fileHandle4.close()
