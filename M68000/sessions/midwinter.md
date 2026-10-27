# Midwinter: handoff

Updated 2026-10-27 by the session that proved the enemy army (work commits `d96c936`, `9ecc19a`; tools `b18f784`).

## Resume point

- Last commit of this workstream: `9ecc19a` (the period end is The Team's clock icon; nine army ticks per report).
- Working data: `M68000/scratchpad/midwinter/` (indexed in `scratchpad/ANCHORS.md`). Rebuild: unzip
  `~/Library/CloudStorage/Dropbox/Daves/ST games/Zuul #67.zip`, `tools/msa2st.py ZUUL067.MSA zuul067.st`,
  `tools/extract_disk.py zuul067.st files`, `tools/lsd_depack.py --all files unpacked`, then the README's two commands
  (cold boot 20M, `drive.txt`).
- Start from: `scratchpad/midwinter/d_team.snap` (The Team, game clock 08:00) for turn-level work;
  `army/clock1.snap` (the SITUATION REPORT) and `army/clock2.snap` (The Team after one report, 10:00, 39 nodes held);
  `d_ski.snap` for the 3D view. Every resume needs `--disk-a scratchpad/midwinter/zuul067.st`.
- Uncommitted work left behind: none of this workstream (the root `Cadaver/` is untracked and not Midwinter's).

## Proven so far

- Boot to the 3D view, deterministic (`drive.txt`, six milestones byte-identical over two runs); only poke the menu VBL
  stub `$a5e0`. `tools/lsd_depack.py` decodes all 63 files. Architecture skeleton with census counts (`architecture.md`).
- Terrain (`terrain.md`): file 37.2's 50 x 50 grid, five diamond-square subdivisions around the player, post-passes.
  `py/terrain/gate_terrain.py`: 70000/70000 cells, post-passes 10000/10000.
- Character records (`ai.md` section 1): 32 x `$4a` at `$2b194`; +1..+14 the 14 bio ratings (Stark 14/14), +32 the
  character's clock, +34/+38 position.
- Enemy army (`ai.md` section 2): 32 units at `$2bb96` random-walking a 96-node road graph (`$25b4a`, `$25cca`,
  state `$2bb36`), capturing sites, speed recomputed hourly from held Warehouses and Synthesis Plants (`$f56e`,
  `$f5e2`). 42 ticks at PLAY (`$ee30`); nine per situation report: The Team's clock icon is `$ec8c` (report
  `$ef36`), dismissing it runs the ticks. `py/army/gate_army.py` (in `tools/gates.py run midwinter`): natural 42/42
  and 9/9, supply 10/10, no other writer between calls, chained 1000/1000 and 284/284.

## Open, in priority order

1. **Encounters and attacks on sites**: `$c2f0`/`$c4f2` put the army unit nearest the player into the 3D view
   (read only). Decode what +6..+10 count, match them against the 3D objects of a frame with a unit in view, and find
   what else attacks or captures a site (bombers, the "mortars/bombers" options), which settles whether a site off
   the road graph (Radio Station 76, Mountain Hut 59) is safe. Proof: a callcap or stserver gate of `$c2f0` over
   positions poked near units, plus a 3D snapshot with a unit in view.
2. **The period end's own tests**: `$f374`, `$f3be`, `$118ba`/`$118f6` (endings: clock `>= $7080`, 20 days; `$24ba4`+10
   zero), the morale loss `$ed88` from `$24bb8`, and the report's counts (`$ef8c`) against `situation_report.png`.
3. **Relationships and recruitment**: the bios' friendships are prose (`$269d2`), so the data is elsewhere. Start from
   the team list `$2b16c` (who writes it) and the S.O.S / recruit paths (`$5784`, bio icons `$3054`/`$3024`).
4. Unit +12 (written by `$f5e2`; reader not found), the non-spread branch and `$2bb2e` (no unit uses it), node names
   (`$35d0`/`$217a` against `$25b4a`).
5. **3D pipeline** (the old item 1): `$18304` -> `$16d9c` per-cell projection (camera `$12c72..$12c7e`), draw list
   `$19ce2`/`$1d5a6`, polygon fill; proof by rendering one frame against the next snapshot (skill section 4b).
6. Terrain leftovers (`terrain.md` "Open"); Decisions icons 3/5; the instruction-counted VBL (`$a5e0` poke).

## Known traps

- The menu's fullscreen VBL outruns the instruction-counted VBL and starves the main loop (poked to `rte`).
- Options and character-screen snapshots catch the pointer mid-redraw: compare them with a 34-pixel tolerance.
- A `u <addr>` into the menu stops inside its packer stub before the depacked code exists: the drive pokes after a
  fixed `s 60000000` instead.
- `--all` listings lose sync at `$10840`, `$1fa0a`, `$19ce2`; the bytes before `$ec8c` are data.
- `stserver`'s `mouse` click does not register in this game (twice now: `d_decisions`, `d_options`), while the same REPL
  lines do. Make the click in the REPL and `snap` at the routine (`u c136`), then load that in `stserver`, as
  `gate_army.py` does. Cause not checked.
- The army moves only at a situation report: a long ski run with no report shows no army change.

## Next session

`/resume midwinter`. Start on item 1. Read `ai.md` section 3, then find a unit near Stark (`d_team.snap`: Stark at
(736, 2352), unit 12 shares his start), drive the ski view into its 200 x 200 window or poke the terrain target, and
break on `$c2f0`. Decode +6..+10 from what `$c4f2` builds in the `$2d47e` slots and gate it with `tools/stclient.py`.
