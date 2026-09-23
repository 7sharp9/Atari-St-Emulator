# Populous: handoff

Updated 2026-09-23 by the session that ended with the handoff commit after `951b15a`.

## Resume point

- Last commits of this workstream: `f425c8b` (pop-208 swamp monster), `c023cea` (trail sprites
  rendered), `e9abb10` (`$1063a` combat end to end), `951b15a` (design digest, `Repl2` fix), then the
  handoff commit. `8e3a350` changed the `/handoff` skill (design-digest check).
- `bin/` is the `5c32af8` build (IKBD fix); every count from the last two sessions ran on it.
- Working data: `$POP_WORK` = `M68000/scratchpad/pop/` (rebuild: `reversing/populous/README.md`,
  "Drive recipe" and "Working data"). This session's data: `$POP_WORK/swamp208/` (poked pop-208
  snapshots `p_cg2`, `p_spawn` + `.after`), `$POP_WORK/systems/view/` (trail renders),
  `$POP_WORK/powers/fight/` (the `$1063a` live logs).
- Start from: `walker/snaps/fight1.snap` for combat and take-overs; `ai/M1.snap` for the Armageddon
  brawl; `ai/cg1.snap` / `cg2.snap` for computer play; `drive/A.snap` for UI work. All in
  `scratchpad/ANCHORS.md`.
- Uncommitted work left behind: none.

## Proven so far

Five topic docs, each count in the table at the top of `reversing/populous/README.md`. The README's
**Design digest** restates the rules for re-use and cites the section proving each line; `/handoff`
re-checks it.

- Graphics: frame rebuilt from RAM 64000/64000 on 12 frames; trail sprites rendered live 32/32
  (`py/systems/trailview.py`); mouse UI `py/verify_drive.py` 17/17.
- Terrain: generator byte-identical for 3 worlds; raise/lower; six powers 2305/2305 and 8/8 casts.
- Mechanics: settlements, mana, spawns; walker direction 2400/2400 + 8000/8000 live; knight
  154/154 live; combat `$1063a` on every live call, rounds 71/71 and resolutions 9/9
  (`py/powers/live.py <snap> <frames> fight`, `mechanics.md` 3.5); Armageddon brawl 441/441; score.
- AI: 4800/4800 decision routines; natural runs 1854/1854, 2766/2766; flood/armageddon casts.
- Systems: trails 400/400 + 400/400 callcaps, 394/394 live; the pop-208 swamp spawn (poked slots,
  natural edge) 400/400 and 237/238 frames with 20 swamp cells made (`py/systems/swamp208.py poke`
  + `trailrun.py` with `TRAIL_*`); its edge is interrupt stack debris at `$3f418` (2000/2000 frames
  measured, `swamp208.py edges`, `systems.md` 1.3).

## Open, in priority order

1. **Town take-over and settlement death, `$10366` claim.** The only resolution path not modelled
   (3 take-overs in `fight1`, counted not compared), and `entity_kill` of a settlement. Model
   `$10366(e, 0)` claiming and the non-knight branch of `$108b8`, then re-run
   `live.py fight1.snap 1500 fight resolve` until the take-overs compare.
2. `$ef4c`'s post-decision writes (settle, merge, fight start `$10e7e`, occupancy and visit counts)
   diff-tested on their own; a knight merging into a friendly walker live.
3. Smaller loose ends: sounds 5/6 and the `$37e78` bits (`systems.md` 6); the command that sets
   `$3c4e4`; `$135fc`'s second call site `$e580` live; the `$f6b2` swamp raise live; a full SAVE/LOAD
   round trip on a disk with space; PAINT MAP, RESTART/NEXT MAP; SPR_320 frames 9 and 11 live (sample
   the type-2 trail on the other parity); a pop-208 spawn on edge 1 or a stale cell (poke `$3f418`).
4. Lowest: the serial link (`$19652`, needs a second emulated machine; also whether the `$3f418`
   debris desyncs it); the LORD/MOUTHS speech (side 1 of the original disk).

For the emulator workstream, not Populous: Timer A is a stub (64 interrupts per frame), so sampled
sound plays at the wrong rate (`systems.md` 6.2).

## Known traps

- `py/repl.py`'s `Repl` loses sync after a `bp`; use `py/powers/pwlib.Repl2` (its `cmd('r')` is fixed
  as of `951b15a`).
- In callcap memory compares exclude `$37f5a..$37f89` (trap wrappers' register save).
- `callcap` masks interrupts: a routine that waits for the VBL must be tested in two halves.
- The game runs in supervisor mode on one stack: interrupt handlers overwrite stack words below the
  main loop between frames, so an uninitialised local can differ frame to frame (`systems.md` 1.3).
- `$14364` takes the view origin as pushed arguments: poke cx/cy before `$b6fc` (at the previous
  frame's `$b7c8`), as `trailview.py` does.
- A land click acts only when one of your entities is in view (`$3d54e`); the GENESIS human is on
  an island (bridging raises: `py/walker/campaign2.py`). `click.snap` is the CONQUEST click.
- Snapshots made before `5c32af8` came from a DLL that injected stray key presses; regenerate
  rather than diff old vs new.
- Scripts spawn the emulator with cwd `M68000/`: pass absolute snapshot paths.
- A loop over frames needs an exit for "the game stopped" (score screen): `live.py` and `trailrun.py`
  have one; `capframes.py` past the end re-dumps the same state (dedupe by frame).
- Full AI live replays take 1.5-2.5 h with 9 processes; `live.py fight` over 1500 frames about 45 min.

## Next session

Item 1: model the town take-over (`$10366` claim, `$108b8`'s non-knight branch) and settlement
death, then run `py/powers/live.py fight1.snap 1500 fight resolve` until the take-overs compare.
Prompt: `/resume populous`.
