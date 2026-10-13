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

**Observation.** A per-decision JSON summary read from RAM: lords (`$4e514`, 32 bytes, side byte
0), settlements, groups (the structure-of-arrays record `$51538`, `../strategy.md` "group-order
table": owner, men, state, food, posture, opponent class), loyalty pressure, and enemy positions.

## Plan and status

| step | what | proof | status |
|---|---|---|---|
| 1 | Injection gate: an order written into a state-2 slot of an AI side runs like a natural one, and `$6522` issues nothing for that side | `gate_inject.sh` 7/7 (above) | done |
| 2 | A* reachability tool over the terrain planes | checked against the stuck census (`../py/fsm/stuck_census.py`): stuck men split into unreachable (island) and reachable-but-walker-fails | open |
| 3 | Observe/act harness driving the REPL, scripted baseline commander | a land played to a result with every decision logged and replayable | open |
| 4 | LLM commander | land outcomes against the original AI on the same seeds, sides swapped | open |
| 5 | State-space forecaster | prediction error against rollouts and against the rule recurrence | open |

## Known risks

- LLM output is not deterministic: every decision is logged with its tick so a run replays.
- The game's own bugs act on injected orders too: the signed-clock camp stall after about 4.5G
  steps, stuck pending words from dead senders (`../README.md` "Bugs and accidents"). The harness
  detects them rather than scoring them against the commander.
