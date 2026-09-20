"""Live price monitoring and SMA buy/sell notifications."""

import logging
import time
from datetime import datetime

import pandas as pd
import yfinance as yf

from config import BUY_THRESHOLD, RUNNER_INTERVAL, RUNNER_POLL_SECONDS, SELL_THRESHOLD, TRADE_MODE
from data.log_manager import LogManager


class Runner:
    """Watch one stock and print a notification when a strategy signal occurs."""

    def __init__(self, stock_symbol, sma_days, output_directory, poll_seconds=None):
        self.stock_symbol = stock_symbol
        self.sma_days = sma_days
        self.output_directory = output_directory
        self.poll_seconds = poll_seconds or RUNNER_POLL_SECONDS
        self.log_manager = LogManager(stock_symbol, output_directory)
        self.has_position = False
        self.last_signal = None

    def fetch_latest_values(self):
        """Return the latest price and SMA calculated from recent daily closes."""
        history_days = max(self.sma_days * 3, 30)
        daily_data = yf.download(
            self.stock_symbol,
            period=f"{history_days}d",
            interval="1d",
            progress=False,
        )
        live_data = yf.download(
            self.stock_symbol,
            period="1d",
            interval=RUNNER_INTERVAL,
            progress=False,
        )

        if daily_data is None or daily_data.empty:
            raise RuntimeError(f"No daily data returned for {self.stock_symbol}")
        if live_data is None or live_data.empty:
            raise RuntimeError(f"No live data returned for {self.stock_symbol}")

        daily_close = daily_data["Close"]
        live_close = live_data["Close"]
        if isinstance(daily_close, pd.DataFrame):
            daily_close = daily_close.iloc[:, 0]
        if isinstance(live_close, pd.DataFrame):
            live_close = live_close.iloc[:, 0]

        daily_close = daily_close.dropna()
        live_close = live_close.dropna()
        if len(daily_close) < self.sma_days or live_close.empty:
            raise RuntimeError(f"Not enough price history for SMA {self.sma_days}")

        sma_value = float(daily_close.tail(self.sma_days).mean())
        current_price = float(live_close.iloc[-1])
        return current_price, sma_value

    def get_signal(self, price, sma_value):
        """Return buy, sell, or None using the configured trading mode."""
        if TRADE_MODE == "mean_reversion":
            buy_ready = not self.has_position and price + BUY_THRESHOLD < sma_value
            sell_ready = self.has_position and price > sma_value + SELL_THRESHOLD
        else:
            buy_ready = not self.has_position and price > sma_value + BUY_THRESHOLD
            sell_ready = self.has_position and sma_value > price + SELL_THRESHOLD

        if buy_ready:
            return "BUY"
        if sell_ready:
            return "SELL"
        return None

    def check_once(self):
        """Fetch one price, print a signal if needed, and return the signal."""
        price, sma_value = self.fetch_latest_values()
        signal = self.get_signal(price, sma_value)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if signal:
            self.has_position = signal == "BUY"
            message = (
                f"{now} | {self.stock_symbol} | {signal} | "
                f"price={price:.4f} | SMA({self.sma_days})={sma_value:.4f}"
            )
            print(message, flush=True)
            self.log_manager.append_to_run_log(message)
            self.last_signal = signal
        else:
            logging.debug(
                "%s price=%.4f SMA(%s)=%.4f no signal",
                self.stock_symbol,
                price,
                self.sma_days,
                sma_value,
            )
        return signal

    def start(self):
        """Keep monitoring until the user stops the runner with Ctrl+C."""
        print(
            f"Watching {self.stock_symbol} with SMA({self.sma_days}) "
            f"every {self.poll_seconds} seconds. Press Ctrl+C to stop.",
            flush=True,
        )
        try:
            while True:
                try:
                    self.check_once()
                except Exception as error:
                    logging.error("Runner update failed: %s", error, exc_info=True)
                    print(f"Runner warning: {error}", flush=True)
                time.sleep(self.poll_seconds)
        except KeyboardInterrupt:
            print("\nRunner stopped.", flush=True)
