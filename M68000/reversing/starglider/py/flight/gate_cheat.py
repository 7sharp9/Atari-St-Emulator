"""Gate: the Del-J-S-space-A-R-G key sequence ($d420) entered twice toggles the practice flag 717(A6) when the cross-hair
lock (705) is on and the throttle word $c3d4 is 0 (INFERRED from the code at $d420..$d4bc, checked here by driving it):
717 goes 0 -> $ff and the game then pins energy/shield/laser energy at the cheat values ($cbc8..$cbd4).
Control: the same keys with the throttle not 0 leave 717 at 0.

    cd M68000 && ATARI_NOTRACE=1 python3 reversing/starglider/py/flight/gate_cheat.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flightlib import *
from fly import Flight, SCAN
SEQ = [0x53, 0x24, 0x1f, 0x39, 0x1e, 0x13, 0x22]          # Del J S space A R G

def run(throttle_zero):
    f = Flight(journal=sg.work('flight', 'j_cheat.jsonl'))
    dr = f.dr
    f.hold(['f'], 2)                                          # 705 on
    if throttle_zero:
        f.hold(['slash'], 4)                                  # throttle $c3d4 -> 0
    for rep in range(2):
        for sc in SEQ:
            dr.hold(sd.Key(sc), steps=100000); dr.step(100000)
    f.run(3)
    s = f.state()
    out = (s['cheat'], s['xhair_lock'], s['stick_t'], dr.u16(G + 606), dr.u16(G + 608), dr.u16(G + 650))
    f.close()
    return out
a = run(True); b = run(False)
print('throttle 0 :  717=%#x 705=%#x c3d4=%d energy=%#x shield=%#x laser=%#x' % a)
print('throttle>0 :  717=%#x 705=%#x c3d4=%d energy=%#x shield=%#x laser=%#x' % b)
print('cheat toggle:', 'MATCH 2/2' if a[0] == 0xff and b[0] == 0 else 'MISMATCH')
