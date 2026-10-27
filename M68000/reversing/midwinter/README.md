# midwinter: Midwinter (Rainbird / Maelstrom Games, 1989)

Mike Singleton's Midwinter: a war on a frozen island, played through 32 characters who ski,
hang-glide, drive snow buggies and ride cable cars across fractal terrain (generated from a coarse
height grid, `terrain.md`) drawn as filled 3D polygons. It is the repo's first 3D game. The emulator boots it from a French
compilation disk, runs the menu, the title, the team and character screens and the first-person
ski view with a Bomber attacking, all unmodified apart from one poke that stubs the menu's fullscreen VBL handler (below).

## Design digest

The game's rules restated for re-use in another design, without addresses. Each line names the section that proves
it (T = `terrain.md`, A = `ai.md`); anything not proven there is labelled inferred. It covers what is decoded so far:
the island, the enemy army, the encounters, the attacks on the player, the player's weapons, sabotage, the period
end and the endings. The 3D renderer, the vehicles' handling, and the characters' relationships and recruitment one
by one are not decoded yet.

### What carries the game

- **An island generated, not stored.** A 50 x 50 grid of heights covers the whole island. Wherever the player is, five
  rounds of diamond-square subdivision refine it into a 100 x 100 grid around the player at 32 times the resolution.
  Each new point's displacement is a hash of its four parents, not a random number, so the same place always has the
  same hills. (T intro, T 2, T 3)
- **The war is a walk on a road graph.** 32 enemy units move over 96 sites joined by up to four roads each. A unit
  steps a fixed distance toward its next site and captures it on arrival, then picks a road at random among those
  leading to sites the enemy does not hold yet. There is no planner. (A 2)
- **Supply is speed.** Every game hour each unit's speed is recomputed from the Warehouses and Synthesis Plants the
  enemy holds, weighted by distance, so each supply building taken speeds the advance near it. (A 2)
- **The enemy moves between the player's turns.** It gets a 42-tick head start, then nine ticks each time the player
  ends a 2-hour period from The Team screen; it does not move while a character travels. (A 2)
- **One unit at a time comes to life.** Only the unit inside a window around the player is materialised. Its five
  vehicle counts (Snow bulls, Tankers, Snow wolves, Snow cats, Snow foxes) feed objects into the view one every five
  frames, each kind in proportion to what is left, at most 38 per encounter. Bulls and tankers drive in convoy along
  the unit's route to its next site; wolves, cats and foxes wander. (A 3)
- **You fight one vehicle at a time.** Of the encounter's vehicles, the highest-numbered one to come within 16 grid
  cells of the player is engaged, once each, and only it can be hit. Each travel mode has its own weapons and rounds
  carried by the character: on skis Space throws a grenade that homes within 1000 and kills within 150; driving has
  a rocket, a gun and an anti-aircraft weapon; sniping destroys whatever is drawn under the crosshair. Every shot
  resets the engaged vehicle's wait, so firing invites its missile at once. (A 3, A 6)
- **Attrition is permanent.** A destroyed vehicle comes off the unit's own counts and its strength (1, or 2 for a cat
  or fox); at 0 the unit is destroyed. Destroying a unit's command vehicle destroys the unit at once. (A 3)
- **Decapitation.** Six units are leaders of four units each. Destroying a leader destroys its whole group wherever it
  is, including stationary garrisons that would otherwise take 255 strength to wear down. (A 3)
- **The air war is aimed at the player, not the map.** In the 3D view a Bomber or a Spotter (whose arrival brings a
  five-shell mortar barrage) is launched at the player with odds of 1 in n per frame, n growing with the distance from
  a fixed point beyond the island's corner nearest the enemy headquarters, and with a per-character byte; the engaged vehicle fires missiles.
  The options' BOMBERS, MORTARS and TRAINING switches and each vehicle's own mask decide which can come (no missiles
  while gliding, nothing in one mode, inferred to be the cable car). A hit within 200 ends the trip. Sites change hands only by the army's
  walk. (A 4)
