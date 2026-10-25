# Developing the emulator

Working notes for the ROM-driven debugging loop. The emulator (`M68000/`, F#)
runs the real TOS 1.00 ROM until it hits an undecoded instruction (an `ILLEGAL:` line on
stderr, see "Undecoded encodings") or a wrong answer, and each pass closes the next gap.

## Build and run

`M68000/run.ps1` is a build-once / exec-many wrapper. A live `window` instance
locks `M68000.exe` and `dotnet run` rebuilds on every call, so the wrapper builds
`M68000.fsproj` once (skip with `-NoBuild`) and always `dotnet exec`s the DLL from
the `M68000/` directory (so `TOS100UK.IMG` / `checkpoint.txt` resolve).

```
./run.ps1 boot 5000000            # cold boot 5M steps, per-instruction trace ON
./run.ps1 repl 100000             # cold boot 100k steps, then the REPL
./run.ps1 rrepl frontier.snap     # load a snapshot straight into the REPL
./run.ps1 snap 5000000 f.snap     # boot 5M steps, save a snapshot
./run.ps1 resume f.snap 20000000  # load snapshot, run 20M more steps
./run.ps1 window                  # live SDL2 window (F12 / close to quit)
./run.ps1 verify 5000000          # boot 5M steps, diff vs checkpoint.txt (exit code = result)
./run.ps1 selftest tests/680x0    # 680x0 ProcessorTests vectors vs Cpu.Step
./run.ps1 teartest f.snap 60      # headless cursor-path frame dump
```

Trace is ON for `boot`/`trace` (you run those to read it) and OFF elsewhere.
`-Trace` forces it on; `-NoBuild` skips the build. The `Debug` configuration is built
optimized (`M68000.fsproj`), so `bin/Debug/...` is the fast build; set `Optimize` to false there
only to step the emulator in a debugger. Run `./run.ps1` with no args
for the full subcommand list.

The raw form still works: `dotnet exec bin/Debug/net8.0/M68000.dll <argv>` where
`<argv>` is any of the modes in `Program.fs`'s `main`. It traces every instruction to stdout
(tens of MB a minute) unless `ATARI_NOTRACE=1` is set; the Python drivers set it.

The REPL (`repl`, `resume <snap> repl`) reads one command per line from stdin; `help` lists them. A
blank line and a whole-line `#` comment (leading spaces allowed) are skipped. EOF or `q` ends it with exit
code 0. Any other line that does not run (an unknown command, a wrong argument count, an operand that does
not parse, a bad `callcap` preset or `mouse`/`wprot` operand) prints `REPL error: <line no>: <line>: <reason>`
to stderr and exits 1 without running the rest of the input, so a typo stops a piped drive script instead
of truncating it while the caller reads the snapshot taken so far. A driver must check the exit code and
show stderr. The shared drivers raise with the exit code and the stderr tail: `tools/pm_fsm_diff.py`,
`tools/capture_hits.py`, and under `reversing/` cadaver's `secrets/repl.py`, impossamole's `boss/repl.py` and
both `route_driver.py`, supersprint's `repl.py` and `ai_econ/aiutil.py`, populous's `popdrive.py`,
`powers/pwlib.py`, `endgame/eg.py` and `ai/livelib.py`, black tiger's `btcommon.py`, `btlib.py`, `btsec.py`,
`graphics/drive.py`, `sound/verify_psg.py` and `ai/btharness.py`, and powermonger's `ui/uilib.py` and
`commander/loop.py`. A one-off script with its own `subprocess.run` needs the same `returncode` check. A
persistent driver that pairs each command with a reply must still not send a blank line: it gets no reply.
An exception from the emulator itself (an unimplemented instruction, a missing `disk` file) or from a
negative hex operand (`ArgumentException`) still aborts the process with the .NET stack trace and a
non-zero code.

### macOS

There is no PowerShell, so use the raw form (`dotnet build -c Debug M68000.fsproj`, then
`ATARI_NOTRACE=1 dotnet exec ...`), `ps aux | grep M68000.dll` for `tasklist` and `pkill -f` for
`taskkill`. The .NET 8 SDK builds it unchanged, and a drive recipe gives the same snapshots as on
Windows (Populous `repro` and `late1..4`: same frames and state). `TOS100UK.IMG` is Hatari's
`tos100uk.img` copied into `M68000/`. There is
no `timeout` command, so bound runs with step counts instead. Ghidra 12.1 ships no macOS decompiler binary: build it once
with `cd <ghidra>/support/gradle && ./gradlew buildNatives` (Xcode command-line tools, JDK 21; the
wrapper fetches Gradle), otherwise `analyzeHeadless` imports and analyses but writes no C.

Real Hatari has no Mac binary here: build `~/GitHub/hatari` out of tree as x86_64 (`cmake ~/GitHub/hatari
-DENABLE_OSX_BUNDLE=0 -DCMAKE_OSX_ARCHITECTURES=x86_64 && make hatari`; the Homebrew libraries in `/usr/local` are
x86_64, so an arm64 link fails) and run it under `arch -x86_64`. `tools/hatari_trace.py` expects a Windows
`hatari.exe`; to drive Hatari headless on the Mac use its control socket the way
`reversing/cadaver/py/secrets/hatari_xp_check.py` does: `SDL_VIDEODRIVER=dummy`, a socket path short enough for
AF_UNIX, a pty for stdout (debugger output is block-buffered into a file), every `hatari-debug` command sent while
the emulation runs (they are ignored while `hatari-stop` has paused it), and Esc as `0x01` (a one-character key
argument is ASCII). The mouse: `hatari-event mousemove dx dy` is relative and the IKBD clamps the absolute cursor
at 0, so pin with `mousemove -2000 -2000`, then move to the target and read the game's own pointer back;
`leftdown`/`leftup` click. To sample memory on every hit without stopping, use `b pc=$addr :trace :quiet :file f.dbg`
with `echo`/`m` lines in the file (single-quoted expressions such as `'a6-146'` and `'VBL'` are expanded). With
only two such breakpoints set, Hatari once reported a stack word changing inside a call that no handler can reach;
a third breakpoint made it vanish: cross-check any surprising mid-call change. Worked example with mouse menus:
`reversing/populous/py/systems/hatari_edges.py`.

## Python tooling (`tools/`, `reversing/<game>/py/`)

`M68000/pyproject.toml` lists the two third-party deps the scripts use (`numpy`, `pillow`,
e.g. for `gfxview.py`/`screendump.py`). Default to [`uv`](https://docs.astral.sh/uv/) over bare
`pip`/`python3 -m pip install`:

```
cd M68000
uv sync                        # once per checkout - creates M68000/.venv, installs numpy+pillow
uv run python tools/gfxview.py game.snap --html game.html
```

or activate the venv once per shell (`source M68000/.venv/bin/activate`) and the many `python
tools/foo.py ...` examples throughout this doc and `reversing/<game>/` work as written. `.venv/` is
git-ignored; `uv.lock` is committed. A new dependency: `uv add <package>` (updates `pyproject.toml`
+ `uv.lock`), not a bare `pip install`.

## Live window input (`Video.fs`)

`./run.ps1 window` (or `window resume <snap>`) opens the SDL2 window and feeds
host input back to the emulator as IKBD serial packets:

- **keyboard** - physical-position scancode map (`scancodeMap`), make on keydown,
  break (`| $80`) on keyup. Covers the typing area, arrow/edit cluster, function
  row, Help/Undo. F12 or closing the window quits.
- **mouse** - relative mode; motion is accumulated and flushed as `$F8`-header
  relative packets once per frame (front-loaded, to avoid catching a half-drawn
  VDI cursor at the VBL). Button edges send immediately. When the program put the
  IKBD in absolute mode (`$09`), no packet is sent: the motion only moves the
  6301's cursor, which the program reads with `$0D` (`MMU.MoveMouse`). If the running program
  put the IKBD into "buttons report as keycodes" mode (command `$07` bit 2, e.g.
  Electronic Pool), a left/right button edge is *also* delivered as key
  `$74`/`$F4` / `$75`/`$F5` via `MMU.EnqueueMouseButton` - a no-op in every other
  mode, so no existing target is affected.
- **joystick 0** - the arrow cluster is also mapped to a joystick-0 state byte
  (`joyBitMap`): Up = fire bit `$80`, Down = `$02`, Left = `$04`, Right = `$08`.
  Emitted as a `$FE` + state-byte report on any key edge, coalesced to one packet
  per frame like the mouse. This is what makes Super Sprint playable from the
  window - it reads the fire bit as the accelerator (see
  `reversing/supersprint/README.md`).

## IKBD command interpreter (`MMU.fs`)

There is no emulated 6301, but the bytes the CPU sends to the keyboard ACIA
transmit register (`$FFFC02`) are parsed (`ikbdTransmit` / `ikbdDispatch`,
command lengths transcribed from Hatari `src/ikbd.c`). It tracks only what target
programs set: the mouse report mode (`$08`/`$09`/`$0A`/`$12`), the mouse
button-action mode (`$07` - bit 2 = "buttons report as keycodes `$74`/`$75`",
what Electronic Pool uses), the joystick auto-report flag (`$14`/`$15`/`$1A`),
and `$80 $01` reset. Nothing here is read back by the CPU, so it is **not** in
`MmuSnapshot` and the 30M diskless boot stays byte-identical.

`ATARI_TRACE_IKBD=1` logs every completed command and every state change to
stderr (survives `ATARI_NOTRACE`) - use it to see which input mode a program
actually asks for. The REPL gets a `mouse` command that goes through the same
mode-aware synthesis the live window uses:

```
mouse move <dx> <dy>     relative motion -> $F8 dx dy packet; in absolute mode ($09) only
                         the 6301's cursor moves (the program reads it with $0D), no packet
mouse down l|r           button press    -> $74/$75 keycode in buttons-as-keys mode, else nothing
mouse up   l|r           button release
```

## `ATARI_NOTRACE`

`ATARI_NOTRACE=1` clears `Trace.enabled` (68k.fs), which the per-step `printfn`
trace sites and `ResolveEa`'s operand-description strings test before formatting
anything, and redirects `Console.Out` to a null sink for the few ungated prints.
Building the trace text costs more than executing the instruction, so a
new decoder's `printfn` must sit behind `if Trace.enabled then` (and an operand
string must be `if Trace.enabled then sprintf ... else ""`). It does not silence result
output: REPL replies, `verify` / `selftest` verdicts and snapshot/until status
lines go through `Diag.result` (68k.fs), which is captured before the redirect.
So `ATARI_NOTRACE=1 ... verify` prints its PASS/FAIL, and a `NOTRACE` REPL still
answers `r` / `m`. `watch` / `ATARI_TRACE_GEMDOS` already used stderr and are
unaffected.

## Performance

A 30M-step diskless boot (`snap 30000000`, trace off) takes about 6.8 s on the Intel Xeon W-3223
Mac, 4.4M steps/s; a real ST executes roughly 1M instructions/s. The same run took 74 s (0.41M
steps/s) before the work below. Where the cost went, in the order it was removed:

| Cost | Fix | 30M boot |
|---|---|---|
| Unoptimized `Debug` build | `M68000.fsproj` optimizes the `Debug` configuration | 74.0 s -> 35.6 s |
| Trace text built per instruction and discarded under `ATARI_NOTRACE` | `Trace.enabled` gate (see above) | -> 16.4 s |
| RAM was the last arm of every MMU `match`, with a per-byte `Some` and bank-size recompute | `ramDirect` fast path at the top of `ReadByte/Word/Long`, `WriteByte/Word` | -> 13.4 s |
| Ungated `printf` of the PC in `AtartSt.Step` | same gate | -> 8.6 s |
| Five `stepCount % period` tests compiled to 64-bit `div` | periods are `[<Literal>]`s in `Program.fs`'s `StepPeriods` | -> 7.9 s |
| MOVE fault bookkeeping on every MOVE (`mergeFixup` closure + `Set`, `Some` for `FaultCcr`, `Move` pattern in `TryFastForwardTbdrPoll`) | empty-list short-circuit, `FaultCcr` as a `voption`, bit-mask pre-test | -> 7.1 s |
| Every active pattern allocated `Some(tuple)` | `[<return: Struct>]`, `ValueSome(struct (...))`; call sites unchanged | -> 6.9 s |

Rules that keep it there:

- A new decoder's `printfn`, and any operand-description `sprintf`, sits behind `if Trace.enabled`.
- Periods and other per-step constants in `AtartSt.Step` are literals, not instance fields.
- A new active pattern in `Instructions.fs` is a struct `ValueOption` pattern.
- `ramDirect` (`MMU.fs`) only covers `memConfigByte` low nibble 5 and `[$8, $100000)`; everything
  else takes the original dispatch. `selftest` runs the flat test bus and never reaches it, so an
  MMU change is gated by the 30M snapshot compare and a game snapshot compare, not by `selftest`.
- With no memory hooks set, an unhooked RAM read or write is one `null` test plus `ramDirect` and no
  call; anything hook-related goes behind that test (section "Memory hooks").

What remains is allocation in the CPU core: the immutable `Cpu` record is copied (104 B) two or
three times per instruction, about 250 B and several objects per step, and macOS's slow
thread-local allocation helper makes each one dear. The one remaining fix is a mutable `Cpu`
(estimated ~15%, not attempted; it needs a per-instruction register snapshot for the group-0
fault handler and clones for `Preview` and for callers of `st.Cpu`). Tried and rejected:

- Struct `EaResolved` plus a struct-tuple `ResolveEa`: allocation fell from 247 to 173 B/step but
  the boot got about 7% slower (interleaved A/B, 5 runs each). The nested value tuple is probably
  too large for the JIT to enregister (an inference, not checked).
- GC and tiering knobs (`gcConcurrent`, `GCgen0size`, `TieredPGO`, `TieredCompilation`, W^X, .NET
  10): none beat the default.
  Re-measured on a Cadaver and a Populous snapshot (`s 10000000` through `dotnet exec`, 10 interleaved rounds, end snapshots `cmp`-identical in all 228 runs): `gcConcurrent=0`, `GCgen0size` 32M/64M/256M,
  `TieredCompilation=0`, `TC_QuickJitForLoops=0`, `TieredPGO=0`, `OSR_HitLimit=1` and two combinations all landed within about +-3% of the default, none won every pair, and 256M, `TieredPGO=0` and
  `TieredCompilation=0` leaned slower. `GCgen0size` is honoured (gen-0 collections fell from 66 to 8 on Cadaver) without any gain, so the cost is the allocation helper, not collection. Allocation is 287 B
  per step on Cadaver and 385 on Populous, with no zero-allocation step: a branch is exactly one 104 B `Cpu` copy, MOVEQ and shifts two, MOVE 400 to 600 B (`ResolveEa` returns a tuple with a boxed `EaResolved` and a
  closure for `(An)+`/`-(An)`, `68k.fs:1049-1075`). `AtartSt.Step`'s `MachineState` is a struct and allocates nothing.
- A 64K-entry opcode dispatch table: the sequential pattern chain costs about 0.7 ns per failed
  pattern, so the estimate is 1-2%; not worth the aliasing-order risk.

Measuring on macOS (no `dotnet-trace`; the runtime writes no perf map there):

- Time with `ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll 30000000 snapshot <path>` and
  byte-compare the snapshot against a pre-change build's. Run-to-run noise is about 0.3 s, so a
  change under ~5% needs an interleaved A/B of two builds (`dotnet build -c Debug -o <dir>` for
  each), five runs apiece, not two sequential runs.
- `sample <pid> 4 -file out.txt` on the running process names the native frames; 40% in
  `JIT_NewS_MP_FastPortable`, `_tlv_get_addr` and `bzero` is allocation. JIT'd frames stay
  unsymbolised: match a hot address cluster against `DOTNET_JitDisasm=Step
  DOTNET_JitStdOutFile=<f>` output by instruction offsets.
- For per-opcode allocation and time, drive `AtartSt` from a `dotnet fsi` script that `#r`s the
  DLL and reads `GC.GetAllocatedBytesForCurrentThread()` around each `Step()`. Run it with
  `DOTNET_gcServer=0` (fsi defaults to Server GC, which inflates allocation-heavy opcodes by
  ~1.7x); its per-opcode ns include the harness's own ~60 ns, so use it for ranking and for bytes,
  not for absolute times. Boot is 83% ROM code: time a game snapshot as well.

## Regression tests: `selftest`

There is no full unit suite. `selftest` runs the
[SingleStepTests / ProcessorTests](https://github.com/SingleStepTests/ProcessorTests)
68000 vectors (`680x0/68000/v1`, one `NAME.json.gz` per opcode, ~8000 randomised
cases each: full initial state -> expected final registers / SR / memory) against
`Cpu.Step`. It catches the class of bug that stays silent under ROM-driven testing (an
`LSR.L` / `ROR.L` sign-smear fails thousands of shift cases the instant it is written).

```
python tools/fetch_680x0_tests.py            # -> M68000/tests/680x0/ (git-ignored, ~190 MB)
python tools/fetch_680x0_tests.py --only LSR ROR
./run.ps1 selftest tests/680x0               # all downloaded opcodes
./run.ps1 selftest tests/680x0 lsr           # filter by file-name substring
```

Output is one line per opcode with the failures split three ways -
`fail (N wrong  N frame  N unimpl)` - plus up to 5 sample `FAIL` lines
(**wrong-answers first** - those are the actionable ones), a `TOTAL` with the
same breakdown, and a **`wrong-answer files (chase these)`** digest listing every
file that still has a genuine flag/register bug, worst first. Non-zero exit if
anything failed.

All 124 files pass: `TOTAL 1000051 pass 0 fail 9 skip`, 0 in every lane. The gate is
0 wrong and 9 skip; the pass total moves when vectors are added or skip rules change,
so do not gate on it. `runCase` skips by three rules: two corrupt `ASL.b.json` vectors
(opcode `$E502` expects a byte shift to rewrite all 32 bits of D2; `isCorruptVector` in
`Program.fs`), DIVS cases whose undefined flags the vectors disagree on
(`isUndefinedDivByZeroFlags`), and a PC or RAM address below 8.

The three failure classes:
- **`wrong`** - a real flag / register / memory divergence. Fix these.
- **`frame`** - the vectors expect the instruction to fault and push a frame and the
  stacked words differ. Group-0 faults (bus and address error) push the real 14-byte
  frame (`EnterGroup0Vector`), so this lane is empty; a new fault path that pushes the
  wrong frame shows up here.
- **`unimpl`** - an encoding `Cpu.Step` does not decode: it raised `IllegalEncoding` and
  took vector 4 (see "Undecoded encodings" below), or threw. Add the mode when a target
  needs it.

What it does and does not cover:

- **Modelled:** the whole 24-bit space as flat RAM (`MMU(flatTestBus = true)`), so only a
  case whose PC or listed RAM address is below 8 is skipped. It never reaches the MMU's
  RAM fast path or any device, so an MMU change is gated by the 30M snapshot compare and a
  game snapshot compare, not by `selftest`.
- **Not modelled:** the prefetch queue. `pc` is compared as "next instruction address",
  right for this interpreter and off by the prefetch amount for a few instruction classes
  the vectors happen not to exercise.

### Undecoded encodings

An opcode word or EA combination the decoders do not handle (an illegal 68000 encoding
such as `MOVE.B An,Dn` or MOVES `$0Exx`, or a legal one not implemented yet) takes the
illegal-instruction exception, vector 4, with the opcode's own address stacked (M68000PRM
Table B-1; line-A `$Axxx` is vector 10 and line-F `$Fxxx` vector 11, handled in `Step`
itself). Real hardware does the same for an unassigned encoding, so a game's CPU probe or
copy protection runs on. Because it can also be a gap in this core, the first entry at each
PC prints one stderr line (survives `ATARI_NOTRACE`, at most 64 PCs a process), and the
trace shows `illegal encoding $xxxx (...) -> vector 4`:

```
ILLEGAL: pc=$020000 opcode=$1008 not decoded (MOVE.B with An operand is illegal (instruction 0x1008)) -> vector 4
```

A run used to abort at that point with `Step failed at PC=...`; it now continues into the
program's (or TOS's) vector-4 handler, and a `callcap` reports the handler's run (usually a
`STEP CAP` or a loop) instead of `THREW`. Grep stderr for `ILLEGAL:` when a run goes wrong.

