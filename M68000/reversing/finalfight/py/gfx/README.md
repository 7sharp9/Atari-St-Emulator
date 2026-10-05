# Final Fight graphics: tile ROM decode, palettes, sheets, characters, backgrounds

Scripts for decoding and dumping the CPS1 graphics of `ffightuc` (gfx ROMs of `ffight.zip`). Everything is numpy/Pillow
(`M68000/.venv/bin/python`); MAME is used only through `ffrun.sh` to take dumps and as an oracle. Outputs go to
`scratchpad/finalfight/gfx/out/` (sheets, chars, bg, pristine, layers, viewer), dumps to `scratchpad/finalfight/gfx/dump/`.
Run the scripts from this directory (`cd M68000/reversing/finalfight/py/gfx`); paths come from `__file__`.

## What is decoded, and the layouts (source lines in `scratchpad/finalfight/src/`)

| item | layout | source |
|---|---|---|
| gfx region | 4 ROMs, `ROM_LOAD64_WORD`: 16-bit chunks, `ff-5m.7a` at byte 0, `ff-7m.9a` at 2, `ff-1m.3a` at 4, `ff-3m.5a` at 6 of every 8 bytes, 0x200000 bytes | `cps1.cpp:5749-5752` |
| pixel decode | 4 bits/pixel, plane offsets `{24,16,8,0}`: MAME numbers bits MSB first, so byte 3 of each 4-byte group is pixel bit 3 and byte 0 is bit 0; pixel x of the group is bit `7-x` | `cps1.cpp:3837-3886` |
| 16x16 (sprites, scroll 2) | 8 bytes per row (pixels 0-7 in bytes 0-3, 8-15 in bytes 4-7), 128 bytes per tile | `cps1.cpp:3859` |
| 8x8 (scroll 1) | 8 bytes per row, 4 used: left half set (gfx 0) bytes 0-3, right half set (gfx 1) bytes 4-7; the map picks the set by `BIT(tile_index,5)` = map column parity | `cps1.cpp:3837-3858`, `cps1_v.cpp:2457-2464` |
| 32x32 (scroll 3) | 16 bytes per row (4 groups), 512 bytes per tile | `cps1.cpp:3870` |
| tile code to ROM tile | `mapper_S224B`: sprites `$0000-$43ff`, scroll 1 `$4400-$4bff`, scroll 3 `$4c00-$5fff`, scroll 2 `$6000-$7fff` in 8x8 units; code is shifted by 1 (16x16), 0 (8x8), 3 (32x32) | `cps1_v.cpp:773-795`, `2385-2425` |
| tile map entry | code word, attribute word; attr bits 0-4 palette line, 5 flip x, 6 flip y, 7-8 priority group; bits 15-10 are the game's terrain code and are ignored by the video (MAME never reads them, so no masking is needed). Scan orders per layer | `cps1_v.cpp:2434-2512` |
| palette | 12-bit RGB plus a brightness nibble: `bright = 0x0f + (nibble << 1)`, `r = R * 0x11 * bright / 0x2d` (integer); page p (0-5) copied from the source at CPS-A `$80010a` when palette control bit p is set; line of a tile = `(attr & 0x1f)` + `$20` (scroll 1), `$40` (2), `$60` (3), sprites page 0 | `cps1_v.cpp:2612-2650`, `2125` |
| sprites | 4 words `x, y, code, attr` (attr 0-4 palette, 5 flip x, 6 flip y, 8-11 / 12-15 = x / y block size - 1), table ends at the first entry with attr high byte `$ff`, clip to bitmap x 64..447, y 16..239 | `cps1_v.cpp:2684-2716`, `2720-2862` |
| layers | layer control `$800168` bits 6-13 pick the layers back to front (0 sprites, 1-3 scroll 1-3), bits 1/3/5 enable scroll 1/2/3 (2 and 3 also need video control bits 2/3); priority masks `$80016a-$800170` per tile group say which pens go in front of the sprites drawn just after that layer | `cps1_v.cpp:2970-2999`, `3001-3040` |

`cpsgfx.py` has the decode (`Gfx`), `bank_map`, `build_palette`, `render_tilemap`/`render_tiles`, `compose` (one frame),
`sprite_tiles`, `render_entries`, `Regs`. `ffframes.py` ports the game's object-list builder (below).

### Corrections to the brief and to `hardware.md`

