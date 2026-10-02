# exit_level0: the whole natural chain out of level 0 (Cadaver, 88th pass)

One command takes the treasury snapshot (`scratchpad/cadaver/secrets_out/action/rwn2/taken53.snap`: room 37, crown 53 and key 104 carried, health 35) to room 60 (the stall under object 84, which starts
level 1), with joystick/keyboard input only: nothing poked, nothing injected (the crown 53 comes from the heal chain's lineage, so `g2` never calls verb 35).  Health 20, XP 980 on arrival, and no health
is lost on any leg after the heal chain.

    cd M68000
    .venv/bin/python reversing/cadaver/py/secrets/overlay/action/exit_level0/route_level0_exit.py OUTDIR [START.snap] [--upto=heal|d1|e1|g1|g2|level1|room31|room90]

About 4 minutes (heal 37 s, d1 34 s, e1 42 s, g1 98 s, g2 21 s).  The master runs the five segments as subprocesses, one emulator at a time, with `M68000_ROOT`, `ATARI_NOTRACE=1` and `.venv/bin/python`, and
`CAD_OUT=OUTDIR/<segment>/_scratch`; everything is written under `OUTDIR/<segment>/` (snapshots, `log.txt`, `_scratch/`).  It prints a line per segment and the final room/health/XP, and exits non-zero on a
failed segment, a missing hand-off snapshot or an end other than room 60.  `--upto=<segment>` stops after that segment.  The segments can also be run alone (`<script> <start.snap> <OUTDIR>`).

## Segments and hand-off snapshots

| segment | script | from -> to | hand-off to the next segment |
|---|---|---|---|
| `heal` | `../route_heal_chain.py OUTDIR/heal START` (repo, 87th pass) | treasury -> room 16 (lever, water) -> heal road (oil 182, flask 392) -> rooms 15, 13, 14 -> BUTTON chain opens door `$2a`; ends in the room 13 stall | `heal/ck_71_L_stall_2a.snap` (room 13, health 47, XP 132) |
| `d1` | `d1/route_gems_to_room27.py` (+ `play.py`) | room 13 -> gems 164 and 290 (rooms 9 and 20), event 5 opens the hole of room 21, the fall into room 27 (health 30) | last `d1/gems/NN_*.snap` |
| `e1` | `e1/route_room27_to_room22_natural.py` (+ `play.py`) | room 27: guard-clearing wait `WQ`, chest stand, gems thrown by id (`SG<id>`), urn 143 and key 167 carried, to room 22 | last `e1/route/NN_*.snap` |
| `g1` | `g1/route_room22_to_altar99.py [phases=ABCD]` (+ `route_room22_to_371.py`, `e3lib.py`, `route_cross38.py`, `profile38.json`, `run.sh`) | room 22 -> 15 -> 16 -> 38 (F1 crossing, `down`) -> 39 -> 40: scroll 371 and key 110; the south-east cluster, urn 165, altar 99 jump; 324 in front | `g1/D_end.snap` (room 39, hero on altar 99's top, health 20) |
| `g2` | `g2/route_altar_to_room36_real.py` (+ `lib.py`, `f1/route_cross38.py`, `f1/profile38.json`) | READ MAGIC 371 cast at 324, take 324, room 38 `up` (F1), rooms 17, 16, 15, 13, door `$2a`, room 36: MASSACRE, object 486, door `$29` -> room 60 | `g2/end_room60.snap` (also `g2/level_change.py <that> <OUTDIR>`: START LEVEL, a separate, optional step) |
| `level1` (optional) | `g2/level_change.py <end_room60.snap> OUTDIR` | room 60 -> START LEVEL (object 84), Space at PLACE LEVELS DISK, about 20M steps (7 s) | `level1/level1_room0.snap` (level 1 room 0, health 20 of 200, XP 980, rucksack empty) |
| `room31` (optional) | `l1/route_level1_first.py <level1_room0.snap> OUTDIR` | room 0 -> 34 -> 29: jump onto block 425, take STAMINA 556, two doses (20 -> 60), the damage-free lane -> room 31 | `room31/end_room31.snap` (room 31 at (10,20,4,14), health 60, XP 980) |
| `room90` (optional) | `l1/route_level1_room90.py <end_room31.snap> OUTDIR` | room 31 altar jump and skull (door `$7a`), room 32 (armour 578, lever 146 at VAR 6 = VAR 7 = 2), room 12 (armour thrown into region 1, lever 225, both pillars crossed in their clear windows) -> room 90 | `room90/end_room90.snap` (room 90 at (14,20,8,14), health 60, XP 1006) |

The hand-off rule is the one of the 88th-pass driver: the last snapshot whose name starts with digits, sorted by name (`d1/gems/`, `e1/route/`), or the fixed name above.  `lib/` is one shared copy of
`drv.py`, `h.py`, `ov.py`, `route_lib.py`, `trek.py`, `route_chain.py` (the d1/e1/g1/f1 copies of the exploration were identical except for their output directory); every output of the libs
(`r16/`, `r12/`, `trek/`, `h/`) goes under `$CAD_OUT`.  `heal` uses the repo's own `action/` libs, which create their `r16/`, `r12/` and `trek/` directories under `scratchpad/cadaver/secrets_out/action/` on import.
`e1/play.py` still carries the injected `G<id>` token (verb 35) of the exploration; no promoted token list uses it.  Each directory's scripts locate the repo from `__file__` or `M68000_ROOT`.

## Knobs (phase searches that exist because the creatures' patrols are a function of the steps spent in a room)

All values below are searched or fixed by the scripts; none is a minimum, and changing one changes every later snapshot (determinism needs the same reloads and the same tokens).

- E1 `WQ` guard wait (`play.py wait_quiet`, `chunk=25000`, `seen_cap=1500000`, `cap=4000000`): in room 27, before `gL14`, wait until the guard creature (object 127, id >= 900) has appeared and gone, then settle 50,000 steps.
  If no guard is seen within `seen_cap` it proceeds ("no guard seen"), and the fireball could then arrive during the chest stand; no run did.
- F1 lookahead (`route_cross38.py <start> <OUTDIR> <down|up> [pre_wait] [--horizon=N] [--margin=N] [--force] [--sweep]`): records the creature table of room 38 every 5,000 steps for `HORIZON` = 4,500,000
  steps with the hero standing still, plans a wait plus a walk whose creature contact count stays below the health margin (`MARGIN` = 2), then executes it.  G1 calls it with `down` (wait 1,045,000 in this chain); G2 calls it with `up` (`--pre=N` of `route_altar_to_room36_real.py` is the optional pre-wait, 0 by default; the wait found in this chain's lineage is 140,000, in the 88th-pass test lineage 955,000).  `profile38.json` is the measured free `down` walk (the e2 lineage).
- G1 W39/W38 wait searches (`g1/route_room22_to_altar99.py` phase D): W39 (wait in room 39 before the north lane, outer, `range(0, 2000001, 125000)`, env `G1_W39LIST`) and W38 (wait in room 38 before the
  FLAME stage, inner, 0..3,500,000 in 250,000 steps, env `G1_WLIST`); each trial aborts at the first health loss and the first free pair is kept (`D_waits.json`; the real chain finds W39 = 1,125,000, W38 = 0).
  Phase C's 4.8M wait (room 53) and the 2.3M room 15 waits are fixed phase fixes, not minima.
- `find_n` pulse searches (`g1` and `g2`): with six or more items carried the Return grid shows four cells and the cursor `2122(A5)` sticks, so the RIGHT-pulse count that opens the panel of item
  `oid` (item word `1236(A5) == oid` after FIRE) is searched on forks of the last checkpoint (`find_n(R, 482)`, `find_n(R, 165, nav=True)` in G1, `find_n(Rt, 324)` in G2); the first count that works is used.
- `route_altar_to_room36_real.py` flags: `--upto=A|F|B|C|D`, `--pre=N`; `--poke2a` and `--hp=N` are TEST ONLY (door word / health poked) and are not used by the master.
- `l1/route_level1_room90.py` (90th pass) searches three waits that are frame-phase lotteries, all on forks of the leg's own checkpoint: the throw's settle (first of 0, 5,000, ... that sends the armour into region 1: 145,000 in this chain), and the wait before each pillar crossing (first with no health loss and a clearance of at least 2: 100,000 under 214 and 1,500,000 under 213 in this chain). The pillars' clock runs on frames, so a recording with the hero standing still does not predict a walk.
