#!/bin/sh
# usage: run_all_tracks.sh <frames> <seed> <mode random|chase> [usegate 1|0]; run from M68000/; 3 emulator processes at a time.
# Needs agents/tracks/snaps/race_0..7.snap (tracks/drive_track.py); logs go to scratchpad/supersprint/agents/collide/tmp/ (read by summarize.py).
# Env: RACE=<R> pokes the race counter at $beb2 (hazards), SIGNS=1 ports the sign group $b24e.
F=${1:-700}; S=${2:-3}; MODE=${3:-random}; G=${4:-1}
P=reversing/supersprint/py/collide
W=scratchpad/supersprint/agents
mkdir -p $W/collide/tmp
seq 0 7 | xargs -P3 -I{} sh -c "uv run python $P/traj_track.py $W/tracks/snaps/race_{}.snap $F $S {} $G $MODE > $W/collide/tmp/run_${MODE}_${S}_g${G}_{}.log 2>&1"
