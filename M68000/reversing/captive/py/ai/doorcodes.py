"""Coded-door list (fed $1bee8, 8 x (x, y, state)) per case of a gen.py json; prints code and corner order.
Usage: doorcodes.py <gen.json>"""
import json, sys
TAB = bytes.fromhex('')  # filled from the snapshot below when available
N = ['TL', 'TR', 'BL', 'BR']  # corner index c = 2*bottom + right (ai.md)
def order(b):  # table byte: corner k at bits 2k+2 for k=0..2 (ror 2,4,6), 4th at bits 0-1 ($120f4 reader)
    return [N[(b >> s) & 3] for s in (2, 4, 6, 0)]
def main():
    d = json.load(open(sys.argv[1]))
    cases = d if isinstance(d, list) else d.get('cases', d)
    for c in cases:
        ft = bytes.fromhex(c['fedtab'])
        off = 0x1bee8 - 0x1bd3e
        ents = []
        for i in range(8):
            x, y, st = ft[off + 4*i], ft[off + 4*i + 1], int.from_bytes(ft[off + 4*i + 2: off + 4*i + 4], 'big')
            if x or y or st:
                ents.append((x, y, st, (st >> 4) & 0x1f))
        print(c.get('args'), [(f'({x},{y})', f'${st:04x}', code) for x, y, st, code in ents])
main()
