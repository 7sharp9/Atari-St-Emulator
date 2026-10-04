# Black Tiger: sound

Addresses are runtime absolute (COMMAND.PRG image `$c470..$1f274`, BTSND at `$31972`). Scripts are in `py/sound/` (table in its README);
raw logs and renders under `scratchpad/black_tiger/agents/sound/`. "Gate" lines give the match count of a live check; INFERRED marks what has
only been read or guessed. Object-kind and routine names that come from other areas are marked (mechanics) or (ai).

| image | content |
|---|---|
| `img/sound/sound_sheet.png` | top: output level of the volume table by raw sample byte; below: the waveform of each sound id as the handler plays it, and id 0 as it plays in the attract run |

## 1. Mechanism

There is no sequencer, no tone, noise or envelope use and no per-song data. Every sound is a digitised **unsigned 8-bit sample** streamed
through the three YM2149 volume registers R8, R9, R10 by a Timer A interrupt, one sample per tick, using a 256-entry table that maps the
sample byte to a triple of volume nibbles (a table-driven three-voice volume DAC). The driver has one voice: a new request replaces the sound in progress. All sounds are effects except id 0, the title tune.

Gate (PSG writes, 20M steps of the attract demo from `tl/t23.snap`): the only writers of `$ff8800..$ff8806` are `$0106f6` (211,548 byte writes) and
`$0106fc` (105,774) = 52,887 ticks x (4 + 2), plus TOS's floppy port-A select `$fc1c66/$fc1c7c` (463 each). The only PSG operands in the whole
COMMAND.PRG listing are the handler (`$106ee..$106fc`) and the reset routine (`$10776..$10816`); `$f58c` writes register 14 (port A), not audio.
The cracktro (`boot20M.snap`, 3M steps) writes nothing to the PSG besides TOS's port A.

## 2. The driver

| addr | role (read to the end of each body) |
|---|---|
| `$10692` | init (once, from `$f230`): `clr.b $484`, `$134 <- $106c2`, rate 0 through `$10746`, PSG reset `$10776`, IMRA bit 5 on |
| `$105e8` | `sound_play`, D1.w = id, D1 high word negative = loop. Returns if `$184ee == D1`. Else: if `$3157c != 0` reset the rate to 0; `D1 << 3` indexes the BTSND header through `$1eea6` (= `$31972`): `$31582 = base + offset`, `$3157e = length`, `$31586 = D1 high word`. Id 0 is special-cased: length `$da5c`, pointer `$201cc` (the BT4 file), rate index 1. Copies the pair to `$31588/$3158c`, enables Timer A (IERA/IMRA bit 5) |
| `$105c0` | `sound_stop`: clears IERA and IPRA bit 5 and `$184ee`. Only caller `$ebec` (leaving the title/attract loop) |
| `$105d8` | C-callable `sound_play(word)`: `moveq #0,D1; move.w 4(A7),D1; bsr $105e8`. Four callers, all `shop_buy_item` (`$faf8 $fb1a $fb4e $fb64`), all id 7 |
| `$106c2` | Timer A handler: `subq.l #1,$3157e` first (zero: `$1070e`); `b = *$31582++`; `A0 = $17ce0 + 8*((b + $80) & $ff)`; `movep.l (A0)+ -> $ff8800` then `movep.w (A0)+ -> $ff8800`; clear IPRA bit 5; rte |
| `$1070e` | count reached 0: if `$31586 < 0` reload from `$31588/$3158c` and re-enter `$106c2` (loop), else disable Timer A and clear `$184ee` |
| `$10746` | `timera_set_rate(D1 & 7)`: TACR = 0, `$3157c = D1 & 7`, then the table word `$184e0[rate]`: low byte to TACR, high byte to TADR |
| `$10776` | PSG reset (R0-R5 = 0, R7 = `$ff`, R8-R10 = 0) |

Because the count is decremented before the fetch, a stream of L bytes plays L-1 ticks (the last byte is never read). No loop is ever
requested: `$31586` is 0 when the title tune starts (live `m 31586 2` at `$10666`) and every other request is a long whose high word is 0, so
`$1070e`'s loop branch is unused by the shipped call sites (INFERRED from the site list in section 5).

