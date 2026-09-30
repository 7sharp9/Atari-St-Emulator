# Impossamole: secrets, the crack layer and the algorithms

What the player is not told (cheats, keys, dead code, the crack's trainer) and the non-trivial routines (the packers, the random number generator, the two
sound engines). Everything here was measured by the 107th-pass helper agent with scripts in `py/secrets/` (data and snapshots under
`scratchpad/impossamole/agents/secrets/`, indexed in `scratchpad/ANCHORS.md`); the parent re-ran the depacker check (755,712 of 755,712 bytes), the random
number generator (200 of 200 calls), the score gate and the `LUMBAJAK` and `HEINZ...` name entries. Statements marked *read* come from code only and were not
run; *inferred* is a guess. Run scripts from `M68000/` with `ATARI_NOTRACE=1 uv run python reversing/impossamole/py/secrets/<script>`.

## Cheats

The high-score name entry (`$19dfc`..`$19f58`) compares the typed 8 characters with the 8-byte names at `$1837e` (compare `$18348`..`$18368`, reached from
`$182bc`) and stores the match number in `$bb7d`.

| code | name | effect | mechanism | proof |
|---|---|---|---|---|
| 1 | `LUMBAJAK` | maximum health 34 instead of 18 | `$bb7e` sets `$22` at `$bb9e`..`$bbaa` | real chain `cheat_chain.py`: max 34, health 34 after the level installs (`$bbc8`) |
| 2 | `HEINZ...` | weapon 3 at every level start | `$bbe8`..`$bbf4`, `$bb72 := 3` | same chain: weapon 3, other names 1 |
| 3 | `COMMANDO` | a collected special weapon never runs out | `$d2fa` skips the `subq.b #1,$227fb` every 25 frames | `cheat_effects.py`: `$227fb` 30 to 25 in 3M steps without, stays 30 with |
| 4 | `ANNFRANK` | one extra life | `$bb7e` sets `$bb78 := 1`; at health 0 `$ec50` revives with max/2 and clears it, else Game Over | `$bb78 = 1` after `$bb7e`; health poked to 0 gives 9, `$bb78 = 0`, no Game Over in 6M steps |
| 5 | `OOCHOUCH` | water and hazard tiles do no damage | `$eb26`, `beq $eb5a` skips the foot-sensor test on category 9 | `cheat_water.py` into the Amazon pits: 5 hazard hits (`$eba2`) without, 0 with (31 of 33 frames on category 9) |
| 6 | `JUGGLERS` | heal pickups give double | `$12e92`, `asl.w #1,D1` on `4 + world` | callcap `$12e7e` at health 1: 8 without, 15 with |

- **The name is exact.** There is no keyboard: entry is a joystick-1 letter grid (32 cells at `$1a083`: A-Z, `@ . ! ?`, DEL `$fe`, END `$ff`; 8 columns by 4 rows,
  cursor `$19c1e` starts on END, one step per 6 VBLs, fire edge-detected once per loop pass). The name is fixed at 8 characters: the eighth pick ends the entry, a
  shorter one ends with END and is padded with blanks. So `HEINZ` + END is `HEINZ   ` and fails; the name is `H E I N Z . . .` (three full stops). There is no lower
  case. `cheat_entry.py NAME` types a name with real packets from `data/name_entry.snap`; all six gave `$bb7d` 1-6 and landed at rank 2, while `HEINZ`, `LUMBAJA`
  + END and `LUMBAJAL` gave 0.
- **Where and when.** The compare runs only in `$182bc`, the shared Game Over and ending high-score routine (Game Over by fire or the 250-frame timeout, and the
  world-5 ending), so it works on both. `$19f5a` enters the name only when the score ties or beats a table score (`cmp.l`, `ble`); the default table at `$184ef` is
  `R.AL 999999`, `TERRY 008000`, `ROB 006000`, `BOB GOTH 004000`, `GREGGY 002000`, so a run needs at least 2000 (`score_gate.py`: 2000 enters at rank cell 4, 999998
  at cell 1, 999999 at cell 0; 1999 reaches no entry loop). `$182c2` clears `$bb7d` on every visit, before the gate, so a cheat lasts one run (next title fire to
  the next Game Over or ending). The table lives in memory only.
- Cheats 3, 5 and 6 were tested with `$bb7d` poked (`$bb7a` longword, neighbours preserved), not by a name followed by play; the name to code step was proven
  separately, so the chain is covered piecewise.

## Keys the game reads

