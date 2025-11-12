#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# Project environment setup script
#
# What it does:
#   1. Determines project root (directory of this script)
#   2. Creates a Python virtual environment in .venv if missing
#   3. Activates the environment
#   4. Upgrades pip
#   5. Installs requirements.txt if present
#
# Usage:
#   ./setup.sh            # normal setup
#   ./setup.sh --fresh    # delete and recreate .venv before installing
#
# After running, to use the environment in a new shell:
#   source .venv/bin/activate
###############################################################################

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

FRESH=false
if [ "${1:-}" = "--fresh" ]; then
	FRESH=true
fi

if $FRESH && [ -d .venv ]; then
	echo "Removing existing virtual environment (.venv) because --fresh specified"
	rm -rf .venv
fi

if [ ! -d .venv ]; then
	echo "Creating virtual environment in .venv";
	python3 -m venv .venv
else
	echo "Virtual environment already exists (.venv)"
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "Upgrading pip..."
python -m pip install --upgrade pip >/dev/null

if [ -f requirements.txt ]; then
	echo "Installing dependencies from requirements.txt..."
	pip install -r requirements.txt
else
	echo "No requirements.txt found (skipping dependency install)"
fi

# optional: update requirements with exact pinned versions (uncomment if desired)
# echo "Freezing exact versions to requirements.txt" && pip freeze > requirements.txt

echo
echo "Setup complete. Activate with: source .venv/bin/activate"
if $FRESH; then
	echo "(Performed fresh environment rebuild)"
fi