- **Entry 0 of the object list is on top**: entries are drawn last to first. The source copy (`cps1_v.cpp:2740-2862`) reads
  first to last; drawn that way 272 to 4,003 pixels per frame differ from MAME's screenshot in every frame with overlapping
  sprites, drawn last to first all 86,016 match (`prove.py` ablation). The cause is probably `prio_transpen`'s
  priority update (not in the source copies); the empirical rule is what `compose` implements.
- **The object table is one frame old, and double-buffered by the game**: frame k shows the table that was in object RAM at the end of
  frame k-1, at the OBJ base register of frame k-1 (`$900000` and `$904000` alternate, `158(A5)`; `frame.md`). A single dump
  therefore cannot reproduce its own screenshot's sprites exactly; two consecutive frames can (`gfxdump.lua` dumps
  several).
- **The palette copy happens at the VBL write of `$80010a`**, so the palette in gfx RAM at a dump can be newer than the one the
  chip drew with when the game fades or flashes: 3072 of 3072 pens equal in 5 dumps, 2506 and 3061 of 3072 in two dumps taken
  during a fade (`prove.py`).
- The CPS-B priority masks and layer control reach the chip through a two-stage pipeline (`112(A5)` <- `110(A5)`, `$574-$57e`); work RAM
  alone gives the wrong value on the frame a change happens, hence `gfxdump.lua` reads the chip's own registers
  (`m_cps_a_regs`/`m_cps_b_regs` shares).
- The stage byte `190(A5)` of a stage-select map screen is the stage about to start, but the maps and camera values in RAM are
  those of the stage just left; `backgrounds.is_map_screen` drops those dumps (18 of 107).

## Proofs (all rerun by the commands below)

| claim | evidence | command |
|---|---|---|
| tile decode + layers + priority + sprite rules | full composite equals MAME's screenshot pixel for pixel: 86,016 of 86,016 in all 7 frames compared (`gp` 3 frames: stage 0 grapple; `en` 1: enemies; `bo` 1: stage 0 boss area; `s1` 1: stage-select map; `st2` 1: stage 2); with the 20 layer frames below, 27 frames and 2,322,432 of 2,322,432 pixels | `python prove.py` |
| each layer alone | layer-control words poked so only sprites / scroll 1 / scroll 2 / scroll 3 is enabled: 86,016 of 86,016 in 5 frames each (20 frames); non-background pixels in those shots 3,851 / 7,312 / 83,151 / 60,181 | `python prove.py` |
| palette word format | `build_palette` of gfx RAM equals MAME's live palette device in 3072 of 3072 pens (`en` 2 frames, `bo` 2, `gp`); differences only where the game rewrote the palette after the copy (2 dumps, above) | `python prove.py` |
| ablation | `en` 2: both sprite rules 86,016; entries first to last 82,008; this frame's table at this frame's base 85,218. `bo` 2: 86,016 / 85,470 / 82,013 | `python prove.py` |
| frame composer (`ffframes.build`, port of ROM `$16910`) | word for word equal to the game's own routine run in MAME on a fake record: 4,572 of 4,572 tests (1,143 frame blocks reachable from the animation scripts x 4 mirror/palette/x-offset variants), covering all 7 layout kinds and the big-sprite path | `python scan_scripts.py; python gate_oracle.py` (7 s of MAME) |
| the same port against live object RAM | 316 of 358 in-use records of 107 dumps appear as a contiguous run in an object buffer; the 42 misses are records the game did not queue that frame (map screens, culled), not mismatches inside a run | `python gate_frames.py` |
| pristine maps | maps produced by the game's own streaming routines equal 151,230 of 153,678 (98.41 %) of the tile entries in the trusted windows of 90 gameplay dumps (stage 0 scroll 2 97.64 % of 97,206, scroll 3 100 %; stage 1 scroll 2 100 %; stage 2 99.4 % / 99.2 %; stage 3 100 % / 96.0 %; stages 5 and 7 100 %); the rest are tile patches, blinking lights, doors and wall panels the run changed | `python bgmaps.py; python gate_pristine.py` |

## Files

