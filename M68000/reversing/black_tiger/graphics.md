# Black Tiger: graphics (engine, tiles, sprites, pictures, screens)

Addresses are runtime absolute (`dotnet exec bin/Debug/net8.0/M68000.dll`, disk `bt_auto.st`). Scripts: `py/graphics/` (table in its
README); data, snapshots and logs: `scratchpad/black_tiger/agents/graphics/` (`snaps/`, `boss/`, `screens/`, `shop/`, `gates/`, `res_a300.asm`
= the resident BL_TIGER part, `disassemble.py --snap play_start.snap --all 0xa300 0xc470`). "Gate" lines give the match count of a live check;
INFERRED marks what is read or guessed only. The `trap #3` services are listed in `system.md` 7; this document owns the drawing ones.
COMMAND.PRG is relocated at load (`system.md` 1): its file offsets do not equal runtime addresses, always use the runtime ones
(strings, for example, sit `$22c` below where a file offset calculation puts them).

Images (`img/graphics/`, all palette PNGs):

| image | content |
|---|---|
| `level_0_map.png` .. `level_7_map.png` | whole-level background reconstructions from map `n` + its tileset, in the palette the game shows |
| `tiles_T0.png`, `tiles_T2.png` .. `tiles_T7.png` | the seven tilesets, 16 per row, 1 px grid |
| `sprites_BTSPR_banks.png` | the 13 distinct BTSPR banks, every frame slot, level-0 palette |
| `sprites_BTMAN_hero.png` | the 23 hero frames |
| `sprites_BTA_BTB_bosses.png` | BTA (dragon, 9 frames of 128x64) and BTB (demon, 8 frames of 64x64) |
| `sprites_weapon_overlays.png` | hero weapon overlay sprites: 3 families x 5 levels |
| `pics_BTCLIPS.png`, `pics_BTOBJ.png` | the two picture banks (colour 0 transparent, level-0 palette; the shop scene BTCLIPS 17 is in its own colours in `screen_shop.png`) |
| `font_8x8.png` | the 224-glyph text font at `$bb9e` |
| `screens_title_intro.png` | title (`BT000.PI1`), intro picture (`BT001.PI1`), intro with the story text |
| `screen_shop.png` | the live shop screen |
| `screen_ending.png` | the ending picture and its four text pages |
| `proof_tiles_live_vs_render.png` | live frame | tile-only render, levels 2 and 5 |
| `proof_bosses_live_vs_render.png` | live boss crop | decoded frame at the matched offset (BTA, BTB, Block Head, Spear Throwing Demon) |

## 1. The engine is the resident part, called through `trap #3`

The drawing library lives in the resident `BL_TIGER` image (`$a300..$c36f`), not in COMMAND.PRG; COMMAND.PRG reaches it with `trap #3`, function in D0
(`$a640`, table `$a658`). Drawing services, named from their bodies (calls per game frame: `hits` over 1,200,000 steps of `play_start.snap`, 20 frames):

| D0 | addr | body | per frame |
|---|---|---|---|
| 0 | `$a6d6` | clear both screens, D1 x 40 longs each (`$c8` = all, `$b6` = all but the bottom 18 rows) | level start |
| 1 | `$aad8` | page flip (section 3) | 1 |
| 2 | `$ab3a` | set palette from A0 (16 words): sets `$c348`, spins until the VBL handler clears it, copies to `$ff8240` | level start |
| 3 | `$a6fa` | 16 px sprite: 8 bytes per row (four plane words, ST interleaved), colour 0 transparent, clipped | 4 |
| 4 | `$a86c` | 32 px sprite: 16 bytes per row (four plane longs), colour 0 transparent, clipped | 2 |
| 5 | `$aa52` | store the column clip table pointer D1 in `$c326` | init |
| 6 | `$ab5e` | ring-buffer scroll blit (512x512 px buffer at `$c316`, `and.l #$1ffff`) | never called by COMMAND.PRG |
| 7 | `$ad10` | 2-plane picture blit | never called |
| 8 | `$ad7c` | picture blit into both screens (section 6); D2 = x in 8 px units, D3 = y, D5 != 0 colour 0 transparent | 4 |
| 9 | `$af08` | load file named by D1 to A0 (GEMDOS Fopen, Fseek(2), Fseek(0), Fread, Fclose), returns A0 = end rounded to even | level start |
| 11 | `$afa0` | text, 8x8 1 bpp glyphs (section 2) | 3 |
| 20 | `$b12c` | background (section 3) | 1 |
| 25 | `$bac0` | fill rectangle, colour bits of D1 per plane | 1 |

