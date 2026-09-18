import os
import json
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Per-stock output manager
# ---------------------------------------------------------------------------
# Evaluation code writes into an isolated stock directory. Keeping path
# construction here prevents callers from depending on the process cwd.
class LogManager:
    """File-based logger for evaluation and run outputs per stock."""

    def __init__(self, stock, base_dir=None):
        self.stock = stock
        self.base_dir = base_dir or os.getcwd()

    def _path(self, suffix):
        """Build a path for one of this stock's output files."""
        return os.path.join(self.base_dir, f"{self.stock}{suffix}")

    def append_trade_event(self, event, sma, price, profit=None):
        """Write a machine-readable trade event without changing the human log."""
        # JSONL is append-only: each line is independently parseable, which
        # makes interrupted evaluations recoverable and easy to inspect.
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "sma": int(sma),
            "price": float(price),
        }
        if profit is not None:
            record["profit"] = float(profit)
        with open(self._path("_Events.jsonl"), "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")

    def append_to_eval_log(self, message):
        """Append one human-readable evaluation message."""
        with open(self._path("_EvaluationLog.txt"), "a", encoding="utf-8") as handle:
            handle.write(message + "\n")

    def append_to_run_log(self, message):
        """Append one human-readable runner message."""
        with open(self._path("_RunnerLog.txt"), "a", encoding="utf-8") as handle:
            handle.write(message + "\n")

    def append_to_totals(self, message):
        """Append one daily SMA total."""
        with open(self._path("_Totals.txt"), "a", encoding="utf-8") as handle:
            handle.write(message + "\n")

    def clear_totals(self):
        """Replace the totals snapshot before writing the next day."""
        with open(self._path("_Totals.txt"), "w", encoding="utf-8") as handle:
            handle.write("")

    def give_eval_report(self, days, profit):
        days_str = str(days)
        profit_str = format(float(profit), ".6f")
        message = f"SMA {days_str} total profit: {profit_str}"
        print(message)
        self.append_to_eval_log(message)
        self.append_to_totals(f"SMA {days_str}: {profit_str}")

    def give_runner_report(self, days, profit):
        days_str = str(days)
        profit_str = format(float(profit), ".6f")
        message = f"SMA {days_str} total profit: {profit_str}"
        print(message)
        self.append_to_run_log(message)
        self.append_to_totals(f"SMA {days_str}: {profit_str}")

    def update_sma_from_totals(self, sma):
        """Restore one strategy's accumulated profit when resuming."""
        totals_path = self._path("_Totals.txt")
        if not os.path.exists(totals_path):
            return

        with open(totals_path, "r", encoding="utf-8") as handle:
            for line in handle:
                prefix = f"SMA {sma.days}"
                if prefix not in line:
                    continue
                parts = line.split(":", 1)
                if len(parts) != 2:
                    continue
                try:
                    sma.total_profit = float(parts[1].strip())
                except ValueError:
                    continue
                break

    # Compatibility aliases keep older scripts working after the public
    # methods were renamed to the standard Python snake_case style.
    appendTradeEvent = append_trade_event
    appendToEvalLog = append_to_eval_log
    appendToRunLog = append_to_run_log
    appendToTotals = append_to_totals
    clearTotals = clear_totals
    giveEvalReport = give_eval_report
    giveRunnerReport = give_runner_report
    updateSMAFromTotals = update_sma_from_totals
