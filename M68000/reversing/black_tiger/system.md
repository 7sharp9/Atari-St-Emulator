# Black Tiger: system architecture

Capcom 1989, US Gold, Clipper Computer Products conversion; Replicants / The Best crack. Addresses are runtime absolute
(`dotnet exec bin/Debug/net8.0/M68000.dll`, disk `bt_auto.st`). Scripts are in `py/systems/` (table in its README); data
and snapshots under `scratchpad/black_tiger/agents/systems/`. "Gate" lines give the match count of a live check;
INFERRED marks what has only been read or guessed. Images are in `img/systems/`:

| image | content |
|---|---|
| `title_screen.png` | the title (BT000.PI1) as shown by the attract loop |
| `attract_cycle.png` | attract cycle: title, hi-score table, demo |
| `levels_1_8.png` | levels 2..8 reached with the built-in level skip |
| `boss_fight_sheet.png` | the eight boss arenas 1.5M steps after the trigger |
| `shop_screen.png` | the level-1 shop |
| `ending_sequence.png` | ending text screens, then the disk prompt |
| `gameover_hiscore.png` | continue prompt, name entry, attract restart |

## 1. Program layout

1. `\AUTO\BLTIGER.PRG` (this crack's copy of `BL_TIGER.PRG`, JEK-packed, the only packed file) stays resident at `$a2fc..$bc4e`:
   cracktro (SPACE gate `$a562`), then `Pexec("command.PRG")` (strings `$bb54`, `$bb62`). It provides the **trap #3 service
   library** (section 7), a VBL-queue entry `$a53a`, and the IKBD mouse and joystick vectors (`$a5fa`, `$a624`, installed by `$a5b0`
   through Kbdvbase). The game itself never calls a GEMDOS trap; all file, key and graphics access goes through trap #3.
2. `COMMAND.PRG` is a Replicants wrapper: a 556-byte trainer stub (menu, ACIA poll `$c658`) followed by an embedded PRG header at `$c680`
   and the game image. On NORMAL the stub applies the inner relocation table (`$c58e..$c5c4`, `+$c470`) and copies the image over
   itself to `$c470` (`$c5fa..$c63e`, `jmp (A7)`), after which `$c470` is the game entry (`movea.l A7,A5`). Game byte `a` is at file
   offset `a - $c228`. Gate `gates.py container`: 52/60 sampled 24-byte windows equal (the misses hold relocated longs) and the string
   `Please insert Disk` is at file `$b389` = runtime `$175b1`.
3. Mixed code: hand-written asm plus a few C-compiled routines (about 20 LINK frames: the HUD printers `$fe60..$10160`, `$1025c`,
   `$102ea`, `$10386`, `$101fc`, `$10222`, `$f690..`). Data tables sit between code at `$17000..$18500`.
4. No decompressor exists in the game. Every data file is read raw by service 9 `$af08` (Fopen, Fseek(0,2) for the size, Fseek(0,0), Fread,
   Fclose; returns A0 = end rounded up to even).

## 2. Boot chain (GEMDOS trace `ATARI_TRACE_GEMDOS=1`)

Cold boot, `\AUTO` cracktro, trainer menu (poke `w c65e 601e0c38` = NORMAL), then `COMMAND.PRG` init `$f0f0`. The first-load sequence and
destination (heap pointer `$1ee92` advances after each; gate: the trace matches the brief's list 9/9) is:
`BT000.pi1` to screen base - 34 (the Degas header precedes the screen), `btsnd` `$31972` (`$5e0d`), `btman` `$37780` (`$2ffe`), `btspr` `$3a77e`
(`$fe20`), `t0` `$25f8c` (`$b240`), `btclips` `$4a59e` (`$4b3e`), `btobj` `$4f0dc` (`$db0`), then `bt4` `$201cc` (`$da5c`). Pointers: `$1eea6` btsnd,
`$1ee9e` btman, `$1eea2` btspr, `$1efe0` = tile file + `$240`, `$1efe4` btclips, `$1efe8` btobj.

## 3. Role of every file

| file | role | proof |
|---|---|---|
| `BL_TIGER.PRG` | resident library (section 7) | `$a41c` and following |
| `COMMAND.PRG` | trainer stub + game | section 1 |
| `BT000.PI1` | title picture (logo, Capcom 1989, US Gold); `$f270(0)` | `$eb1c`; `img/systems/attract_cycle.png` |
| `BT001.PI1` | start-of-game screen after fire at the title (`$ebf8`: `$f270(1)`, 70-frame wait, palette flash, text `$17351`) | Fopen 340,000,220 right after the title; code |
| `BTSND` | 8 digitised samples. Header: 32 entries of (offset,length), entries 1..8 contiguous from `$100` to the file size `$5e0d`, entries 9..31 repeat entry 8 | gate `btsnd`: 8/8 contiguous, 24/24 padding |
| `BT4` | the title tune as a digitised 8-bit sample (sound id 0: `$105e8` sets length `$da5c`, pointer `$201cc`) | gate `timera`, section 5 |
| `BT5` | ending data, read to `$201cc` (`$1504` bytes) after the last boss | `drive_ending.py` Fread trace |
| `BTMAN`, `BTSPR`, `BTA`, `BTB` | sprite banks (`BTSPR` main; `BTA`/`BTB` boss banks loaded over its slot); contents owned by graphics.md | section 4 |
| `BTCLIPS`, `BTOBJ` | picture banks drawn with `$f2a4` / `$f2ce` (HUD, shop scene, items); there is no collision file | section 7 |
| `0`..`7` | maps of levels 1..8: `$cc8c(level)` patches the digit into the name at `$175d0` and loads to `$201c8` | `drive_levels.py`: Fopen `1`..`7` |
| `T0`, `T2`..`T7` | per-level tile files: the second character comes from `$175fb` = `"00234567"`, so level 2 reuses `t0` (no `T1`) | same |
| `BTIGER.DOC`, `DESKTOP.INF` | never opened by the game | no Fopen in 3.6e8 steps of trace |

File sizes as read: maps `$3204 $4004 $5004 $4304 $4004 $4104 $4004 $4104`; tile files t0 `$b240`, t2 `$7f40`, t3 `$8dc0`, t4 `$7740`, t5 `$8ec0`,
t6 `$5cc0`, t7 `$8140`; boss banks are 37134 (`bta`) and 16654 (`btb`) bytes.

## 4. Memory map

```
$0004ce        TOS VBL queue slot; replaced by $a53a (original in $c2f8, restored by $a51c)
$00a2fc..$00bc4e  BL_TIGER (library; 8x8 font $bb9e; state block $c2f0..$c360)
$00c370        COMMAND basepage; $00c470..$01f274 game text and data
$01ee6a        stack top; $01ee72 palette block; $01eee0 256-byte bit-reverse table (built at $f0f0)
$01f000..$01f00f  player stats (words): +2 zenny (starts $c8), +4 keys, +6 weapon (2), +8 armour, +a potions, +c lives (5), +e vitality units (3)
$01f010        actor records, 16 bytes, 179 slots; slot 0 = hero (+0 type $ff alive, 0 dead; +4 x; +6 y); slot 1 ($1f020) = boss first spawn
$01fb60        map-object records, 10 bytes x 164 (+0 kind word, +2 x, +4 y, +7 timer); built by $cd58 from the level map
$0201c8        level map file (word0 width in tiles, word1 height, cells from $201cc: tile = word & $3ff, class = word >> 10)
$025f8c        tile file t<n> (palette and header $240, tiles from $1efe0)
$031972        BTSND;  $03157c..$03158c sample-player state;  $03195c RNG seed;  $03195e.. text scratch
$037780 BTMAN; $03a77e BTSPR (a boss bank replaces it); $04a59e BTCLIPS; $04f0dc BTOBJ; end $04fe8c
$0f0000 and $0f8000  the two screens ($c322, $c31e from XBIOS 2); $0e8000 32 KB buffer ($c316) used by services 6/7 (INFERRED: title and ending scroller)
```

`BT4` (`$201cc..$2dc28`) overlaps the map and the head of the tile area, so every attract cycle reloads `0` and `t0` after the title.
Boss banks: the table `$17226` (4 bytes per level) has `count, type, bank letter, 0`. `$cfda` spawns `count` records of `type`, and when
the letter is non-zero reads `bt<letter>` into the BTSPR slot (`$cff4..$d00e`) and sets `$1eeba`. Letters: level index 2,5,7 `a`; 4,6 `b`.

## 5. Frame structure

1. **The frame driver is the main loop at `$c574`**, not the VBL queue. Each pass: `bsr $c900` (frame body), `tst.b $1f010` (negative = hero
   alive) then `$c642`. The VBL-queue entry `$a53a` (one call per VBL, TOS VBL `$fc0634` every 12,000 steps) only decrements the
   frame-wait counter `$c32a` while it is >= 0, steps the four-word block that `$bb76` points to (game: `$1eed8`), runs the palette cycle
   and clears `$c348` (the flag service 2 waits on).
2. **A frame is 5 VBLs.** Service 1 flips the pages and restarts the wait (`$c32a := $bb7a` = 2); service 20 (`$ed26`) spins until it
   expires (3 VBLs), then about 25k steps of work (2 VBLs). Gate `frames`: 49/49 frame gaps are exactly 5 VBLs (level 1; the same
   at level 4, 49/49). 59.9k steps per frame, 10 frames/s.
3. `$c900` order (call tree of one frame in `scratchpad/.../logs/frame_order.txt`, per-frame call counts `frame_census_lvl0.txt`):
   `rand_mod $cb6a` (D0=$80), `camera_update $ecca`, `read_input $f358`, `draw_background_tilemap $ed26` (service 20), `poison_hud_blink_tick $e168` (blinks the poison marker while `$17820` is set),
   `$d7b0`, `$d6b6` (not read), `actor_update_and_draw_loop $e19e` (calls `sprite_cull_and_blit $ed4c`, 8 per frame = services 3/4),
   `map_object_sweep_urns_and_dispatch $d4ae` (walks the 164 map records, calls `$ceec` for each live one, 16 per frame), `$10e94`, `$10894`, `$10b84`
   (not read), HUD `hud_time $ff1a`, `hud_zenny $feb2`, `hud_vitality_bar $10160`, `time_over_check $cc26`, `hud_score $cb78`,
   ambient spawners `$c972`, `$ca48` (random spawns, quick read), then service 1 (page flip) and the sound mailbox.
4. **`$ceec` dispatches MAP OBJECT kinds**, not actors: it computes dx = |hero x - rec+2|, dy = |rec+4 - hero y| and jumps through the 33-entry long
   table `$cf20` (kinds 0..2 -> `$d404` nothing, 3..15 -> `$d2b4`, 16 -> `$d16c`, 17..22 (`$11`..`$16`) -> `$d194` (`$11` = shop man via `$ea7c`; `$12`.. old men via `$fca6`),
   kind `$20` -> `$cfa4`). **`$cfa4` is the level exit**: hero within 32 px (dx and dy <= `$20`), set `$1eeb8`, clear actor records
   from `$1f020` (179), load the boss bank by `$17226`, spawn the boss(es) (section 9).
5. **Timer A (`$134 -> $106c2`) is a digital sample player**, not a music sequencer. Per tick it takes one byte from `$31582`, looks up an 8-byte PSG
   volume write in `$17ce0[(b+$80)*8]` (`movep` to `$ff8800`) and decrements `$3157e`; at the end it disables itself (`$1072e`) or loops (high word of the
   effect id negative). Rate from `$184e0[idx]` (idx 1 = TACR 5, TADR 5 = 2,457,600 / 64 / 5 = 7680 Hz, computed). Requests: effect id in the long mailbox `$17848`
   consumed at the end of the frame (`$c956`, `$cc62`) by `$105e8(D1)`; id 0 plays BT4, ids 1..8 are BTSND entries. Gate `timera`: at the title (`tl/t24.snap`) 5348 ISR
   entries, remaining count fell by 5348 and pointer rose by 5348 (3/3 equal); in `play_start.snap` 0 entries. The game plays no PSG tone in play.
6. Random numbers: `rand_mod $cb6a(n)` -> `$fe1c`, seed `$3195c`, `s' = ((s*s mod 2^16) * $c2 + s * $6eb + $3619) mod 2^16` (mechanics gates it, 300/300).

## 6. State machine

```
cracktro -> trainer menu -> $c470
$c4a0 restart: level != 0 -> disk-A prompt ($cb2c), level := 0
$c4c4 attract_demo_loop $eac6: demo flag $1783a := 1, stream index $1784c := 0; protection call $f52e (returns 0); load bt4 (tune) + title BT000
      + hi-score table ($102ea); runs level 1 from the recorded stream until it ends (index $200) or fire ($80 in the live byte; $105c0 stops the sample)
$c4ca new game: zenny $c8, keys/armour/potions 0, continues $1eec0 := 3, lives := 5, score := 0; start screen $ebf8; test $f68e (protection result)
$c50e level_start: flags $177b5[level] -> $17840/$17842, clear objects ($f422), clear screen, palette $17256, static HUD $cd12, level files $cc8c,
      map objects $cd58, btspr reload $caee (disk prompts A / B), level init $c850 (weapon := 2, vitality := 3, +1 if level > 0, +1 if level == 7), lives HUD
$c574 frame_loop -> hero dies ($1f010 := 0): $c582 death animation $cc80 (21 frames), lives-1 -> $c566 same level
      lives == 0: continues-1, "Continue ? Y / N :" (key Y = $59 after & $df) -> score 0, lives 5 -> $c566; else $c632 -> $10386 name entry -> $c4a0
level cleared: $1eeb8 != 0 and boss slot $1f020 type == 0 -> $c656: level < 7 -> $1025c zenny bonus (word $17aa2[level]: 300 500 800 1200 1600 2400 4800),
      level+1, $c50e;  level == 7 -> $c718 ending
$c718 ending: map `bt5` -> $201cc, picture palette `$172f6`, four text screens (`$1741c`, `$174b7`, `$174f8`, `$17543`), level := 0, $caee reload of btspr behind the disk-A prompt, $c4a0
```

Live checks: the game over / continue / name entry chain (go-over drive: pokes lives := 1, hero type := 0, score 90000 for the table; keys N, name `bt`, RETURN,
attract restart); the ending chain (`drive_ending.py`: `bt5` read, text screens, `Please insert Disk A` waiting on `Bconin(2)`, then SPACE, then `btspr`, `bt4`, `BT000.pi1`).
The high-score table is `$1765a` (5 long scores) with 17-byte names at `$17603`, initial entries the developers (Richard J Lilley 40000, Sarah 30000, Teoman 20000, Kate 10000, Graham 5000).

## 7. trap #3 services (`$a640`: `D0 << 2` indexes the long table `$a658`, 32 entries; runs with IPL 3)

| n | routine | function |
|---|---|---|
| 0 | `$a6d6` | clear D1 scanlines of both pages |
| 1 | `$aad8` | page flip (video base, `$bb70` toggle), restart frame wait, `$bb72`++ |
| 2 | `$ab3a` | set 16-colour palette (A0) after the next VBL |
| 3 / 4 | `$a6fa` / `$a86c` | clipped masked blit 16 / 32 pixels wide (D2 x, D3 y, D4 rows, A1 data; D0 = clipped away) |
| 5 | `$aa52` | mask table pointer (D1) |
| 6 / 7 | `$ab5e` / `$ad10` | scroll copy from the `$c316` buffer / draw a tile into it |
| 8 | `$ad7c` | blit to both pages (HUD pictures) |
| 9, 17 | `$af08` | load file (D1 name, A0 destination; returns A0) |
| 10 | `$af70` | non-blocking key (Bconstat/Bconin(2); scancode in the low word) |
| 11 | `$afa0` | 8x8 text (A0 string, D2 position, D1 colour) |
| 12 | `$b0d2` | joystick word `$c2fc` |
| 13 / 14 | `$b0da` / `$b0fc` | set scroll origin and counter block / default counters |
| 15 | `$b108` | D0 = `$c316`, A0 = draw page |
| 19 | `$b116` | palette-cycle setup |
| 20 | `$b12c` | draw tile-map window (A4 tiles, A5 map, D1 width, D2/D3 camera); self-modifying: patches `rts` into the copy tables `$b26a`, `$b8f0`, `$b4ce`, `$b71c` for partial columns |
| 21 | `$af92` | blocking key (Crawcin) |
| 22 | `$aa5a` | copy front page to the draw page |
| 25 | `$bac0` | fill rectangle by plane mask |
| 28 | `$bb34` | mouse buttons and deltas (`$c2fe..$c302`; no game caller found) |
| 16, 18, 23, 24, 26, 27, 29, 30 | stubs | `rts` or `moveq #0,D0` |

Per-frame counts at level 1: service 3 x4, 4 x2, 8 x1..3, 11 x3, 12 x1, 10 x1, 20 x1, 25 x1, 1 x1. `$f2a4` (service 8 with bank `$1efe4` = BTCLIPS) and `$f2ce` (bank
`$1efe8` = BTOBJ) draw those banks as offset tables.

## 8. Input

1. Joystick: the Kbdvbase joystick handler `$a624` writes `$c2fc` (joystick 0, REPL `kbd fe`) and `$c2fd` (joystick 1, `kbd ff`); live: `kbd ff 08` gives `00 08`, `kbd fe 04`
   gives `04 00`. Service 12 returns that word; the game uses the low byte = **joystick 1**: bit0 up, bit1 down, bit2 left, bit3 right, bit7 fire.
2. `read_input $f358`: D0 = byte (or the next demo byte when `$1783a` != 0); `$1eed2/$1eed4` = (dx,dy) from `$17670[D0&$f]`; `$1eece` facing (bit 2, xor `$17822`);
   `$1eed6` = `D0 & $83` (bit 2 set when a direction is held); `$1eed0` = direction class `$176ac[D0&$f]`.
3. Keyboard only through TOS buffered Bconin (services 10, 21): the game proper never reads the ACIA (0 hits of `fc02` in the 20,887-line listing). The only direct ACIA polls are
   BL_TIGER `$a562` and the trainer `$c658/$c662` (already poked in the snapshots). In play: `P` (`$19`) pauses (`$caac`), `Y` at the continue prompt, text at name entry.
4. **Built-in level skip** (shipped, not a crack): `$c6ac..$c706`. ClrHome (`$47`) read while the joystick-1 byte equals `$85` (up + left + fire) sets `$17826`;
   while set, RETURN (`$1c`) does `level := (level+1) & 7` and re-enters `$c50e`; any other key clears it. Gate `drive_levels.py`: 7/7 skips reach level indexes 1..7, 13 Fopen
   (`1`..`7`, `t2`..`t7`), two runs `cmp`-identical (md5 of lvl3 and lvl7).
5. **Attract demo input = a recorded joystick-1 stream**, 512 bytes at `$1784e` (one per game frame, consumed at `$f37c`, index `$1784c`, restart at `$200`; histogram `00` x195,
   `08` x92, `80` x51, `0a` x38, `04` x36, `01` x34 ...). Gate `demo`: 65 frames give hits `$f358` = hits `$f37c` = index delta = 65. The game state (RNG seed, HUD time and score) is not reset
   between cycles, so each cycle plays slightly differently.

## 9. Boss, shop, ending drives (snapshots: `agents/systems/boss/README.md`)

1. Boss: poke the hero position longword `w 1f014 <x><y>` onto the level-exit cell (kind `$20`); `$cfa4` fires within one frame on all 8 levels (30,000 to 90,000 steps,
   `drive_boss.py`; 16 snapshots identical on a second run). Bank files read at the trigger: none (levels 1, 2, 4), `bta` (3, 6, 8), `btb` (5, 7). Boss record types at `$1f020`: `$01`
   (levels 1, 2), `$12`, `$0c`, `$13`, `$12`, `$13`, `$12`. The exit cell of level 1 is (1864,304), reached by walking would need the whole level; the poke skips that and is labelled.
2. Shop: kind `$11` cell, `|dx|,|dy| <= 8`; `$d194` clears the cell, runs 16 mini frames and calls `$ea7c`; the shop screen `$f690` is drawn at 1,436,161 steps after the poke
   (level 1: hits `$ea7c` 1/1, `$f690` 1/1, `$fa9c` 0/0 until a purchase) and waits for input.
3. Ending: with the boss slot emptied the level-end test at `$c642` passes and the code runs the ending of section 6 (Fopen `bt5` `$1504` bytes to `$201cc` at 394,380,178; the
   `Please insert Disk A` prompt waits on `Bconin(2)` at 413,868,644 and any key goes on).

## 10. Copy protection

`$f52e` is the entry of the former protection check and the crack replaced it by `moveq #0,D0 / rts`. The dead body `$f532..$f688` is a direct WD1772 routine (DMA registers
`$8604/$8606/$8609..$860d`, seeks to tracks `$4e` and `$4f`, Read Track `$e4` into `$201cc`, compares the DMA byte count with `$1784`). The only caller is `$eafc`, which stores D0 in
`$f68e`; `$c506` would loop back to the attract if it were non-zero. Gate `protection`: stub bytes `70004e75`, 0 callers of `$f532` in the listing. The two-disk prompts remain (`$cb2c`:
"Please insert Disk A/B", the last character patched at `$175c4`, waits for a key): after a game over from level > 0 (`$c4ac`), after a boss when `btspr` is reloaded (`$caee`), and after the
ending (seen live, section 9).

## 11. Open items

- `$d7b0`, `$d6b6`, `$10e94`, `$10894`, `$10b84`, `$e168` (partly) and the ambient spawners `$c972`, `$ca48` are named from a quick read only; `$e19e` internals belong to ai.md.
- The boss records at +1.5M steps are not always on screen; arena entry behaviour per boss is for ai.md. Boss names are not asserted here.
- The exact device used by service 6/7 buffer `$c316` (title/ending scroller) is INFERRED.
- Sample rate 7680 Hz is computed from TACR/TADR, not measured. `BTMAN` content not examined here.
- Whether the mouse service (28) is ever called: no call site found by grep, not proven live.

## 12. Not exercised

A natural (walked) path to any exit cell, the shop purchase flow (`$fa9c`, mechanics), a real boss kill (the ending drive empties the slot by poke), the disk-B prompt, the time-over path
(`$d44a`), pause (`$caac`), and any run on a fresh cold boot other than the brief's `drive_start.txt` lineage.
