"""Analyze evaluation logs for SMA strategies.

Usage examples:
    # analyze by stock symbol (prefers '<STOCK>_Events.jsonl')
    python3 tools/analyze.py --stock AMZN

    # analyze a specific log file path
    python3 tools/analyze.py --log-file AMZN_EvaluationLog.txt

Options:
    --stock STOCK        Stock symbol prefix; prefers structured events, then legacy text logs
    --log-file PATH      Path to an evaluation log file to analyze
    --top N              Show top N worst/best SMAs (default 10)
    --csv OUT            Write per-SMA aggregated results to CSV file

The script parses "sold" entries (realized trades) and reports counts,
aggregate and average profits, and lists worst/best-performing SMA windows.
It is robust to small formatting differences in the log (trailing periods, whitespace).
"""

from __future__ import annotations
import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Tuple

# Example log line (common format produced by Evaluator):
#   SMA bot 53 sold at 219.97500610351562 for a profit of -2.3350006103515626. SMA: 221.2007555691701.
#
# Pattern notes:
# - Captures the SMA id as group 'sma' (digits after "SMA bot").
# - Matches the literal text "sold at <price> for a profit of <profit>".
# - Captures the profit token as group 'profit'. The profit group accepts
#   optional minus sign and exponent notation (e.g. -1.23, 2.3e-1).
# - A trailing '.' after the profit is common in the logs; the regex makes
#   that final period optional (\.?).
SELL_RE = re.compile(
    r"SMA bot\s+(?P<sma>\d+)\s+sold at\s+[\d\.eE+\-]+\s+for a profit of\s+(?P<profit>[\-\d\.eE+]+)\.?",
    re.IGNORECASE,
)

