#!/bin/sh
# gate.sh [dump hits csv]: the stub gate. Cold boot A under MAME's gdbstub (gate_ram.py: Z0 $53e, continue N times, registers and work RAM at the listed hits),
# cold boot B under the Lua oracle (-debug -debugger none, bpset $53e, the callcap mechanism); registers at every hit and work RAM at the listed hits must be equal (cmp.py).
# Checked: 600 of 600 stops PC == $53e, A5/SP/SR equal 600 of 600, work RAM 65,536 of 65,536 bytes at hits 1, 2, 10, 100, 300, 600. Output: scratchpad/finalfight/gdb/out
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
dumps=${1:-1,2,10,100,300,600}
port=${GD_PORT:-23946}
export GD_OUT=${GD_OUT:-$root/scratchpad/finalfight/gdb/out} GD_DUMPS=$dumps
run=${GD_RUN:-$root/scratchpad/finalfight/gdb/run}
mkdir -p "$GD_OUT" "$run"
ps aux | grep '[m]ame ffightuc' | grep -q gdbstub && { echo "a gdbstub MAME is already running; kill it first (ps aux | grep '[m]ame ffightuc')" >&2; exit 2; }
sh "$here/gdbmame.sh" "$port" 300 > "$GD_OUT/mame_stub.txt" 2>&1 &
mp=$!
i=0; while ! netstat -an -p tcp | grep -q "127.0.0.1.$port .*LISTEN"; do sleep 0.2; i=$((i+1)); [ $i -gt 150 ] && { echo "stub never listened" >&2; kill -9 $mp; exit 2; }; done
(cd "$here" && python3 gate_ram.py "$port" "$dumps") || echo "gate_ram.py failed" >&2
kill -9 $mp 2>/dev/null; wait $mp 2>/dev/null
cd "$run" || exit 1
SDL_VIDEODRIVER=dummy mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" \
  -state_directory "$run/sta" -snapshot_directory "$run/snap" -debug -debugger none -video none -sound none -nothrottle \
  -seconds_to_run 120 -autoboot_script "$here/oracle.lua" > "$GD_OUT/mame_oracle.txt" 2>&1
python3 "$here/cmp.py"; rc=$?
ps aux | grep '[m]ame ffightuc' | grep -E "gdbstub|oracle.lua" | awk '{print $2}' | xargs kill -9 2>/dev/null
exit $rc
