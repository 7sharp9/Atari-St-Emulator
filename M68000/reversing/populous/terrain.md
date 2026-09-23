# Populous (Atari ST): world and terrain systems

All addresses are runtime absolute (TEXT at $ad58). "Verified" means an emulator run byte-matched the
statement or the Python reproduction; "inferred" means read from code but not exercised.

Scripts (in `py/`; working snapshots and callcap JSONs in `$POP_WORK` (default `M68000/scratchpad/pop/`, see README)):

| file | purpose |
|---|---|
| `popmem.py` | image/snapshot readers, `apply_callcap()` (RAM after a callcap JSON delta) |
| `popgen.py` | Python reproduction: `rand`, `raise_pt`, `lower_pt`, `walk`, `gen_land`, `tiles` ($c0ee), `scatter` ($12e06), `build_world(seed, prerolls)` |
| `popworld.py` | world names, name to number, LEVEL.DAT decode, conquest progression |
| `verify_gen.py` | byte compare of `build_world` against three real `$b316` runs (`cc_b316_*.json`) |
| `verify_cmd.py` | compare raise/lower commands run in the emulator (`cmd_*.snap`) with `popgen` |
| `maps_png.py` | renders `h_*`, `alt_*`, `shape_*`, `feat_*`, `occ_*` PNGs and `raise_11_16_delta.png` |
| `level_table.txt` | all 99 LEVEL.DAT records decoded |

## 1. Map data

The world is 64x64 cells. Heights live on the 65x65 cell corners; everything else is per cell.
Cell index is `y*64+x`; corner index is `y*65+x`. x runs to screen right-down and y to left-down in the
diamond view. (0,0) is the top of the book minimap, checked against the in-game minimap (`gameplay.png`).

| address | size | type | contents |
|---|---|---|---|
| `$34be4` | 65x65 | word | **corner height** 0..8. 0 = sea level. Only ever changed through `$bf60`/`$d262`, flood and clear |
| `$33be4` | 64x64 | byte | **cell altitude** (derived by `$c0ee`) |
| `$36e78` | 64x64 | byte | **cell shape / terrain code** (derived by `$c0ee`, then overwritten by rocks, swamps and buildings) |
| `$3c522` | 64x64 | byte | **cell feature**: trees `$32..$34`, building codes `$20..$2b` and `'*'` ($2a) from the people code, +$15 when a building is destroyed (`$108b8`) |
| `$37fd4` | 64x64 | byte | **cell occupant**: entity index+1 (entity array `$3b278`, $16 bytes, entity+8 = cell index) |
| `$38fd8` | 64x64 | byte | per-cell visit counter used by walkers when they choose a cell (`$ef4c`/`$f2f4`); zeroed by `$c0ee` |
| `$36ce8,$3b006,$3d522,$37eb8` | word | | dirty box min x, max x, min y, max y. `$bf60`/`$d262` grow it, and the callers clamp it to 1..63 and pass it to `$c0ee`/`$c27a` |
| `$37f8a` | word | | count of unit corner changes by the last raise/lower (cost basis) |

`$bbd4` (reset_world_state) zeroes all six maps (heights `$1081` words, the others `$1000` bytes), the
211 entities, and both player records. Its initial values: mana 399, magnet at cell $820 = (32,32). In the
tutorial ($37ebc==3) the mana is 10000. In a conquest world numbered above 1235, evil's mana is 2700.

