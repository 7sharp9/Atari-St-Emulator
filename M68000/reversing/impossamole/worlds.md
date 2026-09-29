# Impossamole: the five worlds

Everything outside the Amazon (`README.md`, `graphics.md` are Amazon-centred). The game's engine is one program; a world is
data: three files loaded by `$b328`, a set of `$bb76`-indexed tables in the code, and the per-world spawn types. Nothing structural
differs. All five levels are the same 420-block, 1680x24 collision map (`$31800`) over the same 16x16 tile chain (`$29000`,
`$29800`), rooms are installed the same way (`$18ed4`, exit lists `$e0aa`), and `py/tiles.py --check` matches the live screen at
offset (32, 8) in every world (Amazon 98.7, Klondike 98.7, Orient 98.3, Ice Land 98.8, Bermuda 97.4 % of 10,560 samples). Every
world was reached from a fresh cold boot with the cold-boot scripts in `py/worlds/` (icon presses on the world-select screen, two
separate `kbd` calls each, held fire to confirm); the icon cursor is object slot 0 `78(A0)` and `$bb76` = icon + 1.

| icon | world | `$bb76` | data (`$53000`, packed) | bank 1 tail (`$40600`) | bank 2 tail (`$4c400`) | own spawn types | boss |
|---|---|---|---|---|---|---|---|
| 0 | Klondike Mine | 1 | `MDATA1.DCH` | `MINES22.DAT` | `MINES33.DAT` | 10-13 pickups, 14-49 enemies | 53 |
| 1 | The Orient | 2 | `MDATA2.DCH` | `ORIENT22.DAT` | `ORIENT33.DAT` | 59-62 pickups, 63-93 enemies | 99 |
| 2 | The Amazon | 3 | `MDATA3.DCH` | `JUNGLE22.DAT` | `JUNGLE33.DAT` | 105-108 pickups, 109-132 enemies | 138 |
| 3 | Ice Land | 4 | `MDATA4.DCH` | `ICELND22.DAT` | `ICELND33.DAT` | 146-149 pickups, 150-183 enemies | 191 |
| 4 | Bermuda Triangle | 5 | `MDATA5.DCH` | `BRMUDA22.DAT` | `BRMUDA33.DAT` | 198-201 pickups, 202-235 enemies | 244 |

Types 0-9 (small props, the mole) and 251 (dormant effect markers) are common to every world.

## Loading

The common loader `$b288` reads `CHARS11` to `$24000` (font), `SPRTS22` to `$3b600` (`$5000`, bank 1) and `SPRTS33` to `$42e00`
(`$9600`, bank 2). The per-world loader `$b328` (from world select `$b0ee`) reads the 12-byte record `$b3ea + 12*($bb76-1)`,
three name pointers into the `$b3ac` strings, and sends each file through `$1c6de`: `MDATAn.DCH` to `$53000` (`$c800`
buffer, depacked by `$3b4`), the `*22.DAT` file to `$40600` (`$2800`) and the `*33.DAT` file to `$4c400` (`$6c00`). All are
LSD!-packed (tag, unpacked length, packed length). `$18812` (A0 `$53000`, A1 `$25000`) then expands the MDATA file into the
`$25000` region: classification table, spawn list `$27200`, block map `$27600`, block definitions `$29000`, tile bank `$29800`,
collision map `$31800`. The names come from A0 at `$1c6de` (the GEMDOS trace logs only function numbers). A win or death later
reloads `PICTURES.DCH` (`$fa00` to `$53000`) and `SELECT44.DAT` (`$5000` to `$4c400`) through `$b2d8`.

## Sprite banks: what is common and what is per world

