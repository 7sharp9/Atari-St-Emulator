"""Drive the non-flight screens from g_game1 / g_title with labelled pokes and key taps; save a snapshot and PNG of each.
Screens (outputs WORK/frontend/scr_<name>.png):
  docked    poke 714(A6)=$ff (docked flag) and 658(A6)=$1e (refuel countdown value that shows the dock text), run 2M
  interrog  poke 714(A6)=$ff, tap I ($17); run 3M; then tap SPACE ($39) twice, 3M each (next object)
  controls  from g_title tap K ($25): DEFINE AGAV CONTROLS page
  over_nrg  poke 606(A6)=1 (energy) -> 'POWER DRAINAGE TOO GREAT!'
  over_shd  poke 608(A6)=1 (shield) and 300(A6)... see report
A6 = $5bf00. Usage: screens_flow.py <name> ..."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe_repl, sgcommon
A6 = 0x5BF00
out = sgcommon.work('frontend')
def P(n): return os.path.join(out, 'scr_' + n)
def snap_render(cmds, start, name):
    o = fe_repl.run(start, cmds + ['snap %s.snap' % P(name)])
    fe_repl.render(P(name) + '.snap', P(name) + '.png')
    return o
def wb(o, v): return 'wb %x %x' % (A6 + o, v)
def ww(o, v): return 'ww %x %x' % (A6 + o, v)
what = sys.argv[1:] or ['docked', 'interrog', 'controls']
G1, T = sgcommon.SNAP_GAME1, sgcommon.SNAP_TITLE
for w in what:
    if w == 'docked':
        snap_render([wb(714, 0xff), ww(658, 0x1e), 's 2000000'], G1, 'docked')
    elif w == 'interrog':
        c = [wb(714, 0xff)] + fe_repl.key('17', 200000, 3000000)
        snap_render(c, G1, 'interrog1')
        c += fe_repl.key('39', 200000, 3000000)
        snap_render(c, G1, 'interrog2')
        c += fe_repl.key('39', 200000, 3000000)
        snap_render(c, G1, 'interrog3')
    elif w == 'controls':
        snap_render(fe_repl.key('25', 200000, 2000000), T, 'controls')
    elif w == 'over_nrg':
        snap_render([ww(606, 1), 's 3000000'], G1, 'over_nrg')
    elif w == 'over_shd':
        snap_render([ww(608, 1), 's 3000000'], G1, 'over_shd')
    print(w, 'done')
