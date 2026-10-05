#!/bin/sh
# usage: run.sh <lua script name in lua/> <outdir name under out/> [env assignments via the environment]
# e.g.  CB_LEVEL=3 CB_STOP=3000 CB_BOT=1 ./run.sh objlog.lua l3
here=$(cd "$(dirname "$0")" && pwd)
export M68000_ROOT=$(cd "$here/../../../.." && pwd)
export CB_DIR=$M68000_ROOT/reversing/crudebuster/lua
export CB_RUN=$here/run
export CB_OUT=$here/out/$2
mkdir -p "$CB_OUT" "$CB_RUN/sta/cbuster"
exec $M68000_ROOT/reversing/crudebuster/cbmame.sh run $here/lua/$1 ${CB_SECS:-300}
