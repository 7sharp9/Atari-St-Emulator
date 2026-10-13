# Commander: handoff

Updated 2026-10-14 by the session that ended at commit `f455c7b` (plus the digest and handoff commit after it).

## Resume point

- Last work commit: `f455c7b` commander: land 2 as a rate (`seeds.sh`, six starts per policy); every loss is the
  captain's lead killed in melee by a posture-2 side-2 group. `b9cb0a2` is a CLAUDE.md commit from the same session.
- Working data: `M68000/scratchpad/cmd9/` (the seed set: `start/o0..o5`, `<arm>/o<k>` for scripted, evade, diseng,
  avoid, rollout; `o1_health/` replay snapshots of scripted o1 at 190M..211M; `loop_all_arms.py`, the loop.py with the
  dropped rules, for re-running those arms), `cmd8/` (single-run probes: the 290M A/B, strength/hunt/evstr runs, the
  replays `scr_rep`, `o1rep2` (212M, the `bp 564e` trace), `d1rep`, `r0rep` (the rollout win at 220M..315M)).
  `python3 commander/runstat.py [--every M] <dirs>` reads any run.
- Start from: `scratchpad/cmd3/l2build/l2_built.snap` (campaign land 2 at its first `$f898`); perturbed starts are
  `cmd9/start/o<k>/final.snap` (rebuild: `seeds.sh` makes them). Land 1: `pm123/win/l1_built.snap`. Land 3 is not
  built: `campaign_next.sh scratchpad/cmd9/rollout/o0/final.snap 3`.
- Uncommitted work left behind: none.

## Proven so far

All in `reversing/powermonger/commander/README.md`; every gate re-run from its promoted location.

- Orders from any slot (`gate_inject.sh` 7/7, `gate_orders.sh` 57/57, `gate_ungated.sh` 52/52, `gate_local.sh`), retire
  verdicts (`gate_retire.sh`), order cell = cell centre (`gate_cellpt.py` 16/16), pigeons (`pigeon/gate_pigeon.sh` 7/7).
- Deterministic replayable loop (`gate_loop.sh` re-run this session, `gate_loop_side1.sh`); A* legs 8/8
  (`gate_move.sh`); exact rollouts (`gate_rollout.sh` 20/20, re-run this session).
- Provisioning and the field-fight posture fix (land 1 won at 215M by scripted and rollout; `gate_posture.sh`).
- **Land 2 as a rate** (`seeds.sh`, six starts 1M steps apart, start 0 reproducing each policy's earlier run to the
  step): scripted 0/6 won (6 lost, five at 213M..258M); `--evade` 0/6 (5 lost at 292M..730M, one alive at 2G);
  rollout 1/6 (o0 at 1120M; 4 lost at 347M..417M, one alive at 2G at ratio 0). Two dropped rules (pull the captain out
  of melee; also evade posture-2 groups) 0/6 each.
- **How the captain dies.** All 24 losses: the captain's lead at owner -1 and a side-2 group at posture 2 fighting.
  Traced on scripted o1 (`bp 564e` from `cmd8/o1rep2/at_212000000.snap`): the lead killed (owner `$ff`, category `$0c`,
  not encircled), group 0 dissolved by `$2776`, land lost, his army still 27 men. A lead stands off shooting (mode
  `$34`) and dies only after an enemy man reaches him in melee (`$32`): health 95 → 0 in about 5M steps from 208M on
  o1, while in the rollout win the lead never left `$34` through two posture-2 fights. A `$02` go to does not take a
  lead out of melee (diseng o1 at 210M, one case).

## Open, in priority order