### Cell derivation `$c0ee(x0,y0,x1,y1)` (verified by exact match of `$33be4/$36e78/$3c522`)
For each cell, with corners a=(x,y), b=(x+1,y), c=(x+1,y+1), d=(x,y+1):
```
s    = (a+b+c+d) >> 2
bits = [a>s] | [b>s]<<1 | [c>s]<<2 | [d>s]<<3
if shape==$2f and (bits or s): bits = $2f (a rock survives unless the cell becomes fully sea)
else shape = bits
if s and not bits: s -= 1; bits = $0f       (flat land is drawn as all-corners-up one level lower)
if s==0 and bits not in (0,$0f): bits += $10 (shore slope)
alt = s; if shape != $2f: shape = bits
if bits==0: feature = 0                      (sea wipes trees and buildings)
visit = 0
```
Shape codes: `0` sea; `1..$0e` slope (corner mask) above sea; `$0f` flat land; `$11..$1e` shore slope;
`$1f,$20` the built-up flat around a house (written by `$10366` as `$1f + owner`); `$2f..$31` rock
(only `$2f` survives a re-derive: the scatter's `$30/$31` become ordinary slopes when their cell is
re-derived, `$c194..$c232`); `$35` swamp; `$42` burnt field of a razed settlement (`$108b8`, verified
in play, mechanics.md 3.5). `$21ea0` (16 bytes, from the
LANDn header) maps shape to a colour index (inferred, used by `$12f84`).

PNGs (`py/maps_png.py` regenerates the full set): `h_game_start.png` (heights), `alt_*`, `shape_*` (blue sea, green land, sand shore, grey rock,
purple swamp, yellow house field), `feat_*` (trees green), `occ_*` (occupied cells). Snapshot value
histograms at game_start: heights {0:3254, 1:461, 2:266, 3:141, 4:73, 5:27, 6:3}; features 27/17/28
trees of the three kinds, 7 building cells; 8 occupied cells.

## 2. Raise / lower

Commands reach the terrain through the per-player command record `$21e0c + p*$2e` (byte 0 = command,
1 = x, 2 = y). `$1e712` runs once per frame for p = 0,1 and dispatches through the word table `$21614`
(base `$1e712`):

| cmd | routine | effect |
|---|---|---|
| 1 | `$1186c(p,x,y)` | raise corner |
| 2 | `$116fa(p,x,y)` | lower corner |
| 3 | `$12350` | earthquake (x,y = view origin) |
| 4 | `$12a14` | swamp (x,y = clicked cell) |
| 5 | `$111be` | papal magnet (cost 200, sets `$3b228+p*16`) |
| 6 | `$1263c` | volcano (x,y = view origin `$37e7a,$249ae`, written at `$d00e`) |
| 7-10 | `$11486` | spawn a walker |
| 11,12,13 | inline | paint-map editing: cycle trees `$32..$34`, cycle rocks `$2f..$31`, remove a rock (the cell height must be below 7) |
| 14 | `$1f0fa(p,arg,sub)` | misc. Sub 3 armageddon, 4 flood, 5 knight, 11 mirror land `$11270`, 12 clear land `$113ce`, 13 set landscape type |

**raise_point `$bf60(x,y)`** (verified): reject if x or y is outside 0..64 (returns 0). If h<8:
`$37f8a++`, h++, then visit the eight neighbours in the order E, SE, S, SW, W, NW, N, NE. For each neighbour
where `h - neighbour > 1`, recurse `raise_point(neighbour)`. After that, grow the dirty box with the
original (x,y). Return the final h. The comparison reads raw memory (row wrap and reads outside the
array), but any call made for an out-of-range neighbour is rejected, so the result equals clamped
semantics. **lower_point `$d262`** is the mirror: it requires h>0 and recurses where `neighbour - h > 1`.
Neither routine has a slope limit other than this difference of at most 1 between the 8 neighbours.
Heights are clamped to 0..8.

**cmd_raise `$1186c` / cmd_lower `$116fa`** (verified): allowed if mana (`$3b232+p*16`, long) >= 10
(`$21988`), or paint-map mode (`$3b276`) or armageddon (`$3d524`) is on. (cmd_lower checks only mana or
paint-map.) They seed the dirty box with (x,y), clear `$37f8a`, call the point routine, then
**cost = 4*$37f8a + 10**, charged only when neither flag is set. Affordability is checked before the
change, so mana can go negative. `$c0ee` and `$c27a` are then run over (minx-1, miny-1)..(maxx, maxy).
Emulator proof (`verify_cmd.py`, command injected into `$21e0c` from game_start):
- Raise at the (11,16) peak: 134 corner changes, all equal to Python. Mana went from 542 to -4. The
  delta is in `raise_11_16_delta.png`.
