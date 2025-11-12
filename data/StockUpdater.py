import datetime
import os
import logging
import time

import pandas as pd
import yfinance as yf

from Config import SMA_MIN, SMA_MAX, SMA_STEP, EVAL_DAYS, LOG_PRICE_INTERVAL, LOG_INDEX_INTERVAL, EVAL_INTRADAY_INTERVAL


class StockUpdater:
    """Provides methods to update price and SMA data via yfinance.

    historicalUpdate: updates intra-day price for evaluation simulation across days.
    liveUpdate: grabs the latest 1m close price and writes to Price.txt.
    smaUpdate: computes rolling SMAs (1..200) from daily close data and writes snapshot to SMA.txt.
    """

    def __init__(self):
        # Cache for downloaded data (logging unified via root logger in Main)
        self.cachedIntradayData = None
        self.cachedDailyData = None
        self.cachedSymbol = None
        self.maxRetries = 3
        self.retryDelay = 3

    def fetchWithRetries(self, stockSymbol, interval, startDate, endDate):
        """Download data from yfinance with retry logic and error handling."""
        for attempt in range(self.maxRetries):
            try:
                logging.info(f"Fetching {stockSymbol} data (interval={interval}, start={startDate}, end={endDate}), attempt {attempt + 1}")
                data = yf.download(stockSymbol, interval=interval, start=startDate, end=endDate, progress=False)
                
                if data is None or data.empty:
                    logging.warning(f"yfinance returned empty data for {stockSymbol}")
                    if attempt < self.maxRetries - 1:
                        time.sleep(self.retryDelay)
                        continue
                    else:
                        raise RuntimeError(f"No data returned for {stockSymbol} after {self.maxRetries} attempts")
                
                logging.info(f"Successfully fetched {len(data)} rows for {stockSymbol}")
                return data
                
            except Exception as e:
                logging.error(f"Error fetching data (attempt {attempt + 1}/{self.maxRetries}): {e}")
                if attempt < self.maxRetries - 1:
                    time.sleep(self.retryDelay)
                else:
                    raise
        
        raise RuntimeError(f"Failed to fetch data after {self.maxRetries} attempts")

    def historicalUpdate(self):
        """Updates intra-day price for evaluation simulation, with caching and error handling."""
        try:
            stockSymbol = open("Stock.txt", "r").readline().strip()

            file1 = open("DayIndex.txt", "r")
            dateIndexRaw = file1.readline()
            file1.close()
            dateIndex = int(dateIndexRaw) - 1  # convert to 0-based

            if dateIndex == EVAL_DAYS - 1:  # all days processed
                file2 = open("Price.txt", "w")
                file2.write("DONEALL")
                file2.close()
                logging.info("All evaluation days processed")
                return  # let Evaluator.py handle the cleanup and exit

            #assert 0 <= dateIndex <= EVAL_DAYS - 2

            # Download all intraday data for evaluation period if not cached
            if self.cachedIntradayData is None or self.cachedSymbol != stockSymbol:
                logging.info(f"Caching intraday data for {stockSymbol}")
                now = datetime.datetime.now()
                evalEndDate = now.strftime("%Y-%m-%d")
                evalStartDate = (now - datetime.timedelta(days=EVAL_DAYS - 1)).strftime("%Y-%m-%d")
                
                data = self.fetchWithRetries(stockSymbol, EVAL_INTRADAY_INTERVAL, evalStartDate, evalEndDate)
                
                if "Close" not in data.columns:
                    logging.error(f"No 'Close' column in intraday data for {stockSymbol}. Columns: {data.columns.tolist()}")
                    raise RuntimeError("No 'Close' column in downloaded data")
                # Ensure we have a 1-D Series of close prices
                close = data["Close"]
                if isinstance(close, pd.DataFrame):
                    # pick first column if multi-ticker structure sneaks in
                    close = close.iloc[:, 0]
                self.cachedIntradayData = close.reset_index(drop=True)
                self.cachedSymbol = stockSymbol
                self.cachedIntradayData.to_csv("StockData.csv")
                logging.info(f"Cached {len(self.cachedIntradayData)} intraday data points")
            
            # Get current price index
            fileHandle2 = open("PriceIndex.txt", "r")
            priceIndex = int(fileHandle2.readline()) - 1  # 0-based
            fileHandle2.close()
            
            maxIndex = len(self.cachedIntradayData) - 1
            # Show indexing progress on console
            print(f"maxIndex: {maxIndex}, priceIndex: {priceIndex}")
            # Log index info based on config interval
            if LOG_INDEX_INTERVAL > 0 and (priceIndex % LOG_INDEX_INTERVAL == 0 or priceIndex == 0 or priceIndex == maxIndex):
                logging.debug(f"DayIndex={dateIndex}, PriceIndex={priceIndex}, MaxIndex={maxIndex}")
            elif LOG_INDEX_INTERVAL == 0:
                logging.debug(f"DayIndex={dateIndex}, PriceIndex={priceIndex}, MaxIndex={maxIndex}")

            if priceIndex > maxIndex or maxIndex <= 0:  # finished the day's data or no data
                file = open("Price.txt", "w")
                file.write("DONE")
                file.close()
                logging.info("Day complete or no data available")
            else:
                closePrice = self.cachedIntradayData.iloc[priceIndex]
                # Normalize to a native float if possible
                try:
                    closeIsNaN = bool(pd.isna(closePrice))
                except Exception:
                    # pd.isna returned array-like; treat as invalid
                    closeIsNaN = True
                if closeIsNaN:
                    logging.warning(f"NaN price at index {priceIndex}")
                    file = open("Price.txt", "w")
                    file.write("DONE")
                    file.close()
                else:
                    # Write price as string
                    file = open("Price.txt", "w")
                    file.write(str(float(closePrice)))
                    file.close()
                    # Log price based on config interval
                    if LOG_PRICE_INTERVAL > 0 and (priceIndex % LOG_PRICE_INTERVAL == 0 or priceIndex == 0 or priceIndex == maxIndex):
                        logging.debug(f"Price at index {priceIndex}: {float(closePrice)}")
                    elif LOG_PRICE_INTERVAL == 0:
                        logging.debug(f"Price at index {priceIndex}: {float(closePrice)}")

                    
        except Exception as e:
            logging.error(f"historicalUpdate failed: {e}", exc_info=True)
            # Write DONE to prevent infinite loop
            file = open("Price.txt", "w")
            file.write("DONE")
            file.close()
            raise

    def liveUpdate(self):
        """Grabs the latest 1m close price with error handling."""
        try:
            stockSymbol = open("Stock.txt", "r").readline().strip()

            endDate = datetime.datetime.now().strftime("%Y-%m-%d")
            startDate = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

            data = self.fetchWithRetries(stockSymbol, "1m", startDate, endDate)
            
            if "Close" not in data.columns or data["Close"].empty:
                logging.warning(f"No close data for {stockSymbol} in liveUpdate")
                raise RuntimeError("No close data available")
            
            closePrice = data["Close"].iloc[-1]
            
            if pd.isna(closePrice):
                logging.warning(f"Latest price is NaN for {stockSymbol}")
                raise RuntimeError("Latest price is NaN")

            file = open("Price.txt", "w")
            file.write(str(closePrice))
            file.close()
            logging.info(f"Live price for {stockSymbol}: {closePrice}")
            
        except Exception as e:
            logging.error(f"liveUpdate failed: {e}", exc_info=True)
            file = open("Price.txt", "w")
            file.write("ERROR")
            file.close()
            raise

    def smaUpdate(self):
        """Computes rolling SMAs (1..200) with caching and error handling."""
        try:
            stockSymbol = open("Stock.txt", "r").readline().strip()

            maxDays = EVAL_DAYS - 1  # evaluation period (0-based)
            file1 = open("DayIndex.txt", "r")
            indexRaw = file1.readline()
            file1.close()
            dayIndex = int(indexRaw) - 1
            assert 0 <= dayIndex <= maxDays

            # Download daily data if not cached
            if self.cachedDailyData is None or self.cachedSymbol != stockSymbol:
                logging.info(f"Caching daily data for {stockSymbol}")
                endDate = datetime.datetime.now().strftime("%Y-%m-%d")
                startDate = (datetime.datetime.now() - datetime.timedelta(days=1000)).strftime("%Y-%m-%d")

                data = self.fetchWithRetries(stockSymbol, "1d", startDate, endDate)
                
                if "Close" not in data.columns:
                    logging.error(f"No 'Close' column in daily data for {stockSymbol}. Columns: {data.columns.tolist()}")
                    raise RuntimeError("No 'Close' column in daily data")
                
                # Calculate all SMAs
                for i in range(SMA_MIN, SMA_MAX + 1, SMA_STEP):
                    data[f"SMA_{i}"] = data["Close"].rolling(window=i).mean()
                
                self.cachedDailyData = data
                self.cachedSymbol = stockSymbol
                logging.info(f"Cached {len(self.cachedDailyData)} daily data points")
            
            data = self.cachedDailyData
            
            file2 = open("SMA.txt", "w")
            bufferOffset = len(data) - EVAL_DAYS
            
            if bufferOffset < 0:
                logging.warning(f"Insufficient historical data: {len(data)} days available, need at least {EVAL_DAYS}")
                bufferOffset = 0
            
            targetIndex = bufferOffset + dayIndex
            
            if targetIndex >= len(data):
                logging.error(f"Target index {targetIndex} exceeds data length {len(data)}")
                targetIndex = len(data) - 1
            
            # Build all SMA lines first (avoid partial writes if error later)
            lines = []
            nanCount = 0
            for i in range(SMA_MIN, SMA_MAX + 1, SMA_STEP):
                smaValue = data[f"SMA_{i}"].iloc[targetIndex]
                if pd.isna(smaValue):
                    nanCount += 1
                    smaValue = 0.0
                lines.append(str(smaValue))
            file2.write("\n".join(lines))
            file2.close()
            logging.debug(f"Updated SMA values for day {dayIndex} (NaN replaced: {nanCount})")
            
        except Exception as e:
            logging.error(f"smaUpdate failed: {e}", exc_info=True)
            # Write zeros to prevent crashes
            file2 = open("SMA.txt", "w")
            for i in range(SMA_MIN, SMA_MAX + 1, SMA_STEP):
                file2.write("0.0")
                if i != SMA_MAX:
                    file2.write("\n")
            file2.close()
            raise
