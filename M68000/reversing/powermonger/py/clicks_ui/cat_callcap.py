"""cat_callcap.py <snap> <byte6-hex> ... : `callcap $95f6` (the examine-tool dispatcher) on the first
bucket-walk record of each byte6 category and print the panel text it builds. The panel text names the
opener the cjt table $9624 chose (0x4 tree $a738, 0xc death $a46c, 0x1e mine $a5d8, 0x2c stockpile $9656).
callcap gives no per-handler hit table, so the text is the evidence; click_hits.sh gives hit counts for
real clicks. Root: $M68000_ROOT, else five levels up (M68000/). Side effect: ui/uilib.ram_of writes a
`<snap>.ram` cache next to every snapshot it reads (e.g. pm143/run/p0k0_s3.ram); delete them freely.
Raw REPL output goes to scratchpad/clicks_ui/cat_callcap_raw.txt.
  python cat_callcap.py scratchpad/pm143/run/p0k0_s4.snap 1e 2c 4    (mine, stockpile, tree)
  python cat_callcap.py scratchpad/pm143/run/p0k0_s3.snap c          (death)"""
import sys, os
from pathlib import Path
ROOT = Path(os.environ.get('M68000_ROOT') or Path(__file__).resolve().parents[4])
sys.path.insert(0, str(ROOT / 'reversing/powermonger/py/ui')); sys.path.insert(0, str(ROOT / 'reversing/powermonger/py'))
from uilib import *
from census import walk
snap = sys.argv[1]; want = [int(x, 16) for x in sys.argv[2:]]
base = ram_of(snap)
recs, torn = walk(base)
pick = {}
for o, cx, cy, rec in recs:
    pick.setdefault(rec[6], o)
calls = []; meta = []
for c in want:
    if c in pick:
        calls += ['w 2df96 00010001', f'callcap 95f6 60000 A3={pick[c]:x}']; meta.append((c, pick[c]))
out = repl(snap, calls)
rawdir = ROOT / 'scratchpad/clicks_ui'; rawdir.mkdir(parents=True, exist_ok=True)
(rawdir / 'cat_callcap_raw.txt').write_text(out)
ccs = parse_callcaps(out)
print('callcaps parsed', len(ccs), 'of', len(meta))
for (c, a), cc in zip(meta, ccs):
    print(f'--- byte6 {c:#x} rec ${a:x} returned={cc["returned"]} changed={len(cc["mem"])}')
    t = panel_text(base, cc) if cc['mem'] else None
    if t: print('\n'.join(t))