- Lower at (11,16): 1 change, mana 542 to 528.
- Raise at the sea corner (30,10): 1 change, mana 542 to 528.

Effect on contents: `$c0ee` rewrites shape for every cell in the box, so a house field (`$1f/$20`) that
stops being flat loses its code. The feature is cleared only when the cell becomes sea. The occupant map
is untouched. The people code then reacts to the new shape (not traced here).

The computer player uses the same commands. `$135fc(cell,p)` scans the 9x9 spiral `$227d8`. It issues
cmd 1 where the centre is higher than a neighbour, and cmd 2 where it is lower or the cell is swamp or a
burnt field; when a cell is rock it issues cmd 2 and bumps the rock code. With harmful water, the
computer queues cmd 1 under a drowning walker (`$e012..$e058`, inferred). A no-input run shows this: the
heights diverge from the generated map only in the south-east start area. The count of differing cells is
42 at `repro`/`game_start` (tick 285), 53 at g90, and 233 at late4 (tick 2161). Evil's mana is spent
(42 at repro). `watch` on the height map caught the writes from `$bfb2`/`$d2b2`, called by `$1e712`.

## 3. Generation

**PRNG `$16702`** (verified): `seed = (seed*$24a1 + $24df) & $7fff` on word `$3d52e`. The result is in
D0.w; D0's high word holds the high word of the product, and every caller uses only the word. The period
is 32768.

**new_world `$b316(skip, type)`** (verified with three callcaps from game_start):
1. Seed. In conquest (`$21d5e` = world number, not -1): `seed = LEVEL.w8 + (world & 7)`; landscape type
   = LEVEL.b5; `$14be8(type,0)` loads LANDn (tile graphics plus a $72-byte header of tables; it holds no
   heights). b0..b4 are copied into the player records (see section 4). Otherwise (custom game) the seed
   is the current `$3d52e` (a number typed at the world dialog only survives to here from GAME SETUP >
   CONQUEST; see "The world dialog" below). In that case, if seed != 0 and `rand()&1` and type == -1,
   the landscape type advances by 1 (mod 4). `$37ec2` keeps the seed.
2. `$bbd4` reset, which consumes **4 rand() calls** (2 per player).
3. `$be84` gen_land = `walk(2,4); walk(4,2); walk(3,3)`. **walk `$bebc(rx,ry)`**: `x = rand()%64,
   y = rand()%64`. Loop `raise_point(x,y)` until it returns exactly 6. Each step does
   `x += rand()%(2rx+1) - rx`, then the same for y with ry, and clamps both to 0..64. So there are three
   hills (random walks) that stop once a point reaches height 6.
4. `$c0ee(0,0,63,63)`.
5. **scatter `$12e06`**: 22 clusters. Each cluster draws `r1=rand(), r2=rand()`, then makes 30 tries at
   `x = rand()%9 + r1%59, y = rand()%9 + r2%59`. A try is valid when x and y are below 64, the shape is not
   0 and not `$2f`. On a valid try, clusters 0-6 set shape = `$2f + rand()%3` (rock) and clusters 7-21 set
   feature = `$32 + rand()%3` (tree).
6. `$c27a` redraw; `place_start_walkers $120c6` (no rand calls): the count per side is LEVEL b6/b7
   (`$22ade/$22adf`) in conquest and in the tutorial; otherwise 1 without a computer opponent, else
   `1 + 2*(god[side].+12 > 4)`. Side 0 takes the first flat `$0f` cells from cell `$80` upward, side 1
   from `$f80` downward, then any empty land; each walker has str 45; the score `$36cea` gets +10 per
   walker of the human side only. Then `seed++` (`$b506`). Verified 28/28 (counts, cells, str, score
   credit) on 7 built worlds (`py/endgame/placement.py`).

