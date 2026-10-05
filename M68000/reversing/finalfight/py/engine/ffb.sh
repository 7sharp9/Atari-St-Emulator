#!/bin/sh
# ffb.sh <script.lua> [seconds] : headless MAME 0.289 on ffightuc, own run dir ($FFB_RUN, default <here>/run), SDL dummy (no focus grab).
# FFB_DEBUG=1 adds -debug -debugger none (needed for bpset/wpset). FF_DIR points at reversing/finalfight/lua (lib.lua, ffdrive.lua, tap.lua...).
# States: $FFB_RUN/sta/ffightuc/<name>.sta (copy from scratchpad/finalfight/stage/run/sta/ffightuc/).
here=$(cd "$(dirname "$0")" && pwd)
base=${FFB_BASE:-$(cd "$here/../../../.." && pwd)/scratchpad/finalfight/engine}   # work area (runs/, out/, run/sta/); default scratchpad/finalfight/engine; FFB_BASE overrides
root=${M68000_ROOT:-$(d=$here; while [ ! -d "$d/reversing/finalfight" ] && [ "$d" != / ]; do d=$(dirname "$d"); done; echo "$d")}
run="${FFB_RUN:-$base/run}"
export FF_DIR="$root/reversing/finalfight/lua" FFB_DIR="$here" M68000_ROOT="$root" SDL_VIDEODRIVER=dummy
export FF_OUT=${FF_OUT:-$base/out}
mkdir -p "$run/cfg" "$run/nvram" "$run/sta/ffightuc" "$run/snap" "$FF_OUT/tmp"
dbg=""; [ "$FFB_DEBUG" = 1 ] && dbg="-debug -debugger none"
cd "$run" || exit 1
exec mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" \
  -state_directory "$run/sta" -snapshot_directory "$run/snap" -video none -sound none -nothrottle $dbg \
  -seconds_to_run "${2:-120}" -autoboot_script "$1"
