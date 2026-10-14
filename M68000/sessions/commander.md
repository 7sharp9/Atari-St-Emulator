# Commander: handoff

Updated 2026-10-14 by the session that ended at commit `6e0ea30` (plus this handoff commit).

## Resume point

- Last work commits: `c7cfc04` how the captain dies across the seeds (`leadkill/gate_standoff.sh`, `standoff.py`,
  `loop.py --objs`), `6e0ea30` its `arrow` stage. `6a238f2` is a CLAUDE.md commit from the same session.
- Working data: `M68000/scratchpad/cmd11/so/<arm>/o<k>` (all 30 land-2 seed runs replayed with `--objs 1e5`:
  `objs.bin` object-array samples, `final.snap`), `cmd11/arrow/at_343800000.snap` (rollout o5 before the arrows),
  `cmd11/seqs.txt` (every melee sequence). `cmd10/leadkill/` (the o1 replays and watches), `cmd9/` (the seed runs and
  starts) as before. `python3 commander/runstat.py [--every M] <dirs>` reads any run;
  `leadkill/standoff.py <run> <start snap> -v` reads a sampled one.
- Start from: `scratchpad/cmd3/l2build/l2_built.snap` (campaign land 2 at its first `$f898`); perturbed starts
  `cmd9/start/o<k>/final.snap` (`seeds.sh` rebuilds them). Land 1: `pm123/win/l1_built.snap`. Land 3 is not built:
  `campaign_next.sh scratchpad/cmd9/rollout/o0/final.snap 3`.
- Uncommitted work left behind: none.

## Proven so far

All in `reversing/powermonger/commander/README.md`; every gate re-run from its promoted location.

- Orders from any slot (`gate_inject.sh` 7/7, `gate_orders.sh` 57/57, `gate_ungated.sh` 52/52, `gate_local.sh`), retire
  verdicts (`gate_retire.sh`), order cell = cell centre (`gate_cellpt.py` 16/16), pigeons (`pigeon/gate_pigeon.sh` 7/7).
- Deterministic replayable loop (`gate_loop.sh`, `gate_loop_side1.sh`); A* legs 8/8 (`gate_move.sh`); exact rollouts
  (`gate_rollout.sh` 20/20); `--objs` sampling leaves a replay byte-identical (30/30).
- Provisioning and the field-fight posture fix (land 1 won at 215M by scripted and rollout; `gate_posture.sh`).
- Land 2 as a rate (`seeds.sh`, six starts): scripted 0/6, `--evade` 0/6, rollout 1/6. Of 27 losses, 24 are the
  captain killed (23 in melee, 1 by two arrows), 3 the no-lord retire.
- **Who picks the lead** (`leadkill/gate_leadkill.sh`): `$548a` keeps the last acceptable candidate and `$503c` weighs
  the hunted group's lead last, so every enemy man who passes the gate aims at him (model 64/64 picks); an arriving
  chaser drags him into `$32`; a go to while he shoots makes it worse.
- **What kills him** (`leadkill/gate_standoff.sh`, README "Across the seeds"): in all 39 melee sequences of the 30
  runs the lead loses at most the summed health of the men he fights (one a tick each way). The 23 killing sequences
  fought 2 to 8 men with 120 to 553 health; the survived ones at most 150 (the win's big fight: one 65-health man,
  94 to 30, back to 95 later). Where he stands does not separate them: killers picked him from 0 to 4081 units.
  Rollout o5's lead was shot twice (82 each, `$5b4c` in `$596a`, `gate_standoff.sh arrow`). The earlier "standoff
  distance" hypothesis is refuted.
- No lord holds goods on land 2 in the death window (five states read), so equipping the men is not a lever there.

## Open, in priority order

1. **A rule that keeps more than one healthy enemy man from reaching the captain.** He survives one man (less health
   than his 95) and dies to two or more. Two leads to test, each as a `seeds.sh` arm against scripted 0/6 and rollout
   1/6:
   - *Interception.* evade o3 survived 5 men (150 health) because his own men took chasers off him. Run
     `chase_fate.py` on a watch of that fight (replay `cmd9/evade/o3` with `--snap-at 367000000`) and of a killing
     one, and count the chasers diverted against the ones that arrived, with his men's count and posture in each.
     If his own men in contact are what diverts chasers, the rule is to fight only with the captain's men between
     him and the enemy (march the group so the lead trails, or attack only with a men margin).
   - *A second side-1 group.* None of the 30 runs ever had a side-1 group other than 0. strategy.md shows groups 1..5
     come from `$5c2c` → `$25d6` (a lord's captain defects); find whether side 1 can get one on land 2 (a conquered
     lord, an alliance) and whether it fights side 2 while the captain stays out of melee range.
2. **Rollout food blindness** (unchanged): inside a 40M horizon food costs nothing until it hits 0; try a longer
   horizon for get-food candidates or score food left against the eating rate.
3. Seeds for land 1 and rand1 side 3 (`seeds.sh` on `pm123/win/l1_built.snap` and `pm142/rand1.snap`).
4. **Why side 2 makes no new group** after losing both (`$26d0` hits over the rollout win's 315M..1120M).
5. LLM prompt: captain food against trip cost, enemy groups near the captain, and how many healthy enemy men are within
   reach of the lead; re-run on two seeds.
6. Land 3: build it from the land-2 win (`cmd9/rollout/o0/final.snap`) and play it.
7. Movement with rollouts; state-space forecaster (plan step 5); smaller items (side-0 peace bit from the `$c706`
   clobber, sender-word readers, `$25d6` rebuilding slot 0, UI click with side 1's slot held, which callers of
   `$548a` other than `$503c` leave in D0's high byte).

## Known traps

The PowerMonger traps in `sessions/powermonger.md` apply.

- `loop.py --snap-at N` saves `at_N.snap` before that step's decision pokes: resuming it by hand needs the logged
  `applied` lines at their steps (`gate_leadkill.sh` pokes the 205M and 205.4M orders). Pick a snap step with no
  applied orders between it and the window you watch (`gate_standoff.sh arrow`), or replay through `loop.py`.
- `loop.py --objs 1e5` samples about 0.6 tick apart: a melee or a chase shorter than that can fall between samples
  (the win's 3-health man at 315M..330M does). Use a watch for an exact count.
- A watch window bounds what it finds: the 15M-step `gate_leadkill.sh win` watch missed the win's 65-health fight at
  337M.
- A new `Scripted` rule whose run ends at the same step as the baseline never fired: compare end steps (or count its
  orders in `decisions.jsonl`) before reading an outcome.
- `loop.py --replay` ignores `--budget` and runs the whole logged run (the land-2 rollout win, 1120M, takes about 4
  minutes; the 2000M budget runs about 12). It takes the log path relative to the current directory.
- One run per arm on land 2 is noise: use `seeds.sh`. `avoid` and `diseng` arms repeat scripted o0 (and avoid o5 =
  diseng o5) step for step.
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

Work Open 1, interception first: watch evade o3's survived fight (from 367M) and one killing fight (scripted o1 from
205M is already in `cmd10/leadkill`), run `chase_fate.py` on both, and see whether his own men in contact are what
diverts chasers. If so, write the rule (keep the captain's men between him and the enemy, or attack only with a men
margin), add it to `seeds.sh` as an arm and compare with scripted 0/6 and rollout 1/6. The prompt that starts it is
`/resume commander`.
