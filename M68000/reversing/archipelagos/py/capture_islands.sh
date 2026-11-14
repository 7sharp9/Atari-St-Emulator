#!/bin/bash
# Fresh captures for the island gates, from the snapshots py/run_drive.sh writes (scratchpad/archipelagos/).
# Writes isl/ent*.snap + exit*.snap (state at the $15a20 entry and at the $15b8e return) and
# blood/rng_log.txt (every write to the RNG seed $16978 during island 1's build).
# POKEs: the parameter-block sets for "defaults" and "setB" (ww at $1697a..), and ww 1d566 for N=150 / 4321.
d=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$d/tools/rdis.py" ] && [ "$d" != / ]; do d=$(dirname "$d"); done
cd "$d" || exit 1
W=scratchpad/archipelagos; DLL=bin/Debug/net8.0/M68000.dll
run() { ATARI_NOTRACE=1 dotnet exec $DLL resume "$1" repl --disk-a $W/tmb58.st 2>&1 | grep -E "breakpoint|gave|REPL|ILLEGAL"; }
mkdir -p $W/isl $W/blood
# island 1 as loaded from the disk: type a character, Return
run $W/n0.snap <<E2
kbd 02
s 40000
kbd 82
s 100000
kbd 1c
s 40000
kbd 9c
bp 15a20 3000000
snap $W/isl/ent1.snap
bp 15b8e 3000000
snap $W/isl/exit1.snap
q
E2
# the RNG seed's writes during the same build
ATARI_NOTRACE=1 dotnet exec $DLL resume $W/n0.snap repl --disk-a $W/tmb58.st 2>$W/blood/rng_watch.err >/dev/null <<E2
kbd 02
s 40000
kbd 82
s 100000
watch 16978 20
kbd 1c
s 40000
kbd 9c
s 3000000
q
E2
grep -E 'pc=.01(6632|5a96)' $W/blood/rng_watch.err > $W/blood/rng_log.txt
# POKE: parameter block sets, applied at the $15a20 entry
pset() { name=$1; shift; i=0; { for v in "$@"; do printf 'ww %x %s\n' $((0x1697a+2*i)) $v; i=$((i+1)); done
  echo "snap $W/isl/ent_$name.snap"; echo "bp 15b8e 6000000"; echo "snap $W/isl/exit_$name.snap"; echo q; } | run $W/isl/ent1.snap; }
pset defaults 001e 006e 0037 001e 0041 005a 0064 0032 04d2
pset setB 0019 0096 0040 0014 0040 005a 0064 0028 1234
# POKE: island number (> 100 takes the computed path $16166)
for N in 150 4321; do run $W/n2.snap <<E2
ww 1d566 $(printf '%04x' $N)
kbd 39
s 40000
kbd b9
bp 15a20 8000000
snap $W/gen/ent_$N.snap
bp 15b8e 60000000
snap $W/gen/exit_$N.snap
q
E2
done
