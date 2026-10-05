#!/bin/sh
# probe.sh <name> <level> <type hex> <variant hex> [frames] [extra env...]
# Injects one pool A record of <type>/<variant> at screen centre of an otherwise empty level (script list pointed at its terminator),
# P1 idle beside it (CB_BOT=1 CB_IDLE=1: attacks when in reach), shots every 40 frames, log in out/<name>/objlog.txt.
here=$(cd "$(dirname "$0")" && pwd)
name=$1; lvl=$2; ty=$3; var=$4; fr=${5:-600}; shift 5 2>/dev/null
case $lvl in
  3) ptr=c54e ;; 4) ptr=c730 ;; 2) ptr=c44e ;; *) ptr=c82c ;;
esac
stop=$((800+fr))
rm -rf "$here/../run/$name" "$here/../out/$name"
"$here/run.sh" $name objlog.lua CB_LEVEL=$lvl CB_STOP=$stop CB_BOT=1 CB_IDLE=1 CB_HP=${HP:-1} CB_POOLB=1 CB_CLEARA=799 \
  CB_WPOKES=799:81e06:0006,799:81e08:$ptr,800:8040a:0300,800:80108:0340,801:80108:0340,800:80406:0100 \
  CB_SPAWN=802:$ty:$var:3a0:1c0 CB_SHOTS=802:$stop:${SHOT:-40} CB_X="80400:b,80401:b,80402:b,8005c:b" "$@" >"$here/../out/$name.log" 2>&1
