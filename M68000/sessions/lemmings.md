# Lemmings: handoff

Updated 2026-10-31 by the seventh working session (the object table `$23044`, infographic republished).

## Resume point

- Last commit of this workstream: `d202acb` lemmings: object table `$23044` ... (`git log --oneline -- reversing/lemmings`).
  The emulator fix is `8b6c474`.
- Working data: `scratchpad/lemmings/`: `lemmings.st`, `files/`, `b300000000.snap` (cold boot, cracktro),
  `lvl1_a.snap` (level 1, all 10 out; stops in the cracktro frame, `A5 = $c822`: set `A5 = 272d4` before a
  `callcap`), `interesting/menu.snap` (title menu; `py/overrun.py` starts here), `sel.snap` (digger selected; every skill
  and object run starts here), `blk/post.snap` (blocker placed), `trapbusy/` (the four trap arms), `info/` (infographic
  build; `runs.prev/` is the previous build's runs, byte-identical to the current ones), `interesting/full.asm` (whole
  program, `$400`-`$27000`). Rebuild with `reversing/lemmings/drive.txt`, then `click_digger.txt`.
- Disk: `~/Library/CloudStorage/Dropbox/Daves/ST games/Lemmings (1990)(Psygnosis)[cr BBC][a].st`.
- Uncommitted work left behind: none (other sessions' files in the tree are theirs).

## Focus

Lemming behaviour (record, state machine, terrain collision, objects, update order). `extras.md` holds the side findings
(codes, levels, ending, crack).

## Infographic

`reversing/lemmings/infographic/` builds "Inside Lemmings", published private at
https://claude.ai/artifact/3M9FDun4B75R8QL7mofGaC (version 3, current with `mechanics.md` at `d202acb`).
`JOBS=2 infographic/build.sh` rebuilds it locally; plate text is hand-written in `template.html`: update it when
`mechanics.md` changes, rebuild, and ask Dave before republishing to the same URL. Dark mode and phone width are unchecked.

## Proven so far

Detail and match counts are in `reversing/lemmings/mechanics.md`.

- Boot to gameplay, deterministic (`drive.txt`). Two emulator walls fixed behind the net.
- Lemming array `$23484`, stride `$2c`, 10 of 10; skill click path, hit test `$1540`, digger (`click_digger.txt`).
- Collisions: terrain bitmap `$41806`/`$330` and object map `$62f80`/`$198`; the cell dispatch `$8b6e`.
- Blocker: stamp `02 0a 03`, turn handlers once each against 0 and 0 in the control (`click_blocker.txt`).
- All eight skills, fall and splat driven, steel refusal for basher and miner (`py/skilldrive.py`, `py/terrain_diff.py`).
- Walker thresholds (`py/stepsweep.sh`); basher and miner erase ticks (`py/maskwatch.py`).
- Exit, trap and reversal cell codes 1 to 6 (`py/objdrive.py`); the bomber's crater 113/113 pixels.
- Objects ("Objects"): `$23044` holds each level object's 34-byte copy of its type record (`$39ce`); the cell high nibble
  is the slot (`$33d0`); animator `$32a6` once a tick, 14/14 frames of level 1's loop; code 4 traps are one-shots that
  let a lemming through while animating, four arms, kills 0/1/1/2 as predicted (`py/trapbusy.py`). Set 0's 12 type roles inferred.
- Access codes 260/260 and 18/18, level catalogue, no secrets, the overrun past level 120 (`extras.md`, `py/codes.py`, `py/overrun.py`).

## Running

Nothing running.

## Open, in priority order

1. Object graphics at `$67270` (frame = 4 planes then mask, `+12` the mask offset; plane order unproven): render level 1's
   three objects and set 0's types to PNGs from `sel.snap` memory, match against a screen frame, and name the types
   from the pictures (commit the PNGs, index them in the README).
2. Fields +10 (frame), +20, +36/+38/+42; the release rate (`72(A5)`/`58(A5)`, `$34ac`); the blocker's refusal test
   (`$1b60`) and ground-loss release: drive each against a control from `sel.snap`.
3. Code `$b` (set 0 type 11, not dispatched by `$8b6e`: grep the other readers of `25(A0)`/`26(A0)`); one-way cells 7 and 8
   driven; a level with real traps (find one in `levels.txt` whose objects include set-0 types 6, 8 or 10) to confirm the
   trap with no pokes.
4. Optional: table of all 140 codes, `BasicFX`/`FullFX` (the effects switch `14(A5)` is 0 in `sel.snap`, so trap sound
   `$10` is unproven); dark-mode and phone check of the published infographic.

## Known traps

- A5-relative offsets in the docs are decimal: `54(A5)` is `$2730a` (A5 = `$272d4`), not `$27308`; a poke at the wrong
  hex sum looks like a game that ignores it (the overrun run zeroed `52(A5)`, the lemming count, and the level still needed 75%).
- The REPL's save command is `snap <path>` (`snapshot` is only the argv form); an unknown REPL word is silently ignored, so check
  the file exists. Forcing a win: `w 2730a 00000000` (saved and required percent) then ESC (`py/overrun.py`).
- In the intro program any `kbd` takes the TOS ACIA ISR into the loader and looks like a hang: `extras.md` "Keys and engine".
- `ATARI_NOTRACE=1`; `resume <snap> repl --disk-a <st>`; `mouse down l` / `mouse up l`; `m <addr> <len>` takes a decimal length.
- Pinning the pointer to the corner scrolls the level left; read the scroll `+2` of `$26c04` after the last move
  and aim at world `(lx - 8, ly - 13)` (`skilldrive.py` does this for lemming 0 at its fixed offset).
- `w` is a longword: poking a skill count also writes its neighbour (`+36` basher with `+38` floater); level 1 has 0 in every
  count but the digger's, so `skilldrive.py` writes `00050000`.
- A skill refused at once (builder with a hill ahead) is the game's own terrain test, not a failed click: read `+14` and the
  count after the click before concluding.
- The bomber keeps walking during its countdown, so its crater is wherever it stops: aim the window with `--x0`.
- Inside the blitter `$8cf8` `A5` is the blit block `$c822`, not `$272d4`, and `bt` throws AddressError down the `A6` chain there: read
  the caller from the stack yourself (`m <A7+56> 4` after its `movem.l` of 14 registers).
- Stop a `hits` or `bp` census at the exact phase: a `hits` first-step is relative to the run's own start, not the snapshot's.
- A poked object-map cell's high nibble picks the object slot whose `$23044` busy bit code 4 tests: `objdrive.py`'s `$04` used slot 0 (the
  entrance, idle), so its "vanishes at once" held only because that slot was idle. Poke `(slot << 4) | code` deliberately (`py/trapbusy.py`).
- `infographic/runs.sh` and `py/stepsweep.sh` start every emulator at once; on a shared machine run `JOBS=2 infographic/build.sh`.
- macOS `head -n -1` fails; write the script out in full instead of trimming another.
- The listing at `$2000` misses the input and click code below it; use `$400`.
- An agent's output files go in its own directory only: `make_blank_disk.py` deleted the tracked `blank_80ss.st` (restored).

## Waiting on Dave

- `/resume` and `/handoff` cannot be invoked by a session started from another session (the wrappers are
  `disable-model-invocation`): this session's resume was skipped and the handoff ran only when Dave typed it. If side
  sessions are meant to run them, the wrappers in `.claude/skills/` need that flag dropped.

## Next session

`/resume lemmings`. Item 1: decode one object frame (level 1's exit, slot 1, 48 by 17, 510 bytes at `$67270 + $22ec`) to
a PNG and match it against a screen render of that area; then the other types. Fold results into `mechanics.md`
"Objects" and the infographic, `JOBS=2 infographic/build.sh`, and ask Dave before republishing.
