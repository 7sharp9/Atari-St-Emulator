"""HUD poke-and-render: which screen region does each global drive?
For every (name, address, width, value) below: resume g_game1, poke the global, run STEPS steps (about 3 frames of the
main loop), render; a control run with no poke and the same budget is rendered too. The report is the bounding box and
pixel count of the pixels that differ between poke run and control run. A broken-model control (poking an unrelated
field, $5c000, near the globals) must give an empty diff.
usage: hud_poke.py [name ...]   (default: all)   -> WORK/frontend/hud/<name>.png, report on stdout"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe_repl, sgcommon
from PIL import Image
A6 = 0x5BF00
STEPS = 300000
POKES = [   # name, offset from A6 (or absolute with 'abs:'), width, value
    ('alt_c000',     304, 'ww', 0xC000), ('alt_e000', 304, 'ww', 0xE000), ('alt_f000', 304, 'ww', 0xF000),
    ('speed_0',      542, 'ww', 0x0000), ('speed_080', 542, 'ww', 0x0080), ('speed_100', 542, 'ww', 0x0100), ('speed_1c0', 542, 'ww', 0x01C0),
    ('energy_hi',    606, 'ww', 0x55F0), ('energy_low', 606, 'ww', 0x0900),
    ('shield_hi',    608, 'ww', 0x9C40), ('shield_low', 608, 'ww', 0x2000),
    ('lastpts',      646, 'ww', 0x1234),
    ('missiles0',    632, 'ww', 0x0000), ('missiles2', 632, 'ww', 0x0002),
    ('score_bcd',    'abs:c098', 'w', 0x12345678),
    ('hi_bcd',       'abs:c0a0', 'w', 0x00987654),
    ('control_unrelated', 'abs:5c000', 'ww', 0x4242),
]

REGIONS = {'cockpit': (130, 200), 'topbar': (0, 10)}
BOXES = {'alt_gauge': (26, 150, 48, 200), 'speed_gauge': (268, 150, 292, 200)}   # x0,y0,x1,y1 of the two vertical gauges   # the 3D window (y 10..129) changes with any flight poke

def diff(a, b, y0=0, y1=200, x0=0, x1=320):
    A, B = Image.open(a).convert('RGB'), Image.open(b).convert('RGB')
    pa, pb = A.load(), B.load()
    xs, ys, n = [], [], 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            if pa[x, y] != pb[x, y]:
                n += 1; xs.append(x); ys.append(y)
    return (n, (min(xs), min(ys), max(xs), max(ys))) if n else (0, None)

if __name__ == '__main__':
    out = sgcommon.work('frontend', 'hud'); os.makedirs(out, exist_ok=True)
    want = sys.argv[1:]
    ctl = os.path.join(out, 'control.snap')
    fe_repl.run(sgcommon.SNAP_GAME1, ['s %d' % STEPS, 'snap ' + ctl])
    fe_repl.render(ctl, os.path.join(out, 'control.png'))
    for name, a, w, v in POKES:
        if want and name not in want: continue
        addr = int(a[4:], 16) if isinstance(a, str) else A6 + a
        cmd = {'ww': 'ww', 'wb': 'wb', 'w': 'w'}[w] + ' %x %x' % (addr, v)
        s = os.path.join(out, name + '.snap')
        fe_repl.run(sgcommon.SNAP_GAME1, [cmd, 's %d' % STEPS, 'snap ' + s])
        fe_repl.render(s, os.path.join(out, name + '.png'))
        res = []
        for rn, (y0, y1) in REGIONS.items():
            n, bb = diff(os.path.join(out, 'control.png'), os.path.join(out, name + '.png'), y0, y1)
            res.append('%s %d px %s' % (rn, n, bb))
        for bn, (x0, y0, x1, y1) in BOXES.items():
            n, bb = diff(os.path.join(out, 'control.png'), os.path.join(out, name + '.png'), y0, y1, x0, x1)
            res.append('%s %d px %s' % (bn, n, bb))
        print('%-18s %-22s %s' % (name, cmd, ' | '.join(res)))
