#!/usr/bin/env bash
# pos.sh <snap> <out> [stops]: at a $f898 snapshot, every $11f78 entry of the coming frame: step, D0, D1, D2, A3
d=$(cd "$(dirname "$0")" && pwd)
while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); [ "$d" = / ] && { echo "no repo root"; exit 1; }; done
cd "$d"
snap=$1; out=$2; n=${3:-45}
{ echo "disk scratchpad/powermonger.st"; for i in $(seq "$n"); do echo "bp 11f78 3000000"; echo r; done; echo q; } > "$out.repl"
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$snap" repl < "$out.repl" > "$out.out" 2>&1
python3 - "$out.out" <<'PY'
import re,sys
t=open(sys.argv[1]).read(); step=0
for blk in t.split('--- breakpoint')[1:]:
    m=re.match(r' \$(\w+) hit .*? after (\d+) step',blk); step+=int(m.group(2))
    g=lambda r:int(re.search(r'%s:(\w{8})'%r,blk).group(1),16)
    print('step %d D0=%08x D1=%08x D2=%04x A3=%05x'%(step,g('D0'),g('D1'),g('D2')&0xffff,g('A3')))
PY
