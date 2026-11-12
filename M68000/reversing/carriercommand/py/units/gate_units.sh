#!/bin/bash
# Gate for vehicles.md: carrier motion (manual rudder with a grounding, and autopilot), arctangent grid, repair
# scheduler, flare decoy capture. Every run resumes c_s30.snap with REPL pokes; no snapshot is written.
here=$(cd "$(dirname "$0")" && pwd)
root=$here; while [ ! -f "$root/tools/rdis.py" ]; do root=$(dirname "$root"); done
work=${CARRIER_WORK:-$root/scratchpad/carrier}
S=$work/c_s30.snap
py="uv run --project $root python -I"
cd "$root"
$py "$here/carrier_proof.py" "$S" 150 'w 644 00400000' 'w 648 00300000' | grep '^ticks' \
  | awk '{printf "carrier manual %d/%d\n", $4, $2}'
$py "$here/carrier_proof.py" "$S" 600 'w 5e964 ff85c840' 'w 5e96c ff890d10' 'w 5e996 00000000' 'w 640 00000301' \
  'w 650 ff8a5c20' 'w 654 ff8c1a50' 'w 658 00700000' | grep '^ticks' | awk '{printf "carrier autopilot %d/%d\n", $4, $2}'
$py "$here/atan_grid.py" | grep -o 'grid [0-9]* cases; port match [0-9]*' | awk '{printf "atan grid %d/%d\n", $6, $2}'
$py "$here/repair_proof.py" "$S" 10 'w af0 04000fa0' 'w af4 00000100' 'w af8 08000fa0' 'w afc 0000ff00' 'w b00 01000fa0' \
  'w b04 0002ff00' 'w b18 02000fa0' 'w b1c 0001ff00' | grep '^repair calls' | awk '{printf "repair %d/%d\n", $5, $3}'
$py "$here/repair_proof.py" "$S" 12 'w af0 0f800fa0' 'w af4 00000100' 'w b00 0e000fa0' 'w b04 0002ff00' 'w b18 0f000fa0' \
  'w b1c 0001ff00' 'w b30 05dc05dc' 'w b34 00000100' 'w af8 07000fa0' 'w afc 0001ff00' | grep '^repair calls' \
  | awk '{printf "repair high-to-medium %d/%d\n", $5, $3}'
# flare capture: the missile's target pointer (+30) after its first re-target scan, per case
ok=0
chk() { got=$($py "$here/flare_test.py" t "$1" "$2" | awk '$2=="state"{print $9}' | sed -n "${3}p"); [ "$got" = "$4" ] && ok=$((ok+1)); echo "flare $1 $2 call $3: $got (want $4)"; }
chk 6000 none 2 0005f21a
chk 6001 none 2 0005e95a
chk 7000 5000 2 0005f35a
chk 3000 5000 2 0005f35a
chk none none 14 0005e95a
echo "flare cases $ok/5"
