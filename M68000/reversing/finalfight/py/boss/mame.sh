#!/bin/sh
# mame.sh <script.lua> [seconds] : headless MAME (0.289) on ffightuc with a run directory of its own ($DM_RUN, default <root>/scratchpad/finalfight/boss/run), no focus grab (SDL dummy).
# Needs DM_DEBUG=1 for bpset/wpset (DM_ADDRS, DM_WPS). The environment (DM_*) is passed through to dm.lua. -seconds_to_run is emulated time since MAME start, so a state loaded at frame 8299 needs a large value (default 600).
here=$(cd "$(dirname "$0")" && pwd)
root=${M68000_ROOT:-$(d=$here; while [ ! -d "$d/reversing/finalfight" ] && [ "$d" != / ]; do d=$(dirname "$d"); done; echo "$d")}
run="${DM_RUN:-$root/scratchpad/finalfight/boss/run}"
export FF_DIR="$root/reversing/finalfight/lua" SDL_VIDEODRIVER=dummy
mkdir -p "$run/cfg" "$run/nvram" "$run/sta" "$run/snap"
dbg=""; [ "$DM_DEBUG" = 1 ] && dbg="-debug -debugger none"
cd "$run" || exit 1
exec mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" \
  -state_directory "$run/sta" -snapshot_directory "$run/snap" -video none -sound none -nothrottle $dbg \
  -seconds_to_run "${2:-600}" -autoboot_script "$1"
