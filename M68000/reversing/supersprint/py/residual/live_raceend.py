"""Live checks of the race-end control phase of $be40 (loop $c6f6..$ca02, exit $ca3e..$caa6) and the session tail of $13a5e.
Each scenario resumes the live Track-1 race (ss_prep.snap, human = slot 1 red), pokes lap counters -3906(A4)[car] and runs `hits`.
Predictions (from the code):  after the first car shows lap counter 4 (and its HUD digit -4822 is not yet 4) the finish latch is set ONCE ($c8fc);
170 further loop passes follow; the control calls ($d4fa human, $eaea drone) run in 4 of them (countdown 169..166) plus the latch pass itself = 5 per car;
$ca9c (after the demotion loop) is reached once; other cars at lap 4 are demoted to (3, 5, 99)  -3906/-3850/-3842; -8072 is restored to its value at the latch.
usage: live_raceend.py <scenario>   scenarios: one | two | final | ctl64 | tail0 | tail1"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
from repl import Repl
A4 = sscfg.A4
sc = sys.argv[1]
r = Repl(sscfg.SNAP_RACE)

def rd(a, n):
    return r.mem(a, n)
def w16(a, v):
    base = a & ~3; b = bytearray(r.mem(base, 4)); b[a - base:a - base + 2] = v.to_bytes(2, 'big', signed=False) if v >= 0 else (v & 0xFFFF).to_bytes(2, 'big'); r.cmd('w %x %s' % (base, bytes(b).hex()))
def g16(a): return int.from_bytes(rd(a, 2), 'big')
def arr(off, n=4): return [int.from_bytes(rd(A4 + off + 2 * i, 2), 'big') for i in range(n)]
def hits(steps, addrs):
    out, regs = r.cmd('hits %d %s' % (steps, ' '.join(addrs)))
    h = {}
    for l in out:
        m = re.match(r'\s+\$([0-9a-f]{6,8})\s+(\d+)\s+first (\d+)\s+last (\d+)', l)
        if m: h[int(m.group(1), 16)] = (int(m.group(2)), int(m.group(3)), int(m.group(4)))
    return h, regs

print('start: laps -3906', arr(-3906), 'disp -4822', arr(-4822, 3), 'drone -3914', arr(-3914), 'frame', g16(A4 - 8072), 'R -1748', g16(A4 - 1748), '-150/-148', g16(A4 - 150), g16(A4 - 148))
if sc in ('one', 'two'):
    w16(A4 - 3906 + 6, 4)
    if sc == 'two': w16(A4 - 3906 + 4, 4)
    h, regs = hits(4000000, ['c6f6', 'c8fc', 'c8da', 'ca9c', 'd4fa', 'eaea', 'caa4', 'df18'])
    for k in sorted(h): print('  $%05x hits %d first %d last %d' % ((k,) + h[k]))
    print('PC after budget %x' % regs['PC'])
    # state at the exit: re-run to $ca9c from a fresh state is not needed: the budget ran past it; re-resume for the arrays
    r.close(); r = Repl(sscfg.SNAP_RACE)
    w16(A4 - 3906 + 6, 4)
    if sc == 'two': w16(A4 - 3906 + 4, 4)
    out, _ = r.cmd('u c8fc 4000000'); f_latch = g16(A4 - 8072); print('at the latch ($c8fc): frame counter -8072 = %d, laps %s' % (f_latch, arr(-3906)))
    out, _ = r.cmd('u ca9c 4000000'); print('at $ca9c (after the demotion loop): laps %s  -3850 %s  -3842 %s  frame -8072 = %d (latch value %d)' % (arr(-3906), arr(-3850), arr(-3842), g16(A4 - 8072), f_latch))
    out, regs = r.cmd('u caa4 100'); print('at the epilogue $caa4: D0 = %d (0 = race ran to its end, 1 = aborted)' % (regs['D0'] & 0xFFFF))
elif sc == 'final':
    w16(A4 - 3906 + 6, 3)
    out, regs = r.cmd('u b34c 4000000'); sp = regs['A7']; print('$b34c reached: arg word at 4(A7) = %d (1 = lap-3 announce); laps %s disp %s' % (g16(sp + 4), arr(-3906), arr(-4822, 3)))
    print('banner flag -1802 = %d, banner frame -1806 = %d' % (g16(A4 - 1802), g16(A4 - 1806)))
    r.cmd('s 40'); print('after the call: -1802 = %d  -1806(frame) = %d  -1804 = %d' % (g16(A4 - 1802), g16(A4 - 1806), g16(A4 - 1804)))
elif sc == 'ctl64':
    print('score increment array -4876(A4) =', rd(A4 - 4876, 6).hex(), ' scores latched -4870:', rd(A4 - 4870, 18).hex(), ' staging -4846:', rd(A4 - 4846, 18).hex())
    h, regs = hits(1500000, ['16084', '13bbe', '1464a'])
    for k in sorted(h): print('  $%05x hits %d first %d last %d' % ((k,) + h[k]))
    print('after: staging -4846:', rd(A4 - 4846, 18).hex(), 'frame', g16(A4 - 8072))
elif sc in ('tail0', 'tail1'):
    w16(A4 - 3906 + 2, 4)        # the human (slot 1) finishes first, so it survives the elimination and the session would continue
    if sc == 'tail1': w16(A4 - 150, 1)
    h, regs = hits(30000000, ['be40', '13a9c', '13b00', '13b16', '13b1e', '13b2c', '1000e', '1a4ca', '13b30'])
    for k in sorted(h): print('  $%05x hits %d first %d last %d' % ((k,) + h[k]))
    print('PC after budget %x; -1748 = %d; slot drone flags -3914 = %s; -150/-148 = %d/%d' % (regs['PC'], g16(A4 - 1748), arr(-3914), g16(A4 - 150), g16(A4 - 148)))
r.close()
