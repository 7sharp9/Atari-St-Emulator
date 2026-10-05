# Crude Buster: the world around the fighters (levels, flow, text, props, hit boxes, demos, flags)

Agent WORLD. Addresses are 68000 addresses of the decrypted `cbuster` image. Every claim carries its count and the script that reproduces it (`README.md` lists the scripts, `py/gates.sh` re-runs the three gates in about six minutes). *read* = read from the code, not run; *inferred* = guessed from structure or screenshots. Pictures are in `shots/` (contact sheets of forced spawns, attract screens, clear sequence).

## 0. What changed against the brief and `architecture.md`

- **Pool C is not "effects".** Its 44 types are the **enemy attack hit boxes**: the `$22040` handler copies the owner's facing and frame (`+4`, `+20` from the record at `+28`), runs the player hit test `$fa10`, then clears its own 32-byte record in the same pass (`$22526`). A hit box therefore exists for exactly one frame and is re-created every frame by the owner's attack state; a census sampled at frame end can never see one (6 census runs saw only types 4 and 22, the two multi-frame handlers `$220ac`, `$2227c`). Damage is in a ROM table (section 6).
- **Pool B is props, hazards, decoration and small particles; there is no pick-up in it.** The only health item found is a **pool A** record, type 61 (`$1e706`, +8 energy, section 5). No bonus/score item was found at all: destroying a prop gave no score in 84 of 84 forced types (`out/f/force_hit0.txt`, score cell `$8013c` never changed).
- **`$8624`/`$86be` are screen wipes**, not the clear tally. There is **no score tally** after a level: the clear sequence is three text pages, then the next stage card (section 2.3). `$172a` is the clear sequence, `$71c` the level counter.
- **`$80016` is a shared state word** of five different scene runners (`$4a9e` intro, `$4076` title, `$6c94` best scores, `$5fba` ending, plus `$40ee`'s table); which one owns it is given by the caller.
- **Level scripts never use the vertical trigger bit** (0 of 449 entries have bit 15 set, `py/scriptdump.py`); stage 6 climbs because of its scroll map, not because of the scripts.
- The 'STAGE 1' card with the Power Cola picture exists only for the *following* stages; the first card is plain red text on black (section 2.2).

## 1. The top-level state machine

`$600` reset, `$66c` attract loop, `$696` game start, `$6be` frame loop, `$71c` level end (architecture.md has the call order). Observed on a cold boot with no input (`py/transitions.py` over `lua/framelog.lua`, `out/demo/framelog_long.csv`, 16,800 frames; screenshots every 50 frames in `run/att/snap`, contact sheets `shots/att1.png` to `att3.png`):

| frames from boot | routine | `$80016` state | screen (screenshot) |
|---|---|---|---|
| 0-76 | `$4a9e` intro | 0 `$4b2a` | skyline pictures load in columns (palette `$ff72`, graphics `$4ae00..$4b400`) |
| 77-329 | | 1 `$4bae` | skyline, big red text `NEW YORK / A.D.2010` (`$3370` id 0) |
| 330-369 | | 2 `$4c42` | skyline with the sun and a silhouette (sprites via `$51cc`, `$5446`) |
| 370-1124 | | 3 `$4ca2` | white nuclear dome, typed text `NUCLEAR EXPLOSIONS OF UNKNOWN ORIGIN ...` and `AND THE MASSIVE METROPOLIS WAS ALL BUT DESTROYED.` (`$5878` ids 1, 2) |
| 1125-2386 | | 4 `$4db8` | `AND 20 YEARS AFTER` over the DEAD END picture, `THE RESTORATION PROCESS HAD BARELY BEGUN ...`, `THIS ORGANIZATION IS CALLED BIG VALLEY ...` (`$3370` 3, `$5878` 3, 4) |
| 2387-3255 | | 5 `$4e9c` | `AND NOW`, handshake picture and TOP SECRET document, `THE GOVERNMENT HAS REQUESTED TWO MEN ...`, `THESE TWO MEN WILL BE PAID WELL FOR THE JOB ...` (`$3370` 5, `$5878` 6, 7, 8) |
| 3256-3712 | | 6 `$50a6` | the two heroes, `"CRUDE BUSTER"`, `ONWARD, CRUDE BUSTER! LET NOTHING DEFEAT YOU!` (`$3370` 9, `$5878` 9) |
| 3713-4306 | `$4076` title | 0-6 table `$40ee` | sky pan, CRUDE BUSTER logo, `INSERT COIN`, `DATA EAST  (c) 1990 DATA EAST CORPORATION`; `$80041` bit 2 set for the whole phase (3713 to about 4300) |
| 4307-5054 | `$762` demo | `$80018` = 0 | two-player demo 0 on level index 1 (stage 2); replay starts at frame 4417, 633 frames |
| 5055-5606 | `$6c94` best scores | 0-3 table `$6d20` | hero silhouettes, `BEST SCORES` (10 entries), ends with the `DATA EAST PRESENTS` logo |
| 5607-9238 | `$4a9e` again | 1-6 | the same story, 3632 frames (first pass 3636) |
| 9239-9832, 9833-10575 | title, demo 1 | `$80018` = 1 | demo on level index 2 (stage 3), replay from 9942 |
| 10580-11131, 11132 on | scores, intro | | then demo 2 on level index 3 (stage 4), replay from 15468 (`py/demo_check.py`: segments `[4416,5049,0,lvl1] [9941,10574,1,lvl2] [15467,16100,2,lvl3]`) |

The cycle is 5,526 frames: the demos start at frames 4307, 9833 and 15,359 of the boot (the replay frames 4417, 9942, 15468 of `py/demo_check.py` follow 110, 109 and 109 frames later). The `$4a9e`/`$4076`/`$6c94`/`$5fba` runners all loop `lea table; D0 = $80016*4; jsr (table[D0])` until `$80016 == 7` (intro, title, ending) or `== 4` (best scores). `$80041` bit 2 is set at the start of `$4076` (`$407c`) and cleared at its end (`$4328`): observed 3713 and about 4300.

## 2. Game flow

### 2.1 Game start, per-level setup (`$696`, `$1444`, `$1488`)

`$e3c` (called from the VBL handler) on a start press with a credit: clears both player flags, sets the pressing player's flag (`$80100` or `$80180` = `$80`), subtracts a credit with `sbcd`, sets `$80040` bit 7 and jumps to `$696` (checked: frame 701 in `out/c/census_l0.txt`, `$80040: 00>80` and `$80032` credits `01>00`). A second player joins later through `$ee8` (blocked when `$80040` bits 3, 5, 6 or `$80041` bit 3 are set, read). `$1444` clears `$80014`, the effect lists and sets the level byte to 0 (this is the write `startlevel.lua` replaces). `$1488`, per level:

1. clears the frame counter `$8004a`, the scroll/work block `$80400-$83dff` (`$c9a`) and the layers, palette fade-out through the mailboxes (`$70c2` waits until the VBL handler consumed them);
2. level 0 only, and only in a real game: big text `STAGE` + stage digit (`$28fa` ids 17 and 11), 64-frame wait (`$c8c`);
3. depacks the level graphics (`$81c4`), then palettes: `$7098` writes `$70b6[level]` = 1..6 to mailbox `$8000a` (sprite palette block), `$706e` writes `$708c[level]` = `$1111, $2121, $3131, $4141, $5151, $6162` to mailbox `$80008` (tile palette blocks);
4. music: `$e1c` with `$1532[level]` in a game, `$153e[level]` in the attract demo: level 0..5 = **1, 7, 9, 8, 7, 6** in a game, **6**, 7, 9, 8, 7, 6 in the demo (read; sound ids are the SND agent's);
5. `$154a` resets the players (energy `$38` at `+0x13`, positions `$80108/$8010c` = `$170/$1c0` for P1, `$140/$1c0` for P2; level 5: y `$7c0`; level 0 in a game: P1 starts with the walk-in state `$80103 = 1`), `$12ae` loads the timer word `$80042` (`$0300` from `$12f8` in a game, `$18` in the demo, where `$1308` counts it down one step per 63 frames and the demo ends at 8), `$8624` with effect 2 (the grid wipe in), `$129e` (`HI-` and the hi-score), and for level 3 sound `$50`.

Scroll counters after a level start: `$8040a` (x) = `$100`, `$80406` (y) = `$100` except level 5 where `$80406` = `$700` (observed, `out/c/census_l5.txt`). Level 0's start card: red `STAGE 1` for 64 frames, then the 98-frame grid wipe and the player walk-in with comic text (`shots/st0.png`).

### 2.2 The six levels: lengths, scroll maps, lock rules

The scroll engine is `$886c` (called from `$7fe4`): `$8876` looks up one word of the level map `$8908[level]` at index `(sy_page-1)*16 + (sx_page-1)` (page = high byte of `$80406`/`$8040a`, words in `py/scrollmaps.py`). Word fields: low nibble = **blocked directions** (bit 0 up, 1 right, 2 down, 3 left; stored in `$80401`), bit 5 (`$20`) = **hold zone**, bit 6 (`$40`) = **forced scroll**, bit 7 (`$80`) = **end of area** (scroller skipped). Scroll requests are bits of `$80400` (bit 1 right, bit 2 down, bit 0 up) set by `$a712` (player x beyond scroll+`$90`, refused while the pool A live count is 5 or more: `$81e03` bit 7) and `$a7f6`; `$8ade` masks them with the lock nibble into `$80402`; `$8ba2` moves x by one pixel per frame (`$80428` is the matching background scroll). Hold zones freeze the scroll while **`$80400` bit 5 is set, which is set by 25 handlers (the lock holders) and cleared by 12** (`py/flagops.py 80400`; confirmed live: in stage 1 the scroll stopped at `$8040a = $200`, page 2 = `$200d`, with the stone-slab wall B29 alive, and moved again once it was destroyed; `$80400` read `$a2` while stuck, `$00` after).

| level (stage) | map | scrollable x range | other | last script trigger (A / B) |
|---|---|---|---|---|
| 0 (1) | 8 pages `000d 200d 000d 000d 200d 000d 000d 800f` | `$100`-`$800` (1792 px), hold zones at pages 2 and 5 | page 8 frozen (boss arena) | `$800` / `$7b0` |
| 1 (2) | `000d 000d 200d 000d 200d 000d 200d 800f` | `$100`-`$800`, hold zones pages 3, 5, 7 | | `$7e0` / `$728` |
| 2 (3) | 10 pages, hold zones 3, 5, 8 | `$100`-`$a00` (2304 px) | | `$a00` / `$8e0` |
| 3 (4) | 10 pages, hold zones 6, 8 | `$100`-`$a00` | | `$a00` / `$990` |
| 4 (5) | row 1: 4 pages right then `000b` (page 5: **down only**), row 2: page 5 hold zone then 3 pages right | x `$100`-`$500`, one page down (`$80406` `$100` to `$200`), then `$500`-`$900` | `$1948` special-cases `$8040a == $500`: boss arena | `$8f0` / `$880` |
| 5 (6) | 7 rows x 16, starts in row 7 (`$80406 = $700`): 3 pages right, then diagonal **auto-scroll** pages (`400c` up+right, `400d` right) climbing row by row to row 1, page 14 | | players are placed by `$773c` relative to the scroll (x +`$70`, y `$b0`) in the stage 6 band `$390 <= sx < $c98` | `$ee0` / `$eb0` |

Idle rule `$1948` (read): when the scroll has not changed for `$400` frames (counter `$8053c`, last scroll `$8053e`) with no boss event and no lock holder, `$28fa` draws an eight-frame graphic message (ids `$32`-`$39` = 50-57, tiles at `$a061e`, frame chosen by `$8004b`, probably the GO arrow: *inferred* from the table, not seen); id 58 erases it while the scroll moves. Stage 5 at page `$500` uses ids 59 and `$3c`-`$43` instead.

Level scripts (list A `$6c000`, list B `$6d000`): triggers are horizontal only; per level entry counts A = 42, 33, 59, 32, 60, 47, B = 26, 57, 25, 34, 28, 6 (`static_gate.py`); full dump `out/scripts.txt`.

### 2.3 Clear sequence, stage cards, game over

Level end (`$6f4`: `$80040` bit 4 -> `$71c`; verified end to end with `lua/clearpoke.lua`, which sets the bit by poke from a level-1 state, `out/cp/clearpoke.csv`, screenshots `shots/cp0.png`, `cp1.png`):

| step | frames after the bit is set | what |
|---|---|---|
| `$71c` -> `$8624`, `$804ae = 6` | 1-102 | grid wipe out (effect 6 of `$8758`), `$80041` bit 0 set |
| level byte +1 (`$738`) | 103 | `$80046` 0 -> 1 observed at r = 133 of the log |
| `$172a` | | sound 1, `$80041` bit 3, palette `$fff1`, depack the result screen (`$51000` to `$aa000`), scroll `$100/$100`, **pool B type 40 (POWER COLA poster) spawned at scroll+(`$80`,`$c0`)** (`$21efa`, D6 = 40) |
| three text pages of 128 frames each | 128 + 128 + 128 | `NICE FIGHT!` (`$1c8a` 8), `STAGE n CLEAR` (9), `GO TO NEXT STAGE!` (10); the pool B runner `$2c0ce` and the players `$7626` run, no pool A |
| stage card | until `$80040` bit 4 clears | big red `STAGE n+1` (`$28fa`: id 17 plus digit id 11+level) with the poster; the loop `$183c` exits when bit 4 is clear |
| `$1488` for the new level | 98-frame wipe in | gameplay at the next frame (r = 809 in the poke test) |

Observed: the card loop ran from about r = 520 to r = 700, where the poke test cleared the bit (`CB_UNPOKE`); the loop left at once and `$1488` and level 1 followed (`out/cp/clearpoke.csv`: `700 1 80 8`, `701 1 80 0`, `711 1 80 1`, `809 1 80 0`). **Who clears the bit in a real clear is not proven**: the only writer is `$da14` (`bclr #4,$80040`), state 5 of the routine entered at `$d878` after 32 frames; it uses the same record fields (`+5` state, `+87`, `+90`) as the players' victory routines `$c83a`/`$c86a`/`$ca6e` that set the bit, and `$172a` runs `$7626` (players), not pool A. *Inferred*: bit 4 is set and cleared by the players' victory state machine; the poke test hangs because the players are not in it (this is the hang the brief reports). There is no score tally anywhere in `$172a`/`$1ab2`/`$2c0ce` (read).

Game over: both player flags clear at `$6fe` -> `$70c` sets `$80040` bit 5, `$188e`: sound 13, palette, `$8624` effect 6, `GAME OVER` big text (`$28fa` 19), 256 frames, then `$752`/`$758` (`clr.w $80040`) and the attract loop. Observed in the long census runs: `$80040` `80>a0` (frame 20446 of `census_l1`), `a0>00` at 20809, `$80041` bit 4 (continue prompt) and `$8005a` bit 6 about 630 frames before. Continue (`$7a86`, `$7b2e`): after a player dies with credits, the prompt `CONTINUE?` counts down from 9 (`$8005a` bit 6 marks the running timer; the player-record bytes `124/125(A6)` and `126/127(A6)` count nine steps of 63 frames, `$7aa0`/`$7b4c` load 9), the other player's button or start continues (`$7c98` takes a credit with `sbcd` and re-enters at `$76d0`, sound `$59`); expiry goes to the high-score check.

High scores: 10 entries of 4-byte BCD at `$80080`, 3-letter names at `$800c0` (4 bytes each), defaults written by `$6c24` at reset: scores `1000000, 900000 ... 100000` and the developers' initials `AKR INO AKI OTA H.K TII ANY NOA IUM !EA` (`$6c44`, `$6c6c`, `strings.md`). `$7dc8` compares `60(A6)` (the player's score) with entry 9; when it qualifies the player enters the name: left/right (`$7e26`) cycle through `A-Z 0-9 ! , . - ? &` (`$7fba`), buttons advance/confirm, `$7f5e` inserts the score and name into the table (down-shift, 10 entries). **Not exercised in this pass** (no run reached a qualifying game over): read only.

The ending (`$5fba`, 7 states, table `$600e`; the `CONGRATULATIONS.` page `$602a` is `$3370` id 14): 0 `$606e` picture load, 1 `$611a` music 14 and picture, 2 `$6162` dialogue (`HEY,WE MADE IT!`, `WE'VE GOT A BIG PRIZE.`, `YEAH....IT WAS A BIT HARD,THOUGH!`, `GET OUT OF HERE AND HAVE A DRINK,PAL.`, `OK!`, `THANKS TO CRUDE BUSTER....` ...), 4 `$62b8` (`CRUDE BUSTER.... BORN TO FIGHT NOT ALWAYS FOR THE CRUDE OF JUSTICE.`, `KEEP GOING ON, "CRUDE BUSTER", FOR ANOTHER COMBAT!!`), 5 `$631c` staff roll (`$1c8a` 60-68: `GAME DESIGN`, `CHARACTER DESIGNS`, `BACKGROUND DESIGNS`, `PROGRAMS`, with the Japanese staff names, `strings.md`), 6 `$65c4`. All strings are in `strings.md`; the ending was **not played** (read only).

## 3. Text

Four text writers, all writing tile codes into the text layer (chip 0 playfield 1 at `$a0000`; the code is the tile number ORed with the attribute word):

| routine | table | format | speed |
|---|---|---|---|
| `$1c8a` | `$1cce` (65) | records `attr.w dst.l` then ASCII bytes; a code with bit 7 set is a 16-bit marker (`$ffff` end, `$fffe` next record); **tile number = ASCII**; codes `$60`-`$69`, `$71` are icon tiles | instant |
| `$5878` | `$5930` (19) | `attr dst` then ASCII bytes, `$ff` end, `$fe` next record + one pad byte; byte 0 = a blank cell (pause) | one char per 4 frames |
| `$3370` | `$3456` (24) | `attr dst` then 16-bit glyph codes, each drawn as a 2x2 tile block (`D0`, `+1` below, `+2` left of the cell, `+3`); `$ffff`/`$fffe` as above | one glyph per 8 frames |
| `$28fa` | `$2962` (80) | the same 2x2 glyph codes, instant | instant |

The 2x2 font with attribute `$e000` is the red logo font: **letter = `$b4 + 4*(c - 'A')`, digit = `$8c + 4*d`**, `$b5c` and `$a38` are `.`, `$6e0`/`$6e4` open/close quotes, `$83c` a blank. Proof: every `$e000` string of `$28fa` and `$3370` decodes to English (`strings.md`), and the ones on screen match the screenshots (`NEW YORK A.D.2010`, `20 YEARS AFTER`, `AND NOW`, `CONGRATULATION`, `CONTINUE`, `STAGE`, `GAME OVER`, `BEST SCORES`, `PRESENTS`, `"CRUDE BUSTER"`; screenshots `shots/att2.png`, `st0.png`). The `$d000` strings of `$3370` use a per-text painted font whose glyph ids are numbered by first appearance (ids 19c, 1a0, ... run in order), so the letters cannot be recovered from the ROM tables alone; ids 1, 2, 4, 6, 7(part), 8, 10, 11, 15 have no immediate-D7 caller (`py/d7callers.py`) and 12/13 are the `$a1a` coin/continue message (read). `strings.md` lists **every string with address, attribute and destination** (427 lines, generated by `py/strings_dump.py`; the four tables are decoded to their ends, 65 + 19 + 24 + 80 entries). The default best-score table, the name-entry alphabet and the number-digit map are at the end of it. Copyright/warning text (`$1c8a` id 1, `$1e18`) and the ROM-exported staff list (ids 60-64) are in `strings.md`; ids 31-49 are developer-screen labels with no caller (`$18ce` is called by nothing).

## 4. Pool B: types, classes, usage

Method: (a) handler address from `$10558` (46 distinct handlers for 84 types), (b) script use from `$6d000` (`py/scriptdump.py`), (c) code spawn sites: callers of the spawn helper `$21efa` whose D6 immediate is the type (`py/callers.py`, a literal-only scan, so incomplete), (d) census of six bot-driven runs (`lua/census.lua`, 30,000 frames each; the bot with god mode only reached stage 1 page 7 and the first screens of the others, runs 2-5 continued into the attract demos after a game over, so stages 3-6 columns also contain demo spawns), (e) a **forced-spawn harness** (`lua/forcespawn.lua`): load a stage state at frame 1300, write one record into pool B slot 12 (`free` = 192 px right of the scroll edge at floor height, `on` = on top of P1, `hit` = 28 px in front of P1 with P1 punching five frames in every twenty), run 100 frames, log the record, every other new record, P1/P2 score, energy and lives, and screenshots at frames 4 and 50. 85 cases (84 types + a no-spawn baseline whose spawns are subtracted) x 3 modes x 6 stages are in `out/f/force_pv*_B.txt`, `force_hit0.txt`; contact sheets `shots/B_pv*_N.png`.

Findings that hold for the class, not the single type:

- **Spawn helper `$21efa`** (read): finds the first free record among B slots 0-23 (24-31 are reserved for script entries whose type has bit 7 set), copies type, variant (`+16`), facing and position from the caller, and stores a two-way link (`+60`) unless the type is `$2b`. Type `$2b` (43) is the *comic hit text*: position given in D4/D5, variant = which burst.
- **Class `$28df4`** (types 6, 7, 11, 12, 16, 17, 36, 44, 66, 67, 68) and **class `$290e4`** (8, 9, 10, 13, 14, 15, 37, 63, 64) are **liftable props** (poles, signs, board stack, trash can): they sit still, `+17` bit 7 (touched) and bit 6 (grabbed) are set by the players' grab code, the object then follows the player's frame offsets (`$29000`), sound `$54`/`$53`, and when grabbed both classes spawn comic text `$2b` variant `$10` (THOOM) at the object and play sound `$54` (`$28df4`) or `$53` (`$290e4`); class `$290e4` also spawns type 38 (`$26`) (read). They are not destroyed by punches (0 of 20 of these types died in the `hit` test), and they carry the pick-up hint of `$2c2c4`: **a two-frame blinking `PICKUP!!` burst drawn for 192 frames after the object enters the screen, only while the level index is below 3** (read: `cmpi.b #3,$80046`, counter `28(A6)`; seen in every forced sheet of stages 1-3, absent from the stage 4 sheet `shots/B_pv3_3.png`). The same file has the blinking `BREAK!!` hint `$2c358` (comic text variant 20) and `BUTTON!!`/`ROLL!!` are comic-text variants 18 and 19.
- **Lock holders** (class `$29694`: types 24, 28, 29, 30; and `$298ea`, `$29bbc`, `$29f78`): set `$80400` bit 5 (`bset #5,$80400` at `$296c0`) and clear it when destroyed (`$29872`). Punches produce `KRAK` sparks (comic text variant 4 at frames 12, 52, 92 of the `hit` test) and **wear the wall down**: standing against the level 1 type 28 wall at x 480 and pressing b1 every 6 frames raised its +5 counter 0, 1, 2 and removed the record about 150 frames after the first jab (`player/lua/walllab.lua`; the same in the natural level 1 run at frame 943 and 3448, level 3 at 3977 and level 4 at 959, `player/natural.md`). The `hit` test above ran only 100 frames, which is why it saw sparks and no death. The stage 1 wall B29 was also removed by throwing a liftable prop (census run: scroll stuck at `$200` from about frame 1470, `$8040a = $25d` by frame 1770 after the bot's stuck-pulse picked up and threw a can); whether a thrown prop or the pulse's jabs removed it was not separated.
- **Breakables**: B27 (oil drum) dies on the first punch (frame 12), spawning white puff B33 and `KRAK`; B26 (grey machine) after three punches (frame 32) with puff and `WHAM` (variant 12); B32 (flame) the same; B58 (red burst) dies at frame 12.
- **Hazards**: B4/B5 (handler `$28d60`) cost **10 energy** on contact (`$38` -> `$2e`) and knock the player down with `BAM` texts; B58 costs 1. Both are level independent (6 of 6 stages).
- **Comic hit text B43** has 21 variants (0-20): 0/1 plain red bursts, 2/3 `POW`/`BAM`, 4/5 `KRAK`, 6/7 `ZAP`, 8/9 `BOOM`, 10/11 `CRUSH`, 12/13 `WHAM`, 14/15 `BANG`, 16/17 `THOOM`, 18 `BUTTON!!`, 19 `ROLL!!`, 20 `BREAK!!` (the odd variants of 2-17 draw the word on a burst, the even ones without; 2/3 are a stylised word that reads like POW/BAM; 21 of 21 variants spawned and drawn, `shots/V0_0.png`, `V0_1.png`); life 16 frames.
- **Cinematic/decoration**: B40 POWER COLA poster (also the clear/stage-card picture), B38 arc, B46 red door (spawns four B47 chips), B48 window (spawns shards B49, 5 variants), B56 brick wall that collapses into B43 and four B57 chunk variants, B72 striped screen (spawns 14 B73 chip variants), B0/B59/B61 are wide foreground strips.

Per-type table (`py/bcards.py`; "draws" is read by eye from the contact sheets, so it is a description, not a name from the game; census columns count stage-run N; `-` = none):

| type | draws (D) | handler | script uses (stage: n) | spawned by code at | census (stage: n) | free: dies at frame | on player: hp change | punch test (b1 x5 per 20 frames, 100 frames) |
|---|---|---|---|---|---|---|---|---|
| 0 | wide riveted belt strip (scroll-synchronised, removes itself at scroll $9f8) | `$280b4` | 3: 1 | - | - | never (100) | 0 | survives |
| 1 | tiny falling chip | `$2810c` | - | $012c3c | 1: 15 | 11 | 0 | dies at 16 |
| 2 | small shard | `$28764` | - | $01303a | - | 65 | 0 | dies at 65 |
| 3 | tiny speck | `$28be6` | - | $0130a2 | - | never (100) | 0 | survives |
| 4 | falling hazard with POW/BAM burst | `$28d60` | - | $01e9e6 | - | 42 | -10 | dies at 42 |
| 5 | falling hazard with POW/BAM burst (same handler as 4) | `$28d60` | - | $014c70 $018770 $018bf8 $019074 | 2: 1, 3: 2, 5: 1 | 42 | -10 | dies at 42 |
| 6 | black pole | `$28df4` | 2: 1, 3: 1 | - | 2: 1 | never (100) | 0 | survives |
| 7 | thick black post | `$28df4` | 2: 3 | - | 2: 1 | never (100) | 0 | survives |
| 8 | wooden board stack | `$290e4` | 1: 2, 2: 1, 3: 1, 4: 3, 5: 1 | - | 1: 2, 2: 1, 3: 1 | never (100) | 0 | survives |
| 9 | grey pipe piece | `$290e4` | 1: 1 | - | 1: 1 | never (100) | 0 | survives |
| 10 | trash can | `$290e4` | 1: 2 | - | 1: 2 | never (100) | 0 | survives |
| 11 | black post on base | `$28df4` | - | - | - | never (100) | 0 | survives |
| 12 | small bust/head | `$28df4` | - | - | - | never (100) | 0 | survives |
| 13 | blue round sign '30' | `$290e4` | 2: 3, 4: 1 | - | 2: 2, 3: 1, 4: 1, 5: 1, 6: 1 | never (100) | 0 | survives |
| 14 | red round sign '60' | `$290e4` | 2: 3 | - | 2: 3, 3: 1, 4: 1, 5: 1, 6: 1 | never (100) | 0 | survives |
| 15 | street pole | `$290e4` | 2: 3, 4: 1, 5: 2 | - | 2: 3, 3: 1, 4: 1, 5: 2, 6: 1 | never (100) | 0 | survives |
| 16 | blue sign on pole | `$28df4` | 2: 1, 4: 4 | - | 2: 2, 3: 1, 4: 2, 5: 1, 6: 1 | never (100) | 0 | survives |
| 17 | thin pole | `$28df4` | 2: 5, 4: 1 | - | 2: 4, 3: 2, 4: 2, 5: 2, 6: 2 | never (100) | 0 | survives |
| 18 | small red-outlined box | `$29276` | - | - | - | never (100) | 0 | survives |
| 19 | black silhouette blob | `$29276` | - | - | - | never (100) | 0 | survives |
| 20 | faint grey grille | `$29276` | - | - | - | never (100) | 0 | survives |
| 21 | brown chunk | `$292cc` | - | - | - | 20 | 0 | dies at 20 |
| 22 | teal chunk | `$292cc` | - | - | 2: 38 | 20 | 0 | dies at 20 |
| 23 | car | `$2946e` | 1: 1, 2: 4 | - | 1: 1, 2: 5, 3: 2, 4: 2, 5: 2, 6: 2 | never (100) | 0 | survives |
| 24 | red brick wall section (lock wall) | `$29694` | 1: 2 | - | 1: 1 | never (100) | 0 | survives |
| 25 | billboard CLEAN UP NEW YORK / CLEAN WORLD | `$2946e` | 1: 3, 2: 2, 4: 6 | - | 1: 3, 2: 3, 3: 1, 4: 3, 5: 1, 6: 1 | never (100) | 0 | survives |
| 26 | grey machine box | `$298ea` | 3: 11 | - | 3: 6 | never (100) | 0 | dies at 32 |
| 27 | red oil drum | `$29bbc` | 1: 2, 2: 5, 3: 6, 4: 7, 5: 5 | - | 1: 2, 2: 6, 3: 4, 4: 2, 5: 2, 6: 1 | never (100) | 0 | dies at 12 |
| 28 | rock pile (lock) | `$29694` | 1: 1, 2: 3, 4: 1, 5: 3 | - | 1: 1, 2: 4, 3: 1, 4: 2, 5: 3, 6: 1 | never (100) | 0 | survives |
| 29 | tall stone slab wall (lock) | `$29694` | 1: 1 | - | 1: 1 | never (100) | 0 | survives |
| 30 | brick wall (lock) | `$29694` | - | - | - | never (100) | 0 | survives |
| 31 | hanging chain with blue links | `$29df4` | 3: 1 | - | - | never (100) | 0 | survives |
| 32 | flame | `$29f78` | - | - | - | never (100) | 0 | dies at 32 |
| 33 | white puff | `$2a1be` | - | $029af4 $02a146 | 2: 1, 3: 4, 4: 1 | 30 | 0 | dies at 30 |
| 34 | (?) nothing visible | `$2a212` | 2: 17 | - | 2: 17, 3: 5, 4: 5, 5: 5, 6: 5 | never (100) | 0 | survives |
| 35 | (?) spawner of type 50 | `$2a2e4` | 2: 2 | - | 2: 2 | never (100) | 0 | survives |
| 36 | small prop with pick-up hint | `$28df4` | 3: 4, 5: 5 | - | 3: 2 | never (100) | 0 | survives |
| 37 | small grey prop with pick-up hint | `$290e4` | 1: 4, 2: 3, 4: 2, 5: 3 | - | 1: 2, 2: 4, 3: 1, 4: 1, 5: 2, 6: 1 | never (100) | 0 | survives |
| 38 | electric arc column | `$2a44e` | - | $0291ac | - | never (100) | 0 | survives |
| 39 | small debris | `$2a4b2` | - | $00c544 | - | 60 | 0 | dies at 60 |
| 40 | POWER COLA poster | `$2a5e2` | - | $001794 | - | never (100) | 0 | survives |
| 41 | (?) lives 1 frame, plays sound $49 | `$2a6a0` | - | $02a686 $02a690 | - | 1 | 0 | dies at 1 |
| 42 | tiny sparkles (sound $4d) | `$2a79e` | - | $00d9e4 | - | never (100) | 0 | survives |
| 43 | comic hit text / burst, 21 variants | `$2a880` | - | $00da6e $00daca $00f786 $00f910 | 1: 130, 2: 993, 3: 114, 4: 251, 5: 64, 6: 80 | 16 | 0 | dies at 16 |
| 44 | small red prop with pick-up hint | `$28df4` | 1: 3, 5: 2 | - | 1: 3, 5: 1 | never (100) | 0 | survives |
| 45 | row of white puffs | `$2a8d4` | - | $029826 | 1: 3, 2: 3, 3: 1, 4: 1, 5: 2, 6: 1 | 64 | 0 | dies at 64 |
| 46 | red double door | `$2a94c` | 1: 1 | - | 1: 1 | never (100) | 0 | survives |
| 47 | small chips, 4 variants | `$2aa1c` | - | $02a9d6 $02a9e0 $02a9ea $02a9f4 | 1: 4 | 29 | 0 | dies at 25 |
| 48 | barred window | `$2aac4` | 1: 2 | - | 1: 2 | never (100) | 0 | survives |
| 49 | shards, 5 variants | `$2ab72` | - | $029648 $029652 | - | 32 | 0 | dies at 28 |
| 50 | tiny pieces | `$2abf0` | - | $02a3c2 | 2: 326 | 1 | 0 | dies at 1 |
| 51 | (?) spawner of type 53 | `$2acbe` | 2: 1 | - | 2: 2, 3: 1, 4: 1, 5: 1, 6: 1 | never (100) | 0 | survives |
| 52 | (?) spawner of type 53 | `$2acbe` | - | - | - | never (100) | 0 | survives |
| 53 | small blue-green fragments | `$2ad50` | - | $02acf6 | 2: 572 | 17 | 0 | dies at 17 |
| 54 | pale grey block | `$292cc` | - | - | 2: 44 | 20 | 0 | dies at 20 |
| 55 | (?) small | `$2ae42` | - | $00b862 $024362 | 1: 4, 2: 16, 3: 16, 4: 16, 5: 35, 6: 16 | 24 | 0 | dies at 24 |
| 56 | brick wall that collapses into 43 and 57 | `$2aea6` | 1: 1 | - | 1: 1 | never (100) | 0 | survives |
| 57 | brick chunks, 4 variants | `$2af7c` | - | $02af50 $02af5a $02af64 $02af6e | 1: 4 | 18 | 0 | dies at 22 |
| 58 | red burst hazard | `$2aff6` | - | $018580 $0186d4 $0188d8 $01bde8 | - | never (100) | -1 | dies at 12 |
| 59 | olive foreground sheet | `$2946e` | 4: 1 | - | 4: 1 | never (100) | 0 | survives |
| 60 | hanging blob | `$2ab72` | - | - | - | 32 | 0 | dies at 28 |
| 61 | brown foreground belt | `$2946e` | 4: 2 | - | 4: 1 | never (100) | 0 | survives |
| 62 | hook | `$2ab72` | - | - | - | 32 | 0 | dies at 28 |
| 63 | white pole | `$290e4` | 4: 1 | - | - | never (100) | 0 | survives |
| 64 | coloured cable pole | `$290e4` | 4: 3 | - | 4: 1 | never (100) | 0 | survives |
| 65 | grey metal door | `$2b120` | 4: 1 | - | - | never (100) | 0 | survives |
| 66 | thin pole | `$28df4` | 5: 1 | - | - | never (100) | 0 | survives |
| 67 | thin pole (green) | `$28df4` | 5: 1 | - | - | never (100) | 0 | survives |
| 68 | thin horizontal bar | `$28df4` | 5: 2 | - | - | never (100) | 0 | survives |
| 69 | striped panel | `$2b1ca` | 5: 1 | - | - | never (100) | 0 | survives |
| 70 | pale cone | `$2b1ca` | 6: 1 | - | - | never (100) | 0 | survives |
| 71 | orange/black barrier | `$2b1ca` | 6: 1 | - | - | never (100) | 0 | survives |
| 72 | striped screen (spawns 14 chips of type 73) | `$2b308` | 6: 3 | - | - | never (100) | 0 | survives |
| 73 | small chips, 14 variants | `$2b44e` | - | $02b3b0 $02b3ba $02b3c4 $02b3ce | - | 42 | 0 | dies at 42 |
| 74 | black rectangle | `$2b4f0` | 6: 1 | - | - | never (100) | 0 | survives |
| 75 | blue console | `$2b4f0` | - | - | - | never (100) | 0 | survives |
| 76 | red sparks | `$2b4f0` | - | - | - | never (100) | 0 | survives |
| 77 | debris | `$2b4f0` | - | - | - | never (100) | 0 | survives |
| 78 | (?) small dark pieces | `$2b4f0` | - | - | - | never (100) | 0 | survives |
| 79 | orange fireball sphere | `$2b654` | 5: 2 | - | - | never (100) | 0 | survives |
| 80 | (?) nothing seen | `$2b6fa` | - | $01656e | - | never (100) | 0 | survives |
| 81 | white puffs | `$2b7c2` | - | $017046 $017120 $01c1b2 $01c30a | 2: 11, 3: 1, 4: 1, 5: 1, 6: 1 | 8 | 0 | dies at 8 |
| 82 | (?) small pink bit | `$2b830` | - | $016de0 $021a40 | - | 60 | 0 | dies at 75 |
| 83 | (?) small | `$2b958` | - | $01fe9a | - | 30 | 0 | dies at 39 |


Types never reached in the six census runs but present in the scripts: 6 and 7 only partly (stage 3), 31, 44, 66-68, 69-72, 74, 79 (stages 4-6, which the bot did not reach); their bodies were not read beyond the handler-class summary in `out/handlers_B.txt`. Types with no script entry and no code spawn site found (11, 12, 18-21, 30, 32, 41, 42, 52, 55, 80-83 among them) are either spawned through computed D6 or dead: **not resolved**.

## 5. Pickups, drops and the pool A items

- **Health item = pool A type 61** (`$1e706`): in `$1e794` it heals when the owner player touches it: `if energy < $30 then energy += 8` for P1 (`$80113`, `$1e7de`) or P2 (`$80193`, `$1e7fc`), else it waits, blinks after `$c0` frames (`bset #4,(A6)`) and disappears at `$f0` (read). **Harness check** (`lua/forcespawn.lua` pool A, parent link = P1, hp preset 24): variant 2 (falls straight down onto the player) healed `$18 -> $20` (+8) and died at frame 124; variants 1 and 4 (tossed sideways) expired without healing at frames 362 and 101; 3 runs, `out/f/force_A2.txt`, `force_A3.txt`.
- **Sibling items 59, 60, 62** (`$1e2c8`, `$1e4a0`, `$1e922`): 59 = red explosion burst (-1 energy on contact, dies at frame 65), 60 = a `BUTTON!!` object that drains 1 energy per 16 frames, 62 = a timed object that cost **10 energy at frame 250** and died (same harness, `force_A3.txt`, `A4_0.png`). They are what the **carrier** produces: the death routine at `$1a764` (inside pool A type 31's handler `$1a2c6`, which is in stage 4 (level index 3) script once) spawns five records through `$21eb6` with D6 drawn from `$1a818` + 4 x (variant) = rows `3b 3c 3e 3b`, `3b 3c 3c 3e`, `3b 3c 3d 3e`, `3b 3c 3e 3e`, `3b 3e 3c 3b`, one row per spawned record (`$1a7e8`: row = the call's index 0-4, column = `$ea44 & 3`; types 59-62): only the third record can be the health item 61, with probability 1 in 4. So the "bonus carrier" mostly drops hazards: *inferred* from the harness effects, the item graphics were not identified.
- Enemy drops in general were not traced (pool A is ENEMIES' area); the tables of `$21eb6` callers (`py/callers.py 21eb6`) list 78 spawn sites.
- Score values: the add routine `$3fae` adds `table[D7-1]` (BCD at `$4016`: 10, 50, 100, 100, 200, 200, 300, 300, 400, 400, 500, 600, 800, 1000, 1000, 1000, 2000, 2000, 3000, 3000, 4000, 5000, 10000, 1000000) to the long at `60(A6)` of the player record (`$8013c`, `$801bc`) and updates the hi-score `$80010`, only while `$80040` bit 7 is set (read; the score cell offsets are the `$1b4a` table entries 2 and 3). Only 5 call sites with immediate ids were found (`py/d7callers.py 3fae`), the other adders use computed ids.

## 6. Pool C: the enemy attack hit boxes

`$21e72` (the pool C spawn helper) is called by pool A code with D6 = type; it sets `+28` = owner, `+60` of the owner = this record. Handlers: `$22040` (40 types) as above; `$22066` (type 11: no copy of the owner's frame), `$22080` (29: copies `+3`, `+4`, `+20`), `$220ac` (4: multi-frame state machine with an own hit box and the owner's `+51` grab flags), `$2227c` (22: persistent: sets `+51` bit 1 of the owner, i.e. a **grab/hold**, and hits repeatedly).

The hit test `$fa10` (read) skips a player that is inactive, in states `$a`-`$f`, `$12`-`$14`, `$16`, `$17` (the down/knock states), facing value 11, flag `+88` bit 2 or `+58` bit 4, then compares the player's box (`+64..+70`) with the hit box (`$69000[type][state][facing][frame]`, offsets added to the record position, `$fbdc`). On a hit `$fc34` (read): spawns B43 variant 0 at the contact, flips the victim's facing, **subtracts `4 * table[(DSW & $c) >> 2][type]` from the victim's energy `+19`** (tables at `$fcba` -> `$fd2a`, `$fcca`, `$fd5a`, `$fd8a`; energy clamped at 0 sets `+58` bit 1 = dead), sets the victim's reaction state `+23` from `$fdba[type]` (128 = flinch, 130/144/145/146/160/162 = heavier reactions), plays sound `$6b` once per frame (`$81e43` bit 2), and sets `+35` bit 6 of the owner.

**Measured** (harness: record of type t on top of P1, owner = P1, 60 frames): 16 types overlapped P1's box and hurt it; **16 of 16 damages equal 4 x table[0][type]** (types 7, 8, 12, 17, 20, 22, 23, 24, 28, 31, 33, 34, 35, 36, 40, 41; `py/damage_tables.py`; C22 hit twice). The other 28 types did not overlap in this geometry (their boxes are offset from the owner), so their damage is the table value, *not measured*. Damage per hit (energy of 56, one heart = 8) of the four DIP difficulty rows (the index is `$80054 & $c` where `$80054` is the inverted DSW word; which row is Easy/Hard is *inferred* from the values: row 1 is the lowest):

| type | row 0 (default DSW in MAME) | row 1 | row 2 | row 3 | reaction `$fdba` |
|---|---|---|---|---|---|
| 0 | 12 | 8 | 16 | 20 | 128 |
| 1 | 12 | 8 | 16 | 20 | 128 |
| 2 | 12 | 8 | 16 | 20 | 128 |
| 3 | 12 | 8 | 16 | 20 | 128 |
| 4 | 20 | 16 | 24 | 28 | 145 |
| 5 | 12 | 8 | 16 | 20 | 128 |
| 6 | 12 | 8 | 16 | 20 | 128 |
| 7 | 24 | 20 | 32 | 36 | 130 |
| 8 | 24 | 20 | 32 | 36 | 146 |
| 9 | 24 | 20 | 32 | 36 | 146 |
| 10 | 16 | 12 | 20 | 24 | 128 |
| 11 | 12 | 8 | 16 | 20 | 130 |
| 12 | 16 | 12 | 20 | 24 | 128 |
| 13 | 20 | 16 | 28 | 32 | 128 |
| 14 | 20 | 20 | 28 | 32 | 128 |
| 15 | 12 | 8 | 16 | 20 | 128 |
| 16 | 12 | 8 | 16 | 20 | 128 |
| 17 | 16 | 12 | 24 | 28 | 128 |
| 18 | 12 | 8 | 16 | 20 | 128 |
| 19 | 12 | 8 | 16 | 20 | 128 |
| 20 | 16 | 12 | 20 | 24 | 128 |
| 21 | 20 | 16 | 24 | 28 | 128 |
| 22 | 16 | 8 | 20 | 24 | 128 |
| 23 | 20 | 16 | 24 | 28 | 130 |
| 24 | 28 | 24 | 32 | 36 | 162 |
| 25 | 12 | 8 | 20 | 24 | 128 |
| 26 | 16 | 12 | 24 | 28 | 128 |
| 27 | 24 | 20 | 32 | 36 | 144 |
| 28 | 12 | 8 | 16 | 20 | 128 |
| 29 | 20 | 16 | 24 | 28 | 144 |
| 30 | 20 | 16 | 28 | 32 | 128 |
| 31 | 20 | 16 | 28 | 32 | 160 |
| 32 | 48 | 40 | 60 | 64 | 144 |
| 33 | 32 | 24 | 40 | 44 | 128 |
| 34 | 12 | 8 | 20 | 24 | 128 |
| 35 | 20 | 16 | 24 | 28 | 160 |
| 36 | 20 | 16 | 24 | 28 | 160 |
| 37 | 16 | 12 | 24 | 28 | 128 |
| 38 | 16 | 12 | 24 | 28 | 128 |
| 39 | 20 | 16 | 28 | 32 | 144 |
| 40 | 16 | 12 | 24 | 28 | 128 |
| 41 | 20 | 16 | 28 | 32 | 144 |
| 42 | 16 | 12 | 24 | 28 | 128 |
| 43 | 16 | 12 | 24 | 28 | 128 |

Spawn sites and handler for every type: table below (`py/ccards.py`).

| type | handler | spawned by pool-A code at | harness: damage to P1 (hp of 56) | record life (frames) |
|---|---|---|---|---|
| 0 | `$22040` | $010cba $01d8fa | 0 | 1 |
| 1 | `$22040` | $010d20 $01d944 | 0 | 1 |
| 2 | `$22040` | $01178c | 0 | 1 |
| 3 | `$22040` | $012be2 | 0 | 1 |
| 4 | `$220ac` | $01355a $0135e0 | 0 | 57 |
| 5 | `$22040` | $01345a | 0 | 1 |
| 6 | `$22040` | $0140a0 | 0 | 1 |
| 7 | `$22040` | $015a32 | 24 | 1 |
| 8 | `$22040` | - | 24 | 1 |
| 9 | `$22040` | - | 0 | 1 |
| 10 | `$22040` | - | 0 | 1 |
| 11 | `$22066` | $017ca2 $017d24 | 0 | 1 |
| 12 | `$22040` | $0112e0 | 16 | 1 |
| 13 | `$22040` | $01124c | 0 | 1 |
| 14 | `$22040` | $014eb2 | 0 | 1 |
| 15 | `$22040` | - | 0 | 1 |
| 16 | `$22040` | - | 0 | 1 |
| 17 | `$22040` | $0147d0 | 16 | 1 |
| 18 | `$22040` | - | 0 | 1 |
| 19 | `$22040` | $011ece | 0 | 1 |
| 20 | `$22040` | $011f98 | 16 | 1 |
| 21 | `$22040` | $012034 | 0 | 1 |
| 22 | `$2227c` | $01208e | 32 | >=60 |
| 23 | `$22040` | $015f04 $015f7c $0161d6 | 20 | 1 |
| 24 | `$22040` | $01b37e $01b3fc | 28 | 1 |
| 25 | `$22040` | - | 0 | 1 |
| 26 | `$22040` | - | 0 | 1 |
| 27 | `$22040` | $01cc44 $01cce0 | 0 | 1 |
| 28 | `$22040` | - | 12 | 1 |
| 29 | `$22080` | $01d46a | 0 | 1 |
| 30 | `$22040` | - | 0 | 1 |
| 31 | `$22040` | - | 20 | 1 |
| 32 | `$22040` | $020826 | 0 | 1 |
| 33 | `$22040` | $0209aa | 32 | 1 |
| 34 | `$22040` | $016cce $021932 | 12 | 1 |
| 35 | `$22040` | $014a70 | 20 | 1 |
| 36 | `$22040` | $01c732 | 20 | 1 |
| 37 | `$22040` | - | 0 | 1 |
| 38 | `$22040` | - | 0 | 1 |
| 39 | `$22040` | $016524 | 0 | 1 |
| 40 | `$22040` | - | 16 | 1 |
| 41 | `$22040` | - | 20 | 1 |
| 42 | `$22040` | - | 0 | 1 |
| 43 | `$22040` | - | 0 | 1 |


## 7. Flags (`$80040`, `$80041`, `$80014`, `$80015`, `$8005a`, `$80400`)

Writers from the linear listing (`py/flagops.py`), meaning from the handlers and a check per row. "Observed" cites a transition in a logged run (frame numbers are of the cold-boot or census logs named in the row).

| cell bit | name | set by | cleared by | check |
|---|---|---|---|---|
| `$80040` 7 | GAME_RUNNING | `$eda` (start) | `$758` (`clr.w`) | observed: `00>80` at frame 701 (census_l0), `a0>00` at 20809 (census_l1); read: gates `$e1c` sound, `$ea44` random source, input source `$f60`, score adds `$3fae`, `$3d66` HUD |
| `$80040` 6 | GAME_COMPLETED | `$746` | `$758` | read only (the ending was not reached); `$7668` swaps the player update for the victory walk `$7e1c` when the low two bits of the player flags are both set |
| `$80040` 5 | GAME_OVER | `$70c` | `$758` | observed: `80>a0` at 20446 (census_l1), cleared with the whole word at 20809; blocks joining (`$efc`) |
| `$80040` 4 | LEVEL_CLEARED | `$c86a`, `$ca6e` (player victory state machine), `$20bd4` | `$da14` | poke test: setting it runs the full clear sequence (section 2.3); natural set/clear not observed |
| `$80040` 3 | SCENE_LOCK (inferred) | `$1725a`, `$23e5c`, `$23fac` (pool A handlers) | `$1708` (level setup) | 11 read sites in the player code (`$7d0e`, `$a2de`, ...); not observed in any run; also blocks joining and score on the clear screen |
| `$80040` 2 | BOSS_FIGHT | 17 handlers (`$13208`, `$13882`, `$14438`, `$148da`, `$14bf4`, `$150a4`, `$15666`, `$15c90`, `$162f0`, `$16552`, `$1a24e`, `$1a376`, `$1a8e2`, `$1b122`, `$1c858`, `$1dd38`, `$201c2`) | `$17238`, `$20426`, `$23e2e`, `$23f7e` | observed: `80>84` at frame 4250 and `84>80` at 6738 of census_l0 while `$8005c` fell from `$10` to 0 in 16 steps; it enables the boss energy bar `$3f06` |
| `$80041` 0 | TRANSITION | `$8624`, `$86be` (wipes) | `$1444`, `$86ae`, `$8748` | observed: set during every wipe (77-113 intro, 780-878 stage 1 card, clearpoke r = 31..133); 14 draw routines skip while set |
| `$80041` 1 | HINT_MESSAGE (inferred) | `$199a` (idle-too-long message in `$1948`) | | tested by `$ba32`, `$bb20`; not observed |
| `$80041` 2 | TITLE_SCREEN | `$407c` | `$4328` | observed: `80041 = 4` from 3713 to about 4300 (attract log) |
| `$80041` 3 | CLEAR_SEQUENCE | `$1730` | `$187c` | observed: `80041 = 8` during the card loop (clearpoke), cleared when the loop left |
| `$80041` 4 | CONTINUE_PROMPT | `$79f0`, `$18ada` | `$7982`, `$18c04` | observed: `00>10` at 19816 (census_l1) 630 frames before game over, with `$8005a` bit 6 |
| `$80041` 5 | (pool A handler private) | `$20ab8` | `$20ace` | read; tested at `$7186` |
| `$80041` 7 | BOSS_EVENT_B | the same 7 handlers that set `$80040` bit 2 (`$150ac`, `$1566e`, `$15c98`, `$162f8`, `$1655a`, `$1c860`, `$201ca`) | `$17252`, `$20bdc`, `$23e54`, `$23fa4` | read; tested by the player placement `$774e`, `$7870` (players are positioned from the scroll while set) |
| `$80014` 4 | DEMO_ARMED | `$12c2` | `$762` | observed: `$80014 = $10` from 4317, `$18` from 4416 (bit 3), `$10` again at 5050, 0 at the next demo start (9833) |
| `$80014` 3 | DEMO_REPLAYING | `$7a0` | `$834` | observed: bit 3 set exactly in the 634-frame segments of `py/demo_check.py`; `$f6a` selects the replay reader `$10b2` when `$80040` bit 7 is clear |
| `$80014` 1, 0 | RECORD_P2, RECORD_P1 | `$10a8`, `$1046` | `$144c` | read: the developers' recording path (`$fec`); never set (0 of 16,800 frames); bit 7 (`$80014`) is the record switch, never set by code |
| `$80015` 0-2 | MESSAGE_SHOWN_1..3 | `$9f8`, `$a04`, `$a10` | `$770`, `$778`, `$780` | read: per `$80033` value (1-3) the `INSERT COIN`-style message of `$980`; stays 0 in the attract log |
| `$80015` 3 | `$1a154` private (stage 5 boss helper, `$1980` test) | `$1a154` | | read |
| `$80015` 4 | `$173fc` private | `$173fc`, cleared `$17908` | | tested `$a4f6`; read |
| `$8005a` 6 | CONTINUE_RUNNING | `$7b44` | `$7a5a`, `$7b1e`, `$7c56`, `$7c7a`, `$7cec` | observed with `$80041` bit 4 at 19816 (census_l1), cleared at 20446 |
| `$8005a` 7 | CONTINUE_ACCEPTED | `$7a62` | `$7c82`, `$7cf4` | read |
| `$8005a` 5 | CONTINUE_BUTTON_HELD | `$7bfe` | `$7bd2`, `$765c` | read |
| `$80400` 5 | LOCK_HOLDER_ALIVE | 25 handlers (`bset #5,$80400`) | 12 (`bclr`) | observed (stage 1: `$a2` while the wall stands, `$00` after it is gone); with a hold-zone page (map bit 5) the scroller is skipped and bit 7 mirrors it |
| `$80400` 7 / 6 | SCROLL_FROZEN / FORCED_SCROLL | `$88f0`, `$a1fc`.. / `$8b14`, `$a206` | `$88fa`, `$8a92` | read (bit 6 = forced-scroll page, stage 6) |
| `$8005c` | BOSS_ENERGY | boss handlers (`move.b ...,$8005c`) and `$3f2e` (clamp) | | observed: `$10` to 0 in 16 steps in census_l0; drawn by `$3f06` as a bar of 8-unit hearts |

`$80032` is the credit count (BCD), `$80033` the message selector, `$80042/$80044` the continue/demo timer and its frame divider (`$1308`: 63 frames per step), `$81e03` bit 7 the pool A spawn block, `$81e05` the shared fighter coordination bits (`$c780` family).

## 8. The demo input streams

Format (read from `$10b2`, then proven): each demo has two buffers, P1 at `$5c000 + $400*n`, P2 at `$5d000 + $400*n`, pointer tables `$5e000`/`$5f000` (3 entries each: `$5c000, $5c400, $5c800` and `$5d000, $5d400, $5d800`); the content is pairs **(held input byte, repeat count)**; byte bits = the `$80051` layout: 0 up, 1 down, 2 left, 3 right, 4 button 1, 5 button 2, 6 button 3, 7 start. Replay model: per frame `D0 = byte(ptr); cnt -= 1; if cnt == 0 { ptr += 2; D0 = byte(ptr); cnt = count(ptr) }; $80051 = D0` with the first count loaded by `$8ce` (so the first pair is used for count-1 frames, every later pair for exactly `count` frames, and the replay starts one frame after `$80014` bit 3 appears). Demo records at `$87a`, `$896`, `$8b2` (word 1 = level index) give the level: **demo 0 = level index 1 (stage 2), demo 1 = index 2 (stage 3), demo 2 = index 3 (stage 4)**, 633 replayed frames each (the first pair of 634). Stream sizes: 54, 30, 42 pairs (P1) and 62, 56, 65 (P2), counts sum to 634, 686, 634 frames (the demo timer ends the demo after 633/634 frames, so demo 1's stream is not played to its end).

Proof (`py/demo_check.py`, attract run of 16,800 frames): **3798 of 3798 frames equal** (3 demos x 2 players x 633 frames, observed `$80051`/`$80053` vs expanded stream), (the final stream positions are +106, +58, +82 bytes for P1 and +122, +110, +128 for P2). Demo playback also fixes the enemies' "random" source: `$ea44` returns the timer `$80042` when `$80040` bit 7 is clear and an LFSR in `$81e0e` otherwise (read).

Fresh-game replay (`lua/streamplay.lua`, `py/replay_check.py`): start a game at the demo's level, give P2 the active flag as `$83e` does, feed the *decoded* streams through the real P1/P2 ports from the frame at which `$8004a` equals the demo's value at its first replay frame (`$6d`: frames 816, 815, 816), compare `(P1x, P1y, P2x, P2y)` every frame with the attract demo. Result: the trajectories are identical for **386, 436 and 536 frames** (demos 0, 1, 2) and then differ by one or two pixels (first differences: demo 0 frame 386 P2x 582 vs 581, demo 1 frame 436 P1x 464 vs 462, demo 2 frame 536 P2x 663 vs 664), with the same level, same start positions and same scroll. Cause *inferred*: the real game's enemy random numbers differ from the demo's (`$ea44`), changing an enemy's attack timing; not isolated.

## 9. Proposed edits to `architecture.md` (not applied)

1. Pool table row C: replace "effects" by "enemy attack hit boxes (one-frame, re-created by the owner every frame; damage `4 * table[DSW]` at `$fcba`; `$220ac`/`$2227c` are multi-frame)". Row B: "props, hazards, decoration, particles; liftable props pick up with a 192-frame `PICKUP!!` hint in stages 1-3; no pick-up items. The health item is pool A type 61".
2. Flags table: use the names of section 7 for `$80040` 7/6/5/4/2, `$80041` 0/2/3/4, `$80014` 4/3/1/0, `$80015` 0-2, plus the new cells `$8005a` 6/7, `$80400` 5, `$8005c`.
3. "The levels" paragraph: `$8624`/`$86be` are grid wipes (eight effects, table `$8758`, effect id in `$804ae`); `$172a` is the clear sequence (three 128-frame text pages, stage card with the POWER COLA poster, loop until `$80040` bit 4 clears); there is no score tally. Add the per-level tables of section 2.1/2.2 (palette words, music ids 1, 7, 9, 8, 7, 6, scroll maps).
4. "Attract loop": replace the *inferred* screen list by the table of section 1 (state words and routines proven by logging `$80016` and screenshots).
5. Level scripts: "0 of 449 entries use the vertical trigger bit"; the scroll counters change vertically only through the scroll maps (stage 5 one page down, stage 6 a diagonal climb).
6. `$80014`: `$834` clears bit 3 and `$762` clears bit 4; `$80041` bit 7 is set by 7 of the 17 boss handlers, not by "the same sites".

## 10. Open items

- A natural level clear was never reached by the bot (stage 1 boss fight reached, `$80040` bit 2 for 2,488 frames; the boss died at frame 6738 but the run then stalled at the next page with the bot's chase logic); the natural writer sequence of `$80040` bit 4 is therefore *inferred* (section 2.3).
- High-score name entry, continue with a credit, the ending and the six-stage clear were read, not played.
- Pool B: 46 handlers classified (`out/handlers_B.txt`) but only the classes liftable, lock holder, breakable, hazard, comic text and the cinematic props were read or tested; the names in the table are descriptions of pictures. Types 69-72 (`$2b1ca`, `$2b308`), 74-78 (`$2b4f0`), 79, 83 (`$2b958`, 264 instructions, uses `$80100`/`$80180`: a boss-adjacent prop) were not read. Which spawner makes the many stage 2 B22/B50/B53/B54 records (census: 38, 326, 572, 44) was not traced.
- Pool C: damage of 28 of 44 types is the ROM table value only; the box geometry (`$69000`) was not decoded.
- Pool A pickups: heal effect and three hazards measured with a forced record; the drop table from `$1a764` read; no natural pick-up was observed in play.
- `$80040` bit 3, `$80041` bits 1, 5, 7, `$80015` bits 3, 4: read only.
- The painted-font (`$d000`) strings of `$3370` are ids only.
- Stage 6 and stage 5 are only known from scripts and maps; their on-screen layout, the stage 6 diagonal climb and `$773c`'s player placement were not driven.
- Fresh-game replay differs after 386-536 frames; the cause (enemy RNG) is not isolated.

## 11. Errors in the brief

- "`$8624`, `$172a`, `$71c` clear sequence/bonus tally": `$8624` is a screen wipe; no tally exists.
- "pool C = effects, mostly `$22040`": `$22040` is the one-frame attack hit box handler.
- "pool B ... pickups, bonus items, vehicles?": no pickup, bonus item or vehicle among the 84 types; the car (type 23) is a liftable prop.
- "stage cards with the Power Cola picture": the picture belongs to the clear screens and the stages 2-6 cards; stage 1's card is plain.
- "attract `$4a9e`, `$4076`, `$762`, `$6c94` eight-state tables": the tables have seven states (7 = exit) for `$4a9e`, `$4076`, `$5fba` and four for `$6c94`; `$762` has no state table (it uses `$80018` as the demo index 0-2).
- "`$80016` ... which routine is which screen": see section 1; `$80016` is shared.
