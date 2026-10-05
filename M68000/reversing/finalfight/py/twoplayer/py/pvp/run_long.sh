#!/bin/sh
# run_long.sh : the long two-player runs (about 1 to 5 minutes each; MAME runs about 15x real time). Needs run/make_states.sh to have made d2p_ch12_1900 and dch1_1900, and copies of
# ff_enemies.sta (scratchpad/finalfight/ff_enemies.sta) in the run directories. Every run uses its own MAME run directory (cfg, nvram, states collide otherwise): run_t, run_1p.
here=$(cd "$(dirname "$0")" && pwd); d=$(cd "$here/../.." && pwd)
. "$d/run/env.sh"
for r in run_t run_1p run_2 run_3; do mkdir -p $base/$r/sta/ffightuc; cp $runroot/sta/ffightuc/d2p_ch12_1900.sta $runroot/sta/ffightuc/dch1_1900.sta $base/$r/sta/ffightuc/; cp $root/scratchpad/finalfight/ff_enemies.sta $base/$r/sta/ffightuc/; done
cp $root/scratchpad/finalfight/ff_enemies.sta $runroot/sta/ffightuc/
# 1. stage 0 from a cold boot to the camera x $aa0 trigger, one player and two players (bots: lua/bot2p.lua); spawn lists for p2_entries.py
env FF_CH1=1 FF_CH2=-1 FF_BOT_CAM=2720 FF_BOT_STOPF=20000 FF_SAVE=d1p_boss FFD_RUN=$base/run_1p sh $d/run/run.sh p1boss 900
env FF_CH1=1 FF_CH2=2 FF_BOT_CAM=2720 FF_BOT_STOPF=30000 FF_SAVE=d2p_boss FFD_RUN=$base/run_t sh $d/run/run.sh p2boss 1200
# 2. target rule, health at spawn: one player and two players from the 1900 states (extra_target.lua writes T, H, G, P lines into FFD_TLOG)
env FF_LOAD=dch1_1900 FF_BOT_START=0 FF_CH2=-1 FFD_EXTRA=$d/lua/extra_target.lua FFD_TLOG=$out/tgt_1p.t FF_BOT_STOPF=8500 FFD_RUN=$base/run_1p sh $d/run/run.sh tgt_1p 900
env FF_LOAD=d2p_ch12_1900 FF_BOT_START=0 FFD_EXTRA=$d/lua/extra_target.lua FFD_TLOG=$out/tgt_a.t FF_BOT_STOPF=8500 FFD_RUN=$base/run_t sh $d/run/run.sh tgt_a 900
env FF_LOAD=d2p_ch12_1900 FF_BOT_START=0 FF_BOT_STOPF=9000 FFD_EXTRA=$d/lua/extra_target.lua FFD_TLOG=$out/tgt_b.t FF_FUZZ_SEED=1 FFD_RUN=$base/run_t sh $d/run/run.sh tgt_b 900
# 3. token request $27b5a under the debugger: entry and exit breakpoints (py/pvp/bps_tokens.lua), from ff_enemies with 127(A5) poked to 1 and 3, and a fuzz of (tokens, rank, 127)
bp() { name=$1; run_dir=$2; shift 2; env FF_LOAD=ff_enemies FF_BOT_START=0 FF_BOT_P1=0 FF_BOT_NOATK=1 FF_BOT_STOPF=$BPSTOP FF_BOT_LOG=$out/$name.log FFD_BPS=$d/py/pvp/bps_tokens.lua FFD_BPOUT=$out/$name.txt \
   FFD_RUN=$base/$run_dir FF_MAMEARGS="-debug -debugger none" "$@" sh $d/run/ffrun.sh $d/lua/bot_bp.lua 900; }
BPSTOP=6500 bp bpe1 run_1p FF_P127=01 FFD_EXTRA=$d/lua/extra_poke127.lua
BPSTOP=6500 bp bpe3 run_t FF_P127=03 FFD_EXTRA=$d/lua/extra_poke127.lua
BPSTOP=10500 bp bpf1 run_1p FF_FUZZ_SEED=1 FFD_EXTRA=$d/lua/extra_fuzz_tok.lua
BPSTOP=10500 bp bpf2 run_t FF_FUZZ_SEED=2 FFD_EXTRA=$d/lua/extra_fuzz_tok.lua
