# Commander: handoff

Updated 2026-10-13 by the session that ended at commit `b51c614` (plus the digest and handoff commit after it).

## Resume point

- Last work commit: `b51c614` commander: campaign land 1 won by the LLM (180M steps, 10 calls) and the baseline (455M).
- Working data: `M68000/scratchpad/cmd2/` (gitignored; every gate rebuilds its outputs under `$CMD_WORK`, default
  `scratchpad/cmd1`). Run records: `cmd2/{m1,l1,s1}/<policy>/decisions.jsonl` (land 0, land 1, rand1 side 1),
  `cmd2/llm500`, `cmd2/rollout1g`. Agent outputs: `cmd2/agents/<name>/`.
- Start from: `scratchpad/pm123/win/l1_built.snap` (campaign land 1, won by the LLM and the baseline) or
  `pm123/win/m1_win.snap` / `map_cont.snap` to build land 2 (see Open 1).
- Uncommitted work left behind: none.

## Proven so far

All in `reversing/powermonger/commander/README.md`; every gate re-run from its promoted location.

- Orders from any slot, local side 1 included: `gate_inject.sh` 7/7, `gate_orders.sh` 57/57, `gate_ungated.sh` 52/52
  (go to, home, alliances, invent throttle, equip), `gate_local.sh`; a `$2e` ends the land with the observed ratio's
  verdict (`gate_retire.sh`). An order cell is the cell centre (`gate_cellpt.py` 16/16).
- Orders by pigeon: second orders, the dead-sender leak after a commander dies, the pending word is stale AI state
  (`pigeon/gate_pigeon.sh` 7/7).
- Decision loop: one piped REPL, 3-7% overhead, deterministic and replayable (`gate_loop.sh`, `gate_loop_side1.sh`).
- A* legs as go-to orders arrive where direct orders stick, 8/8 pairs (`gate_move.sh`); walker per tick 245,839/245,840
  ticks, the 206 disagreements explained (`walk/`).
- Exact rollouts, fork determinism 15/15 (`gate_rollout.sh`).
- Scripted baseline with posture 4 attacks, the `$6762` chain and empty-group recruiting: level with the game's AI on
  four starts (README table). Trade food rule corrected in economy.md (`py/gate_trade.py` 268/268).
- Wins as side 1: campaign land 0 by every policy (`gate_win.sh`: twice identical, `$1a4da` runs); campaign land 1 by
  the LLM in 180M steps / 10 calls / $0.53 and by the baseline in 455M (`runs/l1_llm/` replays to the same snapshot).

## Open, in priority order

1. **Play the campaign on.** Build land 2 (and on) from a won land: `m1_win` → Continue Conquest → pick a land next
   to a conquered one (`py/drive_win.sh` drove land 0 → land 1; strategy.md "The campaign"), then run all policies
   on it. Proof: lands won per policy, steps and calls to win, each win's `$1a4da`.
2. **Rollout score that values the captain.** The rollout policy lost land 1 with 5 lords against 2 because its
   F/E score ignores the local captain group. Add a large penalty for captain-group men or health lost (or a land-end
   loss inside the horizon) and re-run land 1; proof: a won land 1 and no loss on rand1 side 3 against the current table.
3. **LLM prompt regression.** With the pigeon and posture guidance (current `prompt_system.txt`) the side-3 rand1 run
   issued 12 orders in 25 calls (2 attacks) and ended 5 lords / 67 men at 300M, against 22 orders (19 attacks) and
   12 / 73 for the previous prompt (`scratchpad/cmd2/s1/llm_s3` against `cmd2/llm500`). One run each: re-run both
   prompts on two seeds before changing the prompt; the land-1 win used the current prompt.
4. **Evaluation across seeds**: several Play Random Land rolls (pm143/lands, pm121/k*) with side 1 and an AI side,
   each policy against the unpoked game, so the README tables become rates, not single runs.
5. Movement with rollouts (`--policy rollout` refuses `--move`) and the Mover's stall timer started at pigeon delivery
   (README "Orders by carrier pigeon": 1.2-1.5M steps per 1000 world units).
6. State-space forecaster (plan step 5): train on rollout traces; the walker still needs the job dispatchers
   (`$15122`→`$34f2`, `$5cde`/`$155ac`, `$3c08`) and moving targets before it can forecast.
7. Smaller: the side-0 peace bit left by the `$c706` clobber (is it read?); readers of the sender word beyond `$6af2`
   and `$25d6` (whole-image scan); `$25d6` rebuilding slot 0 while the harness holds the slot; a UI click while the
   harness holds side 1's slot.

## Known traps

The PowerMonger traps in `sessions/powermonger.md` apply.

- On rand1 every AI group's lead holds a Boat (byte 33 = `$0a`): it walks straight over water, so movement tests need
  `prep.py`'s boat stripping or side 1's captain.
- An injected order sets no pending word and lasts one tick in the slot (`$6a3a` clears bytes 1..3): write each order
  of a decision `--gap` steps apart, and do not re-send on a timer shorter than the pigeon flight (a duplicate pigeon).
- A side with no lord and no men never ends the land (captain owner word stays 1): the loop retires such a side.
- `claude -p --output-format json` prints a list of events whose result event carries session and account metadata:
  `llm.py` keeps it as `*.cli.json` under the work dir; never commit those (`runs/l1_llm/llm_io` holds prompts and
  reply text only).
- `$57fba` is rebuilt from zero every tick: a snapshot can catch it torn (5 of 800 reads); score from observe's totals.
- `loop.py --replay` takes the log path relative to the current directory (pass an absolute path).

## Next session

Build campaign land 2 from `pm123/win/m1_win.snap` (Continue Conquest, pick a land adjacent to land 0 or 1) and run
the baseline, LLM and rollout policies on it as side 1 (Open 1); fix the rollout score's captain blindness first
(Open 2) so all three policies are worth comparing. Then start the multi-seed evaluation (Open 4).
