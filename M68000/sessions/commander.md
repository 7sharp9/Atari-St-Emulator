# Commander: handoff

Updated 2026-10-14 by the session that ended at commit `cd44b37` (plus this handoff commit).

## Resume point

- Last work commits: `4f886a9` how an enemy man reaches the captain's lead (`leadkill/`), `cd44b37` its `win` stage and
  the design-digest line. `f7e49e4` is a CLAUDE.md commit from the same session.
- Working data: `M68000/scratchpad/cmd10/` (`leadkill/`: the gate's replays `replay/at_205000000.snap`,
  `pre_pick.snap` (o1 just before `$521a6`'s pick of the lead), `win/at_315000000.snap`, the watches; `trace/`, `win/`,
  `goto/`: this session's first, unpromoted runs of the same). `cmd9/` (the six land-2 seeds per arm, `o1_health/`) and
  `cmd8/` as before. `python3 commander/runstat.py [--every M] <dirs>` reads any run.
- Start from: `scratchpad/cmd3/l2build/l2_built.snap` (campaign land 2 at its first `$f898`); perturbed starts
  `cmd9/start/o<k>/final.snap` (`seeds.sh` rebuilds them). Land 1: `pm123/win/l1_built.snap`. Land 3 is not built:
  `campaign_next.sh scratchpad/cmd9/rollout/o0/final.snap 3`.
- Uncommitted work left behind: none.

## Proven so far

All in `reversing/powermonger/commander/README.md`; every gate re-run from its promoted location.

- Orders from any slot (`gate_inject.sh` 7/7, `gate_orders.sh` 57/57, `gate_ungated.sh` 52/52, `gate_local.sh`), retire
  verdicts (`gate_retire.sh`), order cell = cell centre (`gate_cellpt.py` 16/16), pigeons (`pigeon/gate_pigeon.sh` 7/7).
- Deterministic replayable loop (`gate_loop.sh`, `gate_loop_side1.sh`); A* legs 8/8 (`gate_move.sh`); exact rollouts
  (`gate_rollout.sh` 20/20).
- Provisioning and the field-fight posture fix (land 1 won at 215M by scripted and rollout; `gate_posture.sh`).
- Land 2 as a rate (`seeds.sh`, six starts): scripted 0/6, `--evade` 0/6, rollout 1/6; all 24 losses are the captain's
  lead killed in melee by a posture-2 side-2 group.
- **How the captain dies** (`leadkill/gate_leadkill.sh`, README "How the captain dies"): `$548a` keeps the last
  acceptable candidate (its key is D0, not the distance) and `$503c` weighs the hunted group's lead last, so every enemy
  man who passes the gate (bow, better weapon, health at least the lead's, or retry byte 39 = 2) aims at the lead, one
  claim per tick: the model predicts 64/64 live picks. Poking one hunter's byte 39 hands the lead to the next of the
  tick. A chaser who arrives puts the lead in `$32` one melee tick later (`$1533c` → `$56a6`); melee drains 1 a tick each
  way, and the gate opens to every enemy once the lead's health falls below theirs (7 of 40 pass at 190M, 25 of 30 at
  211M). A go to while the lead still shoots makes it worse (health 5 against 83 in 2.6M steps, two destinations). The
  rollout win's lead was engaged once (315M..330M), by a 3-health man, and two chasers were diverted by his men.

## Open, in priority order

1. **A rule from the lead-kill mechanism.** The inferred difference between the win and o1 is the lead's standoff
   distance when the groups meet (about 3 cells against half a cell; two runs). First measure it across the seeds:
   for each of the 24 losses and the win, the distance from the lead to the first chaser aimed at him, and that
   chaser's health (replay each run's log to the lead's first `$32` with `--snap-at`, `chase_fate.py` on a watch). If
   it separates, the rule is about where the captain stands when an enemy group closes (halt short of the lord's cell
   rather than march onto it; not a go to once fighting). The other lever is the health race: weapons on the
   captain's men raise their drain (`weapon >> 1 + 1`), so they kill or divert chasers sooner; check whether land 2
   offers equip at all. Either rule goes to `seeds.sh` as an arm against scripted 0/6 and rollout 1/6.
2. **Rollout food blindness** (unchanged): inside a 40M horizon food costs nothing until it hits 0; try a longer
   horizon for get-food candidates or score food left against the eating rate.
3. Seeds for land 1 and rand1 side 3 (`seeds.sh` on `pm123/win/l1_built.snap` and `pm142/rand1.snap`).
4. **Why side 2 makes no new group** after losing both (`$26d0` hits over the rollout win's 315M..1120M).
5. LLM prompt: captain food against trip cost, enemy groups near the captain, and the lead's exposure; re-run on two
   seeds.
6. Land 3: build it from the land-2 win (`cmd9/rollout/o0/final.snap`) and play it.
7. Movement with rollouts; state-space forecaster (plan step 5); smaller items (side-0 peace bit from the `$c706`
   clobber, sender-word readers, `$25d6` rebuilding slot 0, UI click with side 1's slot held, which callers of
   `$548a` other than `$503c` leave in D0's high byte).

## Known traps

The PowerMonger traps in `sessions/powermonger.md` apply.

- `loop.py --snap-at N` saves `at_N.snap` before that step's decision pokes: resuming it by hand needs the logged
  `applied` lines at their steps (`gate_leadkill.sh` pokes the 205M and 205.4M orders).
- A new `Scripted` rule whose run ends at the same step as the baseline never fired: compare end steps (or count its
  orders in `decisions.jsonl`) before reading an outcome.
- `loop.py --replay` ignores `--budget` and runs the whole logged run (the land-2 rollout win, 1120M, takes about 4
  minutes); use `--snap-at` to keep the states you need. It takes the log path relative to the current directory.
- One run per arm on land 2 is noise: use `seeds.sh`.
- Camped men are mostly not in the object table; a per-man census works for a marching or fighting group.
- Killing `loop.py` leaves its emulator children running: `pkill -9 -f 'scratchpad/<run dir>'`, check `pgrep -fl`.
- A rollout process loads `rollout.py` and `loop.py` once at start: editing them mid-run changes nothing in that run.
- Every local-side rule in `Scripted` is gated on `local` (and `--evade` on its flag) so side-3 gate runs stay
  byte-identical; `gate_rollout.sh`'s choices depend on Scripted, so re-run it after any change.
- `Scripted` skips a group whose lead object is missing; the land does not end while the captain group's owner word
  stays 1.
- Rollout runs on land 2 cost 15 to 40 minutes each on a loaded machine; `seeds.sh` par counts each as 6 processes.
- On rand1 every AI group's lead holds a Boat: movement tests need `prep.py`'s boat stripping.
- An injected order sets no pending word and lasts one tick in the slot: write a decision's orders `--gap` apart.
- `claude -p --output-format json` output carries session and account metadata (`*.cli.json`): never commit it.
- `$57fba` is rebuilt every tick and can be read torn; score from observe's totals.
- To stop at the Nth pick of a man, count the `$5350` writes before his in a watch of the same lineage and `bpc 5350 N`;
  the watch's step counter is the emulator's absolute count, not the REPL command's.

## Next session

Work Open 1: measure the lead's standoff distance and the first chaser's health at the lead's first `$32` across the
24 land-2 losses and the win (replay each `cmd9/<arm>/o<k>` log with `--snap-at`, `chase_fate.py`). If it separates
wins from losses, write the halt-short rule, add it to `seeds.sh` as an arm, and compare with scripted 0/6 and rollout
1/6. The prompt that starts it is `/resume commander`.
