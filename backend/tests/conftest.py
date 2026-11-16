from pathlib import Path
import sys


# Permit the documented root command without a global editable installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
