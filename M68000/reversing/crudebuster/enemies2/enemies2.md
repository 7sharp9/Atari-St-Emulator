# Crude Buster: pool A objects of levels 3, 4 and 5, bosses, level end and ending

Group ENEMIES2 of the Crude Buster workstream. Subject: MAME `cbuster` (World FX), addresses are 68000 addresses of the decrypted image. Level numbers are the level byte `$80046` (0 to 5); "level 3, 4, 5" are the fourth, fifth and sixth stages
(level 3 is the snowy street with the antiques shop and ends at the 0x3a ape boss; level 4 is the mine/sewer stage with a vertical descent and ends at the 0x12 horned mutant; level 5 is the laboratory with a diagonal staircase and ends at the 0x48 final boss, then the ending).

Method and status labels follow `BRIEF.md`: *proven* = a live MAME run with a count and a script that reproduces it, *read* = from the linear listing only, *inferred* = neither. Names of types are descriptive, taken from the handler body and from what the
object draws and does (contact sheets in `grunts/out/`, `special34/out/`, `l5a/out/`, `l5b/out/`); they are not the developers' words. The detailed per-type references are the four group documents, each with its own scripts and run logs:

| document | content |
|---|---|
| `grunts/grunts.md` | pool A types 0x35, 0x39, 0x3f, 0x40, 0x44 (the common fighters of levels 3 to 5), shared machinery of these types |
| `special34/special34.md` | levels 3 and 4: 0x1f, 0x1a, 0x17, 0x16, 0x19, 0x1d, 0x1e/0x0d, 0x12, 0x0c, 0x11, 0x3a, type 5 variant 1, riders and children |
| `l5a/l5a.md` | level 5 fighters 0x4a, 0x4b, 0x4c, 0x4d and their children 0x41, 0x37, 0x25 |
| `l5b/l5b.md` | the end of level 5: pool B props, 0x4f, 0x4e, 0x13, 0x48, 0x49, 0x47, who ends a level, the ending sequence |

This document is the integration: census of the three level scripts, the camera and screen-lock rules, the spawn graph, the type index, the boss/event flags, how each level ends, corrections to the earlier brief, and the open items.
Scripts of this file are in `py/` and `lua/` (README table in `README.md`); each group directory has its own README.

## 1. What is proven and by whom (summary)

| item | status | evidence |
|---|---|---|
| list A entries of levels 3, 4, 5 and the census by type and variant | proven (static) | `py/scripts_dump.py`, `py/type_by_level.py` |
| level 3: all 32 list A entries spawned in a played-through run (position within 2 px) | proven | `py/census.py out/l3/objlog.txt 3` (32 of 32) |
| level 4: first half (26 of 60 entries to trigger `$4ff`), second half through injected runs of SPECIAL34 | proven in part | `py/census.py out/l4/objlog.txt 4`; `special34/py/README.md` |
| level 5: 38 of 47 entries in my bot run; the other nine (4a/1, 39/0 shifted by the scroll, and the end sequence entries 4c x4, 4d, 4e, 4f) in L5A and L5B runs | proven | `py/census.py out/l5/objlog.txt 5`; `l5a/l5a.md` section on spawn check; `l5b/py/full.sh` |
| camera cell maps and the freeze rule | proven (rule by observation, map static) | `py/lockmap.py`, sections 3 and the level 3 parked-bot runs |
| damage tables: indexed by the pool C hit-box type, not by the owner type | proven | three groups matched 13 of 15 (GRUNTS), 9 of 9 (L5A), 5 of 5 (L5B) and 50 of 50 (SPECIAL34) box types live; static `grunts/py/dmg.py` |
| level end flags and who sets bit 4 of `$80040` | proven | `l5b/py/levelend.sh` (12 of 12), re-run by the lead for two cases (section 6) |
| the ending sequence timing | proven | `l5b/l5b.md` section 3, three runs equal |
| final boss `$48`: health `$27`, +1,000,000 on death, bit 4 1010 frames after the death | proven | `l5b/py/full.sh full` |
| type names | descriptive | sprite plus body |

## 2. Census of the level scripts

List A (`$6c000`, pool A types, 8-byte entries trigger/type/variant/x/y) counts by type and variant, all six levels (`py/type_by_level.py`; levels 0 to 2 are ENEMIES1's):

| type/variant | L0 | L1 | L2 | L3 | L4 | L5 |
|---|---|---|---|---|---|---|
| $00/00 | 5 | 1 | 3 |  |  |  |
| $01/01 | 13 | 5 | 6 | 7 |  |  |
| $02/02 | 7 | 5 | 4 |  |  |  |
| $03/00 |  | 10 | 4 |  |  |  |
| $04/00 | 4 |  |  |  | 7 |  |
| $04/01 | 6 |  |  |  |  |  |
| $05/00 |  | 3 | 16 |  | 2 |  |
| $05/01 |  |  |  | 1 | 6 |  |
| $06/00 |  |  | 8 |  | 6 |  |
| $06/01 |  | 2 | 4 | 1 |  |  |
| $07/00 | 4 |  |  |  |  |  |
| $08/00 |  |  | 7 |  | 2 |  |
| $09/00 | 1 |  |  |  |  |  |
| $0a/00 |  | 1 |  |  |  |  |
| $0b/00 |  |  | 1 |  |  |  |
| $0e/00 | 1 |  |  |  |  |  |
| $0f/00 |  | 1 |  |  |  |  |
| $12/00 |  |  |  |  | 1 |  |
| $14/00 |  | 2 | 2 |  |  |  |
| $14/01 | 1 | 2 | 1 |  | 2 |  |
| $15/01 |  |  | 1 |  |  |  |
| $16/00 |  |  |  |  | 3 |  |
| $17/02 |  |  | 1 |  |  |  |
| $17/12 |  |  |  | 1 |  |  |
| $17/22 |  |  |  | 1 |  |  |
| $19/00 |  |  |  | 1 |  |  |
| $1a/00 |  |  |  |  | 4 |  |
| $1a/01 |  |  |  |  | 1 |  |
| $1a/02 |  |  |  |  | 1 |  |
| $1c/00 |  | 1 |  |  |  |  |
| $1c/01 |  |  | 1 |  |  |  |
| $1d/01 |  |  |  | 2 |  |  |
| $1e/00 |  |  |  |  | 1 |  |
| $1f/00 |  |  |  | 1 |  |  |
| $35/00 |  |  |  | 7 | 3 | 2 |
| $39/00 |  |  |  | 6 | 9 | 6 |
| $39/03 |  |  |  |  |  | 9 |
| $3f/00 |  |  |  | 3 | 9 | 6 |
| $40/00 |  |  |  | 1 | 2 | 2 |
| $44/00 |  |  |  |  | 1 | 2 |
| $44/01 |  |  |  |  |  | 2 |
| $4a/00 |  |  |  |  |  | 4 |
| $4a/01 |  |  |  |  |  | 1 |
| $4b/00 |  |  |  |  |  | 6 |
| $4c/00 |  |  |  |  |  | 4 |
| $4d/00 |  |  |  |  |  | 1 |
| $4e/00 |  |  |  |  |  | 1 |
| $4f/00 |  |  |  |  |  | 1 |

Totals per level: 42, 33, 59, 32, 60, 47 entries.
New in levels 3 to 5 relative to levels 0 to 2 (the ENEMIES1 range): types $12, $16, $19, $1a, $1d, $1e, $1f, $35, $39, $3f, $40, $44, $4a to $4f, and the variants $05/01 (levels 3, 4), $17/12 and $17/22, $39/03, $44/01, $4a/01, $1a/01 and $1a/02.
Type $05 variant 1 differs from variant 0 only in its entry (health 6 in both; var 0 goes state `$c` then 9, a forward jump; var 1 goes `$b` (an immune in-place hop of 32 frames), `$15`, `$16`, then the normal AI; proven, `special34/out/t5v0`, `t5v1`).
Types $01, $04, $06, $08, $14 appear in levels 3 and 4 with variants already seen in levels 0 to 2; they are named by address only (`$10778`, `$11322`, `$121a4`, `$12c5e`, `$179ca`) and belong to ENEMIES1.

List B (`$6d000`, pool B props) has 34, 28 and 6 entries in levels 3, 4, 5; tables are in `out/census_tables_B.md`. Pool B types in these levels: $10/$40/$19 (props), $9b/$9c (bit 7 set: spawned from record 24), $08/$0f/$11/$0d, $24/$25/$2c, $3b/$3d/$41/$3f in level 3 and 4; the level 5 entries are the
camera-holding crates $46 and $47 (`$c7` is $47 with bit 7), three glass tubes $48 and a machine $4a (section 7).

Arrival behaviour of list A (proven, `spawn_gate.py` of the kernel pass and `py/census.py`): an entry spawns when the horizontal scroll counter `$8040a` reaches its trigger (all 47 level 5 triggers are horizontal; vertical movement is camera only), one entry per frame,
at the entry's x and y (an entry may be at x = scroll x + `$120`: just outside the right edge); at most five pool A records live; a handler's first run or a scroll step moves a new record by up to 1 pixel (in level 5 also up to 16 pixels in y for entries spawned while the staircase scrolls).
Entries that spawn left of the camera (the 0x4a at x $260, the 4c at x $cd0, the 0x1a cart variant 2 at x $3d0) are removed by `$2242c` within a few frames.

### 2.1 Level 3, entries in order with the observed spawn (played-through run, 32 of 32)

Each row shows the scroll when a record with the entry's type, variant and position (within `$20`) became active in the run `out/l3/objlog.txt` (teleport bot with health clamp; frame numbers are the bot's).