The per-world files overwrite the tail of each common bank. Bank 1 (`$3b600`, 128-byte frames, 240) frames 0-159 are common and
160-239 are per world; bank 2 (`$42e00`, 384-byte frames) frames 0-99 (hero, shop bubbles, mole, explosion rings) are common and
100-171 are per world; the font is identical. `py/worlds/compare_banks.py` against the Amazon: Klondike bank 1 0-159 identical
160/160, tail 21/80, bank 2 0-99 100/100, tail 0/72; Ice Land 160/160, 18/80, 100/100, 0/72; Bermuda 160/160, 0/80, 100/100, 0/72;
Orient checked frame by frame with the same result. The extent of each bank comes from the LSD! headers, not from the last
non-zero frame: Klondike bank 2 is `MINES33` `$5a00` = frames 100-159 (real art to 150, 151-159 zero), and frames 160-171 there are
noise (zero-byte fraction 0.05-0.10 against at least 0.13 in real frames; inferred residue of `SELECT44.DAT`'s earlier load at
`$4c400`, not compared byte for byte), so "172 frames" holds for the Amazon, Orient (real to 169) and Bermuda only. Last real frames:
bank 1 218 (Klondike), 200 (Orient), 187 (Amazon), 221 (Ice Land), 239 (Bermuda); bank 2 150, 169, 171, 166, 171. Sheets:
`graphics/<world>_sprites_bank1.png`, `_sprites_bank2.png` (clipped to the header extent, world-specific frames labelled).

Palettes are `$2166e[$bb76-1]` (`$216a2`, `$216c2`, `$21722`, `$21682`, `$21762`) and equal the live hardware palette in every world
(`graphics/world_palettes.png`).

## Collision categories

The Amazon table uses only 0-4 and 9 (`graphics.md`). The other worlds add 5-8, and the code reads them from the foot sensors
`$227e8/$227e9`:

| cat | where | effect (live-checked unless noted) |
|---|---|---|
| 5 | Klondike ids `$72 $73 $75`, Orient, Bermuda tiles 114/115/117 (conveyor left) | in hero states 0/1 (`$c36e-$c44a`) `subq.w #1,2(A0)`, needs x > `$1c`; blocked when a side sensor (`$227e0-2`, `$227e4-6`) reads >= 4. Klondike platform (cols 396-399): x `$64` to `$58` in 24 samples; Bermuda 2929 to 2925 in 140,000 steps |
| 6 | Klondike `$74 $76 $77`, Bermuda 116/118/119 (conveyor right) | `addq.w #1,2(A0)`, needs x < `$104`. Klondike (cols 388-391) `$a5` to `$b0`; Orient belt (cols 696-703) `$96` to `$a1`; Bermuda 2051 to 2055 |
| 7 | Ice Land mounds and one 8-cell flat patch (row 20, cols 148-155), Bermuda tile 255 (ship deck, 78 cells) | slide: with no stick held the hero keeps moving 2 px per update in its facing direction (`$227f4`) until a side cell is >= 4 (`$c536`, `$c558-$c5ba`, `$c362`). Ice patch: 24 px of slide over 300,000 steps after releasing right; ordinary ground coasts 2 px and stops within about 20,000 steps |
| 8 | Klondike `$92-$97` (slow ground), Orient `$ce-$d1` (grass tops), Bermuda rock terrain (2925 cells) | half-speed walk: `$c92a-$c98c` (mirror `$ca12`) moves 1 px per iteration instead of 2 and plays sound 7. Klondike `$40` to `$46` against `$40` to `$4c` on category 4; Bermuda 12 px in 300,000 steps against 12 px in 150,000. Orient category 5/8 not tested |
| 9 | Klondike green sludge `$78 $79 $e4`, Orient water `$e0 $e1`, Ice pools and icicles, Bermuda sea (1696 cells) | hazard; `$eb3e` (state <= 1) tests `$227e8/9 == 9` and subtracts damage at `$eb8c`. What a fall into the water costs was not measured |

The hero's camera-follow pull toward x=192 adds -2 px per iteration, so drift tests with x above 192 read conveyor plus pull.
`tiles.py --cats` and `level_map.py` (`CATTINT`, `CATCOL`) knew only the Amazon categories, so `py/worlds/world_pipeline.py` extends
the tints at runtime (`graphics/<world>_categories.png`).

