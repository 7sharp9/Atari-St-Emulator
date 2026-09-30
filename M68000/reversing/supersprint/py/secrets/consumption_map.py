"""consumption_map.py - merge the poison-scan results into one map of SUPER.DAT (in-place buffer at $28e00) per 4 KB block:
   B = consumed at boot (bootpoison_SUPER.json, any 2 KB sub-block with diffs outside its own buffer)
   A = attract loop (runtime_poison_attract.json)   R = race track (runtime_poison_race.json)   M = menus (runtime_poison_menus.json)
   0..7 = per-track race runs (runtime_poison_trackN.json, only candidate blocks)
Blocks with none of the flags are never consumed in any scenario tested."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import AGENT
def load(name):
    p = os.path.join(AGENT, name)
    return {e['lo'] - 0x28e00: e['diff'] for e in json.load(open(p))} if os.path.exists(p) else None
boot = {}
pb = os.path.join(AGENT, 'bootpoison_SUPER.json')
if os.path.exists(pb):
    for e in json.load(open(pb)): boot[e['off']] = e['diff_outside_buffer']
scen = {'A': load('runtime_poison_attract.json'), 'R': load('runtime_poison_race.json'), 'M': load('runtime_poison_menus.json')}
for t in range(8): scen[str(t)] = load('runtime_poison_track%d.json' % t)
for k, n in (('o', 'opt'), ('s', 'select'), ('p', 'shop'), ('h', 'hiscore')): scen[k] = load('runtime_poison_%s.json' % n)   # o=options s=select-track p=shop h=hi-score entry
rows = []
unused_bytes = 0
for off in range(0, 0x33e2a, 0x1000):
    flags = ''
    if any(boot.get(o, 0) for o in range(off, off + 0x1000, 0x800)): flags += 'B'
    for k, d in scen.items():
        if d is not None and d.get(off, 0): flags += k
    tested = ''.join(k for k, d in scen.items() if d is not None and off in d)
    rows.append((off, flags, tested))
    if not flags and off < 0x30900: unused_bytes += 0x1000
print('SUPER.DAT offset  flags(consumed by)  scenarios that tested the block')
for off, fl, te in rows: print('%06x-%06x  %-12s %s' % (off, min(off + 0x1000, 0x33e2a), fl or '-- NEVER --', te))
print('4KB blocks of the in-place region never consumed in any tested scenario:', unused_bytes // 0x1000, '(%d bytes)' % unused_bytes)
