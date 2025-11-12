from numpy import double


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

    def smaUpdate(self, updater):
        """Active every trade day at end - update SMA mark from file."""
        # get SMA
        try:
            updater.smaUpdate()
        except Exception as e:
            print("Error grabbing SMA data for given ticker.")
            raise e

        # read SMA from file
        try:
            readFile = open("SMA.txt", "r")
            i = 1
            while i < self.days:  # skip other SMAs
                readFile.readline()
                i = i + 1

            self.smaMark = double(readFile.readline())  # get SMA
            readFile.close()
            # print(smaMark)

        except Exception as e:
            print("Error trying to read SMA data.")
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
        if not self.bought:  # buying
            if self.downtimeDays == 0:  # not in T-1 (2 days)
                if self.smaMark + 0.05 < price:  # above SMA (by more than 0.05) -> buy
                    self.bought = True
                    self.buyPrice = price
                    logger.appendToEvalLog(
                        f"SMA bot {self.days} bought at {price}. SMA: {self.smaMark}."
                    )
                    print(f"SMA bot {self.days} bought at {price}. SMA: {self.smaMark}.")
        else:  # selling
            if self.smaMark > price + 0.05:  # below SMA (by more than .05) -> sell
                self.downtimeDays = self.downtimeDays + 2
                self.bought = False
                self.totalProfit = self.totalProfit + ((price - self.buyPrice) - 0.05)  # .05 is fee
                tempProfit = double(((price - self.buyPrice) - 0.05))
                logger.appendToEvalLog(
                    f"SMA bot {self.days} sold at {price} for a profit of {tempProfit}. SMA: {self.smaMark}."
                )
                print(f"SMA bot {self.days} sold at {price} for a profit of {tempProfit}. SMA: {self.smaMark}.")