COMMAND.PRG's wrappers: `$f400` (text with the arguments on the stack), `$f2a4(index, x8, y, flag)` = draw BTCLIPS picture, `$f2ce` = BTOBJ picture,
`$f270(n)` = show `BT00<n>.PI1` (the Degas file is read into the draw buffer with its 34-byte header ahead of the screen, palette = header + 2, then flip).
Init `$f0f0` (called first, `$c49a`): builds the 256-entry **bit-reverse table at `$1eee0`** (mirroring), clears the screens, saves the ST palette to `$1ee72`, sets
the black palette `$17276`, shows `BT000.PI1`, sets the clip table `$176d1`, loads BTMAN (`$37780`, pointer `$1ee9e`), BTSPR (`$3a77e`, `$1eea2`), `t0` (`$25f8c`,
tile graphics pointer `$1efe0 = $25f8c + $240`), BTCLIPS (`$4a59e`, `$1efe4`), BTOBJ (`$4f0dc`, `$1efe8`).

## 2. Screen, viewport, HUD, text

1. Low resolution, two screens `$f8000` (`$c31e`) and `$f0000` (`$c322`) from `Logbase` (`$aa86`); `$c31a` = draw buffer.
2. The playfield is a **256x160 window at screen (32,20)** (`$c33a` = `$c90`, set by service 13). Sprite and tile coordinates are viewport relative. The blitters clip with
   the column table `$176d1` = `01 03 07 x14 06 04` (index `(x>>4)+1`; for a 16 px sprite bit 1/0 = which destination word may be written, for a 32 px sprite
   bits 2/1/0 = its three words; 0 = column off) and against 160 rows.
3. Text, service 11 (`$afa0`): glyph row bytes from `$bb9e + (c - $20) * 8`; D2 = `(x/8) << 8 | y` (bit 8 of D2 = odd 8 px cell); pen colour = D1 & 15 (each plane of the
   glyph pixels is set or cleared by its D1 bit, other pixels untouched; D1 bit 31 clears the cell first); CR starts the next line, 9 text rows (`$5a0` bytes) below.
   **Gate** (`screens_check.py`, `text.py`): the font and these rules reproduce the hi-score screen (names at x=80, y=81/90/114/123/141, pen 7), the Continue prompt (80,80), the
   8 story lines (pen 15, x=40, y=32..158 step 18) and the 4 ending pages (pen 3): all strings found with exact glyph/background match.
4. **Font**: 224 glyphs (`$20..$ff`) in the layout of the Atari ST ROM 8x8 system font (`font_8x8.png`).
5. HUD (state fields: `mechanics.md` 4): key icon BTCLIPS 4 at screen (48,183), weapon icon BTCLIPS 15 at (120,183), armour icon at (176,183) (BTCLIPS 5..8, one per armour grade
   INFERRED from the shop, 6), potion BTCLIPS 9 at (240,183), coin BTCLIPS 16 at (216,23), vitality bar segment BTCLIPS 20 from (80,28). Gate (`pics_check.py`): BTCLIPS 4, 5, 9, 15, 16, 20
   found at 100% at those positions (84/84, 137/137, 144/144, 42/42, 188/188, 96/96). Time, score, lives and money are text. The first 16 playfield rows differ from the tile render because the
   HUD text sits over them.

## 3. Buffering, scroll, timing

1. `$aad8` toggles `$bb70`, sets `$c31a` to the other screen, writes the video base high/mid bytes (`$8201/$8203`) with the buffer just finished (no VBL wait), bumps `$bb72`, arms
   `$c32a = $bb7a` (2). The VBL-queue entry `$a53a` counts `$c32a` down to -1; service 20 starts by polling it (`$b12c`: `tst.w $c32a / bpl`), so a game frame is at least 3 VBLs
   (measured here: 100 handler entries and 20 flips in 1.2M steps = 5 VBL per frame, `hits a53a aad8`).
2. `$a53a` also advances the four animation counters through `$bb76` (`+1 +1 -1 +1`) and, if `$c346 != 0`, rotates palette registers 6..15 every `$c342` VBLs. `$c346` stays 0: service 19
   is never called, so there is no palette cycling in the shipped game.
