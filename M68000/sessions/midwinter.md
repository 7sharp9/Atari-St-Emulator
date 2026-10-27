# Midwinter: handoff

Updated 2026-10-27 by the session that proved the attacks and the period end (work `788ed13`, `7a07a84`; lessons
`b2d4e0e`).

## Resume point

- Last commit of this workstream: `7a07a84` (period end proven; the handoff commit follows it).
- Working data: `M68000/scratchpad/midwinter/` (indexed in `scratchpad/ANCHORS.md`). Rebuild: unzip
  `~/Library/CloudStorage/Dropbox/Daves/ST games/Zuul #67.zip`, `tools/msa2st.py ZUUL067.MSA zuul067.st`,
  `tools/extract_disk.py zuul067.st files`, `tools/lsd_depack.py --all files unpacked`, then the README's two commands
  (cold boot 20M, `drive.txt`).
- Start from: `d_ski.snap` (3D view, unit 27 in the encounter window, slot 0 engaged, a Bomber in the air) for combat
  work; `d_team.snap` (The Team, 08:00) for turn-level and sabotage work; `army/clock1.snap` (the SITUATION REPORT).
  Every resume needs `--disk-a scratchpad/midwinter/zuul067.st`.
- Uncommitted work left behind: none of this workstream (the root `Cadaver/` is untracked and not Midwinter's).
  Throwaway probes are in `scratchpad/midwinter/atk/` (also `atk/all.asm`, the whole-image listing of `d_ski`).

## Proven so far

- Boot to the 3D view, deterministic (`drive.txt`); architecture skeleton with census counts (`architecture.md`).
- Terrain (`terrain.md`): `py/terrain/gate_terrain.py` 70000/70000 cells, post-passes 10000/10000.
- Character records (`ai.md` 1): Stark's 14 bio ratings 14/14; +63/+64 the building the character is in.
- Enemy army (`ai.md` 2): `py/army/gate_army.py` natural ticks 42/42 and 9/9, supply 10/10, chained 1000/1000, 284/284.
- Encounters and losses (`ai.md` 3): `py/army/gate_encounter.py` search 96/96 and 1/1, frames 9600/9600 and 329/329,
  kills 512/512.
- Attacks (`ai.md` 4): Bomber (BOMBERS, mask bit 0), Spotter with its mortar barrage (MORTARS, bit 1) and the engaged
  vehicle's missiles (TRAINING off, bit 2), per-vehicle masks, launch odds from a point off the island's corner past
  the HQ (a units slip, inferred), bomb and shell hits within 200. Nothing but the army's walk takes a site, and no
  site is ever released. `py/attack/gate_attack.py`: launches 768/768 x2, odds 1452/1452, missile 128/128 and 5/5,
  bomb 1494/1494, shell 361/361, 0 feature-list writes over the 170-frame natural run; five broken models fail.
- Period end (`ai.md` 5): building counts, prisoners, Morale loss (2 / 10 per gain, one period late), the endings (HQ
  blown up or 20 days win, no free Heat Mines loses) and the radio reward (no enemy Radio Station: full team).
  `py/army/gate_period.py`: natural 6/6, poked 200/200 per routine, the report's 14 numbers 14/14; three broken models
  fail.
- All five gates in `tools/gates.py run midwinter` (about 90 s). Design digest in the README covers all of the above.

## Open, in priority order

1. **The player's side of combat**: which slot becomes engaged (`$ca7e`/`$cb2e`, within 32 of the camera), the
   engaged vehicle's script `$20ce2` and its missile odds `$1faa6` (reads character +72), the player's shot
   (`$1fd96` on object `$1cd7e`, ammunition `$2513e`; `$14220` calls the kill `$cbbe`), and the radio message
   `$d048` (needs interrupts: drive it). Prove with stclient calls from `d_ski.snap`, as `gate_attack.py` does, and
   one driven kill.
2. **Sabotage**: planting and removing explosives, the blast `$41e2..$4272` (`$4340`, the building word's bit 6, the
   Ruin type `$10`, the Cable Car Station's linked building, `$2c188` counts, the HQ flag `$24e8c`), and the ending
   screens `$115ae`/`$1137a`. It is the player's only lever on sites, the radio reward and the HQ win. Drive one
   sabotage from `d_team.snap` (a character inside a building) and gate the blast against a model.
3. **Relationships and recruitment one by one**: the team list `$2b16c` writers other than `$f8d8`, S.O.S / recruit
   paths (`$5784`, bio icons `$3054`/`$3024`).
4. **3D pipeline**: `$18304` -> `$16d9c`, draw list `$19ce2`/`$1d5a6`, polygon fill; proof by rendering a frame. Also
   matches encounter slots and attackers to on-screen objects.
5. Leftovers: character +72's name, `$13f28` (missile 1-in-5), `$14774` (driving mask skip), record +0 bit 7 after a
   hit, travel mode 1 (mask 0, inferred cable car), the Bomber's drop rule and the missile's detonation (read, not
   gated); unit +12's reader, the non-spread branch and `$2bb2e`, node names; terrain leftovers; Decisions icons 3/5.

## Known traps

- The menu's fullscreen VBL outruns the instruction-counted VBL and starves the main loop (poked to `rte`).
- Options and character-screen snapshots catch the pointer mid-redraw: compare with a 34-pixel tolerance.
- A `u <addr>` into the menu stops inside its packer stub before the depacked code exists: the drive pokes after a
  fixed `s 60000000`.
- `--all` listings lose sync at `$10840`, `$1fa0a`, `$19ce2`; the bytes before `$ec8c` are data. Use `--linear` there.
- `stserver`'s `mouse` click does not register in this game, while the same REPL lines do: click in the REPL,
  `u <routine>`, `snap`, load in `stserver` (`gate_army.py`, `gate_period.py`).
- The army moves only at a situation report: a long ski run with no report shows no army change.
- From `d_ski.snap` a missile from the engaged vehicle hits at frame 170 (`$14dfc` by `$2061a`) and the trip ends: bound
  natural 3D runs below that, or steer, or poke the missile object `$1ce02` +38 busy.
- Unit coordinates (and the feature list) are twice the terrain target's (`$19cd4`): poke the target to `unit / 2`.
- `$cbbe`'s unit-kill path ends in `$d048`, which waits on an interrupt: under `call`, stop it with `stops=[0xcd6e]`.
- `$f374` loops 65536 times on a record with kind `$80` (held, no buildings): never poke one.

## Next session

`/resume midwinter`. Start on item 1. From `d_ski.snap`, read `$ca7e`/`$cb2e` and `$1fa0a`/`$1faa6` (engagement and
missile odds), then the player's shot `$1fd96` and its hit test up to `$14220` -> `$cbbe`. Gate them with stclient
calls in `py/attack/`, keeping a broken-model control per rule and a corpus that straddles every threshold.
