"""Analyze evaluation logs for SMA strategies.

Usage examples:
    # analyze by stock symbol (looks for '<STOCK>_EvaluationLog.txt')
    python3 tools/Analyze.py --stock AMZN

    # analyze a specific log file path
    python3 tools/Analyze.py --log-file AMZN_EvaluationLog.txt

Options:
    --stock STOCK        Stock symbol prefix used for log file (e.g. AMZN -> AMZN_EvaluationLog.txt)
    --log-file PATH      Path to an evaluation log file to analyze
    --top N              Show top N worst/best SMAs (default 10)
    --csv OUT            Write per-SMA aggregated results to CSV file

The script parses "sold" entries (realized trades) and reports counts,
aggregate and average profits, and lists worst/best-performing SMA windows.
It is robust to small formatting differences in the log (trailing periods, whitespace).
"""

from __future__ import annotations
import argparse
import re
from collections import defaultdict
from typing import Dict, Tuple
import csv
import sys

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


def parse_log(path: str) -> Tuple[Dict[int, Dict[str, float]], Dict[str, float]]:
    """Parse an evaluation log file and aggregate sell trades per SMA.

    Returns:
        per_sma: dict mapping sma -> {'count': int, 'total': float, 'positive': int}
        overall: dict with keys 'count', 'total', 'positive'
    """
    per_sma = defaultdict(lambda: {'count': 0, 'total': 0.0, 'positive': 0})
    overall = {'count': 0, 'total': 0.0, 'positive': 0}

    # Open the log and iterate line-by-line. This keeps memory usage low when
    # analyzing large logs. We try a strict regex match first (SELL_RE). If the
    # strict match fails but the line contains the text "for a profit of" we
    # attempt a permissive fallback parse to salvage the profit value.
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            for line in fh:
                # Try strict regex match first (recommended format)
                m = SELL_RE.search(line)
                if not m:
                    # Not a strict match. Try permissive fallback only when the
                    # line contains the expected phrase. This handles minor
                    # formatting differences (extra periods, trailing characters).
                    if 'for a profit of' in line:
                        try:
                            # Get the substring after the phrase and take the
                            # first token as the profit candidate. Strip common
                            # trailing punctuation before conversion.
                            parts = line.split('for a profit of', 1)[1]
                            token = parts.strip().split()[0].rstrip('.;,')
                            profit = float(token)
                            # find SMA id with a small regex
                            sma_m = re.search(r"SMA bot\s+(\d+)", line, re.IGNORECASE)
                            if sma_m:
                                sma = int(sma_m.group(1))
                            else:
                                # cannot determine SMA id — skip this line
                                continue
                        except Exception:
                            # fallback failed — skip line
                            continue
                    else:
                        # line doesn't contain a sell event we care about
                        continue
                else:
                    # Strict match succeeded — extract SMA and profit safely
                    sma = int(m.group('sma'))
                    profit_str = m.group('profit').strip()
                    # Remove any trailing punctuation that sometimes appears in logs
                    profit_str = profit_str.rstrip(' .;,')
                    try:
                        profit = float(profit_str)
                    except ValueError:
                        # As a last resort, remove any non-numeric suffix and parse
                        profit = float(re.sub(r"[^0-9eE+\-\.]+$", "", profit_str))

                # Update aggregated counters for this SMA and overall
                per_sma[sma]['count'] += 1
                per_sma[sma]['total'] += profit
                if profit > 0:
                    per_sma[sma]['positive'] += 1
                overall['count'] += 1
                overall['total'] += profit
                if profit > 0:
                    overall['positive'] += 1
    except FileNotFoundError:
        # Let caller handle missing-file errors
        raise
    return per_sma, overall


