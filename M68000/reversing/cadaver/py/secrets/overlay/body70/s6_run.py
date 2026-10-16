"""s6_run.py face|control [total_steps]: from room64_arrival.snap (natural arrival in room 64), watch 2299(A5) (VAR 17) and the even byte below
($018a4c, len 2), then
  face:    hold Left until the hero stalls in front of object 70 (event 7 every frame while facing), release, hold Right back to the arrival lane
  control: hold Right only (same release/settle), never facing 70
then run `total` steps in 2M chunks counting $04d124 (timer 7 handler), $010d32 (verb 49), $011230 (verb 28 MESSAGE), polling VAR 17 and 2315(A5).
If VAR 17 reaches 2: hold Left again to face 70, stop at the next MESSAGE ($011230) and render the screen after it prints."""
from lib17 import *
import re
arm = sys.argv[1]; total = int(sys.argv[2]) if len(sys.argv) > 2 else 50000000
r = Repl(OUT + 'room64_arrival.snap')
r.cmd('watch 18a4c 2'); r.err.clear()
def wl():
    out = [l for l in r.err if l.startswith('WATCH')]; r.err.clear(); return out
c0 = r.hits(1, 0x4d124)
if arm == 'face':
    print('L', hold(r, LEFT), st(r))
    print('R', hold(r, RIGHT), st(r))
else:
    print('R', hold(r, RIGHT), st(r))
    print('R', hold(r, RIGHT), st(r))
for l in wl(): print('  ', l)
base = r.steps; print('window starts at %d steps from arrival' % base, flush=True)
done = 0; v2 = None
while done < total:
    h = r.hits(2000000, 0x4d124, 0x10d32, 0x11230); done += 2000000
    ws = wl()
    print('%9d  VAR17 %d  t7(2315) %3d  hits 4d124 %d 10d32 %d 11230 %d  room %d pos %s' % (done, r.b(VAR17), r.b(A5 + 2315), h.get(0x4d124, 0), h.get(0x10d32, 0), h.get(0x11230, 0), r.w(ROOM), pos(r)), flush=True)
    for l in ws: print('   ', l)
    if r.b(VAR17) == 2 and v2 is None: v2 = done; break
print('VAR17 reached 2 at', v2, 'steps into the window' if v2 else '')
if v2:
    r.snap(OUT + 'var17_eq2_%s.snap' % arm)
    joy(r, LEFT); out = r.cmd('bp 11230 3000000'); joy(r, 0)
    print([l for l in out if 'hit' in l or 'PC' in l][:4])
    regs = ' '.join(r.cmd('r')); print(regs)
    r.cmd('s 400000'); r.snap(OUT + 'cold_msg_%s.snap' % arm)
    print('VAR17 after facing', r.b(VAR17))
    for l in wl(): print('   ', l)
r.close()