**Rates.** `$184e0` = `0506 0505 0405 1f01 0802 0406 0106 0000` (data << 8 | control). Timer A clock 2,457,600 Hz / prescale (control 6 = 100,
5 = 64) / TADR: rate 0 = TACR 6, TADR 5 = 4915.2 Hz (all BTSND sounds); rate 1 = TACR 5, TADR 5 = 7680 Hz (id 0). Rates 2..6 exist but no code selects
them (`$10746` is called with 0 or 1 only). Live: `watch fffa19 7` shows `fffa19 <- 0, <- 6; fffa1f <- 5` when id 1 starts and `<- 0, <- 5; <- 5`
when the tune starts at `$eb2a`. The emulator raises Timer A every 187 steps regardless of TACR/TADR (`Program.fs` `timerAPeriod`), so wall-clock
tempo is not an emulator observable; every gate checks the register sequence.

## 3. The volume table `$17ce0` and the sample format

256 entries x 8 bytes: `08 A 09 B 0a C 00 00` (register select, value, ...), bytes identical in COMMAND.PRG (file offset 47800) and RAM (2048 bytes
compared by `btsnd.load_tables(Snap)`). The index is `(byte + $80) & $ff`, so the table starts at the middle of the unsigned range. The table
is **decreasing** in the raw byte: byte 0 gives `(14,13,12)`, byte 127 `(13,9,8)`, byte 128 `(12,11,9)`, byte 255 `(0,0,0)`.

Proof that the triples are chosen to make a linear DAC: the output level of each triple from Hatari's measured three-voice table (section 7) falls
from 38,145 (byte 0) to 0 (byte 255) with linear-fit correlation -0.9988 and a largest deviation of 2,801 from the line (7% of the range); 43 of 255
adjacent steps invert by a small amount (the table is an approximation to a ramp that uses all three channels to place intermediate levels, INFERRED from the shape).
Samples centre on byte about 128: mean raw byte 125.4-125.8 in every BTSND sound.

## 4. Sample data

**BTSND** (24,077 = `$5e0d` bytes) loads to `$31972` (`$1ee92` copied to `$1eea6` at `$f142`). Header: 32 entries x (offset.l, length.l) at `8*id`; entry 0
is empty; entries 9..31 repeat entry 8; samples are contiguous from `$100` to `$5e0d`.

| id | offset | length | ticks played | duration | notes |
|---|---|---|---|---|---|
| 1 | `$0100` | `$0539` | 1336 | 0.27 s at 4915.2 Hz | |
| 2 | `$0639` | `$1fca` | 8137 | 1.66 s | longest effect |
| 3 | `$2603` | `$0816` | 2069 | 0.42 s | |
| 4 | `$2e19` | `$058a` | 1417 | 0.29 s | |
| 5 | `$33a3` | `$0ad2` | 2769 | 0.56 s | |
| 6 | `$3e75` | `$0ad2` | 2769 | 0.56 s | byte-identical data to id 5 (2769/2769 bytes), separate header entry |
| 7 | `$4947` | `$0a14` | 2579 | 0.52 s | near-Nyquist tone (lag-1 autocorrelation -0.62) |
| 8 | `$535b` | `$0ab2` | 2737 | 0.56 s | ids 9..31 alias it |
| 0 | BT4, `$da5c` at `$201cc` | 55,900 | 55,899 | 7.28 s at 7680 Hz | the title tune (below) |

