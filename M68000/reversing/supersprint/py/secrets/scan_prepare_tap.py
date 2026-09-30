"""scan_prepare_tap.py - scancode scan of the PREPARE-TO-RACE screen with TAPS (make, 30000 steps, break) instead of a held make:
a held make (no break) of any key except ESC makes the harness run die in the race-start initialisation (see held_key_crash.py /
poke_crash.py: poking the same cell value does NOT do that, so it is an IKBD-delivery artefact, not a key function).
Metric: steps until the race loop $df18 is entered (baseline 9.74M; ESC ends the countdown early)."""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
from multiprocessing import Pool
def job(code):
    r = R(os.path.join(AGENT, 'snap', 'prep_kbd.snap'))
    if code is not None:
        r.cmd('kbd %02x' % code); r.cmd('s 30000'); r.cmd('kbd %02x' % (code | 0x80))
    out, g = r.cmd('u df18 14000000')
    m = [l for l in out if 'reached PC' in l or 'gave up' in l]
    r.close()
    return code, (int(re.search(r'after (\d+) step', m[0]).group(1)) + (30000 if code is not None else 0)) if 'reached PC' in m[0] else None
if __name__ == '__main__':
    codes = [None] + list(range(1, 0x76))
    with Pool(8) as p: res = dict(p.map(job, codes))
    base = res[None]
    print('baseline', base)
    print('differ (> 1000 steps from baseline or never):', {'%02x' % c: v for c, v in res.items() if c is not None and (v is None or abs(v - base) > 1000)})
    json.dump({'baseline': base, 'res': {str(k): v for k, v in res.items()}}, open(os.path.join(AGENT, 'scan_prepare_tap.json'), 'w'))