- **Sabotage ruins buildings, never sites.** A character at a site with explosives (from a Magazine or a Store)
  marks buildings on the PLANT EXPLOSIVES screen, each costing charges (fewer with more Sabotage skill) and minutes,
  and the plunger turns them all into Ruins at once, raising Morale. The site's owner and the army's units are
  untouched; what changes is everything that counts buildings: a held site's ruined Warehouse or Synthesis Plant
  slows every unit from the next period end, a ruined HQ wins, and ruined Radio Stations bring the full team.
  (A 7)
- **The situation report is the scoreboard.** Every number on it is a live count: free Heat Mines, buildings the
  player has blown up by type, units and vehicles destroyed, prisoners (characters inside a Police Station of an
  enemy-held site), and the enemy's held Factories, Synthesis Plants, Warehouses and Radio Stations and its mobile
  units and vehicles. Each period the team loses Morale for the enemy's gains: 2 per supply or radio building and 10
  per Heat Mine above the previous high mark. (A 3, A 5)
- **Three endings and one reward.** Blowing up the enemy Headquarters wins; so does lasting 20 days, when General
  Masters' troops desert; losing every Heat Mine to the enemy makes the Free Villages surrender. When the enemy holds
  no Radio Station (only sabotage can bring that about, since sites are never released), every character joins the
  team at once. (A 5, A 7)
- **Deterministic.** One generator, `s' = (s * k + k) mod 65537 - 1`, drives the army's choices and every encounter;
  the terrain uses no random numbers at all. That is what lets the gates replay the game's routines exactly. (A 2, A 3,
  T 2)

### Limits that became features

- **No stored map detail.** 2,500 heights and a hash give the whole island at 32 times their resolution, with the
  same ground on every visit. (T)
- **The 3D view never simulates the army.** The strategic layer stays a cheap graph walk run between turns, and the
  view only has to animate one unit's vehicles near the player, using simple rules (follow a route, or wander and
  turn with chance 1 in 16). (A 2, A 3)
- **No strategic pathfinding.** The road graph is the path. Locally, convoys take a randomised greedy route with
  wall-following through the 100 x 100 blocked-cell grid, ending at the window's edge. (A 2, A 3)
- **Fixed tables.** 32 units, 96 sites, 41 object slots and an encounter cap of 38 objects. (A 2, A 3)

### Bugs and accidents a new design should drop

- Five sites have no roads, so the walk never reaches them; three of them are handed to the enemy at the start, and
  the other two can never fall: nothing else takes a site. (A 2, A 4)
- The attack odds measure the player's distance from the Enemy Headquarters' map coordinates read at terrain scale,
  a point off the island beyond its far corner, so "attacks grow near the headquarters" survives only as a direction
  (inferred intent). (A 4)
- A missile is given the launching vehicle's heading after its aim at the player has been computed, so the
  computed aim is thrown away and the missile has to steer onto the player's path. (A 4)
- When no road leads to an unheld site, the unit picks among roads 0 to 2 only, so a site whose fourth road is its
  only way out never sends a unit that way from this branch. (A 2)
- A bull drawn for a unit that is not moving places nothing, while a tanker drawn falls through to the wolf test: the
  two kinds are skipped differently. (A 3)
- An object's count is taken before a free slot is found, so with every slot full the drawn vehicle is lost from the
  encounter. (A 3)
- The engagement scan keeps the vehicle's kind in the register that held the camera's x cell, so after an
  engagement the rest of that scan tests the wrong box and clears the latches of vehicles that were in range. (A 3)
- A glider's shot destroys its target's object without calling the kill, so a glider hit would not count against
  the unit (read, not gated). (A 6)
- A draw with all five counts at 0 divides by zero and survives only because the zero-divide vector is a bare `rte`
  (read, not driven). (A 3)

## Provenance

