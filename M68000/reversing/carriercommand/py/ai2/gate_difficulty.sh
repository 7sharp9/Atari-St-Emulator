#!/bin/bash
# Gate for ai.md section 6: island 56's missile site against the player carrier 20,000 away, same snapshot and
# 16M steps, only difficulty $446 (and the values $18da6 derives from it) changed. Expect 0, 2, 0 launches ($19cc6).
here=$(cd "$(dirname "$0")" && pwd)
root=$here; while [ ! -f "$root/tools/rdis.py" ]; do root=$(dirname "$root"); done
work=${CARRIER_WORK:-$root/scratchpad/carrier}
z=$(printf '%x' $((0x2c0000 + 0x2d10 + 0x4e20)))
ok=0
for arm in 0:0 6000:2 c000:0; do
  d=${arm%:*}; want=${arm#*:}
  got=$(uv run --project "$root" python -I "$here/defence.py" "$work/ai2/st56.snap" 16000000 5e96c:4:$z 11cc:2:0 62eca:2:2 diff=$d \
        | grep -o '"addr": "\$019cc6", "count": [0-9]*' | awk '{print $4}')
  echo "difficulty \$$d: missile-site launches $got (want $want)"; [ "$got" = "$want" ] && ok=$((ok+1))
done
echo "difficulty arms $ok/3"
