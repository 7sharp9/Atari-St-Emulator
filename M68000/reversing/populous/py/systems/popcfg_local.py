"""Paths for the systems scripts: popcfg (WORK, R, DLL, DISK), the repo root, and OUT = $POP_WORK/systems."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..')))
from popcfg import R, WORK, DLL, DISK
REPO = os.path.normpath(os.path.join(R, '..'))
OUT = os.path.join(WORK, 'systems')
os.makedirs(OUT, exist_ok=True)
