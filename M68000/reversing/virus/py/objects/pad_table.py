"""Launch-pad colour table $246ba: the model, the reader trace and the on-screen recolour test.

    uv run python pad_table.py model   <snap>                 # who references the table (raw scan of the code), the table bytes
    uv run python pad_table.py reads   <snap> <frames>        # bp at the two reads ($245ae, $24726): D3 after the read vs the model
    uv run python pad_table.py writes  <snap> <frames>        # write watch over the table across <frames> frames (control: ship state)
    uv run python pad_table.py screen  <snap> <out_dir>       # poke one table byte, render, diff: which tile changes

Model: $24754 / $245b8 with D6 = x and D7 = z below $900 (the 9 x 9 cell pad) return height $420 and the tile type
D3 = T[(((D7 << 3) & $fc00) + D6) >> 8]  (16-bit words).  At a cell corner (x = 256 k, z = 256 j) that is T[8 j + k].
"""
import struct
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import vcommon
from vcommon import ROOT, WORK, work
from stclient import StServer
T0 = 0x246ba

def model_index(x, z):
    return ((((z << 3) & 0xfc00) + x) & 0xffff) >> 8

def hx(v): return int(str(v).lstrip('$'), 16)

def s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v

def cmd_model(snap):
    r = vcommon.load_ram(snap)
    lo, hi = T0, 0x24706
    # raw scan: every aligned word / long in the code region $c000..$27000 equal to an address in the table, and
    # every PC-relative displacement (lea d16(PC), An = opcode 0x41fa | An<<9) that lands in it
    hits = []
    for a in range(0xc000, 0x27000, 2):
        w = struct.unpack('>H', r[a:a + 2])[0]
        if a + 4 <= 0x27000:
            l = struct.unpack('>I', r[a:a + 4])[0]
            if lo <= (l & 0xffffff) < hi and a % 2 == 0 and (l >> 24) == 0:
                hits.append(('abs.l', a, l))
        if (w & 0xf1ff) == 0x41fa:
            disp = s16(struct.unpack('>H', r[a + 2:a + 4])[0]); tgt = a + 2 + disp
            if lo <= tgt < hi: hits.append(('lea pc', a, tgt))
        if (w & 0xf1ff) == 0x41f9 and False: pass
    print('references to $%x..$%x:' % (lo, hi - 1), [(k, hex(a), hex(v)) for k, a, v in hits])
    T = r[lo:hi]
    print('bytes $246ba..$24705 (%d):' % len(T), T.hex(' '))
    print('values:', sorted(set(T[:75])), ' last two bytes of the 75:', T[73:75].hex(), ' $24705 =', hex(r[0x24705]), ' code starts at $24706:', r[0x24706:0x24710].hex(' '))

def cmd_reads(snap, frames):
    s = StServer(ROOT)
    try:
        s('load', snapshot=snap)
        r = vcommon.load_ram(snap)
        T = r[T0:T0 + 76]
        s('bp_set', addrs=[0x245ae, 0x24726])
        ok = ok_ctl = n = 0; seen = {}; idxs = set(); ok_rm = 0
        last = None
        for _ in range(frames * 8):
            r_ = s('run', max_steps=400000)
            if r_['reason'] != 'breakpoint':
                if r_['reason'] == 'max_steps': continue
                break
            pc = hx(r_['pc'])
            regs = s('regs')
            d6, d7 = hx(regs['d6']) & 0xffff, hx(regs['d7']) & 0xffff
            a0 = hx(regs['a0'])
            if not (d6 < 0x900 and d7 < 0x900): continue
            idx = model_index(d6, d7)
            d3b = hx(regs['d3']) & 0xffff                  # the index the code computed, before the read
            s('step', n=1)
            d3 = hx(s('regs')['d3']) & 0xff
            n += 1; ok += (d3 == T[idx]) and (d3b == idx); ok_ctl += (d3 == T[idx + 1]) if idx + 1 < len(T) else 0
            idxs.add(idx); ok_rm += d3 == T[min(75, 9 * (d7 >> 8) + (d6 >> 8))]
            seen[(pc, a0 == T0)] = seen.get((pc, a0 == T0), 0) + 1
        print(f'pad-region reads: {n}; index in D3 == model index and the byte read == T[index]: {ok}/{n}; distinct indices {len(idxs)}; controls: index + 1 {ok_ctl}/{n}, row-major 9 x 9 (9 j + k) {ok_rm}/{n}; by (pc, A0 == $246ba): {seen}')
    finally:
        s.close()

