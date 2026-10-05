#!/bin/sh
# ffrun.sh <script.lua> [seconds]: run a MAME Lua script on Final Fight (ffightuc) without the debugger, as reversing/finalfight/ffrun.sh,
# but with its own MAME run directory so parallel agents do not share cfg/nvram/states.
#   FF_E_RUN  MAME run dir (default scratchpad/finalfight/p3/e/run); saved states are looked up in <run>/sta/ffightuc/
#   FF_E_OUT  output dir for logs (default scratchpad/finalfight/p3/e/out), exported to the Lua as FF_OUT unless FF_OUT is set
# Missing saved states are copied in from scratchpad/finalfight/ (ff_enemies.sta, ff_gameplay.sta) and scratchpad/finalfight/p3/e/ (ff_k8.sta).
# Extra MAME arguments: $FF_MAMEARGS (e.g. "-debug -debugger none" for the execution counters). ROMs: $FF_ROMS (default ~/mame-roms).
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
run=${FF_E_RUN:-$root/scratchpad/finalfight/p3/e/run}
export FF_DIR="$root/reversing/finalfight/lua"
export FF_OUT=${FF_OUT:-${FF_E_OUT:-$root/scratchpad/finalfight/p3/e/out}}
mkdir -p "$run/cfg" "$run/nvram" "$run/sta/ffightuc" "$run/snap" "$FF_OUT/tmp"
for s in "$root/scratchpad/finalfight/ff_enemies.sta" "$root/scratchpad/finalfight/ff_gameplay.sta" "$root/scratchpad/finalfight/p3/e/ff_k8.sta"; do
  [ -f "$s" ] && [ ! -f "$run/sta/ffightuc/$(basename "$s")" ] && cp "$s" "$run/sta/ffightuc/"
done
# headless: without the dummy SDL driver macOS makes mame the frontmost app
export SDL_VIDEODRIVER=dummy
cd "$run" || exit 1
exec mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" \
  -nvram_directory "$run/nvram" -state_directory "$run/sta" -snapshot_directory "$run/snap" \
  -video none -sound none -nothrottle ${FF_MAMEARGS} -seconds_to_run "${2:-120}" -autoboot_script "$1"
