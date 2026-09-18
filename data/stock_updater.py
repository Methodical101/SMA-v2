import datetime
import logging
import os
import time

import pandas as pd
import yfinance as yf

from config import SMA_MIN, SMA_MAX, SMA_STEP, EVAL_DAYS, LOG_PRICE_INTERVAL, LOG_INDEX_INTERVAL, EVAL_INTRADAY_INTERVAL


# ---------------------------------------------------------------------------
# Market-data access and local evaluation state
# ---------------------------------------------------------------------------
class StockUpdater:
    """Provides methods to update price and SMA data via yfinance."""

    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.getcwd()
        self.cached_intraday_data = None
        self.cached_daily_data = None
        self.cached_symbol = None
        self.max_retries = 3
        self.retry_delay = 3

    def _path(self, filename):
        """Resolve a state or cache filename inside the stock directory."""
        return os.path.join(self.base_dir, filename)

    def _get_stock_symbol(self):
        """Read the stock symbol saved in the stock folder.

        The parent-file fallback keeps older folder layouts working.
        """
        for candidate in (self._path("Stock.txt"), os.path.join(self.base_dir, "..", "Stock.txt")):
            try:
                with open(candidate, "r", encoding="utf-8") as handle:
                    symbol = handle.readline().strip()
                    if symbol:
                        return symbol
            except FileNotFoundError:
                pass
        raise FileNotFoundError("Stock.txt not found in current or parent directory")

    def _write_price_state(self, value):
        """Save the next price or a control word such as DONE."""
        with open(self._path("Price.txt"), "w", encoding="utf-8") as handle:
            handle.write(str(value))

    def fetch_with_retries(self, stock_symbol, interval, start_date, end_date):
        """Download data from yfinance with retry logic and error handling."""
        # Temporary network failures are retried, while the final failure is
        # raised so the caller cannot mistake an incomplete run for success.
        for attempt in range(self.max_retries):
            try:
                logging.info(
                    f"Fetching {stock_symbol} data (interval={interval}, start={start_date}, end={end_date}), attempt {attempt + 1}"
                )
                data = yf.download(stock_symbol, interval=interval, start=start_date, end=end_date, progress=False)

                if data is None or data.empty:
                    logging.warning(f"yfinance returned empty data for {stock_symbol}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    raise RuntimeError(f"No data returned for {stock_symbol} after {self.max_retries} attempts")

                logging.info(f"Successfully fetched {len(data)} rows for {stock_symbol}")
                return data
            except Exception as e:
                logging.error(f"Error fetching data (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise

        raise RuntimeError(f"Failed to fetch data after {self.max_retries} attempts")

    def historical_update(self):
        """Updates intra-day price for evaluation simulation, with caching and error handling."""
        # The evaluator communicates with this method through small state
        # files, preserving resume behavior across process restarts.
        try:
            # DayIndex and PriceIndex are one-based files, so convert them to
            # zero-based indexes before using pandas.
            stock_symbol = self._get_stock_symbol()

            with open(self._path("DayIndex.txt"), "r", encoding="utf-8") as handle:
                date_index = int(handle.readline().strip()) - 1

            if date_index == EVAL_DAYS - 1:
                self._write_price_state("DONEALL")
                logging.info("All evaluation days processed")
                return

            if self.cached_intraday_data is None or self.cached_symbol != stock_symbol:
                logging.info(f"Caching intraday data for {stock_symbol}")
                now = datetime.datetime.now()
                eval_end_date = now.strftime("%Y-%m-%d")
                eval_start_date = (now - datetime.timedelta(days=EVAL_DAYS - 1)).strftime("%Y-%m-%d")

                data = self.fetch_with_retries(stock_symbol, EVAL_INTRADAY_INTERVAL, eval_start_date, eval_end_date)

                if "Close" not in data.columns:
                    logging.error(f"No 'Close' column in intraday data for {stock_symbol}. Columns: {data.columns.tolist()}")
                    raise RuntimeError("No 'Close' column in downloaded data")

                close = data["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                self.cached_intraday_data = close.reset_index(drop=True)
                self.cached_symbol = stock_symbol
                self.cached_intraday_data.to_csv(self._path("StockData.csv"))
                logging.info(f"Cached {len(self.cached_intraday_data)} intraday data points")

            with open(self._path("PriceIndex.txt"), "r", encoding="utf-8") as handle:
                price_index = int(handle.readline().strip()) - 1

            max_index = len(self.cached_intraday_data) - 1
            if LOG_INDEX_INTERVAL > 0 and (price_index % LOG_INDEX_INTERVAL == 0 or price_index == 0 or price_index == max_index):
                logging.debug(f"DayIndex={date_index}, PriceIndex={price_index}, MaxIndex={max_index}")
            elif LOG_INDEX_INTERVAL == 0:
                logging.debug(f"DayIndex={date_index}, PriceIndex={price_index}, MaxIndex={max_index}")

            if price_index > max_index or max_index <= 0:
                self._write_price_state("DONE")
                logging.info("Day complete or no data available")
                return

            close_price = self.cached_intraday_data.iloc[price_index]
            try:
                close_is_nan = bool(pd.isna(close_price))
            except Exception:
                close_is_nan = True

            if close_is_nan:
                logging.warning(f"NaN price at index {price_index}")
                self._write_price_state("DONE")
            else:
                value = float(close_price)
                self._write_price_state(value)
                if LOG_PRICE_INTERVAL > 0 and (price_index % LOG_PRICE_INTERVAL == 0 or price_index == 0 or price_index == max_index):
                    logging.debug(f"Price at index {price_index}: {value}")
                elif LOG_PRICE_INTERVAL == 0:
                    logging.debug(f"Price at index {price_index}: {value}")

        except Exception as e:
            logging.error(f"historical_update failed: {e}", exc_info=True)
            self._write_price_state("DONE")
            raise

    def get_last_valid_price(self):
        """Return the last valid (non-NaN) close price from cached intraday data, or None."""
        try:
            data = self.cached_intraday_data
            if data is None or len(data) == 0:
                return None
            for i in range(len(data) - 1, -1, -1):
                price = data.iloc[i]
                if not pd.isna(price):
                    try:
                        return float(price)
                    except Exception:
                        continue
            return None
        except Exception:
            return None

    def live_update(self):
        """Grabs the latest 1m close price with error handling."""
        try:
            stock_symbol = self._get_stock_symbol()
            end_date = datetime.datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

            data = self.fetch_with_retries(stock_symbol, "1m", start_date, end_date)

            if "Close" not in data.columns or data["Close"].empty:
                logging.warning(f"No close data for {stock_symbol} in live_update")
                raise RuntimeError("No close data available")

            close_price = data["Close"].iloc[-1]
            if pd.isna(close_price):
                logging.warning(f"Latest price is NaN for {stock_symbol}")
                raise RuntimeError("Latest price is NaN")

            self._write_price_state(close_price)
            logging.info(f"Live price for {stock_symbol}: {close_price}")

        except Exception as e:
            logging.error(f"live_update failed: {e}", exc_info=True)
            self._write_price_state("ERROR")
            raise

    def sma_update(self):
        """Computes rolling SMAs with caching and error handling."""
        try:
            # Daily data is downloaded once, then reused for every day in the
            # evaluation. This avoids downloading the same history repeatedly.
            stock_symbol = self._get_stock_symbol()

            max_days = EVAL_DAYS - 1
            with open(self._path("DayIndex.txt"), "r", encoding="utf-8") as handle:
                day_index = int(handle.readline().strip()) - 1
            if not 0 <= day_index <= max_days:
                raise ValueError(f"day_index {day_index} out of range for EVAL_DAYS={EVAL_DAYS}")

            if self.cached_daily_data is None or self.cached_symbol != stock_symbol:
                logging.info(f"Caching daily data for {stock_symbol}")
                end_date = datetime.datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.datetime.now() - datetime.timedelta(days=1000)).strftime("%Y-%m-%d")

                data = self.fetch_with_retries(stock_symbol, "1d", start_date, end_date)
                if "Close" not in data.columns:
                    logging.error(f"No 'Close' column in daily data for {stock_symbol}. Columns: {data.columns.tolist()}")
                    raise RuntimeError("No 'Close' column in daily data")

                for i in range(SMA_MIN, SMA_MAX + 1, SMA_STEP):
                    data[f"SMA_{i}"] = data["Close"].rolling(window=i).mean()

                self.cached_daily_data = data
                self.cached_symbol = stock_symbol
                logging.info(f"Cached {len(self.cached_daily_data)} daily data points")

            data = self.cached_daily_data
            buffer_offset = max(len(data) - EVAL_DAYS, 0)
            target_index = buffer_offset + day_index
            if target_index >= len(data):
                logging.error(f"Target index {target_index} exceeds data length {len(data)}")
                target_index = len(data) - 1

            lines = []
            nan_count = 0
            for i in range(SMA_MIN, SMA_MAX + 1, SMA_STEP):
                sma_value = data[f"SMA_{i}"].iloc[target_index]
                if pd.isna(sma_value):
                    nan_count += 1
                    sma_value = 0.0
                lines.append(str(float(sma_value)))

            with open(self._path("SMA.txt"), "w", encoding="utf-8") as handle:
                handle.write("\n".join(lines))
            logging.debug(f"Updated SMA values for day {day_index} (NaN replaced: {nan_count})")

        except Exception as e:
            logging.error(f"sma_update failed: {e}", exc_info=True)
            with open(self._path("SMA.txt"), "w", encoding="utf-8") as handle:
                for i in range(SMA_MIN, SMA_MAX + 1, SMA_STEP):
                    handle.write("0.0")
                    if i != SMA_MAX:
                        handle.write("\n")
            raise

    # Compatibility aliases keep older integrations working while new code
    # uses the clearer snake_case method names above.
    fetchWithRetries = fetch_with_retries
    historicalUpdate = historical_update
    liveUpdate = live_update
    smaUpdate = sma_update
