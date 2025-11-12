from numpy import double
import logging

from Config import SMA_MIN, SMA_STEP, BUY_THRESHOLD, SELL_THRESHOLD, TRADING_FEE, DOWNTIME_DAYS, TRADE_MODE


class SMA:
    """Represents a single Simple Moving Average trading strategy with buy/sell logic."""

    days = 0
    bought = False
    buyPrice = double(0.0)
    totalProfit = double(0.0)
    downtimeDays = 0
    smaMark = double(0.0)

    def __init__(self, days):
        self.days = days
        self.bought = False
        self.buyPrice = double(0.0)
        self.totalProfit = double(0.0)
        self.downtimeDays = 0
        self.smaMark = double(0.0)

    def smaUpdate(self, updater):
        """Active every trade day at end - update SMA mark from file."""
        # Note: SMA data file is updated once per day by Evaluator. Just read it here.

        # read SMA from file - calculate line index based on SMA_MIN and SMA_STEP
        try:
            readFile = open("SMA.txt", "r")
            # Calculate which line this SMA is on (0-indexed)
            lineIndex = (self.days - SMA_MIN) // SMA_STEP
            
            # Read to the correct line
            for _ in range(lineIndex):
                readFile.readline()

            smaValue = readFile.readline().strip()
            readFile.close()
            
            if smaValue == "" or smaValue == "NaN":
                logging.warning(f"Invalid SMA value for SMA {self.days}: '{smaValue}'")
                # Keep previous value
                return
            
            self.smaMark = double(smaValue)

        except Exception as e:
            logging.error(f"Error trying to read SMA data for SMA {self.days}: {e}")
            raise e

    def report(self, logger):
        """Send profits so far to logger for printing."""
        logger.giveEvalReport(self.days, self.totalProfit)

    def smaDowntimeUpdate(self):
        """Starts every day - decrement downtime counter."""
        if self.downtimeDays != 0:
            self.downtimeDays -= 1

    def smaAction(self, price, logger):
        """Active every time slice during trade time - buy/sell logic."""
        # Determine buy/sell signals based on TRADE_MODE
        if TRADE_MODE == 'mean_reversion':
            # mean reversion: buy when price is sufficiently below SMA, sell when above
            buy_condition = (not self.bought) and (self.downtimeDays == 0) and (price + BUY_THRESHOLD < self.smaMark)
            sell_condition = self.bought and (price > self.smaMark + SELL_THRESHOLD)
        else:
            # default/momentum: buy when price sufficiently above SMA, sell when below
            buy_condition = (not self.bought) and (self.downtimeDays == 0) and (self.smaMark + BUY_THRESHOLD < price)
            sell_condition = self.bought and (self.smaMark > price + SELL_THRESHOLD)

        if buy_condition:
            self.bought = True
            self.buyPrice = price
            logger.appendToEvalLog(
                f"SMA bot {self.days} bought at {price}. SMA: {self.smaMark}."
            )
        if sell_condition:
            # perform sell
            self.downtimeDays = self.downtimeDays + DOWNTIME_DAYS
            self.bought = False
            self.totalProfit = self.totalProfit + ((price - self.buyPrice) - TRADING_FEE)
            tempProfit = double(((price - self.buyPrice) - TRADING_FEE))
            logger.appendToEvalLog(
                f"SMA bot {self.days} sold at {price} for a profit of {tempProfit}. SMA: {self.smaMark}."
            )
