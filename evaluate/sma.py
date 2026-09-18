import logging

from config import SMA_MIN, SMA_STEP, BUY_THRESHOLD, SELL_THRESHOLD, TRADING_FEE, DOWNTIME_DAYS, TRADE_MODE


# ---------------------------------------------------------------------------
# Individual strategy state and trading rules
# ---------------------------------------------------------------------------
class SMA:
    """Represents a single Simple Moving Average trading strategy with buy/sell logic."""

    def __init__(self, days):
        self.days = days
        self.reset()

    def reset(self):
        """Reset all position and performance state to its initial values."""
        self.bought = False
        self.buy_price = 0.0
        self.total_profit = 0.0
        self.downtime_days = 0
        self.sma_mark = 0.0

    def sma_update(self, updater):
        """Active every trade day at end - update SMA mark from file."""
        # SMA.txt contains one line per configured window. The index is
        # derived from the configured range rather than hard-coded to 1..200.
        try:
            with open(updater._path("SMA.txt"), "r", encoding="utf-8") as read_file:
                lines = read_file.read().splitlines()

            line_index = (self.days - SMA_MIN) // SMA_STEP
            if line_index < 0 or line_index >= len(lines):
                logging.warning(f"Invalid SMA line index for SMA {self.days}: {line_index}")
                return

            sma_value = lines[line_index].strip()
            if not sma_value or sma_value == "NaN":
                logging.warning(f"Invalid SMA value for SMA {self.days}: '{sma_value}'")
                return

            self.sma_mark = float(sma_value)
        except Exception as e:
            logging.error(f"Error trying to read SMA data for SMA {self.days}: {e}")
            raise

    def report(self, logger):
        """Send profits so far to logger for printing."""
        logger.give_eval_report(self.days, self.total_profit)

    def force_liquidate(self, price, logger):
        """Force-liquidate any open position at the provided price."""
        if not self.bought:
            return False

        profit = (price - self.buy_price) - TRADING_FEE
        self.total_profit += profit
        logger.append_to_eval_log(
            f"SMA bot {self.days} FORCE-LIQUIDATED at {price} for P/L {profit}. SMA: {self.sma_mark}."
        )
        logger.append_trade_event("force_liquidate", self.days, price, profit)
        self.bought = False
        self.buy_price = 0.0
        return True

    def sma_downtime_update(self):
        """Starts every day - decrement downtime counter."""
        if self.downtime_days != 0:
            self.downtime_days -= 1

    def sma_action(self, price, logger):
        """Active every time slice during trade time - buy/sell logic."""
        # A strategy can hold at most one position. A sell is checked again
        # after a buy so the state cannot produce an accidental same-tick
        # second trade.
        if TRADE_MODE == 'mean_reversion':
            buy_condition = (not self.bought) and (self.downtime_days == 0) and (price + BUY_THRESHOLD < self.sma_mark)
            sell_condition = self.bought and (price > self.sma_mark + SELL_THRESHOLD)
        else:
            buy_condition = (not self.bought) and (self.downtime_days == 0) and (self.sma_mark + BUY_THRESHOLD < price)
            sell_condition = self.bought and (self.sma_mark > price + SELL_THRESHOLD)

        if buy_condition:
            self.bought = True
            self.buy_price = price
            logger.append_to_eval_log(
                f"SMA bot {self.days} bought at {price}. SMA: {self.sma_mark}."
            )
            logger.append_trade_event("buy", self.days, price)

        if sell_condition and self.bought:
            self.downtime_days += DOWNTIME_DAYS
            self.bought = False
            profit = (price - self.buy_price) - TRADING_FEE
            self.total_profit += profit
            logger.append_to_eval_log(
                f"SMA bot {self.days} sold at {price} for a profit of {profit}. SMA: {self.sma_mark}."
            )
            logger.append_trade_event("sell", self.days, price, profit)
            self.buy_price = 0.0

    # Compatibility aliases for scripts that used the original method names.
    smaUpdate = sma_update
    smaDowntimeUpdate = sma_downtime_update
    smaAction = sma_action