3. **Scrolling is a full software redraw every frame.** `$ecca`: scroll x `$1efec` = (hero x `$1f014` - `$80`) & `$fff8` (8 px steps, modulo `$1effe` = map width x 16; the world is cyclic
   in x); scroll y `$1efee` = `$1eff0 - $78` (1 px steps; `$1eff0` takes the hero y `$1f016` unless the hold flags `$17830/$17832` are set). `$ed26` calls service 20 with D1 = map width,
   D2/D3 = scroll, A4 = `$1efe0`, A5 = `$201c8`. Service 20 draws 10 (+1 when `scroll y & 15 != 0`) rows of 16 tiles, 128 bytes per tile, with one of the copy bodies `$b2aa` (aligned) or
   `$b50e..$b75c` (byte-interleaved, 8 px shift) chosen by `scroll & 8`, and specialised row bodies for `scroll y & 15`. No hardware scroll register, no parallax layer.

## 4. Tilesets, maps, palettes

1. `T<n>` (n = 0, 2..7) layout:

| offset | content |
|---|---|
| +$000 | palette A, 16 words `$0RGB`, loaded to `$25f8c` |
| +$020 | palette B (`$25fac`); differs from A only in T0 and T6 |
| +$040 | 512 bytes, one class byte per tile index (collision: `mechanics.md` 3; read by `$ec7c` at `$25fcc`) |
| +$240 | tiles: 16x16, 128 bytes, 16 rows of four plane words (ST interleaved), opaque |

   Tile counts (file length - 576) / 128: T0 352, T2 250, T3 279, T4 234, T5 281, T6 181, T7 254. The highest tile index used by the maps equals count - 1 for T0, T2, T3, T4, T5, T7 and is
   173 for T6.
2. Level n uses `t<digit>` with the string `"00234567"` at `$175fb` (the table read at `$ccd6`): levels 0 and 1 share `T0`, which is why there is no `T1`. For level 1 the resident T0
   is kept and `$ccbe..$ccd2` pokes colours 1..3 of palette A to `$0010,$0121,$0032` (green). The shifter palette of the level snapshots equals palette A (level 1: with this override) on 8/8 levels
   (`tiles.py level_palette`). Colours 4..6, 8, 9, 13..15 are identical in every level (hero, HUD), 7 and 10..12 shift slightly in T4..T7. Palette B is loaded at `$d0c0` and A restored at `$d118`
   (the handlers of the invisible map objects `$1b` door-in `$d05c` and `$1c` door-out `$d0d0`, which teleport within the level; proven live, `secrets.md`).
3. Map `n` (file `n`, loaded at `$201c8`): word width, word height, width x height words; word `& $3ff` = tile index, `>> 10` = object marker (`mechanics.md` 1). Sizes: 128x50, 128x64, **64x160**, 128x67,
   128x64, 128x65, 128x64, 128x65. `$cd58` strips the marker bits (`andi.w #$3ff`) in the loaded copy.
4. **Gate** (`tiles.py check --draw`, snapshots at the page-flip entry so the draw buffer and the scroll variables belong together): the tile render at the live scroll equals the draw buffer in
   94.5% to 96.3% of the 40960 playfield pixels in every one of the 15 snapshots tested (one flip snapshot per level, 8, plus 7 walking/attack ones) (`gates/tiles_levels.txt`, `tiles_walk.txt`; e.g. L2 39380/40960 with 136 of 160 tiles exactly
   equal). The rest is HUD text, actors, objects and the flail chain (`tiles_residual.py`: 50 snapshots, 101,104 differing pixels, 3 snapshots with none outside the HUD/actor boxes and the others
   18 to ~1500 outside my crude +-64 px boxes; `proof_tiles_live_vs_render.png` shows two clean cases). There is no other background layer in the game.

## 5. Actor sprite banks

The actor record (`$1f010`, 16 bytes: type, state, frame, facing, x word, y word, ...) is owned by `ai.md` 1; the draw loop is `$e19e`, the piece dispatcher `$ed4c`.

1. **Bank layout** (BTMAN, each BTSPR bank, BTA, BTB):

```
+0 word H            rows of every piece of every frame in the bank
+2 word animoff      animation table; entry (10 bytes) at animoff + state*10:
   +0 word listoff   frame list: one word per frame = offset of that frame's pixels from the bank start
   +2 byte nframes   +3 sbyte x step   +4 sbyte y step (added to the actor each frame)
   +5 byte width code 1..8   +6 byte trigger frame (ff none)   +7 byte overlay kind   +8 word overlay record
pixels: code -> pieces left to right:  1=[16] 2=[32] 3=[32,16] 4=[32,32] 5=[32,32,16] 6,7=[32,32,32] 8=[32,32,32,32]
   32 px piece = H rows x 16 B (four plane longs, drawn by service 4); 16 px piece = H rows x 8 B (service 3); pieces are consecutive; colour 0 transparent
```

