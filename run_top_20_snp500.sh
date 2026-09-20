#!/usr/bin/env bash

# Run the SMA evaluator for a group of large S&P 500 companies.
#
# The list below is a practical, manually maintained list of large S&P 500
# constituents. Market-cap rankings change, so update this list when you want
# a newly ranked top 20. Yahoo Finance uses "BRK-B" for Berkshire Hathaway.
#
# Usage:
#   ./run_top_20_snp500.sh
#
# Each stock is automatically started fresh when its folder does not exist and
# resumed when its existing session folder is found. Evaluations run one at a time so
# each process has its own state directory and Yahoo Finance is not flooded
# with twenty simultaneous downloads.

set -u

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR" || exit 1

if [[ -x "$PROJECT_DIR/.venv/bin/python" ]]; then
    PYTHON="$PROJECT_DIR/.venv/bin/python"
else
    PYTHON="${PYTHON:-python3}"
fi

if [[ $# -ne 0 ]]; then
    echo "Usage: $0" >&2
    exit 2
fi

# Review or replace these symbols when the current S&P 500 ranking changes.
STOCKS=(
    NVDA
    AAPL
    MSFT
    AMZN
    GOOGL
    AVGO
    META
    TSLA
    BRK-B
    GOOG
    JPM
    WMT
    V
    LLY
    ORCL
    MA
    NFLX
    XOM
    COST
    JNJ
)

FAILED_STOCKS=()
TOTAL_STOCKS="${#STOCKS[@]}"

echo "Running $TOTAL_STOCKS S&P 500 evaluations."
echo "Python: $PYTHON"
echo

for stock in "${STOCKS[@]}"; do
    echo "============================================================"
    echo "Starting $stock"
    echo "============================================================"

    if "$PYTHON" "$PROJECT_DIR/main.py" \
        --eval \
        --stock "$stock" \
        --fix \
        --log-level INFO \
        --log-level-packages WARNING
    then
        echo "Completed $stock"
    else
        echo "FAILED: $stock" >&2
        FAILED_STOCKS+=("$stock")
    fi

    echo
done

echo "Batch complete."
if (( ${#FAILED_STOCKS[@]} > 0 )); then
    echo "Failed stocks: ${FAILED_STOCKS[*]}" >&2
    exit 1
fi

echo "All $TOTAL_STOCKS stocks completed successfully."
