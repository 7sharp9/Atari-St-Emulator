"""Print the frames where (f40, f41, f400) of the F lines change: flags.py <log> [first_frame]   ($80040, $80041, $80400)"""
import sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
from loglib import load
F, eps = load(sys.argv[1]); f0 = int(sys.argv[2]) if len(sys.argv) > 2 else 700
prev = None
for f in sorted(F):
    if f < f0: continue
    k = (F[f]['f40'], F[f]['f41'], F[f].get('f400'))
    if k != prev:
        print(f"f{f}: $80040={k[0]:02x} $80041={k[1]:02x} $80400={k[2]:02x}  scroll {F[f]['sx']:04x},{F[f]['sy']:04x} n={F[f]['n']}")
        prev = k
