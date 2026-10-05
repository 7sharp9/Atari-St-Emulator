#!/bin/sh
# ffmame.sh callcap | script <file.lua> : debugger wrapper (callcap.lua is reversing/finalfight/lua/callcap.lua; set CALLCAP_SPEC)
d=$(cd "$(dirname "$0")/.." && pwd)
. "$d/run/env.sh"
run="$runroot"
mkdir -p "$run/cfg" "$run/nvram" "$run/sta" "$run/snap"
export FF_DIR="$d/lua"
export FF_OUT=${FF_OUT:-$out}
case "$1" in
  callcap) script="$d/../../lua/callcap.lua" ;;
  script)  script="$2" ;;
  *) echo "usage: $0 callcap | script <file.lua>" >&2; exit 2 ;;
esac
export SDL_VIDEODRIVER=dummy
cd "$run" || exit 1
exec mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" \
  -state_directory "$run/sta" -snapshot_directory "$run/snap" -debug -debugger none -video none -sound none -nothrottle \
  -seconds_to_run "${FFD_SECONDS:-300}" -autoboot_script "$script"
