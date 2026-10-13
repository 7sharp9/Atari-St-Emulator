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
- **Forecaster.** First exact rollouts: the game is deterministic (`../strategy.md` "RNG and
  determinism"), so snapshot, inject a candidate order, run N ticks and read the outcome. One sim
  pass is about 177k steps and the emulator runs about 10M steps in 2.4 s (`step.py`, startup
  included), so a 1000-tick lookahead (177M steps) costs about 45 s: a handful of candidates per
  major decision, run in parallel, but still too slow for tree search. A state-space model over
  per-side aggregates (men, food, loyalty pressure) trained on the rollout traces comes second,
  judged against the rollouts and against a hand-written recurrence of the proven rules.

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
or unchanged for 8 decisions, then leaves it 20M steps (an injected order sets no pending word): get men `$08` at the
nearest reachable own lord when under 22 men, get food `$06` when food is short of the `$68ee` trip cost, else attack
`$0c` the nearest reachable enemy lord with fewer than men − 4 at home. It is weaker than the game's AI: after 1G
steps on side 3 it holds 1 lord, 28 men at home and no group, against 4 lords and 60 group men with the slot taken
and no orders, and 13 lords unpoked (one run each, this seed).

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
| 5 | State-space forecaster | prediction error against rollouts and against the rule recurrence | open |

## Files

| file | what |
|---|---|
| `gate_inject.sh` | the injection gate, 7/7 |
| `gate_orders.sh [arm...]` | every player order from side 3's slot, 57/57 (`BUDGET`, `PAR`, `CHECK_ONLY=1`) |
| `observe.py <snap\|ram> [--compact]` | the observation JSON |
| `gate_observe.py`, `gate_ui.py` | observe.py against the older scripts and against the game's panels |
| `gate_ungated.sh [arm...]`, `check_ungated.py` | go to, home, alliance with no goods / at the player (YES, NO), invent, equip: 52/52 |
| `gate_local.sh [arm...]` | orders from the local side 1's slot, and its writers over 200M steps |
| `gate_retire.sh [arm...]`, `parse_retire.py` | `$2e` from side 1's slot: win at ratio 4, defeat below, captain loss; the end-of-land markers |
| `gate_cellpt.py` | an order's target cell to the lead's target point (the cell centre), 16/16 |
| `act.py <snap> gate` / `Poker` | order pokes; `gate` prints the injection gate's arms |
| `step.py <in> <out> <steps> [order.json] [--hits a,b] [--watch addr len]` | one decision step |
| `loop.py <work> [--side K] [--budget N] [--every N] [--policy scripted\|none\|llm] [--replay LOG]` | the decision loop |
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
