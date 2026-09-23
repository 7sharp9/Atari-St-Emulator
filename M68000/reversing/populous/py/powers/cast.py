"""cast.py - cast each power through the game's own UI (popdrive clicks) and diff the real
routine's net effect against powers_ref.

For each cast: resume a base snapshot, poke side_mana (and, where stated, the RNG seed at the
routine's entry), move the pointer to the icon, press, `bp <routine>` (entry snapshot),
`u <exit>` (exit snapshot), release, run on. The model runs on the entry RAM with the arguments
read from the entry stack; the comparison covers every game-state map and record (REGIONS).

usage: python cast.py [name ...]      names: flood earthquake volcano volcano_good swamp knight armageddon
Snapshots go to $POP_WORK/powers/snaps/<name>_{entry,exit,after}.snap.
"""
import os, re, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pwlib import *
import powers_ref as P
from popdrive import Game, move_lines, icon_point, screen_of_uv, classify

SN = os.path.join(PD, 'snaps')
REGIONS = [(P.HGT, 65 * 65 * 2, 'heights'), (P.ALT, 4096, 'alt'), (P.SHAPE, 4096, 'shape'),
           (P.FEAT, 4096, 'feature'), (P.OCC, 4096, 'occupant'), (P.VISIT, 8192, 'visits'),
           (P.ENT, 0x16 * 211, 'entities'), (P.SIDE, 32, 'side_state'), (P.GOD, 0x5c, 'god_recs'),
           (P.SEED, 2, 'seed'), (P.SCORE, 4, 'score'), (P.SOUND, 2, 'sound'), (P.POINTS, 2, 'points'),
           (P.ARMA, 2, 'armageddon'), (0x3c4ca, 2, 'magnet0'), (0x3d526, 2, 'magnet1'),
           (P.QUERY, 2, 'query'), (0x3c514, 4, 'battles'), (P.NENT, 2, 'count')] + \
          [(b, 2, 'box') for b in P.BOX]

ROUT = {'flood': (0x11f6a, 0x120c2), 'earthquake': (0x12350, 0x12638), 'volcano': (0x1263c, 0x129d2),
        'swamp': (0x12a14, 0x12b9c), 'knight': (0x12ba0, 0x12d22), 'armageddon': (0x12d26, 0x12e02)}


def minimap_click_for_origin(ox, oy):
    """screen point of a minimap click that sets the view origin to (ox, oy) ($c3e2: (u-3, v-3))."""
    u, v = ox + 3, oy + 3
    assert (u + v) % 2 == 0, 'origin parity: u+v must be even'
    x, y = screen_of_uv(u, v)
    assert classify(x, y) == ('minimap', (u, v)), (x, y, classify(x, y))
    return x, y


def regs_after(out, marker):
    i = out.rindex(marker)
    return {k: int(v, 16) for k, v in re.findall(r'\b([DA][0-7]|PC):\s*([0-9a-f]{8})', out[i:i + 600])}


def compare(pre, post, model):
    res = {}
    for a, n, name in REGIONS:
        diff = [k for k in range(a, a + n) if post[k] != model[k]]
        chg = [k for k in range(a, a + n) if post[k] != pre[k]]
        r = res.setdefault(name, [0, 0, 0])
        r[0] += n - len(diff); r[1] += n; r[2] += len(chg)
    return res


