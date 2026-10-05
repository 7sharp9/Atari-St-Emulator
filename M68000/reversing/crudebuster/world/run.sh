#!/bin/sh
# run.sh <script.lua|name> [secs] : MAME run with this agent's run dir (CB_RUN default ./run); env passes through.
# <name> without a slash is looked up in the shared lua/ dir, then in ./lua. MODE=script runs with the debugger.
here=$(cd "$(dirname "$0")" && pwd)
cb=$here/..
export CB_DIR=$(cd "$cb/lua" && pwd) CB_RUN=${CB_RUN:-$here/run}
s=$1
case "$s" in
  /*) ;;
  *) if [ -f "$CB_DIR/$s" ]; then s=$CB_DIR/$s; else s=$here/lua/$s; fi ;;
esac
exec "$cb/cbmame.sh" ${MODE:-run} "$s" ${2:-300}
