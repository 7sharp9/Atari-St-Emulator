"""lever_operate.py [operate|control]: the TUNNEL lever (object 144, slot 1's door) operated through the player's own action panel.

Start: scratchpad/cadaver/room2_tunnel_entry.snap (room 1 = TUNNEL, hero bbox (20,12,14,6)).  Natural joystick input only, nothing injected:
Left holds the hero to the stall at (14,12,8,6), one step short of the lever's box (7,15,5,12), where the fire probe returns object 144 with the icon
list 7, 11, 6; fire held opens the panel (`$009c82`), icon 7 (operate, `$00a448` -> `$00a486`, event 5) is confirmed with fire; the consumer runs the lever's
event-5 block (`30` COND state bit 0, `15` ELSE branch: `10` CLEAR FLAG n of the type-4 record, sound, `32` state bit 0 = 1).  Then Up holds the hero out of
the TUNNEL into room 2 and Left into room 3.

  operate  the sequence above; prints the hits on the action path, the lever record before/after, the type-4 flag bytes that changed (the RAM diff
           outside the stack, the display and the queue ring) and the room after each walk
  control  the same walks without the panel: Up leaves the hero where it is (14,12,8,6), room 1

  jump     not the lever's mechanism: from x trail 16 (right 24,000 steps) hold fire+left; the jump carries the hero over the lever at base z 34 (its top is 33) and it
           lands on it; every frame it stands there `$008870` queues the touch event 9 (`$008a02`, `$008a26`): 11 passes in 600,000 steps, 0 in the
           ground-level approach. The lever record stays 0 (it has no event-9 block).

    python reversing/cadaver/py/secrets/overlay/action/lever_operate.py [operate|control|jump]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drv import *
control = len(sys.argv) > 1 and sys.argv[1] == 'control'
if len(sys.argv) > 1 and sys.argv[1] == 'jump':
    r = Repl('scratchpad/cadaver/room2_tunnel_entry.snap')
    tbl = r.l(A5 + 56); p10 = int.from_bytes(r.mem(tbl + 0x46 + 10, 4), 'big')
    joy(r, RIGHT); r.cmd('s 24000'); joy(r, 0); r.cmd('s 40000')
    joy(r, FIRE | LEFT); tot = {0x8a02: 0, 0x8a26: 0}; released = False
    for i in range(120):
        for k, v in r.hits(5000, *tot).items(): tot[k] += v
        if not released and pos(r)[2] <= 7: joy(r, 0); released = True
    print('pos', pos(r), 'z', tuple(r.mem(0x3833c, 2)), 'touch branch $8a02:', tot[0x8a02], 'event-9 push $8a26:', tot[0x8a26], 'lever byte 3:', r.mem(p10, 4)[3])
    r.close(); sys.exit()
r = Repl('scratchpad/cadaver/room2_tunnel_entry.snap'); t = Tally(r)
tbl = r.l(A5 + 56); p10 = int.from_bytes(r.mem(tbl + 0x46 + 10, 4), 'big')
p = walk(r, LEFT, max_steps=1500000)
print('stall', p, 'probe', end=' '); res = probe(r); print((res[0], res[1]) if res else None)
b0 = r.mem(p10, 0x10)
r.snap(OUT + 'lever_before.snap')
if not control:
    open_panel(r, t); print('icons', icons(r))
    path = pick_icon_id(r, t, 7)
    t.run(600000)
    print('hits', {hex(k): v for k, v in sorted(t.tot.items()) if v and k in (0xa448, 0xa486, 0xfe24, 0xfe30, 0x9c82, 0xa08c)})
    print('lever record byte 3:', b0[3], '->', r.mem(p10, 0x10)[3])
    r.snap(OUT + 'lever_after.snap')
for mv, nm in ((UP, 'U'), (LEFT, 'L'), (UP, 'U')):
    pp = walk(r, mv, max_steps=1500000); print(nm, 'pos', pp, 'room', r.w(A5 + 1166), flush=True)
r.close()
if not control:
    import numpy as np
    off = 5 + 19 * 4 + 2 + 4
    a = np.frombuffer(open(OUT + 'lever_before.snap', 'rb').read()[off:off + 0x100000], np.uint8)
    b = np.frombuffer(open(OUT + 'lever_after.snap', 'rb').read()[off:off + 0x100000], np.uint8)
    d = np.nonzero(a != b)[0]
    print('changed bytes', len(d), 'outside the A5 block, screens and stack:',
          [(hex(int(i)), hex(int(a[i])), hex(int(b[i]))) for i in d if not (A5 - 0x200 <= i < A5 + 0x1400 or 0x70000 <= i < 0x80000 and False)][:40])
