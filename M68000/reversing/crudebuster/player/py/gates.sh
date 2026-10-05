#!/bin/sh
# Player/combat gates (player.md). Re-creates every run from scratch (MAME 0.289, set cbuster) and runs the checking scripts.
# About 6 minutes with 4 MAME processes in parallel. Output under $P/out/g_*; run dirs $P/run_g<N> (own cfg/state per process).
#   py/gates.sh            (from anywhere; derives its own directory)
here=$(cd "$(dirname "$0")" && pwd)
P=$(cd "$here/.." && pwd)
M68000_ROOT=$(cd "$P/../../.." && pwd)
export M68000_ROOT P
CB_DIR=$M68000_ROOT/reversing/crudebuster/lua; export CB_DIR
PY=${PY:-$M68000_ROOT/.venv/bin/python}
CBM=$M68000_ROOT/reversing/crudebuster/cbmame.sh
run() { # run <n> <outname> <script> <seconds>   (environment of the caller carries the CB_* variables)
  mkdir -p "$P/out/g_$2" "$P/run_g$1"
  CB_RUN=$P/run_g$1 CB_OUT=$P/out/g_$2 "$CBM" run "$P/lua/$3" "$4" > "$P/out/g_$2/run.log" 2>&1
}
plan() { "$PY" "$here/mkplan.py" "$1" > "$P/lua/plans/$2.lua"; }
G=$P/out
# ---- batch 1: moves, chain, hit boxes, melee boxes
( CB_LEVEL=0 CB_PLAN=$P/lua/plans/moves1.lua CB_STOP=2400 CB_REGIONS="80100:80,80000:60" CB_POKES="80113:38:b,80136:7fff:w" run 1 moves1 reclog.lua 300 ) &
( CB_LEVEL=0 CB_PLAN=$P/lua/plans/chain.lua CB_STOP=2100 CB_REGIONS="80100:80" CB_POKES="80113:38:b,80136:7fff:w" run 2 chain reclog.lua 300 ) &
( SP=$("$PY" -c "d=[24,32,40,48,56,64,72,80]; print(','.join('%d:1:1:p%d:q'%(1000+140*i,d[i%8]) for i in range(40)))")
  CB_LEVEL=0 CB_PLAN=$P/lua/plans/spam.lua CB_SPAWNS="$SP" CB_STOP=6700 CB_REGIONS="80100:80,81000:400" CB_POKES="80113:38:b,80136:7fff:w" run 3 hitbox reclog.lua 400 ) &
( SP=$("$PY" -c "d=[40,56,72]; print(','.join('%d:1:1:p%d:q'%(1000+130*i,d[i%3]) for i in range(50)))")
  CB_LEVEL=0 CB_PLAN=$P/lua/plans/empty.lua CB_SPAWNS="$SP" CB_STOP=4000 CB_FA10=1 CB_REGIONS="80100:10" CB_POKES="" run 4 melee reclog.lua 400 ) &
wait
"$PY" "$here/gate_move.py" "$G/g_moves1/reclog.txt"
"$PY" - <<PYEOF
rows = {}
for ln in open("$G/g_chain/reclog.txt"):
    p = ln.split(); rows[int(p[0])] = bytes.fromhex(p[1])
res = []
for k in range(15):
    t = 1000 + 70 * k; fr = [f for f in range(t, t + 68) if rows[f][5] == 2]
    res.append((k + 1 if k else None, len(fr), max(rows[f][21] for f in fr)))
