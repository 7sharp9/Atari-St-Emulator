"""Boss contact damage (agents/boss): hop over the step into the boss's box and log health drops with the live
objects, to separate contact damage (104(A0) of the boss = 1, `bsr $e80e` at $15eb6) from the boss's shots.

    uv run python reversing/impossamole/py/boss/contact_check.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from repl import Repl, slot, w, sw

r = Repl('scratchpad/impossamole/pass99/boss_room.snap')
r.run('w bb74 12120300', 'kbd ff', 'kbd 08')
while sw(r.mem(0x1a572, 108), 2) < 168:
    r.run('s 20000')
r.run('kbd ff', 'kbd 00', 's 60000')
# hop only when no boss shot is alive (slots 12-15 empty), so any damage is contact
for attempt in range(400):
    b = slot(r, 7)
    if not any(w(slot(r, n), 0) for n in range(12, 16)) and int.from_bytes(b[22:26], 'big') != 0x221f6 and sw(b, 2) == 224:
        break
    r.run('w bb74 12120300', 's 24000')
r.run('w bb74 12120300')
h0 = r.mem(0xbb74, 1)[0]
r.run('kbd ff', 'kbd 09', 's 30000', 'kbd ff', 'kbd 08')
last = h0
seen_air = False
for i in range(120):
    r.run('s 6000')
    h = r.mem(0x1a572, 108)
    hp = r.mem(0xbb74, 1)[0]
    b = slot(r, 7)
    shots = [(n, sw(slot(r, n), 2), sw(slot(r, n), 4)) for n in range(12, 16) if w(slot(r, n), 0)]
    if os.environ.get('DBG'):
        print(i, sw(h,2), sw(h,4), r.mem(0x227f3,1)[0], 'boss', sw(b,2), sw(b,4), hex(int.from_bytes(b[22:26],'big')), b[100], b[101], b[102], 'hero102', h[102])
    if hp != last:
        print(f'health {last}->{hp} at hero ({sw(h,2)},{sw(h,4)}) box x={sw(h,2)+sw(h,8)}..{sw(h,2)+sw(h,8)+h[12]} '
              f'y={sw(h,4)+sw(h,10)}..{sw(h,4)+sw(h,10)+h[13]}; boss box x={sw(b,2)}..{sw(b,2)+b[12]} y={sw(b,4)}..{sw(b,4)+b[13]} '
              f'boss 104={b[104]} shots={shots}')
        last = hp
    st = r.mem(0x227f3, 1)[0]
    seen_air = seen_air or st == 2
    if seen_air and st in (0, 1):
        break
print('boss anim at hop', hex(int.from_bytes(slot(r,7)[22:26],'big')))
print('start health', h0, 'end', last)
r.run('kbd ff', 'kbd 00')
r.close()
