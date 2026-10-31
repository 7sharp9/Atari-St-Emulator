# Commander: handoff

Updated 2026-10-31 by a session that resumed at `367ece7`, found Open 1 and Open 2 already settled by `6a9294d`
(committed without a handoff), recomputed its tables and launched nothing.

## Resume point

- Last commit of this workstream: `6a9294d` LLM not separable from the game's AI under three prompts; the
  rollout's early land ends are side 3 killing side 1's starved lone captain.
- Working data: `M68000/scratchpad/cmd12/r1s3/<arm>/o<k>` (ai, scripted, llm v1, rollout; six starts, 700M),
  `cmd13/r1s3/llm` (v2), `cmd13/r1s3b/{llm,llm_v1,llm_v2}` (v3, with v1 and v2 linked in for one table),
  `cmd13/so/` (the `--objs` replays of rollout o1, o3, o4 and AI o0), `cmd12/rngtest`, `cmd12/ticktest`,
  `cmd11/so/`, `cmd9/`. Tables: `python3 reversing/powermonger/commander/pairs.py scratchpad/cmd13/r1s3b 3 --at 300,440`
  (recomputed this session; matches the README table). Rebuild recipe: `seeds.sh` header, README "Policies against
  the game's AI".
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
- Land 2 as a rate (`seeds.sh`, six starts): scripted 0/6, `--evade` 0/6, rollout 1/6; of 27 losses 24 are the captain
  killed. Who picks the lead (`leadkill/gate_leadkill.sh`, 64/64) and what kills him (`leadkill/gate_standoff.sh`:
  summed health of the men he fights; standoff distance refuted). No lord holds goods in the death window.
- **Against the game's AI** (README "Policies against the game's AI", rand1 side 3, six starts, lords minus the AI's at
  300M / 440M): rollout +1.5 / +1.5, ahead from 5 of 6 (sign test p about 0.03); scripted -2.7 / -1.8, behind 6/6;
  LLM v1 -1.2 / -1.5, v2 -2.0 / -2.0, v3 -1.8 / -3.3: not separable under three prompts ($11.80, $12.84, $13.01;
  194, 205, 210 calls). The game's AI is one trajectory on rand1 (`startpoke.py`).
- **The rollout's early ends** (README, same section): side 1 gets no orders, its captain starves alone, and side 3's
  men kill him, as the AI does; `standoff.py --side 1` on 4/4 `--objs` replays (`cmd13/so/`).
- **Land 2's only second-group source** (README "A second side-1 group", `captains.py`): `$041a`, alive in 13 of 30.

## Running

Nothing running.

## Open, in priority order

1. **Land 2, a second side-1 group.** In the 13 end states where `$041a` lives, read whether his group (side 2
   group 1) still has men; if he can be alive and groupless, aim the captain at the Capital then (a `Scripted` rule
   gated on his group's men = 0) and `watch` `28(group)` of side 1's slot 1 for the `$26d0` write. If he never is,
   land 2 has no second-group lever.
2. **Rollout food blindness**: inside a 40M horizon food costs nothing until it hits 0; try a longer horizon for
   get-food candidates or score food left against the eating rate (rand1 seeds, `pairs.py` against `cmd12` rollout).
3. Seeds for land 1 (`seeds.sh` on `pm123/win/l1_built.snap`).
4. **Why side 2 makes no new group** after losing both (`$26d0` hits over the rollout win's 315M..1120M).
5. **Who rewrites the RNG seed in play**: whole-300M `watch 2df84 4` from `cmd12/rngtest/start/o1/final.snap`;
   candidates `$10d22`, `$ffd8`, `$a9da`/`$a9e6`, `$718e`.
6. Land 3: build it from `cmd9/rollout/o0/final.snap` and play it.
7. Movement with rollouts; state-space forecaster (plan step 5); smaller items (side-0 peace bit from the `$c706`
   clobber, sender-word readers, `$25d6` rebuilding slot 0, UI click with side 1's slot held, callers of `$548a`
   other than `$503c` and D0's high byte).

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
- `llm.py` passes `--model sonnet`, an alias: all three arms so far were answered by `claude-sonnet-5-5` (`model_usage`
  in `llm.jsonl`), but a later arm may get another model. Pin the full id before an arm that is compared with them.
- Six starts per LLM arm cannot resolve a prompt change: across v1/v2/v3 one start moves by up to 6 lords at 300M
  (paired differences v1 - v2: -2 -4 +5 +2 +6 -2, SD 4.1).


## Waiting on Dave

- **Whether the LLM arm continues, and in what form.** Another prompt revision at six starts (about $12) cannot be
  read: the per-start spread between LLM runs is up to 6 lords, and resolving a 2-lord shift needs about 30 starts
  per arm (inferred from the six v1 - v2 pairs, SD 4.1), about $60 an arm. Recommendation: no v4 prompt run. Either
  close step 4 as "rollout ahead, LLM not separable", or fund one design change that could plausibly move it by more
  than the spread (for example the LLM proposing candidates that the rollout scores), with `--model` pinned.

## Next session

Unless Dave funds an LLM arm, work Open 1 (land 2's second group) from `cmd11/so/` end states and `captains.py`.
If he does, pin the model in `llm.py`, copy `seeds.sh` aside, run only the llm arm into a new `scratchpad/cmd14/`
dir, and score it with `pairs.py` against `cmd12/r1s3`. The prompt that starts it is `/resume commander`.
