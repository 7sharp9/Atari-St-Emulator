#!/bin/sh
# full.sh [name] [extra env...] : one run from the level-5 start to the end of the attract restart: approach bot (see lua/objlog.lua), all L5B logs
here=$(cd "$(dirname "$0")/.." && pwd)
n=${1:-full}; shift
"$here/run.sh" $n "$here/lua/objlog.lua" CB_LEVEL=5 CB_BOT=3 CB_HP=1 CB_KILL=35,39,3f,40,44,4a,4b CB_BTYPES=46,47 CB_EHP=1 CB_EHPT=4c,4d,4e CB_LANEY=384 CB_PREF=48 \
  CB_STOP=${STOP:-30000} CB_POOLB=1 CB_HPTAP=1 CB_X=8040a:w,80406:w,81e03:b,80041:b,80016:w,80040:b,8013c:l,80054:b CB_TAP=80040:80041,80016:80017 "$@"