## Rooms and routes

`$c028` (8 bytes per world) holds the start room; `$e0aa` points to the five exit lists (`$e0be`, `$e1a6`, `$e2d4`, `$e3a8`,
`$e47c`). `py/level_rooms.py <snap>` prints a world's graph, `--route S E` the shortest exit chain to a room. All 53 exit records of
Klondike and Orient were poke-warped and gave the five predicted fields (`$227b4`, camera, limit, hero x; 23/23 and 30/30,
`py/worlds/census_warps.py`), so the room-installer arithmetic of the Amazon holds for both.

| world | start room | exits | boss room | route to the boss |
|---|---|---|---|---|
| Klondike | `0..55` (limit `$5e0`) | 23 (5 top: blocks 266, 296, 304, 332, 359) | `375..383` (camera = limit `$2ee0`), by the bottom exit at block 406 from `384..409` | 12 hops (`graphics/klondike_level_map.png`) |
| Orient | `0..107` (limit `$c60`) | 30, several adjacent triggers (114-115, 335-338, 215-218, 308-310, 393-395) | `400..408` (camera = limit `$3200`), by the top exits 393-395 (hero x `$20`) | 6 hops: bottom 103 (`156..170`), top 167 (`171..222`), bottom 215 (`223..295`), bottom 290 (`312..327`), top 324 (`346..399`), top 393 |
| Amazon | `0..137` | 21 | `318..326` | 4 hops: bottom 135, top 168, top 283, bottom 317 |
| Ice Land | `0..127` | 21 | `402..410` (camera = limit `$3240`) | 3 hops: bottom 123 (`141..309`), bottom 306 (`364..402`), bottom 398 |
| Bermuda | `0..40` | a chain of 25 short rooms (9-80 blocks) | `400..408` (camera = limit `$3200`) | 17 hops, alternating bottom and top exits |

The Bermuda chain is `0..40 -> 40..70 -> 70..89 -> 90..110 -> 110..140 -> 140..160 -> 160..170 -> 170..190 -> 190..199 -> 200..230 ->
230..250 -> 250..259 -> 260..270 -> 270..290 -> 290..310 -> 310..320 -> 320..400 -> 400..408`. In the Amazon the whole route was played
with real input (`README.md`, "The route to the boss room on real input"); in the other worlds the warps are poked.

## Bosses

The boss is the level's only kind-2 spawn record; the allocator `$1021a` reads its type word from `$10370` (`[2, 2, 3, 2, 2]`, so the
Amazon is the odd one out). All five have 60 hit points and end the level by writing `$22803 := $ff` in a death block of the same shape
(`README.md`, "How a level ends"). Each was killed live: from the warped boss room, `py/worlds/boss_kill_world.py` (which, unlike
`boss_kill.py`, keeps `$bb76`) places a real fire pulse's shot on the boss and took hit points 60 to 0 one at a time in every world (Orient
60 pulses, Ice Land 60, Klondike 223 because that boss ignores hits while `79(A0)` is non-zero, Bermuda 202 because it is shielded in
phase 2). The shot position was poked in all four, so contact and damage are proven there and natural aim only in the Amazon.

| world | type | descriptor | handler | `bcs` site | writer | spawn | contact dmg | picture |
|---|---|---|---|---|---|---|---|---|
| Klondike | 53 | `$10f2a` (`02 10 18 18 03 3c 01`) | `$0148e8` | `$01491e` | `$014ad6` | block 378, y 168, room `375..383` | 1 | grey segmented larva rising from the floor, parts in slots 7-9 |
| Orient | 99 | `$115aa` (`02 30 20 18 02 3c 01`) | `$0154a4` | `$0154b0` | `$015752` | block 405, y 120, room `400..408` | 1 | green dragon, slots 7-10 |
| Amazon | 138 | `$11aee` | `$015e9a` | `$015eb2` | `$01602e` | block 324, y 120 | 1 | tree face on a trunk |
| Ice Land | 191 | `$122a6` | `$016886` | `$0168b2` | `$016958` | block 406, y 72, room `402..410` | 1 | ice-cream cone with eyes (frames 161, 160); no shield phase (`$13a9c` every frame), flies x 47 to 259 |
| Bermuda | 244 | `$12a60` | `$017514` | `$01754e` | `$0176a6` | block 406, y 144, room `400..408` | 2 | tornado (frames 160-166), a second part in slot 8; phase byte `78(A0)` = 2 skips `$13a9c` at `$01753c` (shielded; script `$17796`, a step per 16 frames) |

