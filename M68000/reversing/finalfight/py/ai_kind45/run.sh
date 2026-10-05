#!/bin/sh
# Run MAME (ffightuc) headless for the ai_kind45 scripts. The MAME run directory (cfg, nvram, states, snapshots) comes from $AI45_RUN
# (default scratchpad/finalfight/p3/c/run); two runs at once need two directories. States are read from $AI45_RUN/sta/ffightuc/:
# ff_enemies.sta is copied there from scratchpad/finalfight/ if missing.
#   run.sh drive <script.lua> [seconds]     no debugger, -nothrottle (drv.lua)
#   run.sh callcap                          CALLCAP_SPEC=<spec.lua>, debugger (lua/callcap.lua)
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
run=${AI45_RUN:-$root/scratchpad/finalfight/p3/c/run}
mkdir -p "$run/cfg" "$run/nvram" "$run/sta/ffightuc" "$run/snap"
[ -f "$run/sta/ffightuc/ff_enemies.sta" ] || cp "$root/scratchpad/finalfight/ff_enemies.sta" "$run/sta/ffightuc/"
export FF_DIR="$root/reversing/finalfight/lua"
export SDL_VIDEODRIVER=dummy      # without it macOS makes mame the frontmost app even with -video none
cd "$run" || exit 1
case "$1" in
  drive)
    exec mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" \
      -state_directory "$run/sta" -snapshot_directory "$run/snap" -video none -sound none -nothrottle \
      -seconds_to_run "${3:-300}" -autoboot_script "$2" ;;
  callcap)
    exec mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" \
      -state_directory "$run/sta" -debug -debugger none -video none -sound none -seconds_to_run 120 \
      -autoboot_script "$root/reversing/finalfight/lua/callcap.lua" ;;
  *) echo "usage: run.sh drive <script.lua> [seconds] | callcap" >&2; exit 2 ;;
esac