def cast(name, base, power, click, pokes=(), entry_pokes=(), after_steps=12 * 120000):
    """click = list of REPL lines up to (and including) the 'mouse down' that fires the power."""
    os.makedirs(SN, exist_ok=True)
    ent, ex = ROUT[power]
    fe, fx, fa = [os.path.join(SN, '%s_%s.snap' % (name, k)) for k in ('entry', 'exit', 'after')]
    for f in (fe, fx, fa):
        if os.path.exists(f): os.remove(f)
    from repl import Repl
    r = Repl2(os.path.join(WORK, base))
    try:
        for c in list(pokes) + click:
            r.cmd(c)
        out, rg = r.cmd('bp %x 3000000' % ent)
        if not any(('breakpoint $%08x hit' % ent) in l for l in out):
            raise RuntimeError('power routine not reached: ' + ' | '.join(out[-20:]))
        for f in entry_pokes:
            f(r)
        r.cmd('snap ' + fe)
        r.cmd('u %x 6000000' % ex)
        r.cmd('snap ' + fx)
        for c in ('mouse up l', 'mouse up r', 's %d' % after_steps, 'snap ' + fa):
            r.cmd(c)
    finally:
        r.close()
    pre, post = bytearray(ram(fe)), ram(fx)
    a7 = rg['A7']
    side, x, y = P.rw(pre, a7 + 4), P.rw(pre, a7 + 6), P.rw(pre, a7 + 8)
    mm = bytearray(pre)
    sys.setrecursionlimit(100000)
    {'flood': lambda: P.flood(mm, side), 'earthquake': lambda: P.earthquake(mm, side, x, y),
     'volcano': lambda: P.volcano(mm, side, x, y), 'swamp': lambda: P.swamp(mm, side, x, y),
     'knight': lambda: P.knight(mm, side), 'armageddon': lambda: P.armageddon(mm, side)}[power]()
    if power == 'earthquake':
        # the 20 shake frames run the VBL handler, which consumes the sound request: $16d5a..$16d6c
        # moves $36d02-$42 to $24954 and clears $36d02 (sound on, $21920). $2287a ends where it began.
        assert P.rw(post, 0x24954) == P.rw(mm, P.SOUND) - 0x42 and P.rl(post, P.VIEWOFF) == P.rl(pre, P.VIEWOFF)
        P.ww(mm, P.SOUND, 0)
    res = compare(pre, post, mm)
    tot = sum(r[0] for r in res.values()), sum(r[1] for r in res.values())
    changed = {k: r[2] for k, r in res.items() if r[2]}
    print('%-13s %-10s side %d arg (%d,%d) seed %04x mana %d->%d  match %d/%d bytes  changed %s' % (
        name, power, side, x, y, P.ruw(pre, P.SEED), P.rl(pre, P.mana_a(side)), P.rl(post, P.mana_a(side)),
        tot[0], tot[1], changed))
    bad = {k: r for k, r in res.items() if r[0] != r[1]}
    if bad:
        print('   MISMATCH', bad)
    return pre, post, mm, (side, x, y), out


def icon_click(g, name, button='l'):
    x, y = icon_point(name)
    return move_lines(g.px, g.py, x, y) + ['s 240000', 'mouse down %s' % button], (x, y)


def scroll_then_icon(g, origin, icon):
    mx, my = minimap_click_for_origin(*origin)
    L = move_lines(g.px, g.py, mx, my) + ['s 240000', 'mouse down l', 's 240000', 'mouse up l', 's 240000']
    x, y = icon_point(icon)
    return L + move_lines(mx, my, x, y) + ['s 240000', 'mouse down l']


def swamp_click(g, cell):
    """arm the swamp icon, then click the land corner (cx+1, cy+1) -> cmd 4 at cell (cx, cy)."""
    x, y = icon_point('swamp')
    L = move_lines(g.px, g.py, x, y) + ['s 240000', 'mouse down l', 's 240000', 'mouse up l', 's 240000']
    pt = g.best_point_for_corner(cell[0] + 1, cell[1] + 1)
    assert pt, 'corner not clickable in this view'
    return L + move_lines(x, y, pt[0], pt[1]) + ['s 240000', 'mouse down l']


MANA = 'w 3b232 %08x' % 200000


