#!/usr/bin/env python3
"""Decode the text tables behind the 324(A5) command ring (types 0, 10, 11, 12).
Type 0 / 12: table $65f4c, word offsets (index = param & $7f), entries: col.b row.b(bit7: +32 rows) attr.b chars.. 0 ('\\' = new header)
Type 10: table $6718a, entries: word offset into map, word attr, words code.. (0 end, neg = new header)
Type 11: table $681fc (big font, strings).
Prints index, x, y, attr, text.
"""
import os, sys
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
rom = open(os.path.join(root, 'scratchpad', 'finalfight', 'ff_main.bin'), 'rb').read()
def w(a): return int.from_bytes(rom[a:a+2], 'big')
def type0(idx, base=0x65f4c):
    a = base + w(base + 2*idx); out = []
    while True:
        col, row, attr = rom[a], rom[a+1], rom[a+2]; a += 3
        y = row & 0x7f; blk = 32 if row & 0x80 else 0
        s = ''
        while True:
            c = rom[a]; a += 1
            if c == 0: out.append((col, y + blk, attr, s)); return out
            if c == 0x5c: out.append((col, y + blk, attr, s)); break
            s += chr(c) if 32 <= c < 127 else '<%02x>' % c
        if a & 1 == 0 and False: pass
def count(base):
    return w(base) // 2
def type10(idx, base=0x6718a):
    a = base + w(base + 2*idx); out = []
    while True:
        off = w(a); attr = w(a+2); a += 4; s = ''
        while True:
            c = w(a); a += 2
            if c == 0: out.append((off//128, (off % 128)//4, attr, s)); return out
            if c & 0x8000: out.append((off//128, (off % 128)//4, attr, s)); break
            s += chr(c) if 32 <= c < 127 else '<%02x>' % c
if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else '0'
    if which in ('0', '12'):
        n = count(0x65f4c)
        for i in range(n):
            try: print('%02x' % i, type0(i))
            except Exception as e: print('%02x ERR %s' % (i, e)); break
    elif which == '10':
        n = count(0x6718a)
        for i in range(n):
            try: print('%02x' % i, type10(i))
            except Exception as e: print('%02x ERR %s' % (i, e)); break