Gate 1 (`verify_psg.py`): poke the pending-sound cell, log `watch ff8800 8`, compare each tick's (R8,R9,R10) with the decoder: 23,813 of 23,813 ticks
exact over ids 1..8, and the captured tick count equals length - 1 for each. LABELLED POKE `w 17848 <id>` (the game's own request cell).

**Id 0 as played.** BT4 occupies `$201cc..$2dc28`. The level loader writes the map (`0` to `$201c8`, 12,804 bytes) and the tile file (`t0` to `$25f8c`
= `$201cc` + 24000) over it, so the tune plays 24,000 ticks of BT4 and then the first bytes of T0 until a newer request cuts it. Gate 2
(`verify_natural.py tl/t23.snap 20000000`, no pokes): 52,887 ticks logged, 52,887 explained: id 2 (8137), id 0 with the T0 overwrite (30,525 ticks until
the first effect), then ids 4 and 1 including interruptions. Whether this happens at the same tick on a real ST depends on disk timing (INFERRED).
This agrees with the systems doc (the title tune is loaded, then `0` and `t0` after the title).

## 5. Requests and arbitration

Effects are requested by storing the id in the long `$17848`; the frame driver (`$c956` in the routine at `$c900`, `$cc62` in `$cc36`) does once per
frame `tst.l $17848 / move.l $17848,D1 / bsr $105e8 / clr.l $17848`. So at most one request per frame reaches the voice and the last write in a frame
wins (`tally_requests.py tl/t25.snap 10000000`: 61 requests, 23 handed to `$105e8`; `tl/t26`: 93 and 46). `$105e8` ignores a request equal to
`$184ee`, the id in progress (id 4 requested twice 100,000 steps apart plays 1417 ticks once), and a different id restarts the voice (id 4 then id 5 cuts id 4
after 276 ticks and plays id 5 whole). Nothing resumes an interrupted sound.

Routes that write the cell:

| writer | mechanism |
|---|---|
| `$f526` via `$f51e` (D0 = id, 0 = none) | a shot/effect record in one of the three 14-byte tables (ai: H hero shots `$31592` x9, E effects `$31612` x30, P hostile projectiles `$317b8` x30) with word 12 bit 15 set; id = low 15 bits. The bit is set when the record is spawned with D3 = 0 (`$10838`, `$10b28`, `$10e0c`) or when its delay D3 counts down (`$10894`, `$10b84`, `$10e94`), by looking the record's type up in a per-table sound-id word table: `$18504` (H), `$18608` (E), `$1116c` (P) through `$10aee` / `$10e70` |
| `$d186 $d2fa $d33e $d364 $d37e $e12e $10992` | direct `move.l #n,$17848` |
| `jsr $105d8` x4 | shop purchases, id 7, direct (not through the cell) |
| `$eb2a` | `clr.w D1 / bsr $105e8`, id 0, direct |

The per-type tables (leading words, then unrelated data; extents INFERRED): H `$18504` = 4 4 4 0 2 1 1 5 0; E `$18608` = 0 0 0 1 2 0 0 0 0 0 0 0 0 1 5;
P `$1116c` = 0 8 8 8 8 0 5 8 0 1 5. Only the types the spawn sites actually use matter (section 6.1).

## 6. Which event requests which sound

### 6.1 By id

| id | event | route and proof |
|---|---|---|
| 0 | title tune | `$eb2a` in the title/attract entry, cut by `$ebec` (`$105c0`). `tl/t23.snap`: 1 start; gate 2 |
| 1 | an urn bursts (hero shot hits a container, map kinds 1/2) | `$d5e4` spawns E type 3, `$18608[3] = 1`. Live: hero beside the level-1 urn, fire held: `$d5e4` 1 hit and one id-1 request; control (hero 16 px lower, shots miss): `$d5e4` 0 hits, no id 1 (`events_misc.py`) |
| 2 | time over (the hero is killed by the clock) | `$d472` spawns E type 4, `$18608[4] = 2`. Live: `w 1eedc ffff0000` gives one id-2 request (`events_misc.py`) |
| 3 | the hero takes contact damage | `$e12e` in the hero contact handler (`$e016`), 242 steps after the invulnerability counter `$1eeb2 <- $14` at `$e05c` (live, level 4 snapshot, hero poked onto an item; `events_misc.py`). Also seen at level indices 4 and 7 in `events_drive.py` when the poke drops the hero onto an enemy |
| 4 | the hero attacks (three H shots of types 0, 1, 2 per attack) | `$d6b6` `hero_shot_spawner` (ai), `$18504[0..2] = 4`. The most frequent request: 51 / 68 / 63 / 65 per 10M-step demo window (`tl/t25 t26 t29 t30`), 18-27 per boss run |
| 5 | map kind `$10` (clears the screen's enemies, mechanics; `$d186`) and map kind `$1d` (a trap that fires a P shot of type 6 at the camera top, mechanics; `$d160`, `$1116c[6] = 5`) | kind `$10`: 8 of 8 levels request id 5 at `$d186`; kind `$1d`: 6 of 6 levels that contain it (2-7) request id 5 through `$f526` (`events_drive.py`; probe `events_probe.py`) |
| 6 | picking up map kind `$e` (key, `$d364`) or `$f` (hourglass, `$d33e`) (names from mechanics) | `$f`: 8 of 8 levels request id 6 at `$d33e`; `$e` forced into the item table (probe): `$d364` id 6. `$d37e` (the "class 4" case) is reached by no kind in the probe, so it is dead or needs a kind outside 3..`$21` (INFERRED) |
| 7 | picking up a coin kind 3..9 (`$d2fa`), and buying anything in the shop (`$105d8`) | kinds 3-9 forced into the item table: all 7 request id 7 at `$d2fa` (7/7; level index 2's natural kind-3 coin too). Shop `callcap $fa9c`, items 0..9: 10/10 affordable purchases set the current sound to 7, 0/10 refused ones do (the refusal path does not return from the callcap, it waits in its text loop) (`events_shop.py`) |
| 8 | a hostile projectile (P shot of types 1-4 or 7) is spawned: map kind `$1e` (periodic projectile trap, P type 2, `$d276`); a chest whose content roll is 6 (four P shots of type 3, `$d3c4..$d40a`); a spear thrown by actor type `$11` (P type 4, `$e824`, animation event `$e7e2`) | kind `$1e`: requests in 2 of the 6 levels that contain it (0 and 6; the trap fires only while the hero is within its window); chest with one key (`w 1f004`) and 12 RNG seeds (`w 3195c`): 5 request id 8, and they are exactly the seeds that reach `$d3cc` (the roll == 6 branch) (`events_misc.py`); boss arena of level index 6: 3 requests. Spear: code-read, INFERRED |
| 9 (= sample 8) | a hero shot hits terrain | `$109be` finds a non-zero `$1850c[tile class]`, spawns an effect (E types 1/2, silent) and sets `$31590`; `$10992` then requests 9. Fire held against a wall: 3-18 requests per run (`events_boss.py`, `events_misc.py` control) |

### 6.2 By map-object kind, across the eight levels

`events_drive.py` poked the hero onto the first record of every kind present in each level (`w 1f014 <x><y>`, 150,000 steps, `watch 17848 4`). Level
index 0 is `play_start.snap`; 1..7 are `agents/systems/lvl1..7.snap`. A kind that is not listed requested nothing.

| kind (mechanics' name) | levels containing it | request | in levels |
|---|---|---|---|
| `$0f` hourglass | 0-7 | `$d33e` id 6 | 0-7 |
| `$10` clear screen | 0-7 | `$d186` id 5 | 0-7 |
| `$1d` trap | 2-7 | `$f526` id 5 | 2-7 |
| `$1e` projectile trap | 0-3, 6, 7 | `$f526` id 8 | 0, 6 |
| `$0a` chest (one key poked) | 0-7 | `$f526` id 8 | 0 (roll-dependent) |
| `$03` coin | 2 | `$d2fa` id 7 | 2 |
| `$01` urn, `$11` shop man, `$12..$16` old men, `$13`, `$1b/$1c` doors, `$1f` checkpoint, `$20` exit | various | nothing on touch | |

The old men, doors, checkpoint and the shop man's opening (kind `$11`) are silent. Level-exit kind `$20`: no request on contact. Boss arenas (`events_boss.py`,
hero poked onto the exit object, the boss spawns: `$1eeb8 = 1`, `$1f020` type 1 on level indices 0 and 1, `$13` on index 6, fire held 2M steps): ids 4
(18-27) and 9 (9-18) from the hero's own shots, plus id 8 x3 in level index 6; no id is specific to a boss (nothing requests on boss spawn, boss hit or
boss kill in these runs). Map kinds `$0b`, `$0c`, `$0d` (vitality, +50 zenny) and the other forced kinds 10..`$21` request nothing (`events_probe.py`).

## 7. Rendering and numeric checks

The WAVs render the unsigned DAC output level of each tick at the true Timer A rate (4915 or 7680 Hz; the WAV header rounds 4915.2 to 4915), mean removed, scaled
by 1/2 so full scale cannot clip. The level of a triple (A,B,C) is taken from **Hatari's measured three-voice YM2149 table**, `src/includes/ym2149_fixed_vol.h`
(`volume_table[C][B][A]`, 16 x 16 x 16 values 0..65119, "data measured by Paulo Simoes", used by Hatari's `sound.c` as `volumetable_original`; read at render time from
`$HATARI_YM_TABLE` / `$HATARI_SRC`, not copied into the repo; checked here for 4096 values and symmetry under channel permutation). Without that file the renderer falls
back to a summed per-channel model (StSound-style table recalled from memory, INFERRED); the first renders of this agent used it, and its correlation with the measured table
over the 256 table entries is 0.9956.

`wav_check.py` (nobody can listen; the sheet image is a visual check that the waveforms are decaying audio, not noise):

| file | frames | = ticks | rate Hz | seconds | min / max | clipped | DC (LSB) | RMS |
|---|---|---|---|---|---|---|---|---|
| snd0 | 55,899 | yes | 7680 | 7.279 | -9527 / 9545 | 0 | -0.13 | 2492 |
| snd1 | 1,336 | yes | 4915 | 0.272 | -9556 / 9517 | 0 | 0.07 | 4121 |
| snd2 | 8,137 | yes | 4915 | 1.656 | -9527 / 9545 | 0 | -0.10 | 3900 |
| snd3 | 2,069 | yes | 4915 | 0.421 | -9533 / 9540 | 0 | 0.20 | 2594 |
| snd4 | 1,417 | yes | 4915 | 0.288 | -9546 / 9526 | 0 | -0.05 | 4639 |
| snd5 = snd6 | 2,769 | yes | 4915 | 0.563 | -9448 / 9624 | 0 | -0.06 | 4311 |
| snd7 | 2,579 | yes | 4915 | 0.525 | -5963 / 6286 | 0 | 0.25 | 2995 |
| snd8 | 2,737 | yes | 4915 | 0.557 | -9556 / 9517 | 0 | -0.08 | 3934 |
| snd0 as played | 55,899 | yes | 7680 | 7.279 | -11744 / 7328 | 0 | 0.05 | 6153 |

Ids 1..8 are additionally compared with a render of the **live captured** PSG triples (`run/verify_id<N>.out`): 8 of 8 WAVs equal sample for sample. The peak is about 29% of full scale,
so the files are quiet but never clip; the DC offset is zero by construction (mean removal) and the raw streams centre on byte 125-126 against a table centre of 127.5, i.e. the
game's samples carry no large offset of their own. The sheet shows the shapes: every effect decays to silence (the levels settle at the table's midpoint), the tune fades out, and the
tail of the as-played tune is the T0 tile data (clipped-looking block pattern), not audio.

## 8. Open items

* Boss kill, level-clear bonus, the continue/game-over/high-score screens and the ending were not driven for sound: no write site other than those listed exists, so they are silent unless
  they spawn an H/E/P record with a table sound (the boss kill and level-clear code were not read for that).
* Whether kinds `$0b`..`$0d` are silent by design or because the handler is reached only after another condition is untested beyond the forced probe.
* Whether `$d37e` (id 6) is reachable by any item kind; whether `$18504[3..8]`, `$18608[13,14]`, `$1116c[1,3,9,10]` (ids 1, 2, 5, 8) are ever produced by a spawn site: no spawn site uses them in the
  immediate or table-derived types read (`$d3c0` D4 6..8, `$109fc` from `$1850c`), so they are INFERRED unused.
* The shop man's menu itself (kind `$11`) was not driven live for the sound path; `shop_buy_item` was callcapped with the stack argument (section 6.1, id 7).
* Real-hardware timing of the BT4 overwrite, and the real Timer A rate (computed, not observable in the emulator).
* Nothing was listened to.

## 9. What was not exercised

Sound after leaving level 1's attract demo was exercised only through forced pokes (item kinds, exit object, shop callcap); no full natural playthrough of levels 2-8, no
boss kill, no ending. The 20M-step natural gate covers the attract demo of level 1 only.