`verify_gen.py` result: heights, `$33be4`, `$36e78` and `$3c522`, plus the final seed, are identical to
`build_world` for three worlds:
- conquest world 0 GENESIS: seed $6302, 4 pre-rolls
- conquest world 1235 SADINDON (LEVEL record 49 poked, desert): seed $0454
- custom seed $1234: 5 pre-rolls, and the type became 1

The same generator from seed 0 (click.snap path) also matched the pre-play snapshot `postgen.snap`
(1959 raise steps).

**World names** (verified by callcap of `$1d5fc` and `$16702`): world n uses `seed=n; v=rand()`, and the
name is `P1[v&31] + P2[(v>>5)&31] + P3[(v>>10)&31]`. The tables are `$21d64` (RING VERY KILL SHAD HURT
WEAV MIN EOA ...), `$21f7c` (OUT QAZ ING OGO ... A E I O U T Y) and `$21efc` (HILL TORY HOLE PERT MAR CON
... ER ED ME AL T). World 0 is the literal "GENESIS" (`$215e0`) in the briefing and in `world_number`,
but `$1d0e6` names the next world through `rand(n)` for n = 0 too, so the world offered after 2470 is
shown as SHISODING; `world_number` maps SHISODING to 0, the GENESIS map. `$1d714` parses a name by greedy prefix
match per table, requires full length, then returns the first n in 0,5,...,5000 with `rand(n)==code`
(errors -1..-5). All names 5..2470 round-trip (`popworld.py`). Examples: 5 HURTOUTORD, 25 SCOQUEMET,
1235 SADINDON, 2470 WEAVUSPERT.

**LEVEL.DAT** = 99 records of 10 bytes, record = world/25, read by `$1a5c4` into `$22ad8`:

| byte | meaning | where it goes |
|---|---|---|
| b0 | his rating 1..10 (shown as `(10-b0)/2` into VERY POOR..VERY GOOD) | `$21e3a+12` |
| b1 | his reaction speed 1..10 (`(10-b1)/2` into VERY SLOW..VERY FAST) | `$21e3a+16` |
| b2 | his powers: bit0 earthquake, 1 swamp, 2 knight, 3 volcano, 4 flood, 5 armageddon | `$21e3a+14 = b2<<3 \| 7` |
| b3 | your powers (same bits) | `$21e0c+14 = b3<<3 \| 7` |
| b4 | flags: 1 water fatal (else harmful), 2 swamps bottomless (else shallow), 4 cannot build, $10 built just on towns, 8 only built up (else built on people) | `$219b2` |
| b5 | landscape 0 grass, 1 desert, 2 snow/ice, 3 rock (LANDn) | `$3b246` |
| b6,b7 | starting walkers, you / him | `$120c6` |
| w8 | seed base (seed = w8 + (world&7)) | `$b338` |

In the player power word, bits 0-2 are always set: modify land, attack towns, attack leader (the "OPTIONS FOR EVIL" menu items 1-3, see `ai.md`). Bits 3..8
gate `$12350/$12a14/$12ba0/$1263c/$11f6a/$12d26`. `level_table.txt` lists all records.

**Conquest progression `$1d0e6(score)`**, called only after a won conquest game with the score `$36cea`
(a lost conquest game, TRY IT AGAIN, rebuilds the same world; a lost custom game builds a new one from
the running seed; both verified). World number `$3c51a`; `$21d5e` is what the briefing returned (-1 in a
custom game).

```
old = world
world += score/5000 + 1                    ; ldiv, word add
if world % 5: world += 5 - world % 5
if world > 2470:
    if old == 2470: world = 0; conquered = 1
    else:           world = 2470
seed = world; name_buf = world_name(rand())          ; $1d5fc, for world 0 too
```

