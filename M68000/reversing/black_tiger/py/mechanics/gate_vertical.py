"""Gate: player_model.step_vertical ($d7b0) vs callcap $d7b0 on random player states in the level-1 map.
Usage: gate_vertical.py [N=300] [seed=1]     (labelled pokes: the whole state block below, per case)"""
import os, random, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import btlib as b, player_model as pm

N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
snap = os.path.join(b.WORK, "play_start.snap")
base = bytearray(b.ram_from_snap(snap))
m0 = pm.Mem(base)
W = m0.rw(0x1effe)
cells = {1: [], 2: [], 0: []}
for row in range(1, 50):
    for col in range(128):
        c, _ = pm.tile_class(m0, col * 16, row * 16)
        cells.setdefault(c, []).append((col, row))
REGIONS = [(0x1f000, 0x1f004), (0x1f010, 0x1f020), (0x17828, 0x17838), (0x1eecc, 0x1eed8), (0x1eff0, 0x1eff4)]
cases, lines = [], []
for k in range(N):
    st = bytearray(base)
    m = pm.Mem(st)
    r = random.random()
    cls = 3 if r < 0.06 else (1 if r < 0.45 else (2 if r < 0.7 else 0))
    col, row = random.choice(cells.get(cls) or cells[0])
    x = col * 16 + random.randrange(16)
    y = row * 16 + random.randrange(16) + random.choice((0, 0x10, 0x20))
    y = min(y, 50 * 16 - 1)       # stay inside the 50-row map (out-of-map reads are not modelled)
    m.wb(0x1f010, 0xff); m.ww(0x1f014, x); m.ww(0x1f016, y)
    m.ww(0x1f000, random.choice((0, 0, 1, 2, 3))); m.wb(0x1f011, random.choice((0, 1, 2, 3, 4, 5, 6, 8, 0xb)))
    m.wb(0x1f01e, random.choice((0, 2)))
    m.ww(0x17830, random.choice((0, 0, 1, 3, 6, 7))); m.ww(0x17832, random.randrange(10))
    m.ww(0x1782e, random.choice((0, 8, 0xfff8)))
    m.ww(0x1eed0, random.randrange(6)); m.wb(0x1eed6, random.choice((0, 4, 0x80, 0x84, 0x88)))
    m.ww(0x1eece, random.randrange(2)); m.wb(0x1eecf, random.randrange(2)); m.ww(0x1eff0, random.randrange(800))
    pre = bytearray(st)
    ev = pm.step_vertical(m)
    pred = {a: st[a] for a in range(0x17800, 0x20000) if st[a] != pre[a]}
    cases.append((pre, pred, ev))
    for lo, hi in REGIONS:
        for a in range(lo, hi, 4):
            lines.append("w %x %s" % (a, pre[a:a + 4].hex()))
    lines.append("callcap d7b0 400000")
out = b.repl(snap, lines)
blocks = re.split(r"(?=^--- callcap)", out, flags=re.M)[1:]
assert len(blocks) == N, (len(blocks), N)
ok = deaths = deaths_ok = 0
bad = []
for (pre, pred, ev), blk in zip(cases, blocks):
    got = {int(a, 16): int(v, 16) for a, v in re.findall(r"^mem \$([0-9a-f]+) \$[0-9a-f]+->\$([0-9a-f]+)", blk, re.M)
           if not (0x1ee00 <= int(a, 16) < 0x1ee50)}
    if ev:
        deaths += 1
        deaths_ok += (got.get(0x1f010) == 0)
        if got.get(0x1f010) != 0: print('death mismatch state', pre[0x1f000:0x1f004].hex(), pre[0x1f010:0x1f020].hex(), {hex(a):v for a,v in got.items() if 0x1f000<=a<0x1f040}, len(got))
        continue
    if got == pred: ok += 1
    else: bad.append((pred, got, pre[0x1f010:0x1f020].hex()))
print("cases %d: model==callcap byte-for-byte %d/%d; death branch cases %d (emulator cleared $1f010 in %d)" % (N, ok, N - deaths, deaths, deaths_ok))
for p, g, s in bad[:3]:
    print("MISMATCH state", s); print(" pred-only", {hex(a): v for a, v in p.items() if g.get(a) != v}); print(" got-only", {hex(a): v for a, v in g.items() if p.get(a) != v})
