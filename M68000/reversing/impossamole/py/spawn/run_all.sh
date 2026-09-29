#!/bin/zsh
# Runs every spawn-type proof and saves the output under scratchpad/impossamole/agents/spawn/out/. About 10 minutes.
# Needs bin/Debug/net8.0/M68000.dll and `cd M68000 && uv sync`. Pokes are labelled in each script's docstring.
cd "${0:A:h}/../../../.." || exit 1
D=reversing/impossamole/py/spawn
O=scratchpad/impossamole/agents/spawn/out
mkdir -p $O
for s in spawn_behaviour flier_paths; do uv run python $D/$s.py > $O/$s.txt 2>&1; done
uv run python $D/anim_map.py scratchpad/impossamole/pass103/room188.snap 21f00 22300 > $O/anim_map.txt
uv run python $D/live_census.py > $O/census.txt 2>&1
for s in immune_shot marker_shot verify_fliers trigger_scan chase_check wander_check croc_ride monkey_trigger monkey_drop rock_hit slab_crush walker_swap bush_swap; do
  ATARI_NOTRACE=1 uv run python $D/$s.py > $O/$s.txt 2>&1
done
# wander_check on more snapshots (2-7 direction picks each)
for n in live_c1 box_edge room118 rock_top; do
  ATARI_NOTRACE=1 uv run python $D/wander_check.py scratchpad/impossamole/pass103/$n.snap >> $O/wander_check.txt 2>&1
done
ATARI_NOTRACE=1 uv run python $D/chase_check.py scratchpad/impossamole/pass103/live_c3.snap >> $O/chase_check.txt 2>&1