The LORD screen (`$14f54`; if it fails to load, the world is restored and the name cleared, `$1d5ba`)
shows `WELL DONE <rank> YOU CONQUERED <old name> NOW BATTLE AT <new name>`, rank =
`settings_string_table[24 + world/250]` (MORTAL, IMMORTAL, ETERNAL, DEVA, GREATER BEING, DEITY, GREATER
DEITY, MORTAL GOD, GREATER GOD, ETERNAL GOD), or after 2470 `WELL DONE YOU HAVE CONQUERED EVIL` / `THE
BATTLE IS OVER BUT TRY <name>`. It waits for a click, reloads `gmusic1` and runs the world dialog.
Verified: `next_diff.py` 65/65 cases (new world, name, conquered flag; 4 wrap to 0), and through the UI
3/3: GENESIS won with 500 goes to 5 HURTOUTORD, won with 50300 to 15 TIMUSLUG, 2470 won with 71450 to 0
SHISODING with the EVIL message; each following briefing showed the predicted name and loaded the
predicted LEVEL record. Score contributions: +10 per starting walker of the human side and the power
bonuses of section 4 (credited only to the local side `$3affe`); the end-of-game formula is in
`mechanics.md` 6.

**The world dialog `world_select_screen $1a5c4`** (rows `$2166e + $2e*i`; START GAME at x 32..144, NEW
GAME at x 192..288, y 168..184):

```
if name_buf == "": name_buf = "GENESIS"
first pass: validate name_buf; later passes: edit_text_field($37e86, 16 chars)   ; $188b0
if name_buf[0] is a digit: $3d52e = $37ec2 = atoi(name_buf); name_buf = ""; return -1
n = 0 if name_buf == "GENESIS" else world_number(name_buf)      ; < 0: NO SUCH WORLD, edit again
read LEVEL.DAT record n/25 into $22ad8                          ; no file: INSERT THE ORIGINAL POPULOUS DISK
NEW GAME: name_buf = "", edit;  START GAME: human side 0, computer side 1 (ctrl 0/1), $219b0 = 1,
    paint and armageddon off, $3c51a = n; return n
```

`edit_text_field` reads `read_key $20068` (scancode `$20021` through the tables at `$2009a`/`$2011a`),
upper-cases, accepts $20..$7a up to 15 characters, BACKSPACE/DELETE, RETURN or START GAME ends. At the
boot briefing (`$b5c4`) and after a win (`$1d5da`) the caller just loops on -1, so a typed number is
dropped and GENESIS comes back; only GAME SETUP > CONQUEST (`$1ba14`) keeps it (`$21d5e` = -1,
`$3c4de` = 1, then `new_world(0,-1)` at `$1fa86` on the custom path: typed 1234 built
`build_world(1234, 5)`, landscape 0 -> 1). Verified through the UI (NEW GAME, typing, RETURN, START
GAME): 45/45 checks over SADINDON (1235), LOWLOPMAR (1240), WEAVUSPERT (2470), SHISODING (0) and
GENESIS (0): world number, `$21d5e`, LEVEL record and the built world against `build_world`. The
computer starts with 2700 mana above world 1235 (verified on 1240 and 2470) and 399 otherwise.

**Start paths.** `main $ae14` sets the game mode `$37ebc` = `atoi(argv[1])`, 1 without an argument
(`$ae38`). `game_mode_setup $1c7a6` runs before the main loop: in mode 3 (tutorial) only, it copies
`$22af2`/`$22b20` over both god records, sets pause `$3b274` = 1, seed `$3d52e` = `$37ec2` = `$69bc` and
the game options `$219b2` = `$22ad6` (1, water fatal); in all modes pointer 1, `$3d528` = 2 and
`$3c4b8` = `$3c4b0`. `$b510` then builds `new_world(0, 1)` while `$21d5e` is -1 (the custom path); only
mode 2 then runs the briefing and `new_world(0, -1)`. The mode is cleared at `$b5b0`/`$b5ea`, so its
tests apply to the first world only (tutorial human mana 10000 at `$bd9e`; `reset_world_state`'s
`$d1c2`/`$d0c0` panel calls run only when it is 0).

