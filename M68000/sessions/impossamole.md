# Impossamole: handoff

Updated 2026-09-26 by the session that ended at commit `cad3d3d`.

## Resume point

- Last commit of this workstream: `cad3d3d` (this session's own first commit).
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image, a
  `extracted/` directory with every root-dir file pulled via a one-off FAT12 reader (not committed
  as a script; trivial to redo, see README's BPB table), and snapshots `after_f1.snap` (crack boot
  menu, F1 pressed) → `after_space.snap` (trainer menu skipped) → `after_retry{1,2,3,4}.snap`
  (settling through GEMDOS file loading to the title screen).
- Start from: `scratchpad/impossamole/after_retry3.snap` or `after_retry4.snap` — both sit in the
  title-screen VBL-wait loop at `$1ab90`/`$1aba0` described below. **Must be resumed with
  `--disk-a "impossamole cr replicants - emotion cr replicants.st"` or every floppy read silently
  fails** (see README's "Open item" trap).
- Uncommitted work left behind: none beyond the scratchpad snapshots (gitignored, reproducible from
  the README's exact command sequence).

## Proven so far

- Disk boots (executable boot sector, checksum `$1234`) straight into a Replicants crack menu, no
  `\AUTO\`, no Pexec until past the trainer menu.
- F1 (scancode `$3B`/`$BB`, two separate `kbd` calls with a real step gap between, per the
  established keyboard discipline) selects IMPOSSAMOLE+++ over the crack's F2 "E-Motion" option.
  Reproduced via REPL script, screenshot in `reversing/impossamole/trainer_menu.png`.
- Any other key (tried Space) skips the "PRESS 'T' FOR TRAINER" prompt; loader then switches to
  real GEMDOS `Fopen`/`Fread`/`Fclose` (funcs `$3d`/`$3f`/`$3e`) and reaches the real game title
  screen ~20-30M steps later. Screenshot in `reversing/impossamole/title_logo.png` — correct
  IMPOSSAMOLE logo, hero sprite, Gremlin/Core Design publisher logos. No instruction wall, no crash.

## Open, in priority order

1. **Title screen doesn't advance past a `$1ab90` wait loop that reads `$1a2e9` byte, which stays
   `$00` across 30M steps (two snapshots 30M apart both show it static).** Find `$1a2e9`'s real
   writer before assuming it's VBL-driven (`find_ram_callers.py`, or a `watch $1a2e9` over a fresh
   run from `after_retry3.snap`, `--disk-a` attached). If it *is* VBL-fed, check whether the game's
   VBL handler is installed yet at this point, and whether this emulator's VBL delivery reaches it
   (`ATARI_TRACE_OS`/a VBL-specific trace, if one exists, over the same run). `README.md`'s "Open
   item" section has the exact disassembly and the two addresses (`$1abc2`/`$1abdc`) that look like
   a handshake with something else, worth reading first.
2. Once past the title: reach the world-select screen (`SELECT44.DAT` is presumably its data) and
   into actual isometric gameplay for one of the 5 worlds (Bermuda / Iceland / Jungle / Mines /
   Orient — named by the `BRMUDA/ICELND/JUNGLE/MINES/ORIENT` `.DAT` pairs).
3. Classify the main game binary once reached via GEMDOS Pexec (watch for the `Pexec` trace line
   the crack loader should eventually issue) — likely hand-written 68000 asm given the crack/trainer
   wrapper, but confirm via the LINK-frame-count heuristic (§0 of the reversing skill) rather than
   assuming.

## Known traps

- `resume <snap> repl` does not reattach a disk image — `--disk-a` must be passed again on every
  resume for a disk-booted game, or floppy reads silently return "no data" (looks exactly like a
  real protection/geometry failure). Cost this session a wrong "sector 11 unreadable" diagnosis
  before catching the missing flag via `ATARI_TRACE_FDC=1` + a direct `LoadDiskA` code read. Not
  yet promoted to CLAUDE.md — do that if a second workstream hits the same trap.
- The disk's BPB claims `nFATs=1`, but the real root directory only resolves assuming 2 FAT copies
  are physically present — a manual FAT12 reader (or a generic PC-side tool trusting the BPB
  literally) will parse the wrong sectors as the root directory. TOS's own GEMDOS driver reads it
  correctly (confirmed live: `Rwabs(recno=11)` for `Fopen("DISK.ID")` matches the 2-FAT offset,
  i.e. real hardware/TOS doesn't trust this BPB field literally either) — this is presumably a
  known Replicants/scene mastering quirk, not a bug worth chasing further.

## Next session

Start at `scratchpad/impossamole/after_retry3.snap`, resumed with `--disk-a` attached. First
disassemble the callers/writers of `$1a2e9` (open item 1) before running more raw steps — burning
step budget on the same wait loop without knowing what it's actually gated on is how the disk-image
trap above ate time this session. Once past the title screen, drive to the world-select screen and
take a screenshot before going further, so the milestone ladder (title → select → gameplay) has
proof at each rung the way every prior game's README does.
