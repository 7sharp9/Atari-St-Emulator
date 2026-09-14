---
name: reverse-engineer-st-game
description: Workflow for reverse-engineering a commercial Atari ST game against this repo's F# 68000 emulator and tools/, boot it, drive it to gameplay, map control flow and graphics, and (if needed) reverse game logic via the snapshot+callcap differential-test harness. Use when asked to analyse, reverse-engineer, or "look at" a new Atari ST disk image/game, or to document or port its mechanics/graphics.
---

# Reverse-engineering an Atari ST game

Grounded in three prior subjects at `M68000/reversing/{a_013,supersprint,powermonger}/`. Each produced the same shape of artifact: a boot-to-gameplay narrative, a `.sym` file, callgraph/cfg dot+svg, screenshots at milestones, and topic docs (`mechanics.md`/`graphics.md`/`ai.md`/`economy.md` as needed). That shape is the deliverable, reproduce it for a new game rather than inventing a new format.

## Scope: what actually transfers

This skill is Atari ST / 68000 specific. It leans on this repo's F# 68000 core, the real Hatari binary as an oracle, and `tools/` whose opcode tables and graphics decoders assume ST hardware (planar bitmaps, `$ffff8240` palette, GEMDOS/XBIOS traps). Full reuse: another ST game. Partial reuse: another 68000 platform (Amiga/Genesis/Mac), the CPU core and disassembler technique transfer, the memory map/OS calls/graphics formats don't. For anything outside 68000 entirely, only the *method* below (milestone ladder, snapshot+callcap differential testing, README template, gate discipline) transfers, the tool layer would need rebuilding from scratch.

## 0. Setup

- Get the disk image legally; do not commit it or the cracked archive. Record sha256 + size in the README (`supersprint/README.md` is the template).
- `unzip "<game>.zip"` → a `.ST` FAT12 image. `./run.ps1 -DiskA "<game>.ST" boot <N>` (or `--disk-a` on a bare `dotnet exec`).
- `taskkill //F //IM dotnet.exe` before any run, orphaned instances make resume look non-deterministic.
- Create `M68000/reversing/<game>/` now.

## 1. Trace the boot, find the walls

`ATARI_NOTRACE=1 ATARI_TRACE_GEMDOS=1 ATARI_TRACE_OS=1 dotnet exec bin/Debug/net8.0/M68000.dll <N> --disk-a "<game>.ST"` narrates `Pexec`/`Fopen`/`Fread`/`Setscreen`, free ground truth for what the game loads and when. Paste the summary into the README.

Any unimplemented opcode/EA mode is an instruction wall. Fix it through the shared EA decoder (`x.ResolveEa`/`x.ReadEa`/`x.WriteEa`), the pattern the 45th–56th passes used for every prior game, new titles mostly hit missing addressing modes on existing instructions, not new hardware behaviour. Each fix is its own commit behind the regression net (§6); non-negotiable.

## 2. Drive it to gameplay

Progress attract → menu → gameplay by injecting input, not by guessing: REPL `kbd <hex>…` / `mouse move|down|up`, or `ATARI_KEY_INPUT`. Read the game's own IKBD handler first (disassemble around the vector it installs, typically `$118`/`$120`) to learn its packet format and key mapping, then script the exact byte sequence, Super Sprint's README section "Driving it into a race" is the model.

`screendump.py --rez <r> --screen <hex> --palette f --out x.png` at each milestone (title, menu, gameplay). Keep every screenshot that proves a milestone; drop exploratory ones before committing.

## 3. Map control flow

Once a step range covers the behaviour of interest:
```
ATARI_TRACE_EVENTS=<game>_events.bin ATARI_TRACE_GEMDOS=1 dotnet exec bin/Debug/net8.0/M68000.dll <N> --disk-a "<game>.ST"
python tools/trace_cfg.py <game>_events.bin --steps <lo> <hi> --range <lo> <hi> --names <game>.sym \
    --callgraph callgraph.dot --blocks blocks.txt
python tools/trace_cfg.py <game>_events.bin --steps <lo> <hi> --range <lo> <hi> --names <game>.sym --cfg cfg.dot
dot -Tsvg callgraph.dot -o callgraph.svg
dot -Gnslimit=1 -Gmclimit=1 -Tsvg cfg.dot -o cfg.svg
```
Scope `--range` to the program's own text segment (from the `Pexec` basepage decode); for `--cfg`, one dense region at a time, a whole-program CFG is unreadable. Build the `.sym` sidecar (`addr<TAB>name`) incrementally as routines are named; it feeds both `trace_cfg.py --names` and `disassemble.py`.