## Klondike Mine and The Orient

- Klondike spawn list: 229 records (95 kind 0, 133 kind 1, 1 kind 2). Enemy types 14-49: 14 rock-strip ambusher (`$013cb4`, shared
  with Amazon 109 and Orient 63; hp 254), 15/16 dynamite figure (hp 255, dmg 2), 17/18 mine cart, 19 lantern goblin (hp 10), 20-22
  skeleton (hp 4 or 255), 23 dirt pile, 24-37 rock bat (hp 1/2/255), 38/39 red-capped bug, 40 stalagmite (`$01439e`, shared with the
  Amazon's crumbling rock 113), 41/42 boar (hp 4), 43-47 green frog (hp 255), 48/49 rock strip (`$1468e`, `$14706`, shared with Orient
  92/93). Pictures come from the decoded frames (`graphics/klondike_spawn_types.png`), 36 of 49 types matched live pixel for pixel.
- Orient spawn list: 222 records (105, 116, 1). Enemy types 63-93: 63 striped-block ambusher, 64/65 monkey with a staff (hp 255),
  66/67 tumbler, 68 ninja (hp 8), 69/70 yellow kung-fu fighter (hp 5), 71/72 cloud (hp 255, dmg 0), 73 straw-hat monk (hp 10), 74
  black-haired fighter (hp 255), 75-84 paper crane (hp 1/3/255), 86/87 lantern box (hp 15), 88/90 orange sumo (hp 8), 91-93 orange
  strips; 33 of 40 matched live (`graphics/orient_spawn_types.png`).
- Klondike bank 2 frames: 100-111 dynamite figures, 112-115 carts, 116-127 skeletons, 128-129 rock strips, 130-135 lantern goblin,
  136-141 boar, 142-143 rubble, 144-150 boss; bank 1 world frames 160-163 pillar, 164 dirt pile, 165-172 dust, 173-179 rock bat,
  180-185 frog, 186-191 red-capped bug, 192-195 ore, 196-198 stalagmite, 199-207 spiders, 208-210 diamonds, 211-213 chest,
  215-218 white ovals. Orient bank 2: 100-105 monkey, 106-109 tumbler, 110-115 black-haired fighters, 116-121 monk, 122-133 yellow
  fighter, 134-141 ninja, 142-147 clouds, 148-150 orange strips, 151 striped block, 152-155 sumo, 156-169 dragon; bank 1: 160-163
  stripes, 164-169 paper cranes, 170-177 lantern boxes, 178-180 Buddhas, 181-182 teacups, 183 bow, 184 blade, 185-186 dashes,
  187-192 lightning, 193-200 fireballs. Frame checks: Klondike hero frame 0 319/319, skeleton (125) 283/283, bank-1 frame 175 86/86;
  Orient hero 278/319 and monk 102 485/485.
- Klondike's conveyors are the roller tiles over sludge pits (`graphics/klondike_conveyors_room93.png`).

## Ice Land and Bermuda Triangle

- Ice Land spawn list: 227 records: 146-149 pickups (ice cream, cone, lolly), kind-1 enemies 150-183 (black flying birds 151-160,
  snowman and rolling snowball 162-163, sledding figure 164-166, blue ice monsters 167-168, silver flying pieces 169-170, penguins
  171-172, red-suited dwarf 173-175, polar bear 176, fountain and water jets 177-178, ice blocks 179-183), boss 191 and 47 type-251
  markers. Pictures are inferred from the decoded frames (`graphics/ice_spawn_types.png`).
