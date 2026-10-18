# Lemmings: handoff

Updated 2026-10-18 by the first working session (boot to gameplay, lemming array found).

## Resume point

- Last commit of this workstream: the one that adds `reversing/lemmings/drive.txt` and `mechanics.md`
  (`git log --oneline -- M68000/reversing/lemmings`). The emulator fix is `8b6c474`.
- Working data: `scratchpad/lemmings/`: `lemmings.st`, `files/` (extracted), `b300000000.snap` (cold boot,
  300M steps, in the cracktro), `lvl1_a.snap` (level 1 gameplay, all 10 lemmings out, PC `$a61c`),
  `lvl1.asm` (whole-image listing `$2000`-`$27000` of `lvl1_a.snap`), `f0..f3.snap` (four snapshots 24,000
  steps apart). Rebuild any of it with `reversing/lemmings/drive.txt` (recipe in its header).
- Disk: `~/Library/CloudStorage/Dropbox/Daves/ST games/Lemmings (1990)(Psygnosis)[cr BBC][a].st`,
  sha256 `118f33d9...a1d` (full in the README).
- Uncommitted work left behind: none from this workstream (`Cadaver/` untracked is another session's).

## Focus

Lemming behaviour first: the per-lemming record, the skill/state machine, the terrain collision it reads,
the per-frame update order. Graphics, level format and sound only as far as behaviour needs them.

## Proven so far

- Boot to gameplay, deterministic: `drive.txt` run twice from `b300000000.snap`, `cmp` identical
  (`README.md` "Boot to gameplay"). Needs a NOP of the cracktro's ACIA poll at `$a438` and `--disk-a` on
  every `resume`.
- Two emulator walls fixed and committed behind the net (VR vector base; line-resolution video address
  counter): `README.md` "What it needed from the emulator".
- Lemming array: `$23484`, stride `$2c`, 10 of 10 records in level 1 (`mechanics.md`, "The lemming array").
- The code is already depacked in RAM at `$2000`-`$27000` once the menu is up, so the `Ice!` depacker is
  not needed to read it.

## Open, in priority order

1. Name the state bits. `$7802` dispatches on the bits of the long at record `+14` (17 bit tests, handler
   table in `mechanics.md`). Read each handler's body to its first branch, find which bit each skill icon
   click sets (watch `+14` of one record through a click), then `callcap` one handler per bit from a
   snapshot with a lemming holding it (`capture_hits.py` for natural hits of `$7802`'s handlers).
2. Terrain collision: the handlers read a level bitmap; find the pixel-test routine (`$80ea` and the
   subroutines the handlers call), the bitmap's address and format (`$41800`/`$43800` buffers are
   written during level build), and prove walk/fall/dig/bash/mine/build against it.
3. Fields: +10 (a per-tick counter, probably the animation frame), +21 (countdown, bomber?), +36, +38
   (`$1af30`), +42 (`$21c`). Name from the handlers that write them.
4. Tick rate: how often `$7802` runs per VBL (`hits`), and what `72(A5)`/`58(A5)` (release rate) do.
5. Level format (`LEVEL000-024`, `LEVELDAT`, `GROUND*`, `OBJECTS*`) as far as the entrance table `136(A5)`
   and terrain need. The `20 13 00 10` headers are probably a compressed level container; unread.

## Known traps

- `ATARI_NOTRACE=1` on every raw `dotnet exec`; run from `M68000/`. `resume <snap> repl --disk-a <st>`.
- `mouse down l` / `mouse up l` (the side argument is required). The pointer is the game's own at
  `$272f6`/`$272f8`, clamped at 0.
- Colours in `snap_render.py` are wrong on menu and briefing screens (per-scanline Timer B palette
  splits): read the logic from RAM, not from those renders.
- The emulator's video counter is line-resolution only; a game that needs sub-line beam position
  would still loop. Timer B itself is scanline-accurate (`HblTick`).
- Do not poll a value this game changes with `snap` over a few frames and call it "stuck": it runs its
  update on a tick, and the minimap/dispatch loops skip `+24 != 0` records.

## Next session

`/resume lemmings`. Start from `lvl1_a.snap`: item 1. Watch `+14` of the first lemming while selecting a
skill and clicking it (the skill panel is at the bottom of the screen; find its pointer hit-test the way
the menu's was found), and name the dispatch bits from that.
