#!/bin/sh
# Run MAME under the debugger harness (callcap.lua of reversing/finalfight/lua, or any script); same FFP_RUN / FFP_OUT as ffrun.sh.
#   ffmame.sh callcap            CALLCAP_SPEC=<spec.lua>
#   ffmame.sh script <file.lua>
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
run=${FFP_RUN:-$root/scratchpad/finalfight/p3/f/run}
mkdir -p "$run/cfg" "$run/nvram" "$run/sta" "$run/snap"
case "$1" in
  callcap) script="$root/reversing/finalfight/lua/callcap.lua" ;;
  script)  script="$2" ;;
  *) echo "usage: $0 callcap | script <file.lua>" >&2; exit 2 ;;
esac
export FF_DIR="$root/reversing/finalfight/lua"
export FF_OUT=${FFP_OUT:-$root/scratchpad/finalfight/p3/f/out}
export SDL_VIDEODRIVER=dummy
cd "$run" || exit 1
exec mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" \
  -state_directory "$run/sta" -debug -debugger none -video none -sound none \
  -seconds_to_run 400 -autoboot_script "$script"
