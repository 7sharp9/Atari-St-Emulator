# Carrier Command: handoff

Updated 2026-11-12 by the session that ended at commit `b8c8312`.

## Resume point

- Last commit of this workstream: `b8c8312` carriercommand: digest launch line carries its proof labels.
- Working data: `M68000/scratchpad/carrier/` (rebuild recipe: `reversing/carriercommand/README.md` "Running it"
  and "Snapshots"; indexed in `scratchpad/ANCHORS.md`). Manta snapshots in `scratchpad/carrier/manta/`, rebuilt by
  `py/units/manta_snaps.py`; meshes in `scratchpad/carrier/mesh/`, rebuilt by `py/render/subdivide.py 5`.
- Start from: `scratchpad/carrier/manta/m_takeoff.snap` (Manta 0's first airborne tick, +28 = 3, from `c_s30` with
  `w 126c 00ff0001` applied). `c_s30.snap` for anything else; apply `w 126c 00ff0001` before runs over about 1G steps.
- Uncommitted work left behind: none.

## Proven so far

Gates: `uv run python tools/gates.py run carriercommand`, 5/5 PASS at `e0f53c9` (render, economy, target, units,
difficulty).

- Enemy target choice `$2337a`: 1344/1344 score words, 21/21 decisions (`py/ai/gate_score.py`; `ai.md` section 2).
- Missile-site range by difficulty, wrap at `$8000`: launches 0/2/0 (`py/ai2/gate_difficulty.sh`; `ai.md` section 6).
- Economy: production 175/175, lines 14/14, landings 4/4, RNG 1/1 (`py/world/gate_economy.sh`; `economy.md`).
- Renderer: sine, rotations, projection, face test, spans (`py/render/gate_render.sh`; `render.md`).
- Vehicles: carrier 150/150 and 600/600, atan 529/529, repair 10/10 and 12/12, flares 5/5, Manta take-off 42/42 at
  rest and 42/42 with the carrier turning, controls 11/13 (`py/units/gate_units.sh`; `vehicles.md` sections 1-5).
- The Manta is model 5; missiles share byte-identical model copies (`render.md` section 6).
- Model 5 subdivided with a fitted cage: silhouette IoU 0.961 worst view against the game polygons (control 0.985)
  (`py/render/subdivide.py 5`; `render.md` section 6).
- Design digest in the README, fact-checked by a fresh-context reviewer.

## Running

Nothing running.

## Open, in priority order

1. Manta airborne flight `$1d354` (+28 = 3): model climb to the target altitude (+34), turn to the destination,
   arrival and circling per tick from `m_takeoff.snap`, as `takeoff_proof.py` does; promote into the units gate.
   Unblocks craft fuel (+10, falls about 1.2 a tick airborne) and terrain following.
2. Walrus launch (`$1201a`, type 6, dock rather than lift) and driving, same method.
3. An attack run to capture: `ai/atk2.txt` with the time-bomb poke, round by round against `ai.md` section 4.
4. Drone launcher `$25` and the command centre's missiles: an enemy island with a `$25`, A/B on difficulty.
5. 3D drawing order: `watch 9de 2` during one model's draw against `py/render/model.py`'s BSP order.
6. Production priorities and fuel screens (`$22770`, `$228d2`).

## Known traps

- The crack's stack leak kills every run about 1.55G steps after `c_s30`; `w 126c 00ff0001` stops it.
- The main frame is not a fixed 72,000 steps once combat is on screen: count ticks with a `bp`, not steps.
- Calling a command handler mid-play: use `StServer.call_resume`, not `call` (which leaves the CPU parked at its
  return address with SR `$2700`). The launch handler refuses while the lift moves (`$dca` nonzero): wait for 0.
- `subdivide.py`'s silhouette IoU needs 600 px: at 200 px the edge-on views cost about 5% from rasterization alone.

## Waiting on Dave

- Emulator fix for mouse input: model the MFP in-service register so a game that lowers its IPL in the ACIA
  handler gets one packet byte per interrupt (README "Running it").
- Optional, low priority: instruction-fetch bus errors build their frame with the data function code and opcode 0
  (`68k.fs` `EnterGroup0Vector`); Hatari uses the program code and the IR.
- Which subdivided Manta to keep for a modern version: fit1 (0.932, softer) or fit2 (0.961, near the original).
- Push: master is ahead of origin by 12 commits, this handoff included.
- Blog: `7sharp9.github.io/IDEAS.md` entry 9 (algorithm infographics, seven Carrier Command candidates) is in an
  untracked file there.

## Next session

1. `/resume carriercommand`; run the five gates.
2. Read the airborne state `$1d354` to its first branch, then the steering and altitude code it calls.
3. Model it per tick from `m_takeoff.snap` (`py/units/manta_snaps.py` rebuilds it), with the carrier at rest and turning.
4. Promote the proof into `gate_units.sh` with labelled `re:` expects.