| # | trigger | type | var | x | y | name | first seen at scroll |
|---|---|---|---|---|---|---|---|
| 1 | H$110 | $01 | 1 | $0230 | $0190 | `$10778` fighter (ENEMIES1) | x=$0110 y=$0100 (frame 737) |
| 2 | H$120 | $01 | 1 | $0238 | $0160 | `$10778` fighter (ENEMIES1) | x=$0120 y=$0100 (frame 753) |
| 3 | H$120 | $39 | 0 | $0240 | $0160 | clinger | x=$0121 y=$0100 (frame 754) |
| 4 | H$160 | $35 | 0 | $0280 | $0160 | heavy brute / sentry | x=$0160 y=$0100 (frame 817) |
| 5 | H$1c0 | $35 | 0 | $02f0 | $01c0 | heavy brute / sentry | x=$01c0 y=$0100 (frame 1038) |
| 6 | H$200 | $39 | 0 | $01c8 | $01c0 | clinger | x=$0200 y=$0100 (frame 1102) |
| 7 | H$200 | $01 | 1 | $01e8 | $01c0 | `$10778` fighter (ENEMIES1) | x=$0201 y=$0100 (frame 1103) |
| 8 | H$2d0 | $35 | 0 | $03f8 | $0190 | heavy brute / sentry | x=$02d0 y=$0100 (frame 1830) |
| 9 | H$300 | $3f | 0 | $02e0 | $0160 | flamethrower trooper | x=$0300 y=$0100 (frame 1878) |
| 10 | H$300 | $05 | 1 | $03b0 | $01c0 | `$11938` grunt (ENEMIES1; var 1 hops in) | x=$0300 y=$0100 (frame 1878) |
| 11 | H$400 | $01 | 1 | $03c8 | $0140 | `$10778` fighter (ENEMIES1) | x=$0400 y=$0100 (frame 2247) |
| 12 | H$400 | $01 | 1 | $03e8 | $0130 | `$10778` fighter (ENEMIES1) | x=$0401 y=$0100 (frame 2248) |
| 13 | H$400 | $06 | 1 | $03e0 | $0180 | `$121a4` (ENEMIES1) | x=$0401 y=$0100 (frame 2249) |
| 14 | H$400 | $1d | 1 | $0530 | $01c0 | motorbike | x=$0401 y=$0100 (frame 2250) |
| 15 | H$440 | $1d | 1 | $0570 | $01c0 | motorbike | x=$0440 y=$0100 (frame 2540) |
| 16 | H$480 | $35 | 0 | $05b0 | $01c0 | heavy brute / sentry | x=$0480 y=$0100 (frame 2604) |
| 17 | H$500 | $3f | 0 | $04e0 | $01c0 | flamethrower trooper | x=$0500 y=$0100 (frame 2825) |
| 18 | H$500 | $3f | 0 | $0620 | $01c0 | flamethrower trooper | x=$0501 y=$0100 (frame 2826) |
| 19 | H$5f0 | $17 | 18 | $05b0 | $0160 | hover platform (delivers boss) | x=$05f0 y=$0100 (frame 3065) |
| 20 | H$600 | $01 | 1 | $05c8 | $01c0 | `$10778` fighter (ENEMIES1) | x=$0600 y=$0100 (frame 3380) |
| 21 | H$600 | $01 | 1 | $05d8 | $01c0 | `$10778` fighter (ENEMIES1) | x=$0600 y=$0100 (frame 3466) |
| 22 | H$6c0 | $35 | 0 | $07f0 | $01c0 | heavy brute / sentry | x=$06c0 y=$0100 (frame 3774) |
| 23 | H$700 | $39 | 0 | $06e0 | $01c0 | clinger | x=$0700 y=$0100 (frame 3838) |
| 24 | H$800 | $40 | 0 | $07e0 | $01c0 | kickboxer | x=$0800 y=$0100 (frame 4459) |
| 25 | H$800 | $1f | 0 | $0910 | $01c0 | Santa boss | x=$0801 y=$0100 (frame 4460) |
| 26 | H$840 | $39 | 0 | $0960 | $01c0 | clinger | x=$0840 y=$0100 (frame 4670) |
| 27 | H$850 | $39 | 0 | $0980 | $0160 | clinger | x=$0850 y=$0100 (frame 4686) |
| 28 | H$890 | $35 | 0 | $09c0 | $0150 | heavy brute / sentry | x=$0890 y=$0100 (frame 4750) |
| 29 | H$8a0 | $35 | 0 | $09c0 | $01c0 | heavy brute / sentry | x=$08a0 y=$0100 (frame 4766) |
| 30 | H$900 | $19 | 0 | $08d0 | $01c0 | tank | x=$0900 y=$0100 (frame 4862) |
| 31 | H$a00 | $39 | 0 | $09e0 | $01c0 | clinger | x=$0a00 y=$0100 (frame 5467) |
| 32 | H$a00 | $17 | 34 | $09c0 | $0160 | hover platform (delivers boss) | x=$0a00 y=$0100 (frame 5468) |

