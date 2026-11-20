"""POKE EXPERIMENT (not natural play): first life of a chain game with one pilot-output rule changed at each tick arrival $255d4
(D2 bit 1, thrust, cleared when the ship's vy word < -CUT, i.e. rising faster than CUT; CUT=none leaves the pilot alone as a control).
    uv run python cut_rising.py <game> <CUT|none> [max ticks]
Prints one JSON line: tick and cause of the first life loss ($25ad2 ground / $25ad8 without it: flag or object), fuel at the loss,
ticks with thrust asked, ticks cut.  The registers are set through stserver `set_reg` exactly as py/mpc/replay.py overwrites D0..D2."""
import os, sys, json, struct
here = os.path.dirname(os.path.abspath(__file__)); ROOT = here
while not os.path.exists(os.path.join(ROOT, 'tools', 'rdis.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from stclient import StServer
game = int(sys.argv[1]); cut = None if sys.argv[2] == 'none' else int(sys.argv[2]); maxt = int(sys.argv[3]) if len(sys.argv) > 3 else 9000
hx = lambda v: int(str(v).lstrip('$'), 16)
s = StServer(ROOT); s('load', snapshot=os.path.join(ROOT, f'scratchpad/virus/chain/long100/starts/main_g{game:03d}.snap'))
s('bp_set', addrs=[0x255d4, 0x25ad2, 0x25ad8, 0x25ba0])
u16 = lambda a: int.from_bytes(s.read(a, 2), 'big')
last = {}; asked = cutn = 0; res = None; seen25ad2 = None
while True:
    r = s('run', max_steps=20_000_000)
    if r['reason'] != 'breakpoint': res = dict(end=r['reason']); break
    g = s('regs'); pc = hx(g['pc']); st = g['step'] if isinstance(g['step'], int) else hx(g['step'])
    if pc in last and st - last[pc] < 2000: continue
    last[pc] = st
    if pc == 0x255d4:
        tick = u16(0x32a44)
        if tick > maxt: res = dict(end='maxticks'); break
        d2 = hx(g['d2']) & 0xffff
        if d2 & 2: asked += 1
        vy = struct.unpack('>h', s.read(0x270b8, 2))[0]
        if cut is not None and (d2 & 2) and vy < -cut and u16(0x32a2e) > 0:
            s('set_reg', name='d2', value=(hx(g['d2']) & ~2)); cutn += 1
    elif pc == 0x25ad2: seen25ad2 = st
    elif pc == 0x25ad8:
        if seen25ad2 is not None and st - seen25ad2 < 100: kind = 'ground'
        else: kind = 'flag' if s.read(0x62a5d, 1)[0] else 'object'
        res = dict(kind=kind, tick=u16(0x32a44), fuel=u16(0x32a2e), wave=u16(0x32a50)); break
res.update(game=game, cut=cut, asked=asked, cut_ticks=cutn)
print(json.dumps(res)); s.close()
