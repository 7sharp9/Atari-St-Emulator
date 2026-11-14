#!/bin/bash
# Gate for vehicles.md: carrier motion (manual rudder with a grounding, and autopilot), arctangent grid, repair
# scheduler, flare decoy capture, Manta take-off. Every run resumes c_s30.snap with REPL pokes; no snapshot is written.
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
# Manta take-off ($1d22c): lift and launch through the game's own handlers, then the model per tick, with the
# carrier at rest and with it turning and accelerating (the run that exercises the heading and the speed hand-off)
$py "$here/takeoff_proof.py" "$S" | grep '^takeoff ticks' | awk '{printf "takeoff at rest %d/%d\n", $5, $3}'
$py "$here/takeoff_proof.py" "$S" 644=00400000:4 648=00300000:4 > "${TMPDIR:-/tmp}/cc_takeoff.$$" 2>&1
grep '^takeoff ticks' "${TMPDIR:-/tmp}/cc_takeoff.$$" | awk '{printf "takeoff carrier turning %d/%d\n", $5, $3}'
grep '^controls broken' "${TMPDIR:-/tmp}/cc_takeoff.$$" | awk '{printf "takeoff controls %s\n", $3}'
rm -f "${TMPDIR:-/tmp}/cc_takeoff.$$"
# Manta airborne autopilot ($1d354 + the shared flight code, flight_proof.py) from m_takeoff.snap: the launch flight,
# a high cruise speed with a target above the 3500 ceiling, and a low hull with a target below take-off altitude.
# A constant counts as controlled when nudging it breaks a tick in at least one of the three runs.
M=$work/manta/m_takeoff.snap
t=${TMPDIR:-/tmp}/cc_flight.$$
$py "$here/flight_proof.py" "$M" 300 > "$t.a" 2>&1
$py "$here/flight_proof.py" "$M" 400 4c2=00c8:2 4ba=00000fa0:4 > "$t.b" 2>&1
$py "$here/flight_proof.py" "$M" 400 4ac=0100:2 4ba=0000012c:4 > "$t.c" 2>&1
for k in a:launch b:ceiling c:low-hull; do
  grep '^flight ticks' "$t.${k%%:*}" | awk -v n="${k#*:}" '{printf "flight %s %d/%d\n", n, $5, $3}'
done
cat "$t.a" "$t.b" "$t.c" | awk '$1=="control"{split($5,r,"/"); key=$2; seen[key]=1; if (r[1]<r[2]) br[key]=1}
  END{n=0; b=0; for (k in seen) {n++; if (k in br) b++; else u=u" "k}; printf "flight controls %d/%d (unexercised:%s)\n", b, n, u}'
rm -f "$t.a" "$t.b" "$t.c"
# Manta fuel ($1ce56, every 16th frame by $8fb; fuel_proof.py), full hull and hull 256 (the +$100 branch)
$py "$here/fuel_proof.py" "$M" 300 | grep '^fuel ticks' | awk '{printf "fuel full hull %d/%d\n", $5, $3}'
$py "$here/fuel_proof.py" "$M" 300 4ac=0100:2 | grep '^fuel ticks' | awk '{printf "fuel low hull %d/%d\n", $5, $3}'
# Manta deck landing ($11bf6 land command, state 0 phases 0-4, $1cfc2; landing_proof.py) from m_air.snap: carrier at
# rest (then the lift-down command $11f3c to the hangar), carrier turning, and from 12,000 out at altitude 400 (the
# far leg at speed 200, the hull speed limit and the climb). Controls as for the flight runs.
A=$work/manta/m_air.snap
t=${TMPDIR:-/tmp}/cc_land.$$
$py "$here/landing_proof.py" --stow "$A" 250 > "$t.a" 2>&1
$py "$here/landing_proof.py" "$A" 400 644=00400000:4 648=00300000:4 > "$t.b" 2>&1
$py "$here/landing_proof.py" "$A" 500 5df64=ff8f1ee0:4 5df68=00000190:4 > "$t.c" 2>&1
for k in a:rest b:carrier-turning c:far-low; do
  grep '^landing ticks' "$t.${k%%:*}" | awk -v n="${k#*:}" '{printf "landing %s %d/%d\n", n, $5, $3}'
done
grep '^stow:' "$t.a" | sed 's/;.*//'
cat "$t.a" "$t.b" "$t.c" | awk '$1=="control"{split($5,r,"/"); key=$2; seen[key]=1; if (r[1]<r[2]) br[key]=1}
  END{n=0; b=0; for (k in seen) {n++; if (k in br) b++; else u=u" "k}; printf "landing controls %d/%d (unexercised:%s)\n", b, n, u}'
rm -f "$t.a" "$t.b" "$t.c"
# Manta runway touchdown on island 0's airstrip (runway_proof.py, from m_air.snap): one tick either side of every
# limit of the touchdown test, then the taxi and parking (states 4 and 5) per tick from a lined-up approach and from
# a skewed slow one. Controls as for the flight runs (clr_bug: the $1d53e clr.w side effect, switched off).
t=${TMPDIR:-/tmp}/cc_runway.$$
$py "$here/runway_proof.py" window | grep '^window cases' | awk '{printf "runway window %d/%d\n", $5, $3}'
$py "$here/runway_proof.py" taxi 400 > "$t.a" 2>&1
$py "$here/runway_proof.py" taxi 450 150 -3500 120 3000 40 > "$t.b" 2>&1
for k in a:lined-up b:skewed; do
  grep '^taxi ticks' "$t.${k%%:*}" | awk -v n="${k#*:}" '{printf "taxi %s %d/%d\n", n, $5, $3}'
done
cat "$t.a" "$t.b" | awk '$1=="control"{split($5,r,"/"); key=$2; seen[key]=1; if (r[1]<r[2]) br[key]=1}
  END{n=0; b=0; for (k in seen) {n++; if (k in br) b++; else u=u" "k}; printf "taxi controls %d/%d (unexercised:%s)\n", b, n, u}'
rm -f "$t.a" "$t.b"