The game reads raw IKBD bytes itself (ACIA handler `$1c51a`): scancodes go to `$1c4bf`, joystick 1 (header `$ff`) to `$1c4c1`. Joystick 0 (`$fe`, `$1c4c0`) and
mouse packets (`$1c4c2`..`$1c4c4`) are written and never read anywhere in the whole-image listing. Init sends `$12` (mouse off) and `$14` (joystick event mode).
The only readers of `$1c4bf` (`hidden_keys.py`, `space_*.py`):

| key | scancode | where | effect |
|---|---|---|---|
| Esc | `$01` | main loop `$b1c2` | fade, `jmp $b088`, back to the title with no high-score entry (title reached in 243k steps); the score stays until the next `$bb7e` |
| Ctrl | `$1d` | `$1abdc`..`$1ac06` | pause: waits in `$1abf4` until the next `$1d` (camera frozen 6M steps, second Ctrl resumes) |
| Space | `$39` | `$ed52`..`$ed9e` | an undocumented one-per-level smart bomb, all five worlds (below) |
| Tab | `$0f` | `$1c434` | dead code: a raster-time profiler that flashes the border colour; nothing calls any of it |

- **The smart bomb.** Conditions: not in the shop (`$bb77 = 0`), boss not dead (`$22803 = 0`), `$227ff = 0`. It plays sound `$20`, saves the hero, sets `$227ff` to the
  world index and dispatches through `$ee16[world]` = `$ee2a, $f050, $f31c, $f5ea, $f868`. `$ee9a`..`$ef08` puts every enemy slot from `$1a5de` (five slots of 108
  bytes) whose `103(A0)` is neither 0 nor `$fe` into its death animation (`101 := 1`, animation from the `$fb60` table, sound `$1c`) and spawns eight effect objects
  from `$1a7fa`. The hero is frozen while `$227ff` is 1..5 (`$d14a`); `$faf2` then sets `$227ff := $ff` and restores it. `$227ff` is written only at `$ee06` and
  `$faf2` and cleared by the `$22784` block clear at each title, level and death start, so it is once per level: a second and third press did nothing (`$ed9a` 0 hits,
  `$227ff` stays `$ff`). Live enemy slots before and after in worlds 1 to 5: 2 to 0, 1 to 0, 3 to 1, 1 to 0, 1 to 0 (the survivor in world 3 has hit points `$fe`, the
  exempt value). Not tested: whether a room change re-arms it (the writers say no). Its slot range is 7-11, so the boss's slot 7 is inside it; the boss room was not tried (note the gate `$22803 = 0`, which is 1 while the boss is alive).
- **Title screen.** Joystick up and down set `$bb7b` to 0 or 1 (`title_toggle.py`): 0 is sound effects, 1 is music for the run (`$b12e` silence reset against
  `$b124` `jsr $1f968`); the two engines are mutually exclusive through the mute gate `$bb7a` (below). `$17c6e` draws glyph `$5b + $bb7b` at column 35, row 5.

## The crack layer

- **Boot.** The boot sector (checksum `$1234`) prints the Replicants menu. F1 does `Fopen("MST.IMG")` and `Fread` of up to `$80000` bytes to `$50000`, then `jmp $50000`;
  F2 returns to the desktop (`EMOTION+.PRG` is then started from it; inferred).
- **MST.IMG is the game.** A 484-byte stub whose banner (file offset `$77`) reads "AUTOMATION PACKER V2.2f", then an LSD!-packed 98,148-byte image (`mst.py`). It
  depacks to a stable base `$a8a8`..`$2280c`; live, `$b000`..`$1c800` matches RAM 70,294 of 71,680 bytes, `$1c800`..`$20000` 14,149 of 14,336 and `$20000`..`$2260c`
  9,740 of 9,740 (the rest is runtime variables). The first 1,880 bytes (`$a8a8`..`$b000`) are the crack's menu prefix and are overwritten later.
- **The prefix** (`data/crack_prefix.asm`): menu text at `$ac18` ("CRACKED TRAINED 'N' PACKED BY R.AL", "PRESS : 'T' FOR TRAINER", "UNLMT LIVE, MONEY & AMMO") and
  a bit-shifting scroller text at `$ade9` (534 bytes): the Replicants' greetings to about 30 crews, one crude remark, "BYE FROM YOUR MASTERS IN CRIME".
