#!/bin/sh
# usage: run.sh <lua file> <outdir> [seconds] ; other env passes through (CB_LEVEL, CB_STOP, ...)
here=$(cd "$(dirname "$0")" && pwd)
M=$(cd "$here/../../../.." && pwd)
export M68000_ROOT=$M
export CB_DIR=$M/reversing/crudebuster/lua CB_RUN=${CB_RUN:-$here/run} CB_OUT=$2
mkdir -p "$2"
exec "$M/reversing/crudebuster/cbmame.sh" run "$1" ${3:-80}
