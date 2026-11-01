# Commander: handoff

## Resume point

- Last commit of this workstream: `52ef030` search arms on land 2 at 30 starts (rollout 4 won, hybrid 8, not
  separable); `outcomes.py`. Earlier this pass: `6783242` (evaluation design, Haiku on rand1), `ce7cc93` (land 2 at
  30 starts for scripted and the Haiku LLM; `--policy hybrid`).
- Every arm in the README so far ran on the emulator build before merge 7df69a2 (midwinter's IKBD fix, record/replay).
  `bin/` now holds, or will hold, the merged build: see Open 1 before comparing a new run with these.
- Working data: `M68000/scratchpad/cmd14/` (README there: `r1s3h` Haiku on rand1, `hybgate`, `l2s30` four arms by
  30 starts), `cmd12/r1s3`, `cmd13/r1s3b`, `cmd9/`. Tables: `outcomes.py scratchpad/cmd14/l2s30 1 scripted llm_haiku
  rollout hybrid_haiku`; `pairs.py scratchpad/cmd13/r1s3b 3 --at 300,440`.
- Start from: rand1 `scratchpad/pm142/rand1.snap` (side 3 testbed); land 2 `scratchpad/cmd3/l2build/l2_built.snap`,
  30 perturbed starts `cmd14/l2s30/start/o<k>/final.snap`; land 1 `pm123/win/l1_built.snap`. Land 3 is not built:
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
- **Haiku = Sonnet on rand1** (v3 prompt, six starts, Haiku minus Sonnet mean -0.2 lords) at about a twentieth of
  the cost ($0.0034 against $0.062 a call).
- **Land 2 side 1 at 30 starts** (README "Land 2 as a rate", `outcomes.py`): won / captain killed / no-lord / alive
  at 2000M: scripted 0/27/3/0, Haiku LLM 0/20/3/7, rollout 4/18/2/6, hybrid 8/18/1/3. Both search arms beat scripted
  28/30 (p < 1e-6); hybrid beats the LLM 21/30 (p = 0.04); hybrid against rollout 15 above, 14 below (p = 1.0), wins
  8 against 4 on disjoint starts (McNemar p = 0.39): not separable. The LLM's candidate won 207 of the 712 rollout
  decisions it was offered at. Haiku $3.36 and $3.33 for the two LLM arms.
- **Land 2's only second-group source** (README "A second side-1 group", `captains.py`): `$041a`, alive in 13 of 30.

## Running

Nothing running.

## Open, in priority order

1. **Re-baseline on the merged build** before any new arm: run scripted on land-2 starts o0..o5 into a new
   `scratchpad/cmd15/` with the 7df69a2 build in `bin/` (after midwinter has installed it and run `gates.py`) and
   compare end steps with `cmd14/l2s30/scripted`. Identical: the new runs pool with cmd14. Not identical: every arm
   compared later re-runs on the new build. The commander pokes orders through the REPL, not the IKBD, so identical
   is expected (inferred, not checked).
2. **Whether hybrid beats rollout** needs about 130 starts per arm (13% against 27%, 80% power, unpaired; inferred
   from the 30-start rates). Waiting on Dave (cost below). A cheaper question first: does the LLM candidate matter
   where it wins? Re-run the hybrid from the decisions where `llm` was best with that candidate removed (a fork of
   the logged run) and see whether the outcome changes.
3. **Land 2, a second side-1 group** (`$041a`, alive in 13 of 30 cmd9-era end states): read whether his group still
   has men; if he can be alive and groupless, aim the captain at the Capital then and `watch` `28(group)` of side 1's
   slot 1 for the `$26d0` write. If he never is, land 2 has no second-group lever.
4. **Water-cell orders from the LLM**: 105 dropped in the land-2 LLM arm. Give the prompt the land mask near each
   target, or snap a water target to the nearest land cell in `llm.py`'s validation; measure the drop count.
5. **Rollout food blindness**: inside a 40M horizon food costs nothing until it hits 0; try a longer horizon for
   get-food candidates or score food left against the eating rate.
6. Seeds for land 1; why side 2 makes no new group (`$26d0` hits over the rollout win's 315M..1120M); who rewrites
   the RNG seed in play (`watch 2df84 4` from `cmd12/rngtest/start/o1/final.snap`; candidates `$10d22`, `$ffd8`,
   `$a9da`/`$a9e6`, `$718e`); land 3; movement with rollouts; the state-space forecaster (plan step 5), which is what
   makes 130-start search arms affordable.

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
- Snapshots from before format v12 differ byte-wise from new ones of the same game state (one ACIA byte): compare
  `obs_hash` and clock, not file hashes (cmd9 against cmd14 starts: 5/5 identical state).
- In the hybrid, an LLM proposal identical to the rollout's first candidate is deduplicated away, and one with no
  valid group order is not offered: 1143 calls gave 712 offers on land 2. Count offers from `rollout.cands`, not calls.
- Land-2 wins at 30 starts fall on disjoint starts between rollout and hybrid: a single start's outcome is a
  trajectory property, so a per-start "this start is winnable" reading is wrong.
- Six starts per LLM arm cannot resolve a prompt change: across v1/v2/v3 one start moves by up to 6 lords at 300M
  (paired differences v1 - v2: -2 -4 +5 +2 +6 -2, SD 4.1).


## Waiting on Dave

- **Fund a 130-start hybrid against rollout comparison, or close step 4.** At the cmd14 medians (rollout 17 minutes a
  run, hybrid 24, three runs at a time at par 5), 100 more starts per arm is about 23 hours of this machine (rollout
  about 9.5, hybrid about 13) and about $11 of Haiku. Recommendation: do
  Open 2's cheaper ablation first; fund the large run only if removing the LLM's winning candidates changes outcomes.

## Next session

Message midwinter (or check `ListAgents`) that the merged build is in `bin/` and gated, then do Open 1 (six scripted
runs, about 20 minutes). Then Open 2's ablation unless Dave has decided on the large run. The prompt that starts it
is `/resume commander`.
