# PowerMonger: handoff

Updated 2026-10-01 by the 139th pass (the least-documented code found by address coverage: the world-build population, shepherds and sheep, the pigeon pool, the building kinds, the game's own text tables; four new gates; no emulator change).

## Resume point

- Last commit of this workstream: the 139th pass's handoff commit (`git log --oneline -6`; the work is `a60534b`, `0fd7c3c`, `05f579c`, `0e71c9d`).
- Working data: `M68000/scratchpad/` (gitignored; on the Mac copied from gpubox, CLAUDE.md "Shell pitfalls"), indexed in `scratchpad/ANCHORS.md`. `pm139/` holds this pass's corpora and time series (~700 MB,
  rebuild with `py/build_series.py`, `tools/capture_hits.py`, recipes in the docstrings of `py/gate_jobs.py`/`gate_pop.py`); the reusable scripts are in `reversing/powermonger/py/` (README table).
- Start from: `scratchpad/pm139/jobs/pop_done.snap` (land 0 just after `$2984`), `pm123/win/m1_ready.snap` (mission 1 conquered; lord 0 is a kind-3 lord with a WorkShop), `pm121/run/k5_s4.snap` (land 5, the best census snapshot).
- Uncommitted work left behind: none from this workstream. Not this workstream's: `M68000/sessions/README.md` (an Obsidian line-rewrap), `.obsidian/`, `Cadaver/`.

## Proven so far

Gates (differential tests against the real 68000 through `callcap`): entity FSM `scratchpad/pm98/repro93..97.py` 675/1335/413/85/99 (not rerun this pass, see Open 1); `pm98/diff_pm98.py` 71/71; `pm99/diff_pm99.py` 1847/1847 (not rerun);
`pm113/diff_4342.py` 110/110; `pm115/diff_4bc8.py` 51/51 + `diff_4bc8_kind2.py` 20/20; `py/diff_1623c.py` 275/275; `py/diff_2776.py` 4119/4119; `py/diff_5cde.py` 768/768 + 85/85; `py/diff_revolt.py` 1778/1778; `py/diff_4f68.py` 1804/1804;
`py/gate_equip.py` 385/385. Rerun green this pass after `relink` became sign-aware: all of those except the three marked. **New:** `py/gate_jobs.py` 3310/3310 (146 states), `py/gate_pop.py` 29860/29860 (8 land builds, 1026 men),
`py/gate_shepherd.py` 1043/1043 (198 states), `py/gate_animals.py` 45094/45094 (55 snapshots; 5 with a live projectile excluded).

- **World-build population** (`economy.md` 5a): 2 men per building-chain settlement; job lottery `$2a98` (captain / shepherd 3/32 / fisher 16/32 / farmer 12/32 / give-up 1/32, 5 rounds, then merchant). `$2c5a` bounds its row with the caller's stale D1:
  1234 of 1234 farmer failures in 8 builds, 222 of 281 merchants. Fishers cap at 30 (marker pool), shepherds stop at 10 or 11 (sheep pool). Model: `call_2984`/`call_2a98`/... in `tools/pm_fsm_ref.py`; `py/pop_census.py`.
- **Shepherds and sheep, pigeons** (`ai.md` "Shepherds, animals and carrier pigeons"): 40 x 20-byte sheep pool `$4ccd6`, made only at build, never freed; modes `$80 $84 $86 $88 $82`; update loop `$4044` in `$3e06`; the other 47 records of `$4c112` are the AI lords' pigeons, `$41dc` their arrival.
- **Buildings and layouts** (`economy.md`): `$4f916` records are buildings named by `housenam` `$a15a` (kind 7 = WorkShop, not capital); six town layouts at `$3078` by lord kind, 72 of 74 lords exact; `py/town_layouts.py`. `callcap 5cde` refuses the two kind-6 lords, proceeds for both kind-3.
- **The game's own text** (`strategy.md`): group states 1..16 (Waiting .. Spying), lord kinds (Village .. Base), posture, aggression, age classes (byte 14 is age, men start 12..43), side names, panels; the loyalty line is a constant ("trusting", 2 of 2 callcaps).
- **Starting armies** (`strategy.md`, code read): `$238c` = Base (lord kind 6) + leader + `word10` followers per side; group men equal word 10 on 10 of 10 sides.
- `py/doc_coverage.py`: 29498 -> 26213 bytes of developer-named routines with no doc, script or port mention (most of what is left is data and UI).
- Earlier, unchanged: the equipment exchange ported (`port/godot/logic/Equipment.fs`, `CreditMode`), the pigeon landing is not a manpower leak, `$42be`, `troops_field` rule exact 2280/2280, modes `$34`/`$36`/`$8a`, every player order but `$04` and a natural `$0e`.

## Open, in priority order

