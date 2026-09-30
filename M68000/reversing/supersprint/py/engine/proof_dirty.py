"""Dirty-rectangle bookkeeping.
(1) $14972(car): restores rect [offset word, rows-1 word] at -3634(A4) + (frame&1)*16 + car*4 from the static stash (-86(A4)) to the
    draw screen (-78(A4)), 16 bytes (32 px) per row, stride 160.  Differential test vs Python.
(2) $14a4a(car) writes that record: (byte offset of the car's 32-px strip, 11) into the slot of the current frame parity."""
import sys, os, random, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from calldiff import CallDiff

cd = CallDiff(); R = cd.ram
scr = struct.unpack_from('>I', R, A4 - 78)[0]; stash = struct.unpack_from('>I', R, A4 - 86)[0]
par = struct.unpack_from('>h', R, A4 - 8072)[0] & 1
random.seed(2)
ok = n = 0
for t in range(30):
    car = random.randrange(4)
    off = random.randrange(0, 180) * 160 + random.randrange(0, 18) * 8
    rows = random.randrange(0, 20)
    slot = A4 - 3634 + par * 16 + car * 4
    cd.poke_word(slot, off); cd.poke_word(slot + 2, rows)
    cd.poke(scr + 0, bytes(random.randrange(256) for _ in range(0)))
    oc, ch, d = cd.call(0x14972, struct.pack('>H', car))
    assert oc == 'returned', oc
    live = cd.apply(R[scr:scr + 32000], scr, ch)
    mine = bytearray(R[scr:scr + 32000])
    for r in range(rows + 1):
        a = off + r * 160
        mine[a:a + 16] = R[stash + a:stash + a + 16]
    ok += sum(1 for a, b in zip(live, mine) if a == b); n += 32000
print('$14972 restore: %d / %d screen bytes equal over 30 random rectangles (frame parity %d)' % (ok, n, par))
# (2) record written by the car blit
good = 0
for t in range(20):
    car = random.randrange(4); x = random.randrange(0, 300); y = random.randrange(31, 186)
    cd.poke_word(A4 - 3690 + 2 * car, x); cd.poke_word(A4 - 3698 + 2 * car, y)
    cd.r.cmd('m 0 4')
    oc, ch, d = cd.call(0x14A4A, struct.pack('>H', car))
    slot = A4 - 3634 + par * 16 + car * 4
    got = struct.unpack('>HH', bytes(cd.apply(cd.ram[slot:slot + 4], slot, ch)))
    want = (((x & 0xFFF0) >> 1) + y * 160, 11)
    good += (got == want)
print('$14a4a rect record (offset, rows-1=11): %d / 20 equal' % good)
cd.close()
