from numpy import double


class LogManager:
    """File-based logger for evaluation and run outputs per stock."""

    stock = ""

    def __init__(self, stock):
        self.stock = stock

    def appendToEvalLog(self, message):
        file = open(self.stock + "_EvaluationLog.txt", "a")
        file.write(message + "\n")
        file.close()

    def appendToRunLog(self, message):
        file = open(self.stock + "_RunnerLog.txt", "a")
        file.write(message + "\n")
        file.close()

    def appendToTotals(self, message):
        file = open(self.stock + "_Totals.txt", "a")
        file.write(message + "\n")
        file.close()

    def clearTotals(self):
        file = open(self.stock + "_Totals.txt", "w")
        file.write("")
        file.close()

    def giveEvalReport(self, days, profit):
        daysStr = str(days)
        profitStr = str(profit)
        print(f"SMA {daysStr} finished today with {profitStr} in profit.")
        self.appendToEvalLog(f"SMA {daysStr} finished today with {profitStr} in profit.")
        self.appendToTotals(f"SMA {daysStr}: {profitStr}")

    def giveRunnerReport(self, days, profit):
        daysStr = str(days)
        profitStr = str(profit)
        print(f"SMA {daysStr} finished today with {profitStr} in profit.")
        self.appendToRunLog(f"SMA {daysStr} finished today with {profitStr} in profit.")
        self.appendToTotals(f"SMA {daysStr}: {profitStr}")

    def updateSMAFromTotals(self, sma):
        file = open(self.stock + "_Totals.txt", "r")
        smaLine = file.readline()
        while smaLine != "":
            if str("SMA " + str(sma.days)) in smaLine:
                parts = smaLine.split(": ")
                value = double(parts[1])
                sma.totalProfit = value
                # print(str("SMA Value: " + str(value)))
                break
            else:
                smaLine = file.readline()
        file.close()