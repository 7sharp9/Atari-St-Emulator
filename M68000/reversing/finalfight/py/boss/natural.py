"""natural.py <rec.bin> <kind> : checks of a played (natural) pool-4 boss against boss.md, on a py/stage/bossrec.sh dump (set DD_RANGES to its ranges, bossrec.sh's default below).
Prints the (+2,+3) change list of the boss record ($ff9a68 unless DM_BOSS) with hp, x, y, camera x and y, 297/299 and score, then one line per check:
  hp     health when +2 first leaves 0 against boss.md "The eight kinds" (1P)
  trig   camera at the frame +2 first leaves 0, and the first frame the camera met the handler's trigger (boss.md: x >= $1300, on screen by $3264, y >= $ac0, x >= $2280, x >= $3240)
  award  the frames from the death (+2 = 4) to 60 frames after 297(A5) goes 0 -> 1 whose score change equals the kill award code, with the boss state then
  shake  frames with a pool-8 kind 3 (shaker) record in use, and frames the flag -27916(A5) is set, over the same window
  st6    whether +2 ever reads 6 (boss.md: no kind-0 code writes it)
  spawn  bytes of the record at its first in-use frame that a hand spawn (dm.lua spawn4: zero +0..+127 except +78, then x, y, tag, kind, ch, level) would not reproduce"""
import sys, os
os.environ.setdefault('DD_RANGES', 'ff12e0-ff1300,ff8000-ffb300')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dd import *
A5 = 0xff8000
SHAKE = A5 - 27916
D = Dump(sys.argv[1]); kind = int(sys.argv[2]); fr = D.frames()
HP = {1: 300, 2: 300, 3: 300, 4: 500, 5: 600}
AWARD = {1: 20000, 2: 30000, 3: 40000, 4: 50000, 5: 100000}
def bcd(v): return int('%08x' % v)
def score(i): return bcd(D.u32(i, P1 + 132))
prev = None; first_live = None; first_inuse = None; dead = None; s297 = None; saw6 = 0
print('frame st hp x y cam camy 297 299 score')
for i in range(D.n):
    b0 = D.u8(i, BOSS)
    st = (D.u8(i, BOSS + 2), D.u8(i, BOSS + 3))
    if b0 and first_inuse is None and D.u8(i, BOSS + 19) == kind: first_inuse = i
    if first_inuse is None: continue
    if st[0] == 6: saw6 += 1
    if st[0] != 0 and first_live is None: first_live = i
    if st[0] == 4 and dead is None and first_live is not None: dead = i
    if dead is not None and s297 is None and D.u8(i, A5 + 297) == 1 and D.u8(i - 1, A5 + 297) == 0: s297 = i
    key = (b0, st, D.u8(i, A5 + 297), D.u8(i, A5 + 299))
    if key != prev:
        print('%d %02x%02x b0=%02x hp=%d x=%04x y=%04x cam=%04x camy=%04x 297=%02x 299=%02x score=%d' % (fr[i], *st, b0, D.s16(i, BOSS + 24), D.u16(i, BOSS + 6), D.u16(i, BOSS + 10),
              D.u16(i, A5 + 1042), D.u16(i, A5 + 1116), D.u8(i, A5 + 297), D.u8(i, A5 + 299), score(i)))
        prev = key
def at(i): return 'frame %d' % fr[i] if i is not None else 'never'
if first_live is not None:
    hp = D.s16(first_live, BOSS + 24)
    print('hp: %d at %s, boss.md %d: %s' % (hp, at(first_live), HP.get(kind, -1), 'match' if hp == HP.get(kind) else 'MISMATCH'))
    j = first_live - 1
    print('trig: +2 leaves 0 at %s; camera x %04x y %04x on the frame before, boss x %04x' % (at(first_live), D.u16(j, A5 + 1042), D.u16(j, A5 + 1116), D.u16(j, BOSS + 6)))
    T = {1: (1042, 0x1300), 3: (1116, 0xac0), 4: (1042, 0x2280), 5: (1042, 0x3240)}
    if kind in T:
        o, v = T[kind]
        k0 = next((i for i in range(first_inuse, D.n) if D.u16(i, A5 + o) >= v), None)
        print('trig: camera %s >= %04x first at %s' % ('x' if o == 1042 else 'y', v, at(k0)))
    if kind == 2:  # $3264: visible when x - camx + $30 <= $1e0 (and the y test)
        k0 = next((i for i in range(first_inuse, D.n) if (D.u16(i, BOSS + 6) - D.u16(i, A5 + 1042) + 0x30) & 0xffff <= 0x1e0), None)
        print('trig: boss x - camera x <= $1b0 ($3264 visible) first at %s' % at(k0))
else: print('hp/trig: the boss never left state 0 in the dump')
if s297 is not None:
    end = min(D.n, s297 + 61)
    aw = [i for i in range(dead, end) if score(i) - score(i - 1) == AWARD[kind]]
    print('award: %d frame(s) with score +%d from death (%s) to 297 := 1 (%s) + 60: %s' % (len(aw), AWARD[kind], at(dead), at(s297),
          ', '.join('%s boss st %02x%02x' % (at(i), D.u8(i, BOSS + 2), D.u8(i, BOSS + 3)) for i in aw) or 'MISMATCH'))
    sh = sum(1 for i in range(dead, end) if D.u8(i, SHAKE))
    p8 = [i for i in range(dead, end) if any(D.u8(i, a) and D.u8(i, a + 19) == 3 for a in range(0xff9b28, 0xff9b28 + 30 * 0xc0, 0xc0))]
    print('shake: shaker record in use in %d frames (%s to %s), flag set in %d, of %d frames from death to 297 := 1 + 60' % (len(p8), at(p8[0]) if p8 else '-', at(p8[-1]) if p8 else '-', sh, end - dead))
else: print('award/shake: 297 never went 0 -> 1 after the death (death %s)' % at(dead))
print('st6: +2 = 6 in %d frames' % saw6)
if first_inuse is not None and first_inuse > 0 and not D.u8(first_inuse - 1, BOSS):
    i = first_inuse
    keep = {0, 6, 7, 10, 11, 18, 19, 20, 96, 78, 79}
    diff = [(o, D.u8(i, BOSS + o)) for o in range(128) if o not in keep and D.u8(i, BOSS + o)]
    print('spawn: record in use from %s; non-zero bytes +0..+127 a hand spawn zeroes: %s; +78/+79 = %02x%02x' % (at(i), ' '.join('+%d=%02x' % d for d in diff) or 'none', D.u8(i, BOSS + 78), D.u8(i, BOSS + 79)))
    print('spawn: +128..+191 (kept stale by a hand spawn): %s' % ' '.join('%02x' % D.u8(i, BOSS + o) for o in range(128, 192)))
else: print('spawn: dump starts with the record already in use')