def cmd_writes(snap, frames):
    s = StServer(ROOT)
    try:
        s('load', snapshot=snap)
        w = s('watch_add', lo=T0, hi=0x24705, kind='w', source='cpu', max_events=1000)['id']
        c = s('watch_add', lo=0x270b0, hi=0x270bb, kind='w', source='cpu', max_events=100000)['id']
        steps = 0
        while steps < frames * 30000:
            r = s('run', max_steps=3000000); steps += r['steps']
            if r['reason'] not in ('max_steps',): print('stopped', r['reason']); break
        ev = s('watch_events', id=w); ec = s('watch_events', id=c)
        L = lambda e: [x for o in (e if isinstance(e, list) else [e]) for x in o.get('events', [])]
        print(f'steps {steps}: writes to $246ba..$24704: {len(L(ev))}; control, writes to the ship state $270b0..$270bb: {len(L(ec))}')
    finally:
        s.close()

def frame(snap, pokes, path, nframes=7):
    s = StServer(ROOT)
    try:
        s('load', snapshot=snap)
        s('bp_set', addrs=[0x255c2])
        for a, v in pokes:
            s('poke', addr=a, width=1, value=v)               # labelled poke: one pad-table byte
        for _ in range(nframes + 1):
            r = s('run', max_steps=3000000); assert r['reason'] == 'breakpoint', r
        s('render', path=path)
        # the grid builder's arrays from the frame just drawn (README "Grid and projection"): types, 26 bytes a row
        # down from $276e0, vertices (sx, sy), 52 bytes a row down from $2758c
        return s.read(0x276e0 - 260, 260), s.read(0x2758c - 520, 520), s.read(0x270ce, 6)
    finally:
        s.close()

def cmd_screen(snap, out):
    import numpy as np
    from PIL import Image
    os.makedirs(out, exist_ok=True)
    r = vcommon.load_ram(snap); T = r[T0:T0 + 76]
    base = os.path.join(out, 'pad_base.png')
    ty0, vx0, cam = frame(snap, [], base)
    A = np.array(Image.open(base).convert('RGB')).astype(int)
    tyw = lambda ty, row, col: struct.unpack('>H', ty[260 - 26 * row - 2 * (col + 1):][:2])[0]
    vtx = lambda vx, row, col: struct.unpack('>2H', vx[520 - 52 * row - 4 * (col + 1):][:4])
    print('camera after the run', cam)
    offs = []; corners = []
    for (k, j) in [(2, 2), (5, 2), (3, 4), (6, 4), (2, 6), (5, 6), (4, 3), (7, 5), (1, 4), (4, 7), (3, 1), (6, 7)]:
        i = 8 * j + k
        new = 15 if T[i] != 15 else 4
        pth = os.path.join(out, f'pad_{k}_{j}.png')
        ty1, vx1, _ = frame(snap, [(T0 + i, new)], pth)
        B = np.array(Image.open(pth).convert('RGB')).astype(int)
        m = (A != B).any(axis=2); m[:14] = False
        ys, xs = np.nonzero(m)
        ch = [(row, col) for row in range(10) for col in range(11) if tyw(ty0, row, col) != tyw(ty1, row, col)]
        if len(ch) != 1 or not len(xs):
            print(f'vertex ({k},{j}) T[{i}] {T[i]} -> {new}: changed type words {ch}, {int(m.sum())} px'); continue
        row, col = ch[0]
        cx, cy = xs.mean(), ys.mean()
        # which of the four tiles round that grid vertex holds the centroid (tile (r, c) = quad (r,c) (r,c+1) (r+1,c+1) (r+1,c))
        hit = None
        for tr in (row - 1, row):
            for tc in (col - 1, col):
                if not (0 <= tr < 9 and 0 <= tc < 10): continue
                q = [vtx(vx0, tr, tc), vtx(vx0, tr, tc + 1), vtx(vx0, tr + 1, tc + 1), vtx(vx0, tr + 1, tc)]
                sg = [(q[(u + 1) % 4][0] - q[u][0]) * (cy - q[u][1]) - (q[(u + 1) % 4][1] - q[u][1]) * (cx - q[u][0]) for u in range(4)]
                if all(v >= 0 for v in sg) or all(v <= 0 for v in sg): hit = (tr - row, tc - col)
        offs.append((row - 0, col - 0, k, j)); corners.append(hit)
        print(f'vertex ({k},{j}) T[{i}] {T[i]} -> {new}: one type word changed, grid (row {row}, col {col}); {int(m.sum())} px changed, centroid ({cx:.0f},{cy:.0f}); tile holding it, relative to the grid vertex: {hit}')
    from collections import Counter
    print('grid (row - j, col - k):', Counter((o[0] - o[3], o[1] - o[2]) for o in offs))
    print('tile corner relative to the poked vertex (None = centroid in none of the four):', Counter(corners))

if __name__ == '__main__':
    c = sys.argv[1]; snap = os.path.abspath(sys.argv[2])
    {'model': lambda: cmd_model(snap), 'reads': lambda: cmd_reads(snap, int(sys.argv[3])), 'writes': lambda: cmd_writes(snap, int(sys.argv[3])), 'screen': lambda: cmd_screen(snap, sys.argv[3])}[c]()
