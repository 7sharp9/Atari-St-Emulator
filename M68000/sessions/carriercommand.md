# Carrier Command: handoff

Updated 2026-11-14 by an overseer session that promoted a subagent's leftovers pass (commit `06754e9`).

## Resume point

- Last commit of this workstream: `06754e9` carriercommand: leftovers settled (before it: `d6d7d69` README cites the
  cold-boot hits command for the Alt+Help message; work: `f3910d8` deck landing, `201db69` runway, `912de8c` runway take-off and hidden keys,
  `bf45541` hidden gate, `fcd1b5f` Walrus).
- Working data: `M68000/scratchpad/carrier/` (rebuild recipe: `reversing/carriercommand/README.md` "Running it"
  and "Snapshots"; `tools/recipe.py` rebuilds the c80 -> c_s30 chain; indexed in `scratchpad/ANCHORS.md`). Manta
  snapshots in `scratchpad/carrier/manta/` (`py/units/manta_snaps.py`); hidden-key PNGs in `scratchpad/carrier/curio/`
  (`py/curio/hidden.py keys`); the curiosity agent's record in `scratchpad/carrier/agents/curio/report.md`.
- Start from: `c_s30.snap` (Walrus 0 in its hangar, selected; the Walrus runs launch from it), `manta/m_air.snap`
  (Manta 0 airborne near VULCAN, for landings and the runway). Apply `w 126c 00ff0001` first.
- Uncommitted work left behind: none.

## Proven so far

Gates: `uv run python tools/gates.py run carriercommand`, 7/7 PASS (render, economy, target, units, difficulty,
hidden, leftovers) at `06754e9`.

- Enemy target choice, missile-site range, economy, renderer: unchanged (`ai.md`, `economy.md`, `render.md`).
- Carrier, atan, repair, flares, Manta take-off, flight, fuel: unchanged (`vehicles.md` proof table).
- Manta deck landing 250/250, 400/400, 500/500, controls 23/32; stow by the lift-down command `$11f3c`
  (`landing_proof.py`; `vehicles.md` section 5 "Deck landing").
- Runway touchdown window 23/23 cases; taxi and parking 399/399, 449/449 (15/22); runway take-off 159/159 (11/14)
  (`runway_proof.py`; section 5). Airstrips only on the nine starting bases.
- Walrus launch, cruise, dock, stow 428/428 at rest; 900/900 carrier turning; controls 20/31 (`walrus_proof.py`;
  section 5 "Walrus").
- Hidden keys (Ctrl+V, Alt+Help, Ctrl+S/Q), cheat keypad 6/7/8, the disabled "Andy's exception handler": 11 trials
  against no-key controls (`py/curio/hidden.py`; README "Hidden keys and leftovers", `ai.md` section 7).
- Leftovers (`py/curio/leftovers.py`, gate `leftovers`; README "Hidden keys and leftovers"): view 33 `$15978` is the
  title screen's 3D view (54 arrivals in 3M steps from `c_eng.snap`, main loop `$3a04` 0); with the cheat flag `$1185`
  poked, keypad + and - step the model type `$64d12` 1 to 2 and 1 to 73 (1/1 each, no-cheat control stays 1).
  `$118e` counts models drawn per frame, 6/6 windows, broken control 0/6. `$14048` is an economy debug print with no
  reference in the image, shown by poking view 0's table entry (`debug_dump.png`). Forced calls: `$3dbc` spawns a
  type-`$21` aircraft at (5000, 500, -10000) against an all-zero control, `$1e462` is a hull-damage helper 2/2.
  "Unreferenced" rests on static scans plus an idle 16-snapshot census, not a proof. `$1f7e4` and `$1ecb6` are live
  code behind the inline string "Bomb dropped." and an inline sound word.

## Running

Nothing running.

## Open, in priority order

1. Walrus on land and in the coast band (`$1e224`): poke a destination onto VULCAN (island box edge 12,000 from the
   carrier in `c_s30`), extend `walrus_proof.py` to the land speed limits and the coast path; a collision as a record
   with its own control. Unblocks island assaults (item 3).
2. The lift's motion `$1e838` up and down, per tick (`landing_proof.py --stow` prints the descent: 163, 147, ... 20).
3. An attack run to capture: `ai/atk2.txt` with the time-bomb poke, round by round against `ai.md` section 4.
4. Drone launcher `$25` and the command centre's missiles: A/B on difficulty.
5. Production priorities and fuel screens (`$22770`, `$228d2`).
6. Leftovers still open: how the shipped title selects slot 5 (no button record does: `watch` the `$718`/`$722`
   writers from a cold boot); whether the cheat flag `$1185` survives to the title (set it in play, return to the
   title, press keypad +); reach `$1f7e4` (Manta bomb release through `$1cc76`) and `$1ecb6` (carrier fire-key exit)
   by driving a bomb drop and a fire key under `hits` with a control; the forced call of `$2119e` (FDC Read Track into
   the noise table) sticks at `$201d0`: an unmodelled Read Track or the crack's stale FDC state; the save format
   driven through the save screen.

## Known traps

- The crack's stack leak kills every run about 1.55G steps after `c_s30`; `w 126c 00ff0001` stops it.
- The main frame is not a fixed 72,000 steps once combat is on screen: count ticks with a `bp`, not steps.
- Calling a command handler mid-play: `StServer.call_resume`, not `call`. Launch refuses while the lift moves.
- `all.asm` shows inline jump tables and strings as junk (`$1d4cc`, `$1ddda`, `$1dff2`): dump the RAM with
  `ccpaths.ram(snap)` to a file and use `tools/disassemble.py --rom <file> --base 0 --all <lo> <hi>`, reading the
  longword tables from the bytes.
- `st`/`sf` on a word variable write one byte (`st $de2.w` leaves `$de2` = `$ff00`): read the field at its width.
- Walrus docking tests with the carrier reversing (`644=00400000 648=00300000` gives speed -32) run the Walrus down
  (2000 hull a bump, `$1bb4e`): use the carrier at rest for docking.
- `subdivide.py`'s silhouette IoU needs 600 px.
- A plain `call_resume` of a drawing routine (`$14048`) draws into the back buffer: poke a view-table entry so the
  game's own flip shows it.
- The listing decodes inline strings and sound words as code, so a "dead" candidate can be a live branch target
  (`$1f7e4`, `$1ecb6`): read the bytes first. The idle 100M census runs the main loop but no combat, bombs or sound.

## Waiting on Dave

- Push: master is ahead of origin by this session's commits (`git rev-list --count origin/master..master`).
- Leftover worktree `.claude/worktrees/agent-a528a4455254d699f` (not this workstream): 7 uncommitted emulator files
  that look like the trace opt-in change already landed as `0c44c77`; check and remove with your OK.
- Emulator fix for mouse input: model the MFP in-service register (README "Running it").
- Optional: instruction-fetch bus error frame (`68k.fs` `EnterGroup0Vector`) uses the data function code.
- Which subdivided Manta to keep: fit1 (0.932) or fit2 (0.961).
- Infographic candidates for 7sharp9.github.io IDEAS.md entry 9 (blog workstream's file): the deck-landing script,
  the tagged exception vectors, the XOR-keyed manual words, the Walrus dock.

## Next session

1. `/resume carriercommand`; run the six gates.
2. Walrus on land (Open 1): `walrus_proof.py` with a destination poked onto VULCAN; model `$1e224` and the land
   limits; promote into the units gate.
3. Then the lift's motion (Open 2) with `landing_proof.py --stow` as the driver.
