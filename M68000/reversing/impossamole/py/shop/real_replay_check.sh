#!/bin/zsh
# Chain check for hop3 + hop4 real-input route (pass103/room188.snap -> boss room 318..326).
# 1. each real_<seg> replays byte-identical from its start snapshot (start of seg1 = hop3's room299.snap);
# 2. ONE process: hop3's route_full.repl + real_seg1..5 .repl from pass103/room188.snap -> boss_room_real.snap,
#    cmp against real_seg5_pit_exit.snap (segment-chained) and the mid snapshot against hop3's room299.snap.
cd "${0:A:h}/../../../.."
D=scratchpad/impossamole/agents/hop4
H3=scratchpad/impossamole/agents/hop3
DISK="scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st"
SEGS=(real_seg1_ladder_a real_seg2_traverse_b real_seg3_tunnel_hop real_seg4_wall_hop real_seg5_pit_exit)
SETTLE=real_seg6_boss_settle
rewrite() { sed -E "s#^snap .*/([^/]*)\$#snap $D/replay_\1#" $1; }
run() { ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume $1 repl --disk-a "$DISK" < $2 > /dev/null 2>&1 }
prev=$H3/room299.snap
for n in $SEGS; do
  { rewrite $D/$n.repl; echo q; } > $D/replay_$n.repl
  run $prev $D/replay_$n.repl
  cmp $D/$n.snap $D/replay_$n.snap && echo "$n: replay byte-identical"
  prev=$D/$n.snap
done
# combined single-process replay: hop3's file has trailing `q`; its snap line becomes replay_room299_mid.snap
{ grep -v '^q$' $H3/route_full.repl | sed -E "s#^snap .*/([^/]*)\$#snap $D/replay_mid_\1#"
  for n in $SEGS; do rewrite $D/$n.repl; done
  echo "snap $D/boss_room_real.snap"
  rewrite $D/$SETTLE.repl | sed -E "s#replay_$SETTLE.snap#boss_room_real_settled.snap#"
  echo q; } > $D/route_full_real.repl
run scratchpad/impossamole/pass103/room188.snap $D/route_full_real.repl
cmp $H3/room299.snap $D/replay_mid_room299.snap && echo "combined: mid snapshot == hop3 room299.snap"
run $D/real_seg5_pit_exit.snap <({ rewrite $D/$SETTLE.repl; echo q; }) 
cmp $D/$SETTLE.snap $D/replay_$SETTLE.snap && echo "$SETTLE: replay byte-identical"
cmp $D/$SETTLE.snap $D/boss_room_real_settled.snap && echo "combined: boss_room_real_settled.snap == segment-chained $SETTLE.snap"
cmp $D/real_seg5_pit_exit.snap $D/boss_room_real.snap && echo "combined: boss_room_real.snap == segment-chained real_seg5_pit_exit.snap"
