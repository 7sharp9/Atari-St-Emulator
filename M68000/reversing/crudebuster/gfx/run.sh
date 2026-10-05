#!/bin/sh
# usage: run.sh <name> <plan.lua|-> <frames> <stop> [poke]   -> dumps/<name>/ (bins + ctl_log) and snapshots in run/snap/<name>/
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../../.." && pwd)
name=$1; plan=$2; frames=$3; stop=$4; poke=$5
export CB_RUN="$here/run/$name"
mkdir -p "$here/dumps/$name" "$CB_RUN/snap"
export CB_DIR="$repo/reversing/crudebuster/lua" CB_OUT="$here/dumps/$name" CB_FRAMES="$frames" CB_STOP="$stop" CB_POKE="$poke"
[ "$plan" != "-" ] && export CB_PLAN="$plan"
exec "$repo/reversing/crudebuster/cbmame.sh" run "$here/lua/${LUA:-dumpframes.lua}" 600
