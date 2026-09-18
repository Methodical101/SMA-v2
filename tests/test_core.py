import json
import os
import tempfile
import unittest
from contextlib import contextmanager

from data.log_manager import LogManager
from evaluate.sma import SMA
from tools.analyze import merge_trade_records, parse_events


@contextmanager
def temporary_working_directory():
    original = os.getcwd()
    with tempfile.TemporaryDirectory() as directory:
        os.chdir(directory)
        try:
            yield directory
        finally:
            os.chdir(original)


class RecordingLogger:
    def __init__(self):
        self.messages = []
        self.events = []

    def append_to_eval_log(self, message):
        self.messages.append(message)

    def append_trade_event(self, event, sma, price, profit=None):
        self.events.append((event, sma, price, profit))


class SmaBehaviorTests(unittest.TestCase):
    def test_mean_reversion_buy_and_sell(self):
        strategy = SMA(10)
        strategy.sma_mark = 100.0
        logger = RecordingLogger()

        strategy.sma_action(98.0, logger)
        self.assertTrue(strategy.bought)
        strategy.sma_action(102.0, logger)

        self.assertFalse(strategy.bought)
        self.assertEqual(len(logger.events), 2)
        self.assertAlmostEqual(strategy.total_profit, 3.9)

    def test_force_liquidation_closes_position(self):
        strategy = SMA(10)
        strategy.bought = True
        strategy.buy_price = 100.0
        logger = RecordingLogger()

        self.assertTrue(strategy.force_liquidate(103.0, logger))
        self.assertFalse(strategy.bought)
        self.assertAlmostEqual(strategy.total_profit, 2.9)


class StructuredEventTests(unittest.TestCase):
    def test_events_are_written_and_analyzed(self):
        with temporary_working_directory():
            logger = LogManager("TEST")
            logger.append_trade_event("buy", 10, 98.0)
            logger.append_trade_event("sell", 10, 102.0, 3.9)
            logger.append_trade_event("force_liquidate", 20, 103.0, -1.0)

            with open("TEST_Events.jsonl", encoding="utf-8") as handle:
                records = [json.loads(line) for line in handle]

            self.assertEqual(records[1]["event"], "sell")
            per_sma, overall = parse_events("TEST_Events.jsonl")
            self.assertEqual(overall["count"], 2)
            self.assertAlmostEqual(per_sma[10]["total"], 3.9)
            self.assertEqual(per_sma[20]["negative"], 1)

    def test_legacy_and_structured_trades_are_deduplicated(self):
        legacy = [("sell", 10, 0.0, 3.9), ("sell", 10, 0.0, 2.0)]
        structured = [("sell", 10, 102.0, 3.9), ("sell", 10, 104.0, 1.5)]

        merged = merge_trade_records(legacy, structured)

        self.assertEqual(len(merged), 3)
        self.assertAlmostEqual(sum(record[3] for record in merged), 7.4)


if __name__ == "__main__":
    unittest.main()
