# PowerMonger: handoff

Updated 2026-10-01 by the 140th pass (the least-covered code: address coverage 26191 to 12956 undocumented bytes; the arrow loop and the order pigeons proven; sound, panels, blitters, land build and maps documented; no emulator change).

## Resume point

- Last commit of this workstream: `1409064` (the documentation and promoted scripts), after `87c308b` (the arrow and pigeon model and gates); `git log --oneline -6`.
- Working data: `M68000/scratchpad/` (gitignored; on the Mac copied from gpubox, CLAUDE.md "Shell pitfalls"), indexed in `scratchpad/ANCHORS.md`. `pm140/` (~1.1 GB) holds this pass's corpora (`proj/corpus` 365 `$596a` entries, `pigeon/` 95 natural `$4562` entries and the census) and the four area agents' directories;
  rebuild the corpora with `py/proj_scan.py`, `py/proj_corpus.py`, `tools/capture_hits.py` (recipes in the gates' docstrings). Reusable scripts: `reversing/powermonger/py/` (README table), now with subdirectories `sound/`, `ui/`, `blit/`, `maps/`.
- Start from: `scratchpad/pm123/win/m1_ready.snap` (mission 1 conquered; lord 0 is a kind-3 lord with a WorkShop), `pm121/run/k5_s4.snap` (land 5, the best census snapshot), `pm139/jobs/pop_done.snap` (land 0 just after `$2984`).
- Uncommitted work left behind: none from this workstream. Not this workstream's: `M68000/sessions/README.md` (an Obsidian line-rewrap), `.obsidian/`, `Cadaver/`.

## Proven so far

Gates (differential tests against the real 68000 through `callcap`): entity FSM `scratchpad/pm98/repro93..97.py` 675/1335/413/85/99 and `pm99/diff_pm99.py` 1847/1847 (not rerun since `relink` became sign-aware, see Open 1); `pm98/diff_pm98.py` 71/71; `pm113/diff_4342.py` 110/110;
`pm115/diff_4bc8.py` 51/51 + `diff_4bc8_kind2.py` 20/20; `py/diff_1623c.py` 275/275; `py/diff_2776.py` 4119/4119; `py/diff_5cde.py` 768/768 + 85/85; `py/diff_revolt.py` 1778/1778; `py/diff_4f68.py` 1804/1804; `py/gate_equip.py` 385/385; `py/gate_jobs.py` 3310/3310; `py/gate_pop.py` 29860/29860;
`py/gate_shepherd.py` 1043/1043; `py/gate_animals.py` 45094/45094. **New this pass:**

- **Arrows** (`ai.md` "Arrows and carrier pigeons"): `py/gate_proj.py` **4210/4210** changed bytes over 456 states (364 natural, 92 synthetic) for `call_596a`/`call_4624`; 8 states excluded where `$5590` reaches its `$1b8c` tail. Damage `$52` to the first enemy man, pigeon or marker in the path, no flag test; the archer's `$34` cool-down ends with the arrow; type `$12` unreachable. Natural: 91 shots, 0 pigeons shot down in 1.05G steps.
- **Order pigeons**: `py/gate_pigeon_send.py` **1567/1567** over 125 states (95 natural). The first group of a side acts directly; any other captain's order travels by pigeon (word 48 of the group = the sender); the "same cell" test compares against record 0, so the direct branch is dead. Live: the player's `$12` runs directly (`$4562` 0 hits).
- **Sound** (`system.md`): a Timer A sample player, not a PSG music engine. `py/sound/gate_echinter.py` 328/328, `gate_timera.py` 300/300, `bank.py` 56/56 and 58/58; the renderer posts the sound events.
- **Panels** (`strategy.md` "How a panel opens"): `py/ui/` person panel 247/247, house panel 103/103, captain panel 12/12, `_getname` 80/80; the examine tool (icon `$2c`) opens them; aggression is display-only; the house panel prints the lord's loyalty.
- **Land build and maps** (`graphics.md`): `py/maps/gate_maps.py` `$10058` 125219/125219, `$10410` 45779/45779, `$ac20` 14539/14539, `$10910` 2561/2561, `$10638` 260/260; minimap 512000/512000 bytes; conquest map 96000/96000, 89310/89310, pick 18/18. Roads are terrain causeways.
- **Blitters** (`graphics.md`): `py/blit/blit_gate.py` 450/450 over the six clip back ends; `check_sh` is the sprite pick.
- Earlier, unchanged: the world-build population, shepherds and sheep, buildings and layouts, the game's own text, the starting armies (`$238c`, code read), the equipment exchange ported, the pigeon landing is not a manpower leak, every player order but `$04` and a natural `$0e`.
- `py/doc_coverage.py`: 26191 to 12956 bytes unmentioned (334 of 978 routines); what is left is data tables and small helpers.

## Open, in priority order

1. **Rerun the entity-FSM gates on gpubox** (`pm98/repro93..97.py`, `pm99/diff_pm99.py`): `pm_fsm_ref.relink` became sign-aware and `reconstruct` gained five modes in the 139th pass, and this pass appended three routines to the module; those scripts are not on the Mac. Expected unchanged.
2. **A natural `$0e` on a WorkShop lord**: from `pm123/win/m1_ready.snap` click order `$0e` on lord 0's town (22,45) (`py/clicks.py`, `order_run.sh` with `SNAP=`): expect `$5cde` to proceed and the men to go to modes `$3e..$46`. Also `$04` transfer, `$10`/`$1c` on a pile, the `$1a` supply line.
3. **The commander AI `$6522` as a gate**: `$6522`, `$6564`, `$661a`, `$6762`, `$69b4`, `$68fe`, `$66e8`, `$67ee`, `$6822` are documented from a read and 25 natural `$661a` captures (`strategy.md`, `scratchpad/pm122/dec/`) but never diffed against `callcap`. `$6822` also decides which captain gets an order directly and which by pigeon.
   Check `strategy.md` first (grep the addresses), then model it in `tools/pm_fsm_ref.py` and gate it on natural entries (`capture_hits.py <snap> 6522 ...`) as `gate_proj.py` does.
4. **The player's order to a second captain by pigeon, live**: needs a land where the player has two captains (`$04` transfer, then select the second box, then an order): expect `$4562` 1 hit, `$57fd8` counter 1, a pigeon of owner 1 flying, `$41dc` then `$6b38`, and the pigeon icon over the captain box (`$3ee8`, never seen on screen). Today it is a code read plus synthetic states.
5. **Wire `$1b8c`/`$2776` into `kill_rout_5590`** (`pm_fsm_ref.py`; `call_1b8c` and `call_2776` exist): removes the 8 excluded `gate_proj.py` states and the standing exclusion of `$5590`'s tail.
6. **`$238c`, `$2eac`, `$2906`**: read, not gated (`$10638` is now proven, 260/260; `$25d6`, `$1d70`, `$1b2a` exist). A `callcap 238c` gate per land build (8 states) needs `$2eac` (lord allocation, layout walk) and `$2906` (nearest forest op per lord).
7. **Category `$18`**: the game's click text says "Boat", `graphics.md` and the README say territory marker; a sprite crop of a live `$18` record settles it. Also category `$16` (`a_flight`, the developers' `_birds` for `$4c5f4`): are the "catch markers" birds? Draw one (`$11b44` never ran naturally).
8. **A natural `$36` contact** (a category-8 sheep engagement): sheep are the only category-8 records; a shepherd never triggers it. Check whether `$4dae`'s class table or an order can target a sheep (`ai.md` row `$36`); the Cow (category `$22`) nothing creates.
9. **Sound leftovers** (`system.md` "Not exercised"): which loader fills `$5879a` (resource 9, inferred), what `$1b9d0(0, $80)` does to the driver, the real playback rate (the emulator's Timer A ignores `TADR`), `_format_`/`_dda_loa`/`_dda_sav` live. **Map leftovers**: `_fix_it`'s four shapes rendered; a click on a conquered land (`$113a8`); the dead `$10458`/`$10c7e` family.
10. Older: whether food or a captain's position changes the health cap (`$5ccc`); `$1b8c` via `$5778`; `$4342`'s arrival branch; the crack's `$b842` patch; the `$54` merchant loop `$15b0c` (a `callcap $159de` with poked goods); the person panel's remaining Stock rows; the link handshake `$6eb6`.

## Known traps

- **`callcap` outcome `THREW ... WriteEa: immediate operand is not a valid destination`** is a runaway, not an emulator bug in `WriteEa`: an odd-address word access (an address error: a farmer's word 42 is its field cell, not a group offset) or a `bpc` hit that is not a call (`gate_maps.py` skips those by checking the entry registers). Check the poked field before suspecting the emulator.
- **Transcribe from the listing, not from a similar neighbour**: `call_596a` first carried the `btst #6/#4,7(A3)` flag tests of `$32c6` that `$596a` does not have; the gate caught it on the first natural hit. Read the whole block before modelling.
- **`bpc <addr> <n> <max>` counts hits from the start snapshot, and `max` bounds the whole gap**: `capture_hits.py --max` defaults to 50M; the first hit of a quiet routine can be 20M steps away. A hit it does not reach still leaves a `.snap` with no `.ram`: filter on `.ram`.
- **`py/gate_proj.py` and `gate_pigeon_send.py` poke synthetic states with `w` longwords built by `Harness.bytepokes`**; a `reuse` run keeps stale callcap JSON, delete `o_<state>.json` when a case builder changes.
- **`callcap` presets are not in the JSON's `reg0`** (`reg0` is read before the presets apply); `regN` is after. **`bpc` gives up after 200000 steps by default**; a world build is 2.5 M steps.
- **macOS `seq -s,` leaves a trailing comma** (`capture_hits.py` rejects it); build the hit list in Python. **The Edit tool drops trailing spaces from `new_string`**: use a Python replace for edits that end in a space.
- **Whole-routine callcap of `$3e06` cannot be entered mid-routine**: compare only what the part under test owns (`gate_animals.py`). **Bucket links of records below `$51b66` are negative 16-bit offsets** (sheep, markers, pigeons, shots, trees, buildings): sign-extend (`_objaddr`).
- **A failure branch that always follows another failure is a clue** (`farmer_fail` after every `fisher_fail` was a stale D1): tag the model's arms by cause and count before writing a reason.
- Earlier traps still apply: a routine's tail that ends in the iterator's `bra $1622c` cannot be `callcap`ed in place; REPL `w` takes longwords at even addresses; edit `.sym` lines in place; subagent reports need one spot check (this pass: every headline gate rerun from the promoted location, all reproduced; every agent contradicted its brief);
  the terrain redraw is gated (`w f890 00000000`); entity records are the first 512 only; one entity tick is ~200k steps; a symbol's address space depends on its type; `hits` after `u` starts at the end of that span; a refused click leaves `$57fd4` armed; `py/clicks.py` pointer moves 1:1
  (start `hits` before `mouse down`, replace the settle after it: `scratchpad/pm140/pigeon/live/o12h.cmds`); do not reopen the SingleStepTests track or `$4342`'s 8 proven branches; a full `pm_export.py` rerun regresses `entities.json`.
- Port traps (`port/stepper`): `--shot`/`--selfcheck` prove one instant (use `--playtest`); the port stays a renderer by Dave's decision (no entity simulation; `Equipment.fs` stays uncalled); the `port/` and `tools/pm_fsm_ref.py` identifiers still say herd/shepherd, morale, survivability: rename only with a gate rerun.

## Next session

Do Open 1 on gpubox if it is reachable (one command each), then Open 3: the commander AI `$6522` as a gate is the largest routine family in the strategic layer without a differential proof, and the natural entries are cheap to capture; take the order-routing helper `$6822` first because it
decides direct versus pigeon delivery. Open 4 and 2 are one live run each (about 10 tool calls). Keep proofs in the gate style (a model in `tools/pm_fsm_ref.py`, a script in `py/`, a match count); label code reads as code reads.
