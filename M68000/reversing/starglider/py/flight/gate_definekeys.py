"""Gate: 'K' on the title screen runs the DEFINE AGAV CONTROLS dialogue ($ce46) and stores six scancodes; 'G' enters the
object gallery ($dd7a) only when the practice flag 717(A6) is set; otherwise any key (G included) starts the game.

    cd M68000 && ATARI_NOTRACE=1 python3 reversing/starglider/py/flight/gate_definekeys.py

Legs (from g_title): (1) K, then six keys, then Y: prints the six bytes at 728..733(A6) and checks them against the
keys pressed, in the prompt order dec-alt(730) inc-alt(731) bank-left(728) bank-right(729) accelerate(732)
decelerate(733); then flies 4 passes holding the user key for 'bank right' and checks stick_x rises by $20 per pass.
(2) G with 717 = 0: the game starts (PC leaves the title loop, 'MANUAL CONTROL' screen). (3) G with 717 = $ff: the
gallery: PC stays in $dd86..$de18/$14556/$bcba range and the screen is rendered to $WORK/flight/title_G717.png."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flightlib import *
OUT = sg.work('flight')

def tap(dr, sc, hold=150000, gap=120000):
    dr.hold(sd.Key(sc), steps=hold); dr.step(gap)

dr = sd.Drive(ROOT, journal=sg.work('flight', 'jt_define.jsonl'), period=POLL)
dr.load(sg.SNAP_TITLE, sg.DISK)
start = dr.fork()
tap(dr, 0x25)                                         # K
chosen = [0x1e, 0x30, 0x2c, 0x2d, 0x1f, 0x20]         # A B Z X S D, for 730 731 728 729 732 733
for sc in chosen: tap(dr, sc)
got = {n: dr.u8(G + n) for n in (730, 731, 728, 729, 732, 733)}
want = dict(zip((730, 731, 728, 729, 732, 733), chosen))
print('define keys:', {k: hex(v) for k, v in got.items()}, 'MATCH 6/6' if got == want else 'MISMATCH')
dr.rpc('render', path=os.path.join(OUT, 'define_confirm.png'))
tap(dr, 0x15)                                         # Y: accept, start the game
dr.step(3000000)
before = (dr.s16(0xc3ce), dr.s16(0xc3d0))
dr.hold(sd.Key(0x2c), steps=4 * POLL)                 # user 'bank left' key Z (728)
mid = (dr.s16(0xc3ce), dr.s16(0xc3d0))
dr.hold(sd.Key(0x1e), steps=4 * POLL)                 # user 'decrease altitude' key A (730)
after = (dr.s16(0xc3ce), dr.s16(0xc3d0))
print(f'user keys: Z (bank left) stick_x {before[0]} -> {mid[0]}; A (decrease altitude) stick_y {mid[1]} -> {after[1]}'
      ' (-$20 per pass expected for both; 3-4 passes in 4 x 44,000 steps)')

for leg, flag in (('G, 717=0', 0), ('G, 717=$ff', 0xff)):
    dr.restore(start)
    dr.poke(G + 717, 1, flag)
    tap(dr, 0x22, hold=200000, gap=1500000)
    r = dr.rpc('regs'); r = r[0] if isinstance(r, list) else r
    print(f'{leg}: PC {r["pc"]}, 606={dr.u16(G+606):#x} 378/380={dr.u16(G+378):#x}/{dr.u16(G+380):#x}')
    dr.rpc('render', path=os.path.join(OUT, 'title_G717.png' if flag else 'title_G.png'))
dr.close()
