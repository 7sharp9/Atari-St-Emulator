#!/bin/bash
# seeds.sh <out dir> <snap> <side> "<offsets, M steps>" "<arms>" [par] [budget]: one land played by several policies
# from several starts, so a land's outcome is a rate, not one chaotic run (README "Evaluation across seeds").
# Start k is <snap> advanced <offset k> million steps with no orders and the slot not taken (loop.py --policy none
# --no-take), so the starts differ only by the game's own clock. That spreads a policy arm (its orders fall at other
# ticks) but not an unpoked arm (--policy none --no-take), which then plays one trajectory shifted in time; startpoke.py
# shows the RNG and the dice counter do not spread it either (README "Policies against the game's AI"), so score a
# policy's starts against that one AI outcome with pairs.py. An arm is a name and its loop.py flags,
# name=flags with commas for spaces ("scripted=--policy,scripted", "evade=--policy,scripted,--evade").
# Each run is <out>/<arm>/o<offset>; `python3 commander/runstat.py <out>/*/o*` reads them all.
# par (default 4) runs at once: a rollout arm starts --par 5 workers of its own, so count it as 6.
d=$(cd "$(dirname "$0")" && pwd); R=$d; while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "$R"; L=reversing/powermonger/commander/loop.py
O=$1; SNAP=$2; SIDE=$3; OFFS=$4; ARMS=$5; PAR=${6:-4}; BUDGET=${7:-2000e6}
mkdir -p $O/start
for o in $OFFS; do
  [ -f $O/start/o$o/final.snap ] && continue
  if [ "$o" = 0 ]; then mkdir -p $O/start/o0; cp $SNAP $O/start/o0/final.snap; continue; fi
  echo "$L $O/start/o$o --snap $SNAP --side $SIDE --budget ${o}e6 --policy none --no-take"
done | xargs -P $PAR -I{} sh -c 'python3 {} > /dev/null 2>&1'
for a in $ARMS; do
  n=${a%%=*}; f=$(echo ${a#*=} | tr , ' ')
  for o in $OFFS; do
    [ -f $O/$n/o$o/final.snap ] && continue
    echo "$L $O/$n/o$o --snap $O/start/o$o/final.snap --side $SIDE --budget $BUDGET $f"
  done
done | xargs -P $PAR -I{} sh -c 'python3 {} > /dev/null 2>&1'
