#!/bin/sh
# usage: run_job.sh <name> [VAR=value ...]  runs drive5.lua level 5 with its own run dir run/<name> and output out/<name>/objlog.txt (log: out/<name>.log)
here=$(cd "$(dirname "$0")" && pwd)
name=$1; shift
env CB_RUN="$here/run/$name" CB_LEVEL=5 "$@" "$here/run.sh" "$here/lua/drive5.lua" "$here/out/$name" 300 > "$here/out/$name.log" 2>&1
