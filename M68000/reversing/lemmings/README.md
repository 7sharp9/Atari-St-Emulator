# Lemmings (Psygnosis, 1990)

Focus of the first workstream: lemming behaviour (`sessions/lemmings.md`).

## Provenance

`Lemmings (1990)(Psygnosis)[cr BBC][a].st`, 839,680 bytes, sha256
`118f33d900ad089dde85104f3635dc0a483f02944d55502d218de695ccb1a45d`. Source:
`~/Library/CloudStorage/Dropbox/Daves/ST games/`. Not committed; working copy in
`scratchpad/lemmings/lemmings.st`.

## Disk layout

Extracted with `tools/extract_disk.py` into `scratchpad/lemmings/files/`. `\AUTO\LEMMINGS.PRG`
(56,056 B) is the loader. Data files: `CODE` and `MAIN` (`Ice!` packed), `LEVEL000`-`LEVEL024`,
`LEVELDAT`, `LEMMING1`-`3`, `TIM1`-`10`, `GROUND1`-`5`, `OBJECTS1`-`5`, `SPECIAL0`-`3`, `ODDTABLE`,
`INTROPAR`, `ENDSAMPL`, `*.IMG` logos.

## Boot to gameplay

TOS runs `\AUTO\LEMMINGS.PRG` (`Pexec`, nothing read through GEMDOS afterwards). The stages, each
read from the code and checked by running it:

1. **BBC cracktro** (a scroller over a starfield, code at `$a000`-`$bb00`). Its exit test at `$a432` is
   `cmpi.b #$b9,$fc02.w` / `bne` after the scroll pointer `$beba` passes `$bed2`: a direct ACIA poll
   for the space break code, which the emulator never delivers (TOS's ISR pops the FIFO first; CLAUDE.md,
   "Emulator behaviours"). `drive.txt` NOPs the 4-byte `bne` at `$a438`.
2. The cracktro copies a loader to `$70000` (`$a46a`-`$a488`). It is a FAT reader that drives the
   WD1772 and the DMA directly (`$8604`/`$8606`, INTRQ polled on MFP GPIP bit 5), loads the game by
   file name, and flashes the screen on a timeout. It reads the disk's own boot sector and root
   directory, so it needs `--disk-a` on every `resume` (the snapshot does not mount the disk).
3. The loader unpacks `CODE` and `MAIN` (`Ice!`) into low RAM (a loop around `$706c4`-`$7073c`, about
   1.5M steps). The game code then runs at `$2000`-`$27000` with its globals at `A5 = $272d4`.
4. Intro animation, title, main menu (about 130M steps after the cracktro). The menu pointer is the
   game's own: x at `$272f6`, y at `$272f8` (320 x 200 space), clamped at 0 (three
   `mouse move -127 -127` pin it). 1 PLAYER is at (30,155). A click shows the level briefing
   ("Level 1  Just dig!"), a second click starts the level.

`drive.txt` replays the whole path from the 300M-step cold boot snapshot to `scratchpad/lemmings/lvl1.snap`;
two runs gave byte-identical snapshots (`cmp`, 2026-10-18 session). The raster colour effects (palette
bands, menu text colours) render wrongly in `snap_render.py` because the game splits the palette per
scanline from Timer B; the logic is unaffected.

## What it needed from the emulator

| wall | symptom | fix |
|---|---|---|
| MFP vector base | The game writes VR (`$fffa17`) = `$00`, so its Timer B handler sits at vector 8 (`$20`); the emulator delivered vector `$48` (`$120`), which holds junk, and the CPU took a line-F bomb 170k steps into the title. | `PendingInterruptVector` takes the high nibble from VR (TOS sets `$48`, unchanged for every other game). |
| video address counter | The Timer B handler (`$28ac`) syncs to the beam: waits for bit 0 of `$ff8207` to read 1, then for the low byte `$ff8209` to go non-zero and back to 0. The counter registers were static, so the loop detector aborted at `$28c2`. | `HblTick(line)` refreshes `$ff8205/07/09` once per scanline (base + 160 per displayed line, held after line 199). Line resolution only. |

Both are one commit (`emulator: MFP vector base from VR ...`). Net: `verify 5000000` PASS; the 30M
diskless snapshot differs from HEAD in the two counter bytes only (`cmp -l`: 2 bytes); a PowerMonger
20M resume differs in the three counter bytes only; `selftest tests/680x0` 1000051 pass, 0 fail, 9 skip.

## Files

| file | contents |
|---|---|
| `drive.txt` | cold-boot snapshot to level 1 gameplay (REPL script) |
| `mechanics.md` | the lemming record, the per-frame update dispatch, skill assignment and the state bits |
| `extras.md` | access codes, level catalogue, ending, crack traces, keys (not behaviour) |
| `py/` | `codes.py` (generate/check codes), `ice.py` (Pack-Ice depacker), `levels.py` (run from `M68000/` with `PYTHONPATH=reversing/lemmings/py`; writes `levels.txt`) |
| `endpic.png` | the ending screen (`ENDPIC.IMG`, grey) |
| `click_digger.txt` | `lvl1_a.snap` to a digger assigned to lemming 0 (REPL script) |
| `click_blocker.txt` | `sel.snap` to a blocker assigned to lemming 0, its object-map stamp and the two turn handlers' hit counts (REPL script) |
| `py/skilldrive.py`, `py/terrain_diff.py` | drive a skill on lemming 0 from `sel.snap` and print/diff the terrain bitmap window (basher, miner; `--wall`, `--cells` poke terrain and object-map cells) |
| `py/objdrive.py`, `py/stepsweep.sh` | object-map cell codes (exit, traps, reversals) on lemming 0 beside level 1's exit; the walker's step, hop and wall thresholds by step height |
| `infographic/` | `gather.py` + `template.html` build the "Inside Lemmings" artifact from the `skilldrive.py` runs; it is a snapshot of `mechanics.md` and goes stale when that changes (`infographic/README.md`) |