# Match forced liquidations such as:
#  SMA bot 61 FORCE-LIQUIDATED at 401.9010009765625 for P/L -7.804010009765625. SMA: 412.18...
#  SMA bot 61 Force-Liquidated at 401.9010009765625 for net of -7.804010009765625. SMA: 412.18...
FORCE_RE = re.compile(
    r"SMA bot\s+(?P<sma>\d+)\s+FORCE-?LIQUIDATED\s+at\s+"
    r"[\d\.eE+\-]+\s+for\s+(?:P/?L|net\s+of)\s+"
    r"(?P<profit>[\-\d\.eE+]+)\.?",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Input parsing and compatibility merging
# ---------------------------------------------------------------------------
def _aggregate(records: Iterable[Tuple[str, int, float, float]]) -> Tuple[Dict[int, Dict[str, float]], Dict[str, float]]:
    """Add trade records together for the summary and CSV output.

    A record has four values:
    - event name, such as ``sell``
    - SMA number
    - price
    - profit

    Only the SMA and profit are needed for the final report.
    """
    per_sma = defaultdict(lambda: {'count': 0, 'total': 0.0, 'positive': 0, 'negative': 0, 'zero': 0})
    overall = {'count': 0, 'total': 0.0, 'positive': 0, 'negative': 0, 'zero': 0}

    for _, sma, _, profit in records:
        stats = per_sma[sma]
        stats["count"] += 1
        stats["total"] += profit
        if profit > 0:
            stats["positive"] += 1
        elif profit < 0:
            stats["negative"] += 1
        else:
            stats["zero"] += 1

        overall["count"] += 1
        overall["total"] += profit
        if profit > 0:
            overall["positive"] += 1
        elif profit < 0:
            overall["negative"] += 1
        else:
            overall["zero"] += 1
    return per_sma, overall


def parse_log_records(path: str) -> List[Tuple[str, int, float, float]]:
    """Extract realized trades from the old text log format.

    Older sessions do not have a JSONL event file. Keeping this parser means
    those sessions can still be analyzed after the application is upgraded.
    """
    records = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            match = FORCE_RE.search(line)
            event = "force_liquidate"
            if not match:
                match = SELL_RE.search(line)
                event = "sell"
            if not match and "for a profit of" in line:
                sma_match = re.search(r"SMA bot\s+(\d+)", line, re.IGNORECASE)
                profit_match = re.search(r"for a profit of\s+([-\d.eE+]+)", line, re.IGNORECASE)
                if sma_match and profit_match:
                    records.append((event, int(sma_match.group(1)), 0.0, float(profit_match.group(1))))
                continue
            if match:
                try:
                    records.append((
                        event,
                        int(match.group("sma")),
                        0.0,
                        float(match.group("profit").rstrip(" .;,")),
                    ))
                except (ValueError, TypeError):
                    continue
    return records


def parse_log(path: str) -> Tuple[Dict[int, Dict[str, float]], Dict[str, float]]:
    """Parse and aggregate realized trades from a legacy text log."""
    return _aggregate(parse_log_records(path))


def parse_event_records(path: str) -> List[Tuple[str, int, float, float]]:
    """Read the newer one-JSON-object-per-line event file."""
    records = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                event = json.loads(line)
                if event.get("event") not in {"sell", "force_liquidate"}:
                    continue
                sma = int(event["sma"])
                price = float(event["price"])
                profit = float(event["profit"])
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
                raise ValueError(f"Invalid event at {path}:{line_number}: {error}") from error

            records.append((event["event"], sma, price, profit))
    return records


def parse_events(path: str) -> Tuple[Dict[int, Dict[str, float]], Dict[str, float]]:
    """Parse and aggregate realized trades from structured JSONL events."""
    return _aggregate(parse_event_records(path))


def merge_trade_records(*record_sets: Iterable[Tuple[str, int, float, float]]) -> List[Tuple[str, int, float, float]]:
    """Merge legacy and structured records without counting the same trade twice.

    Structured events include a price, while legacy records may not expose it
    reliably. A matching event and legacy record therefore use event, SMA, and
    profit as their compatibility identity.
    """
    merged = []
    legacy_records = list(record_sets[0]) if record_sets else []
    event_records = [record for records in record_sets[1:] for record in records]

    # Treat each legacy occurrence as a single consumable match. This avoids
    # dropping legitimate repeated trades that happen to have equal profits.
    legacy_counts = Counter(
        (event, sma, round(profit, 12))
        for event, sma, _, profit in legacy_records
    )
    merged.extend(legacy_records)

    for event, sma, price, profit in event_records:
        key = (event, sma, round(profit, 12))
        if legacy_counts[key]:
            legacy_counts[key] -= 1
            continue
        merged.append((event, sma, price, profit))
    return merged


# ---------------------------------------------------------------------------
# Human-readable reporting and exports
# ---------------------------------------------------------------------------
def summarize(per_sma: Dict[int, Dict[str, float]], overall: Dict[str, float], top: int = 10) -> None:
    """Print a human-friendly summary of aggregated results."""
    print(f"Parsed sells: {overall['count']}")
    print(f"Overall total profit from sells: {overall['total']:.6f}")
    avg = (overall['total'] / overall['count']) if overall['count'] else 0.0
    print(f"Overall average profit per sell: {avg:.6f}")
    print(f"Overall positive sells: {overall['positive']}")
    print(f"Overall negative sells: {overall['negative']}")
    print(f"Overall zero sells: {overall['zero']}\n")

    smas = sorted(per_sma.items(), key=lambda kv: kv[1]['total'])

    print(f"Top {top} worst SMAs (by total profit):")
    for sma, stats in smas[:top]:
        avg_s = (stats['total'] / stats['count']) if stats['count'] else 0.0
        print(
            f"  SMA {sma}: trades={stats['count']}, total={stats['total']:.6f}, "
            f"avg={avg_s:.6f}, positive={stats['positive']}, negative={stats['negative']}, zero={stats['zero']}"
        )

    print(f"\nTop {top} best SMAs (by total profit):")
    for sma, stats in reversed(smas[-top:]):
        avg_s = (stats['total'] / stats['count']) if stats['count'] else 0.0
        print(
            f"  SMA {sma}: trades={stats['count']}, total={stats['total']:.6f}, "
            f"avg={avg_s:.6f}, positive={stats['positive']}, negative={stats['negative']}, zero={stats['zero']}"
        )


def write_csv(per_sma: Dict[int, Dict[str, float]], out_path: str) -> None:
    """Write per-SMA aggregate stats to CSV (columns: sma, trades, total, avg, positive)."""
    with open(out_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['sma', 'trades', 'total_profit', 'avg_profit', 'positive_trades', 'negative_trades', 'zero_trades'])
        for sma in sorted(per_sma.keys()):
            stats = per_sma[sma]
            avg = (stats['total'] / stats['count']) if stats['count'] else 0.0
            writer.writerow([
                sma,
                stats['count'],
                f"{stats['total']:.6f}",
                f"{avg:.6f}",
                stats['positive'],
                stats['negative'],
                stats['zero'],
            ])


def parse_totals_file(path: str) -> Dict[int, float]:
    """Parse a <STOCK>_Totals.txt file produced by LogManager.append_to_totals.

    Returns a mapping sma -> reported_total (float).
    Expected lines: 'SMA 1: -165.3868' or 'SMA 1: 12.34'
    """
    totals = {}
    with open(path, 'r', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith('SMA '):
                parts = line.split(':', 1)
                if len(parts) != 2:
                    continue
                left, right = parts
                m = re.search(r"SMA\s+(\d+)", left)
                if not m:
                    continue
                sma = int(m.group(1))
                val_str = right.strip().rstrip('.;,')
                try:
                    val = float(val_str)
                except ValueError:
                    try:
                        val = float(re.sub(r"[^0-9eE+\-\.] +$", "", val_str))
                    except Exception:
                        continue
                totals[sma] = val
    return totals


def report_totals_discrepancies(per_sma: Dict[int, Dict[str, float]], totals: Dict[int, float]) -> None:
    """Compare realized sell aggregates (per_sma) to reported totals and print discrepancies.

    Flags SMAs where sign differs or absolute difference is non-zero.
    """
    print('\nComparing realized sell aggregates to totals file...')
    discrepancies = []
    for sma, reported in totals.items():
        agg = per_sma.get(sma)
        if not agg:
            if reported != 0.0:
                discrepancies.append((sma, 'reported_only', reported, 0.0))
            continue
        realized_total = agg['total']
        if (realized_total < 0 and reported >= 0) or (realized_total > 0 and reported <= 0):
            discrepancies.append((sma, 'sign_mismatch', reported, realized_total))
        elif abs(reported - realized_total) > 1e-6:
            discrepancies.append((sma, 'value_mismatch', reported, realized_total))

    if not discrepancies:
        print('No discrepancies found between realized sells and totals file.')
        return

    print(f'Found {len(discrepancies)} discrepancies:')
    for sma, kind, reported, realized in sorted(discrepancies, key=lambda x: x[0]):
        print(f'  SMA {sma}: {kind} -> reported={reported:.6f}, realized={realized:.6f}')


def main(argv=None):
    """Parse CLI arguments, select compatible inputs, and generate reports."""
    parser = argparse.ArgumentParser(description='Analyze SMA evaluation logs (sell trades).')
    parser.add_argument('--stock', '-s', help="Stock symbol; prefer '<STOCK>_Events.jsonl', then legacy text log")
    parser.add_argument('--log-file', '-l', help='Path to evaluation log file')
    parser.add_argument('--events-file', help='Path to structured JSONL trade events')
    parser.add_argument('--top', '-t', type=int, default=10, help='Top N worst/best SMAs to show')
    parser.add_argument('--csv', help='Optional CSV output path for per-SMA stats')
    parser.add_argument('--compare-totals', action='store_true', help='Compare against <STOCK>_Totals.txt and list discrepancies')
    parser.add_argument('--totals-file', help='Path to totals file (overrides --stock)')
    args = parser.parse_args(argv)

    if not args.stock and not args.log_file and not args.events_file:
        parser.error('Specify --stock, --log-file, or --events-file')

    path = args.log_file if args.log_file else f"{args.stock}_EvaluationLog.txt"
    events_path = args.events_file
    if not events_path and args.stock:
        candidate = f"{args.stock}_Events.jsonl"
        if os.path.isfile(candidate) and os.path.getsize(candidate) > 0:
            events_path = candidate

    try:
        # If both files exist, merge them. This matters when an old run is
        # resumed: its legacy log contains the earlier trades, while the new
        # JSONL file contains only trades emitted after the upgrade.
        if events_path:
            event_records = parse_event_records(events_path)
            legacy_records = parse_log_records(path) if os.path.isfile(path) else []
            per_sma, overall = _aggregate(merge_trade_records(legacy_records, event_records))
        else:
            per_sma, overall = parse_log(path)
    except FileNotFoundError:
        missing_path = events_path if events_path else path
        print(f"Error: input file not found: {missing_path}")
        sys.exit(2)
    except ValueError as error:
        print(f"Error: {error}")
        sys.exit(2)

    smas = sorted(per_sma.items(), key=lambda kv: kv[1]['total'])

    summarize(per_sma, overall, top=args.top)

    if args.csv:
        if args.top and args.top > 0:
            topn = args.top
            worst = [sma for sma, _ in smas[:topn]]
            best = [sma for sma, _ in list(reversed(smas[-topn:]))]
            chosen = []
            for s in worst + best:
                if s not in chosen:
                    chosen.append(s)
            filtered = {s: per_sma[s] for s in chosen if s in per_sma}
            write_csv(filtered, args.csv)
        else:
            write_csv(per_sma, args.csv)
        print(f"Wrote CSV to {args.csv}")

    if getattr(args, 'compare_totals', False):
        totals_path = args.totals_file if args.totals_file else (f"{args.stock}_Totals.txt" if args.stock else None)
        if not totals_path:
            print("Error: --compare-totals requires --stock or --totals-file")
            sys.exit(2)
        try:
            totals = parse_totals_file(totals_path)
        except FileNotFoundError:
            print(f"Totals file not found: {totals_path}")
            sys.exit(2)
        report_totals_discrepancies(per_sma, totals)


if __name__ == '__main__':
    main()

