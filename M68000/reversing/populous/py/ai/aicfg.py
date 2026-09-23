"""aicfg.py - shared paths/imports for the AI scripts (data in $POP_WORK/ai/)."""
import os, sys
PY = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
if PY not in sys.path: sys.path.insert(0, PY)
from popcfg import WORK, R, DLL, DISK
AI = os.path.join(WORK, 'ai')
os.makedirs(AI, exist_ok=True)
def P(name): return os.path.join(AI, name)
