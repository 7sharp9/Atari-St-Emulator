"""scan_screens.py SCREEN - exhaustive scancode ($01..$75) scan on one screen, from a snapshot inside that screen's input loop.
Metric per screen (baseline = no key; a scancode is reported iff its metric differs):
  select   steps until the race routine $be40 is entered (SELECT TRACK; initiating channel = joystick 0, so keys should be ignored) + track arg
  prepare  steps until the race loop $df18 (PREPARE TO RACE, keyboard player in; ESC shortens)
  options  (channel words, sound flag, entries of main loop top $138b2) after 1.5M steps (options screen)
  race     entries of $df18 / $c9c8 (pause poll) / $138b2 over 1.2M steps + speed of the human car (race, human on joystick 0)
  winner   key code returned by the F-poll at $1ad40 and the animation index chosen (winner's circle)
  shop     steps until the prepare routine $18024 is entered (item-choice screen, human on joystick 0)
Key is held (make only) from the snapshot on, like a held key."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
from multiprocessing import Pool
SNAP = os.path.join(AGENT, 'snap')
CFG = {
    'select': os.path.join(SNAP, 'sel2.snap'), 'prepare': os.path.join(SNAP, 'prep_kbd.snap'), 'options': os.path.join(SNAP, 'opt.snap'),
    'race': sscfg.SNAP_RACE, 'winner': os.path.join(SNAP, 'pre_winner.snap'), 'shop': os.path.join(SNAP, 'shop.snap'),
}
def until(r, addr, cap):
    out, g = r.cmd('u %x %d' % (addr, cap))
    import re
    m = [l for l in out if 'reached' in l]
    until.regs = g
    return int(re.search(r'after (\d+) step', m[0]).group(1)) if m else None
def metric(screen, code):
    r = R(CFG[screen])
    try:
        if code is not None: r.cmd('kbd %02x' % code); r.cmd('s 30000')
        if screen == 'select':
            s = until(r, 0xbe40, 8000000)
            return (s, r.w16(until.regs['A7'] + 4) if s else None)
        if screen == 'prepare': return until(r, 0xdf18, 14000000)
        if screen == 'shop': return until(r, 0x18024, 14000000)
        if screen == 'options':
            a = Acc(r, [0x138b2]); a.run(1500000)
            return ([r.g16(o) for o in (-4810, -4808, -4806)], r.g16(-8068), a.tot[0x138b2])
        if screen == 'race':
            a = Acc(r, [0xdf18, 0xc9c8, 0x138b2]); a.run(1200000)
            return (a.tot[0xdf18], a.tot[0xc9c8], a.tot[0x138b2], r.g16(-3730 + 2))
        if screen == 'winner':
            out, g = r.cmd('u 1ad44 30000000'); d0 = g['D0'] & 0xffff
            out, g = r.cmd('u 1ad80 3000')
            return (d0, r.w16(g['A6'] - 2))
    finally:
        r.close()
def job(a): return a[1], metric(*a)
if __name__ == '__main__':
    screen = sys.argv[1]
    codes = [None] + list(range(1, 0x76))
    with Pool(8) as p:
        res = dict(p.map(job, [(screen, c) for c in codes]))
    base = res[None]
    diff = {c: v for c, v in res.items() if c is not None and v != base}
    print('screen', screen, 'baseline', base)
    print('scancodes tested', len(codes) - 1, 'differing from baseline:', {'%02x' % c: v for c, v in diff.items()})
    json.dump({'screen': screen, 'baseline': base, 'diff': {'%02x' % c: v for c, v in diff.items()}}, open(os.path.join(AGENT, 'scan_screen_%s.json' % screen), 'w'), default=str, indent=1)
