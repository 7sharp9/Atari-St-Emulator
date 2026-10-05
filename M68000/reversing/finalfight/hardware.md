# CPS1 hardware as Final Fight (`ffightuc`) sees it, from `cps1.cpp` 0.289

Source: `mamedev/mame` tag `mame0289`, fetched with `curl -sL https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/capcom/<file>` into `scratchpad/finalfight/src/` (`cps1.cpp` 15198 lines, `cps1.h` 370, `cps1_v.cpp` 3070, plus `ioport.cpp`, `inpttype.ipp`, `ioport.h`, `romentry.h` for string tables and ROM-loader macros). `cps1.cpp` ends in `GAME(` lines (14956 onward). Citations are `file:line` in those copies; `cps1.cpp` unless prefixed `v:` (`cps1_v.cpp`) or `h:` (`cps1.h`).
Evidence tags: **[S]** read in the source; **[R]** also confirmed in the `ffightuc` program ROM (`scratchpad/finalfight/ff_main.bin`, sha256 `8535dd51...`) by disassembly or an absolute-operand scan; **[I]** inferred, not read.

### Which set, which config

`ffightuc` is a clone of `ffight` (`GAME(..., ffightuc, ffight, cps1_10MHz, ffight, ...)`, 14992). It uses board 89624B-3, PAL S224B, IOB1, CPS-B-05 (v:66 header table, v:1802). Config lookup is by exact driver name with `strcmp`, with no clone chain (v:2049-2059), so `ffightuc` gets its own row: `{"ffightuc", CPS_B_05, mapper_S224B}` (v:1802). Do not read the `ffight`/`ffightu` row (`CPS_B_04`, v:1796-1799): CPS-B-04 puts layer control at `$80016e` and priority masks elsewhere, and this ROM writes layer control to `$800168` [R]. The input ports are shared (`INPUT_PORTS_START(ffight)`, 1598).

Machine config `cps1_10MHz` (3909-3946): 68000 at 10 MHz (3912), Z80 at 3.579545 MHz (3918), YM2151 at 3.579545 MHz (3940), OKIM6295 at 16 MHz/4/4 = 1 MHz with pin 7 initially high (3946), palette 0xc00 pens (3932), mono output. No EEPROM, no NVRAM device, no protection device, no `init` (`empty_init`, 14992): everything is switches (below). Screen: pixel clock 8 MHz, 512 x 262 total, visible 64..447 by 16..239 (h:39-47, 3925), about 59.63 Hz (h:30-37).

### Main 68000 map (`cps_state::main_map`, 577-594) [S]

| Range | Access | Handler | Line |
|---|---|---|---|
| `$000000-$3fffff` | read | `rom()` (region `maincpu`, `CODE_SIZE` 0x400000, 4063) | 579 |
| `$800000-$800007` | read | `portr("IN1")`, one 16-bit port; all four words read the same port [I] | 580 |
| `$800018-$80001f` | read | `cps1_dsw_r` (below) | 582 |
| `$800020-$800021` | read | `nopr()` | 583 |
| `$800030-$800037` | write | `cps1_coinctrl_w` | 584 |
| `$800100-$80013f` | write only | `cps1_cps_a_w`, shared `m_cps_a_regs` | 586 |
| `$800140-$80017f` | read/write | `cps1_cps_b_r` / `cps1_cps_b_w`, shared `m_cps_b_regs` | 589 |
| `$800180-$800187` | write | `cps1_soundlatch_w` (Z80 command) | 590 |
| `$800188-$80018f` | write | `cps1_soundlatch2_w` (Z80 "timer fade") | 591 |
| `$900000-$92ffff` | read/write | `ram().w(cps1_gfxram_w)`, shared `m_gfxram` (0x30000 bytes) | 592 |
| `$ff0000-$ffffff` | read/write | `ram()`, shared `m_mainram` | 593 |

