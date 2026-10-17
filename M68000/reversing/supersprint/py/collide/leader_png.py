"""leader_png.py - render the HUD with car 1 forced to lead, at pass counters 1 (marker shown) and 3 (panel shown), to PNGs under agents/collide/png/.
   usage: leader_png.py <snap>"""
import sys, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py', 'physics'))
import pl
OUTD = os.path.join(pl.sscfg.WORK, 'agents', 'collide'); pl.OUT = OUTD
from difflib_ss import *
os.makedirs(os.path.join(OUTD, 'png'), exist_ok=True); os.makedirs(os.path.join(OUTD, 'snap'), exist_ok=True)
LEAD = int(sys.argv[2]) if len(sys.argv) > 2 else 1
h = Harness(sys.argv[1]); h.run_to(0xdf18, 1, 8000000)
pl.poke_arr(h, -3906, [1] * 4); pl.poke_arr(h, -3850, [2] * 4); pl.poke_arr(h, -3842, [50 if i == LEAD else 0 for i in range(4)])
got = {}
for f in range(200):
    h.run_to(0xdf18, 1)
    r = h.snap_ram()
    c = r.g(-4814); R = r.gu(-8072)
    if R % 6 == 5 and c in (1, 3) and c not in got and r.g(-4812) == LEAD and f > 30:
        p = os.path.join(OUTD, 'snap', 'lead%d_c%d.snap' % (LEAD, c)); h.cmd('snap ' + p); got[c] = p
    if len(got) == 2: break
h.close()
for c, p in got.items():
    subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'snap_render.py'), p, os.path.join(OUTD, 'png', 'lead%d_counter%d.png' % (LEAD, c))])
print(got)
