#!/bin/sh
# runload.sh <runname> <state> <stopframe> [extra env...] : load a state (copied from run/c/sta) and run the approach-bot setup
here=$(cd "$(dirname "$0")/.." && pwd)
n=$1; st=$2; stop=$3; shift 3
mkdir -p "$here/run/$n/sta/cbuster"
for d in c d e f g h; do [ -f "$here/run/$d/sta/cbuster/$st.sta" ] && cp "$here/run/$d/sta/cbuster/$st.sta" "$here/run/$n/sta/cbuster/"; done
"$here/run.sh" $n "$here/lua/objlog.lua" CB_LEVEL=5 CB_BOT=3 CB_HP=1 CB_KILL=35,39,3f,40,44,4a,4b CB_BTYPES=46,47 CB_EHP=1 CB_EHPT=4c,4d CB_LANEY=384 CB_STOP=$stop CB_LOAD=$st CB_X=8040a:w,80406:w,81e03:b,80041:b "$@"