| item | value |
|---|---|
| archive | `Zuul #67.zip` (sha256 `1f853028f6e330b92c480f9b7fa7c0afcffa8b64356b395323b55cf5988f9611`), one file `ZUUL067.MSA` (sha256 `9e2b3d59534ffbd66f5e6e0e94f1d71b117c82b4314456220fdda464aad58316`, 753855 bytes) |
| disk image | `tools/msa2st.py` gives `zuul067.st`, 839680 bytes (82 tracks, 10 sectors, 2 sides), sha256 `07bc54a8bbc8792a67e0d812e6972163649a5994fa7b1083ef6f4390fe413a09` |
| compilation | Zuul (French cracking group) menu disk 67: a boot-sector anti-virus ticker ("ZUUL VOUS PRESENTE SON ANTI-VIRUS V1.0 / CODE PAR STIX"), `\AUTO\MENU67.PRG`, F1 Midwinter, F2 the other game (`PACT2.PRG` names `MORTEL.PRG` and `INFEST.2`) |
| game executable | `1.1` (`LSD!`-packed, 85702 bytes) unpacks to a GEMDOS program, sha256 `10acff2dc6f2fe0fe1207b81bf9d495722263c330261e31b35c8cbb2237445dd`: text `$259a2`, data `$7b8c`, bss 0, no relocation table |
| data | `00.2` .. `60.2`, all `LSD!`-packed; `ZZZZZ.PRG` (packed raw code that installs `$68`/`$70`/`$118`/`$114`) |

The disk images and the archive stay untracked.

## Packing

Every game file is `LSD!`-packed: a byte-buffer variant of Pack-Ice 2.x whose decoder is in the menu's
`PACT.PRG` (text `$1f6` checks the magic, `$2d4` decodes). `tools/lsd_depack.py` is transcribed from that
routine and unpacks all 63 files on the disk; each output is the header's length and each decode consumes the
source to exactly the first data byte. The format has no checksum, so those two checks cannot catch a wrong
literal byte. `PACT.PRG` and `PACT2.PRG` are themselves wrapped twice in the menu's "ZUUL & HIDDEN PACKER V1.2"
stub (ByteKiller-style, `py/bk_stub.py`); `PACT3.PRG` is a Pack-Ice 2.4 self-extracting program, not unpacked.

The unpacked `1.1` is the program in RAM at load base `$800` (text `$800..$261a2`, data to `$2dd2e`). At the
program's first instruction (`u 800` after the menu's F1, `scratchpad/midwinter/entry800.snap`) it differs from
the file in 1300 bytes, all in 14 runs, and every run is a crack patch made by the loader, not depack damage:
`bsr` calls replaced by `nop nop` (`$ffb8`, `$1001a`, `$1003a`), `beq` turned into `bra` (`$10302`, `$10346`),
`jsr $11c7e` into a `bra` (`$c10`), call displacements retargeted (`$ffc6`, `$10028`, `$10050`, `$102f0`), a
routine head replaced by `jmp $500` into a resident loader in low RAM (`$10cd2`), and two rewritten blocks
(`$10e1d..$111ce`, 946 bytes, and `$11c7e..$11e06`, 393 bytes; inferred to be the disk protection and loader).
So the depacker's literals are confirmed everywhere outside those runs.

The program is hand-written assembly: no `LINK A6` frame in the text, 1099 `rts`, 780 `jsr abs.l`, 404 `muls`
and 129 `divs`. The trace and callcap route applies, not a decompile.

## Driving it

`drive.txt` runs from a 20M-step cold-boot snapshot to the first-person ski view; two runs give byte-identical
snapshots at all six milestones (title, options, team, character, decisions, ski):

```
cd M68000
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll 20000000 snapshot scratchpad/midwinter/cold20.snap --disk-a scratchpad/midwinter/zuul067.st
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/midwinter/cold20.snap repl --disk-a scratchpad/midwinter/zuul067.st < reversing/midwinter/drive.txt
```

Three emulator gaps, all in input or timing and none in the game, affect the drive. Two are fixed in the emulator;
the third is bypassed by a labelled poke:

| where | what the code does | gap | `drive.txt` |
|---|---|---|---|
| boot-sector ticker `$172c` | `cmpi.b #$39,$fc02.w / bne $1704`: polls the ACIA data register for space | fixed: the data register used to return 0 once TOS's ISR had taken the byte; it now keeps the last byte, as a 6850 does | `u 172c`, then SPACE (`kbd 39`, `kbd b9`) |
| menu key loop `$a4e4` | reads `$fc02` three times per pass (`cmpi.b #$3d / bgt`, `cmpi.b #$3b / blt`, then `move.b $fc02.w,$a404.l`) for F1..F3 | fixed by the same change: every read now sees the same key | `u a4e4`, then F1 (`kbd 3b`, `kbd bb`) |
| menu VBL `$a5e0` | a fullscreen border-removal routine, mostly timed `nop`s | open: the emulator raises the VBL every 12,000 instructions, not every 160,256 cycles; the handler runs about 36,000 instructions, so the next VBL is pending when it returns and the main loop never runs (55 handler runs and 0 main-loop hits in 2M steps) | `w a5e0 4e730001`: the handler is an `rte` (no fullscreen menu art) |

