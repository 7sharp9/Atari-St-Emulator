#!/bin/sh
# Run a MAME Lua script on Final Fight (US, ffightuc) without the debugger: no -debug, full speed
# (-nothrottle), input driven through the ioport. Use ffmame.sh for the debugger-based callcap.
#   ffrun.sh <script.lua> [seconds]
# The scripts in lua/ (lib.lua, ffdrive.lua, resume_check.lua, ioport_dump.lua) take FF_DIR (set here to
# lua/) and FF_OUT (output dir, default scratchpad/finalfight/run). States go to run/sta/ffightuc/.
# Extra MAME arguments: $FF_MAMEARGS. ROMs: $FF_ROMS (default ~/mame-roms).
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
run="$root/scratchpad/finalfight/run"
export FF_DIR="$here/lua"
export FF_OUT=${FF_OUT:-$run}
mkdir -p "$run/cfg" "$run/nvram" "$run/sta" "$run/snap" "$FF_OUT/tmp"
cd "$run" || exit 1
exec mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" \
  -nvram_directory "$run/nvram" -state_directory "$run/sta" -snapshot_directory "$run/snap" \
  -video none -sound none -nothrottle ${FF_MAMEARGS} -seconds_to_run "${2:-120}" -autoboot_script "$1"
