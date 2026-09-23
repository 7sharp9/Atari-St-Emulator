# Populous: handoff

Updated 2026-09-23 by the session that ended with the handoff commit after `ec5b49b`.

## Resume point

- Last commits of this workstream: `ec5b49b` (flood and armageddon cast by the computer live, the
  Armageddon brawl model), then the handoff commit (this file, `py/capframes.py` path fix).
- `bin/` is the `5c32af8` build (IKBD fix); every count from this session ran on it.
- Working data: `$POP_WORK` = `M68000/scratchpad/pop/` (rebuild: `reversing/populous/README.md`,
  "Drive recipe" and "Working data"). Per-area data under `$POP_WORK/<area>/`; pass-2 agents' raw
  output in `$POP_WORK/agents/`.
- Start from: `drive/A.snap` (GENESIS, view on your town) for UI work; `ai/cg1.snap` (hard opponent)
  and `ai/cg2.snap` (ATARI VS ATARI); `ai/F0.snap`, `M0.snap`, `M1.snap` for the endgame powers;
  `systems/spawn.snap` for the trail monsters. All listed in `scratchpad/ANCHORS.md`.
- Uncommitted work left behind: none.

## Proven so far

Five topic docs (`reversing/populous/README.md` has the table with every count):

- Graphics: the frame rebuilt from RAM, 64000/64000 pixels on 12 frames; the mouse UI driven,
  `py/verify_drive.py` 17/17.
- Terrain: world generator byte-identical for 3 worlds; raise/lower; all six powers 2305/2305 under
  `callcap` and 8/8 casts through the UI; next world, names, start paths, starting walkers.
- Mechanics: settlements, mana, spawns, combat; walker direction 2400/2400 and 8000/8000 live;
  knight 154/154 live; score screen 200/200 and 56/56. The Armageddon brawl after a computer cast
  (`mechanics.md` 5, `py/endgame/brawlcheck.py`): magnets and footprint release 441/441 frames,
  vacates 20/20, populations 421/421; `fightcheck.py` rounds 12/12 in it. Footprint table `$22b4e`
  and the `$10366` release are in `mechanics.md` 4.3.
- AI: 4800/4800 decision routines; two natural runs 1854/1854 and 2766/2766; flood and armageddon
  cast by the computer with poked mana (`ai.md` 5, `py/ai/s5_endpow.py`, runs F and M): every AI
  call matched, commands 111/111 and 169/169, flood heights 4225/4225.
- Systems: trail monsters 400/400 + 400/400 and 394/394 live; key checks; pause; LOLO1.GAM; sounds.

## Open, in priority order

1. **The population-208 swamp monster** (`$e89c`, `systems.md` 1.3): reach 208 live entities (a long
   ATARI VS ATARI run from `ai/cg2.snap`, or pokes) and diff the spawn; its edge comes from `$db4c`'s
   uninitialised local -146(A6), so record which edge it really takes.
2. **What the player sees of the trail monsters.** Confirm the SPR_320 frames Dave identified by eye
   with a rendered frame of the forced type-0 run (`py/systems/trailrun.py 220 0`) through
   `pop_render.py`, and finish the SPR_320 frame identities.
3. The combat resolution (`$1063a` when a side dies: loser's mana to -250, winner +3000 seen twice in
   run M; `$108b8` bookkeeping): model it and check it on fightcheck's RESOLVE lines from
   `M1.snap` and `fight1`.
4. `$ef4c`'s post-decision writes (settle, merge, fight start, occupancy and visit counts) diff-tested
   on their own; a knight merging into a friendly walker live; the non-knight town take-over in
   `$108b8` (`$10366` claim).
5. Smaller loose ends: sounds 5/6 and the `$37e78` bits (`systems.md` 6); the command that sets
   `$3c4e4`; `$135fc`'s second call site `$e580` live; the `$f6b2` swamp raise live; a full-size SAVE
   then LOAD round trip on a disk with space; PAINT MAP, RESTART/NEXT MAP items (code-read only).
6. Lowest: the serial two-player link (`$19652`, MFP 10/12, `$1d03e`, `$3d52c`) needs a second
   emulated machine; the LORD/MOUTHS speech needs side 1 of the original double-sided disk.

For the emulator workstream, not Populous: Timer A is a stub (64 interrupts per frame, ignores
TACR/TADR), so sampled sound plays at the wrong rate (`systems.md` 6.2).

## Known traps

- `py/repl.py`'s `Repl` loses sync after a `bp` (the breakpoint prints registers twice); use
  `py/powers/pwlib.Repl2`.
- In callcap memory compares, exclude `$37f5a..$37f89`: the trap wrappers' register save stack
  changes on every OS call.
- `callcap` masks interrupts: a routine that waits for the VBL (the earthquake's shake) must be
  tested in two halves (callcap from after the wait, `$12470`).
- A land click acts only when one of your entities is in view (`$3d54e`); a magnet click does not.
  The GENESIS human is on an island: contact with the enemy needs the bridging raises of
  `py/walker/campaign2.py`.
- `click.snap` is the CONQUEST click (y 176 is the CONQUEST band), not CUSTOM.
- Snapshots made before `5c32af8` came from a DLL that injected stray key presses on every
  `mouse move`; re-running their drives on the fixed DLL can differ in a few bytes (`$20021`,
  `$37eae`). Pass-2 counts were produced on the old DLL; regenerate a snapshot rather than diff old
  vs new. (`M0.snap` is poked from run A's old-DLL `f01065.snap`; everything after the poke ran on
  the fixed DLL.)
- The scripts that spawn the emulator run it with cwd `M68000/`: pass absolute snapshot paths
  (`capframes.py` now absolutises its own; others may not).
- `capframes.py` past the game's end re-dumps the same state; dedupe by frame (`brawlcheck.py` does).
- A full AI live replay (`py/ai/livecheck.py` over 8 call sites) takes 1.5-2.5 hours with 9
  processes; 18 processes (two scenarios) ran fine together on this 16-core machine. `join.py` over
  the recorded logs in `$POP_WORK/ai/live/` takes minutes.

## Next session

Item 1: the population-208 swamp monster. Run ATARI VS ATARI from `ai/cg2.snap` with a watch on the
entity count `$3c4e2` (or poke the table close to full), stop at `$e89c`, and diff the spawn against
`py/systems/trail_ref.py`; record the edge taken from the uninitialised -146(A6).
Prompt: `/resume populous`.