| | custom (1) | conquest (2) | tutorial (3) |
|---|---|---|---|
| first world | seed 0, 4 pre-rolls | seed 0, replaced after START GAME | seed `$69bc`, 5 pre-rolls |
| god records | DATA defaults: human +12 1, +14 $ffff, +16 1; computer +12 5, +14 $ffff, +16 3 | from LEVEL | computer +12 10, +14 3 (modify land, attack towns), +16 10; human +14 $3f (no volcano, flood, armageddon) |
| walkers you / him | 1 / 3 | LEVEL b6/b7 (GENESIS 3/3) | 15 / 3 |
| mana you / him | 399 / 399 | 399 / 399 (him 2700 above world 1235) | 10000 / 399 |
| options `$219b2` | $10 | LEVEL b4 | 1 |
| starts | running | after START GAME | paused |

The tutorial is a preset practice world against a passive computer (VERY POOR, VERY SLOW), paused
until the player lifts the pause; there is no other tutorial code. Verified by booting each mode from
the DEMO.GOD title menu (`py/endgame/boot_check.py`, 35/35: mode, first world against `build_world`,
`$21d5e`, mana, god records, options, pause, frame count after 20M more steps).

## 4. Terrain powers

All six powers share one gate (`$11f6e`, `$12354`, `$12640`, `$12a18`, `$12bbc`, `$12d2a`):

```
if paint map ($3b276): skip all of this (no cost, no checks)
refuse if mana[side] < cost               (signed long $3b232 + 16*side; costs $21990..$219a4)
refuse if armageddon ($3d524)             (armageddon itself does not test it)
refuse if paused ($3b274)
refuse if !(god_rec[side].+14 & bit)
mana[side] -= cost
if side == human ($3affe): score $36cea += bonus   (also in paint mode, except armageddon)
```

The knight first requires a leader, before the gate and also in paint mode. Sound requests go to
`$36d02` (the VBL plays `code - $42` while sound effects `$21920` are on).

| power | routine | cost | bit | score | sound | RNG draws |
|---|---|---|---|---|---|---|
| earthquake | `$12350(side,x,y)` | 2500 | $08 | 25 | $4c | one per corner that is non-zero when visited, 2 passes of 81 |
| swamp | `$12a14(side,x,y)` | 5000 | $10 | 50 | none | exactly 60 |
| knight | `$12ba0(side)` | 7500 | $20 | 150 | $45 | none |
| volcano | `$1263c(side,x,y)` | 10000 | $40 | 100 | $4b | 165, then one per in-map cell of the 8x8 square |
| flood | `$11f6a(side)` | 40000 | $80 | 250 | $4a | none |
| armageddon | `$12d26(side)` | 80000 | $100 | 5000 | $49 | none |

Earthquake and volcano seed the dirty box `$36ce8/$3b006/$3d522/$37eb8` with (x,x,y,y), grow it with
every height change, clamp it to 1..63 and then run `$c0ee(minx-1, miny-1, maxx, maxy)` and the
minimap redraw `$c27a`. `$37f8a` is not reset by either power. Earthquake and volcano act at the
view origin `$37e7a,$249ae` (the UI posts it; graphics.md, "Mouse input").

