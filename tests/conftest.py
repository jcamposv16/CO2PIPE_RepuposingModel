import sys
from pathlib import Path

# The co2pipe package lives under src/ and isn't installed (no pyproject.toml /
# setup.py yet), so make it importable for the test suite.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
