#!/bin/sh
# itemrun.sh <drop hex> <cody hp hex> -> prints item type, hp before/after, score before/after, pickup frames
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
OUT=${FFP_OUT:-$root/scratchpad/finalfight/p3/f/out}; export FFP_OUT=$OUT
d=$1; h=$2
FF_KILL=1 FF_KEEP=99 FF_HEAL=0 FF_GOD=1 FF_CHP=$h FF_DROP=$d FF_POKES=$here/pokes_prop_w.lua FF_EXTRA=$here/extra_follow.lua $here/run.sh item_${d}_$h w3 220 >/dev/null
python3 - "$OUT/item_${d}_$h.txt" "$d" "$h" <<'PY'
import sys
fn,d,h=sys.argv[1:4]
rows=[]; 
for l in open(fn):
    if l[0] in 'EQ': continue
    p=l.split(); r={t.split('=')[0]:t.split('=')[1] for t in p[2:] if '=' in t}; r['rel']=int(p[1]); rows.append(r)
a=rows[100]; b=rows[200]
pick=[r['rel'] for r in rows if r['sub']=='18']
print('drop %s cody-hp %s: hp %s -> %s  score(+134) %s -> %s  pickup sub18 frames %s'%(d,h,a['hp'][:4],b['hp'][:4],a['scH']+a['sc'],b['scH']+b['sc'],(pick[0],pick[-1]) if pick else None))
PY
