#!/usr/bin/env python3
"""HUD enemy-name sheets from the name selector $5b640 [R]: A0 = $5b682 + word[$5b682 + tag]; D1 = word[A0 + 2*kind];
sheet = A0 + D1 + 32*subtype (tag != $a).  Prints the raw words of each tag-2 kind/subtype sheet (16 words, drawn by $1d3a)."""
import os, sys
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
w = lambda a: int.from_bytes(rom[a:a+2], 'big')
tag = int(sys.argv[1], 0) if len(sys.argv) > 1 else 2
A0 = 0x5b682 + w(0x5b682 + tag)
print('tag', tag, 'table at %x' % A0)
for kind in range(int(sys.argv[2]) if len(sys.argv) > 2 else 9):
    D1 = w(A0 + 2*kind)
    for sub in range(4):
        p = A0 + D1 + 32*sub
        print('kind %d sub %d @%06x: %s' % (kind, sub, p, ' '.join('%04x' % w(p+2*i) for i in range(16))))
