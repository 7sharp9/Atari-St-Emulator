# Midwinter: handoff

Updated 2026-10-26 by the session that proved the terrain generator (work commit `ecccb3d`, tool `012d5dd`).

## Resume point

- Last commit of this workstream: `012d5dd` (tools: `find_files_in_ram.py`; loader pre-switch loads); the terrain work is `ecccb3d`.
- Working data: `M68000/scratchpad/midwinter/` (indexed in `scratchpad/ANCHORS.md`). Rebuild: unzip
  `~/Library/CloudStorage/Dropbox/Daves/ST games/Zuul #67.zip`, `tools/msa2st.py ZUUL067.MSA zuul067.st`,
  `tools/extract_disk.py zuul067.st files`, `tools/lsd_depack.py --all files unpacked`, then the README's two commands
  (cold boot 20M, `drive.txt`).
- Start from: `scratchpad/midwinter/d_ski.snap` (first-person ski view, Capt Stark, 06:00, standing still at 0 mph) or
  `d_decisions.snap`. `scratchpad/midwinter/terrain/gate/` holds the generator and post-pass entry/return snapshots
  (rebuilt by every run of the terrain gate). Every resume needs `--disk-a scratchpad/midwinter/zuul067.st`.
- Uncommitted work left behind: none of this workstream (the root `Cadaver/` is untracked and not Midwinter's).

## Proven so far

- Boot to the 3D view, deterministic (`drive.txt`, six milestones byte-identical over two runs; the ski entry replayed
  from `d_decisions` gives `d_ski.snap` byte for byte). Only poke left: the menu VBL stub `$a5e0`.
- `tools/lsd_depack.py` decodes all 63 files; `1.1` equals RAM at entry except 14 crack-patch runs (README "Packing").
- Architecture skeleton with census counts (`architecture.md`). The loader opens number+10 during play (`$258a2`
  table pointer); the load tables there give numbers, with the files they open.
- Terrain (`terrain.md`): file 37.2 is the island's 50 x 50 height grid; `$19962` refines it by five diamond-square
  subdivisions (`$2ca6`/`$285a`, displacement hashed from the parents' seed words) into the 100 x 100 grid at `$404c4`
  around the target `$19cd4/$19cd6`; `$1991a` heights, `$1d1d2` building pads, `$197ec` triangle shading
  (`$198d8` exact isqrt). `py/terrain/gate_terrain.py` (also `tools/gates.py run midwinter`, 7 s): generator
  70000/70000 cells over 7 windows, post-passes 10000/10000.

## Open, in priority order

1. **3D pipeline**: the landscape render `$18304` -> `$16d9c` (per-cell projection: camera `$12c72..$12c7e`, matrix
   words `$17210..$17216`, screen centre `$17218/$1721a`, clip bounds `$171f0..$171f6`, rows stepped with
   `lea -400(A0)` from `[$12c80]`), `$16cf6` (eight passes through `$161f6..$16bfa`), `$17f20`, `$170e6`; the draw
   list `$19ce2`/`$1d5a6`; the polygon fill (`$19f20`/`$19ed4`/`$17fa0`/`$1b0e4`). The terrain model now supplies the
   input grid. Proof: a Python renderer of one frame against the screen of the next snapshot (skill section 4b).
2. **Terrain leftovers** (`terrain.md` "Open"): what clears the re-centre latch `$14efa`; the `$14cc0` rebuild; the
   feature list `$2a150` and object table `$70010` (`$1cf1c`, the input to the building pads, which the gate takes from
   the game's RAM); the `$3ddb4` table (`$1ce4a`); the map render `$2bc2` against `map.png`.
3. **People and AI**: the character records (inferred: `$2b194`, stride `$4a`, indexed by the current character
   `96(A6)` at `$3192`), relationships and recruitment, enemy movement. Name fields from the bio screen text.
4. Decisions icons 3 (snipe `$3dd2`) and 5 (`$5062`), S.O.S, other vehicles; the computed file numbers (`bp 500` log).
5. Emulator: the instruction-counted VBL (the menu's `$a5e0` stub is the last poke in `drive.txt`).

## Known traps

- The menu's fullscreen VBL outruns the instruction-counted VBL and starves the main loop (poked to `rte`).
- Options and character-screen snapshots catch the pointer mid-redraw: compare them with a 34-pixel tolerance, the
  other four milestones exactly.
- A `u <addr>` into the menu stops inside its packer stub before the depacked code exists: the drive pokes after a
  fixed `s 60000000` instead.
- `--all` listings lose sync at `$10840`, `$1fa0a`, `$19ce2`.
- `d_ski` stands still (0 mph): a watch over it sees no terrain rebuild. Moving needs vehicle input, not yet driven.
- One trial: from `d_decisions.snap` loaded in the `stserver` MCP, the drive's `mouse move -31 -2` / `down l` / `up l`
  with the same steps did not register the click (PC stayed in `$bd18`, no pointer on the render), while the REPL
  replay of the same lines did. Cause not checked; drive clicks through the REPL until it is.

## Next session

`/resume midwinter`. Start on the 3D pipeline (item 1): transcribe `$16d9c`'s per-cell transform on `d_ski` (its
inputs are the terrain grid and the camera block `$12c72..$12c7e`), check it against the buffers `$12ce6..$12cf2` it
fills with a `callcap`, then follow the draw list to the polygon fill and score one frame against the next snapshot.
