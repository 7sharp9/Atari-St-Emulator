"""Gate: the per-object update pass $125e0 (types dispatched through the longword table $12dde) against the Python
model objpass.py.  Two corpora from the g_game1 snapshot:
  poked : one crafted record in pool slot 0 (472(A6) = 1), random type among the 25 types that have code, random
          fields, random player state and RNG state, N cases per type;
  natural: the unmodified full pass (107 records) at the g_game1 and g_game2 snapshots.
The model never sees callcap's output; the live final RAM (base + poked bytes + callcap delta) is compared over the
tracked regions (pool slots 0..11, free list $94c.., the A6 fields the pass writes).
    python3 reversing/starglider/py/objects/objpass_gate.py [N per type] [--break] [--type T]
Prints 'poked a/b', per-type match counts, 'natural a/b' and the branch coverage."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import objlib as ol
from objlib import A6, Mem
import objpass

BREAK = '--break' in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith('--')]
NPER = int(args[0]) if args else 12
ONLY = None
if '--type' in sys.argv: ONLY = int(sys.argv[sys.argv.index('--type') + 1])
POOL = A6 + 4762
TYPES = [1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 21, 23, 24, 25, 26, 27, 32, 33]

def tracked():
    rs = [(A6 + 92, A6 + 108), (A6 + 156, A6 + 160), (A6 + 196, A6 + 200), (A6 + 462, A6 + 466), (A6 + 520, A6 + 522),
          (A6 + 538, A6 + 540), (A6 + 578, A6 + 580), (A6 + 604, A6 + 606), (A6 + 608, A6 + 610), (A6 + 630, A6 + 632),
          (A6 + 636, A6 + 638), (A6 + 640, A6 + 642), (A6 + 726, A6 + 727), (POOL, POOL + 12 * 0x40), (0x94c, 0x94c + 44)]
    return rs
def in_tracked(a): return any(lo <= a < hi for lo, hi in tracked())

def craft(base, rnd, t):
    """returns (pokes [(addr, long)], preset D0)"""
    m = base
    px, py, pz = m.rw(A6 + 302), m.rw(A6 + 304), m.rw(A6 + 306)
    P = {}   # byte pokes
    def pw(a, v): P[a] = (v >> 8) & 0xff; P[a + 1] = v & 0xff
    def pb(a, v): P[a] = v & 0xff
    o = POOL
    for i in range(0x40): P[o + i] = 0
    pw(o, t); pb(o + 2, rnd.choice([0, 0, 1, 0xff]))
    cls = rnd.choice(['near', 'near', 'mid', 'far', 'vfar'])
    rng = {'near': 0x3a0, 'mid': 0x500, 'far': 0x900, 'vfar': 0x4000}[cls]
    dx = rnd.randint(-rng, rng); dz = rnd.randint(-rng, rng)
    if dx == 0 and dz == 0: dx = 5
    if dx == 0: dx = 1
    pw(o + 4, px + dx); pw(o + 8, pz + dz); pw(o + 6, rnd.choice([0xf95c, 0xff9c, 0xfe0c, 0, py + rnd.randint(-300, 300)]))
    pw(o + 10, rnd.choice([0, 0x40, 0x7c0, rnd.getrandbits(12)])); pw(o + 12, rnd.getrandbits(12)); pw(o + 14, rnd.getrandbits(16))
    pw(o + 16, rnd.choice([0x10, 0x40, 0xfed4, 0xff38, 0x19, rnd.randint(-0x200, 0x200)]))
    pw(o + 20, rnd.choice([0, 1, 2, 5, 0x7d0, rnd.randint(0, 0x80)])); pw(o + 22, rnd.choice([0, 1, 0xfff1, 0x64, rnd.randint(-40, 40)]))
    pw(o + 24, rnd.randint(0, 0x7f)); pw(o + 28, rnd.randint(-30, 30)); pw(o + 32, rnd.randint(-30, 30))
    pb(o + 34, rnd.choice([0, 1, 0xff, 0xff])); pb(o + 35, rnd.choice([0, 0xff, 0xff]))
    if rnd.random() < 0.15: pb(o + 36, 0xff); pw(o + 38, rnd.choice([0, 5, 0x1e, 0x1f, 0x1f]))
    pw(o + 44, rnd.choice([0, 0x300, 0x500, 0x700, 0xf000, 0xf900, rnd.getrandbits(16)]))
    pw(o + 40, rnd.randint(-500, 500)); pw(o + 42, rnd.randint(-500, 500))
    pb(o + 46, rnd.choice([0, 0xff])); pw(o + 48, rnd.randint(0, 5))
    # globals
    pw(A6 + 472, 1)
    pb(A6 + 711, rnd.choice([0xff, 0xff, 0xff, 0])); pb(A6 + 712, rnd.choice([0, 0, 0, 0xff])); pb(A6 + 714, rnd.choice([0, 0, 0, 0xff]))
    pw(A6 + 662, rnd.choice([1, 1, 2, 3, 4, 5])); pw(A6 + 664, rnd.choice([0, 0, 0, 5])); pw(A6 + 632, rnd.choice([0, 1, 2]))
    pw(A6 + 608, rnd.choice([0x100, 0x5000, 0xffff, rnd.getrandbits(16), 0x3a99])); pw(A6 + 640, rnd.randint(-50, 50))
    pb(A6 + 726, rnd.choice([0, 0xff])); pw(A6 + 578, 0)
    cnt = rnd.choice([0, 1, 3, 10]); pw(A6 + 604, cnt)
    slots = list(range(1, 11)); rnd.shuffle(slots)
    for i in range(10):
        a = 0x94c + 4 * i
        for k, b in enumerate((POOL + 0x40 * slots[i]).to_bytes(4, 'big')): P[a + k] = b
    for k, b in enumerate((0x94c + 4 * cnt).to_bytes(4, 'big')): P[A6 + 156 + k] = b
    # RNG state: rejection-sample so the next $f21e draw has the low bits the branch under test needs
    mask = rnd.choice([0, 0x7f, 0x7f, 0xf, 0x7, 0x3, 0x1f, 0x3f, 0x7ff, 0x3f])
    c3 = rnd.getrandbits(16); a92 = rnd.getrandbits(32)
    while True:
        S = rnd.getrandbits(32)
        t2 = (S << 1) & 0xffffffff
        if (S >> 31) or t2 == 0: t2 ^= 0x1d872b41
        t2 = (t2 & 0xffff0000) | (((t2 & 0xffff) + c3) & 0xffff)
        t2 = (t2 + a92) & 0xffffffff
        if ((t2 >> 16) & mask) == 0: break
    for k, b in enumerate(S.to_bytes(4, 'big')): P[A6 + 100 + k] = b
    for k, b in enumerate(a92.to_bytes(4, 'big')): P[A6 + 92 + k] = b
    P[A6 + 96] = rnd.getrandbits(8); P[A6 + 97] = rnd.getrandbits(8)
    pw(0xc3ce, c3)
    pw(A6 + 305 - 1, py)   # keep the player's y
    return P, rnd.getrandbits(32)

poke_lines = ol.poke_lines

def apply(mem, P):
    for a, v in P.items(): mem.wb(a, v)

def compare(model_mem, live_mem):
    bad = []
    for lo, hi in tracked():
        for a in range(lo, hi):
            if model_mem.rb(a) != live_mem.rb(a): bad.append(a)
    return bad

def run_cases(snap, base, cases, label):
    lines = []
    for P, d0, tag in cases:
        lines += poke_lines(P)
        lines.append('callcap 125e0 400000 A6=%x D0=%x' % (A6, d0))
    out = ol.repl_run(snap, lines)
    return ol.parse_callcaps(out)

def main():
    rnd = random.Random(1986)
    snap = ol.sg.SNAP_GAME1
    base = Mem(ol.sg.load_ram(snap))
    types = TYPES if ONLY is None else [ONLY]
    cases = []
    for t in types:
        for k in range(NPER): cases.append(craft(base, rnd, t) + (t,))
    ccs = run_cases(snap, base, cases, 'poked')
    assert len(ccs) == len(cases), (len(ccs), len(cases))
    per = {}; ok = 0; vis = {}; untracked = set(); bads = []
    # pokes accumulate in the live REPL (callcap rolls back, pokes persist): replay them in order on a copy
    live_base = base.copy()
    for (P, d0, t), cc in zip(cases, ccs):
        apply(live_base, P)
        model = live_base.copy(); live = live_base.copy()
        sim = objpass.Sim(model, d0, break_model=BREAK)
        try:
            sim.run()
        except AssertionError as e:
            bads.append((t, 'assert ' + str(e))); per.setdefault(t, [0, 0])[1] += 1; continue
        for a, (o, n) in cc['mem'].items():
            live.wb(a, n)
            if not in_tracked(a) and not (0x60000 <= a < 0x80000): untracked.add(a)
        bad = compare(model, live)
        per.setdefault(t, [0, 0]); per[t][1] += 1
        if not bad: ok += 1; per[t][0] += 1
        else:
            bads.append((t, [hex(a) for a in bad[:6]]))
            if '--dbg' in sys.argv and len(bads) < 3:
                print('DBG type', t, 'visited', sorted(sim.visited), 'rec', ' '.join('%02x' % live_base.rb(POOL+i) for i in range(0x40)), 'glob', {n: hex(live_base.rl(A6+n)) for n in (100,92,711,712,714,662,604)}, 'model100', hex(model.rl(A6+100)), 'live100', hex(live.rl(A6+100)), 'c3ce', hex(live_base.rw(0xc3ce)), 'px', hex(live_base.rw(A6+302)), hex(live_base.rw(A6+306)))
        vis.setdefault(t, set()).update(sim.visited)
    print('poked %d/%d' % (ok, len(cases)))
    print(' per type:', ' '.join('%d:%d/%d' % (t, v[0], v[1]) for t, v in sorted(per.items())))
    print(' mismatches (first 8):', bads[:8])
    print(' untracked non-video bytes changed by callcap: %d, range %s..%s (stack)' % (len(untracked), hex(min(untracked)) if untracked else '-', hex(max(untracked)) if untracked else '-'))
    allv = set().union(*vis.values()) if vis else set()
    print(' branch labels reached (%d): %s' % (len(allv), ' '.join(sorted(allv))))
    # natural
    for sn in (ol.sg.SNAP_GAME1, ol.sg.SNAP_GAME2):
        b = Mem(ol.sg.load_ram(sn))
        # D0 at the call is whatever the snapshot holds; take it from the first callcap's register delta line
        out = ol.repl_run(sn, ['callcap 125e0 2000000 A6=%x' % A6])
        cc = ol.parse_callcaps(out)[0]
        live = b.copy(); model = b.copy()
        for a, (o, n) in cc['mem'].items(): live.wb(a, n)
        sim = objpass.Sim(model, 0, break_model=BREAK); sim.run()
        bad = compare(model, live)
        print('natural %s: changed bytes live=%d, tracked mismatches=%d' % (os.path.basename(sn), len(cc['mem']), len(bad)))
def natural_hits():
    import json
    jp = ol.sg.work('objects', 'nat', 'o125.json')
    if not os.path.exists(jp):
        print('natural hits: %s missing; build it with' % jp)
        print('  python3 tools/capture_hits.py scratchpad/starglider/drive/g_game1.snap 125e0 1,2,3,5,8,13,21,34,55,89,144 scratchpad/starglider/objects/nat --name o125')
        return
    ent = json.load(open(jp)); good = 0; changed = 0
    for e in ent:
        sn = e['snap']; sn = sn if os.path.isabs(sn) else os.path.join(ol.ROOT, sn)
        b = Mem(ol.sg.load_ram(sn))
        regs = e['regs']
        out = ol.repl_run(sn, ['callcap 125e0 2000000 A6=%x D0=%x' % (A6, regs['D0'])])
        cc = ol.parse_callcaps(out)[0]
        live = b.copy(); model = b.copy()
        for a, (o, n) in cc['mem'].items(): live.wb(a, n)
        changed += len(cc['mem'])
        sim = objpass.Sim(model, regs['D0'], break_model=BREAK); sim.run()
        good += not compare(model, live)
    print('natural hits %d/%d (changed bytes summed %d)' % (good, len(ent), changed))
main()
natural_hits()