def main():
    names = sys.argv[1:] or ['flood', 'earthquake', 'volcano', 'volcano_good', 'swamp', 'knight', 'armageddon']
    A = os.path.join(WORK, 'drive', 'A.snap')
    g = Game(ram(A))
    for n in names:
        if n in ('flood', 'earthquake', 'knight', 'armageddon'):
            L, _ = icon_click(g, n)
            cast(n, 'drive/A.snap', n, L, [MANA])
        elif n == 'volcano':
            # view origin (52,50): cells 52..59 x 50..57 hold evil's leader, entity 5 at (56,55).
            # The seed is set at the routine's entry to one where the rock draw hits (56,55).
            seed = find_seed(A, 52, 50, (56, 55))
            L = scroll_then_icon(g, (52, 50), 'volcano')
            cast(n, 'drive/A.snap', 'volcano', L, [MANA], [set_seed(seed)])
        elif n == 'volcano_good':
            # view (6,12) holds good's leader, entity 2 at (9,13): seed chosen so the draw hits it
            seed = find_seed(A, 6, 12, (9, 13))
            L, _ = icon_click(g, 'volcano')
            cast(n, 'drive/A.snap', 'volcano', L, [MANA], [set_seed(seed)])
        elif n == 'swamp':
            # GENESIS has almost no flat land near the human's towns (best 7x7 window: 4 eligible
            # cells), so the state is prepared first: corners (6..13, 12..19) set to height 1 and the
            # cells re-derived with the $c0ee model (a legal, self-consistent plateau of $0f cells).
            m0 = ram(A); m1 = bytearray(m0)
            for cy in range(12, 20):
                for cx in range(6, 14):
                    P.ww(m1, P.HGT + 2 * (cx + 65 * cy), 1)
            P.derive_cells(m1, 5, 11, 13, 19)
            pk = poke_lines(m0, m1)
            cell = (9, 15)
            cast(n, 'drive/A.snap', 'swamp', swamp_click(Game(bytes(m1)), cell), [MANA] + pk)


def poke_lines(m0, m1):
    return ['w %x %08x' % (a, struct.unpack_from('>I', m1, a)[0])
            for a in range(0x21464, 0x3d560, 4) if m0[a:a + 4] != m1[a:a + 4]]


def set_seed(seed):
    """entry poke: replace only the seed word $3d52e (the REPL `w` writes a long)."""
    def f(r):
        hi = r.mem(0x3d52c, 2)
        r.cmd('w 3d52c %08x' % ((int.from_bytes(hi, 'big') << 16) | seed))
    return f


def find_seed(snap, ox, oy, cell):
    """a seed whose volcano on the entry state puts a rock draw (rand%5==0) on `cell`
    (ignoring the protection test), found by running the model."""
    m0 = bytearray(ram(snap))
    target = cell[0] + 64 * cell[1]
    for s in range(1, 0x8000):
        mm = bytearray(m0)
        P.ww(mm, P.SEED, s); P.ww(mm, P.PAINT, 1)
        for k in range(5):
            for i in range(k, 9 - k):
                for j in range(k, 9 - k):
                    P.rand(mm)
        hit = False
        for cx in range(ox, ox + 8):
            for cy in range(oy, oy + 8):
                if 0 <= cx < 64 and 0 <= cy < 64:
                    r = P.rand(mm) % 5
                    if cx + 64 * cy == target:
                        hit = r == 0
        if hit:
            return s
    raise ValueError


def best_swamp_cell(g, m):
    ox, oy = g.view
    best = None
    for cy in range(oy + 3, oy + 6):
        for cx in range(ox + 3, ox + 6):
            n = sum(1 for dy in range(-3, 4) for dx in range(-3, 4)
                    if P.rb(m, P.SHAPE + cx + dx + 64 * (cy + dy)) in (0x0f, 0x1f, 0x20, 0x42))
            if g.best_point_for_corner(cx + 1, cy + 1) and (best is None or n > best[0]):
                best = (n, (cx, cy))
    return best[1]


if __name__ == '__main__':
    main()
