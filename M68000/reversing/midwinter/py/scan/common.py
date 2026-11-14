"""Shared helpers for the cell-scan scripts: repo root, data directory, the game's snapshot reader."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'tools', 'rdis.py')): ROOT = os.path.dirname(ROOT)
DATA = os.path.join(ROOT, 'scratchpad', 'midwinter', 'scan')
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'midwinter', 'py', 'pipeline'))
sys.path.insert(0, HERE)
from mw import R
