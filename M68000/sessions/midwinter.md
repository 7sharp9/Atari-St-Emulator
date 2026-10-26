# Midwinter: handoff

Updated 2026-10-26 by the first Midwinter session.

## Resume point

- Last commit of this workstream: see `git log -- M68000/reversing/midwinter` (first commit: setup, drive, architecture).
- Working data: `M68000/scratchpad/midwinter/` (indexed in `scratchpad/ANCHORS.md`). Rebuild: unzip
  `~/Library/CloudStorage/Dropbox/Daves/ST games/Zuul #67.zip`, `tools/msa2st.py ZUUL067.MSA zuul067.st`,
  `tools/extract_disk.py zuul067.st files`, `tools/lsd_depack.py --all files unpacked`, then the README's two commands
  (cold boot 20M, `drive.txt`).
- Start from: `scratchpad/midwinter/run1/d_ski.snap` (first-person ski view, Capt Stark, 06:00) or `d_decisions.snap`.
  Every resume needs `--disk-a scratchpad/midwinter/zuul067.st` (the game loads files during play).
- Uncommitted work left behind: none of this workstream.

## Proven so far

- Boot to the 3D view, deterministic (`drive.txt`, six milestones byte-identical over two runs).
- `tools/lsd_depack.py` decodes all 63 files; `1.1` equals RAM at entry except 14 crack-patch runs (README "Packing").
- Architecture skeleton with census counts (`architecture.md`): vectors, VBL fan-out, screen graph, map loop, 3D frame
  `$14e00` (7 frames per 100 emulator VBLs on `d_ski`, 5 on `s_3d_6`), cracked FAT12 loader.

## Open, in priority order

1. **Terrain**: where the height field lives and how it is generated (fractal/seeded or stored in a data file).
   Start at the landscape render `$18304` and its callees `$16d9c`, `$16cf6`, `$17f20`, `$170e6`, and at the map
   picture (file 27.2 -> `$4a104`). Proof: rebuild the height field (or the map picture) from the seed/file and match
   RAM byte for byte.
2. **3D pipeline**: view rotation `$1d77a` (sine table `$1c6bc`), projection, the draw list `$19ce2`/`$1d5a6`, the
   polygon filler (the inner routines `$19f20`/`$19ed4`/`$17fa0`/`$1b0e4`). Proof: a Python renderer of one frame against
   the screen of `d_ski` (section 4b of the skill).
3. **People and AI**: the character records (inferred: `$2b194`, stride `$4a`, indexed by the current character `96(A6)` at `$3192`), relationships and recruitment,
   enemy movement. Name fields from the bio screen text.
4. Decisions icons 3 (snipe `$3dd2`) and 5 (`$5062`), S.O.S, other vehicles; the computed file numbers (`bp 500` log).
5. Emulator: the REPL `mouse down` gap and the ACIA re-read gap (Known traps); the instruction-counted VBL.

## Known traps

- `mouse down l` sends no packet in relative mouse mode; use `kbd fa 00 00` / `kbd f8 00 00`.
- The ACIA data register is popped on read: the boot ticker and the menu key loop never see a key (poked in `drive.txt`).
- The menu's fullscreen VBL outruns the instruction-counted VBL and starves the main loop (poked to `rte`).
- A `u <addr>` into the menu stops inside its packer stub before the depacked code exists: the drive pokes after a
  fixed `s 60000000` instead.
- `--all` listings lose sync at `$10840`, `$1fa0a`, `$19ce2`.

## Next session

`/resume midwinter`. Start on the terrain (item 1): census `$18304`'s callees on `d_ski`, find the height-field
buffer and its writer, and decide whether the terrain is generated or loaded. That decides whether the terrain work is a
procedural-generation proof or a file-format proof.
