"""Dump fed_MapGen's creature type table $26040 (64 x 8 bytes) and the slot lists $2602a.. from mg_ret.snap."""
import os, sys
r = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(r, 'tools', 'rdis.py')):
    r = os.path.dirname(r)
sys.path.insert(0, os.path.join(r, 'tools'))
from gfxview import load_ram
ram, base = load_ram(os.path.join(r, 'scratchpad', 'captive', 'mg_ret.snap'))
def B(a): return ram[a - base]
def W(a): return (B(a) << 8) | B(a + 1)
print('slot lists $2602a..$26040:', ' '.join(f'{B(a):02x}' for a in range(0x2602a, 0x26040)))
print('idx  b0 cls max  b1   w2   b4  b5   w6   minD0 sheet rel')
for i in range(64):
    a = 0x26040 + 8 * i
    w6 = W(a + 6)
    print(f'{i:2d}  {B(a):02x}  {B(a)>>4:x}  {B(a)&15:2d}  {B(a+1):3d} {W(a+2):5d} {B(a+4):3d} {B(a+5):3d}  {w6:04x}  {w6&31:3d}   {(w6>>5)&7}   {(w6>>8)&1}')
