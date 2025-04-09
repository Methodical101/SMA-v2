import time
import sys
import urllib

from evaluate.Evaluator import Evaluater


class Main:
    def start(self):

        #check for internet
        connected = False
        while not connected:
            try:
                urllib.request.urlopen("http://google.com", timeout=5)
                connected = True
            except Exception as e: #if not work
                #failure
                print("Please connect to the internet. Retrying in 5 seconds...")
                time.sleep(5)


        newOrRes = sys.argv[1]
        if newOrRes == "resume":
            if sys.argv[2] == "eval":
                #eval start
                Eval = Evaluater(sys.argv[3])
                Eval.start()

            if sys.argv[2] == "run":
                #get days from file
                file = open("RunnerDays.txt", "r")
                days = int(file.read())

                #run start
                # Run = Runner(sys.argv[3], days)
                # Run.start()

        else: #new
            stock = sys.argv[3]

            file = open("Stock.txt", "w")
            file.write(stock)
            file.close()

            file1 = open(stock + "_Totals.txt", "w")
            file1.write("")
            file1.close()

            #reset indexes
            file2 = open("PriceIndex.txt", "w")
            file2.write("1")
            file2.close()
            file3 = open("DayIndex.txt", "w")
            file3.write("1")
            file3.close()

            if sys.argv[2] == "eval":
                file4 = open(stock + "_EvaluationLog.txt", "w")
                file4.write("")
                file4.close()

                #eval start
                Eval = Evaluater(sys.argv[3])
                Eval.start()

            if sys.argv[2] == "run":
                file5 = open(stock + "_RunnerLog.txt", "w")
                file5.write("")
                file5.close()

                file6 = open("RunnerDays.txt", "w")
                file6.write(sys.argv[4])
                file6.close()

                #run start
                # Run = Runner(sys.argv[3], days)
                # Run.start()

if __name__ == "__main__":
    app = Main()
    app.start()