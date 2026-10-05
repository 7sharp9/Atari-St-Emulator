#!/bin/sh
# make_states.sh <suffix> : (re)create the states used by the char and pvp runs from a cold boot; names get the suffix so a second creation can be compared with the first.
#   dch<c>_1900<suffix>   one player, character c selected on the real select screen, frame 1900 (Bred spawning, controllable)
#   d2p_ch<a><b>_1900<suffix>  two players, P1 character a, P2 character b (no bot, no enemies); d2pw_ch12_1930<suffix> the same with the bots walking, Bred alive
d=$(cd "$(dirname "$0")/.." && pwd); s=$1
for c in 0 1 2; do
  FF_CH1=$c FF_CH2=-1 FF_BOT_STOPF=1900 FF_SAVE=dch${c}_1900$s sh $d/run/run.sh mk_ch$c$s 200 > /dev/null 2>&1
done
FF_CH1=1 FF_CH2=2 FF_BOT_START=99999 FF_BOT_STOPF=1900 FF_SAVE=d2p_ch12_1900$s sh $d/run/run.sh mk_2p12$s 200 > /dev/null 2>&1
FF_CH1=0 FF_CH2=1 FF_BOT_START=99999 FF_BOT_STOPF=1900 FF_SAVE=d2p_ch01_1900$s sh $d/run/run.sh mk_2p01$s 200 > /dev/null 2>&1
FF_CH1=0 FF_CH2=2 FF_BOT_START=99999 FF_BOT_STOPF=1900 FF_SAVE=d2p_ch02_1900$s sh $d/run/run.sh mk_2p02$s 200 > /dev/null 2>&1
FF_CH1=1 FF_CH2=2 FF_BOT_STOPF=1930 FF_SAVE=d2pw_ch12_1930$s sh $d/run/run.sh mk_2pw$s 200 > /dev/null 2>&1   # bots walked, Bred alive (P2 kill-award run)
