# py/gdbstub: MAME's gdbstub as a live debugger (gdb, a Python client, Ghidra)

MAME 0.289 serves the GDB remote protocol with `-debug -debugger gdbstub` (`gdbmame.sh`). Use it for **interactive** sessions: breakpoints, hardware watchpoints (`Z2`/`Z3`/`Z4`), single steps, register and
memory writes, a disassembler and stack walker from gdb itself. Keep the Lua `callcap` harness for scripted corpora (the stub costs a round trip per stop, about 240 stops per second, and has one client slot).
Work files go to `scratchpad/finalfight/gdb/` (`run/`, `out/`, `pyext/`, `ghproj/`).

| file | what it does |
|---|---|
| `gdbmame.sh [port] [secs]` | cold boot `ffightuc` under the stub (default port 23946); the machine stays halted at reset (PC `$5e88c`, SP `$ff1000`) until the first `c` |
| `session.gdb` | an example gdb session: `gdb -q -nx -x py/gdbstub/session.gdb` (m68k, big endian, `break *0x53e`, `stepi`, a watchpoint, `detach`) |
| `rsp.py` | minimal RSP client (stdlib): `c = RSP(port); c.init(); c.regs(); c.mem(a, n); c.bp(a); c.cont(); c.step(); c.write(a, data)`. `init()` is mandatory: `g` and `p` return `E01` until `qXfer:features:read:target.xml` has been read |
| `gate.sh [hits csv]` | the gate: stub cold boot (`gate_ram.py`: `Z0` at the VBL entry `$53e`, continue N times) against a Lua `-debug -debugger none` cold boot (`oracle.lua`, `bpset 53e`); `cmp.py` compares A5/SP/SR at every stop and work RAM at the listed hits |
| `ghidra/chain.sh` | Ghidra's Debugger (TraceRmi) on the stub, headless: `HeadlessTraceRmi.java` runs inside `analyzeHeadless`, gdb does `target remote` plus `ghidra trace connect`, then the trace's RAM is compared with the oracle |

## Proven (this checkout, MAME 0.289, gdb 15.2, Ghidra 12.1.4)

- `gate.sh`: 600 of 600 stops at PC `$53e` exactly (the stub reports `$53e`, not the debugger's +2), A5 `$ffff8000` (sign-extended, the game's `lea $ffff8000,A5`), A5/SP/SR equal the Lua oracle at 600 of 600
  stops, work RAM `$ff0000-$ffffff` equal at hits 1, 2, 10, 100, 300, 600: 65,536 of 65,536 bytes each (10 s). Cold boots are identical with and without `-debug` (README.md "Harness facts"); a state loaded under `-debug` is not.
- Real gdb attaches (`set architecture m68k`, `set endian big`, `target remote`): registers, `x/i`, `break *`, `stepi`, `x/8xb`, a hardware watchpoint, `detach`. `qRcmd` passes through to MAME's console, so `monitor bpset 53e,a5==ffff8000`
  (conditional), `wpset`, `save`, `cpulist` work.
- `ghidra/chain.sh` (42 s with the one-time setup): `Connected to Ghidra 12.1.4`, a trace in language `68000:BE:32:default`, PC `$53e`, A5 `$ffff8000`, SP `$ffff0ff0` read back from the Ghidra side, `mem[$53e]` = `48e7fffe4bf88000...`
  (the `movem.l` at the VBL entry), and the 64 KB work RAM in the trace equals the oracle's hit-100 dump: 65,536 of 65,536 bytes (583 non-zero).

## Limits and traps

- Needs `-debug` as well as `-debugger gdbstub`; one client per MAME process (after it disconnects the port closes and the next client needs a fresh MAME); only the main 68000 is exposed (no Z80; `qRcmd focus audiocpu` switches the
  console but `g`/`m` stay on the main CPU); no `vCont`, no memory map. A watchpoint stop leaves the PC after the writing instruction.
- `gdb -batch -x` does not work with the Ghidra scripts: ghidragdb's stop hooks run in gdb's event loop, so `chain.sh` feeds gdb on stdin.
- Ghidra's own gaps seen: gdb's `ps` is not mapped to Ghidra's `SR` (it reads 0 in the trace); `ghidra trace putmem` of 64 KB in one packet fails (an oversized-message error that surfaces as a bare `NameError`; 16 calls of 4 KB work), `tx-open` hits the same
  `NameError`: use `tx-start`/`tx-commit`.
- `chain.sh` installs `ghidratrace`, `ghidragdb` and `protobuf` from Ghidra's **own bundled wheels, offline** (`pip --no-index --target scratchpad/finalfight/gdb/pyext`); the system Python and gdb are untouched.
  The Homebrew gdb needs Python support (`gdb --configuration` shows it); a Ghidra GUI launch of the "gdb remote" entry offers to pip-install the same packages.
- **Not run: the Ghidra GUI.** The headless chain is the same TraceRmi path; the GUI procedure, from `Debugger-agent-gdb/data/debugger-launchers/remote-gdb.sh`: start `gdbmame.sh 23946 600` and leave it waiting; in Ghidra open a project holding
  `ff_main.bin` (`lua/dumprom.lua`, `68000:BE:32:default`, base 0), open it in the Debugger tool, Debugger menu "Launch with ..." entry "gdb remote": Target `remote`, Host `localhost`, Port `23946`, gdb command your gdb, Architecture `m68k`, Endian `big`
  (set `PYTHONPATH` to `scratchpad/finalfight/gdb/pyext` if it asks for protobuf). Expect registers and memory panes to refresh on Resume/Interrupt; SR reads 0. The stub gives no memory map, so the trace may build no regions for RAM: the static image is `ff_main.bin`.
- Untested: the `callcap` pattern (set PC, run to a sentinel) through the stub, the `G` (write all registers) packet, Ghidra mapping a trace onto the static program.