1. **What brings an enemy man onto the captain's lead.** It is the whole land-2 loss, and the posture of either side
   does not decide it (the win fought posture-2 groups with the lead at range). 11 of 24 deaths are on a lord's cell,
   13 in the field. Read `$4f68` (ai.md mode `$2c`, the target weighing, `py/diff_4f68.py`) for how a man picks the lead,
   then show it live: from `cmd8/o1rep2` (or `cmd9/o1_health/at_205..208`) `watch` the lead's byte 31 (lead object `$52fe8` on
   o1) and find the enemy man whose word 48 (target link) becomes the lead's object offset, and what he was doing before.
   A proven cause gives a rule to test on the six seeds (`seeds.sh`, add an arm).
2. **Rollout food blindness** (unchanged): inside a 40M horizon food costs nothing until it hits 0; try a longer
   horizon for get-food candidates or score the food left against the eating rate.
3. Seeds for land 1 and rand1 side 3 (`seeds.sh` on `pm123/win/l1_built.snap` and `pm142/rand1.snap`), so those
   one-run results become rates too.
4. **Why side 2 makes no new group** after losing both (`$26d0` hits over the rollout win's 315M..1120M).
5. LLM prompt: captain food against trip cost and enemy groups near the captain; re-run on two seeds.
6. Land 3: build it from the land-2 win (`cmd9/rollout/o0/final.snap`) and play it.
7. Movement with rollouts; state-space forecaster (plan step 5); smaller items (side-0 peace bit from the `$c706`
   clobber, sender-word readers, `$25d6` rebuilding slot 0, UI click with side 1's slot held).

## Known traps

The PowerMonger traps in `sessions/powermonger.md` apply.

- A new `Scripted` rule whose run ends at the same step as the baseline never fired: compare end steps (or count its
  orders in `decisions.jsonl`) before reading an outcome. The first disengage rule (health < 48 at 5M decisions) never
  fired on six seeds, because the lead goes from 74 health to dead between two decisions.
- `loop.py --replay` ignores `--budget` and runs the whole logged run (a 1.4G replay takes about 5 minutes); use
  `--snap-at` to keep the states you need.
- One run per arm on land 2 is noise: from the same 290M snapshot the unchanged scripted policy lost at +30M where the
  original run survived to 1470M (`cmd8/a290/ctl`). Use `seeds.sh`.
- Camped men are mostly not in the object table (side 1 had 4 man objects for a 32-man group at 290M); a per-man census
  works only for a marching group, whose followers point at their lead through word 28.
- Killing `loop.py` leaves its emulator children running: `pkill -9 -f 'scratchpad/<run dir>'`, check `pgrep -fl`.
- A rollout process loads `rollout.py` and `loop.py` once at start: editing them mid-run changes nothing in that run.
- Every local-side rule in `Scripted` is gated on `local` (and `--evade` on its flag) so side-3 gate runs stay
  byte-identical; `gate_rollout.sh`'s choices depend on Scripted, so re-run it after any change.
- `Scripted` skips a group whose lead object is missing; the land does not end while the captain group's owner word
  stays 1 (the retire rule needs no lord and no man).
- Rollout runs on land 2 cost 15 to 40 minutes each on a loaded machine; `seeds.sh` par counts each as 6 processes.
- On rand1 every AI group's lead holds a Boat: movement tests need `prep.py`'s boat stripping.
- An injected order sets no pending word and lasts one tick in the slot: write a decision's orders `--gap` apart.
- `claude -p --output-format json` output carries session and account metadata (`*.cli.json`): never commit it.
- `$57fba` is rebuilt every tick and can be read torn; score from observe's totals.
- `loop.py --replay` takes the log path relative to the current directory (pass an absolute path).

## Next session

Work Open 1: find what sends an enemy man onto the captain's lead. Start from `cmd9/o1_health/at_205000000.snap`
(lead in `$34`, health 95) and run to 208M watching the lead's mode byte and the enemy men's target words; read
`$4f68` for why the lead is picked. Turn the cause into one rule, add it as an arm to `seeds.sh` on the six land-2
starts, and compare its win count against scripted 0/6 and rollout 1/6. The prompt that starts it is
`/resume commander`.
