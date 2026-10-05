#!/bin/sh
# Run MAME headless on Crude Buster (MAME set `cbuster`, World FX) with a Lua script.
#   cbmame.sh script <file.lua> [seconds]   with -debug -debugger none (breakpoints, callcap)
#   cbmame.sh run    <file.lua> [seconds]   no debugger, -nothrottle (input-driven drives; load states here)
# ROMs: $CB_ROMS (default ~/mame-roms: cbuster.zip, a merged set holding the four clones too).
# Set $CB_SET to run a clone (cbusterj, cbusterw, twocrude, twocrudea). $CB_RUN is the run directory
# (cfg/nvram/sta/snap), default scratchpad/crudebuster/run; parallel runs need their own.
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
run=${CB_RUN:-$root/scratchpad/crudebuster/run}
mkdir -p "$run"
roms=${CB_ROMS:-$HOME/mame-roms}
set=${CB_SET:-cbuster}
mode=$1; script=$2; secs=${3:-120}
case "$mode" in
  script) dbg="-debug -debugger none" ;;
  run)    dbg="-nothrottle" ;;
  *) echo "usage: $0 script|run <file.lua> [seconds]" >&2; exit 2 ;;
esac
# headless: without the dummy SDL driver macOS makes mame the frontmost app even with -video none
export SDL_VIDEODRIVER=dummy
cd "$run" || exit 1
exec mame $set -rompath "$roms" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" \
  -state_directory "$run/sta" -snapshot_directory "$run/snap" $dbg -video none -sound none \
  -seconds_to_run "$secs" -autoboot_script "$script"
