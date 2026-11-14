# Carrier Command: handoff

Updated 2026-11-14 by the session that ended at commit `26e048f`.

## Resume point

- Last commit of this workstream: `26e048f` carriercommand: Manta airborne autopilot proven per tick, fuel every
  16th frame, landing states read from code.
- Working data: `M68000/scratchpad/carrier/` (rebuild recipe: `reversing/carriercommand/README.md` "Running it"
  and "Snapshots"; `tools/recipe.py` rebuilds the c80 -> c_s30 chain; indexed in `scratchpad/ANCHORS.md`). Manta
  snapshots in `scratchpad/carrier/manta/` (`py/units/manta_snaps.py`); agent notes for this pass in
  `scratchpad/carrier/agents/{fuel,lowalt,landing}/` (records, folded into `vehicles.md` section 5).
- Start from: `scratchpad/carrier/manta/m_air.snap` (Manta 0 airborne, for the land command) or `m_takeoff.snap`
  (first airborne tick). `c_s30.snap` for anything else; apply `w 126c 00ff0001` before runs over about 1G steps.
- Uncommitted work left behind: none.

## Proven so far

Gates: `uv run python tools/gates.py run carriercommand`, 5/5 PASS at `26e048f` (render, economy, target, units,
difficulty).

- Enemy target choice `$2337a`: 1344/1344 score words, 21/21 decisions (`py/ai/gate_score.py`; `ai.md` section 2).
- Missile-site range by difficulty: launches 0/2/0 (`py/ai2/gate_difficulty.sh`; `ai.md` section 6).
- Economy: production 175/175, lines 14/14, landings 4/4, RNG 1/1 (`py/world/gate_economy.sh`; `economy.md`).
- Renderer: sine, rotations, projection, face test, spans; BSP draw order 1264/1264 (`render.md`).
- Vehicles (`py/units/gate_units.sh`; `vehicles.md` sections 1-5): carrier 150/150 and 600/600, atan 529/529, repair
  10/10 and 12/12, flares 5/5, take-off 42/42 twice (controls 11/13), airborne autopilot `$1d354` 300/300, 400/400,
  400/400 (`flight_proof.py`, controls 22/26), fuel 300/300 at full hull and at hull 256 (`fuel_proof.py`).
- Landing states 0 and 4-6, ground contact and runways: read from code only (`vehicles.md` section 5).

## Running

Nothing running. (stserver PID 49135 belongs to another session.)

## Open, in priority order

1. Drive the carrier landing: land command `$11bf6` from `m_air.snap`, state 0 phases 0-4 per tick, then the lift
   stow; a `landing_proof.py` like `flight_proof.py`, promoted into the units gate.
2. Drive a runway touchdown on an airstrip island (record 1 type `$24`; 9 of 64 islands): poke a Manta inside and
   just outside each limit (`vehicles.md` section 5 "Ground contact") and read +28, hull; then states 4-6.
3. Walrus launch (`$1201a`, type 6) and driving, same method.
4. An attack run to capture: `ai/atk2.txt` with the time-bomb poke, round by round against `ai.md` section 4.
5. Drone launcher `$25` and the command centre's missiles: A/B on difficulty.
6. Production priorities and fuel screens (`$22770`, `$228d2`).

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
- Push: master is 4 commits ahead of origin, this handoff included.
- Leftover worktree `.claude/worktrees/agent-a528a4455254d699f` (not this workstream): 7 uncommitted emulator
  files that look like the trace opt-in change already landed as `0c44c77`; check and remove with your OK.

## Next session

1. `/resume carriercommand`; run the five gates.
2. Write `py/units/landing_proof.py`: land command from `m_air.snap`, model state 0 per tick from `vehicles.md`
   section 5 "Landing", until +28 = 1 and the lift stows it.
3. Promote it into `gate_units.sh` with `re:` expects in `gates.toml`; then the runway touchdown (Open 2).
