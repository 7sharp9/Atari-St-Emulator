"""Gate: which code prints each flight message, under what state. Breakpoint on the text printer $bcba (A1 = string),
collect (A1, caller PC from the stack) over scenarios poked from g_game1; a scenario passes when the expected string
address is printed and the control (no poke) does not print it.

    cd M68000 && ATARI_NOTRACE=1 python3 reversing/starglider/py/flight/gate_messages.py

Strings: $cddc POWER DRAINAGE TOO GREAT!  $cdfa SHIELD DEPLETED, AGAV DESTROYED!  $100b4 MISSILE VIEW
$100c2 DOCKING, PRESS I FOR INTERROGATE  $100e4 LAUNCHING FROM SILO  $100f8 ENERGY CELLS REFUELLING."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flightlib import *

STR = {0xcddc: 'POWER DRAINAGE TOO GREAT!', 0xcdfa: 'SHIELD DEPLETED, AGAV DESTROYED!', 0x100b4: 'MISSILE VIEW',
       0x100c2: 'DOCKING, PRESS I FOR INTERROGATE', 0x100e4: 'LAUNCHING FROM SILO', 0x100f8: 'ENERGY CELLS REFUELLING'}
dr = new_drive(sg.work('flight', 'j_msg.jsonl'))
f0 = dr.fork()
dr.rpc('bp_set', addrs=[0xbcba])

def regs():
    r = dr.rpc('regs'); return r[0] if isinstance(r, list) else r

def printed(budget):
    seen = {}
    t0 = dr.step_count
    while dr.step_count - t0 < budget:
        r = dr.run(budget - (dr.step_count - t0))
        if r['reason'] != 'breakpoint': break
        g = regs(); a1 = int(str(g['a1']).lstrip('$'), 16); sp = int(str(g['a7']).lstrip('$'), 16)
        ret = int.from_bytes(dr.read(sp, 4), 'big')
        if a1 in STR: seen.setdefault(a1, []).append(ret - 4)       # the `bsr $bcba` that printed it ($fd14 tail-branches: its caller)
    return seen

def leg(name, pokes, expect, budget=1500000, setup=None, press=None):
    dr.restore(f0)
    for a, w, v in pokes: dr.poke(a, w, v)
    if setup: setup()
    if press is not None: dr.press(sd.Key(press))
    seen = printed(budget)
    if press is not None: dr.release(sd.Key(press))
    got = sorted(seen)
    callers = {STR[a]: sorted(set(hex(c) for c in cs)) for a, cs in seen.items()}
    ok = (expect in seen) if expect else not seen
    print(f'{name}: {"PASS" if ok else "FAIL"} printed {callers}')
    return ok

res = []
res.append(leg('control (flying, nothing poked)', [], None))
res.append(leg('energy underflow', [(G+606, 2, 3), (0xc3d4, 2, -479 & 0xffff)], 0xcddc))
res.append(leg('shield underflow (ground scrape)', [(G+304, 2, -10), (0xc3d0, 2, -250 & 0xffff), (0xc3d4, 2, -100 & 0xffff), (G+608, 2, 200)], 0xcdfa))
res.append(leg('tower gate (707)', [(G+302, 2, 7872), (G+306, 2, 11852), (G+316, 2, 0x800), (0xc3d4, 2, 0)], 0x100f8))
res.append(leg('silo entry -> docked', [(G+302, 2, -26176 & 0xffff), (G+306, 2, 9840), (G+316, 2, 0x720), (G+304, 2, -48 & 0xffff)], 0x100c2))
def docked():
    dr.step(4500000)             # the craft creeps 800 units forward at speed 10 inside the silo: ~80 passes
    print('   docked: 714=%#x 658=%#x 608=%#x dockings=%d' % (dr.u8(G+714), dr.u16(G+658), dr.u16(G+608), dr.u32(G+192)))
res.append(leg('launch from the silo (Space)', [(G+302, 2, -26176 & 0xffff), (G+306, 2, 9840), (G+316, 2, 0x720), (G+304, 2, -48 & 0xffff), (G+608, 2, 5000)],
               0x100e4, budget=600000, setup=docked, press=0x39))
res.append(leg('missile launched (L)', [], 0x100b4, setup=lambda: (dr.hold(sd.Key(0x26), steps=2 * POLL))))
print('messages: MATCH %d/%d' % (sum(res), len(res)))
dr.close()
