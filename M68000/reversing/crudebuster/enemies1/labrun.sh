#!/bin/sh
# labrun.sh <name> <plan.lua> [state]  : lab.lua run with its own run dir; copies state files from run/lab/sta/cbuster into it.
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../.." && pwd)
name=$1; plan=$2
mkdir -p "$here/out/$name" "$here/run/$name/sta/cbuster"
cp "$here"/run/lab/sta/cbuster/*.sta "$here/run/$name/sta/cbuster/" 2>/dev/null
export CB_DIR=$root/reversing/crudebuster/lua CB_OUT=$here/out/$name CB_RUN=$here/run/$name CB_PLAN=$plan
"$root/reversing/crudebuster/cbmame.sh" run "$here/lua/lab.lua" ${SECS:-3000} >"$here/out/$name/mame.log" 2>&1