def summarize(per_sma: Dict[int, Dict[str, float]], overall: Dict[str, float], top: int = 10) -> None:
    """Print a human-friendly summary of aggregated results."""
    print(f"Parsed sells: {overall['count']}")
    print(f"Overall total profit from sells: {overall['total']:.6f}")
    avg = (overall['total'] / overall['count']) if overall['count'] else 0.0
    print(f"Overall average profit per sell: {avg:.6f}")
    print(f"Overall positive sells: {overall['positive']}\n")

    # Sort SMAs by total profit (ascending => worst first)
    smas = sorted(per_sma.items(), key=lambda kv: kv[1]['total'])

    print(f"Top {top} worst SMAs (by total profit):")
    for sma, stats in smas[:top]:
        avg_s = (stats['total'] / stats['count']) if stats['count'] else 0.0
        print(f"  SMA {sma}: trades={stats['count']}, total={stats['total']:.6f}, avg={avg_s:.6f}, positive={stats['positive']}")

    print(f"\nTop {top} best SMAs (by total profit):")
    for sma, stats in reversed(smas[-top:]):
        avg_s = (stats['total'] / stats['count']) if stats['count'] else 0.0
        print(f"  SMA {sma}: trades={stats['count']}, total={stats['total']:.6f}, avg={avg_s:.6f}, positive={stats['positive']}")


def write_csv(per_sma: Dict[int, Dict[str, float]], out_path: str) -> None:
    """Write per-SMA aggregate stats to CSV (columns: sma, trades, total, avg, positive)."""
    with open(out_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['sma', 'trades', 'total_profit', 'avg_profit', 'positive_trades'])
        for sma in sorted(per_sma.keys()):
            stats = per_sma[sma]
            avg = (stats['total'] / stats['count']) if stats['count'] else 0.0
            writer.writerow([sma, stats['count'], f"{stats['total']:.6f}", f"{avg:.6f}", stats['positive']])


def parse_totals_file(path: str) -> Dict[int, float]:
    """Parse a <STOCK>_Totals.txt file produced by LogManager.appendToTotals.

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
                        val = float(re.sub(r"[^0-9eE+\-\.]+$", "", val_str))
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
        # mismatch in sign
        if (realized_total < 0 and reported >= 0) or (realized_total > 0 and reported <= 0):
            discrepancies.append((sma, 'sign_mismatch', reported, realized_total))
        # magnitude mismatch > small epsilon
        elif abs(reported - realized_total) > 1e-6:
            discrepancies.append((sma, 'value_mismatch', reported, realized_total))

    if not discrepancies:
        print('No discrepancies found between realized sells and totals file.')
        return

    print(f'Found {len(discrepancies)} discrepancies:')
    for sma, kind, reported, realized in sorted(discrepancies, key=lambda x: x[0]):
        print(f'  SMA {sma}: {kind} -> reported={reported:.6f}, realized={realized:.6f}')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Analyze SMA evaluation logs (sell trades).')
    parser.add_argument('--stock', '-s', help="Stock symbol (will look for '<STOCK>_EvaluationLog.txt')")
    parser.add_argument('--log-file', '-l', help='Path to evaluation log file')
    parser.add_argument('--top', '-t', type=int, default=10, help='Top N worst/best SMAs to show')
    parser.add_argument('--csv', help='Optional CSV output path for per-SMA stats')
    parser.add_argument('--compare-totals', action='store_true', help='Compare against <STOCK>_Totals.txt and list discrepancies')
    parser.add_argument('--totals-file', help='Path to totals file (overrides --stock)')
    args = parser.parse_args(argv)

    if not args.stock and not args.log_file:
        parser.error('Specify --stock or --log-file')

    path = args.log_file if args.log_file else f"{args.stock}_EvaluationLog.txt"

    try:
        per_sma, overall = parse_log(path)
    except FileNotFoundError:
        print(f"Error: log file not found: {path}")
        sys.exit(2)

    summarize(per_sma, overall, top=args.top)

    if args.csv:
        write_csv(per_sma, args.csv)
        print(f"Wrote CSV to {args.csv}")

    # Optionally compare to totals file
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