chained = [r[0] for r in res if r[2] >= 2]   # the animation reached frame index 2 or more: the second tap extended the chain
print("jab chain window: second tap set 2..11 frames after the first extends the chain (+29 2 -> 4, 24 frames):", chained, "PASS" if chained == list(range(2, 12)) else "FAIL")
PYEOF
"$PY" "$here/hitbox_gate.py" "$G/g_hitbox/reclog.txt"
"$PY" "$here/melee_gate.py" "$G/g_melee/calls.txt"
# ---- batch 2: damage tables, score, throw, carry
( CB_LEVEL=0 CB_TYPES="05:1,1a:1,15:1,03:1,10:1,11:1,24:1,01:1,00:0,02:2,04:0,04:1,07:0,0d:1,13:1,17:1,26:1,28:1" CB_TRIAL=300 run 1 dmg dmglab.lua 900 ) &
( CB_LEVEL=0 CB_TYPES="01:1,00:0,02:2,04:0,04:1,07:0,09:0,14:1" CB_TRIAL=300 run 2 hit hitlab.lua 900 ) &
( CB_LEVEL=0 CB_BTN=b3 CB_TAP=40 CB_DIST=30 CB_TYPES="01:1,00:0,02:2,04:0,07:0,14:1" CB_TRIAL=400 run 3 throw hitlab.lua 900 ) &
( CB_LEVEL=0 CB_STOP=1500 CB_NOSOLID=0 CB_SAVEAT="1480:l1_wall" run 4 bot_state bot.lua 600 ) &
wait
"$PY" "$here/dmg_check.py" "$G/g_dmg/dmg.txt" 0 | head -3
"$PY" "$here/gate_score.py" "$G/g_hit/hit.txt" jab | tail -1
"$PY" "$here/gate_score.py" "$G/g_throw/hit.txt" thrown | tail -1
"$PY" "$here/gate_throw.py" "$G/g_throw/hit.txt" | tail -1
# ---- batch 3: pickup from the saved state, continue/lives, 2 players
cp "$P/run_g4/sta/cbuster/l1_wall.sta" "$P/run_g1/sta/cbuster/" 2>/dev/null || { mkdir -p "$P/run_g1/sta/cbuster"; cp "$P/run_g4/sta/cbuster/l1_wall.sta" "$P/run_g1/sta/cbuster/"; }
( CB_LOAD=l1_wall CB_PLAN=$P/lua/plans/grab2.lua CB_FROM=1481 CB_STOP=1800 CB_REGIONS="80100:80,81400:80" CB_POKES="80113:38:b,80136:7fff:w" run 1 grab2 reclog.lua 300 ) &
( CB_LEVEL=0 CB_COINS=3 CB_PRESS=0 CB_STOP=5600 run 2 cont1 contlab.lua 900 ) &
( CB_LEVEL=0 CB_COINS=3 CB_PRESSAT=5 CB_PRESS=1 CB_STOP=5600 run 3 cont2 contlab.lua 900 ) &
( CB_LEVEL=0 CB_PLAN=$P/lua/plans/twop4.lua CB_STOP=2200 CB_REGIONS="80100:80,80180:80" CB_POKES="" run 4 twop4 reclog.lua 300 ) &
( CB_LEVEL=0 CB_PLAN=$P/lua/plans/canhit.lua CB_SPAWNSB="1000:0a:0:p24:q" CB_SPAWNS="1090:1:1:p100:q" CB_STOP=1300 CB_REGIONS="80100:10" CB_POKES="80113:38:b,80136:7fff:w" CB_TAPS="81005:2,81006:1" run 5 canhit reclog.lua 300 ) &
wait
"$PY" "$here/gate_pickup.py" "$G/g_grab2"
"$PY" "$here/gate_lives.py" "$G/g_cont1" "$G/g_cont2"
"$PY" "$here/gate_canhit.py" "$G/g_canhit/taps.txt"
"$PY" "$here/p1p2_compare.py" "$G/g_twop4/reclog.txt" | tail -1
( CB_LEVEL=0 CB_PLAN=$P/lua/plans/twop1.lua CB_STOP=1500 CB_REGIONS="80100:80,80180:80,80030:30" CB_POKES="" run 1 twop1 reclog.lua 300 ) &
( CB_LEVEL=0 CB_PLAN=$P/lua/plans/twop2.lua CB_STOP=1700 CB_REGIONS="80100:80,80180:80" CB_POKES="" run 2 twop2 reclog.lua 300 ) &
( CB_LEVEL=0 CB_PLAN=$P/lua/plans/twop3.lua CB_STOP=1500 CB_REGIONS="80100:80,80180:80" CB_POKES="" run 3 twop3 reclog.lua 300 ) &
wait
"$PY" "$here/gate_2p.py" "$G/g_twop1" "$G/g_twop2" "$G/g_twop3"
