#!/bin/sh
# WORLD gates (about 6 minutes). Needs only MAME + the repo; writes under world/{out,run} (gitignored).
#   1 demo streams vs the attract run (3 demos x 2 players x 633 frames)      -> py/demo_check.py
#   2 fresh-game replay of each stream through the real ports                  -> py/replay_check.py
#   3 pool C damage = 4 x table at $fcba (harness vs ROM table)                -> py/damage_tables.py
here=$(cd "$(dirname "$0")/.." && pwd)
PY=$here/../../../.venv/bin/python
cd "$here"
mkdir -p out/demo out/f out/st
# 1: attract run, 16800 frames, per-frame input bytes
CB_OUT=$here/out/demo CB_STOP=16800 CB_RUN=$here/run/dm2 CB_ADDRS="80018:w,80014:b,80051:b,80053:b,80050:b,80052:b,8002a:w,8002c:w,8001a:l,80022:l,8004a:w,80046:b,80042:w,80044:w,80108:w,8010c:w,80188:w,8018c:w,80040:b,80100:b,80180:b,80113:b,80193:b" ./run.sh framelog.lua 700 >/dev/null 2>&1
"$PY" py/demo_check.py out/demo/framelog.csv
# 2: replays (start frame = frame where $8004a equals the demo's first-replay value $6d: 816, 815, 816)
for d in 0 1 2; do
  case $d in 0) lv=1; s=816; df=4417;; 1) lv=2; s=815; df=9942;; 2) lv=3; s=816; df=15468;; esac
  CB_LEVEL=$lv CB_DEMO=$d CB_START=$s CB_STOP=1500 CB_TAG=d$d CB_OUT=$here/out/demo CB_RUN=$here/run/sp$d ./run.sh streamplay.lua 100 >/dev/null 2>&1
  "$PY" py/replay_check.py out/demo/framelog.csv $df out/demo/streamplay_d$d.csv $s 633
done
# 3: pool C sweep from a level-1 state at frame 1300
CB_OUT=$here/out/st CB_STOP=1305 CB_LEVEL=0 CB_SAVE=pv0 CB_SAVE_FRAME=1300 CB_RUN=$here/run/s0 ./run.sh startlevel.lua 300 >/dev/null 2>&1
CB_STATE=pv0 CB_POOL=C CB_TYPES="255,0-43" CB_MODES=on CB_FRAMES=60 CB_SHOTS=4 CB_TAG=pv0_C CB_OUT=$here/out/f CB_RUN=$here/run/s0 ./run.sh forcespawn.lua 200 >/dev/null 2>&1
"$PY" py/damage_tables.py | tail -4
