"""Backward-compatible command wrapper for tools.analyze."""

import os
import sys

# Running this file directly makes Python search ``tools/`` first. Add the
# project root so the canonical package import works in that older command.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.analyze import *


if __name__ == "__main__":
    main()