## Snapshot / preview fidelity: `detcheck`

The REPL and `.snap` files are the lab instruments of every reverse-engineering
workstream, so a restore has to be an *identity operation on every piece of state
a later `Step()` can read* - not just RAM + CPU registers. The `detcheck N` REPL
command asserts exactly that:

```
save S  ->  run N steps, FNV-hash the per-step (stepCount, PC, CCR, D0-7/A0-7,
            mutation delta, ack delta, PeripheralPhase)  ->  T1
restore S  ->  run N again  ->  T2
assert T1 == T2   (and report the first divergent step if not)
```

`AtartSt.DeterminismCheck`. Run it with live PowerMonger gameplay, an armed
Timer B, active FDC I/O and queued IKBD input: the cases a snapshot most easily
loses. It is byte-identical on diskless idle (100k), the PowerMonger boot loader
through FDC reads (3M), live gameplay (2M) and queued IKBD input.

What makes a restore an identity operation:
- `MmuSnapshot` (and `SaveState`/`LoadState`, format v9) carries the latent
  future-determining device state: the six pending-interrupt slots + `mfpVector`,
  `tbCounter` (Timer B's HBL prescaler), the FDC INTRQ countdown
  (`fdcIrq`/`fdcIrqPending`), the DMA sector counter, the IKBD reporting-mode
  latches, and the absolute-mouse / joystick registers. Pre-v9 `.snap` files load
  with documented power-on defaults.
- `Preview` restores `stepCount` too. It is the phase clock for the VBL/HBL/Timer
  raises and scheduled IKBD injection, so a `p 10000` that did not would shift the
  machine's temporal phase permanently while PC and RAM looked untouched.
- The loop detector folds `mmu.PeripheralPhase` (a fingerprint of those latent
  counters) into its recurrence gate, so "provably stuck" is a real proof: same CPU
  state + unchanged mutation counter + unchanged latent device phase + no interrupt
  acked for a frame => the next step's inputs are identical to an earlier step's.
  Residual: an armed self-reloading event-count timer keeps `PeripheralPhase`
  churning, which *suppresses* the check rather than firing it falsely: a missed
  detection, never a false positive.

Disk A: which image is mounted is external state (pass `--disk-a` on resume, as on the
first run), but what the run wrote to it is not. `MMU.fs` journals every Write Sector and
Write Track sector (`diskLog`, the 512 bytes each one replaced): `MmuSnapshot` records the
journal's length, so `callcap`, `Preview` and `detcheck` roll disk writes back with RAM, and
`SaveState` appends an optional `DSKA` section (FNV-1a of the image as mounted, then each
written sector's offset and contents) after the v11 block, without a version bump.
`LoadState` re-applies it when the mounted image hashes the same, and warns and resumes with
the image as mounted otherwise (wrong or no `--disk-a`). A run that never wrote to the disk
writes no section, so its snapshot is byte-identical to the plain v11 layout; an older build
reads up to the section and ignores it (it never checks for end of file), resuming with the
unwritten image as before. The write-protect tab (`wprot`) is not saved.

`mutations` / `interruptAcks` are deliberately NOT restored (nothing reads their
absolute value; the loop detector re-baselines them each epoch) - `detcheck`
folds their per-run delta so the two replays stay comparable.

## Program analysis: `ATARI_TRACE_EVENTS` + `tools/trace_cfg.py`

For reverse-engineering a program's control flow (rather than closing ROM
instruction gaps). `ATARI_TRACE_EVENTS=<path>` makes `AtartSt.Step` write a
compact binary record per **flow-control** instruction - or per instruction with
`ATARI_TRACE_EVENTS_ALL=1` - straight to its own file, so it is unaffected by
`ATARI_NOTRACE`. One emission point (`Atari.TraceEvents`), not the 221 `printfn`
sites.

Record: `stepCount, pc, target` (address actually executed next), `opcode`, and a
`kind` byte classified from the opcode + PC transition
(`seq / branch-taken / branch-not-taken / call / ret / trap / interrupt`).
Interrupt is detected via an `MMU.InterruptAcks` delta.

```
ATARI_TRACE_EVENTS=boot.evt ./run.ps1 -NoBuild snap 3000000 t.snap
python tools/trace_cfg.py boot.evt                      # summary + coverage map
python tools/trace_cfg.py boot.evt --cfg cfg.dot --callgraph cg.dot --blocks b.txt
python tools/trace_cfg.py boot.evt --range fc0700 fc0900 --disasm   # windowed, annotated
dot -Tsvg cfg.dot -o cfg.svg
```

`trace_cfg.py` reconstructs basic blocks (real start/end addrs + hit counts), a
CFG and a call graph (Graphviz DOT), and an executed-address coverage map, from
the event stream alone - no re-execution. Block boundaries are derived, not
disassembled, so cross-check them with `tools/disassemble.py` (`--disasm` does
this for ROM blocks). Flow-only logs give approximate byte coverage;
`ATARI_TRACE_EVENTS_ALL=1` makes it exact at ~20 bytes/step. `M68000/tos100uk.sym`
(`addr<TAB>name`) is auto-loaded so ROM routines show by name - extend it as
passes identify routines; `--names <file>` overrides.

`ATARI_TRACE_GEMDOS=1` additionally decodes `Pexec` (GEMDOS $4B) calls and dumps
the loaded program's basepage (TEXT/DATA/BSS base+len) so trace PCs map back to
file offsets - and, when `ATARI_TRACE_EVENTS` is also set, writes a
`<path>.basepages.json` sidecar next to the event log. `Pexec` tracking is a
stack (mode 4/6 "just go" never returns); for mode 0/1 (load and run) the
basepage is sampled from `act_pd` ($602C) while the child is live, since their D0
on return is the exit code, not the basepage.

`ATARI_TRACE_OS=1` is the **trace narrator**: it turns the run into a readable log
of the OS calls it makes instead of a wall of `trap #1` lines. GEMDOS (trap #1),
BIOS (trap #13) and XBIOS (trap #14) are decoded into `name(arg=value, ...)` with
string pointers dereferenced and quoted and character codes shown as `'x'`; the
`= $xxxxxxxx` line under each call is its D0 return (with the GEMDOS error name,
e.g. `(-33 EFILNF)`, when negative). Nested calls (a `Pexec`'d child's own
traffic) indent under their parent; a call that never returns (`Pexec` "just go",
an unbalanced `Super`) is swept when an outer call returns so the indent can't run
away. AES and VDI (`trap #2`, family in D0, parameter block in D1) are decoded
too: `AES $0a appl_init(int_in=0, int_out=1, ...)`, `VDI $06 v_pline(handle=1,
nintin=0, nptsin=2)` - opcode name plus the `control[]` counts. `Atari.OsCalls`
holds the function tables - extend them as needed. Stderr, like the other `ATARI_TRACE_*` switches, and
it does not touch CPU/MMU state. Independently, `tos100uk.sym` is loaded by the
emulator itself now: the per-instruction trace prefix shows `<flop_rw>` etc. when
the PC is a known routine entry (silenced with the rest of the trace under
`ATARI_NOTRACE`).

```
ATARI_TRACE_OS=1 ./run.ps1 -NoBuild -DiskA inttest_disk.st snap 12000000 t.snap 2>&1 | grep '^OS '
#   OS   1871131     Cconws("Test '")
#   OS   1871324       Bconout(dev=2, c='T')
#   OS   1873215     = $00fc0005
#   OS    353215   Fsfirst("\AUTO\*.PRG", attr=$7)
#   OS    356874   = $ffffffdf (-33 EFILNF)
```

## Running a program off a disk image

`./run.ps1 -DiskA <file.st> <subcommand> ...` (or the `--disk-a <file.st>` argv
switch, or the `ATARI_DISK_A=<file.st>` env var as a fallback) mounts a real
`.ST` floppy image in drive A. The FDC
models single- and double-sided images, PSG side/drive select, Type I head
movement (seek/restore/step), the DMA address counter and the `$FF8606` DMA
status register - enough for TOS to read a FAT12 filesystem and `Pexec` a
program. Write Sector (`$Ax`) is also modelled, so GEMDOS can create
directories and write files (`Dcreate`/`Fcreate`/`Fwrite`/`Fseek`), and so is
Write Track (`$Fx`): the track stream is parsed for its ID and data fields and
each 512-byte sector lands in the image, enough for a game's own formatter
(PowerMonger's FORMAT, `reversing/powermonger/system.md`; Hatari does not do
this for `.ST`). Writes hit the in-memory image only - the host `.ST` file is never modified, so runs stay
deterministic and committed disk artefacts stay byte-stable. `ATARI_TRACE_FDC=1`
logs every FDC register/command write and every sector read/write to stderr
(compare against `tools/hatari_trace.py --trace fdc`).

**Raw `.ST` sector dumps only - `.stx` (Pasti) is not supported.** `MMU.LoadDiskA` reads the file
straight into a flat byte array and takes its geometry from the FAT BPB (sectors per track at 24,
sides at 26) only when the BPB's total-sector count (bytes 19-20) matches the file size; otherwise it
guesses from the size, as Hatari's `Floppy_DoubleCheckFormat` does (under 500 KB one side, then 9..12
sectors per track over 80..84 tracks). That is what lets a raw-sector disk whose sector 0 is not a
BPB (Cadaver's levels disk, PowerMonger's save disk) load with its real geometry. Every sector
read/write is `logicalSector * 512` into that array. There is no image-format signature
check anywhere in the tree, so handing it a `.stx` container (flux-level, used for copy-protected
originals, `RSY\0`-prefixed and not a multiple of 512 bytes) is not rejected - it is silently
misread as a raw sector image, the bogus BPB falls back to the size-based guess, and every
"sector" comes back as garbage from wherever that offset lands in the Pasti container. Convert to
`.st` first (no converter exists in `tools/` yet) or use a `.st`-format release of the same disk.

**Bootable disks work too, unchanged.** The real TOS ROM loads sector 0, verifies
the `$1234` word-sum and jumps to the boot code itself - the emulator only serves
the sectors. `A_013.ST` (a bootable "Automation"-style menu disk with LSD-packed
games) boots to its menu; menu game 2 (Super Sprint) runs straight through,
menu games 3 and 4 (ST Karate, Electronic Pool) run into full gameplay with no
emulator change, and menu game 1 (Super Hang-On) needs seven general 68000/ST
fixes (STOP, MOVEP, ADDA.L/LEA modes, a coarse MFP Timer A for its software-synth
music, PSG `$FF88xx` mirror, ReadLong shifter-register case). Hang-On's intro
crawls through a long software-synth sequence on the coarse Timer A tick and is
slow to reach its title; its post-title raster split uses event-count Timer B,
driven per-scanline (see MFP timers below). Pool's mouse menu works through the
IKBD "mouse buttons act as keys" mode (`$07 $04`, see the IKBD command
interpreter above). See `reversing/a_013/`.

**FDC completion signalling (WD1772 INTRQ / MFP GPIP bit 5).** GPIP bit 5 (FDC
interrupt line, active-low) idles high and re-raises a coarse delay after a
command, cleared on a status read or a new command (`MMU`'s `fdcIrq` /
`FdcTick`). The delay matters because TOS's post-autoboot FDC self-test at
`$fc04a8` issues 8 bogus WD1772 commands and expects each to still be running
when its `_hz_200`+10 poll expires. If the line read "always complete", the
self-test would re-`jsr` the boot sector in `_dskbufp` every iteration, and a
crack whose boot sector checksums to `$1234` (PowerMonger `[cr Replicants]`, TDT
"ALTAIR ANTI VIRUS") would loop forever. With the delay the self-test's first
polled command (a Restore) times out like real hardware and the loop exits;
`[cr Replicants]` boots to its cracktro key-wait. There is no per-command WD1772
state machine (Hatari's `src/fdc.c` has one), so the delay is bucketed:

- a Read/Write Sector that moved data raises INTRQ immediately (the bytes are
  already in RAM, and a per-sector delay would add tens of millions of steps to a
  big load);
- a Seek/Step gets about 4000 steps;
- a Restore, failed search or Read Address gets about 120000 (about 4x the
  self-test's ~30000-step deadline, about 1/12 of the GEMDOS `$40000`-iteration
  poll budget). `$fc04d6` issues a Restore first every self-test iteration, so
  this bucket is what times the self-test out (`$fc04cc` runs 0 times).

The diskless-boot checkpoint (`checkpoint.txt`) is baselined with this self-test
spinning rather than short-circuiting.

Known gap: past the cracktro key-wait `[cr Replicants]` loads about 1 MB of game
data (all FDC reads OK) then its depacker derails to `PC=$20`. `[cr Empire]`'s
WARI.PRG and the HxC WAR.PRG fail the same undiagnosed way.

**MFP timers.** Timer C is the system tick (`instructionsPerFrame/4`). Timer A
(`/64`) and Timer B's delay / pulse modes are off until a program arms them
(gated on the control register plus the channel's IERA/IMRA bit, which TOS never
sets for A/B), then tick on an instruction count - coarse, not per-scanline;
enough for a counter-only ISR (a music tempo counter), wrong tempo.

Timer B in **event-count mode** (`TBCR` low nibble `$08`) is the exception: it is
driven scanline-accurately. `Program.fs` calls `mmu.HblTick()` once per
`instructionsPerLine` (`instructionsPerFrame/300` = 40 - a divisor that lands line
0 on the VBL boundary for the recorder), and `HblTick` decrements a live counter
seeded from `TBDR`, raising the Timer B interrupt on each underflow so a raster
ISR fires at the scanline the game
programmed rather than at an arbitrary instruction count. Super Sprint's menu and
results-screen Timer B ISR (not the race: that runs on the ROM VBL handler), Super
Hang-On's post-title split and Impossamole's attract all run `TBCR=$08` and are
driven by this. The counter is not in `MmuSnapshot` (TOS
never arms event-count Timer B, so the diskless boot stays byte-identical; a
mid-split resume loses at most one scanline of counter phase).

`STOP #imm` is modelled as an idle (`Cpu.Stopped`) that spins until a pending
interrupt outranks the mask STOP loaded into SR.

Build a disk with a program TOS will auto-run at boot:

```
python tools/make_blank_disk.py blank.st                 # empty FAT12 image
python tools/make_test_prg.py TEST.PRG                    # or bring your own .PRG
python tools/add_file_to_disk.py blank.st TEST.PRG --auto --out auto.st
ATARI_TRACE_GEMDOS=1 ATARI_TRACE_EVENTS=run.evt \
  ./run.ps1 -NoBuild -DiskA auto.st snap 12000000 t.snap
python tools/trace_cfg.py run.evt --steps <lo> <hi> --range <tbase> <tend> --cfg prg.dot
```

`M68000/auto_test.st` is the committed ready-to-use image (`blank_80ss.st` +
`\AUTO\TEST.PRG`, the loop-and-Pterm0 program from `make_test_prg.py`). Use
`--steps` to isolate the program's own run - once it terminates, TOS reuses its
TPA addresses for the desktop.

## Graphics/palette explorer: `tools/gfxview.py`

`screendump.py` shows the *live framebuffer*. `gfxview.py` shows everything else -
the bitmaps, sprites, fonts, tiles and palettes a program has decoded into RAM but
not yet drawn. It reads a `.snap` directly (the whole 1 MB RAM image is in there -
`load_ram` parses the `A68S` header: magic, version byte, 19 int32 regs, int16
CCR, then the length-prefixed RAM array first) or any raw binary with `--raw`
`--base <hex>`.

```
python tools/gfxview.py game.snap --html game.html          # interactive viewer
python tools/gfxview.py game.snap --contact ram.png         # whole-RAM overview PNG
python tools/gfxview.py blob.bin --raw --base 21100 --html b.html
```

It auto-detects and prints (to stderr, and bakes into the HTML as jump targets):

* **palettes** - runs of 16 `$0RGB` words. STF (every gun nibble 0..7) by default;
  `--ste` also reports STE-style ones (noisier). Packed palette *tables* are
  common - Super Sprint keeps a 19-entry title-screen fade ramp near `$1d3xx`.
* **data spans** - 2 KB blocks holding non-trivial data (not mostly `$00`/`$FF`,
  graphics-ish byte entropy), merged into runs. Advisory, just to aim the viewer.

The `--html` output is one self-contained file (RAM base64-embedded, JS decoder,
no server). Live controls: base address, width, rows, bpp (1/2/4/8), zoom, palette
(dropdown of every detected palette + greyscale), and the plane layout:

* `st-interleaved` - standard ST screen memory, bitplanes interleaved per 16-px
  word group (what the shifter reads, what `screendump.py` decodes).
* `planar-linear` - bitplanes stored contiguously, each a plain 1bpp bitmap;
  plane `p` at `base + p*plane_stride`, rows every `row_stride` bytes. Super
  Sprint's transposed sprite blitter (`$15436`) uses `plane_stride 8`,
  `row_stride 1` (planes at `src+8/+16/+24`, source `+1` byte/row) - the
  "SS sprite tile 8x8x4" preset.
* `tiles 8x8x4` - a sheet of 32-byte planar cells (4 planes of 8 bytes, one byte
  per row, planes contiguous), `width/8` cells per row. The usual packed layout
  for 4-plane fonts / tilesets. "tile sheet 32x32 cells" preset.
* `chunky8` - one byte per pixel.

`ATARI_GFX_SIDECAR=<snap>.gfx` makes the emulator write a `.gfx` sidecar as it
runs: `palette $xxxxxxxx` for every XBIOS Setpalette address, `pointer
screen_log|screen_phys $xxxxxxxx` for every XBIOS Setscreen base. Behaviourally
inert (only writes the file), like `ATARI_TRACE_OS`. `gfxview.py` auto-loads
`<input>.gfx`, adds the pointers as jump targets, and force-includes any observed
palette address the `$0RGB`-run heuristic didn't find on its own.

The viewer's decoder is verified byte-identical to `screendump.py` /
`Instructions.fs` (the `tiles` mode unit-checked separately). Worked example with
example PNGs: `reversing/supersprint/gfxview.md`.

## Recording a video

`ATARI_FRAME_DIR=<dir>` (optional `ATARI_FRAME_EVERY=<n>`, default 1) makes the
emulator dump one `fNNNNNN.bin` per captured VBL:

```
[rez:1][screen:32000][200 x row-record], row-record = [baseHi:1][baseLo:1][palette:32]
```

one row-record per visible scanline, captured on that line's HBL crossing, so a
mid-frame raster palette split renders with the right colours per band instead of
one flat palette. Each dump is written at the VBL *after* the frame it describes,
so the screen grab and the 200 row-records come from the same frame (a lag of one
frame would be invisible on a static screen and wrong for anything that repaints
its palette every frame, such as Super Sprint's raster split). The last frame is held pending and
never flushed. Behaviourally inert, like `ATARI_GFX_SIDECAR` (only writes files;
30M diskless boot stays byte-identical). Works under `boot`/`rrepl`/any mode that
steps the CPU, so you can drive with `kbd` in a REPL run and capture at the same
time. (Per-row *screen-base* changes are recorded but not honoured - the screen
is one VBL-time grab; palette splits are the common case and are exact.)

Super Sprint's SELECT TRACK / "PREPARE TO RACE" menu screens render their three
ready-cars blue / yellow / red via this split (3-4 palette bands);
`reversing/supersprint/` has the split-vs-flat pair. The split is
*visible* but not scanline-stable: the band boundaries jitter ~18 rows frame to
frame (instruction-count tick vs real HBLANK, and the /300 divisor vs ~313 real
lines), so on some frames a boundary cuts through the top cars. The on-track
race is flat (zero `$ffff8240` writes while racing).

```
$env:ATARI_FRAME_DIR="frames"; $env:ATARI_FRAME_EVERY="2"
#   ... rrepl / boot run, injecting kbd input ...
python tools/frames_to_video.py frames --out race.mp4 --fps 24 --scale 3
```

`frames_to_video.py` decodes each dump with the same planar logic as
`screendump.py` (applying each scanline's own captured palette), writes scaled
PNGs, and runs ffmpeg to stitch them (`--no-video` stops at the PNGs). It also
still reads the legacy `[rez][palette:32][screen]` layout - told apart purely by
total length (38801 vs 32033). Mid-`Setpalette` frames can come out momentarily
wrong - a brightness filter to drop them is a one-liner (see the script's caller
in git history).

The capture reads the shifter's own video-base bytes (`$FFFF8201`/`$8203`), not
TOS's `_v_bas_ad` at `$44E`: games that set the screen address straight through
the hardware registers (Impossamole, most demos) never touch `$44E`, so a `$44E`
capture would dump a stale/black buffer. TOS keeps the two in sync, so ROM-driven
frames are unaffected.

## F# Interactive: typed scripts against the core (`tools/fsi_drive.fsx`)

`Atari.AtartSt` is a public class, so an `.fsx` can load a snapshot, step, read and write memory and registers with types and no rebuild
(`Program.fs` already has an `#if INTERACTIVE` block for it). `tools/fsi_prep.sh` copies `bin/Debug/net8.0` to `scratchpad/fsi/dll`; the script references that copy, never `bin/`, so
fsi cannot hold `M68000.dll` and fail another session's build at the copy step, and a run stays pinned to one build (re-run after each rebuild). From `M68000/`:

```
sh tools/fsi_prep.sh
DOTNET_gcServer=0 dotnet fsi tools/fsi_drive.fsx --snap <snap> --steps <N> [--disk <.st>] [--out <snap>] [--watch <lo>[-<hi>]] [--poke <addr>=<byte>]
```

Checked on Cadaver (`gameplay_empire.snap` with the one-disk Empire image, 2,000,000 steps): the end snapshot is byte-identical to the REPL's `resume <snap> repl --disk-a <st>` / `s 2000000` / `snap <out>` (five
files over two REPL and three fsi runs, all 1,048,935 bytes), and `--watch 189ca-189cd` over 300,000 steps prints the REPL's 25 `WATCH` lines (the same steps, writer PC `$01529c`, values `$1e` down to `$06`).
A typed poke of the VBL second sub-counter to 1 made the game's own interrupt carry into the seconds byte, as expected.

- **Set `DOTNET_gcServer=0`.** `fsi.runtimeconfig.json` of both installed SDKs (8.0.402 and 10.0.303) sets `System.GC.Server: true`; the core allocates per step, and fsi measured 344 to 352 ms per million steps
  against about 240 for `dotnet exec`, and 207 to 257 with workstation GC. Tiered-JIT switches did not help. Noise on a loaded machine is about +-20%: use interleaved runs.
- Startup is about 1.7 s for a no-op script (fsi itself, not the core: construct plus `LoadState` is 15 ms). Use fsi for scripts with logic, not for one `s <n>` the REPL does in a second.
- The core prints a line per instruction unless `Trace.enabled <- false` (`ATARI_NOTRACE`'s switch) and `Console.SetOut(IO.TextWriter.Null)`; its `--- state loaded/saved ---` lines go to stderr and cannot be silenced.
- **Memory callbacks:** `mmu.AddHook` (section "Memory hooks" below) calls an F# function on every read or write overlapping a range, with the PC, step, width, value and source, so a script can
  read arbitrary typed state at the hit (registers, the stack, other memory, through `PeekXxx`). `fsi_drive.fsx --watch` still uses `MMU.SetWatch` (hook id 0, the REPL's `watch`) and captures its `WATCH` lines from stderr:
  one line per CPU write whose bytes overlap the range and one `DMA read sector` line per FDC sector that lands in it. Polling reads after each `Step()` instead costs about 1.1 s per million steps for four bytes and sees value changes only.
- A resume that writes an end snapshot is only possible through the REPL or `SaveState` here: the raw `<N> resume <snap>` argv runs and exits without saving. `run.ps1`'s `rrepl` and `snap` are aliases, not argv.
- The ROM path is cwd-relative (`AtartSt("TOS100UK.IMG")` from `M68000/`); a snapshot does not name its disk image, so pass the same `--disk` the snapshot was taken with (the sectors the run wrote are in the snapshot: see "Snapshot / preview fidelity").
- Not checked: a `Release` build (the `Debug` one is already built with `Optimize=true`, see "Build and run"), a second game's snapshot, a hook on a field that is rewritten with the same value. The core is the Atari ST only: the arcade games (Final Fight, Crude Buster) run under MAME and
  are scripted in Lua (`reversing/finalfight/README.md`, "Harness facts").

## Memory hooks and the `stserver` process

The stdin REPL is a fragile interface for an agent: an alias passed as argv falls through to a
disk-less cold boot, a forgotten `ATARI_NOTRACE` writes gigabytes, a `resume` without `--disk-a` runs
with no disk, zsh does not word-split a variable of REPL tokens, and an unrecognised line silently ends
the session (`runRepl`'s `| _ -> ()`). Its `watch` is one write-only range. Two pieces replace that
for scripted work: memory hooks in the core (`MMU.fs`), and `stserver`, a long-lived JSON-RPC and MCP
process around one `AtartSt` (`server/`). The REPL and `fsi_drive.fsx` keep working unchanged.

### Core: `MMU` memory hooks

```fsharp
type AccessSource = Cpu = 0 | Dma = 1 | Host = 2
[<Struct>] type MemAccess =
    { Address: uint32; Width: int; Value: uint32; IsWrite: bool
      Pc: int; Step: uint64; Source: AccessSource }
type MemHook = { Id: int; Lo: uint32; Hi: uint32; OnRead: bool; OnWrite: bool; Fire: MemAccess -> unit }

mmu.AddHook h          // any number at once; Lo..Hi inclusive; replaces a hook with the same Id
mmu.RemoveHook id; mmu.ClearHooks()
mmu.HostAccess <- true // around a debugger write: its events report Source = Host
mmu.PeekByte/PeekWord/PeekLong   // ReadXxx without the read hooks (device side effects still happen)
st.Capture() / st.Restore(c)     // in-memory checkpoint (Cpu, step count, MmuSnapshot); reusable
st.Cpu <- { st.Cpu with D0 = 5 } // the Cpu property is settable
```

- **An access matches when its bytes overlap the range**: `[Address, Address+Width) ∩ [Lo, Hi]`. A
  word write at `$189cc` is seen by a hook on `$189cd`, the same rule as the REPL `watch`.
- **Granularity is the bus access the MMU sees.** `WriteLong` is two `WriteWord` events; a long read is
  one event of width 4. A word write to the YM2149 or the MFP is delegated byte by byte and reports as
  a word event plus one or two byte events.
- **`Pc` and `Step`** are `WatchPc`/`WatchStep`, which `AtartSt.Step` sets before each instruction (the
  step number is post-increment, as in `WATCH` lines). An interrupt or exception frame push is
  attributed to the PC of the instruction that was about to run. A DMA event carries the previous
  instruction's PC, which means nothing.
- **Reads include instruction fetches.** Opcode and extension-word fetches and the decoder's look-ahead
  (`TryFastForwardTbdrPoll` reads PC+2 and PC+4) go through `ReadWord`, so a read hook on code sees them.
  Use read hooks on data. Separating fetch from data would need a function-code argument on every read.
- **FDC DMA** sector reads (`tryReadSector`, which stores straight into `ram`) fire write hooks with
  `Source = Dma`, one byte event each. The REPL `watch` skips those and keeps its one `DMA read sector`
  line per sector (`checkWatchDma`).
- **The callback is the predicate**: it runs before a write lands and after a read completes, and does
  whatever filtering it likes. It must not read memory through `ReadXxx` (that re-enters the read hooks);
  use `PeekXxx`.
- **Not hooked:** the flat test bus (`selftest`) and the bulk copies in `RestoreRam`/`LoadState`.
- **REPL `watch`** is hook id 0 printing the unchanged `WATCH:` line for CPU and host writes, so one REPL watch at a time,
  as before, and `MMU.SetWatch`/`ClearWatch` keep their signatures. REPL `w` sets `HostAccess` around its
  write.
- **Hot path.** The hooks sit in two arrays, `null` when empty. Writes replaced `checkWatch`'s option
  match with one null test. Unhooked RAM reads pay one more field test before the existing
  `ramDirect` fast path and no call; device reads and any read with hooks set go through the
  non-inlined `PeekXxx` body. Interleaved A/B with no hooks set against the pre-change build (five pairs each, order alternated
  per pair, load average 6.6 to 11.2 on the Xeon Mac): 30M diskless boot, base median 6.94 s (min
  6.83), hooked 6.97 s (min 6.86), pair gaps +4.0, +5.2, +1.6, +0.3 and -1.2% (the two largest under
  the highest load); Cadaver `gameplay_empire.snap` 10M-step resume, base median 2.29 s (min 2.26),
  hooked 2.29 s (min 2.23). Both are within noise: no measurable cost. The pre-registered falsifier,
  hooked slower by more than 3% in every pair, was not met, and every boot pair's end snapshots were
  byte-identical.

### `stserver` (`server/StServer.fsproj`)

A separate executable referencing `M68000.fsproj` (the entry point must be in the last compiled file,
so it cannot live inside `Program.fs`'s `Main`), building to `server/bin/Debug/net8.0/stserver.dll`.
Build it with `dotnet build -c Debug server/StServer.fsproj`, which also builds the core into
`bin/`, so the same shared-`bin/` rule applies (`sessions/README.md`). It reads newline-delimited
JSON-RPC 2.0 from stdin and writes only responses to stdout. Core diagnostics, `Diag.result` and the
`--- state loaded/saved ---` lines go to stderr. Trace is off with no environment variable. The ROM is
`--rom <path>`, else `TOS100UK.IMG` found by walking up from the cwd and then from the server's own
directory, so it runs from any cwd.

The same process answers MCP (`initialize`, `tools/list` built from the method table with JSON schemas,
`tools/call` returning the result JSON as text, `isError` on failure). The repo's `.mcp.json`
registers it as `stserver` (`dotnet exec M68000/server/bin/Debug/net8.0/stserver.dll` from the repo
root), so a Claude session in a checkout where it has been built can call the methods as tools; Claude
Code asks once to approve a project MCP server. Build it first: in a fresh checkout the DLL is missing
and the server fails to start.

Addresses and values are JSON integers (decimal) or hex strings (`"$189ca"`, `"0x189ca"`, `"189ca"`);
results give them as `"$hex"`.

| method | params | result |
|---|---|---|
| `load` | `snapshot`, `disk` (required key: a path, or `null` for a disk-less snapshot), `rom?` | `pc`, `step` |
| `boot` | `disk` (required key), `rom?` | cold reset |
| `save` | `path` | |
| `regs` / `set_reg` | / `name`, `value` | D0-A7, USP, SSP, PC, SR, step, stopped, halted |
| `peek` | `addr`, `width` 1/2/4, `count?` | values; no read hooks |
| `read` | `addr`, `len` | hex string; no read hooks |
| `poke` | `addr`, `width` 1/2/4, `value` | write hooks fire with `source: "host"` |
| `step` | `n` | `pc`, `step`, `watch_hits` (new events per watch id); stops nothing |
| `run` | `max_steps` (required), `until_pc?`, `count?` | `reason` (`breakpoint`, `watch`, `until`, `halted`, `max_steps`, `error`), `steps`, `watch_hits` |
| `bp_set` / `bp_clear` / `bp_list` | `addrs` | breakpoints `run` stops at (it steps at least once first, like `bp`) |
| `watch_add` | `lo`, `hi?`, `kind` `r`/`w`/`rw` (default `w`), `stop?`, `pc_lo?`, `pc_hi?`, `value?`, `mask?`, `source?` (`cpu`/`dma`/`host`), `max_events?` (default 10000) | `id` |
| `watch_remove` / `watch_list` / `watch_events` | `id` / / `id?`, `clear?` (default true) | events `{step, pc, addr, width, value, write, source}`; overflow counted in `dropped` |
| `hits` | `steps`, `addrs` | count, first and last step per address |
| `fork` / `restore` / `drop` | / `id` / `id` | in-memory checkpoint (`AtartSt.Capture`); a fork restores any number of times |
| `render` | `path` | PNG at native resolution: shifter base `$ff8201/3`, `$ff8260`, palette (as `snap_render.py`) |
| `kbd` / `mouse` / `disk` | `bytes` / `action` `move`+`dx`/`dy` or `down`/`up`+`button` / `path` or `null` | as the REPL |
| `shutdown` | | ends the process |

A watch with `stop: true` ends `run` after the instruction that made the matching access. Watches
and breakpoints persist across `load`, `restore` and `step`. An unknown method, a bad parameter or an
exception in the core comes back as a JSON-RPC error and the process stays up. This makes the REPL
pitfalls above impossible: there is no argv to mistype beyond `--rom`, `load` refuses a call without
the `disk` key, nothing traces, values are JSON, and `run` always has a step budget and names the
bound that ended it.

Checked (`server/smoke.py <stserver.dll> <gameplay_empire.snap> <one-disk Empire .st> <outdir>`, all
pass): from Cadaver's `gameplay_empire.snap`, `watch_add 189ca-189cd w` and `step 300000` give 25
events at the same steps as the REPL's `watch 189ca 4` (writer PC `$01529c`, values `$1e` down to
`$06`, first at step 53,304,004). The server's end snapshot is byte-identical to the pre-change REPL's
`s 300000` / `snap`, and a `fork`/`restore` replay gives an identical end snapshot and event list. A
`poke` reports `source: "host"`; a stop watch on the odd byte `$189cd` stops `run` on the first byte
write there, and a word write at `$189cc` reaches a watch on `$189cd` alone. `load` without `disk` is refused, a malformed line is answered and the server stays up.
The MCP handshake and `tools/list` (25 tools) work, as does `tools/call` for `boot`, `run` and `peek`.
The REPL `watch 189ca 4` output is identical before and after the change (25 lines).

## MAME as a second oracle for the ST core (`tools/mame_st/`)

MAME 0.289's `st_uk` driver boots TOS 1.00 UK: `mame -listroms st_uk` wants `tos100uk.bin` (196,608 bytes, CRC `1a586c64`), which `TOS100UK.IMG` equals, plus the IKBD ROM (`keyboard.u1`). The zips are in `~/GitHub/mame/roms`
(`MAMEST_ROMS` overrides), not `~/mame-roms`. It is a second opinion on device behaviour and interrupt flow, **not** a timing oracle (the F# core has no cycle counting) and it cannot load an F# snapshot (a transplant of RAM and CPU
registers at the idle desktop cold-rebooted TOS within a frame; a working one would also need the MFP, shifter, YM, ACIA/IKBD and FDC registers). Real Hatari (`tools/hatari_trace.py`) remains the OS-trace oracle.

```
sh tools/mame_st/mamerun.sh $PWD/scratchpad/mame_st/out_b $PWD/tools/mame_st/boot.lua     # diskless boot, dumps RAM/screen/palette 300 frames after the desktop (about 33 s; frame 3246)
printf 's 5999000\nsnap %s/scratchpad/mame_st/f6m.snap\nq\n' $PWD | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll 1000 repl
.venv/bin/python tools/mame_st/cmp_state.py scratchpad/mame_st/f6m.snap scratchpad/mame_st/out_b 3246
sh tools/mame_st/mamerun.sh $PWD/scratchpad/mame_st/out_t $PWD/tools/mame_st/trace.lua    # every executed PC from reset (debugger `trace`, `noloop`, `curpc`; call `traceflush` before exit)
.venv/bin/python tools/mame_st/cmp_trace.py <pc.trace> <ATARI_TRACE_EVENTS_ALL .evt> ...   # loop-reduced comparison, see its header
```

Idle desktop (F# at 6.0M steps, MAME at frame 3246): screen RAM 32,000 of 32,000 bytes (cursor included), palette 16 of 16 (`& $777`), `phystop`, `membot`, `memtop`, `_v_bas_ad`, `_drvbits` and the other OS variables equal,
`$600-$7ff` 512 of 512, vectors 1,019 of 1,024, sysvars 505 of 512, all 1 MB 1,047,943 of 1,048,576 (reproduced from `tools/mame_st/`). The differences: the 621 RAM bytes sit in about 47 stack and AES clusters (different boot histories,
saved SRs differ in the IPL byte), `_frclock`/`_hz_200` (timing), `_nflops` (MAME 1, F# 2), and `$0-$7` (MAME shows the ROM vectors there; **F# has no ROM shadow at 0**).
Instruction trace from reset: the identical prefix is only 31 instructions (the Timer B calibration poll at `$fc0d06` loops 6,557 times in MAME and falls through in F#: the intended `TryFastForwardTbdrPoll`), then 216,462
instructions match exactly to the end of MAME's 244,279-instruction trace; no CPU-semantics difference showed. A first-touch comparison to MAME frame 3100 aligns 10,852 of about 11,000 distinct PCs with 11 divergences.

Three F# model gaps found (each from the MAME log or trace plus the F# source; none confirmed by an F# patch or a real program):

1. **No HBL interrupt.** TOS's level-2 handler (`$fc061e`, vector `$68`) runs only in MAME and does `ori.w #$300,2(A7)`, so the first HBL at IPL 0 leaves the machine at IPL 3 (MAME logs IRQ 2 three times in 3,100 frames); `MMU.PendingInterruptLevel` returns only
   0, 4 or 6. F# runs the desktop at SR `$2000` where MAME runs `$2300`. A program that reads SR's IPL or installs a `$68` handler can differ.
2. **Coarse FDC.** MAME's WD1772 never raises INTRQ for a diskless Type I command, so TOS's `flop_cmd` loop (`$fc1bd4`-`$fc1bf2`) times out and retries and the desktop takes 7 times the emulated time (frame 2946 against about 5.4M F# steps);
   F# has no per-command state machine, so its success path (`read_le_word`, `$fc15b4`-`$fc1610`) runs instead.
3. **No keyboard power-up traffic.** MAME runs the HD6301 IKBD firmware, which answers TOS's init and fires one ACIA interrupt (`acia_isr`, `$fc281c`, about 59 instructions); F# never takes it in 7M steps.

One divergence is unexplained: at `$fc03b6` (`move #$2300,SR`) MAME takes the pending Timer C interrupt at once and F# one instruction later (a step-clock effect, unverified). Gotchas: `-debugscript` does not run under `-debugger none` (use `machine.debugger:command(...)`),
the `trace` action's `pc` is prefetch-advanced (use `curpc`), and a diskless MAME boot spends minutes in FDC timeouts, so use it for questions about one interrupt or device read, not whole-game runs.

## Other tools

Check this list before writing a one-off helper; each of these has been rewritten ad hoc at
least once by a session that did not know it existed.

| tool | use |
|---|---|
| `server/` (`stserver.dll`) | long-lived JSON-RPC / MCP process around one `AtartSt`: load with a required disk, step, run with a budget, breakpoints, typed peek/poke, multi-range read/write watches with writer PC and source, in-memory fork/restore, PNG render (section "Memory hooks and the `stserver` process"; `server/smoke.py` is its check) |
| `tools/fsi_drive.fsx`, `tools/fsi_prep.sh` | F# Interactive driver: load a snapshot, run N steps, optionally `--watch` a range (the REPL's WATCH lines) or `--poke` a byte, save an end snapshot; a template for typed per-step scripts (section "F# Interactive" above; needs `DOTNET_gcServer=0`) |
| `tools/mame_st/` | MAME `st_uk` as a second oracle for the F# core: diskless boot dump and state compare, executed-PC trace and loop-reduced comparison (section "MAME as a second oracle" above) |
| `reversing/finalfight/py/gdbstub/` | MAME's gdbstub for gdb, a Python RSP client and Ghidra's Debugger (headless), with a 600-stop gate against the Lua harness (its README) |
| `tools/snap_render.py snap png` | the live screen of a snapshot as a PNG (base, rez and palette from the shifter registers, so double-buffered games come out right) |
| `tools/sprite_array_export.py` | game-agnostic struct-driven sprite/object-array batch export (`--base`/`--array-ptr-field` + `--stride --count --w-off --h-off --ptr-off`) or fixed-stride sheet export (`--sequence BASE STRIDE COUNT W H`) or a one-off region (`--region ADDR W H`); st-interleaved 4bpp decode, `--palette` for a live 16-word `$0RGB` table (cadaver `graphics.md` §3/§5) |
| `tools/disassemble.py` | 68000 disassembler; `--snap` for a loaded program, `--rom img --base <hex>` for a relocated image, `--jumptable` |
| `tools/prg2img.py prg img <text>` | relocate a GEMDOS executable to its runtime TEXT address (TEXT+DATA+zeroed BSS), so image addresses equal trace/snapshot addresses |
| `tools/ghidra/DecompileAll.java` | headless Ghidra decompile of a `prg2img` image to one C file, with `.sym` names applied; for compiled-C programs (usage in the file header) |
| `tools/trace_cfg.py` | call graph / CFG / block map from an `ATARI_TRACE_EVENTS` log (above) |
| `tools/add_file_to_disk.py` | put a file on a FAT12 image, `--auto` into `\AUTO\`; `--from-disk NAME --remove NAME...` turns a desktop-launched game into a headless-booting disk |
| `tools/make_blank_disk.py`, `tools/make_test_prg.py` | blank images, test programs |
| `tools/extract_disk.py image.st outdir` | dump every file of a FAT12 `.ST` image, recursing into directories (the reverse of `add_file_to_disk.py`) |
| `tools/gfxview.py`, `tools/screendump.py` | RAM graphics explorer; raw screen-dump-to-PNG. `gfxview.py`'s `load_ram(path)` / `load_video_regs(path)` / `snapshot_regs(path)` already parse a `.snap`'s header (registers, RAM, the live shifter base/resolution/palette) — import them instead of hand-deriving the binary layout (`A68S` magic, 19 regs, then `cpu.CCR` as an **int16**, not a byte, which desyncs every field after it if assumed otherwise; cadaver mechanics.md section 5) |
| `tools/hatari_trace.py` | headless real Hatari on the same ROM (a CPU/OS-trace oracle, not a video one); Windows `hatari.exe` only, on the Mac see "macOS" |
| `tools/pm_fsm_diff.py` | game-agnostic `callcap` differential-test harness (`Harness`/`State`/`run_corpus`); a corpus script's first argument (other than `reuse`) runs only the states whose name contains it. `callcap` runs the routine with interrupts masked, so a routine that waits on an interrupt-cleared flag never returns ("Loop detected"): for PowerMonger's sound calls (`$1ba3e` → `$1ae36`) poke the busy byte `$2c993` to 0 in the state first |
| `tools/capture_hits.py` | corpus capture for a callcap gate: from a start snapshot, stop at chosen natural hits of a routine (`bpc`), snapshot each (+ `.ram`) and write the entry registers and return address to `<name>.json` (usage in the header) |
| `tools/rdis.py [--rom img] [--base <hex>] <lo> <hi> <root>...` | recursive-descent lister: follows branches from the roots, resolves `move.w N(PC,Dn.w) / jmp M(PC,D1.w)` word-offset tables (signed), marks data gaps. Use it instead of `--all` for a handler that interleaves jump tables and animation data (`--all` loses sync there: Final Fight's `$389b8` was not an instruction line in the linear listing). **It does not follow longword state tables** (`jsr (A0)` after `movea.l 0(A0,D0.w),A0`): handlers behind them are not listed, so it is no basis for a "no caller / no writer" claim (Crudebuster: 67 of 94 callers missed); scan the raw image or the `--all` linear listing |
| `tools/disassemble.py --snap <snap> --all <lo> <hi>` | whole-image listing that carries on past jump-table stops; grep it for callers and field writers (`,44(A[0-7])$`) before trusting any "who writes X" claim |
| `tools/find_ram_callers.py <snap> <addr>...` | whole-RAM scan for direct `bsr`/`bcc`/`jsr`/`jmp` instructions whose own decoded text names one of the given target addresses (`disassemble.py --callers` only covers the TOS ROM) |
| `tools/find_field_writers.py <snap> "<N(An) or $addr>" [--width N] [--all]` | whole-RAM census of the decoded instructions that write (with `--all`, also read) a field: operands are matched by the bytes they cover (a `move.l` to `2516(A5)` writes `2518(A5)`; `2518(A5)` no longer matches `12518(A5)`), split by instruction boundary from a linear sweep, plus indexed writes through the same base and `lea`/`pea` of addresses just below the field (block-clear bases). It cannot see writes through computed pointers, code outside the image or DMA: a clean result is a lead, `watch` is the check (header) |
| `tools/find_literal_ptr.py <snap> <addr>` | whole-RAM raw-bytes scan for an address appearing as **data** (4-byte or 2-byte, any alignment) — finds abs-long `jsr`/jump-table references `find_ram_callers.py` can't see, since those encode the target as a literal operand rather than a PC-relative displacement; doesn't catch a displacement-style jump table (use `find_jump_table_hit.py` for that) (cadaver mechanics.md section 14) |
| `tools/find_jump_table_hit.py <snap> <addr>` | does any `table_base + entry` jump table (this game's own dispatch idiom, cadaver mechanics.md section 9) resolve to a target address — collects every literal absolute address any instruction names as a candidate table base, then checks each one's entries for `target - base` (cadaver mechanics.md section 2) |
| `tools/pm_export.py`, `tools/pm_render_ref.py`, `tools/pm_fsm_ref.py` | PowerMonger: asset export, the Python reference renderer, the from-disassembly entity/AI reconstruction |
| `tools/merge_sym.py <game.sym> <sym.txt>... [addr=name] [--write]` | merge subagent `sym.txt` files into a game's `.sym`, reporting addresses named differently (settle each in the code; `addr=name` overrides); `--write` keeps the target's existing lines and comments and appends the new names |
| `reversing/populous/py/popdrive.py` | Populous: plan exact mouse clicks (icons, land corners, minimap) from a snapshot; a worked example of driving a game through its own hit-test code |
| `reversing/powermonger/py/` | PowerMonger working scripts: build any of the 144 lands, capture frame runs, score the port pixel for pixel, `hits` census runs (its README lists them) |

The REPL's `hits <steps> <addr>...` counts how often each address runs over a stretch (first and
last step too): the quick answer to "which of these routines fire at all" before any `bp`. `hits`, `bp`
and `bpc` count instruction starts: an interrupt taken at a counted address and its RTE back to it do not
count it twice, and a STOPped or halted CPU idling at an address does not count at all. They, and `until`,
compare 24-bit addresses, so a PC with junk upper bits (TOS 1.00's handlers run at `$04fc0a1a`: its vectors
carry the vector number in the top byte) matches `bp fc0a1a`. `m` reads the I/O page ($ff8000 up) without
side effects (the ACIA data register is not popped, an FDC status read does not clear INTRQ).

Snapshots (`*.snap`) are session-local working data, keyed to a ROM + opcode-coverage
point - not committed, retake per session.
