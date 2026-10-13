# Commander: handoff

Updated 2026-10-13 by the session that ended at commit `af8d692` (plus the handoff commit after it).

## Resume point

- Last work commit: `af8d692` commander: field-fight posture fix; side 2 on land 2 is beaten by destroying its two
  field groups. Before it `36b21d2` (local-side provisioning; land 2 won by the rollout policy).
- Working data: `M68000/scratchpad/cmd4/` (provisioning runs, l1 and l2 per policy, `l2/rollout_g` the dropped graded
  starve term), `cmd5/` (posture fix runs, `l2/none` with a snapshot every 25M, `l2/post` the A/B), `cmd6/` (the dropped
  pre-contact posture rule), `cmd7/` (gate re-runs). `python3 commander/runstat.py [--every M] <dirs>` reads any of them.
- Start from: `scratchpad/cmd3/l2build/l2_built.snap` (campaign land 2, at its first `$f898`); rebuild with
  `campaign_next.sh scratchpad/cmd2/l1/llm/final.snap 2`. Land 1: `pm123/win/l1_built.snap`. Land 3 is not built:
  `campaign_next.sh scratchpad/cmd4/l2/rollout/final.snap 3` (or from a replay of `runs/l2_rollout`).
- Uncommitted work left behind: none.

## Proven so far

All in `reversing/powermonger/commander/README.md`; every gate re-run from its promoted location.

- Orders from any slot (`gate_inject.sh` 7/7, `gate_orders.sh` 57/57, `gate_ungated.sh` 52/52, `gate_local.sh`), retire
  verdicts (`gate_retire.sh`), order cell = cell centre (`gate_cellpt.py` 16/16), pigeons (`pigeon/gate_pigeon.sh` 7/7).
- Deterministic replayable loop (`gate_loop.sh`, `gate_loop_side1.sh`); A* legs 8/8 (`gate_move.sh`); exact rollouts
  (`gate_rollout.sh` 20/20, re-run after each change this session).
- Provisioning (local side: top up at own lords, fetch below 40 meals, every get food at posture 2, `$6762` chain trimmed):
  land 1 won at 215M by scripted and rollout (was 455M / 440M), scripted captain food never under 200 (land 1) or 117
  (land 2). Land 2 **won by the rollout policy at 1120M** (`runs/l2_rollout`, replay byte-identical, `$1a4da` 1 hit,
  `$1a5b2` 0).
- Field-fight posture: `$5590` kills at the winner's posture 2 and routs home at 4. `gate_posture.sh` (one variable,
  30M per arm from the land-2 300M snapshot): 34 kills / 34 routs / captain dissolved against 49 / 4 / captain alive.
  Scripted sends posture 2 to a local group fighting an enemy group (fires once on land 2; land 1 and the rollout win
  unchanged byte for byte).
- Side 2 on land 2 is the game's AI: two field groups sweep side 3's lords from the south, then march on side 1's
  capital (346M with no orders). The rollout win destroyed both groups (captain at posture 2, left over from a get
  food), after which side 2 made no group for 800M steps (one run). Alliance cannot stop it (strategy.md "Diplomacy").

## Open, in priority order

1. **Scripted's land-2 loss after the fight.** The posture fix keeps the captain alive with 4 men, but side 1 has lost
   every lord to side 2's remaining group and the captain sits camped until 1470M. Candidates: after a costly fight
   fall back to the nearest own lord with men (or, with no lord, attack the weakest lord within reach at posture 2);
   keep the captain at home while side 2's groups are alive and let them come to it (the rollout win's pattern).
   Proof: a won land 2 for the scripted policy, then the same win under a second seed (item 3).
2. **Rollout food blindness.** Inside a 40M horizon food costs nothing until it hits 0, so the rollouts took an attack
   over Scripted's get food at every offer; the winning run starved from 375M to 550M (30 men to 4) and survived by
   luck. A graded starve term (0 at 40 meals, 0.5 at none) did not fix it (one run, `cmd4/l2/rollout_g`). Try a longer
   horizon only for get-food candidates, or score the food the candidate leaves against the captain's eating rate.
3. **Evaluation across seeds** (pm143/lands, pm121/k*), each policy against the unpoked game, so the land-2 result is a
   rate. One run per policy per land so far, on a chaotic game: the pre-contact posture rule flipped a win to a loss.
4. **Why side 2 makes no new group** after losing both: it attacks lords at posture 4 (a conquered captain can defect)
   and fights groups at posture 2. Check `$26d0` (group creation) hits for side 2 over the rollout win's 315M..1120M.
5. LLM prompt: add captain food against trip cost and enemy groups near the captain; re-run land 2 and rand1 side 3 on
   two seeds against the current prompt (the earlier prompt regression: `s1/llm_s3` against `llm500`).
6. Land 3: build it from the land-2 win and play it.
7. Movement with rollouts (`--policy rollout` refuses `--move`); state-space forecaster (plan step 5); smaller items
   (side-0 peace bit from the `$c706` clobber, sender-word readers, `$25d6` rebuilding slot 0, UI click with side 1's
   slot held).

## Known traps

The PowerMonger traps in `sessions/powermonger.md` apply.

- Killing `loop.py` leaves its emulator children (the loop's own and up to `--par` rollout workers) running, and a
  restarted run in the same directory then shares it with them: `pkill -9 -f 'scratchpad/<run dir>'`, then check
  `pgrep -fl <run dir>` is empty, before restarting.
- A rollout process loads `rollout.py` and `loop.py` once at start: editing them mid-run changes nothing in that run
  (useful for an A/B, misleading otherwise).
- Every local-side rule in `Scripted` is gated on `local` so side-3 gate runs stay byte-identical; `gate_rollout.sh`'s
  choices still depend on Scripted, so re-run it after any change and update its count.
- `Scripted` skips a group whose lead object is missing, so a 0-man captain group is never ordered again, and the land
  does not end while its owner word stays 1 (the retire rule needs no lord and no man).
- Rollout decisions with a retreat or captain fork cost a 5-candidate rollout every decision while the captain is
  threatened (land 2: 58 rollouts, about 820 s on a loaded machine).
- On rand1 every AI group's lead holds a Boat: movement tests need `prep.py`'s boat stripping.
- An injected order sets no pending word and lasts one tick in the slot: write a decision's orders `--gap` apart.
- `claude -p --output-format json` output carries session and account metadata (`*.cli.json`): never commit it.
- `$57fba` is rebuilt every tick and can be read torn; score from observe's totals.
- `loop.py --replay` takes the log path relative to the current directory (pass an absolute path).

## Next session

Work Open 1: give the scripted captain a fallback after a costly field fight (recruit at an own lord, or hold at home
while side 2's groups live), re-run land 2 scripted (and rollout as the control) and check with `runstat.py --every 25`
that side 2's two groups die and the captain keeps men. Then start Open 3 (seeds) so the land-2 numbers become rates.
The prompt that starts it is `/resume commander`.
