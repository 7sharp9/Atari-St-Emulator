# Crude Buster graphics workstream (agent GFX): scripts, dumps, assets

Everything runs from this directory with `M68000/.venv/bin/python` (numpy, PIL). `proof.sh` re-runs every offline gate over the dumps below.

## Capture (MAME 0.289, own run dir per run)

| script | use |
|---|---|
| `run.sh <name> <plan|-> <frames> <stop> [pokes]` | `lua/dumpframes.lua` drive: per dumped frame a renderer-state file `dumps/<name>/fNNNNN.bin` (layout in the script header) plus MAME's own `run/<name>/snap/fNNNNN.png`; `ctl_log.txt` holds every tilemap-control write with its time. `LUA=writers.lua` / `LUA=emitcheck.lua` select the other drives |
| `lua/level_poke.sh <N> <name>` | POKED state: at frame 900 `$80046 = N-1` and bit 4 of `$80040` set (the game's own next-level path), bit cleared again at 1500 (the interlude `$172a` waits for it). Levels 1-5 only exist as this poke; level 0 (`a1`) and the attract run (`att`) are natural |
| `lua/dump_regions.lua` | MAME's own tiles1/tiles2/sprites regions (ground truth for the ROM interleave) |
| `lua/writers.lua` | census of the 68000 instruction (CURPC) writing each video region |
| `lua/emitcheck.lua` | every sprite-list entry written by the emitters, with the inputs they read |

Dump sets used: `att` (attract, no coin, frames 0-12000 step 37), `a1` (play1-style natural run, 0-2400 step 20), `lv1..lv5` (poked, 900-3600 step 20), `e0 e3 e5` (emitter logs), `w0..w5` (writer census).
The control registers are write-only on the bus: they come from write taps on `$b5000-$b500f` / `$b6000-$b600f` (installed before frame 1), `m_pri` from a tap on `$bc004` that mirrors `prot_w`, the sprite buffer from a tap on `$bc000` (copy of `$b0000-$b07ff` at the write, which is what `buffered_spriteram16` does).

## Python

| script | use |
|---|---|
| `py/gfxlib.py` | ROM assembly from the zip + layout decode (8x8 chars, 16x16 tiles); run it: compares with MAME's regions |
| `py/cbrender.py` | the renderer (tilemaps, rowscroll, colscroll, banking, sprites, palette, layer order, `m_pri`) |
| `py/ctllog.py` | rebuilds the control-register states of a frame from `ctl_log.txt`, including mid-frame band splits |
| `py/compare.py` | pixel compare against MAME snapshots |
| `py/sensitivity.py` | shows each rule matters (pri inverted, flash parity, unscaled palette) |
| `py/palsets.py`, `py/palcheck.py` | ROM palette sets and their check against live palette RAM; writes `assets/palette_sets.png`, `assets/palettes_by_level.png` |
| `py/emitcheck.py` | sprite emitter model vs live list entries |
| `py/levelmaps.py`, `py/levelcheck.py`, `py/levelstrips.py` | static level maps from ROM, check vs live tilemap RAM, `assets/levels/*` |
| `py/romtables.py` | `data/messages.txt`, `data/level_tables.txt`, `data/anim_index.txt` |
| `py/animatlas.py` | actor animation frames composed from `$30000`: `assets/anim_*.png` |
| `py/assets.py`, `py/frames_assets.py` | tile/sprite sheets, side-by-side frames, layer breakdown |
| `py/xref.py` | callers/operand references in `scratchpad/crudebuster/all_lin.txt` |
| `gfx.sym` | routine names from their bodies |

## Assets

`assets/chars_4000-4fff.png` (char ROM half, 64x64 chars at 2x), `tiles1_*.png`, `tiles2_*.png` (1024 tiles each, 32x32 grid), `sprites_*.png` (10 sheets of 1024), all coloured with the brightest palette each code was seen with in the dumps (grey for unseen); `palette_sets.png`, `palettes_by_level.png`; `frames/*.png` (MAME | renderer | difference, left to right) and `frames/layers_lv3_f2400.png`; `levels/level<N>_A.png` (layer A strip from ROM) and `levels/level<N>_composite.png` (layer A over the live B/C pages, not parallax-correct); `anim_types_state0.png`, `anim_type0.png`.
