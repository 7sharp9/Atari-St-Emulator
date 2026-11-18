"""Checks 1 and 2: replay the controls of cap/flight_bp.txt (120 `bp 255d4` stops) from fl/f1.snap and compare with
the capture's own states; then the same with the thrust bit cleared.

The capture ran `mouse move 15 -10`, `s 3000`, then 120 x `bp 255d4`. The first arrival at $255d4 is 1003 steps into
the snapshot, inside the `s 3000`, so capture stop j (0-based) is replay arrival j + 1. Tick 0's controls are not in
the capture (see below).

    uv run python check_capture.py            (writes check1_controls.json, check1_out.json, check2_out.json)
"""
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay as R

here = os.path.dirname(os.path.abspath(__file__))
cap = os.path.join(R.ROOT, 'scratchpad', 'virus', 'cap', 'flight_bp.txt')

# --- parse the capture as virus_flight.py does
stops = []; cur = None
for l in open(cap).read().split('\n'):
    if l.startswith('--- breakpoint'):
        cur = {'mem': [], 'reg': {}}; stops.append(cur)
    if cur is not None:
        for k, v in re.findall(r'([DA]\d):([0-9a-f]{8})', l):
            cur['reg'][k] = int(v, 16)
        if re.fullmatch(r'([0-9a-f]{2} )*[0-9a-f]{2}', l.strip()):
            cur['mem'].append(bytes.fromhex(l.strip().replace(' ', '')))
print(f'capture: {len(stops)} stops; first stop mem {[m.hex() for m in stops[0]["mem"][:4]]}')
capst = []
for s in stops:
    pv = struct.unpack('>6h', s['mem'][0])
    capst.append({'pos': list(pv[:3]), 'vel': list(pv[3:]), 'att': list(struct.unpack('>2h', s['mem'][1])),
                  'fuel': struct.unpack('>h', s['mem'][3])[0],
                  'd': [s['reg'][k] & 0xffff for k in ('D0', 'D1', 'D2')]})

# --- tick 0's controls in the capture run. The capture's build delivered the mouse packet before arrival 0; the
# current build delivers IKBD bytes 768 steps apart, so the same REPL lines now give D0 = $1398, D1 = $c000 at
# arrival 0 (run: mouse move 15 -10 / bp 255d4 / r). Tick 0 is therefore given the capture's stop-0 inputs
# ($2176, $d2e3, 2), which is an inference: it is the choice that makes arrival 1 equal capture stop 0. The other
# 119 comparisons use only inputs the capture recorded.
controls = [capst[0]['d']] + [c['d'] for c in capst]
json.dump(controls, open(os.path.join(R.WORK, 'check1_controls.json'), 'w'))


def compare(out, label):
    n = {'pos': 0, 'vel': 0, 'att': 0, 'fuel': 0, 'all': 0}; N = 0; first = None
    for j, c in enumerate(capst):
        if j + 1 >= len(out['ticks']):
            break
        t = out['ticks'][j + 1]; N += 1
        e = {k: t[k] == c[k] for k in ('pos', 'vel', 'att', 'fuel')}
        for k in e:
            n[k] += e[k]
        allok = e['pos'] and e['vel'] and e['att']
        n['all'] += allok
        if not allok and first is None:
            first = j + 1
    print(f'{label}: capture states compared {N}; ' + ', '.join(f'{k} {v}/{N}' for k, v in n.items()) +
          f'; first differing arrival: {first}')
    return first


out = R.replay(controls)
json.dump(out, open(os.path.join(R.WORK, 'check1_out.json'), 'w'))
print(f'check 1 replay: {len(controls)} controls, {len(out["ticks"])} states, complete {out["complete"]}, '
      f'{out["seconds"]} s; paths {sorted({p for t in out["ticks"] for p in t.get("path", [])})}; '
      f'ext-write ticks {sum(1 for t in out["ticks"] if t.get("ext"))}')
print('  raw: replay arrival 1', out['ticks'][1]['pos'], out['ticks'][1]['vel'], out['ticks'][1]['att'],
      '| capture stop 0', capst[0]['pos'], capst[0]['vel'], capst[0]['att'])
print('  raw: replay arrival 120', out['ticks'][120]['pos'], out['ticks'][120]['vel'], out['ticks'][120]['att'],
      '| capture stop 119', capst[119]['pos'], capst[119]['vel'], capst[119]['att'])
compare(out, 'check 1 (positive control)')

# game's own inputs with no overwrite and no mouse move: shows that the overwrite, not the game's input, drives it
own = R.replay([None] * len(controls))
compare(own, 'no overwrite, no mouse move (control of the control)')

ctl2 = [[d0, d1, d2 & ~2] for d0, d1, d2 in controls]
out2 = R.replay(ctl2)
json.dump(out2, open(os.path.join(R.WORK, 'check2_out.json'), 'w'))
print(f'check 2 replay: {len(out2["ticks"])} states, complete {out2["complete"]}, end {out2["end"]}; '
      f'thrust ticks in the capture controls: {sum(1 for c in controls if c[2] & 2)}/{len(controls)}')
compare(out2, 'check 2 (thrust bit cleared)')
