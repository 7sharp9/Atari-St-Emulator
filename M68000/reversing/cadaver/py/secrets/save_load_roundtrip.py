"""save_load_roundtrip.py: S then N declines the price (gold untouched); S, Y, slot key '1' ($02) pays, runs the game's own save path
(custom track format + write through the emulated FDC, $00b6e0/$0154b0) and returns to play; poking gold to 7 and pressing L then '1'
restores the saved state.  Works on a scratch COPY of the disk (the REPL never writes the .st file back, checked: cmp of the copy
afterwards shows 0 bytes changed, the save lives in the emulated drive only).
Start gameplay_empire.snap.  Expected:  N: gold 1000, 1186(A5) = 5 (the floor is written before the prompt);  save: gold 995 (paid 5), price 11 (= 5 + 6*(level+1));
load: gold 995, price 11 (both are inside the $564-byte block the save stores from 1128(A5)).
    uv run python reversing/cadaver/py/secrets/save_load_roundtrip.py"""
import shutil, sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
COPY = 'scratchpad/cadaver/savetest.st'
shutil.copy(ROOT + '/' + DISK, ROOT + '/' + COPY)
def fresh():
    r = Repl(disk=COPY); r.cmd(f'w {A5 + 1188:x} 000003e8'); return r
r = fresh()
r.cmd('kbd 1f', 's 60000', 'kbd 9f', 's 600000', 'kbd 31', 's 60000', 'kbd b1', 's 600000')        # S, N
print('declined: gold', r.l(A5 + 1188), 'price 1186(A5)', r.w(A5 + 1186)); r.close()
r = fresh()
r.cmd('kbd 1f', 's 60000', 'kbd 9f', 's 600000', 'kbd 15', 's 60000', 'kbd 95', 's 600000', 'kbd 02', 's 60000', 'kbd 82', 's 12000000')
print('saved: gold', r.l(A5 + 1188), 'price', r.w(A5 + 1186))
r.cmd(f'w {A5 + 1188:x} 00000007', 'kbd 26', 's 60000', 'kbd a6', 's 1000000', 'kbd 02', 's 60000', 'kbd 82', 's 12000000')
print('after poke gold=7 and L,1: gold', r.l(A5 + 1188), 'price', r.w(A5 + 1186)); r.close()
