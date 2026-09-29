#!/bin/zsh
# Replays every driven segment of the hop-4 route and of the shop branch from its start snapshot and cmp's each
# end snapshot with the one the live driver wrote; then replays each whole chain (concatenated .repl) in ONE process.
# Run from anywhere: zsh replay_check.sh
cd "${0:A:h}/../../../.."
D=scratchpad/impossamole/agents/hop4
DISK="scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st"
MAIN=(seg1_ladder_a seg2_traverse_b seg3_tunnel_hop seg4_wall_hop seg5_pit_exit)
SHOP=(seg5b_shop_walk seg6b_shop_wait seg7b_shop_enter seg8b_shop_touch seg9b_shop_toomuch seg10b_shop_buy seg11b_shop_exit)
rewrite() { sed -E "s#^snap .*/([^/]*)\$#snap $D/replay_\1#" $1; }
run() {   # start-snapshot, repl
  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume $1 repl --disk-a "$DISK" < $2 > /dev/null 2>&1
}
segwise() {   # start snapshot, names...
  prev=$1; shift
  for n in "$@"; do
    { rewrite $D/$n.repl; echo q; } > $D/replay_$n.repl
    run $prev $D/replay_$n.repl
    cmp $D/$n.snap $D/replay_$n.snap && echo "$n: replay byte-identical"
    prev=$D/$n.snap
  done
}
chain() {     # start snapshot, final snapshot base name, names...
  start=$1; last=$2; shift; shift
  { for n in "$@"; do rewrite $D/$n.repl; done; echo q; } > $D/replay_chain_$last.repl
  run $start $D/replay_chain_$last.repl
  cmp $D/$last.snap $D/replay_$last.snap && echo "chain to $last: final snapshot byte-identical"
}
segwise $D/room299_poked.snap $MAIN
chain $D/room299_poked.snap seg5_pit_exit $MAIN
segwise $D/seg4_wall_hop.snap $SHOP
chain $D/seg4_wall_hop.snap seg11b_shop_exit $SHOP
cmp $D/shop_exit_bubble.snap $D/replay_shop_exit_bubble.snap && echo "shop_exit_bubble.snap: replay byte-identical"