| file | what it does | runtime |
|---|---|---|
| `cpsgfx.py` | decode, mapper, palette, tilemap and sprite renderers, `compose`, `Regs` (library) | |
| `ffframes.py` | `build()` (port of `$16910`), `script()` (animation scripts `$3b1c`/`$3b3c`) (library) | |
| `sheetlib.py` | fonts, drawing helpers, `owner_of(addr)`: handler region of a code address (tables `$5824 $5a52 $598c $59ce $5ff0 $5872 $601e`) | |
| `gfxdump.lua`, `run_dump.sh` | load a state, dump gfx RAM, work RAM, CPS-A/B registers, live palette and a screenshot for N frames; `FF_POKE="addr=val,..."` pokes u16s after the load | 4 s |
| `make_proof_dumps.sh` | the dump sets `prove.py` reads | 40 s |
| `dump_states.py` | one fresh dump per distinct saved state under `scratchpad/finalfight` (not `stage/`): 92 states | 6 min |
| `prove.py` | the decode proofs above | 30 s |
| `framecap.lua`, `gate_oracle.py` | the game's `$16910` as oracle for the frame composer | 7 s |
| `scan_scripts.py` | finds the 726 animation script starts (calls of `$3b1c`/`$3b10`: `lea`, `movea.l #`, the 3-pointer player thunk, the per-character word-table thunk); 602 pass `frame_ok` | 1 s |
| `gate_frames.py` | composer against live object RAM | 20 s |
| `census.py` | palette line and dump per tile code over 107 distinct gfx RAM dumps (`usage.pkl`) | 1 s |
| `sheets.py` | whole tile ROM per layer type, labelled by the game's own codes: `sheets/sprites_0..3.png` (4 x 34 rows x 64), `scroll2.png`, `scroll3.png`, `scroll1_left.png`, `scroll1_right.png` | 15 s |
| `chars.py` | animation-script sheets: Guy, Cody, Haggar (30-34 scripts each), 17 fighters, bosses DAMND, SODOM, EDI.E, ROLENTO, ABIGAIL, BELGER, props, weapons, items, pool 8 scenery; `chars/*.png` | 15 s |
| `backgrounds.py` | scroll 2 / 3 strips per stage assembled from the dumps (trusted windows), coverage table, disagreement counts; `bg/*.png` | 4 s |
| `layers_full.py` | one dump per stage: on-screen composite and the whole 64 x 64 scroll-2 and scroll-3 maps with the trusted window marked; `layers/*.png` | 5 s |
| `callscript.lua`, `bgmaps.py`, `gate_pristine.py`, `render_pristine.py` | pristine maps of stages 0-7 by calling the game's streaming routines; npy arrays and strips in `pristine/` | 35 s |
| `viewer.py` | the 19-file viewer set in `viewer/` (all under 400 KB, largest 398 KB) | 5 s |

Order from scratch: `make_proof_dumps.sh`, `dump_states.py` (needs the states copied into `run/sta/ffightuc/` by it), `census.py`,
`scan_scripts.py`, `sheets.py`, `chars.py`, `backgrounds.py`, `layers_full.py`, `bgmaps.py`, `render_pristine.py`, `gate_*.py`, `prove.py`, `viewer.py`.
Gotcha: `ffrun.sh`'s `-seconds_to_run` counts emulated seconds; the scripts exit by themselves, 400 is enough for every state here. The dump
screenshots go to `scratchpad/finalfight/run/snap/` (`gp_*.png`, `en_*.png`, ...), which `prove.py` reads.

## Sprite frames and animations

The frame block format and the seven layout kinds are in `ffframes.py`'s docstring (ROM `$016910-$016e38`; grid table `$64770`: 8 bytes per grid
id, tile count and offset list). A frame is `ffframes.build(block, ...)`; a script is `{word offset, word duration * 256 + flags}`
entries, a negative timer word closes it with a loop offset. Player scripts: 30 thunks `movea.l 6(PC,D0.w),A1 / jmp $3b1c` (`$c3c4-$c840`,
three pointers: Guy, Cody, Haggar) plus the direct scripts inside each character's data block (Guy `$fc4c-$103fc`, Cody `$1127a-$12284`,
Haggar `$12dd4-$1416c`, by address range, [I] for the split points). Fighters: the `$3b10` per-character word tables (kind 0: BRED, DUG,
JAKE, SIMONS; `ai.md`), named by the call site's handler region. Palettes come from a dump in which the owner is live
(`chars.live_census`); owners that never appeared in any dump (SIMONS, ROLENTO, ABIGAIL, EL GADO, G.ORIBER family, ROXY/POISON, weapons 3 and 5,
props 2, 4, 8, ...) are drawn with Cody's dump palette, which is wrong for them (28 of the 70 sheets, marked "fallback" in the title line).
The frame's own palette line (block attr bits 0-4) is used, as the game does.

## Backgrounds

