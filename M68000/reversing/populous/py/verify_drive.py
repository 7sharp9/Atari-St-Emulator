"""verify_drive.py - prove popdrive's click model against the running game.

From game_start.snap: a minimap click must set the predicted view; a left click on corner
(11,16) must raise exactly what popgen.raise_pt predicts (134 corners); a right click must lower
as popgen.lower_pt; the magnet icon + a land click must move the papal magnet to cell (cx-1,cy-1);
and each icon click must change exactly the state the $c3e2 table predicts.
Snapshots go to $POP_WORK/drive/ or $POP_WORK/<argv[1]>/ (drive/A.snap = view (6,12), used by
other scripts)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.setrecursionlimit(100000)
from popdrive import Game, click_lines, plan_icon, plan_raise, run
from popmem import ram, l, sw, w
from popcfg import WORK
from popgen import Gen

D = os.path.join(WORK, sys.argv[1] if len(sys.argv) > 1 else 'drive'); os.makedirs(D, exist_ok=True)
S0 = os.path.join(WORK, 'game_start.snap'); A = os.path.join(D, 'A.snap')
ok = 0; total = 0


def check(name, cond, detail=''):
    global ok, total
    total += 1; ok += bool(cond)
    print('%-5s %-28s %s' % ('ok' if cond else 'FAIL', name, detail))


def heights(m): return [sw(m, 0x34be4 + 2 * i) for i in range(65 * 65)]


g = Game(ram(S0))
view, (mx, my) = g.view_for_corner(11, 16)
run(S0, click_lines(g.px, g.py, mx, my), A)
a = Game(ram(A))
check('minimap click', a.view == view, 'click (%d,%d) view %r' % (mx, my, a.view))

for btn, fn in (('l', 'raise_pt'), ('r', 'lower_pt')):
    out = os.path.join(D, '%s_11_16.snap' % fn)
    lines, info = plan_raise(a, 11, 16, btn)
    run(A, lines, out)
    H0, H1 = heights(ram(A)), heights(ram(out))
    gm = Gen(0); gm.h = list(H0); getattr(gm, fn)(11, 16)
    n = sum(H0[i] != H1[i] for i in range(65 * 65))
    check(fn + ' click', gm.h == H1, 'point %r: %d corners changed, model identical %s' % (info['point'], n, gm.h == H1))

run(A, plan_icon(a, 'ui_magnet')[0], os.path.join(D, 'mag0.snap'))
b = Game(ram(os.path.join(D, 'mag0.snap')))
run(os.path.join(D, 'mag0.snap'), click_lines(b.px, b.py, *b.best_point_for_corner(12, 17)), os.path.join(D, 'mag1.snap'))
m0, m1 = ram(os.path.join(D, 'mag0.snap')), ram(os.path.join(D, 'mag1.snap'))
check('magnet click', w(m1, 0x3b228) == 16 * 64 + 11 and w(m1, 0x21d50) == 2,
      'cell %d -> %d, mana %d -> %d' % (w(m0, 0x3b228), w(m1, 0x3b228), l(m0, 0x3b232), l(m1, 0x3b232)))


def st(m):
    return dict(mode=w(m, 0x3b22a), ui=w(m, 0x21d50), ptr=w(m, 0x2165c), view=(sw(m, 0x37e7a), sw(m, 0x249ae)),
                pause=w(m, 0x3b274), music=w(m, 0x21ffc), sfx=w(m, 0x21920))


base = st(ram(A))   # mode 1, ui 2, pointer 1, view (6,12), pause 0, music 1, sfx 1
EXPECT = {
    'mode_magnet': {'mode': 0}, 'mode_settle': {}, 'mode_gather': {'mode': 2}, 'mode_fight': {'mode': 3},
    'ui_query': {'ui': 1, 'ptr': 0}, 'ui_magnet': {'ui': 6, 'ptr': 2}, 'ui_land': {},
    'scroll_n': {'view': (6, 11)}, 'scroll_se': {'view': (7, 13)}, 'scroll_w': {'view': (5, 12)},
    'pause': {'pause': 1}, 'toggle_21ffc': {'music': 0}, 'toggle_21920': {'sfx': 0},
}
for name, exp in EXPECT.items():
    out = os.path.join(D, 'i_%s.snap' % name)
    run(A, plan_icon(a, name)[0], out)
    s = st(ram(out))
    got = {k: v for k, v in s.items() if v != base[k]}
    check('icon ' + name, got == exp, 'changed %r' % got)

print('%d/%d checks' % (ok, total))
