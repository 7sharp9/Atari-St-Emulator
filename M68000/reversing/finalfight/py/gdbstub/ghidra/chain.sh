#!/bin/bash
# chain.sh: Ghidra's Debugger (TraceRmi) attached to MAME's gdbstub, headless, end to end, then the work RAM that landed in the Ghidra trace is compared with the Lua oracle
# (gate.sh must have run once: it writes lua_ram_100.bin). First run does the one-time setup: installs Ghidra's OWN bundled wheels (offline, --no-index) into
# scratchpad/finalfight/gdb/pyext (gdb's PYTHONPATH; the system Python and gdb are not touched) and imports ff_main.bin (lua/dumprom.lua) as 68000:BE:32:default into a Ghidra project there.
# Needs: gdb with Python (e.g. Homebrew gdb; $GDB), Ghidra 12.1.x ($GHIDRA, default ~/Downloads/ghidra_12.1.4_PUBLIC). Does NOT test the Ghidra GUI (README.md has the click procedure).
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../../.." && pwd)
GHIDRA=${GHIDRA:-$HOME/Downloads/ghidra_12.1.4_PUBLIC}; GDB=${GDB:-$(command -v gdb)}
W=${GD_WORK:-$root/scratchpad/finalfight/gdb}; GD_OUT=${GD_OUT:-$W/out}
mkdir -p "$W/out"
[ -x "$GDB" ] || { echo "no gdb (set \$GDB)" >&2; exit 2; }
D=$GHIDRA/Ghidra/Debug
if [ ! -d "$W/pyext/ghidragdb" ]; then
  pip3 install --no-index --find-links "$D/Debugger-rmi-trace/pypkg/dist" --find-links "$D/Debugger-agent-gdb/pypkg/dist" --target "$W/pyext" ghidratrace ghidragdb || exit 2
fi
if [ ! -f "$W/ghproj/ff.gpr" ]; then
  mkdir -p "$W/ghproj"
  "$GHIDRA/support/analyzeHeadless" "$W/ghproj" ff -import "$root/scratchpad/finalfight/ff_main.bin" -processor 68000:BE:32:default -noanalysis > "$W/out/import.log" 2>&1 || { echo "import failed, see $W/out/import.log" >&2; exit 2; }
fi
export PYTHONPATH=$W/pyext MODULE_Debugger_rmi_trace_HOME=$D/Debugger-rmi-trace MODULE_HOME=$D/Debugger-agent-gdb
export GHIDRA_HEADLESS_JAVA_OPTIONS="-Djava.awt.headless=false" RMI_PORT=${RMI_PORT:-15433} RMI_WAIT_MS=60000 RMI_SETTLE_MS=${RMI_SETTLE_MS:-6000} RMI_RAM_OUT=$W/out/trace_ram.bin
ps aux | grep -E "[a]nalyzeHeadless|[m]ame ffightuc.*gdbstub" | grep -q . && { echo "a headless Ghidra or gdbstub MAME is still running; kill it first" >&2; exit 2; }
rm -f "$W/out/trace_ram.bin"
"$GHIDRA/support/analyzeHeadless" "$W/ghproj" ff -process ff_main.bin -noanalysis -readOnly -scriptPath "$here" -preScript HeadlessTraceRmi.java > "$W/out/hl.log" 2>&1 &
hl=$!
for i in $(seq 1 120); do sleep 1; grep -q -E "Listening at|ERROR" "$W/out/hl.log" && break; done
grep -q "Listening at" "$W/out/hl.log" || { echo "Ghidra acceptor did not start, see $W/out/hl.log" >&2; kill -9 $hl; exit 2; }
sh "$here/../gdbmame.sh" 23946 150 > "$W/out/mame_chain.txt" 2>&1 &
mp=$!
for i in $(seq 1 100); do netstat -an -p tcp | grep -q "127.0.0.1.23946 .*LISTEN" && break; sleep 0.2; done
# gdb reads stdin so its event loop runs and ghidragdb's stop hooks fire (-batch -x does not)
( cd "$here"; cat attach1.gdb; sleep 3; cat attach2.gdb; sleep 4; cat attach3.gdb; sleep 12; echo "ghidra trace sync-disable"; echo detach; sleep 1; echo quit ) | "$GDB" -q -nx > "$W/out/gdb_attach.log" 2>&1
for i in $(seq 1 60); do [ -f "$W/out/trace_ram.bin" ] && break; sleep 1; done
sleep 2; kill -9 $mp $hl 2>/dev/null; pkill -9 -f "ghidra.app.util.headless" 2>/dev/null
grep -E "Connected to Ghidra|Connection from|trace=|  (PC|A5|A7|SP|SR|D0) =|mem\[" "$W/out/gdb_attach.log" "$W/out/hl.log" | cut -c1-170
if [ -f "$W/out/trace_ram.bin" ] && [ -f "$GD_OUT/lua_ram_100.bin" ]; then
  python3 - "$W/out/trace_ram.bin" "$GD_OUT/lua_ram_100.bin" <<'PY'
import sys
a, b = open(sys.argv[1], 'rb').read(), open(sys.argv[2], 'rb').read()
eq = sum(1 for x, y in zip(a, b) if x == y)
print('Ghidra trace RAM vs Lua oracle at hit 100: %d of %d bytes equal (%d non-zero)' % (eq, len(b), sum(1 for x in b if x)))
sys.exit(0 if eq == len(a) == len(b) else 1)
PY
else echo "no trace RAM or no oracle dump (run ../gate.sh first)"; exit 1; fi
