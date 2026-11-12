# carriercommand: Carrier Command (Realtime Games / Rainbird, 1988)

A real-time strategy and vehicle simulation: the player's carrier and the enemy's compete for a
64-island archipelago, capturing islands, turning them into resource, factory or defence bases and
supplying the carrier through the network they form. Reached in the emulator: the language menu, the title
menu with its 3D attract scene, the Strategy game with the carrier at Vulcan and the Action game's opening. The game is hand-written
assembly (1 `LINK` frame, about 920 `RTS`), so it is analysed from traces and callcaps, not a decompile.

| Doc | Covers | Proof |
|---|---|---|
| `ai.md` | the enemy carrier's state machine, how it picks its next island, capture and attack, fighting the player's carrier and retreat, island defences, difficulty, the cheat mode, the two games | target choice 1344/1344 score words and 21/21 decisions, with constant-by-constant controls; difficulty A/B/C 3/3 arms; combat states driven state by state |
| `vehicles.md` | the player's carrier motion and autopilot, the arctangent, repair priorities, missiles and flares, the craft slots, the Manta lift, launch and take-off | carrier 150/150 and 600/600 ticks (1950/1950 in the full run), arctangent 529/529, repair 10/10 and 12/12, flares 5/5, take-off 42/42 twice |
| `economy.md` | the fixed island tables, world creation, the RNG, the supply graph and distance matrix, production, production lines and packets, island building | production 175/175, line cost and steps 14/14 each, landings 4/4, RNG 1/1 |
| `render.md` | the 3D engine: sine table, chained 2D rotations, projection, depth tree plus BSP plus back-face culling, the self-modifying span filler, the model format | sine 4096/4096, rotations 360/360 and 120/120, projection 480/480, face test 120/120, spans 780/780 |
| `packer.md` | Automation Packer V2.3r: the `LSD!` LZ77 format, the backwards in-place depack and its safety margin, ratios against modern compressors | depacker output identical to `tools/lsd_depack.py`; minimum read/write gap 218 bytes on all six packed files |

Gates: `uv run python tools/gates.py run carriercommand` (`gates.toml`, five gates, all PASS).

What stands out: the enemy's whole strategy is one additive score over the 64 islands plus an argmax, with a
probable bug that always treats island 4 as connected to its network; difficulty only tunes the island
defences, and past `$8000` a signed compare turns it back to the easiest setting; the enemy carrier only exists
as a physical object while it is fighting; captured islands get a random type; the carrier's autopilot steers
in a straight line and runs aground; repair shares a fixed capacity among the systems at the top priority; a
missile is decoyed by whichever flare its scan meets last within 6000 units; the economy routes goods as packets over an all-pairs distance
matrix relaxed 8 rows per call; the renderer patches its own span filler per colour and uses three layers of
hidden-surface removal with no 3D matrix anywhere; and the cheat phrase is "GROW OLD ALONG WITH ME", typed
while paused.

## Design digest

The game's rules restated for re-use in another design, without addresses. Each line names the section that proves
it (A = `ai.md`, E = `economy.md`, V = `vehicles.md`, R = `render.md`); anything not proven there is labelled
inferred. It covers what is decoded so far: the
world and its economy, the enemy carrier, the island defences, the player's carrier, repair and countermeasures,
and the renderer. The Manta and Walrus flight models, drone launchers and command-centre missiles in action, the
end of an island assault, the production-priority and fuel screens are not decoded yet. The crack's stack leak
and the Automation Packer belong to this copy, not the game ("Provenance", `packer.md`).

### What carries the game

- **A fixed map with a grown starting state.** The 64 islands' names, positions and sizes are fixed tables. The
  buildings each island starts with are not laid out by hand: the ordinary island tick is run 500 times at
  instant-build speed (the tables proven, the 500 ticks read from code). (E 1, E 2)
