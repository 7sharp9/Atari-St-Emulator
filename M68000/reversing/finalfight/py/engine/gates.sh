#!/bin/sh
# gates.sh [batch ...] : agent B (pass 5) gates, every run from a fresh run directory (runs/run_g_*), outputs in out/. Batches: states static cold state debug sound (default: all).
#   FFB_BASE=<dir> puts runs/, out/, run/sta/ somewhere else (default: scratchpad/finalfight/engine). Needs the pass-4 states (scratchpad/finalfight/stage/run/sta/ffightuc: sb_boss sb_s2 sb_s6;
#   scratchpad/finalfight/placement/run/sta/ffightuc: bb_2500; scratchpad/finalfight/twoplayer/run_p/sta/ffightuc: dch2_1900) and MAME 0.289 with ~/mame-roms.
#   Time: states 1 min, static seconds, cold 1 min, state 2 min, debug 2 min, sound (z80 sweep) 5 min. Then: M68000/.venv/bin/python gates.py [gate ...]
here=$(cd "$(dirname "$0")" && pwd); base=${FFB_BASE:-$(cd "$here/../../../.." && pwd)/scratchpad/finalfight/engine}; root=$(cd "$here/../../../.." && pwd)
export M68000_ROOT=$root FFB_BASE=$base
PY=$root/.venv/bin/python
L=$root/reversing/finalfight/lua
mkdir -p "$base/run/sta/ffightuc" "$base/out"
for d in stage/run bb placement/run twoplayer/run_p; do :; done
for s in sb_boss sb_s1 sb_s2 sb_s6; do [ -f "$base/run/sta/ffightuc/$s.sta" ] || cp "$root/scratchpad/finalfight/stage/run/sta/ffightuc/$s.sta" "$base/run/sta/ffightuc/"; done
[ -f "$base/run/sta/ffightuc/bb_2500.sta" ] || cp "$root/scratchpad/finalfight/placement/run/sta/ffightuc/bb_2500.sta" "$base/run/sta/ffightuc/"
batches=${*:-"states static cold state debug sound"}
has() { for b in $batches; do [ "$b" = "$1" ] && return 0; done; return 1; }
if has states; then   # the three poke-built states, built twice from sb_s6 / sb_s2 (RAM hashes compared by gates.py)
  for rep in 1 2; do
    (PD_N=1521 PD_POKES="410:ff80af:01,410:ff80c1:04" PD_SAVE=1520:p5b_bs7 sh $here/pd.sh g_bs7_$rep sb_s6 >/dev/null 2>&1) &
    (PD_N=741 PD_GOD=1 PD_POKES="600:ff8129:01" PD_SAVE=740:p5b_k7 sh $here/pd.sh g_k7s_$rep sb_s2 >/dev/null 2>&1) &
    (PD_N=1791 PD_GOD=1 PD_POKES="410:ff80af:01,410:ff80c1:06" PD_SAVE=1790:p5b_s5pre sh $here/pd.sh g_s5_$rep sb_s6 >/dev/null 2>&1) &
  done; wait
  for st in p5b_bs7 p5b_k7 p5b_s5pre; do n=$(echo $st | sed 's/p5b_//'); case $n in bs7) d=g_bs7_1;; k7) d=g_k7s_1;; s5pre) d=g_s5_1;; esac; cp "$base/runs/run_$d/sta/ffightuc/$st.sta" "$base/run/sta/ffightuc/" 2>/dev/null; done
fi
if has static; then
  $PY $here/regionsets.py > $base/out/g_region.txt
  $PY $here/ringtable.py > $base/out/ringtable.txt
  $PY $here/soundids.py > $base/out/soundids.txt
fi
if has cold; then
  (FFB_RUN=$base/runs/run_g_ring FF_W="ff8144-ff8183,ff8184-ff8203,800180-800181" FF_TAP_OUT=$base/out/g_ring_tap.txt FF_STOP=2300 FF_TAG=g_ring sh $here/ffb.sh $L/tap.lua 200 >/dev/null 2>&1) &
  (FFB_DEBUG=1 FFB_RUN=$base/runs/run_g_ringh FF_ADDRS="4b94 4be4 4c08 13ba 2738" FF_HIT_OUT=$base/out/g_ring_hits.txt FF_STOP=2300 FF_TAG=g_ringh sh $here/ffb.sh $L/hitcount.lua 300 >/dev/null 2>&1) &
  (FFB_DEBUG=1 FFB_RUN=$base/runs/run_g_intro FF_ADDRS="711a 7156 7aa8" FF_HIT_OUT=$base/out/g_intro_hits.txt FF_STOP=1900 FF_TAG=g_intro sh $here/ffb.sh $L/hitcount.lua 300 >/dev/null 2>&1) &
  wait