- Bermuda spawn list: 249 records: 198-201 pickups (blue skull, chest, nose, nut, coconut, shell), enemies 202-235 (202/203 black-coated
  pirate with a blue dome, 204/205 pirate with a "BANG" gun, 206/207 swordsman, 208/209 cannon, 210-218 seagulls, 220-224 barrel and
  ghosts, 225/226 lamp, 227/228 green goblins, 229-231 grey flying machine, 232-235 fireworks or smoke), boss 244 and 49 type-251
  markers (`graphics/bermuda_spawn_types.png`). Bermuda uses every category 0-9 in one map; its one-way plank decks are category 3.
- Bermuda is locked at the start (`$bb79 = $10`) and opens after the other four worlds are won (`README.md`, "How a level ends"); the
  runs here poked `$bb79` to `$0f` (`w bb78 000f0100`) and needed about 4M steps of cursor travel before fire registers, because a fire
  pressed while the cursor is still moving (`$227f3 = 0`) is lost and, once `$227f3 = 1`, the lock test at `$17e2c` is skipped.
- World 5 is the only one whose completion goes to the ending screen (`ending_screen.png`).

## Other `$bb76`-indexed tables

Values dumped, roles read from the code around each access (not all exercised):

- `$ff76`, 8 bytes per world (mask longword, pointer): the random re-spawn table used by `$ff0c`. Every 8th frame it picks
  `(random >> 8) & mask` and, if the record's column is inside the camera window, calls the spawner `$10006`. Klondike has four records
  at `$ff9e` (col 863 row 8 type 20; 863/20/20; 1320/12/24; 1428/4/15); Orient and Amazon have none, Ice Land three, Bermuda more.
- `$130f2`: pointers to per-world pickup score tables, indexed by bank-1 frame minus 175 (Amazon fruit 400, 800, 1600, 3200; Klondike ore
  192 = 400, 193-195 = 800, diamonds 208-210 = 1600, chest 211-213 = 3200; Orient Buddhas 178-180 = 400, teacups 181-182 = 800, bow 183 =
  1600, blade 184 = 3200).
- `$179d8`: four-byte groups of pickup types per world (`10-13`, `59-62`, `105-108`, `146-149`, `198-201`) used with a random 0-3 at
  `$179a2` by the drop routine `$17984`.
- `$13f88`: wait count of the stone-strip ambusher `$13cb4` (`25` for worlds 1-4, `15` for Bermuda); `$13be6` sound bytes
  (`36, 0, 43, 29, 1`); `$fb92` sound bytes (`37, 40, 42, 46, 50`, played from `$fb76`).
- `$ee16`: per-world routine table `[$ee2a, $f050, $f31c, $f5ea, $f868]` used at `$edf8` after the space-key (`$39`) test; `$ed72` skips
  one palette reload in world 5. `$ea92`: 16 bytes per world, the shop room and its return room (`README.md`, "The shop"). `$c028`
  words 0-1 are `(1,4)`, `(1,4)`, `(3,4)` for worlds 1-3 (passed to `$c050`; meaning not decoded).
- Klondike's first skeleton reaches the hero within about 1M steps of gameplay start; no parallax layer, vehicle or different tile size
  was found in any world.

## Files

Images in `graphics/` per world (`klondike_`, `orient_`, `ice_`, `bermuda_`): `_tileset.png`, `_level_tiles.png` (13440x192),
`_level_map.png` (with rooms), `_categories.png` (whole level, categories 5-8 tinted), `_sprites_bank1.png`, `_sprites_bank2.png`,
`_spawn_types.png`, `_gameplay.png`, `_boss_room.png`; `klondike_conveyors_room93.png`. Scripts and cold-boot recipes: `py/worlds/`
(`py/README.md`). Open items: `sessions/impossamole.md`.
