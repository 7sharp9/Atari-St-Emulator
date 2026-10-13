#!/bin/bash
# gate_pigeon.sh: how an injected order reaches a pigeon-carried group (commander README "Orders by carrier pigeon").
# From rand1, side 3 group 1 (20M): s1 go to A (32,60) at 0; s3 go to B (26,60) at 2M; s2 both; s4 A twice.
# From prep2 (rand1_s2 + 20M, commander/prep.py), side 4 group 2, whose sender record is dead (owner -4), go to (36,62)
# at 0, 40M: ctl as is; alive with the sender's owner byte $53dcb := 4; snd0 with the sender word $51aa8 := 0.
# Then check_pigeon.py reads the logs. Work dir $CMD_WORK/pigeon (default scratchpad/cmd1).
d=$(cd "$(dirname "$0")" && pwd); R=$d; while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done; cd "$R"
L=${d#$R/}; W=${CMD_WORK:-scratchpad/cmd1}/pigeon; mkdir -p $W; S=scratchpad/pm142/rand1.snap
[ -f $W/prep2.snap ] || python3 $L/../prep.py scratchpad/pm143/run/rand1_s2.snap $W/prep2.snap 20e6 3:0 2:0 4:2 > $W/prep2.txt
O="--side 3 --k 1 --take 3"
python3 $L/run.py $S $W/s1 20e6 $O --order 0:02:32:60 > /dev/null 2>&1 &
python3 $L/run.py $S $W/s2 20e6 $O --order 0:02:32:60 --order 2e6:02:26:60 > /dev/null 2>&1 &
python3 $L/run.py $S $W/s3 20e6 $O --order 2e6:02:26:60 > /dev/null 2>&1 &
python3 $L/run.py $S $W/s4 20e6 $O --order 0:02:32:60 --order 2e6:02:32:60 > /dev/null 2>&1 &
P="--side 4 --k 2 --order 0:02:36:62"
python3 $L/run.py $W/prep2.snap $W/ctl 40e6 $P > /dev/null 2>&1 &
python3 $L/run.py $W/prep2.snap $W/alive 40e6 $P --setb 0:53dcb:04 > /dev/null 2>&1 &
python3 $L/run.py $W/prep2.snap $W/snd0 40e6 $P --setb 0:51aa8:00 --setb 0:51aa9:00 > /dev/null 2>&1 &
wait
python3 $L/check_pigeon.py $W
