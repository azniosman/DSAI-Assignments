import sys, pathlib

# Ensure 'src' is on sys.path for imports in tests
ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
