"""test_trajectory.py - multi-frame differential test of the whole car model against live runs.
For consecutive frame boundaries (entry of $df18) S_n, S_n+1 of a natural-play race (pseudo-random joystick-0 input), apply
ssport.next_boundary
   S_n --df18--> E_n --controls(n+1)--> S_n+1'   and compare S_n+1' with the live S_n+1 field by field.
Reports match counts per field over (frames x cars).
usage: test_trajectory.py <nframes> <seed> [pokes]"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from difflib_ss import *

N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
h = Harness(sscfg.SNAP_RACE)
drv = Driver(h, seed)
FIELDS = {'X': P.X, 'Y': P.Y, 'HEAD': P.HEAD, 'TGT': P.TGT, 'SPD': P.SPD, 'QX': P.QX, 'QY': P.QY, 'PX': P.PX, 'PY': P.PY, 'FLAG': P.FLAG, 'WP': P.WP,
          'STUN': P.STUN, 'BUMP': P.BUMP, 'F1': P.F1, 'F2': P.F2, 'GATE': P.GATE, 'SECTOR': P.SECTOR, 'TURN': P.TURN, 'LAPPOS': P.LAPPOS,
          'TURNCNT': P.TURNCNT, 'VX': P.VX, 'VY': P.VY, 'VTX': P.VTX, 'VTY': P.VTY, 'AX': P.AX, 'AY': P.AY, 'RX': P.RX, 'RY': P.RY,
          'WPX': P.WPX, 'WPY': P.WPY, 'SAFEX': P.SAFEX, 'SAFEY': P.SAFEY, 'SAFEH': P.SAFEH, 'LAPS': P.LAPS, 'WRENCH': P.WRENCH}
ok = {k: 0 for k in FIELDS}
tot = 0
allok = 0
frames = 0
firstbad = []
badframes = []
prev = None
for i in range(N + 1):
    drv.poke_input()
    if h.run_to(0xdf18, 1) is None:
        break
    r = h.snap_ram()
    cur = r
    if prev is not None:
        m = P.Mem(prev.b)
        # carry the input bytes of the *current* snapshot (the control phase of frame n+1 read them)
        for off in (-4804, -4803):
            m.wb(A4 + off, cur.u8(A4 + off))
        P.next_boundary(m)
        c = P.Mem(cur.b)
        frames += 1
        frame_ok = True
        for nm, off in FIELDS.items():
            for car in range(4):
                tot += 1 if nm == 'X' else 0
                if m.a(off, car) == c.a(off, car):
                    ok[nm] += 1
                else:
                    frame_ok = False
                    if len(firstbad) < 6:
                        firstbad.append((i, nm, car, m.a(off, car), c.a(off, car)))
        if m.gu(-8072) == c.gu(-8072) and m.gu(-8478) == c.gu(-8478):
            pass
        else:
            frame_ok = False
            if len(firstbad) < 6:
                firstbad.append((i, 'cnt', 0, (m.gu(-8072), m.gu(-8478)), (c.gu(-8072), c.gu(-8478))))
        if frame_ok:
            allok += 1
        else:
            badframes.append(i)
    prev = cur
print('frames compared: %d  (all fields of all 4 cars identical in %d frames)' % (frames, allok))
print('per-field matches (of %d car-frames each):' % (frames * 4))
print('  ' + '  '.join('%s %d' % (k, v) for k, v in ok.items()))
print('mismatching frame indices:', badframes[:60])
print('first mismatches (frame, field, car, port, live):', firstbad)
h.close()
