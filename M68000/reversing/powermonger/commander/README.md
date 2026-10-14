# PowerMonger commander: an outside AI for a side

A reimagined commander for PowerMonger: an LLM that plays a side of the original game in the
emulator, with A* as its movement tool and exact snapshot rollouts (later a learned state-space
model) as its forecaster. The game's rules, AI and order pipeline it builds on are documented in
`../strategy.md`, `../ai.md` and `../economy.md`; this directory holds only the commander and its
harness. Continuation record: `M68000/sessions/commander.md`.

## Design

**Layers.**

- **Commander (LLM).** Chooses one order per decision for each of its side's groups, from the
  game's own order set (`../strategy.md` "`$6a3a` / `$6ac6` / `$6b38` — the order executor": attack
  `$0c`, get food `$06`, get men `$08`, invent `$0e`, posture `$16`, alliance `$1e`, spy `$20`, ...).
  The topic docs are its rulebook.
- **Movement tool (A*, `astar.py`).** The game has no pathfinding: a lead walks straight at its
  target and sticks at a shore (`../README.md` "No pathfinding", `../ai.md` mode `$48`). The graph
  has two nodes per cell, the two triangles `$1648e` tells apart (colour B `$438ee` and colour A
  `$418ad`, picked by flag bit 7 and the point's place in the cell; 0 is water), so a half-wet
  shore cell is modelled as the game sees it. `reachable()` and the land components answer "can
  this group get there on foot"; `path()` runs A* over triangle centroids and string-pulls the
  result into waypoints, keeping only legs that pass `Map.leg`, a model of the walker's own
  probe (mode `$10` samples `P + k·step` for k = 1..dwell; any water point sends the man to the
  `$48` sweep). After a man reaches a waypoint his job rewrites his target, so the commander
  issues one order per leg and re-issues after each arrival.
- **Forecaster.** First exact rollouts: the game is deterministic (`../strategy.md` "RNG and determinism"), so
  snapshot, inject a candidate order, run N steps and read the outcome (`rollout.py`, below). A 1000-tick lookahead
  (177M steps) costs about 84 s for one candidate and about 115 s each for six in parallel on a loaded machine
  (2.1M steps/s per process alone, 1.5M at six; process start 0.25 s): a handful of candidates per major decision,
  too slow for tree search. A state-space model over per-side aggregates (men, food, loyalty pressure) trained on
  the rollout traces comes second, judged against the rollouts and against a hand-written recurrence of the proven
  rules.

**Action interface: the command buffer** (proven, `gate_inject.sh` 7/7). Each side has a 6-byte
slot at `$58016 + 6*side`: byte 0 the side, byte 1 the order type, bytes 2 and 3 the target cell x
and y (the AI's natural get-men order for side 3 carried `$306b`, its lord 1's cell (48,107)),
byte 4 the slot state (`../strategy.md` "`$58016` — command buffer"). The executor `$6a3a` runs
slots 1..4 in states 2 and 4, and the commander AI writes a slot only in state 4, so setting a
side's slot to state 2 silences its built-in AI and leaves the slot to the harness, with no UI
clicks. The order acts for the group named by the word `$58042[2*side]`
(`side*$13c + $4c + 2k`), which the player's captain-portrait click sets the same way; the harness
writes it before the order (a longword `w` there covers two sides' words). The commander's own
group (group 0) runs the order in the same pass; any other group gets it by carrier pigeon, as the
game's own orders do (group 1 in the gate: landed 8.7M steps later).

**The target cell is the cell centre** (`gate_cellpt.py`, 16/16: 8 supply orders including the map's corners, 8
attacks on lords). The world is 256 units per cell, so cell (x, y) covers world `[256x, 256x+256)` by
`[256y, 256y+256)` and a world point is in cell `(x>>8, y>>8)`. Supply `$390e` writes the lead's target words 20/22
as the cell byte with `$80` below it; an attack on a settlement or lord goes through `$4a7a` → `$4b80`, which rebuilds
the same centre from the lord's packed cell `y*64+x`. An attack on a cell holding only a foreign man takes `$4b96`
with that man's own position instead (one case, not isolated). For movement this means an A* waypoint is sent as its
cell's centre, two waypoints in one cell are one order, and the centre lies on the cell's diagonal, so `$1648e`
samples it as triangle B: a waypoint whose cell has a wet triangle B is a water target.

Gate (`gate_inject.sh`, from `pm142/rand1.snap`, 30M steps per arm, a watch on side 3's slot):
unpoked, side 3's AI writes the slot 3 times (`$08`, `$22`, `$02`); with the slot at state 2 it
writes nothing and no attack runs; an attack `$0c` on player lord 9 at (15,92) runs `$6c32`,
`$4a7a` and `$4b80` once each, leaving group 1 in state 8 with opponent class 2 (a lord), or with
`$58042[3]` set to group 0, group 0 marching then fighting (state `$d`) within the 30M steps.

**Every player order works from an AI slot** (`gate_orders.sh` 57/57, 16 arms of 40M steps from
`rand1.snap`, side 3, each against a same-budget control). The executor `$6ac6`/`$6b38` tests only
the order type, the acting-group word and the group's sender; the local side is tested only in the
HUD and chat tails (`$6e72`, `$6d98`, `$6dd0`, `$6e10`, `$6e5c`), and `$3154`'s target filter
excludes the issuing side, not the local one. Encoding of bytes 1..3 and the signal each arm checks:

| order | bytes 1..3 | runs | signal |
|---|---|---|---|
| posture | `$16`, word = posture 2..4 | `$6cc6` → `$35a0` | group posture 2 → 4 (also by pigeon to group 1) |
| transfer men | `$04`, from `2k`, to `2k` | `$6ba8` → `$1c18` | group 1's 17 men to group 0 |
| dismiss | `$14 00 00` | `$6cbc` → `$1cc4` | group 0's 12 men home to lord 12 |
| drop food / equipment | `$12` / `$18`, `00 00` | `$39d4` D7 = 1 / 2 | food or the 12 boats dropped |
| spy | `$20`, cell x, y of a town | `$6d56` → `$3154` → `$1d36` | arrival mode `$7a`, `$3dca`; the lord's men +1 |
| alliance | `$1e`, town cell | `$6d32` → `$3154`; `$33b0` → `$3458` → `$34a8` | both sides' peace bytes to `$0c`; carried goods paid as tribute |
| get food / men | `$06` / `$08`, town cell | `$3154`; `$150c0` / `$15122` | lord's food to the army / join-wait `$28` |
| invent / equip / trade | `$0e` / `$10` / `$1c`, town cell | `$3154`; `$5fa0` / `$61f8` / `$63f4` | arrival handler runs; invent refused at a lord without a workshop (inferred) |
| go to | `$02`, any cell | `$6b8e` → `$3888` | group state 5, arrival mode `$1e`, then camp (state 6) on the cell |
| home | `$0a 00 00` | `$6c16` → `$3c08` | group state 7, target the cell of the lead's settlement `34(lead)`, arrival mode `$4c`, camp |
| supply | `$1a`, any cell | `$6d00` → `$390e` | arrival mode `$74`, food dropped |
| attack | `$0c`, cell of the target | `$6c32` → `$4a7a` | `gate_inject.sh` |

`gate_ungated.sh` (52/52, 60M-step arms with a mid snapshot, two runs byte-identical) adds the rest, each
against a same-snapshot control: go to and home as in the table; an alliance with no goods scores
`rel - 2 < 0` and is refused silently (no `$3458`, peace bytes unchanged); an alliance aimed at the player opens panel
`$1a` and YES (`$2a`, `$6dea` → `$34a8`) or NO (`$32`) answer it; invent at a lord with a WorkShop is accepted (lead mode
`$92`, gather kind from posture) but credits nothing in practice, because `$60dc` credits one unit per
`$580a6[side].word8 + 4` deliveries (`+$2000` for kind `$e` and up) and every side's word8 on rand1 is `$53e`..`$1c0a`:
with side 3's word8 poked to 0 the lord's boats go 13 → 23; equip at a lord holding goods takes `goods >> (posture-2)`
and hands them with the carried goods to the men (`pm143/run/rand1_s2.snap`: boats 13 → 10, men holding a boat 1 → 16).
An envoy reaching the player also triggers a bug: `$c706` returns with A0 = 8 and A1 = `$c9f7`, so `$33b0` judges the
offer for side 0 and, with tribute, runs `$34a8(0)` before the player answers (`$580ac` 0 → 8, side 3's bit 0 set) and
consumes the tribute (`../strategy.md` "Diplomacy").

A target can change sides during the walk (a lord defected 0.18M steps before the spy reached
him, and `$3da4` joined the spy to the new owner): the side is checked only at dispatch, so the
harness re-reads the target's owner at arrival. Go to `$02` and home `$0a` are not gated (the AI
issues `$02` itself).

**The local side and the end of a land** (`gate_local.sh`, `gate_retire.sh` + `parse_retire.py`, from `rand1.snap`
against no-poke controls of the same budget). The verdict `$d2c8` judges only the local side (`$57ffe`, side 1 here;
`../strategy.md` "How a land ends"), so a commander that plays to a result plays side 1. Side 1's slot `$5801c` is
already in state 2 on rand1 and no AI writes it: in 200M unaided steps its only writers are `$6a3a`'s per-tick clear
(`$6a52`/`$6a56`), and an injected order adds one write, the dispatch at `$6b46`. Orders run as on an AI side: an
attack `$0c` on side 4's lord 13 at (40,115) runs `$6c32`, `$4a7a`, `$4b80` in the first `$6a3a` pass (control 0 of
each in 30M) and the lord changes owner to side 1; a get men `$08` at own lord 9 leaves group 0 in state 3 with its lead
at the lord in mode `$1c`. A click on the panels while the harness holds the slot, and a side-1 order to a non-captain
group, are not tested.

A `$2e` in side 1's slot ends the land in the same tick: `$6e10` sees state 2 and calls `$d2c8` directly (163,174
steps after rand1's stop; `$71ae` 0 hits). The verdict reads `$57fce` as left by the previous tick's `$d23a`, so the
harness decides from the ratio it observed: with `$57fce` poked to 4 in the same batch the victory routine `$1a4da`
runs, otherwise the defeat routine `$1a5b2` (1 hit each, control 0 `$d2c8` in 50M). Zeroing the captain group's
owner word `$51690` makes `$d23a` post `$2e` itself at `$d25a` and the verdict runs one tick later. Detection: `d2c8`
in a step's `hits` list is exact; from a snapshot, `$57fce` stays frozen at the verdict's value, the menu mode word
`$2df6e` drops from 6 to 0 once the main menu opens (about 8M steps later), and `$51690` stays 0 after a captain loss.
`$3f2a0[land]` is set only by a win and rand1 already holds `$3f2a0[0] = 1`, so it is not a marker on this roll.

On rand1 side 1 counts 30 men against 149 for the others: ratio 0, and ratio 4 needs about 65% of the land's counted
men. Side 3 reaches 4 unaided by 400M steps of the 1G-step run (`pm151/r1`, by the formula; side 1 is not local
there), so a win is reachable on this land but takes most of the map.

**Orders by carrier pigeon** (`pigeon/gate_pigeon.sh` 7/7; code read of `$6ac6`, `$4562`, `$41dc`, `$2776`, `$6822`).
A group's sender word (`$51538 + side*$13c + 124 + 2k`) decides the route: 0 runs the order in the same executor pass,
otherwise `$4562` takes the first free record of the pigeon pool (`$4c112 + 26i`, i = 1..47, shared by all sides; +5
owner, +6 category, +20 the lead it rides to, +23 order type, +24 target) and copies the sender record's owner byte
and position at launch; a full pool drops the order silently. On landing (`$41dc`) a live rider gets the order through
`$6b38` and `$4220` clears the pending word. A second order while one is in flight gets its own pigeon: both land and
run in order, so a replacement takes effect only after the group has started on the first (go to A at 0 then B at 2M:
2.5M steps toward A, then camps at B). Flight is 1.2 to 1.5M steps per 1000 world units from the sender's launch
point (6 deliveries; 26.5M for 18,500 units). When a side's first group dissolves, `$2776` frees every pigeon owned by
that side (`$27c6`), so every order in flight is lost; later launches copy the dead sender's owner byte (0 or below),
the pool loop skips them (`$417a`), and they never fly, even after the sender record is reused, each one holding a
pool record until its rider's group dissolves (`$283a`). The pending word (word 4) is set only by the AI's `$6822`
and cleared only by a landing: under the harness it is stale AI state that neither blocks nor reports an injected
order (p9 in `gate_move.sh`: the AI's own pigeon was freed with its commander, the word stuck at 4 and every order
was dead-sender). The excess executions after side 3's captain died in the LLM run were side 2's orders (26/26
`$6b38` entries). `pigeon/pig.py <snap>` prints each group's route (none, direct, pigeon, never) and its pigeons in
flight. For the policies: do not order a `never` group (the order cannot arrive and leaks a pool record), send once
and wait while a pigeon to the group is in flight, start a stall timer at delivery, and ignore the pending word.
Poking the sender word to 0 would deliver every order at once, but it changes the game's rules, so the harness does
not do it.

**Observation (`observe.py`).** A per-decision JSON summary of a snapshot or RAM image, every
offset cited to its doc section and unproven fields emitted raw: the clock, local side and
selected group; the 160 lord slots (`$4e514`: kind, cell, food, men at home, loyalty, work order,
goods); the 400 building records (`$4f916`: owner, kind, cell, lord, residents); per side the six
groups (`$51538 + $13c*side`: men, state, posture, food, opponent class, target, sender, carried
goods, and the lead's position, mode and health), the command slot, the acting-group word and
the side totals. An opponent-class word outside {0, 2, ..., `$c`} holds an entity offset while
fighting a group. Gates: `gate_observe.py` agrees with `../py/side_dump.py`, `sides.py` and
`group.py` on rand1 and six long-run chunks (1312/1312, 945/945, 4051/4051) and with the `$57fba`
rule (56/56); `gate_ui.py` agrees with the game's own captain (`$9036`) and house (`$95f6`) panels
rendered under callcap (380/380 fields). Settlement residents, build progress and group target,
eat timer and sender are not checked against the UI.

**Act and step.** `act.py`'s `Poker(ram)` emits the REPL pokes to take a slot, select the acting
group and write an order, filling each longword's neighbour bytes from a working copy of RAM (the
slot+4 longword covers the next side's bytes 0 and 1, the acting-word longword the next side's
word); `act.py <snap> gate` reproduces `gate_inject.sh`'s arms byte for byte, and its arm C run
ends in RAM identical to the gate's. The neighbours come from the input snapshot, so the pokes are
valid before the first step only. `step.py <in.snap> <out.snap> <steps> [order.json]` writes and
runs one REPL script and prints the observation of the result.

**The decision loop (`loop.py`).** One persistent emulator (`resume <snap> repl`) driven over stdin/stdout pipes: at
each decision (every `--every` steps, default 5M) it reads observe.py's regions with `m`, builds a `Poker` from that
RAM (so pokes are valid mid-run), asks the policy for actions and writes them `--gap` steps apart (400k: the executor
runs once per tick and clears every slot after dispatch, so each order must be consumed before the next). It steps
with `bp d2c8 <n>`, which runs exactly n steps unless the verdict is reached and gives every chunk a sync line, so a
land end is caught at its step. The REPL prints nothing for `w` and `s`, one line for `m`, and ends on EOF, `q`, an
empty line or an unknown command. Each run writes `decisions.jsonl` (a start record, per decision the step, clock,
observation hash, per-side totals and actions, an `applied` record with the exact `w` lines, an end record with the
reason and the ratio) and `final.snap`; `--replay LOG` re-issues the applied pokes at their steps without a policy.
The loop costs 3 to 7% over plain `s` (three interleaved pairs of 300M steps; a decision read is about 12 ms).
Policies: `scripted` (below), `none` (slot taken, no orders), `llm`.

Gates (`gate_loop.sh`, side 3, 1G steps from rand1; `gate_loop_side1.sh`, side 1): two runs give identical logs and
byte-identical final snapshots, a run reading RAM by `snap` instead of `m` and a replay of the first log give the same
snapshot, and side 1 played to the end of the land twice gives the same log and snapshot (the replay too). On side 1
the land ends by the baseline's own retire at 400.36M steps, a defeat at ratio 0: side 1 has no lord and no man left
from about 400M, and **a captain group with no men does not dissolve**, so its owner word stays 1 and neither `$d23a`'s
captain test nor `$d2c8` fires; without the retire rule the land ran on for 1.6G more steps (one run). The loop retires
on ratio 4 or on a side with no lord and no man.

The scripted baseline (`Scripted`) orders a group when it is alive, has no pending word and is idle (state 0, 1, 6)
or unchanged for 8 decisions, then leaves it 20M steps. In order: a group camped 20 ticks at a target lord that is now
its own follows the AI's `$6762`/`$67d0` chain (after a fight with a lord get food at posture 4, after state 2 get men
at posture 3, after state 3 equip at posture 2, after state `$a` invent at posture 3); a group under 22 men, empty ones
included, gets men at posture 2 from the nearest reachable own lord; a larger one attacks at posture 4 the nearest
reachable enemy lord with fewer than men − 4 at home, or gets food first when short of the trip cost. On the local
side it also provisions, before get men: a group within a cell of an own lord holding 20 food or more takes it while
under 500 food, and a group under 40 meals (`men/8 + 1` each, `$3f6a`) fetches it from the nearest such lord; every
local get food goes at posture 2, which moves the whole store (`$150f2`, `food >> 0`) where posture 4 moves a
quarter, and of the `$6762` chain the local side keeps only get food after a fight and get men at a lord with men at
home (a top-up at home otherwise walked the captain through get men, equip and invent for 80M steps). An AI side's
groups carry about 24,000 food each on land 2, so none of this applies to them, and the side-3 gate runs are
unchanged (`gate_rollout.sh` 20/20 after the change). A posture
order `$16` goes just before the main order when it differs. **Posture is what the first version lacked**: at
posture 2 an attack kills the garrison instead of routing it (`$5590`), including the conquered lord's captain, the
man who would defect and found a new group (`$5c2c` → `$25d6`), so the side never replaced a group. Counting group
creations (`$26d0`) and dissolves (`$28ae`) over 1G steps from rand1: no posture 0 and 3, posture 4 1 and 2, the
game's AI 2 and 2; conquered lords left with no men at home 20M later 11 of 14 against 6 of 21 for the AI. Side 3
lords / men at 1G or at the land end (one run per cell; rand1_s2 is rand1 plus 100M steps, not a separate roll):

| start | game's AI | slot taken, no orders | first baseline | current baseline |
|---|---|---|---|---|
| rand1 | 13/88 (end 676M) | 4/66 | 1/28 | 10/116 (end 600M) |
| k25 | 14/113 | 4/79 | 4/26 | 20/220 (end 747M) |
| k60 | 3/24 | 2/4 | 4/31 | 7/25 |
| rand1_s2 | 13/88 (end 576M) | 5/72 | 13/78 (end 714M) | 12/106 (end 614M) |

Waiting on pigeons in flight and skipping `never` groups gave mixed results against this policy (rand1 8/83, k25
18/153, k60 7/24) and are not in it. The attack margin of 4 still sends about 20-man groups to die at the player's
city, as the game's AI does.

**Movement (`move.py`, `loop.py --move`).** `plan_legs` takes the cells of the A* triangle path in order, keeps those
whose centre samples land, and string-pulls: from the current point (the start, then each leg's centre, where the
walker snaps on arrival) the farthest kept cell whose straight leg passes `Map.leg`, then cells within two of the path
when none does; a plan whose last leg fails is refused rather than issued (2738/2738 land goals 4..24 cells away
behind water got a plan, 1 to 7 legs, `plan_stats`-style count, no emulation). `Mover` sends each leg as a go to
`$02`, the next when the lead stands in the leg cell, the real order from the last leg, and re-plans after 12M
steps without progress (12M more for a pigeon-carried group). A lead holding a Boat (byte 33 = `$0a`) skips the water
probe and goes straight, and on rand1 every AI group's lead holds one (12/12, 13/13, 14/14 men of 2:0, 3:0, 4:0;
drop equipment `$18` empties the carried boats but not the men's), so `prep.py` strips the held boats of named
groups for the test. Gate (`gate_move.sh`, `ab.py`, same snapshot and 120M steps per arm): on 8 pairs where the
straight walk crosses water to a goal on the same land the direct order never arrives and the legs arrive in all 8
(21M to 67M steps, no re-plans; `Map.simulate_walk` called the direct verdict right in 9/9 boat-free pairs);
p10 arrives both ways through the detour sweep; b1 (a boat lead) arrives straight. p9 does not arrive: its group's
pending word stayed set, so the first orders were not taken (open). Two `--move` runs on side 1 over 400M steps are
identical. The Mover does not yet wait on a set pending word.

**Rollouts (`rollout.py`, `loop.py --policy rollout`).** `rollout(snap, side, cands, N)` runs each candidate (an
action list, poked `gap` steps apart after an `m` read, as the loop does) in its own emulator, at most `par` at once,
adds a no-order candidate, and returns per side the lords, men, food, groups, force and the ratio as if local, with
the land-end step. The score is `F/E`, a side's men at home plus group men over the others' plus 1, the unclamped
core of `$d23a`'s ratio (the clamped ratio ties nearly every short-horizon candidate at 0). F is recomputed from the
observation, not read from `$57fba`, which `$d322` rebuilds from zero every tick, so a snapshot can catch it torn
(5 of 800 decision reads). For the local side the score also values the captain, because only the captain group's
loss ends a land against the player: a land end inside the horizon scores 10 + F/E when the ratio read at `$d2c8` is 4
and −1 otherwise, a captain group with owner ≤ 0 scores −1, and otherwise F/E loses 1 × the fraction of the captain's
men lost since the decision and 0.5 when the captain group ends the horizon with men and no food (heuristic weights).
The policy proposes Scripted's orders, none, hold-the-first, and for the first ordered group get men, get food, attack a
lord with fewer men at home than the group (`attack_loose`) and the second-nearest target, scores each over N steps
and issues the best (ties: own lords, then list order); the list is cut at K. On the local side it also forks when
Scripted orders nothing but the captain is idle (at most once per 20M steps) or threatened, with none, the scripted
attack and the same alternatives for the captain; threatened means an enemy group with at least the captain's men
within 16 cells, and then the first alternative is a retreat, a go to `$02` to the reachable own lord farthest from
those groups. Neither addition can fire for an AI side: from rand1, side 3, the gate's 300M-step run ends in the same
snapshot with and without them. It does not combine with `--move`. Forking is exact (`gate_rollout.sh`: five forced
candidates from rand1, and every chosen candidate of a 300M-step run against the loop's own snapshot N steps later,
20/20 `cmp`-equal). An order to a group far from the captain changes nothing but the pigeon's payload for 20M steps
or more, so N must exceed the flight time to score it; at N = 40M 14 of 25 decisions tied.

**The first won land** (`gate_win.sh`). On campaign land 0 (`pm123/win/m1_s0.snap`: side 1 26 men against side 2's 20,
ratio 2) every policy wins as side 1: the scripted baseline sets posture 4, attacks lord 0 at (29,62), sees ratio 4
and retires at 35M steps; `$d2c8` runs with `$57fce` = 4 and the victory routine `$1a4da` follows (the defeat routine
`$1a5b2` 0 hits). With movement and the rollout policy the run is the same to the step; the LLM retires at 40M; with no
orders the land is still at ratio 2 after 1G steps. Two baseline runs give identical logs and snapshots. Land 0 is
the tutorial land, won by one attack, so this proves the loop end to end (orders, verdict, victory) rather than
strength.

**The campaign.** `campaign_next.sh <final.snap> <land>` takes a loop's won `final.snap` (stopped at `$d2c8`) through
the victory routine, Continue Conquest and a click on the next land to its first `$f898` (strategy.md "The
campaign"); from the LLM's land-1 win it builds land 2 (`$3f2a0` = 01 01, `$580a4` = 2) byte-identical to a hand
drive. One run per policy and land, side 1, 2G steps (the LLM 1G, a decision per 20M):

| policy | land 1 (side 1: 1 lord, 21 men; side 3: 5 lords, 90) | land 2 (side 1: 1 lord, 20; side 2: 2 lords, 53; side 3: 7 lords, 70) |
|---|---|---|
| no orders | ratio 0 at 2G | lost at 346M |
| scripted baseline, before provisioning | won at 455M (5 lords, 70 men against 36); same with `--move` | lost at 444M: the captain's food hit 0 at 300M and its men starved 25 → 0 |
| scripted baseline, provisioning only | won at 215M (5 lords, 71 men; captain food never under 200) | lost at 329M: captain food never under 117; side 3 gone by 240M, then the captain, attacking (26,52) at posture 4, met side-2 men and fought from 32 men to 1 |
| scripted baseline | won at 215M, the same final snapshot | lost at 1470M: the field-fight posture fix kept the captain alive through that fight with 4 men, then it sat camped with no lord to recruit from; from five perturbed starts it lost at 213M to 258M ("Land 2 as a rate") |
| LLM | won at 180M, 10 calls, $0.53 (5 lords, 74 men) | lost at 298M, 15 calls: took 4 of side 3's lords, let food reach 0 (40 men to 17), then attacked a town side 2 had just taken |
| rollout, F/E score (K 5, N 40M) | lost at 725M: idle captain starved (food 0 at 450M) with side 1 ahead 57 to 44 | not run |
| rollout, captain score | won at 440M, 24 rollouts | lost at 229M: side 2's 69 men caught the captain; no candidate moved it away |
| rollout, captain score and retreat | won at 440M, the same final snapshot | lost at 460M: survived side 2's sweep by retreating, then starved at home (food 0 at 370M) |
| rollout, captain score, retreat and provisioning | won at 215M, the scripted run's final snapshot | **won at 1120M**, 58 rollouts: the captain still starved from 375M to 550M (30 men → 4), refilled from towns it took, and side 1 ended with 9 lords against side 2's none; a replay of the log (`runs/l2_rollout/decisions.jsonl`) ends byte-identical; from five perturbed starts it lost four and drew one ("Land 2 as a rate") |

Each win runs the victory routine `$1a4da` and each loss the defeat routine `$1a5b2`, 1 hit each. On land 2 the game's
side 2 grows from 2 lords to 8 or 9 in every run, whatever side 1 does. The LLM's land-1 decisions are one plan:
attack the weakest town at posture 4, take its men at posture 2, attack the next, and retire when the ratio reads 4
(`runs/l1_llm/decisions.jsonl`, with its prompts and replies in `llm_io/`; a replay of the log gives the same final
snapshot). The land-1 rollout win turned on the captain terms: at 360M get food scored 1.09 against 0.34 for the
rest (the starve penalty), at 400M the captain's attack 2.64.

Before provisioning, three of the land-2 losses and the old land-1 rollout loss were the captain starving, and not
for want of food: at 150M the retreat run's side 1 held 5 lords with 327 food the captain never took, and side 2
conquered the richest of them (137 food) with its store intact. Provisioning keeps the scripted captain fed on both
lands. The rollout policy still lets it starve: food scores nothing inside a 40M horizon until it reaches 0, so the
rollouts chose an attack over Scripted's get food at 60M, 140M and 190M. A starve term graded from 0 at the 40-meal
reserve to the full 0.5 at no food did not fix it (one run: food 0 at 400M, the captain group at 0 men from 1100M,
which never ends the land) and is not kept. Run records: `scratchpad/cmd3/l{1,2}/<policy>`,
`scratchpad/cmd4/l{1,2}/<policy>` (provisioning; `l2/rollout_g` the graded term).

**Side 2 on land 2, and field-fight posture.** Side 2 is the game's own AI, and with no orders for side 1 it plays one
plan (`scratchpad/cmd5/l2/none`, a snapshot every 25M): its two field groups (20 and 29 men) sweep side 3's lords from
the south, (35,78), (54,77), (41,66), (26,52), (17,41), taking men at each (to 35 and 47), then turn north to side 1's
capital (52,24) and end the land at 346M. An alliance cannot stop this: only `$3154` and the pointer test read the
peace bits, and any contact breaks them (strategy.md "Diplomacy"). What does stop it is destroying the two field
groups, which side 2 did not replace in the one run that destroyed them (why it makes no new group is not checked: it
attacks lords at posture 4, the posture that lets a conquered lord's captain defect, and fights groups at posture 2).
In the land-2 rollout win the captain, at posture 2 left over from a get food,
destroyed side 2's 39-man group between 225M and 245M without losing a man, and its last group (34) at 305M to 315M
(30 men to 18). Side 2 then made no group in the remaining 800M steps and lost its lords one by one.

Posture decides those fights because `$5590` settles a beaten man by the winner's posture: killed at 2, routed home
(where his lord can recruit him again) at 4 (strategy.md "Combat"). The scripted captain fought at posture 4, the
posture of its attack orders. From the scripted run's 300M snapshot, with the captain fighting a side-2 group at
posture 4 (`gate_posture.sh`, replaying `runs/l2_scripted_prov`; 30M steps per arm, one variable): unchanged, 34 kills (`$55f2`) and 34 routs
(`$560a`) and the captain group dissolved; with a posture-2 order to the captain, 49 kills, 4 routs, the captain alive
with 4 men and side 2's group men 36 against 56. `Scripted` now sends that order (marked `fix`, which the rollout
policy prepends to every candidate rather than forking on it) to a local group fighting an enemy group. In the full
scripted run it fires once and the captain survives that fight, but with 4 men and no lord left to recruit from it
then sits camped until the land ends at 1470M (lost). The fix leaves land 1 and the land-2 rollout win
byte-identical (it never fires there). Extending posture 2 to every order given near an enemy group sent 0 fixes and
lost the land-2 rollout run at 1042M (`scratchpad/cmd6`), so it is not kept.

**Land 2 as a rate.** The table above is one run per policy. `seeds.sh` plays each policy from six starts: the land-2
start advanced 0 to 5 million steps with no orders and the slot not taken (`--policy none --no-take`), about 6 ticks
apart, which is enough for every run to diverge. Start 0 is the original start, and each policy's run from it repeats
its table entry to the step (scripted lost at 1,470,123,932; rollout won at 1,120,015,233), so the starts and the
loop are deterministic. Runs: `scratchpad/cmd9/<arm>/o<k>`, starts `cmd9/start/o<k>`.

| policy | won | lost | other |
|---|---|---|---|
| scripted | 0 | 6: o0 at 1470M, o1..o5 at 213M to 258M | |
| scripted `--evade` | 0 | 5: 292M to 730M (o3 by the no-lord retire) | o0 alive at the 2G budget, ratio 1 |
| scripted, pull the captain out of melee (dropped) | 0 | 6, each within 0.5M steps of scripted's | |
| the same and evade posture-2 groups (dropped) | 0 | 6: 224M to 427M | |
| rollout (K 5, N 40M) | 1: o0 at 1120M | 4: 347M to 417M | o3 alive at the 2G budget, ratio 0 |

Of the 27 losses, 24 end the same way: the captain himself is killed, and his group's dissolve posts `$2e` (strategy.md
"How a land ends"); the other three (scripted o0, which the pull-out arm repeats, and evade o3) end by the no-lord
retire. In all 24 the captain's lead has owner -1 and a side-2 group at posture 2 is fighting (state 13); 23 of them
die in melee and one (rollout o5) by two arrows ("How the captain dies"). Traced on
scripted o1 from 212M (`bp 564e`, the `jsr $2776` in `$5590`'s kill tail): A0 is the captain's lead `$52fe8` with
owner `$ff`, category `$0c` and dwell `$a0` (killed, not routed), flags `$10` (leader, not encircled), group word 42 =
`$188` (side 1 group 0), and the attacker's lead is side 2's group 0 at posture 2; the land ends 1.2M steps later.
His army did not lose: it still had 27 men, and in o1 it had already destroyed one of side 2's two groups.

**How the captain dies.** What decides it is whether a healthy enemy man reaches the lead. A lead carries a bow (grade 6 from spawn) and in a
fight stands off shooting: mode `$34`, the shot cool-down. On o1 (`cmd9/o1_health`) the captain's lead was in `$34` at
full health 95 from 190M to 205M; from 208M he was in `$32` on (26,52), the lord he had been ordered to attack, against
side 2's group at posture 2, his health falling 86, 74, 56, 28 a million steps apart, to 0 at 213M. The enemy's
posture only turns a lead beaten in melee from a rout into a kill. The chain that puts him in melee, traced on o1 from
205M (`leadkill/gate_leadkill.sh`, its comment holds the recorded outputs):

- **Every enemy man who can pick the lead does.** When the two groups meet, `$4bc8` (through `$4dae`) gives each side's men class 4
  (hunt a group) aimed at the other's lead, and each man's `$4f68` pick runs `$503c`: it weighs every live, unrouted
  member of the hunted group's roster through `$548a`, then the lead, last. `$548a` skips a man already claimed this
  tick (byte 32 = the tick `$57fed`; the winner is claimed at `$5340`) and accepts one only if the picker holds a bow
  (weapon 6, `$e` or `$10`), a better weapon, at least the candidate's health, or has retry byte 39 = 2. The key it
  keeps for the best candidate is the word D0, whose high byte is the high byte of the candidate's own record offset
  and whose low byte is the last byte the gate compared, not the distance, so every acceptable candidate after the
  first replaces the previous one: the last acceptable candidate in roster order wins, and the lead is weighed last.
  Replaying `$503c`/`$548a` from the state at each of the 64 picks of 205.4M..208.5M (both sides) predicts the game's
  target 64 of 64 (`leadkill/model_pick.py`); the captain's lead was picked 6 times, side 2's lead 4.
- **The gate holds only while the lead's health is the highest.** Byte 39 counts failed picks and is not reset by a
  success, so a man at 2 passes against anyone until his next failure. At 205.9M man `$521a6` (unarmed, health 79,
  byte 39 = 2) picked the lead; poking only his byte 39 to 0 made him pick `$5301a`, and the next pick of the same tick,
  `$5223c` (also 2), took the lead instead and reached him 0.7M steps earlier. Removing one hunter hands the lead to the
  next.
- **A chaser who arrives drags the lead into melee.** The arrival `$15302` engages a target only in a mode up to `$2c`
  or with prev `$3c` and up, which a lead in `$34` is not, but the chaser is now in `$32` himself, and `$1533c` calls
  `$56a6` on any target not in `$32`: the lead is stamped `$32` one melee tick later, at step 1,345,254,840.
- **Melee is a health race the lead loses.** The melee drain is `(weapon < 6 ? weapon : 0) >> 1 + 1` (ai.md, the combat
  block), so an unarmed man and the bow-armed lead both take 1 health per tick, and the lead loses at most the health
  of the men who reach him. Once his health falls below side 2's men (70 to 90), every one of them passes the gate and
  prefers him: the census of side-2 fighters passing against him went from 7 of 40 at 190M to 25 of 30 at 211M
  (`leadkill/census.py`).

**Across the seeds** (`leadkill/gate_standoff.sh`: every land-2 run of "Land 2 as a rate" replayed with the object
array sampled every 100k steps, about 0.6 tick; each replay ends at its logged step with its logged obs_hash, 30 of
30). A sequence is the melees from one the lead enters at health 85 or more up to the next such entry. In all 39
sequences of the 30 runs the lead's loss is at most the summed health of the men he fought, and close to it when they
are few: in the rollout win, at 337M..347M, one man of health 65 took him from 94 to 30, and he was back at 95 by
1003M. Every killing sequence fought 2 to 8 men with 120 to 553 health in all; every survived one at most 150 (evade
o3, 94 to 3 against 5 men, rescued by his own men). What kills the captain is the number of healthy men who reach him
in one fight, not where he stands: the men he fought in the killing sequences picked him from 0 to 4081 units (up to
16 cells; scripted o2 551 to 1356), and the win's 65-health man from 1540 at 330.6M. The 15M-step watch of the win
(`gate_leadkill.sh win`, 315M..330M) caught a lone 3-health man and missed the 65-health fight after it. The odd death
is rollout o5's: the lead never left `$34` and lost 82 = `$52` twice, 95 to 13 at 344.1M and to 0 at 346.1M,
both written at `$5b4c` in the arrow loop `$596a` (ai.md, which tests no flags, so a lead can be shot) and then 0
at `$5594`, the `$5590` kill (watch of `$53014` from `scratchpad/cmd11/arrow/at_343800000.snap`).
Of the 24 deaths, 11 are on a lord's cell (the attack target, or the captain's own capital (52,24) when side 2 came
to it) and 13 in the field.

Arming the captain's men is not a lever on land 2 inside the window where he dies: no lord of any side holds goods at
the land-2 start or at 200M on scripted o1, and the few weapons there are by the long runs' ends (1120M to 2000M) are
mostly side 2's (pikes, bows; five states read, a sample, not a trace).

Moving the lead out does not work. A go to (23,49) or (26,47), 3 to 5 cells away from side 2's men, given while the
lead was still in `$34` before any chaser arrived (`gate_leadkill.sh goto`): he moved about 40 units, was stamped `$32`
0.5M steps later than the control, and ended the 2.6M-step window at health 5 against the control's 83, because a lead
walking in `$10` is engaged by a chaser on arrival (`$15302`'s mode test passes). A go to (`$02`) order to a captain
already in melee is consumed (the slot reads type 0) but the group stays in state 13 and the lead in mode `$32` on the
same cell until he dies (diseng o1, 210M; one case).

The other rules tried all fail as well. Evading groups that outnumber
the captain, or every posture-2 group, only delays the meeting, because side 2's groups march on him and change
posture after their own orders. Field fights are cheap otherwise: no group carries weapons (only the leads hold a
bow, grade 6 from spawn), so men and health decide them, and the captain beat single groups while losing few men.
Recruiting up to the strongest enemy group and attacking a lone group within 4/3 of the captain's men were also
tried, one land-2 run each, and did not help (`scratchpad/cmd8/l2`). The rollout policy wins land 2 at 1 in 6, the
scripted baseline at 0 in 6; the one win is the run in the table above.

**Policies against the game's AI** (side 3 from rand1, one run each, so a signal and not a rate; the land ends when
local side 1's captain is lost):

| policy | side 3 at 300M: lords / force | end of land | side 3 at the end |
|---|---|---|---|
| unpoked (the game's AI) | 8 / 77 | 676M | 13 lords, force 88 |
| slot taken, no orders | 4 / 65 | not by 1G | 4 lords at 1G |
| first scripted baseline | 7 / 54 | not by 1G | 1 lord, force 28 at 1G |
| current scripted baseline | | 600M | 10 lords, 116 men |
| rollout (K 5, N 40M, a decision per 5M) | 12 / 86 | 549M | 13 lords, force 70 |
| LLM (`prompt_system.txt`, sonnet, a decision per 20M) | 12 / 73 | 491M | 13 lords (480M) |

The rollout run took 364 s for 549M steps (246 s in 25 rollout batches); the LLM run 395 s, 25 calls, $1.48, 22
orders, all valid (`scratchpad/cmd2/llm500`, `rollout1g`).

**The LLM policy (`llm.py`, `prompt_system.txt`).** The model is called through Claude Code's headless mode (no API key
on this machine): `claude -p --output-format json --model sonnet --tools "" --system-prompt <digest>
--no-session-persistence --strict-mcp-config --max-budget-usd 1.00`, the observation on stdin, from an empty working
directory; in CLI 2.1.292 `--output-format json` prints a list of events and the reply is the `result` event. The
system prompt is a rules digest written from these docs (order set, posture, eating and desertion, the ratio and the
retire, conquest by settlement residents, the invent throttle, the pigeon delay); the user message is a compact JSON
of the side's groups, its lords and the enemy's (men at home, residents, distance and A* reachability per group) and
visible enemy groups. The reply is strict JSON, `{"orders":[{"group","order","x","y","posture","to_group"}],
"retire","why"}`, validated per order (group alive with no pending word, one order per group, town orders aimed at
the right side's lord, no water centre for go to and supply, reachability for boatless groups) and an invalid order is
dropped with its reason logged. Every prompt, reply and raw CLI output is stored by hash under `<work>/llm/`; backend
`replay:<dir>` answers from such a log. `llm.py selftest` checks parse, validation and replay offline (15/15).
One live run (side 3, rand1, a decision per 20M steps, 200M steps): 10 calls, all valid JSON, 12/12 orders valid,
14.5 s and about $0.06 per call; replaying its log gives the same final snapshot. The model read a lord's men at home
as his defence and attacked a lord it already owned; the prompt now lists residents and splits own and enemy lords
(each fix checked by one or two calls, not by a run). Not yet measured against the game's AI.

## Plan and status

| step | what | proof | status |
|---|---|---|---|
| 1 | Injection gate: an order written into a state-2 slot of an AI side runs like a natural one, and `$6522` issues nothing for that side | `gate_inject.sh` 7/7 (above) | done |
| 2 | A* reachability tool over the terrain planes | sampler port 4128/4128 against `$1648e` (`gate_sampler.py`); the census's 4230 stuck pairs classified (`classify_stuck.py`): 2417 reachable with water on the line, each with a verified waypoint path; one waypoint followed live where the control stays stuck (`live_check.py`) | done |
| 3 | Observe/act harness driving the REPL, scripted baseline commander | observe/act/step built and gated; every player order gated from an AI or the local slot (`gate_orders.sh` 57/57, `gate_ungated.sh` 52/52, `gate_local.sh`); `loop.py` deterministic and replayable, a land played to its verdict on side 1 twice with identical logs and snapshots (`gate_loop.sh`, `gate_loop_side1.sh`) | done |
| 4 | LLM commander | land outcomes against the original AI on the same seeds, sides swapped. Built: `llm.py` policy, one replayed 200M-step run | in progress |
| 5 | State-space forecaster | prediction error against rollouts and against the rule recurrence. Built: exact rollouts (`rollout.py`, `gate_rollout.sh` 20/20) | in progress |

## Files

| file | what |
|---|---|
| `gate_inject.sh` | the injection gate, 7/7 |
| `gate_orders.sh [arm...]` | every player order from side 3's slot, 57/57 (`BUDGET`, `PAR`, `CHECK_ONLY=1`) |
| `observe.py <snap\|ram> [--compact]` | the observation JSON |
| `gate_observe.py`, `gate_ui.py` | observe.py against the older scripts and against the game's panels |
| `gate_ungated.sh [arm...]`, `check_ungated.py` | go to, home, alliance with no goods / at the player (YES, NO), invent, equip: 52/52 |
| `pigeon/pig.py <snap>`, `pigeon/run.py`, `pigeon/bptrace.py`, `pigeon/gate_pigeon.sh` | order routes and pigeons in flight per group; the pigeon trials, 7/7 |
| `gate_local.sh [arm...]` | orders from the local side 1's slot, and its writers over 200M steps |
| `gate_retire.sh [arm...]`, `parse_retire.py` | `$2e` from side 1's slot: win at ratio 4, defeat below, captain loss; the end-of-land markers |
| `gate_cellpt.py` | an order's target cell to the lead's target point (the cell centre), 16/16 |
| `act.py <snap> gate` / `Poker` | order pokes; `gate` prints the injection gate's arms |
| `step.py <in> <out> <steps> [order.json] [--hits a,b] [--watch addr len]` | one decision step |
| `loop.py <work> [--side K] [--budget N] [--every N] [--policy scripted\|none\|llm\|rollout] [--move] [--evade] [--replay LOG] [--snap-at N,...] [--objs EVERY]` | the decision loop; `--objs` samples the object array to `objs.bin` |
| `rollout.py <snap> <cands.json\|-> --side K --steps N`, `gate_rollout.sh` | exact rollouts of candidate orders; fork determinism 20/20 |
| `gate_posture.sh` | field-fight posture: kills against routs from the land-2 300M snapshot, one variable |
| `seeds.sh <out> <snap> <side> "<offsets>" "<arms>" [par] [budget]` | one land played by several policies from starts a few million unpoked steps apart, so an outcome is a rate |
| `leadkill/gate_leadkill.sh [pick] [r39] [goto] [win]` | how an enemy man reaches the captain's lead (scripted o1, `runs/l2_scripted_o1`): the target-pick replay 64/64, the retry-byte poke, the go-to arms; `win` the chases on the rollout win's lead over 315M..330M (`runs/l2_rollout`, about 4 minutes) |
| `leadkill/model_pick.py <out>` | `$503c`/`$548a` replayed from REPL dumps at each `bp 5350`, compared with the game's pick |
| `leadkill/chase_fate.py <watch> [lead]` | each chaser aimed at a lead and what ends the chase (engaged, diverted, re-pick, dead), from a `wfilter.py 46-49` watch |
| `leadkill/gate_standoff.sh [arm/o<k>...]`, `leadkill/standoff.py <run> <start snap> [-v]` | every land-2 seed run replayed with `loop.py --objs 1e5`: per run how the lead died, each melee sequence's loss against the health of the men he fought, arrow hits (`-v`: every chase with its distance, every melee) |
| `leadkill/census.py <snap>...` | side 1's leads and how many side-2 fighters pass `$548a`'s gate against them |
| `runs/l2_rollout/`, `runs/l2_scripted_prov/` | the land-2 rollout win and the scripted run the posture gate replays |
| `move.py <snap> <side> <k> <gx> <gy>`, `ab.py [pair...]`, `prep.py`, `gate_move.sh` | A* legs as go-to orders, the direct-vs-legs gate, boat stripping |
| `gate_win.sh [snap] [loop args]` | side 1 played to a won land (campaign land 0 by default), twice, then the victory routine |
| `campaign_next.sh <final.snap> <land> [out]` | a won land's loop end through Continue Conquest to the next campaign land, built |
| `runstat.py <run dir> ...` | one status line per loop run (last decision, per-side lords and men, groups, end record) |
| `gate_loop.sh [budget]`, `gate_loop_side1.sh [budget]` | loop determinism and replay, side 3 and side 1 |
| `llm.py selftest` / `llm.py prompt <snap> [side]`, `prompt_system.txt` | the LLM policy, its offline test and its prompt |
| `astar.py <snap> x0 y0 x1 y1 [--cells] [--speed N]` | land path as world waypoints, with a verified flag |
| `gate_sampler.py [snap...]` | `tools/pm_fsm_ref.terrain_sample` against `$1648e` under callcap |
| `classify_stuck.py [prefix...]` | the stuck census split into unreachable / water on line / not stuck / boat |
| `walk/` | the per-tick walker from a full record and the census that checks it: `list206.py` → `model206.py` → `census_run.py` (110 game runs) → `census_cmp.py` → `classify_fixed.py`; `trace_cmp.py` for one man, `reset_test.py` for the re-dispatched |
| `live_check.py <snap> <obj> [--chunks N]` | a man's target poked to the first waypoint, against a control |

All write under `$CMD_WORK` (default `scratchpad/cmd1`).

## Known risks

- The walker is right per tick but not yet a forecaster (`walk/`). Started from a man's whole record, `walk/walker.py`
  reproduces the game's position, step, heading, dwell, target, modes and sweep on 245,839 of 245,840 traced ticks of
  the 206 pairs `Map.simulate_walk` got wrong (the one miss is a tick cut by the step budget). Those 206 have four
  causes, none of them the hand-off `$14fa2` (no class b/c man has its flag bit 4): 121 men are re-dispatched by a job
  routine every few dozen ticks (`$15122` → `$34f2` re-summons a get-men recruit to the lord's cell centre on each
  get-men arrival, `$5cde`/`$155ac` send him to a tree, `$3c08`), so the `$48` sweep, which needs 500 to 1140 ticks to
  round the water, never finishes (median gap 19 ticks, max 76); 49 are caught mid-sweep, and the sweep depends on its
  history, which `simulate_walk`'s fresh mode-`$10` start discards; 25 arrive after the census window (one needed
  2085 ticks, model 2115); 11 chase a moving target (a chased entity, or a camp seat that `$4a` rewrites to the
  resting lead's position). From the full record with the observed re-dispatches, class b disagreements fall from
  183 to 11 (all moving targets) and class c stays 0 of 239 (`walk/classify_fixed.py`). A forecaster still has to
  model the job dispatchers, or stop at the next re-dispatch, and simulate the chased entity.
- LLM output is not deterministic: every decision is logged with its tick so a run replays.
- The game's own bugs act on injected orders too: the signed-clock camp stall after about 4.5G
  steps, stuck pending words from dead senders (`../README.md` "Bugs and accidents"). The harness
  detects them rather than scoring them against the commander.