2. **Which bank**: type byte bit 7 set (`$ff`, the hero) = BTMAN via `$1ee9e`; otherwise bank = BTSPR long table entry `type - 1` (`$1eea2`): offsets `$50, $602, $20a8, $20a8, $3ea0, $4f38, $65d6, $65d6, $8080 x3,
   $8f48, $adf6, $b21c, $bb20, $c3d2, $dd1a`, then zeros (types 3 and 4, 7 and 8, 9..11 share a bank). H = 32 except banks 1 and 14 (27) and 13 and 15 (16 px wide, code 1). Extents are taken from the data: the 13 distinct
   banks tile the file to `$fe20` exactly (slots: bank 1 3, 2 13, 3 14, 5 8, 6 11, 7 13, 9 7, 12 15, 13 7, 14 5, 15 16, 16 12, 17 16; bank 2 has two unreferenced slots, bank 12 two, bank 3 one plus
   280 trailing bytes); BTMAN has 23 frames ending exactly at the file end. Atlases: `sprites_BTSPR_banks.png`, `sprites_BTMAN_hero.png`. The type to creature table is `ai.md` 5.
3. **Drawing rules**: facing byte != 0 = stored orientation, 0 = mirrored (every plane word/long bit-reversed through `$1eee0` into the scratch buffer `$1ee92`, `$f058/$f090`; the whole row, so the piece
   order of wide sprites reverses too). Screen x = actor x - scroll x (modulo world width) - width code x 8 (centre anchored); screen y = actor y - scroll y - H (y is the feet line). The drawn frame is
   `frame - 1` in a snapshot taken at the page flip (`$e514` stores frame + 1 after the draw), and the x/y step is applied after the draw too.
4. **Gates.** Banks from the files (`sprites_check.py`): 97 actor instances over 50 snapshots, 30 exact (every non-transparent pixel equal): skeleton-type 3 19/28 (449/449, 436/436, 535/535, 597/597, 627/627,
   646/646), type 2 2/7 (462/462, 471/471), type 13 7/8 (48/48), hero 2/50 (322/322, 368/368); the rest are actors whose state changed after the draw, the hero covered by his own flail or an enemy,
   and types 15 and 12 (not matched, open). `hero_check.py` (all 23 BTMAN frames per snapshot): 4 attack snapshots at 100.0% (322/322, 368/368), idle 87-89%, walking 69-76%. **Boss and escort sprites
   with the banks read from RAM** (`boss_check.py`, 132 slot-1.. instances over the 64 + 40 boss snapshots, 71 exact):

| actor | levels (index) | bank | width code | as stored | mirrored |
|---|---|---|---|---|---|
| Block Head (`BTIGER.DOC`), type 1 | 0, 1 | BTSPR bank 1 (H 27, 3 frames) | 2 | 0 of 23 | 24 of 25 |
| type `$0c` (Spear Throwing Demon, the orange sphere frame; `ai.md` 9) | 3 | BTSPR bank 12 (H 32) | 2 | 0 of 1 | 6 of 7 |
| type `$12` (dragon) | 2, 5, 7 | BTA (H 64, 9 frames of 4096 B) | 8 (128 px, four pieces) | 14 of 28 | 9 of 16 |
| type `$13` (samurai demon) | 4, 6 | BTB (H 64, 8 frames of 2048 B) | 4 (64 px, two pieces) | 10 of 14 | 8 of 18 |

   Exact means `ok == tot` over at least 100 pixels; the non-exact instances are frames where the boss moved between the draw and the snapshot (a y fall of 20 px per frame in the snapshots where the teleport left it above ground,
   dying/dissolving frames) or is partly behind the hero. **Mirrored wide pieces are right**: the 128 px four-piece BTA dragon and the 64 px BTB demon match exactly when drawn mirrored as a whole row
   (2871/2871, 2274/2274, 2480/2480, 2810/2810 and 2692/2692 for BTA; 1757/1757, 1712/1712, 1578/1578 and 1763/1763 for BTB), with the hero on the other side of the boss (`BR*` snapshots, facing 0). Width codes 3, 5, 6, 7 occur in no shipped bank (every
   BTSPR bank uses code 1 or 2, BTA 8, BTB 4); they are decoded from the jump tables only and are NOT exercised.
