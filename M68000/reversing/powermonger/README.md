# powermonger: the emulator bugs the cracks exposed, and what the analysis established

PowerMonger (© 1990 Bullfrog / Electronic Arts), driven from two scene cracks. The
[cr Replicants] build boots cold all the way into the **isometric battle view**: cracktro,
ICE depack, title and credits, name entry, option menu, campaign world map, the "Between Pages
1-5" mission briefing, and past the briefing's OK button into the height-mapped terrain view
(`iso_view.png`). Any of the 144 random lands can be built from the briefing snapshot and the
195-land campaign can be played through the real UI. The [cr Empire] build boots to its title
and the "Pondering over the map..." screen and has not been driven further. Five emulator
bugs the cracks exposed on the way (FDC self-test, shifter register gap, `SUBA.L` decode,
`DIVU` / `DIVS` overflow and zero divide, Timer A) are documented below. Gameplay, mechanics, AI,
economy, rendering and the system services are analysed in five topic documents, each backed
by a Python or F# reconstruction diffed against the real 68000 through `callcap`, or (where
noted) driven live through the game's own UI; "What runs, and what the analysis established"
below is the overview by topic. The scripts are indexed in [`py/README.md`](py/README.md).

| document | covers | proof |
|---|---|---|
| [`ai.md`](ai.md) | the entity/commander decision loop: the `$14b62` per-tick iterator, the 75-entry mode table, the 50-byte object record, spatial buckets, the mode catalogue and the per-mode handler pseudocode, target selection, the regroup/dissolve/forest-animator dispatch, the revolt chain `$550e`, `$5c2c`, `$25d6`, shepherds, animals and carrier pigeons, arrows, the `$15000` page of mode bodies; the evidence taxonomy | differential tests vs the real 68000: entity FSM core **675/1335/413/85/99** tracked bytes over 154 states; regroup `$3c08` **71/71** (22 states) + its group-teardown subtree **1847/1847** (13 states); contact reconcile `$4bc8` **51/51** + **20/20**; dying-entity `$1623c` **275/275** (23 states); group dissolve `$2776` **4119/4119** (28 states); lord's work order `$5cde` **768/768** + **85/85** returns (47 states); the revolt chain **1778/1778** over 49 states (all 27 natural `$550e` calls on 4 lands); conquest target pick `$4f68` **1804/1804** (192 states, 170 natural); shepherd cycle **1043/1043** (198 states), animal update **45094/45094** (55 snapshots); arrow loop `$596a` **4210/4210** (456 states), order pigeon `$4562` **1567/1567** (125 states); the `$15000` mode bodies **18452/18452** (1889 states); forest animator `$4342` 8 of 9 branches |
| [`economy.md`](economy.md) | the goods ledger (felling trees, invention, army-supply upgrades), the separate food/manpower ledger and every writer of it, the settlement record, the world-build population and job pick, the settlement heartbeat and the loyalty/revolt accumulator, weapon-grade "invention", buildings and town layouts | shares `ai.md`'s FSM and revolt-chain proofs; settlement heartbeat `$157e6` **99/99** natural (27 states, 12 branch families) + **85/85** synthesised; every `food`/`troops_field` writer enumerated from a ~1B-step watch and cross-checked against the player's own order paths; `troops_field` equals the live men on 416 lord instances (378 exact, 416 within 1); job pick `$2a98` **3310/3310** (146 states), population `$2984` **29860/29860** (8 lands, 1026 men; 41760/41760 over 8 Play Random Land builds); equipment exchange `$160f8`/`$16892` **385/385** (201 states) |
| [`strategy.md`](strategy.md) | the sim tick + measured cadence, the order executor pipeline (`$6522` decide, `$58016` command buffer, `$6a3a` execute, `$4b80` stamp), the player's commands and what each order does, force accounting, the 195-land campaign, diplomacy, combat, RNG/determinism, the world build, how a land ends, the developers' symbol names and the game's own text | driven live through the real UI and the emulator's REPL: mission 1 won and lost both ways (retire + natural defeat), every player order but `$04` and a real `$0e` exercised at least once, diplomacy's envoy/tribute/break traced end to end, and 4 lands' natural `$6522`/`$661a` decisions captured over 200M steps each and matched against the disassembly; gates: commander AI **323/323** natural + **280/280** synthetic states, executor **288** natural states + **80/80** synthetic, order senders and arrival executors **57039/57039** bytes over 2234 states, world build (`$10d1e` **22501/22501**, `$4672` **114947/114947**, `$238c` **44963/44963**, `$2eac`, `$2906`, `$1073c`), info panels (`_getname` 80/80 seeds, person 247/247, house 103/103, captain 12/12) |
| [`graphics.md`](graphics.md) | asset formats, the software heightmap rasteriser (projection, DDA span walker, dither), all 4 yaw quadrants, the 4 sprite sheets and their blitters, the sprite pick, camera control, zoom, the land build (colour bake, roads, land script), the minimap and the conquest map, palettes and fades | frame-pixel scoring against the real emulator's own composited buffer: **100.00%** match on 27 captures across every drawn category; the projection `$fec6`/`$fecc` Proven vs the real 68000 (**3240/3240** vertices, byte-identical corner buffer); the rasteriser maths (`$ef62`/`$e420`) byte-exact vs a live single-step; blitters **450/450**, minimap **512000/512000** bytes, land build `$10058` **125219/125219**, `$10410` **45779/45779**, `$10910` **2561/2561**, `$10638` **260/260**, `$ac20` **14539/14539** |
| [`system.md`](system.md) | the system services: the sample player (a Timer A DAC on the PSG volume registers, the per-frame sequencer, the bank layout), the save-disk code and its message strings, the serial link's MFP setup | `callcap` gates: 328/328 sequencer states, 300/300 Timer A passes, 56/56 sequence and 58/58 sample records |
| [`port/`](port/README.md) | a from-scratch Godot 4.x + F# port of the iso renderer: the porting contract (`port/SPEC.md`), the asset pack, an F# logic library, a Godot scene and a frame stepper | the port's frame matches the game's pixel for pixel on the 27 captures above; the F# rasteriser, projection and entity pass cross-checked byte-exact against the Python reference renderer `tools/pm_render_ref.py`; stepper `--selfcheck` 23/23 |

`powermonger.sym` (about 1,260 names) is the shared symbol file, feeding `trace_cfg.py --names` and the
disassembler. `powermonger_orig.sym` is the developers' own symbol table (1,196 names, cut to 8 characters),
recovered from `DATA\SPRITE40.DAT` by `py/s40_symbols.py` (`strategy.md` "Original names").

**Disks are not committed** (commercial). Reproduce:

```
unzip "Powermonger (1990)(Bullfrog)[cr Replicants].zip"
#   sha256 2099be892f49d779bbdf6f5d397b160c3048647c1d3c73d1fba2c0552cb02b31   819200 bytes  (820 KB, DS 80/10/2, bootable $1234, TDT "ALTAIR ANTI VIRUS V3.00" boot sector)
unzip "Powermonger (1990)(Bullfrog)[cr Empire].zip"
#   829440 bytes  (810 KB, AUTO\WARI.PRG, "SK Micro Intro 6.0 (C) 1990 YODA" cracktro)
```

## Design digest

The game's rules restated for re-use in another design, without addresses. Each line names the
section that proves it (S = `strategy.md`, A = `ai.md`, E = `economy.md`, G = `graphics.md`,
P = `port/SPEC.md`); anything not proven there is labelled inferred. `/handoff` re-checks this list
against every session's changes.

### What carries the game

