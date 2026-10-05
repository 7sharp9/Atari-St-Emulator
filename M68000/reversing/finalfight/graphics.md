# Final Fight graphics: decode, palettes, sheets, backgrounds

The CPS1 tile ROMs are decoded and proven against MAME: a Python renderer (`py/gfx/`, README there with the file table and runtimes) draws sprites, the three scroll layers and the priority masks from a gfx RAM
dump and the chip registers, and equals MAME's screenshot pixel for pixel. The PNGs in `gfx/` are the viewer set; everything else regenerates under `scratchpad/finalfight/gfx/out/` (`py/gfx/README.md`, "Order from scratch").

## Format

| item | layout (sources: `scratchpad/finalfight/src/cps1.cpp`, `cps1_v.cpp`) |
|---|---|
| gfx region | four ROMs (`ff-5m.7a`, `ff-7m.9a`, `ff-1m.3a`, `ff-3m.5a`), `ROM_LOAD64_WORD`: 16-bit chunks at byte 0, 2, 4, 6 of every 8, 0x200000 bytes (`cps1.cpp:5749-5752`) |
| pixels | 4 bits per pixel; MAME counts bits MSB first, so byte 3 of each 4-byte group is pixel bit 3 and byte 0 is bit 0 (`cps1.cpp:3837-3886`) |
| tiles | 16x16 (sprites and scroll 2): 128 bytes; 8x8 (scroll 1): 64 bytes in a left and a right half set chosen by map column parity; 32x32 (scroll 3): 512 bytes |
| code ranges | `mapper_S224B` in 8x8 units: sprites `$0000-$43ff`, scroll 1 `$4400-$4bff`, scroll 3 `$4c00-$5fff`, scroll 2 `$6000-$7fff` (`cps1_v.cpp:773-795`) |
| map entry | code word, attribute word: bits 0-4 palette line, 5 flip x, 6 flip y, 7-8 priority group; bits 15-10 are the game's terrain code and the chip never reads them (`placement.md`), so no masking is needed |
| palette | 12-bit RGB plus a brightness nibble: `bright = $0f + (nibble << 1)`, `r = R * $11 * bright / $2d` (integers); a page is copied from the `$80010a` source only when its palette-control bit is set |
| sprites | 4 words `x, y, code, attr`, block size in attr bits 8-15, table ends at the first entry with attr high byte `$ff` |

**Corrections to `hardware.md`'s source reading** (by pixel comparison): object entries are drawn **last to first**, entry 0 on top (first to last loses 272 to 4,003 pixels per busy frame; the cause is probably
`prio_transpen`, which is not in the source copies); frame k shows the object table that was in object RAM at the end of frame k-1, at frame k-1's OBJ base (the game alternates `$900000` and `$904000`); work RAM gives the
wrong layer-control value on the frame a change happens (two-stage register pipeline), so the dump script reads the chip's own registers; a stage-select map screen's stage byte is the stage about to start while its maps
are those of the stage just left.

## Proofs (reproduced this pass from `py/gfx/`)

| claim | result | command |
|---|---|---|
| composite of sprites, three layers and priority masks equals MAME's screenshot | 86,016 of 86,016 pixels in each of 7 frames (stage 0 grapple x3, enemies, boss area, map screen, stage 2) | `python prove.py` |
| each layer alone (layer control poked) | 86,016 of 86,016 in 5 frames per layer, sprites, scroll 1, 2 and 3 (20 frames) | `python prove.py` |
| total | 2,322,432 of 2,322,432 pixels | `python prove.py` (3 s) |
| palette word format against MAME's live pens | 3,072 of 3,072 in five dumps; 2,506 and 3,061 of 3,072 in two dumps taken during a fade | `python prove.py` |
| the frame composer `ffframes.build` (port of the game's object-list builder `$16910`) against the game's own routine run in MAME on a fake record | 4,572 of 4,572 tests word for word (1,143 frame blocks reachable from animation scripts x 4 mirror, palette and x-offset variants) | `python gate_oracle.py` (8 s) |
| the same port against live object RAM | 316 of 358 in-use records of 107 dumps found as contiguous runs; the 42 misses are records the game did not queue that frame | `python gate_frames.py` |
| pristine stage maps (the game's own column streamers `$62d6c $62db6 $62f88 $62d92 $62dec $630c8` called in MAME on a fake camera record) against 90 gameplay dumps | 151,230 of 153,678 tile entries equal (98.41%); the rest are runtime tile patches, blinking lights and doors | `python gate_pristine.py` (13 s) |

## Viewer set (`gfx/`)

| file | content |
|---|---|
| `00_proof_mame_vs_decode_diff.png` | MAME screenshot, this decode, and the difference mask (0 pixels differ) |
| `01_sprite_rom_0000-087f.png` | sprite ROM, codes `$0000-$087f` (all four sheets: `py/gfx/sheets.py`) |
| `02_scroll2_tile_rom.png`, `03_scroll3_tile_rom.png`, `04_scroll1_tile_rom_left_half_set.png` | the other layers' tile ROM (scroll 1's pictures are built from both half sets, so a half-set sheet looks interleaved) |
| `05_cody_animations.png`, `06_guy_animations.png`, `07_haggar_animations.png` | the three players, one row per animation script, labelled with the script address |
| `08_bred_animations.png`, `09_damnd_animations.png`, `10_sodom_animations.png` | a fighter and two bosses |
| `11_items.png`, `12_weapon_kind_0.png` | items and one weapon |
| `13_stage0_scroll2_pristine.png`, `14_stage0_scroll3_pristine.png`, `15_stage2_scroll2_pristine.png`, `16_stage3_scroll2_pristine.png` | whole-stage backgrounds as the game builds them (stage 2: street, bar interior, car park) |
| `17_stage1_screen_composite.png`, `18_stage0_scroll2_whole_map_dump.png` | one composed screen; the whole 64x64 scroll-2 map from a stage 0 dump |

Strips for every stage and layer (stage 0 3,328 px wide, stage 1 5,376, stage 2 4,096, stage 3 4,096, stage 4 9,216, stage 5 13,312, bonus 6 1,024, bonus 7 1,280) and 70 character sheets are in `scratchpad/finalfight/gfx/out/`
(`pristine/png/`, `chars/`); regenerate with `py/gfx/`.

## Not done or unproven

- Player sheets cover the animation scripts reached by direct `$3b1c`/`$3b10` calls (30 to 34 per player); scripts reached through pointer tables were not searched, so the full move set of `player.md` is larger. Which player
  and which fighter, boss, prop or weapon a script belongs to is by the handler region of the call site [I]; Cody and DAMND look right by eye.
- 28 of the 70 sheets have no dump with their owner live and use Cody's palette (marked "fallback" in the sheet title): SIMONS, ROLENTO, ABIGAIL, EL GADO, the G.ORIBER family, ROXY/POISON, weapons 3 and 5, some props.
- Held-weapon and second-record parts (`78(A0)`, `76(A0)`), held-fighter draws, and the debris and effects pools are not composed.
- Pristine strips of stages 4 and 6 are not validated (no gameplay dump; grey ramp). The bot's states `sb_s4` and `sb_s6` (`py/stage/`) are the way to take them: `py/gfx/gfxdump.lua` from those states. Stage 1 has dumps only in area 1.
- The pristine strips pick the best camera-y page per dump; which page matched is not recorded.