- **Islands are bases of three kinds besides the two home bases.** Capturing a neutral island plants a command
  centre; when it completes the island becomes RESOURCE, FACTORY or DEFENCE, and for the enemy that type is a
  random pick of the three, not a choice (from code; four captures observed, types 1, 1, 2, 1). An island falls when no command centre is
  left on it (inferred). (A 3, A 4)
- **Supply is a graph that ownership cuts.** Most islands link to two or three neighbours (one hangs off a single
  link); a link carries goods
  only between two islands of the same owner, so taking an island severs the other side's routes through it
  (from code). Goods travel as packets, one hop at a time, along shortest routes from an all-pairs distance
  matrix (the routing from code; four landings proven, all on the island that made them). (E 3, E 4)
- **Production is per island type.** Each economy pass adds to an island's stock: 100 for the base and 25 per
  production line for a factory (proven 175/175); 100 per supported building for a resource island, 0 for a
  defence island, capped at twice the island's area (from code). A production line pays its cost
  from the stock every pass, counts down its steps and then sends a packet of its item to its destination
  (14/14). (E 4)
- **The enemy's whole strategy is one score per island.** At each decision it scores all 64 islands and goes to
  the first maximum: a penalty growing with distance from the carrier, a bonus for neutral islands (more for large
  ones), a smaller one for the player's, a penalty for its own, a large bonus for islands touching its connected
  supply network, a small term of distance from its base (added for its own islands, subtracted for others, so it
  favours others' islands near its base and its own far from it), a bonus for the player's home island, and
  never the island it is at. So it grows its network from the nearest worthwhile island outward and hops through
  its own islands only when nothing better is in reach. There is no lookahead (1344/1344 score words, 21/21 targets, ten of eleven
  constants load-bearing). (A 2)
- **The enemy carrier is abstract until it fights.** Travel is a countdown of octagonal distance / 250 ticks with
  no physical object at sea; on arrival it resupplies at its own island (hull +4 a tick), captures a neutral one, or
  attacks a player island if its hull is high enough. Only when a player unit comes within 150,000 of it at an
  island is it placed in the world, beside the island, as a vessel that can be fought. (A 1, A 3, A 5)
- **Carrier combat is a short script.** Engaged beyond 30,000, the enemy carrier launches an aircraft every 30
  ticks while it has aircraft left and one of its four slots is free; inside 30,000 it turns to the reverse bearing and, when lined up,
  fires a missile at most every 200 ticks, launching aircraft only straight after one. Below 3000 hull or out of missiles it retreats along its stored heading and goes back to choosing an
  island once nothing is within 150,000 (thresholds and retreat proven; the missile cooldown and the
  aircraft-after-missile rule from code). (A 5)
- **An assault on an island is a dice round** every 250 ticks: the enemy's attack (aircraft up to four, plus half
  its hull) against the sum of the island's defence structures, each hit costing a random building health or the
  carrier hull, an aircraft or a missile (inferred; two structures destroyed and one missile lost in a 144M-step
  run). (A 4)
- **Difficulty is the island defences, not the planner.** One number, raised by destroy events and higher from the
  start of the Action game, sets how many drones a launcher keeps up, drone speed, drone and structure armour,
  missile speed and turn rate, the missile-site range, and whether command centres shoot at aircraft. The target score and the
  state machine never read it (the missile-site range proven, 0, 2, 0 launches at 0, `$6000`, `$c000`; the
  other parameters, the rises and the planner never reading it from code). (A 6)
- **Only the islands near the action are simulated in full.** Two structure blocks hold the live islands, loaded
  when the player's carrier or a craft comes within 130,000 and dropped when nothing refers to them (a switch
  proven); one island's building tick runs per frame, in an order the RNG reshuffles every 64 ticks (from code). (A 6, E 5)
- **Islands build themselves.** Each island ticked builds the highest-weight structure its class allows, at most
  two at once; the class is the island type, plus a second tier when the area is at least 2000. Scenery has a 1 in
  4 chance a tick to vanish. This rule grows the starting world and every captured island (from code). (E 5)
