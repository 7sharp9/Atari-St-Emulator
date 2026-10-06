#!/bin/sh
# gdbmame.sh [port] [seconds] [extra mame args]: cold-boot ffightuc under MAME's gdbstub (needs -debug; halted at reset until the first `c`; ONE client per MAME process).
# Then, from another shell: gdb -q -nx -x py/gdbstub/session.gdb   (or python: rsp.py).  Work dir: scratchpad/finalfight/gdb/run.
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
run=${GD_RUN:-$root/scratchpad/finalfight/gdb/run}
port=${1:-23946}; secs=${2:-300}; [ $# -ge 2 ] && shift 2 || shift $#
mkdir -p "$run/cfg" "$run/nvram" "$run/sta" "$run/snap"
export SDL_VIDEODRIVER=dummy
cd "$run" || exit 1
exec mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" \
  -state_directory "$run/sta" -snapshot_directory "$run/snap" -debug -debugger gdbstub -debugger_host 127.0.0.1 \
  -debugger_port "$port" -video none -sound none -nothrottle -seconds_to_run "$secs" "$@"
