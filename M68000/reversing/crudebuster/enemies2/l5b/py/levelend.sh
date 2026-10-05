#!/bin/sh
# levelend.sh <level> <P2:0|1> : start the level, poke $80040 bit 3 (boss-cleared flag, value $88) at frame 1500, log the writers of $80040/$80041 (CB_TAP)
here=$(cd "$(dirname "$0")/.." && pwd)
L=$1; P=$2
"$here/run.sh" le${L}_$P "$here/lua/objlog.lua" CB_LEVEL=$L CB_P2=$P CB_STOP=2600 CB_BOT=0 CB_HP=1 CB_POKES=1500:80040:88 CB_TAP=80040:80041,80016:80017 CB_X=80040:b,80100:b,80180:b