- **The defences are a few timers.** A missile site fires at an opposing carrier within its range on a random
  128..255-tick timer; a drone launcher puts up a drone every 100 ticks to the difficulty's limit; a drone has
  1000 fuel, wanders within 24,000 of home and attacks an opposing unit within 25,000 (all from code; only the
  missile site seen firing). (A 6)
- **The player's carrier is a point mass.** Speed eases toward a target speed by a 32nd of the gap each tick, the
  heading turns by a sixth of the yaw rate, and the ship moves twice as fast in open sea away from islands and its
  own craft; fuel burns with speed every 16 ticks (1950/1950 ticks). Engine damage caps the speed. (V 1)
- **The autopilot turns, then goes.** It steers straight at the destination; above about 1.4 degrees of error it
  drops to a crawl and turns nearly on the spot, then accelerates, capping cruise speed inside 2000 and
  declaring arrival and braking inside 1000, then coasting (the proven run ended about 2400 past the destination).
  (V 1)
- **Damage degrades systems, and repair is a priority queue.** Each of ten systems has a health and a priority.
  Engines and laser give nothing below half health; the switch systems work above half; the repair systems and
  superstructure scale linearly. Repair shares one capacity equally among the damaged systems at the highest
  priority present, and that capacity scales with the repair system's own health, so damage to it slows every
  repair (10/10, 12/12). (V 3)
- **A launch is a short deck sequence.** A Manta goes up the lift to the deck, then takes off in three phases
  in the carrier's own frame: it rises off the lift, rolls along the deck accelerating to a fixed speed, then pitches
  up and climbs off the bow, leaving with the carrier's speed added to its own (the take-off 42/42 ticks with the carrier at rest and 42/42
  turning). With no destination it is sent to a holding point 6000 behind the carrier (from code, matching the one
  launch observed). (V 5)
- **Missiles home and flares decoy.** A missile re-targets every 5 calls to any of the (at most two) flares within
  6000 of it (5/5 cases); its guidance slews yaw and pitch by at most 11.25 degrees a call (inferred). (V 4)
- **Two games from one engine.** Strategy starts from the player's home island against an enemy holding eight;
  Action drops the player into a war already under way, 15 islands against 37, at a higher difficulty (proven).
  (A 8)
- **A cheat phrase typed while paused** unlocks invulnerability, refuelling, repair and a teleport for craft on
  autopilot (the phrase proven, the keys inferred). (A 7)

### Limits that became features

- **Cheap distances shape the game.** Every range decoded so far is octagonal (`max + min / 2`) or a
  Chebyshev box, so no multiply is needed; the target score's distance term uses the same octagon. (A 2, A 5, V 1,
  V 4)
- **No lookahead, so the enemy is readable.** Being an argmax re-run at each arrival, its next island can be
  predicted from the map, and the network bonus makes it creep along its own supply chain. (A 2)
- **No obstacle avoidance, so the player navigates.** The autopilot reads only its destination; islands are
  handled after the move, and a carrier that comes within 10000 of an island's box is stopped, thrown into reverse and locked out of control
  for 50 ticks (grounding proven; the absence of avoidance from code). (V 1)
- **One graph, several uses.** The supply network's distance matrix routes goods, drives the enemy's network bonus,
  and gives the island panel its DISTANCE TO BASE, ISOLATED and RE-ROUTING readouts. It is relaxed 8 rows a call,
  spread over many frames, and packets and the enemy's next choice wait while it is incomplete (inferred).
  (E 3, A 1, A 2)
- **Fixed slot counts are the rules.** Four Mantas and four Walruses, four enemy aircraft aloft, two flares, two
  live islands, 128 drawn objects (all from code). (V 4, V 5, A 5, A 6, R 1)
- **A 3D world with no 3D matrix and no terrain.** Rotations are chains of 2D rotations by stored sine and cosine
  pairs; islands, buildings and trees are ordinary models over a single sea-and-sky half-plane. Hidden surfaces
  are three cheap layers stacked: objects sorted by depth, each model a precompiled BSP tree, and a back-face test
  per leaf item that carries test vertices (the arithmetic proven, the orders read from code). (R 1, R 2, R 4)