Dynamic spawns of level 3 (activations without a script entry, same run): one extra 0x05 var 1 record (frame 1878, health 0 in its first frame: read as a pool B dropper's spawn, not traced), 0x33 (by the 0x1d bikes at scroll $401 and $440), 0x1b (debris, x $4fc), 0x0c + 0x34 var 1 (by 0x17 var $12 at scroll $5f0), 0x45 and 0x46 (by 0x19 at scroll $900),
0x11, 0x40 var 1, 0x40 var 2, 0x34 var 1 (by 0x17 var $22 at scroll $a00), 0x3a (by 0x11 morphing, frame 5725).

### 2.2 Level 4

| # | trigger | type | var | x | y | name | first seen at scroll |
|---|---|---|---|---|---|---|---|
| 1 | H$130 | $39 | 0 | $0110 | $0160 | clinger | x=$0130 y=$0100 (frame 769) |
| 2 | H$130 | $39 | 0 | $0100 | $01c0 | clinger | x=$0131 y=$0100 (frame 770) |
| 3 | H$130 | $39 | 0 | $0120 | $01c0 | clinger | x=$0132 y=$0100 (frame 771) |
| 4 | H$138 | $3f | 0 | $0258 | $0160 | flamethrower trooper | x=$0138 y=$0100 (frame 1152) |
| 5 | H$140 | $3f | 0 | $0260 | $0160 | flamethrower trooper | x=$0140 y=$0100 (frame 1160) |
| 6 | H$150 | $40 | 0 | $0270 | $0190 | kickboxer | x=$0150 y=$0100 (frame 1203) |
| 7 | H$1c0 | $3f | 0 | $02e0 | $0160 | flamethrower trooper | x=$01c0 y=$0100 (frame 1315) |
| 8 | H$1c0 | $3f | 0 | $02e0 | $01c0 | flamethrower trooper | x=$01c1 y=$0100 (frame 1316) |
| 9 | H$200 | $39 | 0 | $01f0 | $0160 | clinger | x=$0200 y=$0100 (frame 1425) |
| 10 | H$200 | $3f | 0 | $01d0 | $01c0 | flamethrower trooper | x=$0200 y=$0100 (frame 1426) |
| 11 | H$200 | $39 | 0 | $01f0 | $01c0 | clinger | x=$0200 y=$0100 (frame 1427) |
| 12 | H$200 | $3f | 0 | $0338 | $0160 | flamethrower trooper | x=$0200 y=$0100 (frame 1428) |
| 13 | H$200 | $39 | 0 | $0310 | $01c0 | clinger | x=$0200 y=$0100 (frame 1463) |
| 14 | H$200 | $3f | 0 | $0338 | $01c0 | flamethrower trooper | x=$0200 y=$0100 (frame 1476) |
| 15 | H$240 | $1a | 0 | $0210 | $01c0 | mine cart | x=$0240 y=$0100 (frame 1628) |
| 16 | H$250 | $35 | 0 | $0380 | $01c0 | heavy brute / sentry | x=$0250 y=$0100 (frame 1825) |
| 17 | H$280 | $1a | 0 | $0250 | $01c0 | mine cart | x=$0280 y=$0100 (frame 1873) |
| 18 | H$300 | $1a | 1 | $02d0 | $01c0 | mine cart | x=$0300 y=$0100 (frame 2113) |
| 19 | H$390 | $1a | 0 | $0360 | $01c0 | mine cart | x=$0390 y=$0100 (frame 2458) |
| 20 | H$3a0 | $39 | 0 | $04c0 | $0190 | clinger | x=$03a0 y=$0100 (frame 2792) |
| 21 | H$3c0 | $39 | 0 | $04d0 | $0190 | clinger | x=$03c0 y=$0100 (frame 2850) |
| 22 | H$3c0 | $39 | 0 | $04f0 | $0190 | clinger | x=$03c1 y=$0100 (frame 2851) |
| 23 | H$3c0 | $1a | 0 | $0390 | $01c0 | mine cart | x=$03c2 y=$0100 (frame 2852) |
| 24 | H$3f0 | $16 | 0 | $0520 | $0140 | hover-bike gunner | x=$03f0 y=$0100 (frame 2937) |
| 25 | H$400 | $16 | 0 | $0520 | $0180 | hover-bike gunner | x=$0400 y=$0100 (frame 3432) |
| 26 | H$420 | $16 | 0 | $0550 | $0180 | hover-bike gunner | x=$0420 y=$0100 (frame 3464) |
| 27 | H$400 | $1a | 2 | $03d0 | $01c0 | mine cart |  |
| 28 | H$500 | $3f | 0 | $04e0 | $01c0 | flamethrower trooper |  |
| 29 | H$500 | $40 | 0 | $0620 | $01c0 | kickboxer |  |
| 30 | H$500 | $44 | 0 | $04e8 | $0250 | whip man |  |
| 31 | H$500 | $1e | 0 | $04c8 | $02c0 | level 4 mid boss |  |
| 32 | H$550 | $05 | 1 | $0638 | $0290 | `$11938` grunt (ENEMIES1; var 1 hops in) |  |
| 33 | H$570 | $05 | 1 | $0638 | $0290 | `$11938` grunt (ENEMIES1; var 1 hops in) |  |
| 34 | H$590 | $05 | 1 | $0638 | $0290 | `$11938` grunt (ENEMIES1; var 1 hops in) |  |
| 35 | H$5a0 | $05 | 1 | $0638 | $0290 | `$11938` grunt (ENEMIES1; var 1 hops in) |  |
| 36 | H$5b0 | $05 | 1 | $0638 | $0290 | `$11938` grunt (ENEMIES1; var 1 hops in) |  |
| 37 | H$5b0 | $35 | 0 | $06e0 | $0250 | heavy brute / sentry |  |
| 38 | H$5b0 | $35 | 0 | $06e0 | $02c0 | heavy brute / sentry |  |
| 39 | H$600 | $3f | 0 | $05f0 | $0250 | flamethrower trooper |  |
| 40 | H$690 | $06 | 0 | $0658 | $02c0 | `$121a4` (ENEMIES1) |  |
| 41 | H$690 | $06 | 0 | $0678 | $02c0 | `$121a4` (ENEMIES1) |  |
| 42 | H$690 | $04 | 0 | $07c0 | $02c0 | `$11322` (ENEMIES1) |  |
| 43 | H$6a0 | $04 | 0 | $07d0 | $02c0 | `$11322` (ENEMIES1) |  |
| 44 | H$6b0 | $04 | 0 | $07e0 | $02c0 | `$11322` (ENEMIES1) |  |
| 45 | H$6b0 | $06 | 0 | $0678 | $02c0 | `$121a4` (ENEMIES1) |  |
| 46 | H$6b0 | $06 | 0 | $0698 | $02c0 | `$121a4` (ENEMIES1) |  |
| 47 | H$6c0 | $06 | 0 | $06a0 | $02c0 | `$121a4` (ENEMIES1) |  |
| 48 | H$6c0 | $04 | 0 | $07f0 | $02c0 | `$11322` (ENEMIES1) |  |
| 49 | H$700 | $04 | 0 | $06c8 | $02c0 | `$11322` (ENEMIES1) |  |
| 50 | H$700 | $04 | 0 | $06d8 | $02c0 | `$11322` (ENEMIES1) |  |
| 51 | H$700 | $04 | 0 | $06f0 | $02c0 | `$11322` (ENEMIES1) |  |
| 52 | H$700 | $14 | 1 | $0830 | $02c0 | `$179ca` (ENEMIES1) |  |
| 53 | H$710 | $06 | 0 | $0840 | $02c0 | `$121a4` (ENEMIES1) |  |
| 54 | H$720 | $14 | 1 | $0850 | $02c0 | `$179ca` (ENEMIES1) |  |
| 55 | H$7a0 | $08 | 0 | $08d0 | $0230 | `$12c5e` (ENEMIES1) |  |
| 56 | H$7a0 | $08 | 0 | $08d0 | $0260 | `$12c5e` (ENEMIES1) |  |
| 57 | H$800 | $05 | 1 | $0828 | $0290 | `$11938` grunt (ENEMIES1; var 1 hops in) |  |
| 58 | H$8c0 | $05 | 0 | $09e0 | $0250 | `$11938` grunt (ENEMIES1; var 1 hops in) |  |
| 59 | H$8c0 | $05 | 0 | $09f0 | $0250 | `$11938` grunt (ENEMIES1; var 1 hops in) |  |
| 60 | H$8f0 | $12 | 0 | $0980 | $01c0 | claw machine / horned boss |  |

The bot reached the descent block (scroll x $500, y $100) and stopped there; the lower half (entries from trigger $500: 0x3f, 0x40, 0x44 at y $250, 0x1e at x $4c8 y $2c0, the five 5/1 hoppers at trig $550 to $5b0, the 0x04/0x06 groups at y $2c0, the two 0x14, two 0x08, three 0x05, and the 0x12 at trig $8f0) was driven through injections by SPECIAL34
(`special34/py/README.md`: 0x12 boss body, 0x1e morph). Dynamic spawns seen: 0x34 riders (by 0x16), 0x39/0x35/0x3f variants 1 and 2 (the cargo of the mine carts 0x1a), 0x0d + 0x41 (0x1e morph), 0x42 + 0x43 (jaws of the 0x12 claw).

### 2.3 Level 5

| # | trigger | type | var | x | y | name | first seen at scroll |
|---|---|---|---|---|---|---|---|
| 1 | H$120 | $3f | 0 | $00f0 | $07c0 | flamethrower trooper | x=$0120 y=$0700 (frame 753) |
| 2 | H$120 | $3f | 0 | $0250 | $07c0 | flamethrower trooper | x=$0121 y=$0700 (frame 754) |
| 3 | H$140 | $44 | 0 | $0260 | $07c0 | whip man | x=$0140 y=$0700 (frame 785) |
| 4 | H$160 | $44 | 0 | $0280 | $0760 | whip man | x=$0160 y=$0700 (frame 817) |
| 5 | H$1c0 | $4b | 0 | $01a0 | $07c0 | skeletal android with flying skull head (head = 0x41) | x=$01c0 y=$0700 (frame 913) |
| 6 | H$1c0 | $4b | 0 | $02e0 | $07c0 | skeletal android with flying skull head (head = 0x41) | x=$01c1 y=$0700 (frame 915) |
| 7 | H$200 | $3f | 0 | $01c8 | $0760 | flamethrower trooper | x=$0200 y=$0700 (frame 2479) |
| 8 | H$200 | $3f | 0 | $01e8 | $07c0 | flamethrower trooper | x=$0201 y=$0700 (frame 2480) |
| 9 | H$200 | $3f | 0 | $0338 | $0760 | flamethrower trooper | x=$0201 y=$0700 (frame 2481) |
| 10 | H$200 | $3f | 0 | $0318 | $07c0 | flamethrower trooper | x=$0201 y=$0700 (frame 2482) |
| 11 | H$280 | $4a | 0 | $0250 | $07c0 | cyborg mutant with metal claw arms | x=$0280 y=$0700 (frame 2829) |
| 12 | H$280 | $4a | 0 | $03b0 | $07c0 | cyborg mutant with metal claw arms | x=$0281 y=$0700 (frame 2830) |
| 13 | H$290 | $4a | 0 | $0260 | $0760 | cyborg mutant with metal claw arms | x=$0290 y=$0700 (frame 2845) |
| 14 | H$290 | $4a | 0 | $03c0 | $0760 | cyborg mutant with metal claw arms | x=$0291 y=$0700 (frame 2846) |
| 15 | H$2b0 | $35 | 0 | $03e0 | $0760 | heavy brute / sentry | x=$02b0 y=$0700 (frame 2877) |
| 16 | H$2c0 | $35 | 0 | $03f0 | $07c0 | heavy brute / sentry | x=$02c0 y=$0700 (frame 2893) |
| 17 | H$300 | $44 | 1 | $02e8 | $0760 | whip man | x=$0300 y=$0700 (frame 2957) |
| 18 | H$300 | $44 | 1 | $02c8 | $07c0 | whip man | x=$0300 y=$0700 (frame 2958) |
| 19 | H$400 | $39 | 0 | $0440 | $06c0 | clinger | x=$0400 y=$0700 (frame 3552) |
| 20 | H$400 | $40 | 0 | $0470 | $06c0 | kickboxer | x=$0401 y=$06ff (frame 3553) |
| 21 | H$400 | $39 | 0 | $04a0 | $06c0 | clinger | x=$0402 y=$06fe (frame 3554) |
| 22 | H$400 | $40 | 0 | $04d0 | $06c0 | kickboxer | x=$0403 y=$06fd (frame 3555) |
| 23 | H$500 | $39 | 0 | $0580 | $05c0 | clinger | x=$0500 y=$0600 (frame 3808) |
| 24 | H$600 | $39 | 0 | $0680 | $04c0 | clinger | x=$068d y=$0473 (frame 4205) |
| 25 | H$700 | $4a | 1 | $0820 | $0480 | cyborg mutant with metal claw arms | x=$0700 y=$0400 (frame 4320) |
| 26 | H$800 | $39 | 0 | $0840 | $03c0 | clinger | x=$0800 y=$0400 (frame 4576) |
| 27 | H$800 | $39 | 0 | $08c0 | $03c0 | clinger | x=$0801 y=$03ff (frame 4577) |
| 28 | H$800 | $39 | 3 | $0920 | $0440 | clinger | x=$0802 y=$03fe (frame 4578) |
| 29 | H$840 | $39 | 3 | $0960 | $0400 | clinger | x=$0840 y=$03c0 (frame 4640) |
| 30 | H$880 | $39 | 3 | $09a0 | $03c0 | clinger | x=$0880 y=$0380 (frame 4704) |
| 31 | H$8c0 | $39 | 3 | $09e0 | $0380 | clinger | x=$0925 y=$02db (frame 4869) |
| 32 | H$900 | $39 | 3 | $0a20 | $0340 | clinger | x=$0952 y=$02ae (frame 4914) |
| 33 | H$940 | $39 | 3 | $0a60 | $0300 | clinger | x=$09c1 y=$023f (frame 5025) |
| 34 | H$980 | $39 | 3 | $0aa0 | $02c0 | clinger | x=$0a39 y=$01c7 (frame 5145) |
| 35 | H$9c0 | $39 | 3 | $0ae0 | $0280 | clinger | x=$0abe y=$0142 (frame 5278) |
| 36 | H$a00 | $39 | 3 | $0b20 | $0240 | clinger | x=$0acc y=$0134 (frame 5292) |
| 37 | H$c00 | $4b | 0 | $0c10 | $00c0 | skeletal android with flying skull head (head = 0x41) | x=$0c00 y=$0100 (frame 5600) |
| 38 | H$c00 | $4b | 0 | $0cb0 | $00c0 | skeletal android with flying skull head (head = 0x41) | x=$0c01 y=$0100 (frame 5601) |
| 39 | H$c00 | $4b | 0 | $0c40 | $00c0 | skeletal android with flying skull head (head = 0x41) | x=$0c02 y=$0100 (frame 7102) |
| 40 | H$c00 | $4b | 0 | $0c70 | $00c0 | skeletal android with flying skull head (head = 0x41) | x=$0c03 y=$0100 (frame 8603) |
| 41 | H$cc0 | $4c | 0 | $0df0 | $01c0 | grey-suited fighter with a snake (snake = 0x37) |  |
| 42 | H$ce0 | $4c | 0 | $0e10 | $01c0 | grey-suited fighter with a snake (snake = 0x37) |  |
| 43 | H$d00 | $4c | 0 | $0cd0 | $01c0 | grey-suited fighter with a snake (snake = 0x37) |  |
| 44 | H$e20 | $4c | 0 | $0df0 | $01c0 | grey-suited fighter with a snake (snake = 0x37) |  |
| 45 | H$e20 | $4d | 0 | $0ed8 | $01a0 | tusked horned brute |  |
| 46 | H$e80 | $4f | 0 | $0f30 | $01a0 | tube mutant (tube 2) |  |
| 47 | H$ee0 | $4e | 0 | $0f90 | $01a0 | brown beast (tube 3) |  |

Notes: the nine entries not matched by the bot run are the end sequence (the crates $46 and $47 hold the camera at scroll $c01 and $d01, section 3.4, and the bot does not attack pool B) and two entries whose position moved more than 2 pixels with the staircase scroll.
0x4f and 0x4e do not spawn at their trigger in a natural run: the spawner is stopped while `$81e03` bit 7 is set (by 0x4d while alive); L5A saw 0x4f appear 3 frames after the 0x4d record cleared and 0x4e 3 frames after the last 0x4f row, and the scientist 0x13 is spawned by 0x4e (not by a script entry).

## 3. Camera and screen-lock rules

### 3.1 Cell maps (static, `py/lockmap.py`, `out/lockmap.txt`)

`$7fe4` (called every frame from the frame loop, skipped while `$8005a` bit 6 or `$80040` bit 6) calls `$886c`: `$8876` reads the level's cell map through the pointer table at `$8908` (maps at `$8920 $8930 $8940 $8954 $8968 $89a8`).
The map is one word per 256 x 256 block: row = (y >> 8) - 1, column = (x >> 8) - 1 of the camera counters `$80406` (y) and `$8040a` (x) (the integer words of 16.16 longs), 16 words per row (levels 0 to 3 have one row of 8, 8, 10, 10 words).
Word meaning (read, `$8876`/`$8a88`/`$8ade`):

- low nibble: directions locked, bit 0 up, bit 1 right, bit 2 down, bit 3 left (a left scroll is never requested). Request bits: the player routine sets `$80400` bit 1 (right, `$a792`), bit 2 (down, `$a7f6`).
- bit 15 (`$8000`): final block, the camera never moves there (also `$80400` bit 7 set, which stops the tile feed `$8bea`).
- bit 13 (`$2000`): boss arena: while `$80400` bit 5 (set by boss handlers at their start: `$80400` bit 5 setters are listed in `out/flag_setters.txt`) is set, `$8a88` is skipped, so the camera freezes at the block's left edge; when the flag is clear the block is ordinary.
- bit 14 (`$4000`): forced scroll: `$8b14` sets `$80400` bit 6 and `$80402 = ~(nibble)`, so every direction whose lock bit is clear scrolls 1 pixel per frame regardless of the players; `$7fe4` plays sound 56 every 128 frames while `$80400` bit 6 is set (the staircase rumble, level 5).

| level | map | blocks (x, from `$100`) |
|---|---|---|
| 0 | `$8920` | `$100` free, **`$200` arena**, `$300`, `$400`, **`$500` arena**, `$600`, `$700`, `$800` final |
| 1 | `$8930` | `$100`, `$200`, **`$300`**, `$400`, **`$500`**, `$600`, **`$700`**, `$800` final |
| 2 | `$8940` | `$100`, `$200`, **`$300`**, `$400`, **`$500`**, `$600`, `$700`, **`$800`**, `$900`, `$a00` final |
| 3 | `$8954` | `$100` to `$500` free, **`$600` arena**, `$700`, **`$800` arena**, `$900`, `$a00` final |
| 4 | `$8968` | row 1: `$100` to `$400` free, `$500` right locked and only down free (cell `$000b`), `$600` to `$900` frozen; row 2 (y `$200`): `$100` to `$400` frozen, **`$500` arena**, `$600` to `$800` free (right), `$900` on frozen (final) |
| 5 | `$89a8` | 7 rows (y `$700` bottom to `$100` top): row 7 `$100` to `$300` free, then a diagonal of forced-scroll cells `$400c`/`$400d` (up and right) rising to row 1 at x `$a00` to `$d00`, final block row 1, x `$e00` |

### 3.2 How the camera moves in a free block (read, proven in the level 3 runs)

The player routine (`$a712`) requests a right scroll when the player's x is at or beyond scroll x + `$90`; the camera then moves 1 pixel per frame (`$8ba2` adds 1.0 to `$8040a`, and to `$80462`, the tile counter).
A hysteresis bit (`$81e12` bit 0) is set whenever the player touches the left clamp (x <= scroll + `$10`, `$a73c`): the request is only honoured again after the player's x has been inside [scroll + `$90`, scroll + `$94`). The request is also dropped when `$81e03` bit 7 is set (`$a788`).
Proven by the parked bot (`CB_PARK_AT=5f0`, level 3, `out/l3c` and `out/l3d`, 1 of 1 each): the boss 0x0c was alive at scroll $5f0 (`$80040` = `$84` by frame 3080), the camera advanced to $600 and stayed there from frame 3081 until the boss flag cleared (frame 3469 in `l3c`, 3581 in `l3d`), and moved again at the next frame (3470, 3582). While frozen `$80400` showed bits 7 and 5 (`$a0`/`$a2`) with the move request in bit 1 pending.
In `l3d` `$81e03` was cleared every frame (`CB_CLR81E03=1`, the flag read by `$a788`) and the camera still did not move: the freeze is the cell rule, not the enemy count.

### 3.3 The five-enemy rule

`$10254` clears `$81e02` (live count, byte) and `$81e03` (flag) each frame, counts live pool A records, and sets `$81e03` = `$80` when the count is 5 or more. While the flag is set the script spawner `$f388` does not spawn (`$f3b4`) and the scroll request `$a788` is refused.
(The earlier architecture text said the dispatcher sets the flag; the clearing by `clr.w $81e02` each frame is the missing half.) Other writers of `$81e03` = `$80`, executed while their object lives: types 0x19 (`$18b82`, `$18cca`), 0x46 (`$1fdc0`), 0x4d (`$210cc`), 0x4e (`$2120a`), 0x4f (`$21448`), pool B 0x45 to 0x47 (`$2b238`, while the prop is left of scroll x + `$f0`); 0x4e clears it at `$213fe`.
In level 5 the crates $46 at x $cf0 and $47 at x $df0 hold the camera at scroll $c01 and $d01 until they are broken (5 hits each; proven, `l5b/l5b.md` section 2.1, scroll stayed `$c01`/`$d01` with `$81e03` = `$80` until the hit).

### 3.4 Level 4 descent (partly open)

At scroll x `$500`, y `$100` the cell allows only down. `$1948` (called each frame, skipped while `$80041` bit 4): in level 4 at exactly these counters it discards every scroll request (`andi.b #$f0,$80400`, `$19dc`) unless `$81e02` == 2 and `$80015` bit 3 (set by the first instruction of the 0x1e handler, `$1a154`) hold; then a counter `$8053c` runs
and prompt texts `$3c + (random >> 2 & 7)` are shown through `$28fa` until it reaches `$400`. The player routine counts the descent separately (`$a79c`: player y >= `$210` sets `$81e12` bit 1, 224 frames in `$81e13` set bit 2, then `bset #2,$80400`).
SPECIAL34 found that in its injected run `$81e02` was 4 (not 2) during the whole descent and the camera still scrolled y `$100` to `$200` at +1 per frame (frames 802 to 1059) once the player stood on the lower floor; the 0x1e body starts only when `$80406` >= `$200`. So the count == 2 rule is not what lets the camera pass; which phase of `$81e12` does it is **open**. **How a player gets down is solved**: the descent is a ladder, tile column x `$5de`-`$5ef` (attributes `$0558/$0568/$0570/$0580`, y `$1e0` to `$260`), and a plain down press (no horizontal direction) at x 1502 to 1506 and y 448 starts the climb (sub-action 7; 1501 gives sub-action 6, a fall; 1497-1500 and 1507-1510 nothing). The natural bot found it at frame 8706 (`LADDER found at x=1502`), reached y 592 and the camera went from `$100` to `$200` while it was on the ladder (`player/natural.md`, `player/lua/ladderlab.lua`).
Observed hang (proven twice, lead's bot): with 5 or more pool A records alive and the player at y >= `$210` the player routine loops forever between `$a7ec` and `$a85e` (the frame counter `$8004a` stops; a pokes-free consequence of the code, not of the bot); a single human player can hit it only with five live enemies while standing in that pit.
Idle prompt: `$1948` also counts frames without horizontal scroll in other levels (`$8053c`, `$8053e`) and after `$400` frames shows a prompt text `$32 + random` (a "hurry" style message; the text strings were not read).

## 4. Spawn graph of the pool A handlers (static, `py/spawn_graph.py`, `out/spawn_graph_A.txt`)

Calls of `$21eb6` (spawn a pool A record) with the type and variant loaded just before (hex), grouped by owner; values noted `4(A6)` are copied from the owner.

| owner | spawns |
|---|---|
| 0x0b | $20 |
| 0x0d | $41 (sidekick) |
| 0x0e | $38, $36, $38 |
| 0x0f | $23; $01/3, $02/3, $00/4 |
| 0x10 | $25, $24 |
| 0x11 | $3a (morph) |
| 0x12 | $42, $43 (jaws) |
| 0x13 | $48 (final boss), $47 (pad) |
| 0x14, 0x15 | $1b (var 0 / var 1) |
| 0x16 | $34 (rider) |
| 0x17 | $10, $0c, $11, $40/1, $40/2, $34/1 (by the variant's high nibble: 0 -> $10, 1 -> $0c, 2 -> $11 + 2 x $40; low nibble selects the handler) |
| 0x19 | $45 |
| 0x1a | $39/1, $39/2, $35/1, $39/2, $3f/1, $39/2 (cargo by variant) |
| 0x1c | $2d to $32 |
| 0x1d | $33 (rider) |
| 0x1e | $0d |
| 0x1f | $3b to $3e (grenades, variants 0 to 4 of the five lists at `$1a818`) |
| 0x20 | $21, $22 |
| 0x24 | $25/1, $26 |
| 0x32 | $00/5, $00/6, $04/1 |
| 0x33, 0x34 | $1b |
| 0x37, 0x38 | $37 (snake) |
| 0x45 | $46, or $18 when the level byte is 4 |
| 0x48 | $49 (five crawlers per state `$19`), $47 |
| 0x4b | $41 (skull head) |
| 0x4e | $13 (scientist) |
| 0x4f | $42, $43 |
| pool B 0x2e, 0x30, 0x41 | pool A $05/1 (droppers in levels 3 and 4) |

## 5. Shared engine facts that changed during this pass (corrections to `BRIEF2.md` and the first reading)

1. **Damage is indexed by the pool C hit-box type.** `$fc34` reads `2(A6)` of the box record (= D6 of the `$21e72` call), takes the byte `[dip & $c][box type]` of the tables behind `$fcba`, multiplies by 4 and subtracts it from the player's `+19` (`$80113` for P1).
   The default dip is `$80054` = `$80`, so column 0 applies (proven: boss box `$22` took exactly 12 in 50 of 50 hits; every group saw box types matching live). Box damages at column 0 seen live: 12 (`$00 $01 $05 $0f $10 $12 $13 $19 $1c $22`), 16 (`$0c $11 $14 $16 $1a $25 $26 $28 $2a $2b`), 20 (`$04 $0d $0e $15 $17 $23 $24 $27 $29 $1e $1f`), 24 (`$1b`), 48 (`$20`, final boss flying dash).
   Pool B projectiles use `$10122[type]` unmultiplied (pool B `$3a` bullet 1, explosions type 4 and 5: 10). The `tables_decode.py` damage column (by owner type) is wrong and is marked so in the script; `grunts/py/dmg.py` and `special34/py/boxdmg.py` print the right table.
2. **Contact damage is a second path.** `$2331c` calls `$f4f4` when the enemy's `+17` bit 2 is clear: an overlap of the enemy's hurtbox with the player's body costs the player 1 (`$f78e[type]`, unmultiplied, at most once per 8 frames), writes `+6 = $90` into the enemy, which takes the ordinary hit reaction: it loses 1 health, staggers, and the player is paid the hit score.
   Proven: tank cost an idle P1 1 health every 8 frames (4 of 4); 0x4a 47 of 47, 0x4c 35 of 35 contact hits; 0x4d has contact damage 0; contact never rolls a knockback (0 of 23, GRUNTS). `$f82e` is the real attack test (hurtbox vs the player's attack rectangle `+72..78` while the player's `+28` is non-zero); every punch landing on a 0x1d bike cost the attacker 1 (3 of 3).
3. **Flags in `+0` and `+17`.** `+0` bit 3 = invulnerable (`$22c56` and `$22ce4` skip such a record; `$24022` sets it for 16 frames after a stagger, which is the 15-frame post-stagger immunity measured on 0x3f, 0x40, 0x44, 0x4a to 0x4d). `+17` bit 1 = immune to player hits, bit 2 = no contact damage, bit 3 = post-stagger flash timer, bit 0 = clamp to the screen instead of despawn (L5A).
   A hit lands only if `+0` bit 6 is set, bit 3 clear, `+17` bit 1 clear (0 wrong in 467 injected hits, L5A); consecutive scoring hits on one enemy are at least 32 frames apart (15 stagger + 16 flash).
4. **Score is paid on every hit that lands** (`$248bc` is called in the hit reaction), the kill value on the death state; BCD table at `$4016`: index 1 = 10, 2 = 50, 3 = 100, 5 = 200, 6 = 200/300 ... 14 = 1000, 19 = 3000, 21 = 4000, 23 = 10000, 24 = 1,000,000 (P1 score long at the player record + 60, `$8013c`; the hi-score `$80010` stayed at 1,000,000 in all runs). The rows of `$24952` for types >= `$4f` read past the table end (0x4f gives no score).
5. **The chooser `$2438a` runs every frame in state 7**, from state 6 only on an animation wrap, from state 8 after `$80` frames; only the random leaf routines test `+1` bit 7. 0x39 never calls it. 4d states 7 and 8 call it every frame (L5A). The chooser's predicted state sets matched the log 145 of 145 (4a), 179 of 179 (4b), 1804 of 1867 (4c), 164 of 164 (4d).
6. **`$81e03`** and the camera rules are in section 3. **Pool C** records (hit boxes) are spawned and cleared inside one frame (`wtap.lua`: 151 of 151 for the 0x35 box `$24`).
7. **The census bot corrupts later spawns if it clears only byte 0** (found by GRUNTS): the stall breaker in `lua/objlog.lua` now zeroes all 64 bytes. Census runs taken before this fix (level 4 with a `K` line, the first level 5 run) were repeated; the logs used here are from the fixed script.

## 6. Bosses, event flags and how the levels end

### 6.1 Flag writers (static, `py/flag_setters.py`, `out/flag_setters.txt`, owners corrected)

`$80040` bit 2 (boss event running) is set by: 0x09 `$13208`, 0x0a `$13882`, 0x0b `$14438`, 0x0c `$148da`, 0x0d `$14bf4`, 0x0e `$150a4`, 0x0f `$15666`, 0x10 `$15c90`, 0x11 `$162f0`, 0x12 `$16552`, 0x1e `$1a24e`, 0x1f `$1a376`, 0x20 `$1a8e2`, 0x24 `$1b122`, 0x36 `$1c858`, 0x3a `$1dd38`, 0x48 `$201c2`;
cleared by 0x12 `$17238`, 0x48 `$20426` and the shared boss-death states `$23e2e`/`$23f7e` (shared engine code, which follow with bit 3 at `$23e5c`/`$23fac` and clear `$80041` bit 7 at `$23e54`/`$23fa4` when it was set).
`$80041` bit 7 is set by 0x0e, 0x0f, 0x10, 0x11, 0x12, 0x36, 0x48 (not by 0x1e, 0x0c, 0x1f, 0x3a, 0x4d). **Bit 3 of `$80040` is set at a boss death only when `$80041` bit 7 was set** (shared death) or by 0x12's own code (`$1725a`): so the 0x3a death ends level 3 only because 0x11 set `$80041` bit 7 earlier (proven, SPECIAL34), and 0x1f, 0x1e/0x0d and 0x0c deaths only unlock the scroll.
`$80400` bit 5 (arena flag, section 3.1) is set by every boss at its start, and cleared by the shared death states and by 0x12, 0x19, 0x1c, 0x46, 0x48, 0x4d, 0x4e, 0x4f and pool B 0x18/0x1c/0x1d/0x1e at their ends (`out/flag_setters.txt`).
`$80040` bit 4 (level cleared, read by the frame loop `$6f4`, which calls `$71c`) has three writers:

| writer | what | used in |
|---|---|---|
| `$c86a` | player victory routine `$c6d8` (called from `$a368` while bit 3 is set), solo path: 16 animation steps of 16 frames = 256 frames | every level when the player has no live partner; levels 1, 3, 4 always |
| `$ca6e` | same routine, pair path, 241 to 247 frames | levels 0, 2, 5 when both players are alive |
| `$20bd4` | pool A type 0x48 (final boss), state `$1d` | level 5 only |

Proven 12 of 12 (`l5b/py/levelend.sh <level> <P2>`: poke `$80040 = $88` at frame 1500 and tap the writer); re-run by the lead for level 2 with P2 (`$ca6e` at frame 1747) and level 4 solo (`$c86a` at frame 1756), identical to the table of `l5b.md` section 1.

### 6.2 The levels in order

**Level 3 (street).** Mid-level bosses: 0x17 var `$12` at scroll `$5f0` delivers 0x0c (health `$20`, clears `$80040` bit 2 only) and the arena freezes the camera at `$600`; 0x1f (Santa boss, health `$10`, 16 hits, +50 per hit, +10000 on death, throws grenades 0x3b to 0x3e which land as explosions of 10; death `$84` to `$80` at frame 1495 of the injected run, proven and re-run by the lead: bit 2 cleared at f1495, +10000 at f1359) in the arena `$800`.
End: 0x17 var `$22` at scroll `$a00` delivers 0x11 (health `$30`, +200 per hit, sets bit 2 and `$80041` bit 7) which at health < `$21` replaces itself by 0x3a (white-maned ape, health `$20`, +400 per hit, box `$29` 20 damage, spawns pool B `$51`, `$37`); the 0x3a death sets bit 3 (`$80040` 84 to 88, `$80041` to 0), 256 to 265 frames later `$c86a` sets bit 4, level 4 starts about 100 frames after that
(census run: bit 2 at frame 3065 for 0x0c, 4460 for 0x1f, 5468 for 0x11, bit 3 at 6007, bit 4 at 6263, level byte 4 at 6365; `$80041` = 1 at 6263 (`$8624`, the scene transition), 8 at 6365 (`$1730`)).
**Level 4 (mine and descent).** 0x1a mine carts (health 1, +2 px/frame, cargo of two grunts) bring grunts; 0x16 hover bikes shoot; mid boss 0x1e (health `$30`, +50 per hit, morphs into 0x0d (health `$20`) plus the sidekick 0x41 below `$21`) in the lower arena; end: 0x12 at trigger `$8f0`: mode 1 claw (not hittable, 1292 frames, can kill the player outright by setting his health to 0 at `$1689c`), mode 2 horned mutant at ($910, $2c0), health `$1e`, +300 per hit (30 of 30), +4000 on death, box `$22` 12;
death sets bit 3 by its own code (`$80040` 84 to 88 and `$80041` 80 to 00 in the same frame), bit 4 256 frames later (f4646), level 5 starts at f4748 (SPECIAL34 injected run; mode 0 waits for the scroll low byte `$8040b` == 0 and at `$8f0` it waited forever, 1 of 1).
**Level 5 (laboratory).** The staircase (forced scroll), the fighters 0x35/0x39/0x3f/0x40/0x44/0x4a/0x4b, mid-level 0x4c x4 and 0x4d (health 24, sets `$80400` bit 5 and `$81e03`; kill value 10000), then 0x4f (tube mutant, health 20, no score, grab chain), 0x4e (health `$20`, below `$10` it retreats and spawns 0x13), the scientist 0x13 (invulnerable for 673 frames of its scene, then 7 hits, score 10000 per hit), which becomes the final boss 0x48 (health `$27`, +1000 per hit, +1,000,000 on death) (details in section 7 and `l5b/l5b.md`).
Level 5 never sets bit 3; bit 4 comes from `$20bd4` 1010 frames after the 0x48 death.

### 6.3 Ending (proven, `l5b/l5b.md` section 3, 3 of 3 runs equal)

After `$20bd4` sets bit 4 (T0): `$71c` sees level + 1 > 5, `$746` sets `$80040` bit 6 and `$5fba` runs; the state word `$80016` advances 0 at T0, 1 at +255, 2 at +288 (the two heroes with the loot, speech boxes 12 to 14), 3 at +1189, 4 at +1222 ("THANKS TO CRUDE BUSTER", text 15), 5 at +1881 (staff roll), 6 at +3892 ("THE END"), 7 at +4409, `$80040` is cleared at `$758` at +4410 and the attract loop restarts (story crawl at +4479).

## 7. Type index (levels 3 to 5)

Health is the initial `+5`; hit and kill scores are BCD points paid by the game (verified live unless noted); damage is per pool C box type at dip column 0. "Doc" names the group document.

| type | handler | name | health | score hit / kill | damage and notes | doc |
|---|---|---|---|---|---|---|
| 0x35 | `$1c4f4` | heavy brute, stationary sentry in state `$11` | 12 | 50 / 500 (100 thrown) | sentry box `$24` 20, live only in animation frame 3 (12 of every 48 frames, reach +32..+80 px); fighter: grab-seize-throw (states b c d, 16+48+16 frames, -4 per throw), jump attack box `$0d` 20, advance box `$0c` 16; walk 0.5 px/frame; first hit ends the sentry state for good; state 8 is a soft lock next to the level 3 wall (open) | grunts |
| 0x39 | `$1d494` | clinger | 4 | 200 / 400 | punches b then c, boxes `$00 $01` 12; a body bump in state 7 makes it cling (state d): -1 health to the player per 16 frames, shaken off by mashing buttons (about 110 frames); var 3 (level 5, nine entries) starts in state f and leaps in at 2 px/frame; walk 1.5 px/frame; no stagger immunity | grunts |
| 0x3f | `$1e9f4` | flamethrower trooper | 8 | 200 / 1000 | stab box `$05` 12; back-flip then flame jet 88 frames, box (pool C type 4) 20, reach 80 px, fires at dx 128 to 255; walk 1.0 | grunts |
| 0x40 | `$1ec1c` | kickboxer | 8 | 200 / 3000 | boxes `$25 $26 $28` 16, dash `$27` 20; four-hit combo 72 frames; walk 0.5; var 1 and 2 (riders dropped by 0x17) wait in state 0 until x `$a80`/`$a90` | grunts |
| 0x44 | `$1faac` | whip man | 8 | 400 / 3000 | boxes `$0f $10 $12` 12, jump attack `$11` 16; does nothing while `$80406` < `$200` (never in level 3); var 0 waits in state 0 until scroll x `$500`; var 1 starts at once; walk 0.5 | grunts |
| 0x1a | `$19344` | mine cart carrying two grunts | 1 (never changes) | none | +2 px/frame (188 of 189 steps), removed at scroll x + `$140`; no hit routine | special34 |
| 0x16 | `$184a2` | hover-bike gunner | 0 | index 17 = 2000 on a hit (read) | flies left at -2 px/frame, fires pool B `$3a` bullets (1 damage); kill not reached live | special34 |
| 0x17 | `$18906` | hover platform that delivers a boss (var `$12` -> 0x0c; `$22` -> 0x11 + 2 x 0x40 + 0x34) | 0 | none | not hittable | special34 |
| 0x19, 0x45, 0x46 | `$18c0e`, `$1fbe0`, `$1fd16` | tank, driver, gunner (level 3) | 3, 5, 2 | none | tank shuttles x `$931` to `$981`, 1 damage per 8 frames on touch; gunner missile 10; tank vanishes when the driver dies; holds `$81e03` | special34 |
| 0x1d, 0x33 | `$19dc4`, `$1c312` | motorbike and rider (level 3) | 3 | none | -2 px/frame, each punch knocks it back `$20` and costs the attacker 1 | special34 |
| 0x1e, 0x0d, 0x41 | `$1a14c`, `$14b18`, `$1eda4` | level 4 mid boss, its second form, its sidekick | `$30`, `$20`, `$80` | 50 per hit (read) | 0x1e body starts when `$80406` >= `$200`; morph below `$21`; death does not set bit 3 | special34 |
| 0x1f | `$1a2c6` | Santa boss (level 3) | `$10` | 50 / 10000 | no pool C box; grenades; death clears bit 2 only | special34 |
| 0x0c | `$14824` | claw-armed brawler delivered by 0x17 var `$12` | `$20` | 100 per hit (read) | death clears bit 2 only | special34 |
| 0x11 -> 0x3a | `$16200`, `$1dbbc` | big boss then white-maned ape (level 3 end) | `$30`, `$20` | 200, 400 per hit | box `$29` 20 | special34 |
| 0x12 | `$1654c` | claw machine, then horned mutant (level 4 end) | var 2: `$1e` | 300 / 4000 | box `$22` 12; the claw kills outright | special34 |
| 0x4a | `$20d84` | cyborg mutant with metal claw arms | 16 | 300 / 2000 | var 0 and 1 identical (764 of 764 rows) | l5a |
| 0x4b | `$20eac` | skeletal android with a detachable flying skull (0x41) | 8 | 200 / 200 | throw landing -4 | l5a |
| 0x4c | `$20fca` | grey-suited fighter with a snake on the shoulder (snake 0x37, hp 1, death 50) | 16 | 200 / 10000 | contact 1; no boss flag | l5a |
| 0x4d | `$210cc` | tusked horned brute | 24 | 200 / 10000 | sets `$80400` bit 5 and `$81e03` while alive; contact damage 0; throw landing -8 | l5a |
| 0x4f | `$21448` | tube mutant (tube 2), overlays 0x42/0x43 | 20 | 0 | box `$22` 12 x5 per bash; grab chain: wind-up 32, squeeze 128 (-4 per 32 frames), release 32; death 96 frames | l5b |
| 0x4e | `$2120a` | brown beast (tube 3), same state routines as 0x3a | `$20` | 200 per hit, none on death | ranged box `$29` 20 from off-screen; below `$10` it retreats and spawns 0x13 | l5b |
| 0x13 | `$17296` | mad scientist on a hover pad (0x47) | 8 | 10000 per hit and kill | invulnerable for 256+128+97+192 = 673 frames, no attack, spawns 0x48 | l5b |
| 0x48 | `$1ffbc` | final boss, green tentacled mutant, 30 states, spawns 0x49 crawlers | `$27` | 1000 per hit, 1,000,000 on death | boxes `$1e` 20, `$1f` 20, `$20` 48 (flying dash), grab 4 | l5b |
| 0x49 | `$20bec` | crawler minion | 1 | 400 per hit | contact 1 | l5b |
| 0x34, 0x42, 0x43, 0x3b to 0x3e, 0x1b, 0x47, 0x25 | | riders, claw jaws, grenades, debris, pad follower, effect | | | role by body only | special34, l5a, l5b |

Drops: none of the fighters or bosses of these levels drops an item (6 of 6 grunt kills, none from 0x4a to 0x4d, none from the final sequence except the pickups of the crates). The pickups seen are pool B type 5 variant 1, spawned by the crates $46/$47 (six each), by 0x4b once, and by the droppers/vehicles of levels 3 and 4.

## 8. Open items

- Level 4: which phase of `$81e12` lets the camera descend (section 3.4); the second half of level 4 was never played naturally (injections only); the hang with five live enemies at y >= `$210` is reproduced twice but its release was not studied.
- 0x35 state 8 (terminal soft lock next to the level 3 wall, three runs of 784 to 1729 frames) and why one sentry did not come down in one run (cause not traced); whether it blocks the level 3 camera in a human game is unknown.
- 0x16 kill and score, 0x1a damage and destruction states, 0x19 tank run-over states and the tank's own health, 0x1d throw path, 0x1b, pool B 5/0 and 5/1 semantics, pool B `$4a` (a prop of the final room, never touched): all read only.
- No input was found that throws an enemy (only poking `+17` bit 6 reproduces state 4/5); a real throw drive is missing, so thrown-score values are table values.
- 0x4a state 8, 0x4b states 8/f/9, 0x4c states 8/9 under natural play; 0x4d at its real camera cell; 0x37 attack damage; 0x25 not identified; 0x4f actions 3 and 4 only by poke; 0x48 box `$21` (32) and states `$e`, `$f` never produced a hit; 0x4e never fought unclamped to the end.
- Second player target selection (`$22b48`, `+35` bit 7, P2 addresses) is read only.
- The prompt texts shown by `$1948` and the text ids used by the bosses were not decoded.
