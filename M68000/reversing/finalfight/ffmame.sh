#!/bin/sh
# Run MAME headless on Final Fight (US, ffightuc) with the Lua debugger harness.
#   ffmame.sh callcap            CALLCAP_SPEC=<spec.lua>  (see lua/callcap.lua)
#   ffmame.sh script <file.lua>  run any -autoboot_script under the debugger
# ROMs: $FF_ROMS (default ~/mame-roms: ffight.zip + ffightuc.zip). MAME's own cfg/nvram/state
# directories go under scratchpad/finalfight/run so nothing is written into the tree.
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
run="$root/scratchpad/finalfight/run"
mkdir -p "$run"
roms=${FF_ROMS:-$HOME/mame-roms}
case "$1" in
  callcap) script="$here/lua/callcap.lua" ;;
  script)  script="$2" ;;
  *) echo "usage: $0 callcap | script <file.lua>" >&2; exit 2 ;;
esac
cd "$run" || exit 1
exec mame ffightuc -rompath "$roms" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" \
  -state_directory "$run/sta" -debug -debugger none -video none -sound none \
  -seconds_to_run 120 -autoboot_script "$script"
