#!/bin/bash
# gate_leadkill.sh [pick] [r39] [goto] [win]: how an enemy man reaches the captain's lead on land 2 (README "How the captain
# dies"). Scripted seed o1 (runs/l2_scripted_o1, start rebuilt as seeds.sh does) replayed to 205M; the loop's two orders
# at 205M and 205.4M (posture 4, attack (26,52)) are poked as the log applied them. Work dir ${CMD_WORK:-scratchpad/cmd10}/leadkill.
#   pick  every $5350 target pick over 205.4M..208.5M (64 stops), state dumped, $503c/$548a replayed by model_pick.py:
#         recorded 64 of 64, the captain's lead picked 6 times.
#   r39   from just before man $521a6 picks the lead (the 23rd pick), control against his retry byte 39 poked 2 -> 0
#         (the other three bytes of the longword rewritten as read): recorded control lead stamped $32 at 1345254840 by
#         $521a6; poked, $521a6 picks $5301a and $5223c (retry 2, the next pick of that tick) takes the lead.
#   goto  from the same state + 250k steps (lead in $34), control against a go to (23,49) and a go to (26,47) for the
#         captain: recorded lead stamped at 1345254840, 1345780398, 1345780426; health after 2.6M steps 83, 5, 5.
#   win   the land-2 rollout win (runs/l2_rollout) replayed to 315M, then 15M steps under a watch: chase_fate.py over the
#         chasers aimed at the captain's lead: recorded engaged 1 ($52eee, health 3 at 315M), diverted 2; lead 95 -> 94.
d=$(cd "$(dirname "$0")" && pwd); R=$d; while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "$R"; L=${d#$R/}; C=$(dirname $L); W=${CMD_WORK:-scratchpad/cmd10}/leadkill; mkdir -p $W
EMU() { ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$@"; }
POKE205='w 58044 018802c4\nw 5801c 01160004\nw 58020 02000200\n'
POKE2054='w 58044 018802c4\nw 5801c 010c1a34\nw 58020 02000200\n'
S=$W/replay/at_205000000.snap
if [ ! -f $S ]; then
  [ -f scratchpad/cmd9/start/o1/final.snap ] || python3 $C/loop.py scratchpad/cmd9/start/o1 \
    --snap scratchpad/cmd3/l2build/l2_built.snap --side 1 --budget 1e6 --policy none --no-take > /dev/null
  python3 $C/loop.py $W/replay --replay "$R/$C/runs/l2_scripted_o1/decisions.jsonl" --snap-at 205000000 > /dev/null
fi
P=$W/pre_pick.snap
if [ ! -f $P ]; then
  printf "disk scratchpad/powermonger.st\n${POKE205}s 400000\n${POKE2054}bpc 5350 23 3100000\nsnap $P\nq\n" | EMU $S repl > /dev/null
fi
ARGS=${*:-pick r39 goto}      # win is not in the default: its replay to 1120M takes minutes
for a in $ARGS; do case $a in
pick)
  { printf "disk scratchpad/powermonger.st\n${POKE205}s 400000\n${POKE2054}"
    for i in $(seq 1 64); do printf 'bp 5350 3100000\nm 51b66 25600\nm 51500 1000\nm 57fed 1\ns 1\n'; done; printf 'q\n'; } |
    EMU $S repl > $W/pick.out 2>&1
  echo "== pick"; python3 $L/model_pick.py $W/pick.out | tail -1 ;;
r39)
  for x in ctl:'' r0:'w 521cc 04000000\n'; do n=${x%%:*}; p=${x#*:}
    printf "disk scratchpad/powermonger.st\n${p}watch 51b66 25600\ns 1000000\nq\n" |
      (EMU $P repl 2> >(python3 $R/reversing/powermonger/py/fsm/wfilter.py 46-49 > $W/r39_$n.watch) > /dev/null; wait) &
  done; wait; sleep 1
  for n in ctl r0; do echo "== r39 $n: first picks of the lead, first \$32 stamp on it"
    grep -E 'pc=\$005350 .*<- \$1482$' $W/r39_$n.watch | head -2; grep -m1 -E 'pc=\$005702 .*\$00053007' $W/r39_$n.watch; done ;;
goto)
  for x in ctl:none g1:01021731 g2:01021a2f; do n=${x%%:*}; o=${x##*:}
    { printf 'disk scratchpad/powermonger.st\ns 250000\n'
      [ $o != none ] && printf 'w 58044 018802c4\nw 5801c %s\nw 58020 02000200\n' $o
      printf 'watch 53006 2\ns 2357722\nm 52fe8 50\nq\n'; } | EMU $P repl > $W/goto_$n.out 2> $W/goto_$n.watch &
  done; wait
  for n in ctl g1 g2; do
    s=$(grep -m1 -E 'pc=\$005702' $W/goto_$n.watch | sed -E 's/.*step=([0-9]+).*/\1/')
    h=$(grep -E '^e1 10' $W/goto_$n.out | awk '{print $46}')
    echo "== goto $n: lead stamped \$32 at $s, health \$$h after 2.6M steps"; done ;;
win)
  WS=$W/win/at_315000000.snap
  [ -f $WS ] || python3 $C/loop.py $W/win --replay "$R/$C/runs/l2_rollout/decisions.jsonl" --snap-at 315000000 > /dev/null
  printf "disk scratchpad/powermonger.st\nm 52fe8 50\nm 52eee 50\nwatch 51b66 25600\ns 15000000\nm 52fe8 50\nq\n" |
    (EMU $WS repl 2> >(python3 $R/reversing/powermonger/py/fsm/wfilter.py 46-49 > $W/win.watch) > $W/win.out; wait)
  echo "== win"; python3 $L/chase_fate.py $W/win.watch | tail -4
  python3 -c "import re,sys; L=[l.split() for l in open(sys.argv[1]) if re.match(r'^[0-9a-f]{2}( [0-9a-f]{2}){49}', l)]
print('health: lead at 315M', int(L[0][45],16), '| \$52eee at 315M', int(L[1][45],16), '| lead at 330M', int(L[2][45],16))" $W/win.out ;;
esac; done