- **The trap #1 hook.** `$a91c`..`$a92a` copies `$aa22` (`$e2` words) to `$200`, saves the old GEMDOS vector `$84` into the trap #15 vector `$bc` and installs `$200`.
  The hook (`$200`..`$3c2`) calls the real `Fread` through trap #15 and, if the buffer starts with `LSD!`, depacks it in place (scratch copy at `$60000`). Every
  packed file the game loads is depacked by its own `Fread`, so `$1c6de` never sees packed data.
- **The trainer.** Any key leaves the menu loop; the key is upper-cased (`andi.b #$5f`) and `T` (`$a95c`) applies five single-byte patches, then `jmp $b000`:

  | address | before | after | effect |
  |---|---|---|---|
  | `$eb8c` | `91` (`sub.b D0,$bb74`) | `4a` (`tst.b`) | enemy contact does no damage |
  | `$ebcd` | `01` | `00` | water damage becomes 0 |
  | `$bbd3` | `00` | `fa` | the item counter `$bb73` starts at 250 each level |
  | `$fd4c` | `5b` (`subq.b #5,$bb73`) | `4a` | the 5-point drain of `$bb73` in `$fd0e` is gone |
  | `$d328` | `53` (`subq.b #1,$227fb`) | `4a` | special fire never runs out (as COMMANDO) |

  Proven from two cold boots (`data/cold_T.repl`, `cold_SPACE.repl`): with T the five bytes read `4a 00 fa 4a 4a`, with Space the originals. The label says lives,
  money and ammo, but the game has no lives (energy is the health); "money" is `$bb73` (purpose not decoded) and "ammo" is `$227fb`.
- **Protection.** A floppy-track-length check at `$bc80` (called at `$b006` and `$bc5c`) seeks track 0 and 79, does Read Track (`$e4`), compares the DMA counter after each
  and hangs in a colour-flash loop (`$bcbe`) unless the difference exceeds `$3c` (*read*). The crack disables it on every boot path: `$bc80` is `4e75` (verified live,
  both cold boots; the stray `ffff 8604` at `$bc82` is the tail of the original `movea.l #$ffff8604,A5`). The `DISK.ID` check (`$bbfe`..`$bc50`, `$1c7b6`..`$1c7f6`) is
  live: it `Fread`s 4 bytes of `DISK.ID` into `$1c7fc` and compares them with `$1c7b2` (`00ff00ff`, poked by `$bc46`), retrying every 150 ticks on a mismatch while
  " CRACKED BY THE REPLICANTS" (`$bc64`) shows. With the file present the title comes up after one `$1c7f6`; with it deleted, or its content `11223344`, it retried 6
  times in 12M steps and never passed (`disk_variants.py`). It tests the disk, not a copy: any copy that keeps the file passes. No checksum over the image was found
  (grep only, not a proof). Self-modifying code: `$1c6de` (operands `$1c70a`, `$1c710`), `$1c67c` (VBL vector chain), `$1c74e` (dead file writer).