`disassemble.py --snap <path> <addr>` / `--linear <addr> <n>` reads real instructions at an address of interest. `--callers <addr>` only scans TOS ROM, not the loaded program, grep a `--linear` dump for `jsr $<addr>.l` to find in-program callers.

## 4. Find and decode the graphics

`gfxview.py <snap> --contact ram.png` first, a whole-RAM overview to spot where decoded assets sit. Then `--html` for an interactive per-region viewer (base/width/rows/bpp/palette/zoom) to pin down the actual format (planar/chunky/tiled). `ATARI_GFX_SIDECAR=<path>` during the run records every XBIOS `Setpalette`/`Setscreen` so gfxview can auto-mark candidates. Write findings to `graphics.md`/`gfxview.md`, not just the screenshots.

## 5. Reverse the logic (mechanics/AI), if that's the goal

For "what does routine X actually do", don't read disassembly and guess, build a differential test. `snap` at an anchor point, `detcheck` it first to confirm determinism, then `callcap <addr> [Rn=hex ...]` to run the routine in isolation and get its register delta + full memory diff + trace hash (snapshot-restored after). Write a Python reconstruction of the hypothesis and diff it against `callcap` output over a corpus of states, `tools/pm_fsm_diff.py`'s `Harness`/`State`/`run_corpus` are a game-agnostic differential-test harness; only the reconstruction module (`pm_fsm_ref.py`) is PowerMonger-specific and needs a per-game equivalent. Report a diff count (e.g. "1847/1847") before calling a hypothesis proven, every PowerMonger pass (93rd–99th) gates on this.

## 6. Regression net (every commit that touches the emulator)

1. `./run.ps1 -NoBuild verify 5000000`, PASS (re-run 2–3× on a byte-identical FAIL, that's a build-cache race, not a real failure).
2. `./run.ps1 -NoBuild snap 30000000 after.snap`, `cmp` against a diskless baseline. A diff is a gate *decision*, not an auto-fail, investigate before accepting or reverting.
3. `dotnet build -c Debug` as its own tool call, read it, `&&` never `;`.
4. Full `./run.ps1 selftest tests/680x0`, gate is 0 wrong / 8 skip; the pass total drifts up with coverage, don't gate on it.

Pre-register the falsifier, what result would mean the change is wrong, before running any of this, not after.

## 7. Write the README

Every prior game's README (`M68000/reversing/{a_013,supersprint,powermonger}/README.md`) covers, in this order: what the game is + provenance (publisher/year/cracker, sha256, disk-image file layout); milestones reached and how; "what it needed from the emulator" as a commit table (wall → fix); "how it was run" (exact commands); "how the CFG was built"; "what the artefacts show"; a files table. Match that shape so a later pass, or someone else, can reproduce the run without re-deriving it.

## Known tooling gaps

From repeated friction across passes (not yet built, build the one a pass actually needs, not all speculatively): no call-depth/step prefix or jsr/rts target on the live `-Trace` line; no `.sym` symbolication of that live trace; no REPL breakpoints (`bp`/`bpc`), only `callcap` (call-and-return) and `u <addr>` (run-to-address) exist; no windowed/scoped trace (PC-range or call-subtree only); `trace_cfg.py` only ingests the binary event log, not the text `-Trace` dump.

## Discipline carried over from the CPU-accuracy work

One `watch` region per REPL session, a second concurrent region silently drops events. Transcribe hardware/OS semantics from source (Hatari's `src/*.c`, `M68000PRM.pdf`) rather than recalling them. Stage named files only, never `git add -A`, disk images and cracked archives are copyrighted and must stay untracked.
