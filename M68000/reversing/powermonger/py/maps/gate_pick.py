"""gate_pick.py: the conquest-map pointer test ($11252..$112f6) vs maps_ref.pick_1120e, live, from scratchpad/pm123/win/m1_map.snap
(land 0 conquered). For each probe point the pointer is homed, moved by mouse packets and read back from `$2df92`/`$2df94`, then run (several frames of
the picker loop `$11238`), the snapshot is taken, and both frame buffers (`$2df7c`, `$2df78`) are compared with the map window:
the pixels that differ and carry the box colour (8 free, 10 conquered) are the box. Prediction: pick_1120e -> (land, colour);
the box outline is a 17 x 33 rectangle at (24 col + 7, 40 row + 7 - scroll). Scroll `$11420` is also probed at 100.

    cd M68000 && .venv/bin/python reversing/powermonger/py/maps/gate_pick.py
"""
import os, subprocess, sys
from pathlib import Path
ROOT = Path(os.environ.get('M68000_ROOT') or Path(__file__).resolve().parents[4])
HERE = Path(__file__).resolve().parent
DATA = ROOT / "scratchpad/pm140/agents/maps"      # outputs go to the gitignored scratchpad, not next to the script
DATA.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(HERE))
from disassemble import ram_from_snap
import maps_ref as M
SNAP = 'scratchpad/pm123/win/m1_map.snap'
OUT = DATA / 'gate'; OUT.mkdir(exist_ok=True)
ram0 = bytearray(ram_from_snap(str(ROOT / SNAP)))
conq = bytes(ram0[M.CONQ:M.CONQ + 196])


def pix(buf, base, x, y):
    o = base + y * 160 + (x >> 4) * 8 + ((x >> 3) & 1); bit = 0x80 >> (x & 7)
    return sum(((buf[o + 2 * p] & bit) != 0) << p for p in range(4))


probes = [(20, 20, 0), (44, 20, 0), (68, 20, 0), (20, 60, 0), (45, 62, 0), (20, 100, 0), (100, 100, 0), (200, 150, 0), (12, 12, 0),
          (28, 12, 0), (24, 45, 0), (20, 20, 100), (44, 20, 100), (20, 60, 100), (20, 150, 100), (300, 20, 0), (310, 20, 0), (7, 20, 0)]
tot = ok = 0
for mx, my, sc in probes:
    snap = OUT / ('pick_%d_%d_%d.snap' % (mx, my, sc))
    cmds = ['mouse move -400 -400', 's 300000', 'mouse move 0 0', 's 300000', 'w 1141e %04x%04x' % (0, sc),
            'mouse move %d %d' % (mx, my), 's 300000', 'mouse move 0 0', 's 300000', 'snap %s' % snap.relative_to(ROOT).as_posix(), 'q']
    subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', SNAP, 'repl', '--disk-a', 'scratchpad/powermonger.st'],
                   input='\n'.join(cmds) + '\n', capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE='1'), timeout=600)
    r = bytearray(ram_from_snap(str(snap)))
    mx, my = M.w16(r, 0x2df92), M.w16(r, 0x2df94)    # the pointer the game actually has (the ISR integrates the mouse packets)
    pred = M.pick_1120e(mx, my, sc, conq)
    found = None
    for buf in (M.w16(r, 0x2df7c) << 16 | M.w16(r, 0x2df7e), M.w16(r, 0x2df78) << 16 | M.w16(r, 0x2df7a)):
        win = M.MAPBMP + sc * 160
        for colour in (8, 10):
            pts = [(x, y) for y in range(200) for x in range(320)
                   if pix(r, buf, x, y) == colour and pix(r, win - 0, x, y) != colour] if False else None
        # compare with the map window: window pixel (x,y) is the bitmap pixel at byte offset win + y*160 ...
        pts = {8: [], 10: []}
        for y in range(200):
            for x in range(320):
                c = pix(r, buf, x, y)
                if c in pts and pix(r, M.MAPBMP, x, y + sc) != c:
                    pts[c].append((x, y))
        for c in (8, 10):
            if len(pts[c]) > 20:
                xs = [p[0] for p in pts[c]]; ys = [p[1] for p in pts[c]]
                found = (c, min(xs), min(ys), max(xs), max(ys))
    if pred is None:
        good = found is None
        why = 'no box expected'
    else:
        land, colour = pred
        row, col = divmod(land, 13)
        x0, y0 = col * 24 + 7, row * 40 + 7 - sc
        good = found is not None and found[0] == colour and found[1] == x0 and found[2] == max(y0, 0) and found[3] == x0 + 17 and (found[4] == y0 + 33 or y0 + 33 >= 200)
        why = 'land %d colour %d box (%d,%d)-(%d,%d)' % (land, colour, x0, y0, x0 + 17, y0 + 33)
    tot += 1; ok += good
    print('ptr (%3d,%3d) scroll %3d: predicted %-44s observed %s  %s' % (mx, my, sc, why, found, 'ok' if good else 'MISMATCH'))
print('pick: %d/%d probes agree' % (ok, tot))
