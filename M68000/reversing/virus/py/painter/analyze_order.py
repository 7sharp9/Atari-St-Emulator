"""analyze_order.py <scr_capture.json> ...   Draw-order gate: which dot survives where two dot records overlap.
Each dot routine ($16fb4 ..) is read from its own code bytes: the four plane operations on (A0)+ are `or.w D2` (8558,
plane bit set) or `and.w D1` (c358, plane bit cleared), so the dot paints one definite 4-plane colour.  A dot covers
the pixels set in the mask word 0(A3,(x&15)*2) of its bucket's mask table (3, 2 or 1 pixel wide from $24488) on one
row, or two rows (y, y+1) when the bucket is 4 or nearer (the flag $16fb2 is `sgt` of the bucket number against 4).
Draw order is bucket 9 down to 1, then 0 (a bucket drawn after the tile row of its own number), records in list order.
For every pixel covered by at least two dots of different colours the last dot's colour is predicted and compared with
the screen read at $24478 (the painter's end).  Control: the first dot's colour."""
import json, struct, sys, collections, os

def colours(code):
    out = {}
    for off in range(0, len(code) - 2, 2):
        pass
    # each routine: find the four plane ops after its start
    return out

def routine_colour(code, base, addr):
    """Scan the code from addr for the first four 8558/c358 words (or.w D2,(A0)+ / and.w D1,(A0)+)."""
    p = addr - base; ops = []
    while p < len(code) - 1 and len(ops) < 4:
        w = struct.unpack('>H', code[p:p + 2])[0]
        if w == 0x8558: ops.append(1)
        elif w == 0xc358: ops.append(0)
        p += 2
    return sum(b << i for i, b in enumerate(ops)) if len(ops) == 4 else None

def routine_two_rows(code, base, addr):
    """True when the routine reads the flag $16fb2 (tst.b $16fb2.l = 4a39 0001 6fb2) before its rts: it then paints a second scanline for buckets 4 and nearer."""
    p = addr - base
    while p < len(code) - 1:
        w = struct.unpack('>H', code[p:p + 2])[0]
        if w == 0x4e75: return False
        if w == 0x4a39 and code[p + 2:p + 6] == bytes.fromhex('00016fb2'): return True
        p += 2
    return False

def main():
    tot = collections.Counter(); ex = []; bad = []; xs = []
    for fn in sys.argv[1:]:
        d = json.load(open(fn)); code = bytes.fromhex(d['code'])
        tabs = {k: struct.unpack('>16H', bytes.fromhex(d['tab_' + k])) for k in ('16f72', '16f92', 'ce9a')}
        t24488 = struct.unpack('>10L', bytes.fromhex(d['table_24488']))
        tabname = {0x16f92: '16f92', 0x16f72: '16f72', 0xce9a: 'ce9a'}
        colr = {}
        for fr in d['frames']:
            screen = bytes.fromhex(fr['screen']); cover = collections.defaultdict(list); order = 0
            model_after = {}      # bucket -> list-order index of its last model record (ship, actors, landscape models)
            for b in range(10):
                bb = bytes.fromhex(fr['buckets'][b]); p = 0; k = 0
                while p < len(bb):
                    r = struct.unpack('>L', bb[p:p + 4])[0]
                    sz = {0x26222: 32, 0x261d2: 32, 0x26278: 14, 0x2620e: 4, 0x22a64: 16}.get(r, 8)
                    if sz != 8: model_after[b] = p
                    p += sz
            for b in list(range(9, 0, -1)) + [0]:       # draw order: far to near
                bb = bytes.fromhex(fr['buckets'][b]); p = 0
                tab = tabs[tabname[t24488[b]]]
                while p < len(bb):
                    r = struct.unpack('>L', bb[p:p + 4])[0]
                    if r in (0x26222, 0x261d2): p += 32; continue
                    if r == 0x26278: p += 14; continue
                    if r == 0x2620e: p += 4; continue
                    if r == 0x22a64: p += 16; continue
                    sx, sy = struct.unpack('>2h', bb[p + 4:p + 8]); p += 8
                    if r not in colr: colr[r] = routine_colour(code, 0x16fb4, r)
                    if colr[r] is None or r == 0x173b4: continue
                    if not (0 <= sx < 0x140 and 0 <= sy < 0xb7): continue
                    m = tab[sx & 15]
                    for rr in range(2 if (b <= 4 and routine_two_rows(code, 0x16fb4, r)) else 1):
                        yy = sy + rr
                        if yy >= 200: continue
                        for bit in range(16):
                            if m & (0x8000 >> bit):
                                cover[((sx & ~15) + bit, yy)].append((order, b, r, colr[r], sx, sy, rr)); 
                    order += 1
            for (x, y), lst in cover.items():
                cols = [e[3] for e in lst]
                if len(set(cols)) < 2: continue
                base = y * 160 + (x >> 4) * 8
                pl = [struct.unpack('>H', screen[base + 2 * i:base + 2 * i + 2])[0] for i in range(4)]
                col = sum(((pl[i] >> (15 - (x & 15))) & 1) << i for i in range(4))
                tot['pixels_with_2plus_colours'] += 1
                last = cols[-1]; first = cols[0]
                if lst[-1][1] != lst[0][1] and last != first:          # first and last dot in different buckets
                    tot['cross-bucket pixels (far dot then nearer dot, colours differ)'] += 1
                    tot['  screen == nearer (later) dot'] += col == last
                    tot['  screen == farther (earlier) dot (control)'] += col == first
                    if col == last and 0 not in (last, first) and len(xs) < 3: xs.append((fn.split('/')[-1], x, y, [(e[1], hex(e[2]), e[3], e[4], e[5]) for e in lst], col))
                tot['screen == last dot'] += col == last
                tot['screen == first dot (control)'] += col == first and first != last
                tot['screen == neither (overdrawn by tile/model or later dot not modelled)'] += col != last
                if col != last:
                    lb = lst[-1][1]
                    tot['  of those: a model record sits in the last dot bucket or a nearer one'] += any(b2 <= lb for b2 in model_after)
                if col == last and len(ex) < 3: ex.append((fn.split('/')[-1], x, y, lst, col))
                if col != last and len(bad) < 400: bad.append((x, y, [(o, b, hex(r), c, sx, sy, rr) for o, b, r, c, sx, sy, rr in lst], col))
    for k, v in tot.items(): print(f'{k:80s} {v}')
    for e in xs: print('example', e)
    if os.environ.get('SHOWBAD'):
        for e in bad[:int(os.environ['SHOWBAD'])]: print(e)
main()

import os
if os.environ.get('SHOWBAD'):
    pass
