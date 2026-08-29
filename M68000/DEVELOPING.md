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

## Other tools

See the `atari-st-emulator-efficiency-tooling` memory for the full list.
`tools/disassemble.py`, `tools/hatari_trace.py` (headless real Hatari on the same
ROM), `tools/screendump.py`, `tools/make_blank_disk.py`. Snapshots (`*.snap`) are
session-local working data, keyed to a ROM + opcode-coverage point - not
committed, retake per session.