- **The other files.** `EMOTION+.PRG` (7,094 bytes) is packed with JEK PACKER V1.2 (an Atomik-style LSB-first longword reader with an XOR check; `jek.py` depacks it to
  11,201 bytes, check word ending at 0): the E-Motion launcher ("PRESS 'T' FOR TRAINER / PRESS 'N' FOR NORMAL", credit page "BIG FOUR - THE REPLICANTS - ST AMIGOS
  Presents E_MOTION+ Cracked & trained by Snake"); its trainer pokes were not decoded. `E_MOTION` (309,398 bytes) is the E-Motion game itself, not analysed.
  `MINDBOMB.PRG` (19,840 bytes) uses a third packer (MSB-first longword reader with variable-length numbers, `mindbomb.py`; result `601a 0000f3b6`, 63,068 bytes): the
  "Mind Bomb" demo screen, nothing refers to it. The two `.PC1` files are LSD! then Degas PC1 (`pc1.py`: E-Motion title 16,158 of 16,158 bytes consumed, `PRES_ST` 9,695
  of 9,727; PNGs in `data/`). `DESKTOP.INF` is window and group config only.
- **Text census** (`strings_all.py`, `data/strings_all.txt`: every string of 5+ characters from every file, every depacked payload and the resident image): the only
  hidden strings are the ones above. The ending text (`$185e1`..`$187e9`) and the level names at `$18580` are referenced; the high-score names TERRY, ROB, BOB GOTH and
  GREGGY have no individual reference because a stride loop prints the rows.

## Dead and unreferenced content

Evidence is a whole-image listing (`data/full.asm`, `$2000`..`$43000` from `agents/unpoked/s11/seg11_shaft_exit.snap`) with no `jsr`, `jmp`, `bsr`, PC-relative or
pointer reference; computed jumps are not resolved, so items marked *lead* are not proven.

- `$beaa`: a second PRNG (state `$22798` long and `$227a8` word; rol, exg, eor, `eori.l #-1`) with no caller.
- `$1c434`..`$1c4bc`: the Tab profiler. `$1c74e`: a Fcreate/Fwrite/Fclose routine (D0 buffer, D1 count) with no caller and no save file on the disk: an unused high-score saver.
- **Engine 1's digital and song paths**: `$1c96a`, `$1ca12`, `$1cc82` (a Timer-A YM-volume sample interrupt), `$1cd76`, `$1ce3a`..`$1d0a0`. All 53 entries of the sound table
  `$1cabe` are type 1 (effect voices), so the other types are unreachable; `$134` is written only by the save and restore at `$1a1aa` and `$1a226`. That the original had
  digitised sounds is inferred from the silent slots below.
- **Silent sound slots**: indices 0, 34, 37, 40, 42, 46, 50 and 52 use record 0 (flags 0: no tone, no noise). Indices 37, 40, 42, 46 and 50 are the per-world ambient
  sounds played from `$fb76` (table `$fb92`), so each world's ambient sound is silent in this release. Index 10 (a variant of the hit sound 9) has no caller; 43 aliases 36, 47 and 51 alias 41 and 27.
- **Music module entries** never called: `$1e218` (854 bytes, an effect player with its own channel pair `$1f652`/`$1f694`), `$1e56e`, `$1ea6c` (stop), `$1eab4`, `$1eadc`
  (fade). Only "start song" `$1d6ec` through `$1f95e`, `$1f968`, `$1f972` is used. Removed calls left `rts` stubs at `$b3a4`..`$b3aa`, `$1ac0e`, `$1ac10`, `$1ac12`, `$1ac32`.
- **Spawn types** (`spawn_census.py`; descriptor table `$10474`, 253 entries, null at 89): kind-1 types with a descriptor and no static reference (lead): 26, 79, 83, 85,
  119, 120, 153, 154, 161, 212, 213, 221, 236. Kind-3 candidates are many and mostly spawned by code paths not enumerated (the boss shots 139 and 140 among them).
- `dead_code.py` lists 72 unreferenced code candidates, 27 in the game range (for example `$b9fe`, 144 bytes; `$1c134`, `$1c242`; `$14bbe`; `$153b8`; `$15dda`): lead only.
- Not examined: unreferenced sprite frames, unused room-exit records, a hidden level. `PICTURES.DCH` and `SELECT44.DAT` hold no sixth world.

## The packers

`$1c6de` is not a depacker. It is a GEMDOS file loader (`Fopen` function `$3d`, `Fread`, `Fclose`; D0 buffer, D1 count, A0 name; it patches its own operands). It asks for
the unpacked size, and the trap hook expands in place. `$1c68e` is the tail of the VBL wait loop `$1c686` (`cmpi.b #$96,$1a2e9`).

- **LSD!** (`lsd.py`, transcribed instruction by instruction from the hook at `$242`..`$3c2`; the stub banner names Automation Packer V2.2f, so LSD! is taken as that
  packer's tag, inferred). Header `LSD!`, u32 unpacked length U, u32 packed length P (file size minus 4 for all 21 files). The packed stream starts at file offset 12 and is
  read backwards from the end (after an optional pad byte if the last word is negative); output is written backwards. Bit reader: a byte with a sentinel bit (`lsl.b`,
  reload with `roxl.b`, MSB first). A token starts with one bit: 1 is a literal run (next bit 0: one byte; else a tiered prefix code, 2 bits + 1, 2 bits + 4, 3 bits + 7,
  10 bits + 14, an all-ones value escaping to the next tier, count = value + base + 1), then an end test (stream pointer at or below `$60008`); a match follows, its length by the
  number of leading 1s (2, 3, 4 + 1 bit, 6 + 2 bits, 10 + 10 bits) and its offset by length: 6 bits or 9 bits + 64 for length 2, else 5 bits, 8 bits + 32 or 12 bits + 288; the
  distance copied is offset + length. Colour 0 flickers (`move.w D5,$8240`) while it runs. The layout is in the Pack-Ice family (recalled, not checked against a reference).
- **MDATAn.DCH is packed twice** (`huff.py`). After LSD! the buffer is a static Huffman stream expanded by `$18812`: u32 N (51,200 = `$c800`), a 1,020-byte tree of words (a
  negative word is a leaf, low byte the output; a non-negative word is an offset to the next node), then the bit stream as words, MSB first. The result is exactly the
  `$25000`..`$31800` block (category table, spawn list, block map, block definitions, tile bank, collision map). LSD! barely shrinks these files (ratio 0.85) because they are
  already Huffman coded.
- **Proof.** All 21 LSD! files depack with the source ending exactly at the header and the destination exactly at 0 (`lsd_table.py`). Against each world's live RAM
  (`check_all_worlds.py`, five gameplay snapshots): `MDATAn` to `$25000` (51,200 bytes), `*22.DAT` to `$40600`, `*33.DAT` to `$4c400`, `CHARS11` to `$24000`, `SPRTS22` to
  `$3b600`, `SPRTS33` to `$42e00`: **755,712 of 755,712 bytes**. `PICTURES.DCH` (LSD!, Huffman, 64,000 bytes) is two ST low-res screens, the world select at `$25000` (palette
  `$21682`) and the title picture at `$2cd00` (palette `$21802`), 64,000 of 64,000 live in both states (`pictures.py`, PNGs in `data/`). `SELECT44.DAT` is 20,480 bytes of bank-2
  frames 100..152 (32x24, 384 bytes each) at `$4c400`, 20,480 of 20,480 (`select44.py`).

## The random number generator

`$bef4` (`prng.py`): state `s = $227aa` (16 bit) and four counters `c1..c4 = $227ac, $227ae, $227b0, $227b2` that `$beda` (from the gameplay VBL handler `$1a2c0`) increases by
1, 2, 3 and 4 per VBL. With X the extend flag at entry: `d = s; for c in (c4, c2, c3, c1): d = d + c + X (X = carry out), then ror.w 1`; then `for c in (c3, c1, c4, c2): d ^= c, then
ror.w 1`; store `d` to `$227aa` and return it in D7.w (`ror` leaves X alone, so the caller's X feeds the first add). Proven: `bp $bef4` and `bp $bf58` over live play, 600 of 600
calls on the Amazon snapshot and 600 of 600 in the boss room (callers `$fb6e` and `$ff12` every frame, `$15fd6`, `$16010`, `$16198`); the parent's re-run gave 200 of 200. Every
sample had X = 0 at entry, so the X = 1 branch is exact from the code and unexercised.

- **No external seed.** `$22784` (called by `$b05e`, `$b088`, `$b0ee`) zero-fills `$22798`..`$22806`, so the state and counters are 0 at every title, death and level start (`prng_seed.py`:
  40 VBLs advance the counters by 40, 80, 120, 160). Randomness depends only on the VBL count since the reset and the call sequence, so identical input timing gives identical
  results; a game frame is 2 VBLs (about 24,000 steps). With counters frozen the map is a bijection when all are 0 and near-bijective otherwise (65,532 of 65,536 images), longest
  cycle 798 for counters 1, 2, 3, 4; the counter vector repeats every 65,536 VBLs (`prng_period.py`).
- Consumers: the re-spawn `$ff0c` (`andi.w #7`, then `(s >> 8) & mask` picks a record), the drops `$179d8`, enemy AI and the boss's script (`$15fd6`, `$16010`), the type-140 shot's speed (`$16198`).

## The sound engines

Two engines share the YM2149; `$bb7a` selects one (`$1c840` and the VBL step `$1c9b2` run only when it is 0, the music VBL `$1d814` and Timer B `$1f950` only when it is not).

**Engine 1, effects** (`$1c840`, D0 = index 0..52). Table `$1cabe` has 53 entries of 8 bytes (word type, word record index, long); all type 1. Record at `$1d430 + 13 * index`:

| byte | field |
|---|---|
| 0 | attack step (added to the level per VBL) |
| 1 | decay step (signed) |
| 2 | sustain level |
| 3 | release step (signed) |
| 4 | peak level (0..127) |
| 5 | sweep delay in VBLs (255 = never) |
| 6 | sweep half-period count (bit 7 = stop after the first segment) |
| 7-8 | sweep step, little-endian word added to the period per VBL, negated each half period |
| 9 | flags: bit 0 tone, bit 1 noise, bit 2 hardware envelope (registers 13, 11, 12 written at start) |
| 10-11 | base tone period, little endian |
| 12 | hold duration in VBLs |

Three voices (26-byte structs at `$1d0a4`, `$1d0be`, `$1d0d8`, mixer shadow `$1d0a2`) are allocated round-robin (`$1cc79` bits 0-1, bits 4-6 lock a voice). Envelope handlers: attack
`$1d2d0`, decay `$1d2f4`, sustain `$1d318` (holds until the duration word reaches 0), release `$1d328`. Each VBL (`$1d1d0`) writes 11 YM registers in a fixed order: 7 (mixer), 0..5 (tone
periods, base + sweep offset), 6 (noise, the low period byte of the last noise voice >> 3), 8, 9, 10 (level >> 3). The model in `sfx_engine.py` takes its start state from live RAM;
`sfx_live.py` patches a trigger and an entry filter into the running game in RAM only and logs `watch ff8800 4`. **All 52 indices, 333 VBLs each: 189,332 of 189,332 register writes
match** (`sfx_check.py`); four effects in a row use voices 0, 1, 2, 0 as modelled, 600 of 600 writes over 60 VBLs (`sfx_multi.py`). Unexercised: entry 0 and mid-effect start states.
`data/sfx_inventory.txt` lists every effect with its record, audible length and callers (weapon swipes are 13..15 and 16..18).

**Engine 2, the music module** (`$1d6ec`). Three songs: `$1f95e` song 0 (title, from the `$b088` path), `$1f968` song 1 (the level tune, only when `$bb7b = 1`), `$1f972` song 2 (Game Over
`$b076` and the ending `$b0e2`); song table `$1f97c`. A song header is three longs (one per YM channel); a track is a list of longs pointing at patterns, 0 loops to the start, negative ends. The
per-VBL step is `$1d814`, with sub-tick effects from Timer B (`$1f916` sets event-count mode, data `$80`, vector `$120` to `$1f950` to `$1d92e`); one row every tempo VBLs (`$1eb36`). Pattern
byte code (`$1da0a`, `music_seq.py`):

| byte | meaning |
|---|---|
| `$00`..`$5f` | note |
| `$60` | loop end |
| `$61` n | loop start, n times |
| `$62` addr | call (long aligned to even) |
| `$63` addr | jump |
| `$64` t | transpose |
| `$65` | flag `$1eb34` |
| `$66`..`$7f` | ignored |
| `$80`..`$bf` | length = byte - `$7f` rows |
| `$c0`..`$df` | instrument (table `$1f988`, 22 records of 16 bytes) |
| `$e0` p n1 n2 | glide (n2 played, gliding from n1) |
| `$e1`..`$ef` | channel parameter |
| `$f0`..`$fe` | tempo = byte - `$ef` |
| `$ff` | pattern end |

The period table is 96 words at `$1f6d6` (equal-tempered, C1 3822 to B8; note 96 reads the next table `$1f796`). Proof at note and time level (`music_live2.py`, `music_live.py` logging `bp $1dd22`,
`music_check_songs.py`): song 0 **400 of 400** live note-ons equal in (channel, note, transpose, length, instrument) and order, 399 of 399 gaps within 1 VBL (an earlier 1,200-event run matched
1,200 of 1,200); songs 1 and 2 400 of 400 and 399 of 399. Base period `74(A0)` equals the table word at `note + transpose` in 149 of 150 note-ons; the outlier is note 84 + transpose 12 = 96, a
song-data quirk in the title tune. One pass: song 0 is 2,880 rows (17,656 VBLs, tempos 6, 7, 8), song 1 3,136 rows (18,816 VBLs, tempo 6), song 2 a 16-row jingle (128 VBLs) looping on channel 1.
**Not done**: a register-level replay against a live YM log (the music writes from both the VBL and Timer B, and the REPL has no interrupt-entry log); the instrument record fields (`$db64`..`$dc6e`) are
*read*, not verified. So a port has a proven sequencer and unverified instrument synthesis.

## Other routines read

Palette fade `$1c3c8`: eight steps of 2 VBLs, each decrementing every non-zero R, G and B nibble of the 16 palette words (fade to black) (*read*). The score is a plain decimal longword `$bb6e`;
`$19c32` formats six digits and `$19c98` parses them back (a `mulu` by 10 scheme) (*read*).

## Open

Music at register level; instrument semantics; E-Motion's trainer pokes and internals; the `$fd0e` / `$22801` mechanism (why the trainer's money poke targets `$fd4c`); a sprite-frame reference
census and unused room-exit records; kind-3 spawn types; whether a room change re-arms the smart bomb.
