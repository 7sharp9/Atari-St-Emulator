"""Capture the register sets of every tile-filler call of one frame: `bp 26b78 3000000` 135 times from the snapshot (a frame has
11 rows x 12 tiles = 132 calls plus a few; each stop prints the registers).  Writes the REPL log.  Usage: tile_capture.py <snap> <out.txt>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
repl(sys.argv[1], ['bp 26b78 3000000'] * 135, sys.argv[2])
