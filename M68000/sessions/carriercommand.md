# Carrier Command: handoff

Updated 2026-11-14 by the session that ended at the commit after `fcd1b5f`.

## Resume point

- Last work commits: `201db69` runway touchdown and taxi, `912de8c` runway take-off and the hidden keys, `bf45541`
  the hidden gate, `fcd1b5f` the Walrus.
- Working data: `M68000/scratchpad/carrier/` (rebuild recipe: `reversing/carriercommand/README.md` "Running it"
  and "Snapshots"; `tools/recipe.py` rebuilds the c80 -> c_s30 chain; indexed in `scratchpad/ANCHORS.md`). Manta
  snapshots in `scratchpad/carrier/manta/` (`py/units/manta_snaps.py`); agent notes in
  `scratchpad/carrier/agents/{fuel,lowalt,landing}/` (records, folded into `vehicles.md` section 5).
- Start from: `scratchpad/carrier/manta/m_air.snap` (Manta 0 airborne, about 4,000 from the carrier) or
  `m_takeoff.snap` (first airborne tick). `c_s30.snap` for anything else; apply `w 126c 00ff0001` before runs over about 1G steps.
- Uncommitted work left behind: none.

## Proven so far

Gates: `uv run python tools/gates.py run carriercommand`, 6/6 PASS (render, economy, target, units, difficulty at
`201db69`+, hidden after `912de8c`) (render, economy, target, units,
difficulty).

- Enemy target choice `$2337a`: 1344/1344 score words, 21/21 decisions (`py/ai/gate_score.py`; `ai.md` section 2).
- Missile-site range by difficulty: launches 0/2/0 (`py/ai2/gate_difficulty.sh`; `ai.md` section 6).
- Economy: production 175/175, lines 14/14, landings 4/4, RNG 1/1 (`py/world/gate_economy.sh`; `economy.md`).
- Renderer: sine, rotations, projection, face test, spans; BSP draw order 1264/1264 (`render.md`).
- Vehicles (`py/units/gate_units.sh`; `vehicles.md` sections 1-5): carrier 150/150 and 600/600, atan 529/529, repair
  10/10 and 12/12, flares 5/5, take-off 42/42 twice (controls 11/13), airborne autopilot `$1d354` 300/300, 400/400,
  400/400 (`flight_proof.py`, controls 22/26), fuel 300/300 at full hull and at hull 256 (`fuel_proof.py`).
- Deck landing (state 0, phases 0-4, `$1cfc2`): 250/250 carrier at rest, 400/400 carrier turning, 500/500 from
  12,000 out, controls 23/32 (`landing_proof.py`; `vehicles.md` section 5 "Deck landing"). The stow is the player's
  lift-down `$11f3c`: hangar after 11 ticks, lift at rest after 21 (`--stow`, a record).
- Runway touchdown window 23/23 cases either side of every limit on VULCAN's airstrip; taxi and parking 399/399 and
  449/449 (controls 15/22, incl. the `$1d53e` clr.w side effect); runway take-off 159/159 (11/14)
  (`runway_proof.py`; `vehicles.md` section 5). Airstrips: only the nine starting bases.
- Hidden keys Ctrl+V, Alt+Help, Ctrl+S/Q; cheat keypad 6 (colour card), 7 (fast-forward), 8 (frame meter); the
  disabled "Andy's exception handler" (`py/curio/hidden.py`, hidden gate; README "Hidden keys and leftovers", `ai.md`
  section 7). Agent record: `scratchpad/carrier/agents/curio/report.md`.
- Walrus launch, cruise, dock and stow 428/428 (carrier at rest), launch and cruise 900/900 (carrier turning), controls
  20/31 (`walrus_proof.py`; `vehicles.md` section 5 "Walrus"). Collisions `$1bb4e` read from code, seen once.

## Running

Nothing running. (stserver PID 49135 belongs to another session.)

## Open, in priority order

1. The Walrus on land and in the coast band (`$1e224`): drive one onto VULCAN (island box edge 12,000 from the
   carrier in `c_s30`) and model the land limits; its turret (bits 5 and 6, entity +38); a collision as a record
   with its own control.
2. The lift's motion `$1e838` up and down, per tick (`landing_proof.py --stow` prints the descent: 163, 147, ... 20).
3. An attack run to capture: `ai/atk2.txt` with the time-bomb poke, round by round against `ai.md` section 4.
4. Drone launcher `$25` and the command centre's missiles: A/B on difficulty.
5. Production priorities and fuel screens (`$22770`, `$228d2`).
6. Curiosity leads not yet proven (agent record above): the debug dump `$14048`, view 33 (`$15978`, a model viewer?),
   the dead-code candidates `$3dbc`, `$1f7e4`, `$1e462`, `$1ecb6`, `$2119e`, `$19e1c` (need a hits census), what
   `$118e` counts in the frame meter, the save format driven through the game's own save screen.

## Known traps

- The crack's stack leak kills every run about 1.55G steps after `c_s30`; `w 126c 00ff0001` stops it.
- The main frame is not a fixed 72,000 steps once combat is on screen: count ticks with a `bp`, not steps.
- Calling a command handler mid-play: use `StServer.call_resume`, not `call`. The launch handler refuses while the
  lift moves (`$dca` nonzero).
- `subdivide.py`'s silhouette IoU needs 600 px.
- The `.asm` listing shows inline jump tables and strings as junk instructions (`$1d4cc`, `$1d4ac`, `$1d6a8`):
  decode them from the RAM image.

## Waiting on Dave

- Emulator fix for mouse input: model the MFP in-service register (README "Running it").
- Optional: instruction-fetch bus error frame (`68k.fs` `EnterGroup0Vector`) uses the data function code.
- Which subdivided Manta to keep: fit1 (0.932) or fit2 (0.961).
- Push: master is ahead of origin by this session's commits (landing, runway, hidden keys, handoffs).
- Leftover worktree `.claude/worktrees/agent-a528a4455254d699f` (not this workstream): 7 uncommitted emulator
  files that look like the trace opt-in change already landed as `0c44c77`; check and remove with your OK.

## Next session

1. `/resume carriercommand`; run the six gates.
2. Walrus on land (Open 1): `walrus_proof.py` with a destination poked onto VULCAN, model `$1e224` and the land
   speed limits; promote into the units gate.
3. Infographic candidates for the blog list (7sharp9.github.io IDEAS.md entry 9, owned by the blog workstream):
   the deck-landing script, the tagged exception vectors, the XOR-keyed manual words, the Walrus dock.
