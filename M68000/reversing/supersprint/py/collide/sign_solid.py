"""sign_solid.py - are the flashing signs ($b24e blits via $1432e) solid for car collision?
$1432e writes the sign picture into plane 1 (the solid plane) and plane 2.  Test on race_T.snap with RACE poked to 17 ((R+1)%3==0 enables the sign group):
 1. run frames until plane 1 differs from the previous frame by a small blob (sign on); take that state;
 2. experiment A: park the red car on the blob (X,Y,Q,P pokes, speed 20, no stun/flags), run 2 frames, read STUN/SPD/TGT/FLAG;
    experiment B: identical but the blob's plane-1 bits are first reset to the previous frame's bytes (sign off);
 A showing a wall bounce (STUN 10, speed changed) and B not proves the sign pixels are solid.
usage: sign_solid.py <snap> [track]"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py', 'physics'))
import pl
OUTD = os.path.join(pl.sscfg.WORK, 'agents', 'collide'); pl.OUT = OUTD
from difflib_ss import *
snap = sys.argv[1]
os.makedirs(os.path.join(OUTD, 'snap'), exist_ok=True)
h = Harness(snap)
r0 = h.snap_ram(); h.cmd('w %x %04x%04x' % (A4 - 1748, 17, r0.gu(-1746)))
h.run_to(0xdf18, 1, 8000000)
prev = h.snap_ram(); found = None
for f in range(300):
    h.run_to(0xdf18, 1); cur = h.snap_ram()
    pb = cur.gl(-94) + 8000
    d = [k for k in range(8000) if cur.u8(pb + k) != prev.u8(pb + k)]
    if d and all(cur.u8(pb + k) & ~prev.u8(pb + k) == cur.u8(pb + k) ^ prev.u8(pb + k) for k in d):     # only bits turned ON
        found = (f, d); break
    prev = cur
if not found: print('no sign-on frame in 300 frames'); sys.exit(1)
f, d = found
rows = sorted(set(k // 40 for k in d)); cols = sorted(set(k % 40 for k in d))
print('frame %d: plane-1 bits turned on: %d bytes, rows %d..%d, byte columns %s (x = %d..%d)' % (f, len(d), rows[0], rows[-1], cols, cols[0] * 8, cols[-1] * 8 + 7))
sp = os.path.join(OUTD, 'snap', 'sign_on.snap'); h.cmd('snap ' + sp); h.close()
cx, cy = (cols[0] * 8 + cols[-1] * 8 + 7) // 2, (rows[0] + rows[-1]) // 2
def experiment(sign_on, px, py):
    h = Harness(sp); st = h.snap_ram(); pb = st.gl(-94) + 8000
    if not sign_on:
        for k in d:
            a = pb + k; al = a & ~3; b = bytearray(st.bytes(al, 4)); b[a - al] = prev.u8(pb + k)
            h.cmd('w %x %s' % (al, bytes(b).hex()))
    car = 1
    # word pokes via a read-modify-write of the aligned longword
    def setw(addr, v):
        al = addr & ~3; b = bytearray(h.snap_ram().bytes(al, 4)); b[addr - al] = (v >> 8) & 0xff; b[addr - al + 1] = v & 0xff
        h.cmd('w %x %s' % (al, bytes(b).hex()))
    for nm, v in (('X', px), ('Y', py), ('QX', px * 8), ('QY', py * 8), ('PX', px * 8), ('PY', py * 8), ('SPD', 20), ('STUN', 0), ('FLAG', 0), ('F1', 0), ('HEAD', 0), ('TGT', 0)):
        setw(A4 + getattr(P, nm) + 2 * car, v)
    h.cmd('kbd fe 00'); res = []
    for i in range(1):
        h.run_to(0xdf18, 1); r = h.snap_ram(); m = P.Mem(r.b)
        res.append({n: m.a(getattr(P, n), car) for n in ('X', 'Y', 'SPD', 'STUN', 'TGT', 'FLAG', 'VX', 'VY')})
    h.close(); return res
print('car parked at (X,Y) heading 0 speed 20; after the first df18: STUN (10 = wall bounce just taken, 0 = none), VY')
rowsout = []
for px in range(14, 34, 2):
    for py in (cy - 14, cy - 6, cy + 2):
        A = experiment(True, px, py)[0]; B = experiment(False, px, py)[0]
        rowsout.append((px, py, A['STUN'], B['STUN']))
        print('X=%2d Y=%3d  sign on: STUN %2d SPD %2d VY %5d | sign cleared: STUN %2d SPD %2d VY %5d %s' % (px, py, A['STUN'], A['SPD'], A['VY'], B['STUN'], B['SPD'], B['VY'], '  <-- differs' if (A['STUN'], A['SPD'], A['VY']) != (B['STUN'], B['SPD'], B['VY']) else ''))
print('positions where the sign pixels change the outcome: %d of %d' % (sum(1 for r in rowsout if r[2] != r[3]), len(rowsout)))
