# Lemmings: handoff

Updated 2026-10-18 by the setup session (nothing committed yet by this workstream).

## Resume point

- Last commit of this workstream: none; `reversing/lemmings/README.md` is the first file.
- Working data: `scratchpad/lemmings/` (`lemmings.st` copied from Dropbox, `files/` extracted with
  `tools/extract_disk.py lemmings.st files`, `boot.log` GEMDOS/OS trace of a 300M-step cold boot).
- Disk: `~/Library/CloudStorage/Dropbox/Daves/ST games/Lemmings (1990)(Psygnosis)[cr BBC][a].st`,
  839,680 bytes, sha256 `118f33d900ad089dde85104f3635dc0a483f02944d55502d218de695ccb1a45d`.
- Start from: no snapshot yet. Next step is a drive to a playable level and a snapshot.
- Uncommitted work left behind: this file, `reversing/lemmings/README.md`, the `sessions/README.md` row.

## Focus

Lemming behaviour first: the per-lemming record, the skill/state machine (walker, faller, floater,
climber, blocker, builder, basher, miner, digger, bomber, splat, exit), the terrain collision it
reads, and the per-frame update order. Graphics, level format and sound come after, and only as far
as behaviour needs them (terrain bitmap, level object list).

## Proven so far (setup facts, not behaviour)

- Boot: BBC crack boot sector prints an anti-virus message, then `Pexec` of `\AUTO\LEMMINGS.PRG`
  (text `$a304`+`$dad8`, data/bss 0), `boot.log`. After `Super` the game calls XBIOS `Random()` ~50 times
  and `Vsync`, then makes no further GEMDOS/BIOS calls in 300M steps.
- `LEMMINGS.PRG`: `$601a` header, no symbols, 1 `4e56` word, so not compiled C; its text is mostly
  high-entropy bytes, so it is an encrypted or packed stub (inferred, not yet read).
- `CODE` (80,660 B) and `MAIN` (105,236 B) start with the packer magic `Ice!`: the real game code and
  main data, to be depacked. `LEVEL000-024`, `LEMMING1-3`, `TIM1-10`, `MENACE`... start `20 13 00 10 ..`
  (a shared compressed or tabular header, unidentified). `GROUND1-5`, `OBJECTS1-5`, `SPECIAL0-3`, `ODDTABLE`,
  `LEVELDAT`, `INTROPAR` are not yet classified.
- No `Fopen`/`Fread` after the Pexec, so the game loads from the disk itself (own FDC loader, inferred).

## Open, in priority order

1. Reach gameplay: find how the stub gets to `CODE`/`MAIN` (trace FDC DMA with `watch`, or snapshot
   after the Vsync loop), then drive the menu with mouse to level 1. Snapshot it.
2. Depack `CODE` (`Ice!` format; write or find `tools/` unpacker, check `DEVELOPING.md` "Other tools"
   first) and diff against RAM to find the game's load address.
3. Find the lemming array: poke-and-`watch` while a lemming spawns (entrance trapdoor releases at the
   release rate), then read the per-frame update loop and the skill dispatch table.
4. Collision: how terrain is read (bitmap pixel tests vs a mask) for walk/fall/dig/bash/mine/build.
5. Prove each skill's state machine with `callcap` corpora from natural hits (`capture_hits.py`).

## Known traps

- `ATARI_NOTRACE=1` on every raw `dotnet exec`. Run from `M68000/`.
- The original game is known to run the lemming update on a fixed tick; the VBL is 12,000 steps here.
  Confirm the tick rate from the code, not from this note (recalled, not checked).

## Next session

`/resume lemmings`. Do open items 1 and 2 first: get a gameplay snapshot, then depack `CODE`.