A dump holds the 64 x 64 map of each layer, but the game streams columns: the area start routines fill 42 columns of 16 px (scroll 2) from 9
columns left of the camera and 22 columns of 32 px (scroll 3) from 5 left of camera 2; one more column streams in when bit 4 of the camera x
changes (`transitions.md`, `$62b76-$62f88`, `$62c06`, `$62c66`). So a dump is trusted for world columns `[camcol-9, camcol+33)` (scroll 2)
and `[camcol3-5, camcol3+17)` (scroll 3); camcol = the camera x copy `46(A5)` / `54(A5)` (the register holds that minus `$40`) divided
by the tile size. Rows: the visible band only (map rows 48-63 plus margin for scroll 2). Coverage from the 89 gameplay dumps (`backgrounds.py`):

| stage | scroll 2 world x covered | scroll 3 | notes |
|---|---|---|---|
| 0 | `$0-$d10` (69 dumps; 209 columns claimed twice, 49 disagree: animated patches, concentrated on screen columns 7-19 of the window, 3 % at its edges) | `$0-$300`, `$700-$a60` | areas 0, 1 (subway), 2 |
| 1 | `$800-$b80` | `$4e20-$50e0`, `$d720-$d9e0` (camera 2 x runs far from the world x here) | area 1 only; no dump of areas 0, 2, 3 |
| 2 | `$0-$500`, `$670-$9c0` | `$0-$600`, `$8a0-$ba0` | |
| 3 | `$690-$930` | `$2e0-$5a0` | one dump |
| 4 | none (only the map screen) | none | |
| 5 | `$0-$210` | `$0-$220` | |
| 6 (bonus) | none (the `sb_s6` dump is the map screen) | none | |
| 7 (bonus) | `$0-$320` | `$0-$320` | |
| 8 | `$370-$610` (the ending scene dump `sb_end`) | `$160-$420` | |

Everything else is not covered by a dump. The **pristine maps** close that: `bgmaps.py` runs the game's own column streamers for every world
column of stages 0-7 (`$62d6c`, `$62db6`, `$62f88`, `$62d92`, `$62dec`, `$630c8`, area start order) on a fake camera record, so they hold
the full stage as the game builds it, without runtime patches (strips `pristine/png/stage<N>_scroll<L>_y<Y>.png`, npy arrays in `pristine/`).
Camera y pages: scroll 2 y 0 for every stage and y `$800` for stages 3 and 5 (the map rows alias, the block rows differ); scroll 3 y 0,
`$e0` (stage 0), 0, `$100`, `$210` (stage 1), `$200` (stage 5), `$e` (stage 6). Widths: stage 0 3,328 px of scroll 2, stage 1 5,376, stage 2 4,096, stage 3
4,096, stage 4 9,216, stage 5 13,312, bonus 6 1,024, bonus 7 1,280; scroll 3 wider (the x ranges in `bgmaps.py` are generous: columns past the end of a stage
are the chunk table repeating or blank). Stages 4 and 6 have no gameplay dump, so their strips use a grey ramp, not the game's palette; the pages are tried per dump and the best taken, so which page matched is not recorded. Palettes in the other strips come from
the nearest gameplay dump of the stage, so a seam can show where the area palette changes.

A fresh dump at another camera x is `gfxdump.lua` from any state, after poking the camera record (`1042(A5)`, `1046(A5)` with the limits `1078/1080(A5)`)
and waiting for the streamer; the boss and stage states in `run/sta/ffightuc/` and `transitions.md`'s area-skip recipe (`297(A5) = 1`, `191(A5)`) reach
other areas. The pristine route needs no dump at all.

## Not done, not proven

- No stage-select map or ending scene decode beyond what the layers show; scroll 1 sheet shows 8x8 tiles in the two half sets, big pictures (logos, the
  map) are built from both and look interleaved in the sheet (view them in `layers/` instead).
- Guy/Haggar animation scripts reached by other means than `$3b1c`/`$3b10` calls (jump tables of script pointers) were not searched; the sheets
  list 30-34 scripts per player, the move set of `player.md` probably has more.
- Sprite sheet colouring for tiles never drawn in a dump and not used by an owner with a live palette is grey (2,026 of 8,704 sprite tiles).
- Parts lists (`78(A0)`: weapons held, second records `76(A0)`) and the debris/effects pools are not composed; held-fighter draws (`64(A0)` set) are not.
- The oracle gate proves the frame builder, not that each script belongs to the character it is filed under: Cody's and DAMND's sheets
  look right by eye, the player direct-script split by address and the kind-region naming of other owners are [I].
- Pristine maps were validated only on stages with gameplay dumps (0, 1, 2, 3, 5, 7).
