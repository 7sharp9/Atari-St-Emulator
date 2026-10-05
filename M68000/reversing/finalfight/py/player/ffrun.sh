#!/bin/sh
# Run a MAME Lua script on Final Fight (US, ffightuc) without the debugger (-nothrottle, input through the ioport).
#   ffrun.sh <script.lua> [emulated seconds, default 400]
# Environment: FFP_RUN   MAME cfg/nvram/state/snapshot directory (default <M68000>/scratchpad/finalfight/p3/f/run; the saved
#                         state to load, ff_enemies.sta, must be in $FFP_RUN/sta/ffightuc/; gates.sh copies it)
#              FFP_OUT   output directory for logs (default <M68000>/scratchpad/finalfight/p3/f/out)
#              FF_MAMEARGS extra MAME arguments (pbp.lua needs "-debug -debugger none"), FF_ROMS ROM path (default ~/mame-roms)
# Two runs must not share FFP_RUN at the same time (cfg, nvram, states collide). SDL dummy video keeps MAME from taking focus.
# -seconds_to_run counts emulated time and a loaded state restarts at its saved time (ff_enemies is at about 70 s), so keep it large.
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
run=${FFP_RUN:-$root/scratchpad/finalfight/p3/f/run}
export FF_DIR="$root/reversing/finalfight/lua"
export FF_OUT=${FFP_OUT:-$root/scratchpad/finalfight/p3/f/out}
mkdir -p "$run/cfg" "$run/nvram" "$run/sta" "$run/snap" "$FF_OUT/tmp"
export SDL_VIDEODRIVER=dummy
cd "$run" || exit 1
exec mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" \
  -nvram_directory "$run/nvram" -state_directory "$run/sta" -snapshot_directory "$run/snap" \
  -video none -sound none -nothrottle ${FF_MAMEARGS} -seconds_to_run "${2:-400}" -autoboot_script "$1"
