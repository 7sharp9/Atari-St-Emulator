# Developing the emulator

Working notes for the ROM-driven debugging loop. The emulator (`M68000/`, F#)
runs the real TOS 1.00 ROM until it hits an unimplemented instruction or a wrong
answer, and each pass closes the next gap.

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
`-Trace` forces it on; `-NoBuild` skips the build. Run `./run.ps1` with no args
for the full subcommand list.

The raw form still works: `dotnet exec bin/Debug/net8.0/M68000.dll <argv>` where
`<argv>` is any of the modes in `Program.fs`'s `main`.

## `ATARI_NOTRACE`

`ATARI_NOTRACE=1` redirects `Console.Out` to a null sink so the ~221 per-step
`printfn` trace sites cost nothing on bulk runs. It no longer silences result
output: REPL replies, `verify` / `selftest` verdicts and snapshot/until status
lines go through `Diag.result` (68k.fs), which is captured before the redirect.
So `ATARI_NOTRACE=1 ... verify` prints its PASS/FAIL, and a `NOTRACE` REPL still
answers `r` / `m`. `watch` / `ATARI_TRACE_GEMDOS` already used stderr and are
unaffected.

## Regression tests: `selftest`

There is no full unit suite. `selftest` runs the
[SingleStepTests / ProcessorTests](https://github.com/SingleStepTests/ProcessorTests)
68000 vectors (`680x0/68000/v1`, one `NAME.json.gz` per opcode, ~8000 randomised
cases each: full initial state -> expected final registers / SR / memory) against
`Cpu.Step`. This is what catches the silent-for-passes class of bug (e.g. the
39th-pass `LSR.L` / `ROR.L` sign-smear, which fails thousands of shift cases the
instant it is written).

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
file that still has a genuine flag/register bug, worst first. An empty digest
means all that is left is the two known structural classes. Non-zero exit if
anything failed.

The three failure classes:
- **`wrong`** - a real flag / register / memory divergence. Fix these.
- **`frame`** - the vectors expect the instruction to fault and push a frame; we
  push the simplified 6-byte frame (not the real 14-byte group-0 one) or do not
  fault. One fix (a real exception frame) clears the whole class.
- **`unimpl`** - `Cpu.Step` threw: opcode / EA-mode not decoded yet (ROM-driven
  scope). Add the mode when a real target needs it.

What it does and does not cover:

- **Modelled:** the low 1 MB of address space, as flat identity-mapped RAM
  (`memConfig = $05`). A case whose PC or listed RAM addresses fall outside
  `[$8, $100000)` is **skipped** - that is most absolute-addressing cases, but
  nearly all register / immediate / near-stack cases run.
- **Real failures it surfaces** (the `wrong` count - fix these):
  - unimplemented opcode / addressing-mode combinations (the `unimpl` count) -
    expected while scope is ROM-driven, add the mode when a target needs it;
  - wrong flag / register / memory results in an implemented instruction.
- **Known harness-side imprecision** (also shows as `fail`, lower priority):
  - no prefetch queue, so `pc` is compared as "next instruction address" -
    right for this interpreter, off by the real prefetch amount for a few
    instruction classes;
  - exception entry uses the project's simplified 6-byte frame, so
    TRAP / CHK / privilege / address-error cases mismatch on the stacked frame
    (the `frame` count).

Baseline (25 shift/logic/move opcodes, Aug 2026): register-operand `.b` / `.l`
shift and rotate forms pass ~100%; `.w` memory forms and the arithmetic/move
families still carry real gaps. Drive the numbers down in future correctness
passes.

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

## Running a program off a disk image

`ATARI_DISK_A=<file.st>` mounts a real `.ST` floppy image in drive A. The FDC
models single- and double-sided images, PSG side/drive select, Type I head
movement (seek/restore/step), the DMA address counter and the `$FF8606` DMA
status register - enough for TOS to read a FAT12 filesystem and `Pexec` a
program. `ATARI_TRACE_FDC=1` logs every FDC register/command write and sector
read to stderr (compare against `tools/hatari_trace.py --trace fdc`).

Build a disk with a program TOS will auto-run at boot:

```
python tools/make_blank_disk.py blank.st                 # empty FAT12 image
python tools/make_test_prg.py TEST.PRG                    # or bring your own .PRG
python tools/add_file_to_disk.py blank.st TEST.PRG --auto --out auto.st
ATARI_DISK_A=auto.st ATARI_TRACE_GEMDOS=1 ATARI_TRACE_EVENTS=run.evt \
  ./run.ps1 -NoBuild snap 12000000 t.snap
python tools/trace_cfg.py run.evt --steps <lo> <hi> --range <tbase> <tend> --cfg prg.dot
```

`M68000/auto_test.st` is the committed ready-to-use image (`blank_80ss.st` +
`\AUTO\TEST.PRG`, the loop-and-Pterm0 program from `make_test_prg.py`). Use
`--steps` to isolate the program's own run - once it terminates, TOS reuses its
TPA addresses for the desktop.

## Other tools

See the `atari-st-emulator-efficiency-tooling` memory for the full list.
`tools/disassemble.py`, `tools/hatari_trace.py` (headless real Hatari on the same
ROM), `tools/screendump.py`, `tools/make_blank_disk.py`,
`tools/add_file_to_disk.py`, `tools/make_test_prg.py`. Snapshots (`*.snap`) are
session-local working data, keyed to a ROM + opcode-coverage point - not
committed, retake per session.
