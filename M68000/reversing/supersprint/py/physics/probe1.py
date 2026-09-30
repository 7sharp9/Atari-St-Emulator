import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pl import *
h = Harness(sscfg.SNAP_RACE)
regs = h.run_to(0xdf18, 1)
print({k: hex(v) for k, v in regs.items() if k in ('PC', 'A4', 'A7', 'A5')})
r = h.snap_ram()
print('-4810', r.arr(-4810, 4), 'joy', hex(r.u8(A4 - 4804)), hex(r.u8(A4 - 4803)), '-3914', r.arr(-3914), '-8068', r.g(-8068), '-8072', r.g(-8072))
mem, d, outc = h.callcap(0xdf18)
print(outc, d['steps'], len(mem))
h.close()