Everything else is unmapped. No main-CPU bank switching exists in this driver [S]. The README's "`ff-32m.8h` bank ROM" is wrong: `ff-32m.8h` is `ROM_LOAD16_WORD_SWAP` at program offset `0x80000`, length `0x80000` (5746), so it is plain program ROM at `$080000-$0fffff`. `romentry.h:147` defines WORD_SWAP as `ROM_GROUPWORD | ROM_REVERSE` (a per-word byte swap for the big-endian CPU). Program ROMs `ffu_30.11f`/`ffu_35.11h` (`$000000`, even/odd bytes) and `ffu_31.12f`/`ffu_36.12h` (`$040000`) are `ROM_LOAD16_BYTE` (5742-5745; `romentry.h:145`, `ROM_SKIP(1)`). Region above `$100000` has no ROM loaded [S]; what a read returns there is not stated in the source.

`cps_state::cps1_dsw_r` (257-272) [S][R]: word offset 0 (`$800018`) returns `IN0 << 8 | 0xff`; offsets 1, 2, 3 (`$80001a`, `$80001c`, `$80001e`) return `DSWA`, `DSWB`, `DSWC` in the high byte, low byte `0xff`. So a byte read at `$800018/$80001a/$80001c/$80001e` gets IN0/DSWA/DSWB/DSWC. The ROM does exactly that at `$6f4-$74a`: three reads of `$800018` (into `84(A5)`, `86(A5)`), `$80001a` into `101(A5)`, `$80001c` into `100(A5)`, `$80001e` into `103(A5)`, each followed by `not.b` (active-low switches become active-high in RAM). `$800000` is read as a word at `$2b68` (`not.w`; low byte to `92(A5)` = P1, high byte to `94(A5)` = P2) [R].

`cps1_coinctrl_w` (316-328) [S]: acts only when the upper byte is written (`ACCESSING_BITS_8_15`); data bit 8 and 9 = coin counters 1, 2; bits 10 and 11 = coin lockouts 1, 2, **active when the bit is 0** (`BIT(~data,10)`); bit 15 is a comment only ("CPS-A custom reset?"). The ROM writes the byte at `$800030` (the upper byte), first `$80` then `$00` (`$5e898`, `$5e8a8`) and from `106(A5)` each VBL (`$6de`) [R]. Consequence [I]: coin insertion through MAME's inputs is ignored while the lockout bit is set; read `106(A5)` before blaming the injection.

### Interrupts [S]