5. **Bosses (BTA / BTB)** are replacement sprite banks loaded over BTSPR by the level-exit object (`$cfa4`, `system.md` 9): table `$17226 + 4 * level` = (count, type, file letter, 0): levels 0 and 1 two and four type 1 (no file),
   2: type `$12` 'a', 3: `$0c`, 4: `$13` 'b', 5: `$12` 'a', 6: `$13` 'b', 7: `$12` 'a'. Both files start with 20 identical offsets (`$50`) followed by one bank (H 64). Names: `BTIGER.DOC` lists Block Head, Blue Dragons, Spear Throwing Demons, Blue Samurai
   Dragons, Red Dragons, Gold Samurai Dragons, Black Dragons; assigning them to the BTA/BTB levels by order (blue, red, black dragon; blue, gold samurai) is INFERRED. The dragons are the same art in the level's colours (live palette = tileset palette A).
   Boss positions in the snapshots come from a teleported hero: the rule `y >= scroll y + $21` (`ai.md` 9) pushes the boss to the old camera, which is why several rest at y 857..2441.
6. **Weapon overlay layer**: anim entry +7 = 2 and +8 = record of 6 bytes per frame (sprite index, x displacement, y displacement). The sprite index selects a family through the long table `$1cbde`, the weapon level
   (`$1f00a`, 0..4) selects the sprite: word width code, word H, pixels. Family 0 (`$1cc06..$1ce16`, 5 x 16x16, large spiked head), 1 (`$1ceae..$1d0be`, 5 x 16x16, small head), 2 (`$1d162`, one 16x9 chain link for all
   levels). Gate: hero attack frame 0 (`atk0`, `atk4`): family 1 level 0 at (hero x + `$f`, feet y - `$28`) = 54/54 pixels, the record's own displacement. The chain link (index 2) repeats along the chain; the head/chain
   names are INFERRED from the look.

## 6. Picture banks, Degas files, the shop, the screens

1. **BTCLIPS** (21 pictures) and **BTOBJ** (27 pictures + an empty entry 0) are tables of word offsets; a picture is word w (16 px groups), word h, then h rows of w groups of four plane words. Every gap between
   consecutive offsets equals 4 + w x h x 8 (21/21 and 27/27). Service 8 draws them (`$ad7c`: `$adb0` word aligned for even D2, `$ae1e` byte path for odd D2). Atlases `pics_BTCLIPS.png`, `pics_BTOBJ.png`.
   Contents (from the atlas and the shop): BTCLIPS 0..3 weapon icons (shop items 0..3), 4 key, 5..8 armour icons, 9 potion, 10 and 11 dialog frame, 12..14 frame corners, 15 HUD weapon icon, 16 coin,
   17 the shop scene, 18 and 19 striped fills, 20 vitality bar segment. BTOBJ: 1 and 2 urns, 3..9 coins, 10..13 and 17 dark item/monster pictures, 14 key, 15 hourglass, 16 sign, 23 a 16x5 dot (18..22 alias 17, 24..27 alias 23).
   Gate: BTOBJ 1, 3, 5, 16 found at 100% (192/192, 52/52, 116/116, 167/167); the others do not appear in my snapshots (partial overlaps only), same format.
2. **Shop** (`$ea7c` -> `$f690`; `mechanics.md` 10): `$ea7c` clears the screens (`$b6` rows), sets the palette `$172d6`, calls `$f690`, which draws BTCLIPS 17 (256x112) at (32,0), the ten item icons BTCLIPS 0..9 at
   x = `$17ab2[i] * 8` = 48, 88, 128, 168, 208 and y = `$17ac8[i]` = 118 / 150, the price/"EXIT" text, and the old man's speech; on leaving `$ea94` clears, restores palette `$25f8c` and redraws the HUD (`$cd12`).
   Gate (`shop_check.py`, snapshot `shop/shop_a.snap`, hero poked onto the shop man): live palette == `$172d6` (16/16); the ten icons 1253/1253 pixels; the scene 17450/17920 outside the speech box (rows 8..49).
3. **Title**: `BT000.PI1` (Degas, rez 0, palette in the file): `tl/t24.snap` equals it in 64000/64000 pixels with the same palette.
4. **Intro** (`$ebf8`, after `$eac6`, natural drive): `$f270(1)` shows `BT001.PI1` (palette from the file; 64000/64000), waits 70 ticks, swaps the palette `$17296` / `$172b6` four times at 8 ticks (lightning flash), waits 50,
   prints the story text `$17351` at D2 = `$520` (x=40, y=32), pen 15 (8/8 lines found), and fades out (`$f2f8`). The text screen's palette equals `$172b6` (red). `screens_check.py`.