Clicks are `mouse down l` / `mouse up l`: in relative mouse mode a button change sends a zero-motion packet
(`$F8|buttons 00 00`), and Midwinter reads buttons only from the packet header (`$664a`). Before that emulator fix
the REPL sent no packet and the drive injected `kbd fa 00 00` / `kbd f8 00 00`; those runs give the same six
snapshots byte for byte. Against the earlier drive, which poked the two ACIA loops, today's gives the same title, team, decisions
and ski screens pixel for pixel; options and the character screen differ by 34 pixels each, the mouse pointer caught
at another point of its redraw.

## Documents

| document | covers | proof |
|---|---|---|
| `architecture.md` | vectors, VBL, screen graph, map and 3D frame loops, the cracked loader | census counts per routine |
| `ai.md` | the character records (qualities and skills, clocks, position) and the enemy army: 32 units random-walking a 96-node road graph, capturing sites, with speed from held Warehouses and Synthesis Plants; the 42-tick head start at PLAY and nine ticks per situation report (the team screen's clock icon); encounters: the unit nearest the player and its five vehicle kinds placed around the player, losses, strength and the six leader groups; the period end's counts, prisoners, Morale loss, the report's numbers, the three endings and the radio recruitment; attacks on the player: Bomber, Spotter and missile launches by options switch and vehicle mask, their odds, bomb and shell hits; nothing but the walk takes a site; the player's weapons, the engagement and the kill; sabotage, its blast and what it changes | `py/army/gate_army.py`: natural ticks 42/42 and 9/9, supply 10/10, chained ticks 1000/1000, supply 284/284; `py/army/gate_encounter.py`: search 96/96 poked and 1/1 natural, frames 9600/9600 poked and 329/329 natural, kills 512/512; `py/attack/gate_attack.py`: launches 768/768 and 768/768, odds 1452/1452, missile 128/128 poked and 5/5 natural, bomb 1494/1494, shell 361/361, 0 feature-list writes over a 170-frame natural run; `py/army/gate_period.py`: natural 6/6, 200/200 per routine, the report's 14 numbers 14/14; `py/attack/gate_shot.py`: engagement 400/400, launchers 36/36 each, shots 798/798 each, tumble 48/48, odds 300/300, vehicle fire 144/144, and a driven kill against a no-fire control; `py/sabotage/gate_sabotage.py`: natural blasts 4/4, clicks 1500/1500, blasts 100/100 per type, 1700/1700 with units and nodes untouched, supply after a blast 110/110, and driven sabotages at a village, a held Warehouse, the HQ and the Radio Stations, each against a control; Stark's 14 bio ratings 14/14 |
| `terrain.md` | the island's height field: file 37.2's 50 x 50 grid refined by five diamond-square subdivisions with a hash displacement into a 100 x 100 grid around the player, then heights, building pads and triangle shading | `py/terrain/gate_terrain.py`: generator 70000/70000 cells over 7 windows, post-passes 10000/10000 |

## Architecture

`architecture.md` holds the program skeleton with its census counts:

- the vectors and the IKBD ISR (`$6400`; pointer x/y at `$24fa2`/`$24fa6`, buttons `$24fba`);
- the VBL fan-out and the pointer mode `$62b8`;
- the jmp-linked screen graph: each screen sets an icon list at `84(A6)` and waits in `$bcfe`; `$bcaa` hit-tests 32 x 32
  icons, and a longword action table either `jsr`s and redraws or `jmp`s to the next screen;
- the two real frame loops: the map (`$1546`) and the 3D travel frame `$14e00`, with its landscape render `$18304`,
  draw list `$19ce2` and goggle mask `$1bbe6`;
- the cracked loader: file number in `348(A6)`, `jmp $500` into a resident FAT12 loader plus the LSD depacker.

The character screen's watches and running figure are not buttons: its six icons at y 168 are map, decisions,
team, previous, next and S.O.S, and Decisions' ski icon (x 128) starts the first-person view.

## Milestones

| screenshot | screen |
|---|---|
| `title.png` | title, "Insert graphics disk / Press any key when ready" (after F1 in the menu) |
| `options.png` | Game Options (mouse, joystick, mortars, bombers, ...) and PLAY |
| `team.png` | The Team, Capt Stark only at the start |
| `stark.png` | character screen: biography, qualities and skills, icon bar |
| `situation_report.png` | the SITUATION REPORT after The Team's clock icon (`ai.md` section 2) |
| `map.png` | the full island map with its legend (huts, bunkers, cable cars, heat mines, ...) |
| `decisions.png` | Decisions: the travel and action choices |
| `ski.png` | first-person skiing through the goggles: terrain, a building, the HUD (speed, compass, map) |
| `radio_kill.png` | the radio message after the player's grenade kills unit 27's command vehicle (`ai.md` section 6) |
| `hq_win.png` | the win screen `$115ae` after the Headquarters is blown up (`ai.md` section 7) |
| `rad_report.png` | the SITUATION REPORT after the three held Radio Stations are blown up: "You now have a full team !" (`ai.md` section 7) |
| `ski_crash.png` | 40M steps later: frame 170, when a missile from the engaged vehicle hits (`$14dfc` set by `$2061a`, `ai.md` section 4) and the game returns to Decisions with Stark's clock moved from 06:00 to 06:08 |

## Files

| file | what |
|---|---|
| `architecture.md` | vectors, VBL, screen graph, map and 3D frame loops, the cracked loader |
| `midwinter.sym` | routine names (`tools/merge_sym.py` format) |
| `drive.txt` | cold boot (20M) to the ski view, REPL script with the labelled VBL poke above |
| `repl/` | the REPL scripts behind `architecture.md`'s counts |
| `tables/` | icon/action tables, indirect jump sites, static file-load calls |
| `py/vectors.py` | lists the non-TOS vectors in a snapshot |
| `py/bk_stub.py` | unpacks the menu's ByteKiller-style self-extracting stub |
| `ai.md`, `py/army/` | army model `army_model.py` and its gate `gate_army.py`; encounter model `encounter_model.py` and its gate `gate_encounter.py`; period-end model `period_model.py` and its gate `gate_period.py` (all run the game's routines in `stserver`) |
| `py/attack/` | attack model `attack_model.py` (launches, odds, hits) and its gate `gate_attack.py`, with five broken-model controls (`gate_attack.py <control>`); the player's weapons `shot_model.py` and `gate_shot.py` (nine controls), `drive_kill.py` (a driven kill and its control), `radio_after_kill.py` |
| `py/sabotage/` | sabotage model `sabotage_model.py` and its gate `gate_sabotage.py` (eight controls); `drive_sabotage.sh` and its REPL scripts `*.txt` rebuild the driven snapshots in `scratchpad/midwinter/sabotage/` (run it before the gate); `poke_snap.py`, `radio_setup.py`, `repl.py`, `diff.py`, `state.py` |
| `terrain.md`, `py/terrain/` | terrain model `terrain_gen.py`, its gate `gate_terrain.py`, `render_terrain.py` |
| `terrain_island.png`, `terrain_local.png` | the whole island after the first subdivision; the shaded local grid of `d_ski.snap` |
| `gates.toml` | the promoted gates for `tools/gates.py` |
| `*.png` | milestone screenshots |

`tools/lsd_depack.py` (the game-file depacker) is in the shared tools.

## Not exercised yet

The 3D renderer (projection, draw list, polygon fill), the map render from the height grid, travel by any vehicle other
than skis (the driving and gliding weapons are gated from poked states only), a sniping kill, a kill with no position
poke, the surrender screen, the encounter's objects on screen, relationships and recruitment one by one, the other
game on the disk, a bomb or mortar barrage reaching the player in a natural run (both are gated only from poked
states), the Bomber's drop rule and the missile's detonation.