- **Colour by rewriting the filler.** The span filler patches its own instructions per colour, giving 16 solid
  colours and 48 one-pixel checkerboard dithers whose phase flips each scanline; each span is widened to overlap
  the previous one (780/780 rows), inferred to close gaps on steep edges. (R 5)
- **An arctangent from one table.** The angle is the octant ratio divided by a tabulated ratio-to-angle factor, no
  polynomial or CORDIC, within 0.15 degrees (529/529). (V 2)

### Bugs and accidents a new design should drop

- A fixed-address write marks island 4 as connected to the enemy's network whenever any connected enemy island is
  ticked, so its neighbours (3 and 12) always get the network bonus (the effect proven by two pokes; that it
  is a bug is inferred). (A 2)
- The enemy is drawn to the player's home island by a bonus, but that island cannot be captured, so the result is
  a visit and an immediate re-target (observed once). (A 2)
- Difficulty is raised unsigned and compared signed, so past half scale the drone count, missile-site range and
  command-centre missiles fall back to the easiest setting (0 launches at `$c000` against 2 at `$6000`). (A 6)
- The retreat speed ramp has its operands swapped: the carrier jumps to full retreat speed on the first tick (248
  on all 238 ticks; the intended ramp inferred). (A 5)
- The enemy's aircraft-aloft counter is decremented but never incremented, so the real limit is the four slots
  (from a raw scan). (A 5)
- A flare captures a missile without comparing the carrier's distance, and the later flare slot wins over the
  nearer flare (proven). (V 4)
- The arctangent returns a 90-degree error for an input of exactly -32768, where `neg` leaves the value
  unchanged (proven in the grid). (V 2)
- The random-number generator is also stepped by the sound interrupt, so its sequence depends on interrupt timing,
  not only on the game state (inferred from code). (E 2)

## Provenance

- Zuul #45 compilation (`Zuul #45.zip`, one `ZUUL045.MSA`, 792,456 bytes, sha256
  `cfa9031b32e63562e10e3cf30e9d9b03cf5a4590faee2735a6d3d47b150dcd25`), converted with `tools/msa2st.py` to an
  839,680-byte `.st` (sha256 `c098aee2ba30b05a9ba7bd6d80678d41825854cc67636b136d586058a39f364b`). Other games on
  the disk: Arena, Crystal Castles, Deep Space, Trantor, Star Raiders.
- Carrier Command is `PACT2.PRG` (135,486 bytes), wrapped in Automation Packer V2.3r (`packer.md`); it unpacks
  to a 323,196-byte GEMDOS program (sha256 `0d3938982b8a909de79b52d26824ba05b42980cbcdcd94ce790b912bcfe20448`)
  with the copyright string "COPYRIGHT REALTIME GAMES SOFTWARE LTD 1987/88".
