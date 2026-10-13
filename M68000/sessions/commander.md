# Commander: handoff

Updated 2026-10-13 by the session that ended at commit `136e461` (plus the digest and handoff commit after it).

## Resume point

- Last work commit: `136e461` commander: rollout score values the local captain, idle/threatened captain forks with a
  retreat; campaign land 2 built (campaign_next.sh) and lost by every policy.
- Working data: `M68000/scratchpad/cmd3/` (gitignored). Run records `cmd3/l1/{rollout,rollout_r}`,
  `cmd3/l2/{none,scripted,llm,rollout,rollout_r}` (`decisions.jsonl`, `final.snap`, `dec/<step>.snap` per rollout
  decision); `python3 commander/runstat.py <dirs>` summarises them. Earlier records: `cmd2/` (land 0, land 1, rand1).
- Start from: `scratchpad/cmd3/l2build/l2_built.snap` (campaign land 2, lands 0 and 1 conquered, at its first `$f898`).
  Rebuild: `campaign_next.sh scratchpad/cmd2/l1/llm/final.snap 2` (byte-identical). Land 1: `pm123/win/l1_built.snap`.
- Uncommitted work left behind: none.

## Proven so far

All in `reversing/powermonger/commander/README.md`; every gate re-run from its promoted location.

- Orders from any slot, local side 1 included: `gate_inject.sh` 7/7, `gate_orders.sh` 57/57, `gate_ungated.sh` 52/52,
  `gate_local.sh`; a `$2e` ends the land with the observed ratio's verdict (`gate_retire.sh`); order cell = cell centre
  (`gate_cellpt.py` 16/16). Orders by pigeon (`pigeon/gate_pigeon.sh` 7/7).
- Decision loop deterministic and replayable (`gate_loop.sh`, `gate_loop_side1.sh`); A* legs 8/8 (`gate_move.sh`);
  exact rollouts, fork determinism 20/20 (`gate_rollout.sh`, re-run this session).
- Rollout score with the captain (land end win/loss, captain men lost, captain starving) and captain forks with a
  retreat: off the local side the 300M side-3 gate run is byte-identical to the previous code.
- Campaign: land 0 won by every policy (`gate_win.sh`); land 1 won by the LLM (180M), the baseline (455M) and now the
  rollout policy (440M; lost at 725M before the captain score); `campaign_next.sh` builds land 2. Land 2 lost by every
  policy (no orders 346M, baseline 444M, LLM 298M, rollout 229M, rollout + retreat 460M), each loss `$1a5b2` 1 hit,
  each win `$1a4da` 1 hit. README "The campaign" table.

## Open, in priority order

1. **Keep the captain fed.** Three of five land-2 losses and the old land-1 rollout loss are the captain starving; on
   land 2 side 1's own lords hold 0 food when it does (`dec/330000000.snap`..`370000000.snap`), so get food at an own
   lord cannot help. Candidates to try: take food from each conquered town right after the conquest (the game's own
   `$6762` chain at posture 4; Scripted only follows it after 20 camped ticks), drop the rollout's K cut of get food
   when the captain's food is under its trip cost, and a food-pile pickup (`$06` on a cell). Proof: land 2 played past
   460M with the captain's food never at 0, then a won land 2.
2. **Side 2 on land 2.** The game's side 2 grows from 2 lords to 8-9 in every run, whatever side 1 does (even with no
   orders). Find what it does (`hits` on `$6c32`/`$6b38` attributed per side by the packet's side byte, CLAUDE.md) and
   whether side 1 can pre-empt it (attack side 2 early while it has 2 lords) or ally with it (Diplomacy, `$1e`).
3. **LLM prompt.** The land-2 LLM ignored side 2 and its own food (README table row). Add the captain's food against
   the trip cost and the enemy groups' strength near the captain to the observation; re-run land 2 and rand1 side 3 on
   two seeds against the current prompt before keeping it (the earlier prompt regression: `s1/llm_s3` against `llm500`).
4. **Evaluation across seeds** (pm143/lands, pm121/k*), each policy against the unpoked game, so the tables become rates.
5. Movement with rollouts (`--policy rollout` refuses `--move`); the Mover's stall timer from pigeon delivery.
6. State-space forecaster (plan step 5): train on rollout traces; the walker still needs the job dispatchers.
7. Smaller: the side-0 peace bit left by the `$c706` clobber; readers of the sender word beyond `$6af2`/`$25d6`;
   `$25d6` rebuilding slot 0 while the harness holds it; a UI click while the harness holds side 1's slot.

## Known traps

The PowerMonger traps in `sessions/powermonger.md` apply.

- `gate_rollout.sh`'s side-3 choices depend on Scripted: after any change to Scripted, re-run the gate and update its
  count; the old `cmd2/gate_rollout.txt` (15 equal) predates later baseline commits and its choices no longer match.
- Rollout decisions with a retreat or captain fork cost a 5-candidate rollout every decision while the captain is
  threatened: land 2 took 895 s for 460M steps (39 rollouts) with four other emulators sharing the machine.
- On rand1 every AI group's lead holds a Boat (byte 33 = `$0a`): movement tests need `prep.py`'s boat stripping.
- An injected order sets no pending word and lasts one tick in the slot: write a decision's orders `--gap` apart.
- A side with no lord and no men never ends the land (captain owner word stays 1): the loop retires such a side.
- `claude -p --output-format json` output carries session and account metadata (`*.cli.json`): never commit it.
- `$57fba` is rebuilt every tick and can be read torn; score from observe's totals.
- `loop.py --replay` takes the log path relative to the current directory (pass an absolute path).

## Next session

Work Open 1 on campaign land 2 (`cmd3/l2build/l2_built.snap`): make the captain take food from towns as it conquers
them (rollout candidate and Scripted's follow-up), re-run the rollout and baseline policies to 2G, and check with
`runstat.py` that the captain's food stays above 0. If land 2 is then still lost, look at side 2's growth (Open 2)
before touching the LLM prompt (Open 3).
