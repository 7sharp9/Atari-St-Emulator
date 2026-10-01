"""Open the info panel of bucket-walk records of every (category, byte7) through $95f6 (the click dispatcher) and print it.
python survey.py <snap> [per_combo=1] [catfilter-hex ...]"""
import sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'reversing/powermonger/py'))
from uilib import *
from census import walk
snap = sys.argv[1]; per = int(sys.argv[2]) if len(sys.argv) > 2 else 1
want = {int(x, 16) for x in sys.argv[3:]}
base = ram_of(snap)
recs, torn = walk(base)
combos = collections.defaultdict(list)
for o, cx, cy, rec in recs: combos[(rec[6], rec[7])].append(o)
print('(byte6,byte7): count', {(hex(a), hex(b)): len(v) for (a, b), v in sorted(combos.items())})
calls = []; meta = []
for (c, b7), lst in sorted(combos.items()):
    if want and c not in want: continue
    for a in lst[:per]:
        calls += ['w 2df96 00010001', f'callcap 95f6 60000 A3={a:x}']; meta.append((c, b7, a))
ccs = parse_callcaps(repl(snap, calls))
for (c, b7, a), cc in zip(meta, ccs):
    print(f'--- byte6 {c:#x} byte7 {b7:#x} record ${a:x} returned={cc["returned"]} changed={len(cc["mem"])}')
    t = panel_text(base, cc) if cc['mem'] else None
    if t: print('\n'.join(t))
