package run;

import com.sun.tools.javac.Main;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.util.Objects;

import static log.LogManager.*;

/**
 * Java implementation of SMA trading strategy.
 * TODO: Note from project - should be converted to Python.
 */
public class SMA {
    private final int days;
    private boolean bought = false;
    private double buyPrice;
    private double totalProfit = 0;
    private int downtimeDays = 0;
    private double SMAmark;

    public SMA(int days) {
        this.days = days;
    }

    /**
     * Active every trade day at end - updates SMA mark from Python script output.
     */
    public void SMAupdate() {
        // Get SMA from script
        try {
            // Run the python script
            ClassLoader classLoader = com.sun.tools.javac.Main.class.getClassLoader();
            File path = new File(Objects.requireNonNull(classLoader.getResource("python")).toURI());

            ProcessBuilder process = new ProcessBuilder();
            process.directory(new File(path.getAbsolutePath()));
            process.command("python3", "SMAupdater.py");
            process.start();

        } catch (Exception e) {
            System.out.println("Error grabbing SMA data for given ticker.");
            throw new RuntimeException(e);
        }

        // Read SMA from file
        try {
            ClassLoader classLoader = Main.class.getClassLoader();
            File path = new File(Objects.requireNonNull(classLoader.getResource("SMA.txt")).toURI());
            FileReader file = new FileReader(path);
            BufferedReader read = new BufferedReader(file);

            for (int i = 1; i < days; i++) {  // skip other SMAs
                read.readLine();
            }
            SMAmark = Double.parseDouble(read.readLine());  // get SMA
            read.close();
            file.close();
            // System.out.println(SMAmark);
        } catch (Exception e) {
            System.out.println("Error trying to read SMA data.");
            throw new RuntimeException(e);
        }
    }

    public void Report() throws IOException {
        GiveRunnerReport(days, totalProfit);  // sends profits so far and log prints it
    }

    /**
     * Starts every day - decrements downtime counter.
     */
    public void SMAdowntimeUpdate() {
        if (downtimeDays != 0) {
            downtimeDays -= 1;
        }
    }

    /**
     * Active every 30 min only on trade time - buy/sell logic.
     */
    public void SMAaction(double price) throws IOException {
        if (!bought) {  // buying
            if (downtimeDays == 0) {  // not in T-1 (2 days)
                if (SMAmark + 0.05 < price) {  // above SMA (by more than 0.05) -> buy
                    bought = true;
                    buyPrice = price;
                    AppendToRunLog("SMA bot " + days + " bought at " + price + ". SMA: " + SMAmark + ".");
                    System.out.println("SMA bot " + days + " bought at " + price + ". SMA: " + SMAmark + ".");
                }
            }
        } else {  // selling
            if (SMAmark > price + 0.05) {  // below SMA (by more than .05) -> sell
                downtimeDays = downtimeDays + 2;
                bought = false;
                totalProfit = totalProfit + ((price - buyPrice) - 0.05);  // .05 is fee
                double tempProfit = ((price - buyPrice) - 0.05);
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