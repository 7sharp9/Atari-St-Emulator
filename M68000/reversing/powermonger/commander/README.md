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
- **Movement tool (A*).** The game has no pathfinding: a lead walks straight at its target and
  sticks at a shore (`../README.md` "No pathfinding", `../ai.md` mode `$48`). A* over the terrain
  bytes (`$438ee`, with the `$418ad` half; water is 0 to `$1648e`) answers "is this cell
  land-reachable from this group, and how far" and returns waypoint cells, each a straight leg
  the game's walker can complete. The commander issues one move order per waypoint.
- **Forecaster.** First exact rollouts: the game is deterministic (`../strategy.md` "RNG and
  determinism"), so snapshot, inject a candidate order, run N ticks and read the outcome. One sim
  pass is about 177k steps, so a 1000-tick lookahead is about 177M steps (minutes on this machine):
  enough for a few candidates at a major decision, too slow for search. A state-space model over
  per-side aggregates (men, food, loyalty pressure) trained on the rollout traces comes second,
  judged against the rollouts and against a hand-written recurrence of the proven rules.

**Action interface: the command buffer.** Each side has a 6-byte slot at `$58016 + 6*side`
(byte 0 commander, byte 1 order type, word 2 parameter, byte 4 slot state; `../strategy.md`
"`$58016` — command buffer"). The executor `$6a3a` runs slots 1..4 in states 2 and 4, and the
commander AI `$6522` issues a new order only in state 4. Setting a side's slot to state 2 should
therefore silence its built-in AI and leave the slot to the harness, with no UI clicks. Orders to
a subordinate captain still go through `$6822`'s queued-order header and the pigeon, as the
game's own do. Not yet proven: this is gate 1 below.

**Observation.** A per-decision JSON summary read from RAM: lords (`$4e514`, 32 bytes, side byte
0), settlements, groups (the structure-of-arrays record `$51538`, `../strategy.md` "group-order
table": owner, men, state, food, posture, opponent class), loyalty pressure, and enemy positions.

## Plan and status

| step | what | proof | status |
|---|---|---|---|
| 1 | Injection gate: an order written into a state-2 slot of an AI side runs like a natural one, and `$6522` issues nothing for that side | same-snapshot control with the slot left at 4; `hits` on `$6822` (by side), `$6b38`, the handler; the group's state after | open |
| 2 | A* reachability tool over the terrain planes | checked against the stuck census (`../py/fsm/stuck_census.py`): stuck men split into unreachable (island) and reachable-but-walker-fails | open |
| 3 | Observe/act harness driving the REPL, scripted baseline commander | a land played to a result with every decision logged and replayable | open |
| 4 | LLM commander | land outcomes against the original AI on the same seeds, sides swapped | open |
| 5 | State-space forecaster | prediction error against rollouts and against the rule recurrence | open |

## Known risks

- LLM output is not deterministic: every decision is logged with its tick so a run replays.
- The game's own bugs act on injected orders too: the signed-clock camp stall after about 4.5G
  steps, stuck pending words from dead senders (`../README.md` "Bugs and accidents"). The harness
  detects them rather than scoring them against the commander.
