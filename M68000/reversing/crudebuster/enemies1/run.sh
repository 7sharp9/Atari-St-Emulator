#!/bin/sh
# run.sh <name> <lua> [env...]  : MAME run with its own run dir under enemies1/run/<name>, output to enemies1/out/<name>
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../.." && pwd)
name=$1; lua=$2; shift 2
mkdir -p "$here/out/$name"
export CB_DIR=$root/reversing/crudebuster/lua CB_OUT=$here/out/$name CB_RUN=$here/run/$name
env "$@" "$root/reversing/crudebuster/cbmame.sh" run "$lua" ${SECS:-600} >"$here/out/$name/mame.log" 2>&1