fi
if has state; then
  # shaker, three axes (SH_P20), snapshots compared with the camera log
  for ch in 0 2 4; do (SH_P20=$ch SH_SHOT=1 sh $here/sh1.sh g_shc$ch sb_boss "5:-1:-1" 45 >/dev/null 2>&1) & done
  # terrain: render with and without codes, behaviour of codes 3 and 5
  (sh $here/tr1.sh g_trS0 bb_2500 TR_N=3 TR_SHOTS=1,2,3 >/dev/null 2>&1) &
  (sh $here/tr1.sh g_trS3 bb_2500 TR_N=3 TR_SHOTS=1,2,3 TR_SETBITS=1f0:20:3 >/dev/null 2>&1) &
  (sh $here/tr1.sh g_trS5 bb_2500 TR_N=3 TR_SHOTS=1,2,3 TR_SETBITS=1f0:20:5 >/dev/null 2>&1) &
  wait
  (sh $here/tr1.sh g_trR0 bb_2500 TR_N=200 TR_KEY=right TR_FROM=5 TR_TO=200 TR_GOD=1 >/dev/null 2>&1) &
  (sh $here/tr1.sh g_trR3 bb_2500 TR_N=200 TR_KEY=right TR_FROM=5 TR_TO=200 TR_GOD=1 TR_SETBITS=1f0:20:3 >/dev/null 2>&1) &
  (sh $here/tr1.sh g_trR5 bb_2500 TR_N=200 TR_KEY=right TR_FROM=5 TR_TO=200 TR_GOD=1 TR_SETBITS=1f0:20:5 >/dev/null 2>&1) &
  # Haggar: pile driver and jump slam at five victim health values each (damage branches of $d9b6 / $d9e2)
  for hp in 0300 0065 0064 0019 0018; do (sh $here/hag.sh g_pd_$hp g2b 300 FF_EHP=$hp >/dev/null 2>&1) & done
  wait
  for hp in 0300 008d 008c 001f 001e; do (sh $here/hag.sh g_sl_$hp g2f_74 300 FF_EHP=$hp >/dev/null 2>&1) & done
  # the area-clear carrier (pool-4 kind 7) and the stage 5 area 0 elevator
  (PD_N=1100 PD_P4=1 PD_GOD=1 PD_POKES="600:ff8129:01" PD_SHOTS=760,800 sh $here/pd.sh g_k7 sb_s2 >/dev/null 2>&1) &
  (PD_N=1500 PD_ACT=1 PD_GOD=1 PD_POKES="20:ff8412:0560,20:ff856e:05e0,25:ff8412:0560,60:ff8123:01" sh $here/pd.sh g_elev p5b_s5pre >/dev/null 2>&1) &
  (PD_N=4600 PD_ACT=1 PD_GOD=1 PD_POKES="410:ff80af:01,410:ff80c1:03,1900:ff8129:01" sh $here/pd.sh g_elev0 sb_s6 >/dev/null 2>&1) &
  wait
fi
if has debug; then
  # glass panes of the first bonus stage (kind 12 hit from the left), the bonus-2 car pane (kind 9)
  KEYS="right:405-455"; for t in 460 475 490 505 520 535 550 565 580 595 610 625; do KEYS="$KEYS,b1:$t-$((t+4))"; done
  (PD_DEBUG=1 PD_N=700 PD_PROPS=1 PD_GOD=1 PD_ADDRS="7156 711a 7220 7222 722a 7232" sh $here/pd.sh g_glass sb_s6 PD_KEYS="$KEYS" >/dev/null 2>&1) &
  KEYS="right:5-70,down:5-30"; for t in 80 95 110 125 140 155; do KEYS="$KEYS,b1:$t-$((t+4))"; done
  (PD_DEBUG=1 PD_N=300 PD_PROPS=1 PD_GOD=1 PD_ADDRS="71a2 71ba 71e2 53182 531b4" sh $here/pd.sh g_car p5b_bs7 PD_KEYS="$KEYS" >/dev/null 2>&1) &
  # shaker callers of kind 3 / kind 4 (spawned into ff_enemies, clean arena): entrance types and the leap landing
  K=$root/reversing/finalfight/py/ai_kind123
  for b21 in 8 10 12; do (sh $here/k3run.sh g_k3e$b21 "4160:3:2:$b21:90:0:-1" 4900 $here/noplan.lua >/dev/null 2>&1) & done
  (sh $here/k3run.sh g_k4e8 "4160:4:0:8:90:0:-1" 4700 $here/noplan.lua >/dev/null 2>&1) &
  (sh $here/k3run.sh g_k3n1 "4160:3:1:0:90:0:-1" 16000 $here/noplan.lua >/dev/null 2>&1) &
  wait
  # EDI.E hand spawn with and without +78 (dmk.lua keeps it; the original dm.lua zeroed it and EDI.E took an address error)
  (BK_BOT=2 sh $here/bk.sh g_edi "2:0:2900:48:-1" 40 1500 >/dev/null 2>&1) &
  wait
fi
if has sound; then
  (SW_OUT=$base/out/z80sweep_full.txt SW_START=300 FFB_RUN=$base/runs/run_g_swf sh $here/ffb.sh $here/z80sweep.lua 900 >/dev/null 2>&1) &
  (LUA=sndbp.lua FF_MAMEARGS="-debug -debugger none" SB_OUT=$base/out/sndbp_boss2.txt sh $here/playtap.sh g_sndbp boss >/dev/null 2>&1) &
  # the ids the first sweep did not cover ($40-$4f, $60-$ff), three runs
  A=$(python3 -c "print(','.join('%02x'%i for i in list(range(0x40,0x50))+list(range(0x60,0x80))))")
  B=$(python3 -c "print(','.join('%02x'%i for i in range(0x80,0xc0)))")
  C=$(python3 -c "print(','.join('%02x'%i for i in list(range(0xc0,0xf0))+list(range(0xf8,0x100))))")
  for n in A B C; do eval ids=\$$n; (SW_IDS="$ids" SW_OUT=$base/out/z80sweep_$n.txt SW_START=300 FFB_RUN=$base/runs/run_g_sw$n sh $here/ffb.sh $here/z80sweep.lua 900 >/dev/null 2>&1) & done
  wait
fi
echo "runs done; now: $PY $here/gates.py"
