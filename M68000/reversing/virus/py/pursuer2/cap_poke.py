"""Labelled-poke capture for the two-hit pursuer's ground paths (every poke is a poke: a result reached through it is not a played result).

    uv run python cap_poke.py <snapshot> <ticks> <out.json> <mode> <poke_tick>

modes: none (the same-snapshot control, no poke)
       ground1  set y of the last live `$2202c` record to the ground height under it at <poke_tick> (the walker's own test then fires)
       dgnd     the same on the last `$221ac` record (stun count unchanged)
       dgnd3    the same, life := 3 (stun count 3, hit bit cleared: a ground contact with no shot)
       dgnd0    the same on the last `$221ac` record and its stun count := 0 (no hit bit)
The captured row for <poke_tick> carries the poked pool and 'poked': [slot, mode]. Output as cap_nat.py's, plus 'poke'."""
import json, os, struct, sys, time
here = os.path.dirname(os.path.abspath(__file__))
import pursuer2 as M
S = M.S
sys.path.insert(0, os.path.join(M.PY, 'mpc'))
import shot_capture as C
C.EV.update({0x22164: 'p2_hit1', 0x20206: 'provoke', 0x201b4: 'provoke_entry'})
snap, N, out, mode, kp = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5])
hm = {}
info = {}
def hook(g, k, row):
    w = row['wave']
    if w not in hm:
        hm[w] = g.s('read', addr=0x42a58, len=0x10000)
    row['hw'] = w
    if mode == 'none' or k != kp:
        return
    S._HMAP = bytes.fromhex(hm[w])
    pool = S.unpack_pool(row['pool'])
    beh = M.P2 if mode == 'ground1' else M.DAMAGED
    js = [j for j, a in enumerate(pool) if a[8] == beh]
    if not js:
        info['err'] = 'no record'; return
    j = js[-1]; a = pool[j]
    gh = S.aground(a[0], a[2])
    g.s('poke', addr=0x31d54 + 20 * j + 2, width=2, value=gh & 0xffff)
    new = list(a); new[1] = gh
    if mode == 'dgnd3':
        g.s('poke', addr=0x31d54 + 20 * j + 12, width=2, value=3); new[6] = 3
    if mode == 'dgnd0':
        g.s('poke', addr=0x31d54 + 20 * j + 12, width=2, value=0); new[6] = 0
    raw = bytearray(bytes.fromhex(row['pool']))
    raw[20 * j:20 * j + 20] = struct.pack('>8hL', *new)
    row['pool'] = raw.hex(); row['poked'] = [j, mode]
    info.update(slot=j, before=a, after=new)
t0 = time.time()
cap = C.capture('auto', N, snap=snap, hook=hook)
for q in ('map0', 'map1', 'hmap'):
    cap.pop(q, None)
cap['hmaps'] = hm; cap['poke'] = {'mode': mode, 'tick': kp, **info}
json.dump(cap, open(out, 'w'))
print(len(cap['rows']), 'ticks', round(time.time() - t0), 's', cap['poke'])
