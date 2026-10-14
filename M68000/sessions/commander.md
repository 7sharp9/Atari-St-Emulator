# Commander: handoff

Updated 2026-10-14 by the session that ended at commit `8749a55` (plus this handoff commit).

## Resume point

- Last work commit: `8749a55` rand1 side 3 against the game's AI over six starts (`pairs.py`, `startpoke.py`,
  `captains.py`); the handoff commit also corrects `seeds.sh`'s header.
- Working data: `M68000/scratchpad/cmd12/r1s3/<arm>/o<k>` (ai, scripted, llm, rollout; six starts each, 700M budget;
  `llm/o<k>/llm/` holds every prompt and reply), `cmd12/rngtest`, `cmd12/ticktest` (the AI under seed and dice-counter
  starts), `cmd12/rngwatch.txt` (writers of `$2df84` over 20M steps). `cmd11/so/` (the 30 land-2 runs with `objs.bin`)
  and `cmd9/` as before. `python3 commander/pairs.py scratchpad/cmd12/r1s3 3 --at 300,440` prints the result table.
- Start from: `scratchpad/pm142/rand1.snap` (rand1, side 3 is the AI testbed); land 2 `scratchpad/cmd3/l2build/l2_built.snap`
  with perturbed starts `cmd9/start/o<k>/final.snap`; land 1 `pm123/win/l1_built.snap`. Land 3 is not built:
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
- **Against the game's AI, as a rate** (README "Policies against the game's AI", `seeds.sh` + `pairs.py` on rand1
  side 3, six starts): side 3's lords minus the AI's at 300M / 440M: rollout +1.5 / +1.5, ahead from 5 of 6 starts and
  tied on the sixth at both (5 of 5 untied, one-sided sign test p about 0.03), with fewer men (-5.3 / -2.2); scripted
  -2.7 / -1.8, behind from 6 of 6 but +3 to +28 men; LLM -1.2 / -1.5, 3 of 6 ahead, 3 to 10 lords at 300M ($11.80,
  194 calls, 0 rejected orders).
- **The game's AI is one trajectory on rand1**: offset starts shift it in time (ends 676M..671M, same scores), the
  RNG seed advanced 1 or 2 draws gives the same observation at 60/60 decisions to 300M, and the dice counter `$57fec`
  shifted 1..5 the same totals at 135/136 decisions (`startpoke.py`). So a seeds result is the policy's spread
  against one fixed AI outcome.
- **Land 2's only second-group source** (README "A second side-1 group", `captains.py`): `$041a`, the captain of
  side 2's Capital and lead of its group 1; across the 30 land-2 end states alive in 13, dead in 13, gone in 3, and
  dead in the one run that took the Capital.

## Open, in priority order

1. **The LLM on rand1 is not separable from the AI; the rollout is.** Find what the rollout does that the LLM does
   not, from the logs (`runstat.py --every 20 scratchpad/cmd12/r1s3/{rollout,llm}/o0`, the LLM's `why` in
   `llm/o<k>/llm/llm.jsonl`): the LLM's worst starts (o0, o1, o5: 3 to 5 lords at 300M) against the rollout's on the
   same starts. Change the prompt (captain food against trip cost, enemy groups near our groups, the lords the
   rollout takes), re-run only the llm arm with `seeds.sh` (delete `llm/`), and score with `pairs.py`. Proof: lords
   ahead of the AI from 5 of 6 starts, as the rollout is.
2. **What the rollout trades.** It holds more lords with fewer men, and three of its six lands end early (426M,
   539M, 618M against the AI's 676M). Find whether side 3 ends the land by killing side 1's captain (`bp d2c8` side,
   who killed the lead, `leadkill/standoff.py` style on a `--objs` replay) or whether side 1 starves; an early end by
   side 3's hand is a better score than lords at 440M.
3. **Land 2, a second side-1 group.** In the 13 end states where `$041a` lives, read whether his group (side 2
   group 1) still has men; if he can be alive and groupless, aim the captain at the Capital at that moment (a
   `Scripted` rule gated on his group's men = 0) and check with `watch` on `28(group)` of side 1's slot 1 for the
   `$26d0` write. If he never is, land 2 has no second-group lever.
4. **Rollout food blindness** (unchanged): inside a 40M horizon food costs nothing until it hits 0; try a longer
   horizon for get-food candidates or score food left against the eating rate.
5. Seeds for land 1 (`seeds.sh` on `pm123/win/l1_built.snap`).
6. **Why side 2 makes no new group** after losing both (`$26d0` hits over the rollout win's 315M..1120M).
7. **Who rewrites the RNG seed in play.** Both RNG-shifted starts hold rand1 + 236 draws at 300M, but a 20M watch
   saw only `$12cb4` (26 draws). A whole-300M `watch 2df84 4` from `cmd12/rngtest/start/o1/final.snap` names it;
   candidates `$10d22` (from `$580a0`), `$ffd8`, `$a9da`/`$a9e6`, `$718e` (`find_field_writers.py`).
8. Land 3: build it from the land-2 win (`cmd9/rollout/o0/final.snap`) and play it.
9. Movement with rollouts; state-space forecaster (plan step 5); smaller items (side-0 peace bit from the `$c706`
   clobber, sender-word readers, `$25d6` rebuilding slot 0, UI click with side 1's slot held, which callers of
   `$548a` other than `$503c` leave in D0's high byte).

## Known traps

The PowerMonger traps in `sessions/powermonger.md` apply.

- A seeds result has no AI spread on rand1 (see Proven): pair against the one AI outcome, and do not read a policy's
  spread as the AI's.
- Do not edit `seeds.sh` (or any `.sh`) while a run of it is live: bash reads a script as it executes, so the
  running instance can read the edited tail. Copy it aside; a seeds run lasts about 40 minutes at par 8.
- `seeds.sh` par 8 with a rollout arm runs six rollouts at once, about 36 emulators (load 25 on 16 cores); the
  rollout arm is the long pole (about 30 minutes for six 700M runs).
- `pairs.py` scores the last decision at or before each step; the LLM decides every 20M, so use multiples of 20.
  A starred cell is a run that ended or stopped before that step.
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

Work Open 1: why the LLM is not separable from the AI on rand1 side 3 while the rollout is ahead on lords from 5 of 6
starts. Compare the two arms' logs on o0, o1 and o5, change the prompt, and re-run only the LLM arm with `seeds.sh`
(about $12) scored by `pairs.py`. Open 2 (what the rollout trades for its lords) can run alongside from the existing
logs. The prompt that starts it is `/resume commander`.
