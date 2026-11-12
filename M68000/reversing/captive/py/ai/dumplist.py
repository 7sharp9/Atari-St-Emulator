"""Dump the creature-group list at 4532(A6): dumplist.py <snap>"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from cap import *
sys.path.insert(0, os.path.join(R, 'tools')); from gfxview import load_ram
ram, base = load_ram(sys.argv[1] if os.path.isabs(sys.argv[1]) else os.path.join(R, sys.argv[1]))
rd = lambda a, n: ram[a - base:a - base + n]
w = lambda a: int.from_bytes(rd(a, 2), 'big')
print('party', w(A6 + 26), w(A6 + 28), 'rng', hex(w(A6 + 15530)), 'mode', w(A6 + 13564))
a = A6 + 4532; n = 0
while True:
    sz = w(a + 2)
    if sz & 0x8000: print('end at', hex(a), rd(a, 4).hex()); break
    hdr = rd(a, 8); mem = [rd(a + 8 + 8 * i, 8).hex() for i in range((sz - 8) // 8)]
    print(f'{n:2d} ${a:x} x={hdr[0]:2d} y={hdr[1]:2d} size={sz:3d} flags={hdr[4]:02x}{hdr[5]:02x} tmr={hdr[6]} per={hdr[7]} members={mem}')
    a += sz; n += 1