- **The crack leaves a time bomb running.** The main loop (`$3a40..$3a4c`) pushes a word onto the stack on every
  pass unless the manual-word protection recorded an answer (`$126d` set and the answer length `$126e`
  nonzero). The protection (`$9da2`, reached from the language menu, whose 1..3 key picks one of three 64-word
  lists) has its key reads replaced by `nop`s and a `bra` past the store in this copy, so `$126e` stays 0 and the
  stack sinks 2 bytes per pass (inferred as the cracker's patch: no original to compare). About 1.55G steps
  after `c_s30` (roughly 43 minutes of play) it reaches the sound-channel records at `$4f032`; the VBL handler's
  register save turns a channel pointer into `$ff412d00`, the read at `$1ff5a` bus-errors (correct: `$400000`
  and up is a bus error on the ST), the game's bus-error handler is a bare `rte` that returns to the faulting
  address with the stack 8 bytes deeper each time, and the stack spirals down until a frame lands on `$4` and
  the CPU halts with a double bus fault. A real ST would do the same (inferred). Proven: the stack falls 20
  bytes per 10 passes from `ai/nat/d2.snap` and stays put with `w 126c 00ff0001`; a 750M-step run with that poke
  does not fault, the unpoked one halts within 700M. **Long runs from `c_s30` need `w 126c 00ff0001` first.**
  The halt reproduces within 50M steps from `crash/c10.snap`, and the first bad read about 16.8k steps into
  `crash/f03.snap`.
- The menu-disk copies of `PACT1..4.PRG` have `$ffffffff` as the first long of the text where the program
  needs `movea.l 4(a7),a5` (`2a6f 0004`, as in `STRAID.PRG`), so run alone they take a Line-F exception at
  once (inferred: the Zuul menu loader writes the instruction before launching). Restoring the 4 bytes at file
  offset `$1c` gives `CARRIER.PRG` (sha256 `34caa0021659ecd33f28fbd368f1672645b384cc0e5a4392c8bf7b37b54cc937`),
  put alone in `\AUTO\` on a blank double-sided disk: `carrier_auto.st` (sha256
  `54261b30545e9a354ada6f0a3e11b80000432029d769584938a36984d8ed9464`).
- After depacking, the game prints "Yes, I have kicked out the OS", takes over the machine and runs from low
  RAM (code about `$3900..$235f8`); addresses in these docs are those runtime addresses.

## Running it

```
W=scratchpad/carrier
uv run python -I tools/msa2st.py $W/zip/ZUUL045.MSA $W/zuul045.st
uv run python -I tools/extract_disk.py $W/zuul045.st $W/files
# patch PACT2.PRG's text long at offset $1c to 2a6f0004 -> $W/CARRIER.PRG, then:
uv run python -I tools/make_blank_disk.py --sides 2 $W/blank.st
uv run python -I tools/add_file_to_disk.py $W/blank.st $W/CARRIER.PRG --auto --out $W/carrier_auto.st
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll 80000000 snapshot $W/c80.snap --disk-a $W/carrier_auto.st
(cat reversing/carriercommand/drive.txt; echo "snap $W/c_s30.snap") | \
  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume $W/c80.snap repl
```

The banner "AUTOMATION PACKER V2.3r" appears at step 2.55M, the depack finishes by 7.4M and the language
menu is up by 80M (`language.png`). `drive.txt` presses 1 (English), waits 60M steps for the title menu
(`title.png`), moves the pointer 55 pixels up onto "Start Strategy Game", clicks, and runs 30M steps into the
game (`strategy.png`). Both the cold boot and the drive are deterministic: rerunning them reproduces `c80.snap`
and `c_s30.snap` byte for byte.

**Mouse input needs a workaround.** The game's ACIA handler (`$1794c`) lowers the interrupt mask to 5 on entry.
The emulator raises the next IKBD interrupt as soon as a byte is read and does not model the MFP in-service
register, which on hardware holds off a second channel-6 interrupt until the handler clears it
(`bclr #6,$fa11.w` at `$1797a`). A `mouse move` packet's three bytes therefore nest three handlers deep and are
processed last byte first, and the pointer never moves. `drive.txt` sends each packet byte on its own `kbd`
call with 3,000 steps between them (header `$f8`, `$fa` with the left button down). Keyboard input is one
byte per key and works normally. This is an emulator gap, not fixed yet.

## Snapshots

All in `scratchpad/carrier/` (indexed in `scratchpad/ANCHORS.md`):

| Snapshot | State | Made by |
|---|---|---|
| `c80.snap` | language menu | cold boot, 80M steps |
| `c_eng.snap` | title menu, 3D attract | `c80` + `kbd 02/82` + 60.4M |
| `c_mv.snap` | pointer on "Start Strategy Game" | `c_eng` + the `$f8 00 c9` packet + 0.4M |
| `c_s30.snap` | Strategy game, carrier at Vulcan (-4415,-4288, bearing 005), `$1244 = $ff` | `drive.txt` from `c80` |
| `ai2/menu_0.snap`, `ai2/menu_15.snap` | Strategy and Action game starts | each button clicked from `c_mv` (`py/ai2/menu.py`) |
| `ai2/st2.snap`, `ai2/st56.snap` | enemy carrier repairing at island 56; the player carrier at island 56 for the defence census | `py/ai2/drive.py` from the attack poke run |
| `crash/f03.snap`, `crash/c10.snap` | the leaked stack just before it reaches the sound records; 50M steps before the double bus fault | bisected from `ai/nat/d2.snap` |
| `ai/nat/d1,d2`, `ai/nat2/e2..e12` | enemy target decisions from a run of `c_s30`, stopped at `$1ad02` (the `nat2` run pokes `$11c0` to 1 after each decision to skip 500M-step journeys) | `ai/nat*/script.txt` |
| `ai/s1..s6b` | target decisions after single-variable pokes (`ai.md` section 2) | forced state 1 + pokes + `bp 1ad02` |

## Architecture

The VBL handler is `$176d0` (every 12,000 steps); the main loop runs about every 6 VBLs. Per main frame it
runs the enemy carrier's state machine (`$1ac8c`, from `$3a04`, skipped while paused), one island's building
tick (`$18106`, round robin), every 4th frame the economy chain (`$f254`), the entity dispatcher for vehicles,
drones and island structures (`$193dc`, a jump table by type), and the 3D frame (`$14152`). Shared mechanisms:

- **Fixed tables plus simulation.** The map is data (`$4d41a`); the starting state is grown by running the
  ordinary island tick 500 times at instant-build speed.
- **One graph, two uses.** The adjacency lists at `$22afa` and the distance matrix at `$67b40` route the
  economy's packets and feed the enemy's target score (row 63) and the "ISOLATED" display (row 0).
- **Work spread over frames.** The distance matrix is relaxed 8 rows per call; islands are ticked one per
  frame.
- **Self-modifying inner loops.** The span filler is patched per colour.

## Files

| File | What |
|---|---|
| `ai.md`, `economy.md`, `render.md`, `vehicles.md`, `packer.md` | topic docs |
| `carriercommand.sym` | routine and table names, each from its body |
| `drive.txt` | REPL input from `c80.snap` to `c_s30.snap` |
| `gates.toml` | the promoted proofs for `tools/gates.py` |
| `language.png`, `title.png`, `strategy.png` | milestones |
| `cheat.png` | "Cheat Mode active" after the phrase |
| `islands.png` | the 64 islands from the fixed tables, starting owners and the supply graph (`py/world/render_map.py`) |
| `models.png` | the 3D model table decoded and drawn (`py/render/sheet.py`) |
| `py/ccpaths.py` | repo root and work dir (`$CARRIER_WORK`, default `scratchpad/carrier`) for every script |
| `py/autopack_depack.py` | the Automation Packer depacker and its in-place gap check |
| `py/ai/` | `score.py` (target-choice model), `gate_score.py` |
| `py/world/` | `rng.py`, `prove_production.py`, `prove_line.py`, `prove_transfer.py`, `gate_economy.sh`, `render_map.py` |
| `py/ai2/` | `drive.py` (state-change log for the enemy carrier), `defence.py` (structure launch census with a difficulty poke), `menu.py`, `gate_difficulty.sh` |
| `py/units/` | `carrier_proof.py` (per-tick carrier model against the emulator), `atan_port.py`, `atan_grid.py`, `repair_proof.py`, `flare_test.py`, `takeoff_proof.py` (per-tick Manta take-off model), `manta_snaps.py` (the Manta anchor snapshots), `gate_units.sh` |
| `py/render/` | `rig.py` (REPL and callcap driver), the five gates, `gate_render.sh`, `model.py`, `sheet.py`, `views.py`, `show.py`, `seq.py`, `subdivide.py` (a model as OBJ, subdivided and silhouette-scored, `render.md` section 6) |

## Not exercised in the emulator

The Manta's airborne flight and landing, the Walrus launch and driving, a drone launcher or command
centre firing, the island-capture end of an attack, the production-priority and fuel screens, saving and
loading. The decoded 3D model drawing order has not been compared with the game's.
