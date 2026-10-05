# py/objects: pool 8 objects, the fire bottle and fire, pool 6 weapons

Scripts behind `placement.md` "Pool 8 kinds", `ai.md` "The bottle and the fire" and the weapon text of `player.md`/`frame.md`. Static readers work on
`scratchpad/finalfight/ff_main.bin`; the live scripts run MAME (no `-debug`) through `run.sh` with the harness `sp.lua`. Roots come from `__file__` or `M68000_ROOT` (this directory
must stay four levels below `M68000/`). Python needs numpy and Pillow for `hidediff.py` and `gates_check.py`: `M68000/.venv/bin/python`.
MAME run directory `FFA_RUN` (default `scratchpad/finalfight/objects/run`, screenshots in its `snap/`), logs `FFA_OUT` (default `scratchpad/finalfight/objects/out`); two runs must not share them.
States `sb_boss`, `sb_s1`, `sb_s6` are copied from `scratchpad/finalfight/stage/run/sta/ffightuc/` (regenerate with `py/stage/run.sh`). Every run loads a state without `-debug`.

`sp.lua` is configured by `FFA_*` environment variables (header of the file): `FFA_LOAD` state, `FFA_SPAWNS` (`rel:pool:kind:b20:b21:x:y[:b54[:b98[:b96]]]`, popped through the real allocator
bookkeeping of the pool: 2, 4, 6, 8, a, 12), `FFA_POKES`, `FFA_PIN`, `FFA_HOLD`/`FFA_HOLDA` (per-frame writes), `FFA_SWEEP`/`FFA_LIMIT`/`FFA_KILLALL` (walk player 1 through an area),
`FFA_HIDE` (zero a record's in-use byte: a hide test), `FFA_GFX` (hash of gfx RAM regions), `FFA_WATCH` (byte or word changes), `FFA_SHOT`, `FFA_PLAN2` (inputs). The log has one `F` line per
frame, `R <pool> <addr> <192 bytes>` when a record changed, `X` when it was freed, `G`/`B` for gfx and watch changes.

## Scripts

| file | what it does / proves |
|---|---|
| `run.sh <script.lua>` | headless MAME on `ffightuc` with its own run directory (`FFA_DEBUG=1` adds `-debug -debugger none`); `env.sh` sets `$root`, `$out`, `$run`, `$py` for the shell scripts |
| `sp.lua` | the harness above |
| `tl.py <log> [pools]`, `hist8.py <log> [pool] [from]` | change timeline of the live records; per-record state histogram (kind, `+20`, frames per `state.mode.step`) |
| `fire_run.sh <tag> <player dx> [fighter dx\|none] [start rel]` | hand-spawned fire (pool `$a` kind `$10`) at x `$1c0`, player 1 pinned at fire.x + dx, optional Bred pinned at fire.x + fdx; `fire_check.py` prints the schedule and every hp fall; `fire_overlap.py` replays `$7932` on the ROM box rows against Cody's hurt box; `fire_fighter.py` and `fire_phase.py` check the `$639e` 2-in-8 sampling model against fighter hits |
| `bottle_run.sh <tag> <spawn rel> <x off>` | a kind 8 thrower spawned through the tag-2 allocator; `bottle_check.py` prints the bottle's states (release, landing, free), the fire and Cody's hp falls |
| `bottle_hit_run.sh <tag> <press rel>`, `deflect_run.sh <tag> <dx> <height>`, `deflect_check.py` | Button 1 pressed while the natural bottle is in flight, or at a hovering hand-spawned bottle: deflection (`74 = 1`, +2,000, no fire) |
| `pick_run.sh <tag> <kind>`, `pick_check.py` | a pool 6 weapon at the player's feet and one Button 1 press: kinds 0 and 2 held, kinds 3 and 4 not |
| `area_sweep.sh <tag> <stage> <area> <x0> <x1> <frames> [y] [shots] [gfx]`, `sweeps.sh` | pokes `190/191(A5)` and the phase word to start an area from `sb_s1` and walks player 1 through it; `hist8.py` then gives every pool 8 record's state histogram |
| `ab.sh <tag> <stage> <area> <park x> <frames> <addrs> [regions]`, `ab_count.py` | parked-camera A/B: map changes with the kind's records live (run A) and zeroed (run B) |
| `hide_run.sh`, `hidediff.py` | reference and hidden screenshots of an area; the differing pixels are the record's sprite |
| `kindmap.py` | for every pool 8 kind: placement entries of all stages (`kindmap.py` reads the `py/placement` readers) and the code sites that create it |
| `digest.py`, `lst.py`, `l.sh`, `a5ref.py`, `anim.py` | per-handler calls, `d16(A5)` words, gfx addresses and sound cues; a linear lister that prints dispatch tables as data and elides data-like runs (`l.sh lo hi`); every instruction that addresses a given `d16(A5)`; animation and box decoder for a record whose `56(A6)` is given |
| `gates.sh`, `gates_check.py` | the gate: fresh runs of all of the above, then the counts below (about 12 minutes) |

## Gate (`sh gates.sh`)

See `gates_check.py` for each check; the last run's counts are in `placement.md`/`ai.md` where they are cited. Checks: fire schedule 11/32/19/24 in 26 of 26 logs; player damage 40 with
reaction 8 and the fire as attacker 7 of 7; box replay equals the observed hit frame 7 of 7; fighter sampling model 8 of 8 (4 of 8 phases hit); fighter reach 7 of 7; natural bottle
(landing, fire next frame, Cody hit 40 at fire+2) 3 of 3; deflect 5 of 5 (and the late press makes fire 1 of 1); hovering deflect +2,000 4 of 4; pickup 4 of 4; shell 40 damage and reaction 3;
kind tile writes live against hidden 6 of 6; kind 0 palette flicker; shadow kinds `$1e`/`$1f` by hide diff 2 of 2; kind `$e` doors 1 of 1; bonus stage 6 objects 1 of 1; `kindmap.py` kind 7 has 10
entries; `digest.py` covers 60 kinds.

## Traps

- zsh does not word-split an unquoted variable, so `set -- $t` / `for t in "a b c"` loops pass one argument; call the scripts with separate arguments. `fire_run.sh` takes a decimal dx (`$(( 0x1c0 + dx ))` with a hex dx such as `-a0` evaluates a variable named `a0`).
- Hide tests need the records to exist: the area init allocates them a few frames after the phase poke (rel 7 to 15), so hide at rel 12 or later; screenshots are one frame behind the sprite list, shoot 3 frames after the hide.
- A camera that is parked far from the player moves only a few pixels per frame: kinds with a window test (`$49dc`) need several hundred frames before their records leave state 0.
- A hand-spawned record whose creator sets extra fields (the shell's `+14`, `+46`, `+76`, y) needs those fields poked: a shell with `+14 = 0` flies through the player.
- `hist8.py` counts frames per state key; the change frame is counted to the new key.
