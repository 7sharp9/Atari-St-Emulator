#!/usr/bin/env bash
# Score every labelled-poke capture of run_cases.sh against the no-poke control
# with the port (diff.fsx, port/godot/logic built first), plus the wrong-frame controls. Each line: the port's changed px the game shows with the
# port's colour, and the game's changed px the port reproduces, after excluding the
# control's own missed px (0 since the port draws the tree birds, SPEC.md §6).
#   score_cases.sh   (repo root found via tools/rdis.py)
set -u
here=$(cd "$(dirname "$0")" && pwd); d=$here
while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); done; cd "$d"
C=${PM_WORK:-scratchpad/pm156}/overlay/cap
D() { local f=$1 n=$2; shift 2
      dotnet fsi "$here/$f" 0 "$C/${n}_0.json+$C/${n}_1.json" "$C/ctl_0.json+$C/ctl_1.json" | tail -1 | sed 's/ | without/\n      without/'; }
for n in plough plough_b7 siege0e siege0f siege10 siege11 melee msiege0e msiege10 b6_28 b6_28neg b6_18 b6_34; do
  echo "== $n"; echo -n "  port: "; D diff.fsx $n
done
echo "== wrong-frame controls"
W() { echo -n "  $1 WRONG=$2: "; WRONG=$2 D diff.fsx $1; }
for n in siege0e siege0f siege10 siege11; do W $n b44:1:51c92,51b98,51d5a,51bca; done
W msiege0e b44:1:51c92,51b98
W plough b17:32:51bca,51bfc
W b6_28 b5:1:51b98,51c92
W b6_18 b15:255:51b98
W b6_34 b7:2:51b98,51c92
W b6_34 b7:16:51b98,51c92
