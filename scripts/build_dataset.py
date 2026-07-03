"""CLI wrapper for TGFX dataset substrate generation."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.tgfx.dataset import main


if __name__ == "__main__":
    raise SystemExit(main())
