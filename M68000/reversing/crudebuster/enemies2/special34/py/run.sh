#!/bin/sh
# usage: run.sh <name> <lua> <env assignments...>   -- runs MAME in special34/run/<name>, output in special34/out/<name>
# example: run.sh l3 objlog.lua CB_LEVEL=3 CB_STOP=2500 CB_BOT=1
here=$(cd "$(dirname "$0")" && pwd); S=$(cd "$here/.." && pwd); M=$(cd "$S/../../../.." && pwd)
name=$1; lua=$2; shift 2
mkdir -p "$S/run/$name" "$S/out/$name"
env CB_DIR="$M/reversing/crudebuster/lua" CB_RUN="$S/run/$name" CB_OUT="$S/out/$name" "$@" \
  "$M/reversing/crudebuster/cbmame.sh" run "$S/lua/$lua" ${CB_SECS:-200}