- **Earthquake `$12350`**: `$2287a -= $a0`, 20 frames of screen shake (`$2287a` alternately
  -$1e0/+$1e0, `$14364` draw, `$16ed8` flip and VBL wait), `$2287a += $a0`. Then 2 passes over
  cx = x..x+8 (outer), cy = y..y+8 (inner): skip the corner if its height is 0 **at that moment**
  (raw read, no bounds check); otherwise `r = rand()%5`, r=1 raises, r=2..4 lower, r=0 nothing. The
  number of draws therefore depends on the terrain and on the first pass. It ends with `$b15a`,
  which waits for the sound player to go idle.
- **Volcano `$1263c`**: `for a in 0..4: for i in a..8-a: for j in a..8-a: if rand()%5 in (1,2,4):
  raise_point(x+i, y+j)` (165 draws, a cone of up to 5 levels). Then for cells x..x+7, y..y+7 inside
  the map: `if rand()%5 != 0: continue`; skip the cell if it is one of the protected cells; else
  shape = `$2f` (rock) and feature = 0. The protected cells are both papal magnets `$3b228/$3b238`
  and "the leader cell", read twice from `$3b226`, so **side 0's leader is protected and side 1's is
  not**; with no side-0 leader the protected cell is (0,0). The test comes after the draw, so it never
  changes the RNG sequence. `$c0ee` keeps the `$2f` unless the cell became full sea.
- **Swamp `$12a14`**: 30 tries: `cx = x + rand()%7 - 3; cy = y + rand()%7 - 3` (both draws always
  taken); inside the map, if the shape is `$0f/$1f/$20/$42` and the cell has no occupant, shape =
  `$35`. No dirty box, no re-derive, no minimap redraw. A walker on `$35` dies (`$e9a4`); with
  shallow swamps (option bit 2 clear) the cell reverts to `$0f` after one victim.
- **Flood `$11f6a`**: every corner with h > 0 drops by 1 (the sea rises one level), then
  `$c0ee(0,0,63,63)` and `$c27a(0,0,63,63)`. Settlements on cells that become sea turn into flags $12
  and, with "water is fatal", die: on GENESIS a flood from `drive/A.snap` drowned 4 of the 8
  settlements (two per side) within 12 frames.
- **Knight `$12ba0`** and **armageddon `$12d26`** do not touch terrain (mechanics.md 3.5 and 5).

Proof (`py/powers/`, section "Scripts"): the Python models in `powers_ref.py`, run in place on a full
RAM image, match the real routines under `callcap` on **2670/2670** randomized states (`pw_diff.py 40 2026` and
`40 77` over `game_start`/`g90`/`late4`; full DATA+BSS delta and RNG seed; earthquake's shake frames
need the VBL, which callcap masks, so its RNG and re-derive half is tested by a callcap started at
`$12470`, 150/150; 240 of the states are town take-overs, mechanics.md 3.5), and **8/8** casts made through
the game's UI with popdrive (flood, earthquake, two volcanoes, swamp, armageddon, two knights) match
on all 37824 state bytes between the routine's entry and exit. The volcano's leader asymmetry was
cast both ways: with the seed set at entry so a rock falls on (56,55), evil's leader's settlement
became rock and nine frames later a walker; the same draw on good's leader cell (9,13) was skipped.

- **Water**: sea is height 0 / shape 0. On a walker flagged in water (entity byte 0 & $10), fatal water
  kills it at once (`$dfcc`); harmful water takes the other path (inferred, people code).
- **Trail effects** (`$13372` spawn, `$12f84` tick; slots $d1/$d2): trees, swamp or rock marked
  along a path across the map; `systems.md` 1.
- **Paint map**: cmds 11-13 and cmd 14 subs 11, 12 and 13. Mirror `$11270` copies the higher of
  h[i]/h[$1080-i] to both, and copies trees/buildings (`$32..$37`) point-symmetrically. Clear `$113ce`
  zeroes all maps and kills every entity.

## Open questions
- None specific to terrain. `$3b274` is pause and power-word bits 1-2 are attack towns / attack leader
  (`systems.md` 3, 4); LOLO1.GAM is a truncated save (`systems.md` 5.2).
