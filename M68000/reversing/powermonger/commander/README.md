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
| invent / equip / trade | `$0e` / `$10` / `$1c`, town cell | `$3154`; `$5fa0` / `$61f8` / `$63f4` | arrival handler runs (invent refused at a lord without a workshop, inferred) |
| supply | `$1a`, any cell | `$6d00` → `$390e` | arrival mode `$74`, food dropped |
| attack | `$0c`, cell of the target | `$6c32` → `$4a7a` | `gate_inject.sh` |

A target can change sides during the walk (a lord defected 0.18M steps before the spy reached
him, and `$3da4` joined the spy to the new owner): the side is checked only at dispatch, so the
harness re-reads the target's owner at arrival. Go to `$02` and home `$0a` are not gated (the AI
issues `$02` itself).

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

## Plan and status

| step | what | proof | status |
|---|---|---|---|
| 1 | Injection gate: an order written into a state-2 slot of an AI side runs like a natural one, and `$6522` issues nothing for that side | `gate_inject.sh` 7/7 (above) | done |
| 2 | A* reachability tool over the terrain planes | sampler port 4128/4128 against `$1648e` (`gate_sampler.py`); the census's 4230 stuck pairs classified (`classify_stuck.py`): 2417 reachable with water on the line, each with a verified waypoint path; one waypoint followed live where the control stays stuck (`live_check.py`) | done |
| 3 | Observe/act harness driving the REPL, scripted baseline commander | observe/act/step built and gated (above); every player order gated from an AI slot (`gate_orders.sh` 57/57). Open: the decision loop and scripted baseline, a land played to a result with every decision logged and replayable | in progress |
| 4 | LLM commander | land outcomes against the original AI on the same seeds, sides swapped | open |
| 5 | State-space forecaster | prediction error against rollouts and against the rule recurrence | open |

## Files

| file | what |
|---|---|
| `gate_inject.sh` | the injection gate, 7/7 |
| `gate_orders.sh [arm...]` | every player order from side 3's slot, 57/57 (`BUDGET`, `PAR`, `CHECK_ONLY=1`) |
| `observe.py <snap\|ram> [--compact]` | the observation JSON |
| `gate_observe.py`, `gate_ui.py` | observe.py against the older scripts and against the game's panels |
| `act.py <snap> gate` / `Poker` | order pokes; `gate` prints the injection gate's arms |
| `step.py <in> <out> <steps> [order.json] [--hits a,b] [--watch addr len]` | one decision step |
| `astar.py <snap> x0 y0 x1 y1 [--cells] [--speed N]` | land path as world waypoints, with a verified flag |
| `gate_sampler.py [snap...]` | `tools/pm_fsm_ref.terrain_sample` against `$1648e` under callcap |
| `classify_stuck.py [prefix...]` | the stuck census split into unreachable / water on line / not stuck / boat |
| `live_check.py <snap> <obj> [--chunks N]` | a man's target poked to the first waypoint, against a control |

All write under `$CMD_WORK` (default `scratchpad/cmd1`).

## Known risks

- The walker model (`Map.simulate_walk`) is not yet a forecaster: for 206 stuck pairs it predicts
  arrival through the `$48` sweep where the game stays stuck (121 of them side 4's prev-mode `$14`
  men on k143). Group hand-off (`$14fa2`) and followers are not modelled. `Map.leg`, which only
  rejects legs, is what the path search uses.
- LLM output is not deterministic: every decision is logged with its tick so a run replays.
- The game's own bugs act on injected orders too: the signed-clock camp stall after about 4.5G
  steps, stuck pending words from dead senders (`../README.md` "Bugs and accidents"). The harness
  detects them rather than scoring them against the commander.
