# Midwinter: handoff

Updated 2026-10-27 by the session that proved the encounters (work `9655ddf`, digest `f2931cd`, tool `f942dc9`).

## Resume point

- Last commit of this workstream: `f942dc9` (stclient `stops=`; the encounter gate's kill leg uses it).
- Working data: `M68000/scratchpad/midwinter/` (indexed in `scratchpad/ANCHORS.md`). Rebuild: unzip
  `~/Library/CloudStorage/Dropbox/Daves/ST games/Zuul #67.zip`, `tools/msa2st.py ZUUL067.MSA zuul067.st`,
  `tools/extract_disk.py zuul067.st files`, `tools/lsd_depack.py --all files unpacked`, then the README's two commands
  (cold boot 20M, `drive.txt`).
- Start from: `d_ski.snap` (3D view, unit 27 in the encounter window, slot 0 engaged, an enemy plane attacking) for
  encounter and aircraft work; `d_team.snap` (The Team, 08:00) for turn-level work; `army/clock1.snap` (the SITUATION
  REPORT). Every resume needs `--disk-a scratchpad/midwinter/zuul067.st`.
- Uncommitted work left behind: none of this workstream (the root `Cadaver/` is untracked and not Midwinter's).
  Throwaway probes are in `scratchpad/midwinter/enc/`.

## Proven so far

- Boot to the 3D view, deterministic (`drive.txt`); architecture skeleton with census counts (`architecture.md`).
- Terrain (`terrain.md`): `py/terrain/gate_terrain.py` 70000/70000 cells, post-passes 10000/10000.
- Character records (`ai.md` 1): Stark's 14 bio ratings 14/14.
- Enemy army (`ai.md` 2): `py/army/gate_army.py` natural ticks 42/42 and 9/9, supply 10/10, chained 1000/1000, 284/284.
- Encounters and losses (`ai.md` 3): unit +6..+10 are Snow bulls, Tankers, Snow wolves, Snow cats, Snow foxes (named
  through the identify table `$11ae2` and the shape table `$31698`); +14 strength; +15 groups (leaders 0..5, four
  members each). `py/army/gate_encounter.py`: natural `$c2f0` 1/1 and `$c4f2` 164/164 + 165/165, poked `$c2f0` 96/96,
  chained frames 9600/9600, empty window 2/2, kills `$cbbe` 512/512; four broken models fail. The report's MOBILE
  VEHICLES 4067 equals the unit-table sum 4067/4067.
- All three gates in `tools/gates.py run midwinter` (about 75 s). Design digest in the README (island, army,
  encounters).

## Open, in priority order

1. **What else attacks or takes a site**: the Bomber (type `$1d`), Spotter (`$1a`) and Snow witch (`$12`), the plane
   attacking in `d_ski`, and the options' MORTARS/BOMBERS switches. Settles whether the five road-less sites are safe
   and completes the digest's enemy side. Start: who reads the options flags (`tables/`, the options action table),
   and break on writes to the feature list's kind bytes (`$2a150`) other than `$c136`'s during a ski run.
2. **The period end's own tests and the report's site counts**: `$f374`, `$f3be`, the endings `$118ba`/`$118f6`
   (clock `>= $7080`), the morale loss `$ed88`, and the report's held Factories/Plants/Warehouses/Radio Stations
   (`$ef8c`) against `situation_report.png`. Callcap gate of each.
3. **The engagement and the player's side of combat**: `$ca7e`/`$cb2e` (which slot becomes engaged, within 32 units
   of the camera), what calls `$cbbe` (`$14220`: the player's shot), and the radio message `$d048` (needs interrupts:
   drive it, do not `call` it).
4. **Relationships and recruitment**: the team list `$2b16c` (who writes it), S.O.S / recruit paths (`$5784`, bio
   icons `$3054`/`$3024`).
5. **3D pipeline**: `$18304` -> `$16d9c`, draw list `$19ce2`/`$1d5a6`, polygon fill; proof by rendering a frame. Also
   matches encounter slots to on-screen objects (none visible in the one frame rendered, `d_ski` + 120 frames).
6. Unit +12's reader, the non-spread branch and `$2bb2e`, node names; terrain leftovers; Decisions icons 3/5.

## Known traps

- The menu's fullscreen VBL outruns the instruction-counted VBL and starves the main loop (poked to `rte`).
- Options and character-screen snapshots catch the pointer mid-redraw: compare with a 34-pixel tolerance.
- A `u <addr>` into the menu stops inside its packer stub before the depacked code exists: the drive pokes after a
  fixed `s 60000000`.
- `--all` listings lose sync at `$10840`, `$1fa0a`, `$19ce2`; the bytes before `$ec8c` are data.
- `stserver`'s `mouse` click does not register in this game, while the same REPL lines do: click in the REPL,
  `u <routine>`, `snap`, load in `stserver` (both gates do).
- The army moves only at a situation report: a long ski run with no report shows no army change.
- From `d_ski.snap` the unsteered skier crashes after about 170 frames (`$c4f2` calls) and leaves the 3D loop: bound
  natural 3D runs below that or steer.
- Unit coordinates are twice the terrain target's (`$19cd4`): poke the target to `unit / 2` to put a unit in view.
- `$cbbe`'s unit-kill path ends in `$d048`, which waits on an interrupt: under `call`, stop it with
  `stops=[0xcd6e]`.

## Next session

`/resume midwinter`. Start on item 1. From `d_ski.snap`, find the attacking plane's object (type `$1d` in the 3D object
list `$70010`, or a slot outside `$2d47e`) and the routine that moves it. Then read the options' MORTARS/BOMBERS flags
to their readers, and watch `$2a150` kind bytes over a ski run with the plane active. Gate whatever site-attack rule
turns up with `tools/stclient.py`, as `gate_encounter.py` does.
