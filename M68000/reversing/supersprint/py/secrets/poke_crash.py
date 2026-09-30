"""poke_crash.py - which A4-relative byte, poked to 3 (a 'key down' cell value) just before the prepare->race transition, prevents the race start
($df18 never reached within 12M steps)?  Pokes are done in RAM with no IKBD traffic (snap/prep_kbd.snap)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
from multiprocessing import Pool
import re
def job(args):
    off, val = args
    r = R(os.path.join(AGENT, 'snap', 'prep_kbd.snap'))
    a = sscfg.A4 + off
    base = a & ~3
    cur = bytearray(r.mem(base, 4)); cur[a & 3] = val
    r.cmd('w %x %s' % (base, bytes(cur).hex()))
    out, g = r.cmd('u df18 12000000')
    ok = g['PC'] == 0xdf18
    r.close()
    return off, val, ok
if __name__ == '__main__':
    offs = [-4830, -4810, -4803, -4802, -4801, -4800, -4799, -4798, -4760, -4743, -4700, -4686, -4685, -4684, -4683, -4670, -4600]
    jobs = [(o, 3) for o in offs] + [(-4800, 1), (-4800, 2), (-4800, 0x80), (-4743, 1)]
    with Pool(8) as p:
        for off, val, ok in p.imap(job, jobs):
            print('poke %6d(A4) = %02x  -> race starts: %s' % (off, val, ok), flush=True)