Only one interrupt source feeds the 68000 for this set: `set_vblank_int("screen", cps1_interrupt)` (3916). `cps1_interrupt` (348-354) asserts `M68K_IRQ_IPL1` (353). The scanline-driven `raster_scanline` timer (372-397, `scantimer` at 3981) belongs to the CPS2/other configs, not `cps1_10MHz` [S]; its scanline 240 comment (394-396, "vblank interrupt on IPL1 (IRQ2)") and `CPS_VBSTART` 240 (h:47) give the same VBL line. IPL1 alone is level 2, so the vector is autovector 2 (`$68`) [I from the comment "IRQ2"; the ROM's `$68` -> `$53e` is in the README]. The line is cleared by a CPU-space read (`irqack_r`, 407-417, mapped by `cpu_space_map`, 419-421) that returns an autovector. 357: IPL2 (IRQ4) is "tied high on some early B boards (eg. 89624B-3)", this board, so the game cannot get a raster interrupt (the raster counter registers at CPS-B offsets 0x0e-0x12, `$80014e-$800152`, exist only for CPS-B-21/CPS2, v:308-314). Beyond the VBL interrupt, the only timing the driver adds is the one-frame object-RAM delay (below).

### CPS-A registers (write-only window `$800100-$80013f`) [S]

Index constants h:176-193; commentary v:242-300. The register index used by the code is `offset/2`.

| Addr | h: name | Meaning | ROM sets (reset `$5e8b0-$5e8e8`, VBL `$554-$6de`) [R] |
|---|---|---|---|
| `$800100` | `OBJ_BASE` | object RAM base, value x256 | reset `$9000` (`$900000`); VBL writes `158(A5)` (a variable, so double buffering) |
| `$800102` | `SCROLL1_BASE` | 8x8 layer map | `$9080` (`$908000`) |
| `$800104` | `SCROLL2_BASE` | 16x16 layer map | `$90c0` (`$90c000`) |
| `$800106` | `SCROLL3_BASE` | 32x32 layer map | `$9100` (`$910000`) |
| `$800108` | `OTHER_BASE` | rowscroll table | no absolute write in the ROM; MAME default `$9100` (v:2568) |
| `$80010a` | `PALETTE_BASE` | palette source; **writing it triggers the copy** | `$9140` (`$914000`), rewritten every VBL (`$594`) and at reset (`$5ec52`) |
| `$80010c`/`$80010e` | `SCROLL1_SCROLLX/Y` | scroll 1 | reset `$ffc0`, `0`; VBL `$5e8`.. |
| `$800110`/`$800112` | `SCROLL2_SCROLLX/Y` | scroll 2 | VBL |
| `$800114`/`$800116` | `SCROLL3_SCROLLX/Y` | scroll 3 | VBL |
| `$800118-$80011e` | `STARS1/2_SCROLLX/Y` | starfield, unused (no `stars` region for this set, h:126, v:3044) | ROM writes them anyway |
| `$800120` | `ROWSCROLL_OFFS` | start offset into the rowscroll table | VBL `74(A5)` |
| `$800122` | `VIDEOCONTROL` | bit 0 rowscroll on layer 2; bit 15 flip screen; bits 2 and 3 gate scroll2/scroll3 (v:2332-2333) | reset `$0e`; VBL builds it from `104/131/108(A5)` |

`cps1_base` (v:2099-2111) masks the base value x256 to the register's alignment and `& 0x3ffff`, so all bases index `$900000-$92ffff` gfx RAM; scroll alignment 0x4000 bytes, object and "other" 0x800 (`m_scroll_size`, `m_obj_size`, `m_other_size`, v:2538-2541), palette alignment 0x400. A write to `$80010a` calls `cps1_build_palette` immediately (v:2125-2126): for each of palette pages 0-5 enabled in the CPS-B palette-control register it copies 0x200 words, 12-bit colour plus a 4-bit brightness nibble in bits 15-12 (v:2630-2635, `bright = 0x0f + (nibble << 1)`). With control `$3f` (what the ROM writes, `$58c`) six pages = 0xc00 pens read from `$914000-$9157ff`. Page 0 sprites, 1 scroll1, 2 scroll2, 3 scroll3, 4-5 stars (v:348-353). Tile palette index = `(attr & 0x1f)` plus 0x20 (scroll1), 0x40 (scroll2), 0x60 (scroll3) palette lines (v:2464-2505); sprites use `attr & 0x1f` in page 0.

### CPS-B for `ffightuc`: `CPS_B_05` (v:490) [S]

`CPS1config` is h:61-103; the macro column order is v:485 ("CPSB ID, multiply protection, unknown, ctrl, priority masks, palctrl, layer enable masks"). Resolved row:

| Field | Value | Absolute address (`$800140` + id) | ROM evidence |
|---|---|---|---|
| ID check register (`cpsb_addr`/`cpsb_value`) | `0x20` returns `$0005` | `$800160` reads `$0005` (v:2140-2141) | [R] no absolute-long reference to `$800160` in the ROM; unconfirmed that the game reads it |
| multiply protection, unknown1-3 | all -1 (`__not_applicable__`) | none | none |
| layer control (`layer_control`) | `0x28` | `$800168` | [R] `$57e` writes it from `112(A5)` each VBL; reset writes `$12ea` (`$5e8b8`) |
| priority masks 0-3 | `0x2a, 0x2c, 0x2e, 0x30` | `$80016a, $80016c, $80016e, $800170` | [R] `$554-$56c` from `114,116,118,120(A5)` |
| palette control | `0x32` | `$800172` | [R] `$3f` at `$58c` and `$5ec4a` |
| layer enable masks `[0..4]` | `0x02, 0x08, 0x20, 0x14, 0x14` | within the layer register | scroll1 = bit 1, scroll2 = bit 3, scroll3 = bit 5; stars 0x14 (unused) |
| `in2_addr`, `in3_addr`, `out2_addr`, `bootleg_kludge` | 0 | none | |

Layer control semantics (v:316-329, 2332-2335, 2970-2999): bits 1-5 enable layers by the masks above (scroll2/3 also need `VIDEOCONTROL` bits 2/3); bits 6-7, 8-9, 10-11, 12-13 pick the layer drawn in slots 0..3, back to front, with value 0 = sprites, 1/2/3 = scroll1/2/3. The ROM's reset value `$12ea` [R] decodes to enables `0x2a` (all three tilemaps), slot order back to front scroll3, scroll2, sprites, scroll1. Priority masks give four per-tile-group masks (tile attribute bits 8-7, `group`, v:2467) of pens that draw over sprites (v:331-334, 2515-2531).

Reads of CPS-B at addresses without a handler case return `$ffff` (v:2179). Source-reading note [I]: unused `mult_result_lo/hi = -1` become `-1/2 == 0` in C++ integer division, so `offset == 0` (`$800140`) matches the multiply branch (v:2146-2152) and returns the register-0 square; the ROM has no `$800140` reference in the absolute-long scan, so this is harmless but not verified live.

### GFX mapper `mapper_S224B` (v:773-795) [S]

`bank_sizes = {0x8000, 0, 0, 0}` and `bank_mapper = mapper_S224B_table` (v:773, h:94-95). Ranges are in 8x8-tile units ("shift adjusted to be all in the same scale a 8x8 tiles", h:50-58). `gfxrom_bank_mapper` (v:2385-2425) shifts the tile code left by 1 for sprites and scroll2 (16x16), 0 for scroll1 (8x8), 3 for scroll3 (32x32), range-checks, and returns `(code & (bank_size - 1)) >> shift`; out-of-range returns -1 and the tile is drawn transparent.

| Layer | Range in 8x8 units (v:790-793) | Code range in that layer's own units | ROM byte range in the 0x200000 `gfx` region [computed: unit x 64 bytes] |
|---|---|---|---|
| sprites (16x16, gfx 2) | `0x0000-0x43ff` | `0x0000-0x21ff` | `$000000-$10ffff` |
| scroll1 (8x8) | `0x4400-0x4bff` | `0x4400-0x4bff` | `$110000-$12ffff` |
| scroll3 (32x32, gfx 3) | `0x4c00-0x5fff` | `0x0980-0x0bff` | `$130000-$17ffff` |
| scroll2 (16x16, gfx 2) | `0x6000-0x7fff` | `0x3000-0x3fff` | `$180000-$1fffff` |

Tile words in gfx RAM: two words per tile, code then attribute (v:2452-2512): code (scroll3 `& 0x3fff`), attribute bits 0-4 palette, bit 5 flip X, bit 6 flip Y, bits 7-8 priority group (`TILE_FLIPYX((attr & 0x60) >> 5)`). Tilemap sizes are 64 x 64 tiles for each layer (v:2546-2548) with these index mappers (v:2434-2451): scroll1 `(row & 0x1f) + ((col & 0x3f) << 5) + ((row & 0x20) << 6)`, scroll2 `(row & 0x0f) + ((col & 0x3f) << 4) + ((row & 0x30) << 6)`, scroll3 `(row & 0x07) + ((col & 0x3f) << 3) + ((row & 0x38) << 6)`. Scroll1 tiles pick between the two 8x8 layouts by `BIT(tile_index, 5)` (v:2462); the comment above `cps1_layout8x8` (3831-3835) says Final Fight hardware alternates 8x8 columns between the left and right halves of the 16x16 slot.

Sprites (v:2650-2680 comment, 2684-2716, 2720-2866) [S]: 4 words per entry in a 0x800-byte table, `x, y, code, attr`; attr bits 0-4 palette, 5 flip X, 6 flip Y, bits 8-11 and 12-15 = X and Y block size minus 1 (multi-tile sprites, code within a 16-wide row). The table ends at the first entry whose attr high byte is `0xff` (v:2705). Entries draw in table order. The table is latched into a buffer on the VBL edge (`cps1_objram_latch`, v:3063-3069, wired at 3928), described in the source as "sprites have to be delayed one frame". Background pen is `0xbff` (v:3042). **Correction by pixel comparison with MAME (`graphics.md`): the entries are drawn last to first (entry 0 on top), not first to last as `cps1_v.cpp:2740-2862` reads; the table a frame shows is the one at the OBJ base of the previous frame (the game alternates `$900000` and `$904000`).**

### GFX decode (`cps1.cpp:3837-3886`) and ROM loading [S]

`GFXDECODE_START(gfx_cps1)` (3881-3886) makes four sets from the same region: gfx 0 = `cps1_layout8x8` (left half), gfx 1 = `cps1_layout8x8_2` (right half), gfx 2 = `cps1_layout16x16`, gfx 3 = `cps1_layout32x32`; 0x80 colours each, 4 bits per pixel, plane offsets `{24, 16, 8, 0}` in all four.

| Layout | Line | Size | X offsets (bits) | Y stride | Tile bytes |
|---|---|---|---|---|---|
| 8x8 | 3837 | 8x8 | `STEP8(0,1)` | `STEP8(0, 4*16)` = 8 bytes | `64*8` bits = 64 |
| 8x8_2 | 3848 | 8x8 | `STEP8(32,1)` | 8 bytes | 64 |
| 16x16 | 3859 | 16x16 | `STEP8(0,1), STEP8(32,1)` | `STEP16(0, 4*16)` = 8 bytes | 128 |
| 32x32 | 3870 | 32x32 | `STEP8(0,1), (32,1), (64,1), (96,1)` | `STEP32(0, 4*32)` = 16 bytes | 512 |

A 64-bit word is one row of 16 pixels: bytes 0-3 hold pixels 0-7, bytes 4-7 pixels 8-15, and within each 4-byte group each byte is one bit plane (offsets 24, 16, 8, 0 select bytes 3, 2, 1, 0). `ROM_LOAD64_WORD` is `ROM_GROUPWORD | ROM_SKIP(6)` (`romentry.h:153`): 16-bit chunks, one per 8 bytes, no swap. For `ffightuc` (5749-5752): `ff-5m.7a` at byte offset 0, `ff-7m.9a` at 2, `ff-1m.3a` at 4, `ff-3m.5a` at 6, each `0x80000` long, filling `0x200000`. So 5m supplies bytes 0-1 and 7m bytes 2-3 of the left 8 pixels; 1m supplies bytes 4-5 and 3m bytes 6-7 of the right 8 pixels [I from the layout plus the loader macro, assuming the decoder numbers plane bits in memory byte order; confirm by decoding one known tile]. The mapper comment says "bank 0 = pin 16 (ROMs 1,3,5,7)" (777) and the header notes the PAL turns the top address bits into chip enables (v:402-414).

Sound: `ff_23.12b` (5755-5756) is `ROM_LOAD` 0x8000 bytes to Z80 `0x0000`, then `ROM_CONTINUE(0x10000, 0x8000)` reads the next 0x8000 bytes of the same file (`romentry.h:163`), so the file is 64 KiB (same CRC as parent `ff_09.12b`, comment at 5755). OKI samples: `ff_18.11c` at 0, `ff_19.12c` at `0x20000` (5759-5760), region `oki` of 0x40000 bytes.

### Z80 map (`cps_state::sub_map`, 631-642) [S]

| Range | Access | Device | Line |
|---|---|---|---|
| `$0000-$7fff` | read | ROM (first 32 KiB of `ff_23.12b`) | 633 |
| `$8000-$bfff` | read | `bankr(m_audiobank)`: two 16 KiB entries from audiocpu region offset `0x10000` (file offsets `0x8000` and `0xc000`), `configure_entries(0, 2, base+0x10000, 0x4000)` (3901) | 634 |
| `$d000-$d7ff` | read/write | RAM, 2 KiB | 635 |
| `$f000-$f001` | read/write | YM2151 | 636 |
| `$f002` | read/write | OKI6295 | 637 |
| `$f004` | write | `cps1_snd_bankswitch_w`: bank entry = data bit 0 (292-295) | 638 |
| `$f006` | write | `cps1_oki_pin7_w`: OKI pin 7 = data bit 0 (297-300) | 639 |
| `$f008` | read | soundlatch 0, the 68000's `$800180` byte (low byte if the low byte is accessed, else the high byte, 302-308) | 640 |
| `$f00a` | read | soundlatch 1, the 68000's `$800188` byte (low byte only, 310-314) | 641 |

The YM2151 IRQ line is the Z80's only interrupt input (`irq_handler().set_inputline(m_audiocpu, 0)`, 3941), and the two `GENERIC_LATCH_8` devices carry no callback (3937-3938) [S], so a command written to `$800180` does not interrupt the Z80 [I from absence]; the sound program must poll `$f008` from its YM timer interrupt. The 68000 does a word write to `$800180` (`$9b2`, `$9c4`) and to `$800188` (`$9ac`) [R]. Z80 PAL SOU1 equations are in the comment above `sub_map` (609-629).

### Inputs [S]

Ports are `IN0` (a byte, via `cps1_dsw_r`), `IN1` (a word), `DSWA`, `DSWB`, `DSWC` (`m_io_in` "IN%u", `m_dsw` "DSW%c", h:129-130). `INPUT_PORTS_START(ffight)` includes `cps1_3b` (829-858, 1599), then adds the DIP banks. All inputs are `IP_ACTIVE_LOW`. In a Lua session the tags are `:IN0`, `:IN1`, `:DSWA`, `:DSWB`, `:DSWC` and the field names are MAME's defaults: `Coin 1`, `Coin 2`, `Service 1`, `1 Player Start`, `2 Players Start`, `Service Mode`, `P1 Right`/`Left`/`Down`/`Up`, `P1 Button 1..3` (`inpttype.ipp:25, 34, 586, 598-599, 615`; `ioport.cpp:164`) [S for the strings; the leading colon is [I]].

| Port | Bit | Field | Line |
|---|---|---|---|
| `IN0` (byte at `$800018`) | `0x01` | Coin 1 | 831 |
| | `0x02` | Coin 2 | 832 |
| | `0x04` | Service 1 | 833 |
| | `0x08`, `0x80` | unknown | 834, 838 |
| | `0x10` | 1 Player Start | 835 |
| | `0x20` | 2 Players Start | 836 |
| | `0x40` | Service Mode (a toggle, `PORT_SERVICE`) | 837 |
| `IN1` (word at `$800000`), low byte = player 1 | `0x01` right, `0x02` left, `0x04` down, `0x08` up | 8-way | 841-844 |
| | `0x10` / `0x20` / `0x40` | Button 1 / 2 / 3 | 845-847 |
| `IN1` high byte = player 2 | `0x0100` right, `0x0200` left, `0x0400` down, `0x0800` up; `0x1000`/`0x2000`/`0x4000` buttons 1-3 | | 849-856 |

Bit `0x80` of each byte is unknown. A driver comment (1591-1596) says Final Fight button 3 (`0x40`) is undocumented, absent from the control panel, "probably a leftover", and escapes grabs and choke holds instantly; and that the hidden pattern tests are reached by turning the "Service Mode" dip on and holding P1 Button 1 (scroll/background test) or P1 Button 2 (object viewer) during the boot test. Attack and jump assignment to buttons 1 and 2 is not stated.

DIP banks (`INPUT_PORTS_START(ffight)`, 1598-1654; `DSWx` read through `cps1_dsw_r`). Values below are the bit patterns the port returns (low = switch on):

| Bank | Mask | Setting | Default | Line |
|---|---|---|---|---|
| `DSWA` | `0x07`, `0x38` | Coin A, Coin B (`CPS1_COINAGE_1`: `0x07`/`0x38` = 1 coin 1 credit; `0x00` = 4C/1C ... `0x03`/`0x18` = 1C/6C) | 1C/1C, 1C/1C | 1602, 755-773 |
| | `0x40` | "2 Coins to Start, 1 to Continue" (`0x40` Off) | Off | 1603 |
| | `0x80` | unused | 1 | 1606 |
| `DSWB` | `0x07` | Difficulty Level 1: `0x07` Easiest ... `0x04` Normal ... `0x00` Hardest | `0x04` | 1609-1617 |
| | `0x18` | Difficulty Level 2: `0x18` Easy, `0x10` Normal, `0x08` Hard, `0x00` Hardest | `0x10` | 1618-1622 |
| | `0x60` | Bonus Life: `0x60` 100k, `0x40` 200k, `0x20` 100k then every 200k, `0x00` none | `0x60` | 1623-1628 |
| `DSWC` | `0x03` | Lives: `0x00`=1, `0x03`=2, `0x02`=3, `0x01`=4 | 2 (`0x03`) | 1631-1635 |
| | `0x04` | Free Play: `0x04` Off, `0x00` On | Off | 1636-1638 |
| | `0x08` | "Freeze": `0x08` Off | Off | 1639-1641 |
| | `0x10` | Flip Screen: `0x10` Off | Off | 1642-1644 |
| | `0x20` | Demo Sounds: `0x20` Off, `0x00` On | On (`0x00`) | 1645-1647 |
| | `0x40` | Allow Continue: `0x40` No, `0x00` Yes | Yes (`0x00`) | 1648-1650 |
| | `0x80` | Game Mode: `0x80` Game, `0x00` Test | Game | 1651-1653 |

Default stored values from those lines: `DSWA` `0xff`, `DSWB` `0xf4`, `DSWC` `0x9f` (computed). To get free-play with the easiest game: set `DSWC` bit 2 to 0 (field "Free Play" = On), `DSWB` Difficulty Level 1 = Easiest (`0x07`) and Level 2 = Easy (`0x18`), optionally Lives = 4 (`0x01`): `DSWC` = `0x99`, `DSWB` = `0xff` (computed). Free Play is the setting that removes the coin step: the game then needs only `1 Player Start` (`IN0` `0x10`). Whether this ROM's attract loop reaches the start screen with free play on is not in the source. The ROM stores `DSWC` inverted in `103(A5)` (`$742-$74a`) [R], so the free-play bit is set (1) in that RAM byte when the switch is on.

### ffightuc-specific quirks [S unless tagged]

- `cps1_cps_b_r` returns `$0005` at `$800160` (the CPS-B-05 ID, v:2140-2141). The driver comment (v:2136-2138) says some games interrogate this at boot; this ROM has no absolute reference to it [R].
- The only 8x8-layer special case in the driver is the left/right half alternation per tile column (v:2457-2464), which the source ties to a Final Fight board with mixed USA/Japan gfx ROMs.
- No bootleg kludge (`bootleg_kludge` 0 for all `ffight*` rows except `ffightae` at v:1809).
- No protection beyond the CPS-B ID read-back; no EEPROM, no NVRAM, no multiply registers (CPS-B-05 has none).
- `ffightub` (`CPS_B_03`) and `ffightuc` (`CPS_B_05`) have different CPS-B rows (v:1801-1802); the README's note that `ffightub.zip` holds `ffightuc` ROMs stands, and the config used is by driver name, not by ROM content.

### Not found in the source, or only inferred

1. Which of buttons 1 and 2 is attack and which is jump: not in the driver (only button 3 and the test-mode buttons are described, 1591-1596); needs the ROM or play. The "Service Mode" dip in that comment is `IN0` `0x40` (837) or possibly `DSWC` bit 7 (1651); which one the boot test reads was not checked.
2. What a 68000 read of an unmapped range (`$100000-$7fffff`, `$800008-$800017`, `$800038-$8000ff`) or of the CPS-A window returns: the source maps no handler; MAME's default open-bus value is not in `cps1.cpp`.
3. The vector number for the VBL (`$68`): the source says IPL1 and "IRQ2"; the vector is the 68000's level-2 autovector by hardware convention, not stated in these files.
4. Whether `IN1`'s four-word window all read the same value: inferred from `portr` over an 8-byte range (580); the ROM reads only `$800000`.
5. Plane/byte order of the gfx decode (which ROM carries which bit plane): inferred from `gfx_layout` offsets plus `ROM_LOAD64_WORD`; verify by decoding one tile.
6. Lua tag spelling (`:IN0` etc.) and that field names are exactly MAME's default strings: strings read in `inpttype.ipp`/`ioport.cpp`; the tag prefix is the usual root-device form, not read.
7. Whether the ROM reads the CPS-B ID at `$800160`: no absolute-long reference found (an indirect read through a register or PC-relative form would not show in the scan).
8. The `-1/2 == 0` quirk of the unused multiply and ID registers (`$800140` reads) is source reading only.
9. The exact YM2151 and OKI sample-rate and mixing behaviour (OKI pin 7 effect on rate): not in `cps1.cpp`.
10. Raster or mid-frame register changes: the source gives none for this set, but the ROM's VBL handler runs all CPS-A/CPS-B writes at `$53e`, so a raster effect would show only as a second CPS-A writer, not yet censused.
