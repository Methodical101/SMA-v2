import logging
import os

from config import SMA_MIN, SMA_MAX, SMA_STEP, EVALLOG_INTERVAL
from data import log_manager, stock_updater
from evaluate.sma import SMA


# ---------------------------------------------------------------------------
# Evaluation orchestration
# ---------------------------------------------------------------------------
class Evaluator:
    """Coordinates evaluation across multiple SMA strategies."""

    def __init__(self, stock, base_dir=None):
        self.stock = stock
        self.base_dir = base_dir or os.getcwd()
        logging.info(f"Evaluator initialized for {stock}")

    def start(self):
        """Run the stateful evaluation loop until all configured days finish."""
        # The updater and logger receive the stock directory explicitly. This
        # keeps evaluations independent and avoids changing the global cwd.
        updater = stock_updater.StockUpdater(self.base_dir)
        logger = log_manager.LogManager(self.stock, self.base_dir)
        sma_list = [SMA(i) for i in range(SMA_MIN, SMA_MAX + 1, SMA_STEP)]
        print("Initializing SMA Evaluator...")
        logger.append_to_eval_log("---------------------------------")

        try:
            updater.sma_update()  # start with getting current SMA marks
        except Exception as e:
            logging.error(f"Initial SMA file update failed: {e}")
            raise
        for sma in sma_list:
            logger.update_sma_from_totals(sma)
            sma.sma_update(updater)

        with open(os.path.join(self.base_dir, "DayIndex.txt"), "r", encoding="utf-8") as f:
            current_day = f.readline().strip()
        logger.append_to_eval_log("Day " + current_day)

        while True:
            # Each loop advances one intraday price or transitions to the next
            # day through the DONE/DONEALL sentinel protocol.
            try:
                updater.historical_update()
            except Exception as e:
                logging.error(f"historical_update failed: {e}", exc_info=True)
                raise

            with open(os.path.join(self.base_dir, "Price.txt"), "r", encoding="utf-8") as pf:
                price_message = pf.readline().strip()

            with open(os.path.join(self.base_dir, "PriceIndex.txt"), "r", encoding="utf-8") as rpf:
                current_price_index = int(rpf.readline())

            if EVALLOG_INTERVAL > 0 and (current_price_index % EVALLOG_INTERVAL == 0 or current_price_index == 1):
                logger.append_to_eval_log("Price: " + price_message)
                logger.append_to_eval_log("Price Index: " + str(current_price_index))
            elif EVALLOG_INTERVAL == 0:
                logger.append_to_eval_log("Price: " + price_message)
                logger.append_to_eval_log("Price Index: " + str(current_price_index))

            if price_message == "":
                logging.error("Empty price message")
                raise Exception("Error: No price data found.")
            if price_message == "DONEALL":
                # There is no next price after DONEALL. Close every open
                # position at the last usable price before writing totals.
                final_price = updater.get_last_valid_price()
                if final_price is not None:
                    force_count = 0
                    for sma in sma_list:
                        if sma.force_liquidate(final_price, logger):
                            force_count += 1

                    logger.clear_totals()
                    for sma in sma_list:
                        sma.report(logger)

                    logger.append_to_eval_log(f"Force-liquidated {force_count} positions at {final_price}")
                    logging.info(f"Force-liquidated {force_count} positions at {final_price}")
                else:
                    logger.append_to_eval_log("Force sell skipped! No final price available for force liquidation")
                    logging.warning("No final price available for force liquidation")
                logger.append_to_eval_log("Evaluation Complete!")
                print("Evaluation Complete!")
                try:
                    parent_stock_file = os.path.join(self.base_dir, "..", "Stock.txt")
                    with open(parent_stock_file, "w") as sf:
                        sf.write("")
                except Exception as cerr:
                    logging.error(f"Failed clearing Stock.txt on DONEALL: {cerr}")
                logging.info("Evaluation completed successfully")
                break
            if price_message == "DONE":
                # DONE means one intraday day ended. Reset the intraday index,
                # move to the next day, and publish the previous day's totals.
                logger.clear_totals()
                with open(os.path.join(self.base_dir, "DayIndex.txt"), "r", encoding="utf-8") as df:
                    current_index = int(df.readline())
                with open(os.path.join(self.base_dir, "DayIndex.txt"), "w", encoding="utf-8") as dfw:
                    dfw.write(str(current_index + 1))
                with open(os.path.join(self.base_dir, "PriceIndex.txt"), "w", encoding="utf-8") as pif:
                    pif.write("1")
                logger.append_to_eval_log("Day " + str(current_index + 1))
                print(f"Day {current_index + 1}")
                logging.info(f"Moving to day {current_index + 1}")
                try:
                    updater.sma_update()
                except Exception as e:
                    logging.error(f"Daily SMA file update failed: {e}")
                    raise
                for sma in sma_list:
                    sma.report(logger)
                    sma.sma_downtime_update()
                    sma.sma_update(updater)
                continue

            try:
                price_value = float(price_message)
            except ValueError as e:
                logging.error(f"Invalid price value '{price_message}': {e}")
                continue
            for sma in sma_list:
                sma.sma_action(price_value, logger)

            with open(os.path.join(self.base_dir, "PriceIndex.txt"), "w", encoding="utf-8") as wpf:
                wpf.write(str(current_price_index + 1))


# Keep the old misspelled name working for existing imports.
Evaluater = Evaluator

