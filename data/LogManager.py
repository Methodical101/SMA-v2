from numpy import double


class LogManager:
    stock = ""
    def __init__(self, stock):
        self.stock = stock

    def appendToEvalLog(self, message):
        with open(self.stock + "_EvaluationLog.txt", "a") as file:
            file.write(message + "\n")
        file.close()

    def appendToRunLog(self, message):
        with open(self.stock + "_RunnerLog.txt", "a") as file:
            file.write(message + "\n")
        file.close()

    def appendToTotals(self, message):
        with open(self.stock + "_Totals.txt", "a") as file:
            file.write(message + "\n")
        file.close()

    def giveEvalReport(self, days, profit):
        days = str(days)
        profit = str(profit)
        print("SMA " + days + " finished today with " + profit + " in profit.")
        self.appendToEvalLog("SMA " + days + " finished today with " + profit + " in profit.")
        self.appendToTotals("SMA " + days + ": " + profit)

    def giveRunnerReport(self, days, profit):
        days = str(days)
        profit = str(profit)
        print("SMA " + days + " finished today with " + profit + " in profit.")
        self.appendToRunLog("SMA " + days + " finished today with " + profit + " in profit.")
        self.appendToTotals("SMA " + days + ": " + profit)

    def updateSMAFromTotals(self, sma):
        file = open(self.stock + "_Totals.txt", "r")
        smaLine = file.readline()
        while smaLine != "":
            if str("SMA " + sma.days) in smaLine:
                parts = smaLine.split(": ")
                value = double(parts[1])
                sma.totalProfit = value
                #print(str("SMA Value: " + value))
            else:
                smaLine = file.readline()