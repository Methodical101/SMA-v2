package run;

import com.sun.tools.javac.Main;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.util.Objects;

import static log.LogManager.*;

public class SMA {
    private final int days;
    private boolean bought = false;
    private double buyPrice;
    private double totalProfit = 0;
    private int downtimeDays = 0;
    private double SMAmark;

    public SMA(int days){
        this.days = days;
    }

    public void SMAupdate() { //active every trade day at end
        //get SMA from script
        try{
            //run the python script
            ClassLoader classLoader = com.sun.tools.javac.Main.class.getClassLoader();

            File path = new File(Objects.requireNonNull(classLoader.getResource("python")).toURI()); //get path

            ProcessBuilder process = new ProcessBuilder();

            process.directory(new File(path.getAbsolutePath()));
            process.command("python3", "SMAupdater.py");

            process.start();

        } catch (Exception e) {
            System.out.println("Error grabbing SMA data for given ticker.");
            throw new RuntimeException(e);
        }

        //Read SMA from file
        try {
            ClassLoader classLoader = Main.class.getClassLoader();
            File path = new File(Objects.requireNonNull(classLoader.getResource("SMA.txt")).toURI()); //get path
            FileReader file = new FileReader(path);
            BufferedReader read = new BufferedReader(file);
            for (int i = 1; i < days; i++){ //skip other SMAs
                read.readLine();
            }
            SMAmark = Double.parseDouble(read.readLine()); //get SMA
            read.close();
            file.close();
            //System.out.println(SMAmark);
        } catch (Exception e) {
            System.out.println("Error trying to read SMA data.");
            throw new RuntimeException(e);
        }
    }

    public void Report() throws IOException {
        GiveRunnerReport(days, totalProfit); //sends profits so far and log prints it
    }

    public void SMAdowntimeUpdate(){ //Starts every day
        if (downtimeDays != 0) {
            downtimeDays -= 1;
        }
    }
    public void SMAaction(double price) throws IOException { //active every 30 min only on trade time
        if (bought == false){ //buying
            if (downtimeDays == 0 ){ //not in T-1 (2 days)
                if (SMAmark+.05 < price){ //above SMA (by more than 0.5) -> buy
                    bought = true;
                    buyPrice = price;
                    AppendToRunLog("SMA bot " + days + " bought at " + price + ". SMA: " + SMAmark + ".");
                    System.out.println("SMA bot " + days + " bought at " + price + ". SMA: " + SMAmark + ".");
                }
            }
        } else { //selling
            if (SMAmark > price+.05){ //below SMA (by more than .05) -> sell
                downtimeDays = downtimeDays + 2;
                bought = false;
                totalProfit = totalProfit + ((price - buyPrice) - .05); //.05 is fee
                double tempProfit = ((price - buyPrice) - .05);
                AppendToRunLog("SMA bot " + days + " sold at " + price + " for a profit of " + tempProfit + ". SMA: " + SMAmark + ".");
                System.out.println("SMA bot " + days + " sold at " + price + " for a profit of " + tempProfit + ". SMA: " + SMAmark + ".");
            }
        }
    }
    public int getDays() {
        return days;
    }

    public void setTotalProfit(double profit) {
        totalProfit = profit;
    }
}