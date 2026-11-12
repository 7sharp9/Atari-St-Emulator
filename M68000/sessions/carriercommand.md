# Carrier Command: handoff

Updated 2026-11-12 by the session that ended at commit `29413e4`.

## Resume point

- Last commit of this workstream: `29413e4` carriercommand: vehicles, enemy combat and defences, game modes, the
  crack's stack time bomb.
- Working data: `M68000/scratchpad/carrier/` (rebuild recipe: `reversing/carriercommand/README.md` "Running it"
  and "Snapshots"; indexed in `scratchpad/ANCHORS.md`). The first- and second-wave agent dirs are under
  `scratchpad/carrier/agents/<area>/` with `BRIEF.md`; their final reports were folded into the topic docs and not
  saved as `report.md`.
- Start from: `scratchpad/carrier/c_s30.snap` (Strategy game, carrier at Vulcan). Apply `w 126c 00ff0001` before
  any run longer than about 1G steps (Known traps).
- Uncommitted work left behind: none.

## Proven so far

Gates: `uv run python tools/gates.py run carriercommand`, 5/5 PASS at `29413e4`.

- Enemy target choice `$2337a`: 1344/1344 score words, 21/21 decisions, ten of eleven constants load-bearing
  (`py/ai/gate_score.py`; `ai.md` section 2).
- Missile-site range set by difficulty, signed-compare wrap at `$8000`: launches 0/2/0 at 0/`$6000`/`$c000`
  (`py/ai2/gate_difficulty.sh`; `ai.md` section 6). Combat states 10/11 driven state by state (`ai.md` section 5).
- Economy: production 175/175, line cost and steps 14/14 each, packet landings 4/4, RNG 1/1
  (`py/world/gate_economy.sh`; `economy.md` sections 2, 4).
- Renderer: sine 4096/4096, rotations 360/360 and 120/120, projection 480/480, face test 120/120, spans 780/780
  (`py/render/gate_render.sh`; `render.md`).
- Vehicles: carrier 150/150 and 600/600 ticks (1950/1950 full), arctangent 529/529, repair 10/10 and 12/12,
  flares 5/5 (`py/units/gate_units.sh`; `vehicles.md`).
- The 640M-step double bus fault is the crack's protection stack leak, not the emulator (README "Provenance").
- Packer: `LSD!` in-place depack, minimum gap 218 bytes on six files (`py/autopack_depack.py --gap`; `packer.md`).

## Running

Nothing running.

## Open, in priority order

1. Launch a Manta and a Walrus (drive the launch UI from `c_s30`, or poke a slot to state 3 with a destination),
   snapshot them in flight, then model their flight and driving the way `carrier_proof.py` does (per-tick match
   count over a few hundred ticks). Unblocks craft fuel, terrain following and the command-centre missiles.
2. An attack run to capture: `ai/atk2.txt` held state 3 for 144M steps; run longer with the time-bomb poke and
   check the round formula of `ai.md` section 4 against the structure HP watch, round by round.
3. Drone launcher `$25` and the command centre's missiles: find an enemy island with a `$25` (census the structure
   blocks), put the player carrier in range, A/B on difficulty as `gate_difficulty.sh` does.
4. 3D drawing order: `watch 9de 2` during one model's draw against `py/render/model.py`'s BSP order.
5. Production priorities and fuel screens (`$22770`, `$228d2`, "Set Fuel Priorities"): click them and diff.

## Known traps

- The crack's stack leak kills every run about 1.55G steps after `c_s30`; `w 126c 00ff0001` stops it (README
  "Provenance"). Snapshots after the halt (`agents/ai/nat/d3..d6`) are dead states.
- The main frame is not a fixed 72,000 steps once combat is on screen (48,000 to 72,000): count ticks with `bp`
  on `$1ac8c`, not steps.

## Waiting on Dave

- Emulator fix for mouse input: model the MFP in-service register (software end-of-interrupt mode), so a game
  that lowers its IPL in the ACIA handler gets one packet byte per interrupt. Its own change behind the
  regression net; `drive.txt` would then work with plain `mouse move`.
- Optional, low priority: instruction-fetch bus errors build their frame with the data function code and opcode
  0 (`68k.fs` `EnterGroup0Vector`, line ~1447); Hatari uses the program code and the IR.
- Push: master is ahead of origin by the commits of this session.

## Next session

1. `/resume carriercommand`; check `scratchpad/carrier/c_s30.snap` and the disk exist, then run the five gates.
2. Pick Open item 1: read the launch command path (`$1201a` Walrus launch, Manta launch near it) and get a craft
   airborne in a snapshot.
3. Model the craft per tick against the emulator; promote the script into `py/units/` with a gate.
