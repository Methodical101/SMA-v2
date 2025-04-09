import yfinance as yf
import datetime
import os

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