- **You give orders, not controls.** The player picks an order icon (go, attack, get men, take
  or drop food, take or drop equipment, trade, set men to work, spy, a food supply line, offer an
  alliance, dismiss men, go home, a posture level ...) and clicks a target on the map; the order goes
  to the captain's group, whose lead walks there with the men following in formation. The first
  captain's own group acts at once; an order for any other captain is carried to him by a pigeon from the
  first captain's position and takes effect when it lands (code read for the player, 95 natural launches for the AI). The
  opponent lords issue orders through the same command slots and the same executor. (S "The
  player's commands", S "`$6a3a` / `$6ac6` / `$6b38` — the order executor", A "Arrows and carrier pigeons", A "What each entity decides per tick")
- **Every man is an individual in one table.** Each runs a small per-tick state machine: step
  toward the lead's target, check the ground, turn around an obstacle, fight a neighbouring enemy,
  pay upkeep. Followers do nothing but upkeep; their position is stamped from the lead. (A "What
  each entity decides per tick", A "The entity FSM")
- **Men are conserved.** A lord's counter is his men at home, not in an army: a man joining an army takes
  one off it, leaving puts one back, capture moves one between lords, and none is born after the world build (which gives every settlement two men). A side grows only by
  taking men from another, apart from the pigeon, which revives a dead man's record as a live home man where it lands (E 1, row `$42be`). (E 1, E 6)
- **The map starts populated, and the starting jobs are a lottery.** Every settlement begins with two men. Each draws a job in up to five rounds: a captain for the first man of every lord of
  kind > 3, otherwise shepherd (3 in 32), fisherman (16 in 32, needs a shore cell within nine cells, at most 30 per land), farmer (the rest, needs a free field site within nine cells) or,
  after five failed rounds, merchant. Shepherds come with 2 to 5 animals each (36 to 40 per land, a fixed pool), which wander, turn at the shore and are herded back to the town in a cycle;
  they have no effect on food or goods. (E 5a, A "Shepherds, animals and carrier pigeons")
- **Food is the pressure.** Each lord has a food store that his fishermen and returning men fill and his
  settlements eat; each army carries its own food. Armies take food from towns and drop it back;
  taking food angers a town, giving food or goods calms it. A town with at most 4 food per man at
  home grows unrest. The posture sets how much an order moves: aggressive all, neutral half,
  passive a quarter. (E 1, E 6, S "The player's commands")
- **Goods are a separate ledger.** Men felling trees and carrying them to the workshop credit one of eight item counters (pike,
  sword, bow, plough, boat, pot, catapult, cannon).

  **Merchants.** Merchants, the men the starting job lottery could place nowhere else (E 5a), are meant to carry goods between a nation's lords
  but none was seen carrying anything. A merchant's trip walks a table that never advances, so the destination is his home lord (leader 0 when the home lord is the last record), and the goods he banks on
  arrival come from the record after his home lord (a stale-register bug, proven by `py/fsm15/gate_fsm15.py` over 119 states of mode `$54`; A `$54` row, E 2b).

  **"Invention" is supply.** A man who walks to his lord's cell hands back his weapon
  and takes the best in stock (bow, then sword, then pike; a farmer also takes a Plough), so a weapon improves only when a
  better item reaches the lord. The hand-back has a stale-register bug that credits it to another lord's slot for lord
  indices 8 and up. There is no research timer. (E 2a, E 2b, E 2c, E 4)
- **Combat is a health grind.** Units in contact lock into melee; each tick the attacker takes 1 to 3
  (weapon grade 0, 2, 4; grade 6 and above takes 1) off the target's health (byte 45, the value the captain panel prints as "Very Sickly" ... "Very Strong", "Dead"). At zero the loser is killed or
  routed by a roll that the attacking group's posture can pin; a rout scatters the loser's
  group, which re-forms. Bows fire arrows: an arrow flies 20 ticks and ends on the first enemy man, pigeon or marker
  in its path (a man loses 82 health), and its end frees the archer to shoot again. There is no battle resolver. (S "Combat" 0, 1, 3, A "the combat path (mode `$32` melee)" for the gated drain;
  A "Natural runs on later lands", A "Arrows and carrier pigeons")
- **Land changes hands two ways: conquest by the player, revolt by the game's own clock.**

  **Conquest.** When every man of a lord's settlements is dead or routed by an army hunting him, the
  lord and all his settlements join the attacker (proven, and how mission 1 is won; the conquest arm
  of mode `$2c` made 16 of the 27 natural `$550e` calls).

  **Revolt mechanism.** A settlement's heartbeat pulse (`$157e6`) adds `+2` to its lord's loyalty pressure when his towns go hungry
  (`troops_field·4 >= food`) and takes `1` off when they do not, but **only on a marker's first pulse after it parks** (dwell
  `$ff9d` to `$ff9c`). Every pulse checks the pressure, and at 600 it sends the lord and his
  settlements to an effectively arbitrary side.

  **The player does not trigger it.** The park write is pinned (`$015052`, inside entity
  mode `$16`, gated on the global `$57fd0` season word). `$3c08` only sends a record into mode `$16` when its flags byte has bit 0 set, and the
  one place in the game that sets that bit is the world-build creation of a farmer (`init_far`, the
  village population), not any order. So revolt is a **periodic self-cycle of a parked farmer's
  winter state** (`$7c` and `$16` alternating on `$57fd0`'s rotation: 512 calls of `$1abaa`, 118.4M steps in mission 1, 85.7M on a Play Random Land; `$7c` is
  `in_winte...`, S "Original names"), running independently of the player.

  **Evidence.** The cycle crosses 600
  unassisted: 11 of the 27 natural `$550e` defections on four 200M-step no-input land runs fired
  from this heartbeat cycle at loyalty 600-608, differential-tested against the real 68000
  (`diff_revolt.py`, 1778/1778).

  **Deserters and spies.** A man dismissed or deserting and a spy (order `$20`) arrive in mode
  `$7e`, the same body with no season gate and a stale dwell: they never trigger the first-pulse
  adjustment (traced end to end for one starvation deserter), but each pulse still checks the
  pressure, so a spy walked into mission-1 lord 0's town (loyalty 608) revolted him on his first
  pulse. (E 3, E 3a, E 6, A mode `$2c`, A "The revolt chain", S "How a land ends",
  S "`$d322` + `$3e06`")
- **Winning is a ratio, not annihilation.** The score is `(2·mine + enemy/4) / enemy`, clamped to
  0..4; a land is won only by retiring while it reads 4, and lost by retiring earlier or by the
  captain's group dissolving. (S "`$d322` + `$3e06` → ... `$57fce`", S "How a land ends")
- **A campaign of 195 lands on a 13 × 15 map.** A land can be picked only next to a conquered one;
  each land's parameters come from a fixed table, and only the conquest map carries over. (S "The
  campaign")
- **Diplomacy is an envoy with tribute.** An alliance is offered by sending a group, carrying
  goods, to another lord; he accepts if his attitude plus the tribute clears a bar. It only makes
  the ally's settlements valid for friendly orders, and any contact between the two sides breaks
  it. Only the player ever offers. Driven end to end on land 25 with real clicks and no register pokes (5 pots to an ungarrisoned
  lord whose attitude is -8 are accepted, 3 pots are refused; only those two outcomes were observed); an envoy to a garrisoned lord dies to contact first.
  Afterwards take-food and take-equipment on the ally's town are accepted and a second offer is refused at
  the pointer test.
  (S "Diplomacy")
- **The opponent is simple.**

  **Marching.** Each commander marches at the nearest enemy lord when its army has
  the food for the trip (an army eats `men/8 + 1` per period, so big armies spend food fast). AI
  armies start with so much food (`$5fff`, losing about 96 per 50M steps) that the test never binds in any run: it would take about 13G steps by arithmetic and no run of 12G reached it.

  **Transfer order.** A small captain group handing its men to group 0 is natural but rare: 5 hits in 75 lands, after a defection leaves a lone captain. The order refusal cannot happen from any shipped call site (S "Natural coverage").

  **Get men, food, follow-ups.** A group under 22 men first goes to its
  own best town for men (order `$08`, get men), and the food fallback fetches food the same way. A group
  that has been in camp for 20 ticks then chains food, men, equipment and invention orders from a
  4-entry table (`$6762`/`$67d0`, keyed on the state it came back from); beyond those sequences it has no
  economy or build planning.

  **Invention order.** It is a race: the group holds state 9 for two or three decision passes
  and 26 of 30 natural orders arrive and give the lord's work order to the men (4 are overwritten by an attack or get-men order first).
  (S "`$6522` — the commander AI", S "The AI as modern pseudocode", S "What an AI invention order does")
- **Deterministic.** The AI's "random" numbers are low bits of the tick counter, and a land's map
  is a pure function of its seed, so a run replays exactly from a snapshot. (S "RNG and determinism")
- **The world is drawn as a heightmap.** A software rasteriser projects the grid with perspective,
  fills two triangles per cell far to near, and draws each cell's sprites straight after it, so
  walk order is depth order. A triangle has no colour of its own: its colour byte (colour plane A for one
  half of a cell, colour plane B for the other, both slope shades baked from the altitude plane at world build, water plus a 0-3 tick, or a fixed dark slot for
  back-facing triangles) picks one of the 16 x 16 stipple tiles (pattern-table slots `0x00`-`0x40`), the scanline and screen column
  pick the pixel, and the byte is a slope shade (lighter or darker with the cell's tilt) so the tiles are dither ramps. Seasons rewrite 18 of
  the tiles pixel by pixel; rain and snow are drawn on top.
  (G "The pattern fill", P 4 "Seasons", S "What `$1abaa` actually is")

### Limits that became features

- **A slow, coarse tick.** The whole simulation and both renderers run in one loop that takes
  about 19 frames (2.6 Hz measured in the emulator); orders land seconds apart, which gives the
  game its deliberate pace. (S "Measured cadence")
- **No pathfinding.** A lead steps straight at its target and probes a few cells ahead, turning
  around what blocks it. (A "What each entity decides per tick")
- **Fixed tables:** 511 objects, five sides (side 0 neutral), 400 settlements, one order record
  per side holding its six captains' groups as parallel arrays. (A "The object record", E 3, S "`$51538` — group-order table")
- **The season clock is also a gate.** The season rotation switches the per-settlement heartbeat on
  and off, so upkeep and defections run in bursts. (S "What `$1abaa` actually is", E 6)

### Bugs and accidents a new design should drop

- The captain panel's loyalty line is a constant: its selector loads index 3 unconditionally, so it always reads "trusting" whatever the lord's loyalty is (the house panel does print it). The group aggression rank the panel prints (group word 72, 0 PowerMonger to 7 Wimp; the posture is the other half of that line and is read) is read by nothing but the panel (a whole-image scan, and 0 differing RAM bytes over 50M steps with all 30 words poked; the land build's block clear `$10768` also writes it). (S "The game's own text", S "`$51538` — group-order table")
- An order for a subordinate captain compares the sender's cell with record 0 (all zero) instead of the target lead's cell, so it always goes by pigeon; a pigeon shot down by an arrow keeps its record until its target group dissolves, and the pool of 47 order pigeons has no other reclaim. (A "Arrows and carrier pigeons")
- The arrow's damage test (`subi.b #$52`, then `bgt`) misreads a health byte of `$80` or more as already dead; play keeps health below `$80`. The type-`$12` area effect of the arrow loop has no producer. (A "Arrows and carrier pigeons")
- The starting job pick bounds the farmer's search row with a stale register (the cell index the failed fisherman search left behind), so a man whose fisherman draw fails can never become a
  farmer and ends a merchant: 222 of the 281 merchants in eight builds, and every one of 1234 failed farmer searches (the briefing-preview roll; the Play Random Land roll: 448 of 558 and 2473 of 2473). (E 5a)
- The relation bytes are misaddressed three ways: the update reads one byte and writes the next,
  reading negatives as large positives; the envoy check reads the attitude toward the wrong side;
  and the targeting weight reads outside the relation table, so relations never affect who the AI
  attacks. (S "Diplomacy")
- Breaking an alliance with the player loses the two −8 relation changes: a message call clobbers
  a register, so they are written outside the table. (S "Diplomacy")
- The AI sets posture 4 (passive) on every group it sends to attack, and posture 4 pins every
  kill that group inflicts to a rout (unless the victim's flag bit 5 is set): AI attackers
  rout men rather than kill them. The player's army at posture 3 rolls: 5 kills and 5 routs in the
  mission-1 win; posture is not "discipline", and mission 1 does kill.
  (S "The commander AI `$6522`" step 4, S "Combat" 0, S "What each order does", A "Natural runs on later lands")
- Catapult and cannon are goods that never become weapons: no code stores their tier on a unit, so
  their projectile type is unreachable. (E 4)
- The group dissolve reads the command slot at `3 × side` instead of `6 × side` (a bug, inferred), and the revolt
  chain passes the side in the wrong register; both are transcribed as the code does them. (A
  "The group dissolve", A "The revolt chain")
- The camp wait compares the group's stamp plus 20 with the 16-bit sim clock as signed words (`$65a0`..`$65a6`, a single use of the clock), so once the clock passes 32768 a camped group with an old stamp
  waits for the clock to wrap, an estimated 34,800 ticks: decisions fell from about 1,500 and 1,840 per 250M steps to 0 in two lands, at 4.5 to 5.75G steps. Isolated by clock pokes (only the clock changed: the stall starts at 32768 and ends at `stamp + 20`); probably unintentional (inferred); a run
  rarely lasts that long. (S "Natural coverage", the signed-clock stall)
- An attack on a lord whose cell holds only the attacker's own records is re-issued every tick and never starts (`$4a7a` returns without `$4b80`): 9,660 and 13,594 attack decisions in 2G steps on two
  lands. (S "Natural coverage", the livelock bullet)
- The AI's follow-up table `$67d0` is live (34 natural issues, food to men to equipment to invention);
  the invention order reaches its arrival `$5fa0` in 26 of 30 natural cases on the Play Random Land roll, and the chain ends there.
  (S "The follow-up table", S "What an AI invention order does")
- The wear-removal path never fired in 800M steps on four lands (inferred: unreachable in
  practice). (S "Open threads")
- Starting a new conquest clears only 62 of the 195 conquered-land flags (the clear loop's count is `move.w #$c3,D0` then `neg.b D0`, which leaves `$3d`): the flags of lands 62 and up survive.
  Live: 240 bytes poked to 1, then YES left exactly the first 62 zero. (S "The campaign", the panel `$18` row)

## Drive recipe: cold boot to the isometric view ([cr Replicants])

```
./run.ps1 -NoBuild repl 1 -DiskA "<replicants>.st"     # -DiskA on EVERY rrepl/resume (mount is not snapshotted)
  s 15000000 ; kbd 1c ; s 55000000                     # RETURN -> "Powermonger" title + scrolling credits
  kbd 39 ; s 80000000                                  # SPACE (RETURN ignored here) -> "What Is Thy Name" name entry
  kbd 20 <settle ~800k> a0 <settle> … ; kbd 1c 9c      # type a name SLOWLY (handler drops back-to-back bytes), RETURN
                                                        #   -> "Welcome to the World of PowerMonger" option menu
  mouse move onto ~(155,85) in 320-space ; mouse down l ; mouse up l   # START NEW CONQUEST -> campaign world map
  mouse move onto ~(18,18) in 320-space  ; mouse down l ; mouse up l   # top-left scroll icon -> "Between Pages 1-5" briefing
  w 2df92 001400b1 ; w 2df8e 001400b1 ; w 2df96 00010001 ; s 12000000  # left OK button (cursor 20,177) -> ISOMETRIC VIEW
```

The final `w` pokes stand in for a click delivered through PM's mouse state
machine; `mouse move` / `mouse down l` to screen (20,177) works too. PM screen
is direct-to-shifter, `scratchpad/pmshot.sh <snap> <png>` reads `$FFFF8201/8203`
(`$024400` menus, `$01c700` iso view), not `_v_bas_ad $44E`.

Empire build: `s 8000000` / `kbd 39 b9` (SPACE) / `s 45000000` → title, then the
"Pondering over the map…" narrative screen. Not driven further.

---

## Bug 1: FDC self-test hang

**Symptom.** Booted with the Replicants disk, TOS printed "TDT ALTAIR ANTI VIRUS V3.00:
CHECK OK:" forever.

**Cause** (traced against a real Hatari `cpu_disasm`). After the primary autoboot, TOS runs an
**FDC self-test loop at ROM `$fc04a8`**: 8 iterations, each firing one raw WD1772 command and
polling `$fc0580: btst #5,$fffffa01 / beq` with a `_hz_200 + 10` (~50 ms) deadline. It is
a *presence* check: on real hardware those bare commands are still running when
the deadline expires, every poll times out, and the loop exits after 8 tries
without ever running its `$fc04cc: jsr (A0)`.

The emulator had **MFP GPIP bit 5 (FDC IRQ, active-low) hardwired to 0** ("a command
is always complete"), so every poll succeeded instantly and `$fc04cc: jsr (A0)`
re-executed the still-valid `$1234` boot sector in `_dskbufp` every iteration.
The boot sector's own `move.w #$ff,d7` clobbered the ROM loop's
`add.b #$20,d7 / bne` counter, so the loop never terminated. (A plain TOS boot
survives because its buffer does not checksum to `$1234`; this crack's does.)

**Fix** (`MMU` `fdcIrq` / `FdcTick`). GPIP bit 5 is idle-high and INTRQ is re-raised on a
coarse bucketed delay after a command: immediate for a Read/Write Sector that
moved data, ~4000 steps for Seek/Step, ~40000+ for Restore, a failed search or Read
Address. The self-test's first polled command is a Restore, so it times out and
the loop exits. The diskless-boot `checkpoint.txt` was re-baselined.
## Bugs 2 and 3: the depacker derail

**Symptom.** Past the cracktro, both cracks load ~1 MB of game data and hand off to an **ICE
depacker** ("Ice!" magic `$49636521`, plain-68000 at `$70880` in Replicants).
Depacking completes cleanly; execution then derailed (Replicants to `PC=$20`,
Empire to `$5a6`).

**Cause of Bug 2** (traced instruction by instruction from the depacker's `rts`). The cracktro's VBL
handler at `$660` ends with `move.l #$00078000,$ffff8260.w`. That long write's
low word lands on **`$ff8262`/`$ff8263`**. The emulator's video-register region
ended at `$ff8260`, so the second word hit the generic `raise (BusError …)`
fall-through, which vectored through a cracktro table that does not handle bus
errors: garbage PC, then a vector-table-as-code crash. On a plain ST the shifter is
selected for the whole `$ff8200`-`$ff827f` page but decodes no register in
`$ff8262`-`$ff827f`; Hatari's `IoMemTable_ST` has `{ 0xff8262, 30, IoMem_VoidRead,
IoMem_VoidWrite }`, "No bus errors here".

**Fix 2** (`MMU.fs`). `videoDisplayRegisterEnd` moves from `$ff8260` to `$ff8261`
(`Video_ResShifter` is real), and a new `ShifterVoid` region covers `$ff8262`-`$ff827f`
(reads return open-bus `$ff`, writes are dropped, no bus error). `videoDisplayRegisterMemory`
is unchanged (98 bytes); the snapshot format and diskless boot are untouched.

**Cause of Bug 3.** With the bus error gone, the depacked code reaches `suba.l (d16,PC),A5`.
The hand-coded SUBA.L handler covered only `Dn`/`An`/`#imm.L`/`(xxx).L`.

**Fix 3** (`68k.fs` `DecodeBucket9`). The `match eamode` block is replaced by the shared
EA decoder (`x.ResolveEa` / `x.ReadEa`). Selftest gains about 3000 passes; the wrong-answer lane
stays 0.
## Bug 4: the isometric-view setup code needs real 68000 DIVU/DIVS

**Symptom.** Clicking the world-map scroll icon loads the mission-setup overlay above `$1050`,
which does projection with `DIVU` / `DIVS`. Two `failwith`s in `68k.fs`
`DecodeBucket8` aborted it.

**Quotient overflow.** On overflow the 68000 sets **V=1, C=0** and leaves **N, Z, X and the
destination untouched**, PC advancing (no trap). This is verified against the SingleStepTests
68000 vectors: every overflow vector there touches only V and C (Hatari's `setdivuflags` forces
`N=1/Z=0`, a different chip revision). The DIVS fit-check runs in `int64` so
`Int32.MinValue / -1` is caught as overflow, not a CLR exception.

**Divide by zero.** It now traps to **vector 5** with the standard group-2 frame via
`EnterVector`, the same shape as CHK/TRAPV. The suite has no zero-divisor vectors, so selftest
cannot check the trap path.

**Result.** Selftest: DIVU 4963, DIVS 4992, **0 wrong / 0 unimpl** for both. The 30M-step
diskless boot is byte-identical.
## Bug 5: Timer A never fired; zero divide re-executed the DIVU

Two emulator regressions stopped every world build from `pm67_ok_pre`.

**Timer A.**

- Symptom: `$13b9a` ends in `$1ae40: tst.b $2c993 / bne $1ae40`, waiting for
  the sample player's busy flag, and never returned. The MFP Timer A handler (`$134` to `$1af32`)
  clears the flag (`sf $2c993` at `$1af72`).
- Cause: TACR writes are stored in `MMU.fs`'s `tacr` field, but `RaiseTimerA` read TACR from
  `mfpRegisters`, which stayed 0, so Timer A never raised.
- Fix: `RaiseTimerA` reads `tacr`, as `RaiseTimerB` reads `tbcr`.

**Zero divide.**

- Symptom: land 60 ("Driving a later land") hits `divu D0,D1` with `D0 = 0` at `$164d6`
  within 20M steps of its build, then re-runs the divide forever.
- Cause: PM's vector-5 handler (`$14e4`) is a bare `rte`, so it relies on the 68000 stacking
  the address of the *next* instruction. The emulator's DIVU/DIVS stacked the instruction's own
  address, so the `rte` re-ran the divide.
- Fix: DIVU/DIVS stack `PC + 2 + extension bytes`, which is what Hatari's 68000 path does
  (`gencpu.c` i_DIVU: `incpc` before `exception_cpu(5)`; `newcpu.c`
  `Exception_normal` stacks `m68k_getpc()`; `exception_oldpc` applies only to
  the generic 68020+ tables). The one SingleStepTests zero-divisor vector
  (`80ef`) expects the opcode address; it is skipped for its flags.

**Result.** Selftest: 1000051 pass, 0 wrong, 9 skip. `verify 5000000` passes.
## Driving a later land

**The briefing preview roll.** The preview routine (`$b2dc`) first saves the block
`$580a0..$58367` to `$584c4`, then rolls one of 144 preview lands from entropy (video counter,
timers, RNG): `$580a0 = k*$b + $3fb`, `$5809c = k*$96 + $672` (non-zero), `k = 0..$8f`. It
builds the land through `$b394` and `$10d1e` (branch C of `strategy.md` "The world build,
proven"); that build is discarded. The briefing's "Between Pages" numbers come from
`$5809c` (`$b472`), so a larger `k` gets later pages.

**The OK button.** `$b860` clears `$5809c` (`$b85a`) and restores the saved block over
`$580a0..$58367`, which includes the world parameters at `$58146`. For mission 1 that block
holds seed long `$580a0 = 0` and parameters `1e19 0750 0008 0023 0031 0004`, so `$13b9a`
skips `$10d1e` and, because `$58148 = $0750 >= $100`, builds procedurally
(`$ffa6`/`$2266`/`$ac20`) from those stored parameters.

**Building preview land `k` for real.** Break at `$13b9a` after the OK click and poke both
words, so `$10d1e` runs with the size override:

```
./run.ps1 -NoBuild rrepl scratchpad/pm67_ok_pre.snap -DiskA scratchpad/powermonger.st
  w 2df92 001400b1 ; w 2df8e 001400b1 ; w 2df96 00010001   # briefing OK
  u 13b9a 80000000
  w 580a0 <k*$b+$3fb as a long> ; w 5809c <k*$96+$672>0000
  u 13ce6 80000000 ; s 30000000 ; u f898 5000000 ; snap <out>
```

Mount the Replicants image (`scratchpad/powermonger.st`), as in the drive recipe.

**Season.** `$57fd0` (the season) is `(byte[$58146] & 3) * 2`, read at `$13bdc`
*before* `$10d1e` refills `$58146`. A poked land therefore keeps the season of the stored
block (4 here) unless that byte is also poked at `$13b9a`: `w 58146 1c190750` builds winter
(season word 0), `1d..` spring, `1f..` autumn.

**Script and results.** `reversing/powermonger/py/build_land.sh <k> [steps] [season]` does all
of this and prints the land's render-record census (`census.py`). The unpoked control
reproduces mission 1's terrain byte for byte. `k` = 20/60/100/143 give 44-69 settlement
records (mission 1: 11) and non-zero `$3f86c` altitudes on 37-72 % of cells (mission 1:
10 %). `scratchpad/pm120/k60_iso.snap` is land 60 (`$580a0 = $68f`), settled at the frame
driver.

#### Which builds reach `$10d1e` in play

**The preview poke is branch C.** It leaves `$5809c` non-zero, which is the preview's
setting, so the lands of `build_land.sh` and `cap_land.sh` are branch C.

**Campaign land picks do not build.** A campaign land pick copies a table block and `$13ec6`
clears `$580a0`, so `$13b9a` skips `$10d1e` (live: 0 hits for `$10d1e`, 927 for `$4788`).

**Play Random Land is branch A.** It is the only path that reaches `$10d1e` outside the
preview (`$13e8e` to `$13ece`, seed = video counter + mouse + RNG OR `$71010101`), and it does
so with `$5809c == 0`. Branch A applies when no side is in command state 6 or 8: the sides'
sites are rebalanced by weight, `$58148` is rolled instead of overridden, and `$4788` makes
two tries per tree cell instead of one, so these lands carry more trees.

Live trace from `scratchpad/pm123/win/m1_win.snap`, click (160,120): `$13e8e` at step
264686, `$13ece` at 264689, `$13b9a` at 265397, `$10d1e` at 330184 with `$5809c = 0`,
`$580a0 = $f9abdbf1`, side states 2, 0, 0, 0; `$b85a` and `$b2dc` had 0 hits. The real
anchor is `scratchpad/pm142/rand1.snap`.

**Reproducing the Play Random Land roll.** `PAGES0=1` on `build_land.sh` / `cap_land.sh`
pokes `$5809c = 0` instead, which gives that roll: land 60 has 304 tree records (byte6 4)
against 120 with the preview poke, and land 25 has 281 against 154. `py/gate_pop.py` passes
41760/41760 over 8 such builds (`PM_POP_CORPUS=scratchpad/pm142/corpus_2984a`).
`py/worldbuild/gate_build.py` runs both settings (`strategy.md` "The world build, proven").

#### Looking at a record in the game

What 37 lands of each roll draw, and what the preview-roll ones do when left to run, is in
`port/SPEC.md` §6 ("Every category") and `ai.md` ("Natural runs on later lands"). To look at a
record in the game, poke the camera centre and let a frame render:
`w 4bb3a <x><y>` (two words), `s 2000000`, `u f898` (`reversing/powermonger/py/capture.sh`
snapshots N frames in a row from there). The REPL's `hits <steps> <addr>...`
counts how often each address runs over a stretch, with the first and last step.
## Ending a land and driving the campaign

How a land is won or lost (`$d2c8`, command `$2e`), the 195-land conquest map
(`$3f2a0`, picker `$1120e`), the per-land parameter table (`$3f428`, mission 1
= entry 0) and the manual-lookup protection check are in `strategy.md`
("How a land ends", "The campaign"). The drives, from
`scratchpad/pm121/run/k25_s4.snap` (all in `scratchpad/pm122/end/`):

```
w 5801c 012e0000        # the retire button's write: command $2e in the player's slot
bp d2c8 2000000         # verdict; poke w 57fcc 03b70004 here (ratio 4) for the win branch
s 50000000              # defeat/victory screen, then the main menu ($13de8)
# Continue Conquest: pointer (0,0) -> mouse move 100 100 ; mouse move 60 3 ; click
# land 1 on the map:    mouse move -120 -83 ; click   (click = down / move 0 0 / s 300000 / up / move 0 0)
```

The pointer's live position is `word[$1c492]` / `word[$1c494]`.

## PM's mouse dialog state machine

PM's own IKBD ISR is at `$18be` (vector `$46`). It parses the `$F7`
absolute-position reply (the emulator's `$0D` interrogation answer):

| RAM addr | holds |
|----------|-------|
| `$1c48f` | `$F7` button-edge byte (`%0000dcba`: c=left-down, d=left-up) |
| `$2df92` / `$2df94` | live cursor X / Y (words) |
| `$2df8e` | cursor position **latched at the click** (long) |
| `$2df96` | **left-click pending** flag, set 1 on left-down, cleared by whichever dialog consumes the click |
| `$2df9c` / `$2df98` / `$2df9e` | left level / right pending / right level |

VBL handler `$1270` dispatches on `$1c48f` through a jump table at `$12ac`
(index = `button_byte * 2`): button `4` (left-down) → `$1330`, which sets
`$2df96=1` and latches `$2df8e`.

### The briefing dialog hit-test (`$7298`), decoded

`$7298` runs when `$2df96 != 0`. It loads D0=X, D1=Y from the latched click and
walks the four 8-byte entries of the dialog descriptor at `$7a36`:

| entry word | meaning |
|------------|---------|
| word 0 (`D2`) | offset from `$7a36` to this panel's `{widthCells:b, heightCells:b}` pair + its cell grid; `0` = inactive |
| word 1 (`D3`) | packed rect origin: `left = ((D3>>8) & $1f) * 16`, `top = D3 & $ff` |

The briefing has one active entry (`$7a36` = `0176 0000 …`): panel at screen
`(0,0)`, `$7a36+$176` = `{06, 20}`, so a **24×32 grid of 4×6-pixel cells** over
screen x 0-95, y 0-191. A hit computes `col = (X-left) >> 2`, `row = (Y-top) / 6`,
fetches `grid[row*24 + col]`:

- cell `>= $20` (text / button glyphs `$80`-`$87`) → handler `$7658`
- cell `$01`-`$1f` → jump table `$735e` (`$01`-`$0b` border → `$739e`
  "click-anywhere confirm"; `$10`/`$11` → `$73d4`/`$740e` population digit up/down)

```
r28 y168:  . .  80 81 81 82  . . .  10 10 10 10  . . .  80 81 81 82  . .   ($10 = population up-arrows)
r29 y174:  . .  83 4f 4b 84  . . .  30 30 30 30  . . .  83 4f 4b 84  . .   ("OK" text, "0000" digits)
r30 y180:  . .  85 86 86 87  . . .  11 11 11 11  . . .  85 86 86 87  . .   ($11 = population down-arrows)
```

`$7658` re-walks from the clicked cell to the enclosing `$80` cell, gets its grid
offset in D3 (left OK = `$2a3`, right OK = `$2b1`), plays a click sound, then
jumps through a **per-dialog** table: `D0 = word[$76fa + $7a3c]`,
`jmp $76fe + D0`. `$7a3c` is the dialog id; the briefing's is `$0a`, and
`word[$7704] = $0186` → `jmp $7884`:

```
$7884  cmpi.w #$2a3,D3 ; beq $7890     ; left OK
$788a  cmpi.w #$2b1,D3 ; bne $7896     ; right OK
$7890  jsr $b814
```

**Dialog buttons by id.** After the click sound, `$7658` jumps through the word table at `$76fa + id` (ids below 4 are ignored; `D3` is the clicked button's grid offset, row * width + column of its `$80` corner). A grid with a text-entry field (cell `$89`) is also handled at the top of `$7658` (`$d03e`, `$d038..$d046`). All rows below are code read except id `$18`, which was clicked live (`py/clicks_ui/dlg_click.sh`, `pm142/yes_dlg.snap`; strategy.md "Panel slots and dialogs").

| id | handler | buttons (`D3`) and effect |
|----|---------|---------------------------|
| `$04` | `$7716` | any button: if byte 4 of the order record `$58034` is 2, `bsr $aeac` |
| `$06` | `$7740` | `$17` merges `$3f768` into `$3f2a0` after `$12726`/`$e29c`; with `$14e4e = $2c`: `$47` copies `$3f2a0` to `$3f768` and calls `$e288`, `$77` calls `$1ba72` |
| `$08` | `$77c2` | seven command buttons post order codes into byte 1 of `$58034`: `$11` `$2e`, `$41` `$28`, `$a1` `$2c`, `$d1` `$30` (with `$2df84`), `$101` `$24`; `$71` redraws via `$13ce8`/`$12ce0`; `$131` calls `$d194` |
| `$0a` | `$7884` | the briefing: OK at `$2a3`/`$2b1` runs `$b814` (the protection check below) |
| `$0c` | `$789a` | `$1ba` clears `$d03e`, closes the dialog and sets `$2df6c := 1`; `$1d6` clears `$d03e` and closes |
| `$0e` | `$78d2` | `$92 $da $122 $16a` set `$2df6e` to 2, 4, 6, 8 and close |
| `$10` | `$7928` | `$e2` sets `$2df6c := 0`, `$f6` sets `$2df6c := 1`, both close |
| `$12` | `$7958` | `$68` closes |
| `$18` | `$796e` | YES `$7a` zeroes the conquered-lands record `$3f2a0` (`$c4` bytes) and `$11420`; NO `$8a` sets `$2df6c := 0`; both close. Live: YES leaves `$3f2a0[0]` 0 (was 1); after NO the menu loop opens the id-`$0e` dialog |
| `$1a` | `$79ae` | `$146` and `$162` post orders `$2a` / `$32` for the current captain (`$51538 + $5809e`) into `$58034` |

Ids `$14` and `$16` have no handler. Openers set the id: `$9044` (2, captain), `$b45c` (`$0a`), `$bb4a` (`$0c`), the rest through `$affe`.

`$b814` parses the population digit string, then **unconditionally** (the crack
nopped the "must enter a value" check at `$b842`: `moveq #0,D0 / nop / bne`)
writes `population + $2c` to `$14e4e` (the gate `$739e` and `$7774` test), copies
the game-state seed table `$584c4` → `$580a0`, `jsr $13b9a` (world generation /
`$10d1e` load path), and `move.w #$1,$1c48a` to advance the state machine. One
frame later PM composites the isometric view.

**Traps when driving a click.** A "no click accepted" result comes from clicking outside the
`(0,0)`-anchored grid, or from reading the per-dialog OK table with the base four bytes low, so
that `$7a3c=$0a` looks as if it routes to a handler that ignores OK.
## What runs, and what the analysis established

This section is the overview of current understanding by topic. Each paragraph states the
result as it stands, names the gate that proves it (script, match count) and points at the
topic-doc section that holds the detail. Evidence levels (Proven, Corroborated, Observed,
Hypothesis) are defined in `ai.md` "Evidence taxonomy"; a gate is a differential test of a
reconstruction against the real 68000 through `callcap` (last subsection). Scripts are indexed
in `py/README.md`.

### Boot path

The Replicants build runs from its ALTAIR ANTI VIRUS boot sector through the FDC self-test
(Bug 1 above), `Pexec`s the game, shows the cracktro key-wait (`cracktro.png`), loads about 1 MB
and ICE-depacks it (Bugs 2 and 3), and reaches the title with its scrolling credits
(`title.png`, `credits.png`). From there the drive recipe above goes through name entry
(`name_entry.png`), the option menu (`menu.png`), the campaign world map (`world_map.png`) and
the "Between Pages 1-5" briefing (`briefing.png`) into the isometric battle view
(`iso_view.png`); the world build behind the briefing's OK button needed Bugs 4 and 5 fixed.
The Empire build reaches the title and the "Pondering over the map..." narrative screen
(`empire_intro.png`) and has not been driven further. Any of the 144 preview lands can be built
from the briefing snapshot (`py/build_land.sh`, "Driving a later land", which also says how
Play Random Land's builds differ), and the campaign
(195 lands) can be played through the real UI, including both ends of a land
("Ending a land and driving the campaign"; `py/drive_win.sh` wins mission 1 with real clicks).

### Input and dialogs

PM's own IKBD handler `$18be` (vector `$118`) parses the `$F7` absolute-mouse packet into
`$1c48f` / `$2df92` / `$2df94` and handles scancodes below `$f6` at `$1962` into the key array
`$2de6c`; the shift keys only set the flag `$2df8a`. The per-frame camera loop `$13762` gates
its rotate, horizon, eye and keypad-zoom rows on array slot 54, the right-shift slot that
`$18be` never writes, so those rows cannot be reached from the keyboard (the REPL pokes the
gate and the key together; recipe and effects in `graphics.md` "In-game camera control").
Rotation re-projects the whole terrain (`iso_rotated.png`).

The arrow keys are a separate, ungated block `$13824` that moves the camera cell `$4bb3a` / `$4bb3c`
by one per held tick (live: holding `$4b` for 500,000 steps moves X `$28` to `$26`). Keypad zoom
changes `$ff9c` but never calls the geometry rebuild `$fe04`, so it does nothing; the real zoom
path is the mouse command through `$13f60` into `$fe04` (7 levels), and both extremes are
profiled in `graphics.md` "Zoom comparison" (`iso_zoom_in.png`, `iso_zoom_out.png`).

The mouse dialog protocol, the briefing hit
test and the OK path are decoded in "PM's mouse dialog state machine" above; the icon floor,
the text panels and the info panels are in `strategy.md` "The player's commands".

### The simulation: entities, scheduler, combat

The simulation has no per-unit-type AI. Every man, boat, animal, projectile and pending order
is a 50-byte object record in the array at `$51b66` (511 slots), each with a mode opcode in
byte 31; the iterator `$14b62` walks the array once per tick and jumps through the 75-entry
mode table `$14bb4`. Records are bucketed per grid cell in `$47970`, each side's six captains'
groups live in the `$51538` group-order table, lords in `$4e514`, settlements in `$4f916`.
Target selection is local: bucket-proximity contact, adjacent-settlement siege, and a
group-order destination cell (`ai.md` "The iterator", "The object record", "Where target
selection happens").

**Tick.** The tick body is `$13000`: about 13 ticks per 250 VBLs (roughly 2.6 Hz, compute-bound in the
emulator), with `$6522` / `$d322` / `$3e06` near the top and `$14b62` / `$6a3a` near the
bottom; only the renderers sit behind the present-rate divider `$57ff0` / `$57fee`
(`strategy.md` "Where it runs", "Measured cadence").

**Combat.** There is no battle resolver. Combat is
the melee grind of mode `$32` (`$1533c`): the attacker takes 1 to 3 off the target's health
(byte 45, the value the captain panel prints as "Very Sickly" .. "Very Strong"; weapon
grades 0, 2, 4 give 1, 2, 3 and grade 6 and above gives 1, the gate's `moveq #0` arm); at
zero `$5590` rolls kill or rout from the attacking group's posture (`$30fe`: 2 always kills,
4 always routs, 3 rolls on the tick parity; an encircled loser is always killed).

The AI stamps
posture 4 on every group it sends to attack, so AI attackers rout (ten routs and zero kills in a
re-armed 276-tick mission-1 fight); the player's posture 3 army in the mission-1 win made 5 kills
and 5 routs. `$5778` starts the fight (it puts a camp out and calls `$4bc8`, group to Fighting), not
casualties; arrows (`$596a`) and the slow attrition path (`$5c80` to `$5bd2`, never fired in
800M later-land steps) are the other channels (`strategy.md` "Combat", `ai.md` "the combat
path", "Arrows and carrier pigeons").

**Determinism and seasons.** The AI is deterministic: its "random" numbers are low bits of the tick counter `$57fec`
(counts `$1abaa` calls, 0..512 per season step), and `$57ff6` is the 13-bit LCG that orders
the pixels of the season tileset dissolve, not an AI RNG; a land's map is a pure function of
its seed (`strategy.md` "RNG and determinism"). `$1abaa` is the seasons and weather routine,
not an economy engine; it rotates the season word `$57fd0` through {0, 2, 4, 6} once per full
cycle of its LCG (512 calls; 118.4M steps in mission 1, 85.7M on a Play Random Land), which gates the settlement
heartbeat (`strategy.md` "What `$1abaa` actually is").

### The AI and the player's orders

The commander `$6522` decides, `$58016` carries the command buffer, `$6a3a` executes and `$4b80`
stamps the group lead into mode `$10` (march).

The autonomous decision is "march at the nearest
enemy lord if the army has the food for the trip" (the group's own food, not a force-scaled
budget), plus the follow-up table `$6762` / `$67d0` that chains food, men, equipment and
invention orders after a finished state; there is no economy or build planning. The follow-up
table is live (34 natural issues); `$6808` / `$68aa` are dead. The per-side force totals
`$57fba` (from `$d322` and `$3e06`) reduce through `$d23a` to the 0..4 ratio `$57fce`
(original `_win_state`, drawn as the balance `scale_da` by `$16bb8`, tested `== 4` by the
end-of-land verdict `$d2c8`; the AI never reads it).

Mission 1's enemy captain issues no
autonomous order in about 1000 traced ticks (250M steps); the `$6564` path was confirmed by
forcing a command slot ready, and later lands run it by themselves (`strategy.md` "What
actually fired", `ai.md` "Natural runs on later lands").

**Proofs against the real 68000.** All are differential tests of `tools/pm_fsm_ref.py`-style
reconstructions (corpora, scripts and the branch lists are in the cited sections):

- Entity FSM core (`ai.md` "the dwell/upkeep core", "the movement modes", "the combat path",
  "the settlement heartbeat"): 675/675 tracked bytes over 22 states (prologue, modes `$12`,
  `$68`, `$8a`, `$5c80`, the epilogue), 1335/1335 over 32 (movement modes `$06`, `$08`, `$0e`,
  `$10` and the leaves `$164bc`, `$14262`, `$12d56`), 413/413 over 48 (melee `$1533c`,
  `$56a6`, `$5590`, `$30fe`), settlement heartbeat `$157e6` 99/99 over 27 natural states
  (12 branch families) and 85/85 over 25 synthesised states.
- Regroup `$3c08` 71/71 (22 states) and its flag-bit-4 group teardown `$37c2` / `$1d70` /
  `$1b8c` / `$17a46` 1847/1847 (13 states); set up the fight `$4bc8` 51/51 and 20/20;
  dying-entity path `$1623c` 275/275 (23 states, `py/diff_1623c.py`); group dissolve `$2776`
  4119/4119 (28 states, `py/diff_2776.py`); lord's work order `$5cde` 768/768 plus 85/85
  returns (47 states, `py/diff_5cde.py`); revolt chain `$550e` to `$5c2c` to `$25d6` 1778/1778
  (49 states, all 27 natural `$550e` calls on four lands, `py/diff_revolt.py`); conquest target
  pick `$4f68` 1804/1804 (192 states, 170 natural, `py/diff_4f68.py`).
- Forest animator `$4342`: 8 of 9 branches proven; the arrival/unlink branch stays
  Corroborated (`ai.md` "the forest animator").
- Shepherd cycle 1043/1043 (198 states, `py/gate_shepherd.py`; 1010/1010 over 215 on the Play Random Land roll), animals and pigeons 45094/45094
  (55 snapshots, `py/gate_animals.py`; 49178/49178 over 60 on that roll), arrows `$596a` 4210/4210 (456 states,
  `py/gate_proj.py`), order pigeon `$4562` 1567/1567 (125 states, `py/gate_pigeon_send.py`);
  the `$15000` page of mode bodies 18452/18452 over 1889 states (`py/fsm15/gate_fsm15.py`).
- Commander AI `$6522` with its helpers: 323/323 natural and 280/280 synthetic states
  (3975/3975 bytes), leaves 180/180 and 160/160 (`py/cmdai/gate_cmdai.py`); order executor
  `$6a3a` / `$6ac6` / `$6b38` 288 natural states (157/157 bytes) and 80/80 synthetic
  (2393/2393) (`py/cmdai/gate_exec.py`); the order senders and arrival executors 61143/61143
  bytes over 2273 states, 72 natural (`py/orders/gate_orders.py`) (`strategy.md` "Proof of the
  commander AI", "The order senders and arrival executors, proven").

**Driven live** through the real UI and the REPL (`strategy.md`): mission 1 won and lost both ways
(retire, natural defeat), every player order but `$04` and a real `$0e` exercised at least
once, diplomacy's envoy, tribute and break traced end to end, and four lands' natural `$6522` /
`$661a` decisions captured over 200M steps each and matched against the disassembly. How a
land ends, the 195-land campaign and its manual-lookup protection check are in `strategy.md`
"How a land ends" and "The campaign".

### The economy

**Food and men.** PM has no single economy tick. A lord's food (`pm_leader.food`, `$4e514` +6) and men at home
(`troops_field`, +8) are a ledger that no counter grows: food fills when farmers come
home from their field and when fishermen deliver a catch, and empties when an army takes food, gatherers work
(`$603e`) and the settlement pulse runs; men are only redistributed, captured or dismissed,
and the one path that raises the live count without a capture is a pigeon landing that
revives a dead man's record (`$42be`).

Every writer was enumerated from a watch of about 1B
steps, plus the player's own order paths (`economy.md` 1, 6); `troops_field` equals the live
men of each lord by home settlement on 416 lord instances over 33 snapshots (378 exact, all
within 1, `py/troops_audit.py`), and rule D matches 2280 of 2280 (`py/troops_rule.py`).

**Goods.** The goods are a separate ledger: eight counters per lord (`pm_leader.goods[0..7]`, `$4e514` +24,
one per item type), credited by men felling the trees of the `$4d252` tree array (the forest
operations `$57f68`, the markers `$4c5f4`, the animator `$4342`, the payoff `$60dc`), moved
between lords by merchants (arrival handlers `$159de` / `$159a4`; the merchant start `$15ad2` never advances its
trip table, so the goods come from the record after the home lord) and spent by the army-supply subsystem (`$6352` / `$638c`), which
upgrades a unit's weapon tier (byte 44) or tool tier (byte 33) to the best item in stock.
That upgrade is the whole of "invention": no research timer exists (`economy.md` 2, 2a to 2c,
4). The equipment exchange `$160f8` / `$16892` and its stale-register credit bug are gated
385/385 over 201 states (`py/gate_equip.py`, the F# `Equipment.fs` against 202 cases,
`py/equip_check.fsx`).

**Settlements.** Settlements are 18-byte records in `$4f916` (at most 400, chained per nation, built by
`$2fc0`). Their heartbeat is entity mode `$7c` (`$157e6`), switched on by the season word
(`$57fd0 == 0`), so upkeep and defections run in bursts. Its loyalty accumulator
(`pm_leader` +14) moves only on the first pulse after a marker parks (`$ff9d` to `$ff9c`),
and at 600 the lord and his settlements defect through `$550e`; the park write is not
something the player triggers, and 11 of the 27 natural defections came from this cycle (the
other 16 from the conquest arm of mode `$2c`).

The village population `$2984` gives every
settlement two men and a job from `$2a98`; a stale register in the farmer search decides the
mix (gates `py/gate_jobs.py` 3310/3310 over 146 states, `py/gate_pop.py` 29860/29860 over
1026 men on eight lands and 41760/41760 over eight Play Random Land builds; `economy.md` 5a). The `$163ea` bucket-relink writes that land in
the `$4f916` region for some dead object slots are a corrupt object forward-link, benign
(`economy.md` 3b).

The mission setup `$13b9a` (`$10d1e`, `$2266`, `$ac20`, `$4672`, `$2984`,
`$238c`) is gated in `strategy.md` "The world build, proven" (`py/worldbuild/gate_build.py`:
`$10d1e` 22501/22501, `$4672` / `$4788` 114947/114947, `$238c` 44963/44963, `$2eac`
14631/14631, `$2906` 262/262, `$1073c` 24433/24433, `$1b2a` 996/996, `$1cc4` 4241/4241).

### Rendering

The isometric view is a software heightmap rasteriser. `$fec6` (the entry, which loads
`A3 = $13f8a` and falls into the body at `$fecc`) projects the grid corners with a rotation
by `yaw * 1.40625` degrees and a perspective divide (`EYE = 320`, `HORIZON = 130`), only when
the camera cell, yaw or zoom changes; `$f898` walks the grid far to near through one of four
yaw-quadrant handlers (jump table `$f986`: `$f98e`, `$fa9a`, `$fbb4`, `$fccc`) and fills two
triangles per cell from a 4-plane pattern table through `$ef62`, `$e3e6` and the 16.16 DDA span
walker `$e420`; each cell's sprites are drawn inline right after its triangles (`$115e0`), so
the walk order is the depth order. A triangle has no colour of its own: its colour byte
(from colour plane A or B, baked from the altitude plane by `$10058`, plus the water shimmer
`[$4bb3e] & 3` below `0x0c`, or the forced `0x1c`) selects a 128-byte slot of the pattern table
at `$2e000`, and the scanline picks the row: `A5 = $2e000 + colourByte*128 + ((8*y) mod 128)`,
with a 64-byte phase that flips on every re-projection. The corners in `$3f364` are relative to the
iso window, which is drawn 64 px right of the screen origin; `$ef62`'s own `screenX <= 255` clip
runs on the raw corner before that inset. The open sea, the HUD and the minimap
are baked once into the `$78000` master by `$13b9a`; there is no per-frame sea fill
(`graphics.md` "The terrain mechanism", "The frame pipeline"; `port/SPEC.md` 3, 4).

**Evidence.** The projection is proven against the real 68000 by `callcap` (called in isolation
with `A3 = $13f8a`, the recomputed `$3f364` is byte-identical to the stored corner buffer on
four captures; an integer reconstruction, `py/proj/proj_ref.py` (gate `py/proj/gate_fecc.py`), matches 3240/3240
vertices over 36 generated camera states plus four natural captures, zero fudge; a float
version of the projection agrees to one pixel); the rasteriser is byte-exact against a live single-step
(all 128/128 `$ef62` calls of a frame, the dither phase on every scanline of two traced
triangles, the DDA span endpoints of a 27-row triangle, in quadrant 2); and the whole frame
matches the game's compose buffer 100.00% on 27 captures from 12 views on lands 0, 5, 25 and
60 (including snow, rain, a fight, a projectile and boats), scored against the screen in the
next `$f898` snapshot, with terrain away from sprites at 99.7 to 99.96% (`port/SPEC.md` 6
"Scoring a capture", 4).

**Sprites.** The sprite path is `$115e0` through the dispatch tables
`$1162e` (prepare) and `$1165c` (blit), keyed on the record's category byte 6 (even values,
0 to 30), over the `$47970` bucket chains whose offsets are signed words (scenery and animals
live below `$51b66`). Four sheets are decoded: `$33000` 8 x 11 (352 frames, `port/assets/sprites/sheet_contact.png`),
`$312a0` 16 x 16, `$37c7c` 32 x 24 and `$3af1c` 32 x 32; the frame formulas for every
category are in `port/SPEC.md` 6 and `port/assets/sprites/sprite_triggers.json`, and a
building or tree is `(record[7] & 0x7f) + word[$11746 + word[$57fd0]]` with the table
`{0, 3, 6, 9}` (`graphics.md` "Trees / buildings / mountains").

The 16 and 32 pixel clip
blitters are gated 450/450 (`py/blit/blit_gate.py`), the minimap `$107d6` 512000/512000 bytes
over four modes (`py/maps/gate_minimap.py`), and the land build (`$10058` 125219/125219,
`$10410` 45779/45779, `$10910` 2561/2561, `$10638` 260/260, `$ac20` 14539/14539, all in
`py/maps/`) in `graphics.md` "The land build" and "The minimap and the conquest map".
Profiles at both zoom extremes (the fill is rate-bound; zoomed out the `$f000` slope divides
dominate) are in `graphics.md` "Isometric renderer, measured" and "Zoom comparison".

### The port

`port/` is a from-scratch Godot 4.x plus F# port built on those proofs: `port/SPEC.md` is the
contract, `port/assets/` the asset pack extracted from a live RAM image by `tools/pm_export.py`
(`assets_k60/` the same for land 60), `tools/pm_render_ref.py` the Python reference
renderer, `port/godot/logic/` the F# logic (`Fill.fs` the rasteriser and the four quadrant
walks, `Projection.fs`, `Sprites.fs`, `Scene.fs` the inline draw order, `Season.fs`,
`Weather.fs`, `Equipment.fs`), `port/godot/game/TerrainView.cs` the live scene (arrow keys
pan, PageUp / PageDown rotate through 16 yaw steps, Y cycles the season; the minimap panel and
its camera-window box are port additions, the game draws no viewport rectangle), and
`port/stepper/` a slow-motion replay of one frame in the game's own draw order. The F#
rasteriser, entity pass and projection are cross-checked byte-exact against
`pm_render_ref.py` on synthetic and real data (entity pass 13/13 synthetic cases and 2881/2881
covered pixels on the real 53-record stream; `py/parity.py` equal on all 15178 drawn pixels
of one capture; stepper `--selfcheck` 23/23). Godot stays at zoom 4. Per-capture
verification records are in `port/README.md`.

### Differential testing against the real 68000

The `callcap <addr> [maxSteps] [out|-] [Rn=hex ...]` REPL primitive calls one subroutine in
isolation from a captured state (sentinel return address, interrupts masked, register
presets), records the register and changed-memory delta and a per-step trace hash, then
restores the snapshot through the verified-identity path, so a session replays
byte-identically after any number of `callcap`s (`detcheck`). It is in two emulator
commits (`f6d574f`, `df140df`), which went in behind the regression net (`verify 5M` pass, 30M diskless boot
snapshot byte-identical, selftest 807124 pass / 0 wrong / 8 skip when they landed).

Because `callcap` masks interrupts, a routine that waits on a flag the interrupt
clears never returns (for PM's sound calls poke `$2c993` to 0 in the state).

**Method.** Each gate follows one method: disable every record but the target's (owner byte := 0) so
`callcap 14b62` runs exactly the reconstructed subset, or call the leaf directly with its
entry contract (`$fecc` needs `A3 = $13f8a`; `$3c08` needs `A1`; `$37c2` needs `D2`; `$1d70`
needs `A3`; `$14b62` needs nothing), compare the full changed-memory delta over the object
records, buckets, leader and settlement tables, pre-register a falsifier and a pass bar, and
run negative controls that must flip the result. Arms the corpus does not reach are asserted
off with a `raise`. The reconstruction (`tools/pm_fsm_ref.py`, tables sliced from a RAM image
by `init_tables(ram)`) and the harness (`tools/pm_fsm_diff.py`: `Harness`, `State`,
`run_corpus`) are committed, with `tools/capture_hits.py` for natural corpora and
`tools/disassemble.py --snap` for the listings. The committed harness reproduces the five
original FSM gates byte for byte (675/675, 1335/1335, 413/413, 85/85, 99/99: 2607 tracked
bytes over 154 states; the acceptance scripts are `py/fsm/repro93..97.py`). The other gates live in `py/` and its subdirectories, indexed in
`py/README.md`; `py/gate_coverage.py` lists the routines no gate names.
## Files

The documents are in the table at the top. The rest of the directory:

| file | what |
|------|------|
| `cracktro.png` | Replicants cracktro key-wait |
| `title.png` / `credits.png` | PowerMonger title, scrolling credits |
| `empire_intro.png` | Empire "Pondering over the map..." intro |
| `name_entry.png` / `menu.png` / `world_map.png` | name dialog, option menu, campaign world map |
| `briefing.png` | "Between Pages 1-5" mission briefing |
| `iso_view.png` | isometric battle view, past the briefing OK button |
| `iso_rotated.png` | iso view after about 5 keypad rotation steps (`$ff9a` `$f0` to `$a0`) |
| `iso_zoom_in.png` / `iso_zoom_out.png` | iso view at zoom index 1 / 7 (`$fe04` patched via `$13bbe`, `graphics.md` "Zoom comparison") |
| `chat_message.png` | the link chat panel ("message from <lord>") showing a received character, from a `$26` order injected into slot 2 |
| `info_click.png` | the examine tool: icon `$2c`, then a click on a tree opens its info panel (`m1_s0`) |
| `pm114_prop_contact.png` | every `$37c7c` building/tree frame rendered against the real palette |
| `pm114_tileset_families.png` | the four `g_tileset_sel` frame-offset variants for `r7 = 0, 1, 2, 12` side by side |
| `dither_atlas.png` | pattern-table slots `0x00`-`0x40` decoded against the real palette |
| `dither_triangles.png` | mission 1 terrain: as drawn, by colour byte, by source plane |
| `dither_infographic.html` | interactive pixel probe, tile atlas, ramp anatomy, season fade; built by `py/dither_atlas.py` |
| `blit_variants.png` | one call of each of the six clip back ends of the 16/32 px blitters, before and after (`py/blit/blit_demo.py`) |
| `minimap_modes.png` | the four minimap modes of `$107d6` on `k5_s4`: contour, terrain with marks, terrain, terrain with lord dots (`py/maps/render_maps.py`) |
| `terrain_roads.png` | the land `k5_s4` as a cell map with the `$1d` road and town-ground cells white: the roads link the islands as causeways |
| `worldmap_full.png` | the whole 320 x 608 conquest-map bitmap with the 13 x 15 land grid |
| `scale_da.png` | the five frames of the force-ratio balance `scale_da` |
| `fade_palettes.png` | the five fixed palettes `_work_pa`, `_zero_pa`, `_game_pa`, `_con_pal`, `_lost_pa` (rows in that order) |
| `powermonger.sym` | `addr<TAB>name` symbol table (about 1,260 routines and data tables, the developers' names merged in where known) for `trace_cfg.py --names` and the disassembler |
| `powermonger_orig.sym` | the developers' own symbols (text, data and bss, 8-character names, 1,196 entries) unpacked from `DATA\SPRITE40.DAT`; `py/s40_symbols.py` regenerates it, `py/s40_orphans.py` lists the unreferenced routine starts |
| `py/` | the working scripts, gates and corpus capture helpers; `py/README.md` is the index, with the match count of every gate |
| `port/` | the Godot 4.x plus F# port: `SPEC.md` (the porting contract), `README.md` (layout, the frame stepper, verification records), `assets/` and `assets_k60/` (the asset packs for mission 1 and land 60, `manifest.json` gives the provenance of each file; regenerate with `tools/pm_export.py`), `godot/` (F# logic, C# scene glue), `stepper/` (frame replay), `walkthrough/` (an executable walkthrough document). `tools/pm_render_ref.py` rebuilds a frame from `assets/` alone and is the reference the F# port is cross-checked against |