5. **Game over / hi-score**: the Continue prompt (`$1733e`, "Continue ? Y / N :", text at (80,80), pen 7) is drawn over the dead level; the name screen (`$10386` -> `$102ea`) is text only on a cleared
   screen with the level palette: "Enter your name then press RETURN to exit" at (80,81), the five entries at y = `$69 + 9i` = 105.. (names x=80, scores right of them). Snapshots: systems' `go_prompt` / `go_hi` / `go_hi2`
   (their drive pokes lives and score: `system.md` 9).
6. **Ending** (`$c718`, after the level 7 boss slot is empty, `$c642`): clear, palette `$172f6`, `bt5` read to `$201cc`, service 8 at x = 0, y = `$2c` (44) of `BT5` (96x112, 4 + 6 x 112 x 8 = 5380 bytes = the file), then four text pages (pen 3, all at D2 = `$d30` = (104,48): strings `$1741c`, `$174b7`, `$174f8`, `$17543`, each followed by a 400-tick wait and `$c832`). Gate (`screens_check.py`, ending reached by a labelled poke): picture 10752/10752 in all five snapshots,
   palette == `$172f6`, text found 6/6, 3/3, 3/3, 2/2.
7. **Level start** (`$c50e..$c56e`): service 0 with D1 = `$c8`, palette `$17256` (dark blue `000 002 123 225 ...`), HUD frame `$cd12`, `$cc8c` (map + tileset load, level palette set), the actor build `$cd58`, `$c850`. There is no separate
   level-intro picture: the game goes straight from the load to the first frame (the palette `$17256` shows for the HUD only).

## 7. Palettes and fades

1. Level palette: tileset palette A (section 4); title: `BT000.PI1`; intro: `BT001.PI1` then `$17296` / `$172b6`; shop `$172d6`; ending `$172f6`; level start / HUD `$17256`; black `$17276`.
2. `$f2f8` fade out: 8 steps, each lowers every non-zero R, G, B gun of colours 0..14 by 1, with a busy delay (`$f34a`, `$2000` loop) per colour. `$f0d8` copies the hardware palette (masked `$777`) to A0.
3. Palette B (T0, T6 only) and the VBL palette rotation: section 4.2 and 3.2.

## 8. Method

All snapshots are taken at the page-flip entry `$aad8` (`bp aad8; snap`), where the draw buffer holds the finished frame and the scroll variables belong to it (the displayed buffer is the previous frame).
Level snapshots: LABELLED POKE (superseded by the built-in level skip, `system.md` 8, for the systems drive): `bp c574` (main loop top), `w 17846 000n0000`, patch `jmp $c50e` over `bsr $c900`
(`w c574 4ef90000`, `w c578 c50e0001`), `s 1`, restore (`w c574 6100038a`, `w c578 4a390001`), 3,000,000 steps. Boss snapshots: LABELLED POKES: hero longword `$1f014` onto the exit cell (kind `$20`), 900,000 steps,
then onto the boss ("left" 70 px or "right" 110 px). Ending: LABELLED POKE `w 1f020 00000000` (boss slot cleared). Shop: LABELLED POKE hero onto (1256,224). Everything else (intro, attack, walk, title) is natural input.

## 9. Open items

1. Width codes 3, 5, 6, 7 (48, 80, 96 px pieces) are never used by shipped data; their piece order is read from the jump tables only.
2. Actor types 15 and 12 did not match within +-24 px (3 and 1 instances); type 12's frame in the dying state is unexplained.
3. The shop scene's `$172d6` blink/animation (470 differing pixels of 17920 outside the speech box: the old man's animation, INFERRED) are not traced.
4. BTCLIPS 18 and 19 (striped fills), BTOBJ 10..13 and 17 (dark pictures), 15 and 16 are named by look only; BTCLIPS 0..9 follow the shop item numbers.
5. The boss names per level are INFERRED (section 5.5).
6. Hi-score and game-over screens were not re-captured by this document's scripts (systems' snapshots are used).

## 10. Not exercised

Mirrored 48/80/96 px pieces; a killed boss (dissolve frames only as stored frames); the second palette in play; ring-buffer scroll (service 6) and service 7 (never called); palette rotation (`$c346`); the level 8
boss in its own arena without the teleport; the shop on levels other than 0; the BTCLIPS 10..14 dialog frames in play; the continue/hi-score screens with a natural game over.
