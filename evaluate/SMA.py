from numpy import double

class SMA:
    days = 0
    bought = False
    buyPrice = double(0.0)
    totalProfit = double(0.0)
    downtimeDays = 0
    smaMark = double(0.0)

    def __init__(self, days):
        self.days = days

    def smaUpdate(self, Updater): #active every trade day at end
        #get SMA from python script
        try:
            Updater.smaUpdate()
        except Exception as e:
            print("Error grabbing SMA data for given ticker.")
            raise e

        #Read SMA from file
        try:

            read = open("SMA.txt", "r")

            i = 1
            while i < self.days:  #skip other SMAs
                read.readline()
                i = i + 1

            self.smaMark = double(read.readline()) #get SMA
            read.close()
            #print(SMAmark)

        except Exception as e:
            print("Error trying to read SMA data.")
            raise e

    def report(self, Logger):
        Logger.giveEvalReport(self.days, self.totalProfit) #sends profits so far and log prints it

    def smaDowntimeUpdate(self): #Starts every day
        if self.downtimeDays != 0:
            self.downtimeDays -= 1

    def smaAction(self, price, Logger): #active every 30 min only on trade time
        if self.bought == False: #buying
            if self.downtimeDays == 0: #not in T-1 (2 days)
                if self.smaMark+.05 < price:  #above SMA (by more than 0.5) -> buy
                    self.bought = True
                    self.buyPrice = price
                    Logger.appendToEvalLog("SMA bot " + self.days + " bought at " + price + ". SMA: " + self.smaMark + ".")
                    print("SMA bot " + self.days + " bought at " + price + ". SMA: " + self.smaMark + ".")
        else: #selling
            if self.smaMark > price+.05: #below SMA (by more than .05) -> sell
                self.downtimeDays = self.downtimeDays + 2
                self.bought = False
                self.totalProfit = self.totalProfit + ((price - self.buyPrice) - .05) #.05 is fee
                tempProfit = double(((price - self.buyPrice) - .05))
                Logger.appendToEvalLog("SMA bot " + self.days + " sold at " + price + " for a profit of " + tempProfit + ". SMA: " + self.smaMark + ".")
                print("SMA bot " + self.days + " sold at " + price + " for a profit of " + tempProfit + ". SMA: " + self.smaMark + ".")