1. **Rerun the entity-FSM gates on gpubox** (`pm98/repro93..97.py`, `pm99/diff_pm99.py`): this pass changed `pm_fsm_ref.relink` (sign-aware offsets) and added five modes to `reconstruct`; those scripts are not on the Mac. Expected unchanged; one run proves it.
2. **A natural `$0e` on a WorkShop lord**: from `pm123/win/m1_ready.snap` click order `$0e` on lord 0's town (22,45) (camera on it; `py/clicks.py`, `order_run.sh` with `SNAP=`): expect `$5cde` to proceed (the callcap probe did: D2 = `$3e`) and the men to go to modes `$3e..$46`. Also `$04` transfer, `$10`/`$1c` on a pile, the `$1a` supply line.
3. **What is still not modelled around the pigeons and projectiles**: `$596a` (projectile loop; excluded from `gate_animals.py`), `$6b38` as run by a pigeon arrival, the player's landing `$4244`. Proving `$596a` would remove the exclusion.
4. **`$238c`, `$2eac`, `$10638`, `$2906`**: read, not gated. A `callcap 238c` gate per land build (8 states) needs `$2eac` (lord allocation, layout walk), `$10638` (ground levelling, dispatch table `$106ba`) and `$2906` (nearest forest op per lord) ported; `$25d6`, `$1d70`, `$1b2a` exist.
5. **A natural `$36` contact** (a category-8 sheep engagement): sheep are the only category-8 records; a shepherd never triggers it. Check whether the AI's `$4dae` class table or an order can target a sheep (`ai.md` row `$36`); the sheep panel also has a Cow case (category `$22`) that nothing creates.
6. **Consumers of the displayed fields**: group aggression (`148(A3)`, 0 PowerMonger .. 7 Wimp: where read, if anywhere), the `$9218` forcing, the person and house panels' remaining selectors, the name generator `$a9ce`/`$aa5b`. `py/doc_coverage.py` lists the rest of the unmentioned code (UI click handlers `$9000..$b000`, map and road drawing `$10000`, sound `$1a000..$1c000`, the serial link `$ba74`, the link handshake `$6eb6`).
7. Older: whether food or a captain's position changes the health cap (`$5ccc`); `$1b8c` via `$5778`; `$4342`'s arrival branch; the crack's `$b842` patch; the `$54` merchant loop `$15b0c` (merchants are the lottery's leftovers, so a `callcap $159de` with poked goods is the check).

## Known traps

- **`callcap` presets are not in the JSON's `reg0`**: `reg0` is read before the presets apply (`gate_jobs.py` takes `D1` from its own preset). `regN` is after.
- **`bpc <addr> <n>` gives up after 200000 steps by default**; a world build is 2.5 M steps. Pass a third argument (`bpc 2a96 1 12000000`).
- **macOS `seq -s,` leaves a trailing comma** (`capture_hits.py` rejects it); build the hit list in Python. **The Edit tool drops trailing spaces from `new_string`**: `"60000000 {OUT}"` became `"60000000{OUT}"` in an f-string; use a Python replace for edits that end in a space.
- **Whole-routine callcap of `$3e06` cannot be entered mid-routine** (its epilogue pops registers saved at entry): compare only what the part under test owns (`gate_animals.py`), and exclude states where a later part of the routine touches the same buckets (a live projectile).
- **Bucket links of records below `$51b66` are negative 16-bit offsets** (sheep, markers, pigeons, shots): any model that adds a link word to `OBJ` must sign-extend (`_objaddr`).
- **A failure branch that always follows another failure is a clue**: `farmer_fail` after every `fisher_fail` was a stale D1. Tag the model's arms by cause (`farmer_fail_stale`) and count before writing a reason.
- Earlier traps still apply: a routine's tail that ends in the iterator's `bra $1622c` cannot be `callcap`ed in place (`gate_equip.py` copies the record onto slot 511); REPL `w` takes longwords at even addresses; `merge_sym.py --write` used to drop comments (edit `.sym` lines in place);
  subagent reports need one spot check; `parents[N]` in promoted scripts; byte 38 is overloaded; the terrain redraw is gated (`w f890 00000000`); entity records are the first 512 only; one entity tick is ~200k steps; a symbol's address space depends on its type; a stray `cat > file` waits on stdin;
  `hits` after `u` starts at the end of that span; a refused click leaves `$57fd4` armed; `py/clicks.py` pointer moves 1:1; do not reopen the SingleStepTests track or `$4342`'s 8 proven branches; a full `pm_export.py` rerun regresses `entities.json`.
- Port traps (`port/stepper`): `--shot`/`--selfcheck` prove one instant (use `--playtest`); Mibo's `GameTime` has no F#-callable constructor; the port stays a renderer by Dave's decision (no entity simulation; `Equipment.fs` stays uncalled); the `port/` and `tools/pm_fsm_ref.py` identifiers still say herd/shepherd, morale, survivability: rename only with a gate rerun.

## Next session

Do Open 1 on gpubox if it is reachable (one command each), then Open 2 (the live `$0e` click run, about 10 tool calls). After that pick from `py/doc_coverage.py --min 100` and the UI text tables: the person and house panels' selectors name more fields.
Keep proofs in the gate style (a model in `tools/pm_fsm_ref.py`, a script in `py/`, a match count); label code reads as code reads.
