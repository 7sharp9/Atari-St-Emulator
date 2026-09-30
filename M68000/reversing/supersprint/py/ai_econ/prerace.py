"""prerace.py - build the snapshots the other ai_econ scripts start from (all under data/).

  select_live.snap  ss_attract.snap + joystick-0 fire: SELECT TRACK loop of $19164 paused at its loop head $193b6
                    (player slot 1 = joystick 0; cursor -4(A6)=0; countdown -8(A6))
  prerace_b.snap    ss_select.snap + keyboard fire pulse: paused at $bec0, the top of $be40's per-car init loop (before
                    any per-car array is initialised; levels/wrenches/R can still be poked)
  prerace_k.snap    same run, paused at $c156 = the first cap write of the race-start initialiser (car 0)

    cd M68000 && python3 reversing/supersprint/py/ai_econ/prerace.py
"""
from aiutil import *

r = Repl2(os.path.join(sscfg.WORK, 'ss_attract.snap'))
r.cmd('kbd fe 80'); r.cmd('s 30000'); r.cmd('kbd fe 00')
r.cmd('s 5000000')          # the real SELECT TRACK loop starts ~6M steps after the fire (earlier hits are attract-mode calls)
out, regs = r.cmd('bp 193b6 2000000')
assert any('hit' in l for l in out), out
print('select loop A6=%x cursor=%s timer=%s' % (regs['A6'], r.words(regs['A6'] - 4, 1), r.words(regs['A6'] - 8, 1)))
r.cmd('snap %s' % os.path.join(DATA, 'select_live.snap'))
r.close()

r = Repl2(os.path.join(sscfg.WORK, 'ss_select.snap'))
r.cmd('kbd 2a'); r.cmd('s 40000'); r.cmd('kbd aa')
out, regs = r.cmd('bpc bec0 1 12000000')
assert any('hit' in l for l in out), out
r.cmd('snap %s' % os.path.join(DATA, 'prerace_b.snap'))
out, regs = r.cmd('bpc c156 1 100000')
assert any('hit' in l for l in out), out
r.cmd('snap %s' % os.path.join(DATA, 'prerace_k.snap'))
r.close()
print('ok')
