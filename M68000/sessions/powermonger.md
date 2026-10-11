# PowerMonger: handoff

Updated 2026-10-11 by the 150th session, which ended at the handoff commit after `6ab6e77`. It fanned out 12 agents plus merge passes: the Open 1 doc contradictions resolved, Open 2/3/4/8/9/10 and most of 5 settled live, eight figures added, and no emulator change.

## Resume point

- Last commits of this workstream: `6ab6e77` (all doc, script, figure and `.sym` work of the 150th pass), `3640ad9` (CLAUDE.md: the `hits` overcount and the save-disk BPB trap), then the handoff commit.
- Working data: `M68000/scratchpad/pm150/` (gitignored). `BRIEF.md` is the shared agent brief; `reports/*.md` holds each agent's report, as saved and spot-checked. The data sits under `<area>/` (`captain2`, `saveload/out`, `arms/{x,nat,pig,rerun}`, `weather/{trial,alli,coast}`, `small/{camp,finale,replay,link}`, `sim_unread/ab`, `docfix_*`). Earlier data is still in `pm149/`, `pm148/arms/long/` (the chunk snapshots) and `pm143/` (the Play Random Land roll). `scratchpad/pm150/arms/nat/` is the natural corpus that `py/fsm15/gate_fsm15.py nat` reads.
- Start from:
  - `scratchpad/pm142/rand1.snap`: Play Random Land with **two player captains** (the second-captain and `$04` drives use it).
  - `pm143/run/rand1_s1.snap`: the FILE-panel drives.
  - `pm123/win/m1_ready.snap`: mission 1 conquered.
  - `pm148/arms/long/M2G_k34_c5.snap`: `bp 668c` after 233,300,606 steps.
  - `scratchpad/pm150/saveload/out/file.snap` plus `blank.st`: a save and load round trip.
- Uncommitted work left behind: none from this workstream. Not this workstream's: `.obsidian/`, `Cadaver/`.

## Proven so far

Older gates carry over unchanged; the list is in `strategy.md`, `ai.md` and `economy.md`, with reruns from the `py/README.md` table. A sample: entity FSM `py/fsm/repro93..97.py`, `diff_pm99.py` 1847/1847, `gate_orders.py` 61143/61143 over 2273 states (the 13 strategy rows plus the 6 economy rows), `gate_pop.py`, `gate_equip.py`, the commander AI `py/cmdai/` 323/323 + 280/280, and `gate_fsm15.py` 18452/18452.

New or changed this pass:

- **Gate results**:
  - `py/gate_proj.py`, with `$1b8c` and `$2776` wired into `kill_rout_5590` (`tools/pm_fsm_ref.py`): 473 states, 5082/5082 with `synth noscreen`; 464/4509 without the lead kills. Nothing is excluded now.
  - `gate_fsm15.py nat` (the natural `$36`/`$38`/`$3a` entries): 822/822 over 99 states.
  - `py/arms/gate_nat_arms.py`: 6/6 states, 28/28 bytes. All five natural `$668c` hits are examined: k25 and k8 take the small-group route; k106, k34 and k50 the large-group route with no target left.
  - `py/cmdai/gate_party_class.py` (`$4de2`): 468/468, rerun fresh by the orchestrator.
- **Opponent class.** `280()` (group +204) is the opponent class, not a phase: 2 lord, 4 group, 6 lone man, 8/`$a`/`$c` other. `292()` is the opponent offset. `$5778` overwrites the class with an entity offset, a game bug: live 1/1; an A/B over 8 cases changed 1 posture (`py/cmdai/ab_5778.py`).
- **Stuck pending words are a game bug** (watch-proven). When a side's first group dies, `$2776` frees its pigeons at `$27c6` without clearing the receivers' pending words; `$4562` then copies the dead sender's negative owner byte (`$45a8`), and `$3e06` skips owners <= 0 (`$417a`). Census by `py/arms/pending_census.py`: 595 pending words, 187 dead-sender, 219 orphan.
- **Second captain, live** (`py/captain2/`, `pm142/rand1`).
  - The pigeon order: `$4562` 1 hit; it lands about 9.97M steps later; posture 3 → 2.
  - The pigeon icon is drawn at (71+40j, −4) in the status strip.
  - `$04` transfer: 13 → 7 / 0 → 6, with 6 `$1c04`/`$1c96` pairs.
  - The icon-floor table entries are `$135fc`, `$1361e`, and so on: the old doc addresses were 2 too high.
- **SAVE/LOAD, live** (`py/saveload/`). A round trip matches 101,376/101,376 bytes, and a LOAD replaces the whole land. It keeps the destination's clock and restores the camp stamps, so the first `$65b4` comes at clock = min stamp + 20: predicted 2108, observed at 276,745,802 steps.
- **External claims.**
  - Deforestation does not change the weather (3 arms, `py/season/tree_weather.py`), and felled trees regrow one per season.
  - Posture picks the woodcutters' goods at `$5fa0` (`py/orders/posture_work.py`), but plays no part in alliance acceptance (6/6); it only picks the verb.
  - Men stall at coasts: there is no pathfinding (`py/fsm/stuck_census.py`).
- **Code read plus live.**
  - Requesters, the line editor and Modem Message, and the radios (`py/ui/req_panels.py` 7/7, `py/link/radio.repl`).
  - HUD bars, the `$17a46` mode icon, and sound-ack events 31..36 (`py/ui/sndpost.repl`).
  - Format `$1ba72` (code read).
  - Camp marker frames (`camp_fire_frames.png`).
  - The finale is a crowning: 7/7 frames rebuilt (`py/season/finale_delta.py`, `finale_crown.png`).
  - `$58054` has no effect.
  - A spell draws 65 times.
  - The link-rebuild causeway comes from `$2266` `_setup_p`, which gives a linked side a random start plus a road (a REPLAY MAP control paints none).
  - The Ruin is kind `$0a`, placed by the town layouts at `$302a`.
- **Doc corrections.**
  - Mode table: 74 entries, `$00..$92`.
  - `$168ee` is the walk-path table `_flights`.
  - `$1c390`/`$1c340` are serial.
  - `$550e`: 10 heartbeat / 17 conquest calls.
  - Mission 1 loyalty starts at 608 and the first winter revolts to the same side.
  - Sprite categories run 0..`$2c`.
  - The fill reads two colour planes.
  - The text segment is `$10a6..$1c48a`.
- **Figures.** `fig/` holds eight SVGs, each with a `.facts.md`, placed in strategy.md, ai.md and economy.md (README files table). The two mode graphs are generated from the code by `py/fsm/mode_edges.py`.

## Open, in priority order

1. **A natural player route to `$668c`.** The code read says: capture or drain every lord of an AI side while its commander lives. Drive it, and check whether `$6522` still runs for a side with no lords (`hits 6522`). Also the 19 stuck pending words on sides whose first group is alive: `watch` the pending word and the pigeon slots from one such snapshot (`py/arms/pending_census.py` lists them).
2. **Does the `$5778` overwrite ever cost an escort?** It needs a natural state with the offset in group 0 and another free group of that side (link 0, state 6 or 9). Census the `pm148/arms` chunks with `py/cmdai/phase_census.py`, or run k25 long (its group 0 holds an offset through all 40 X10G chunks). Also: `$4a7a` has no model gate, and class `$a` is unseen.
3. **Emulator save-disk geometry.** `LoadDiskA` should not trust BPB text on a non-TOS disk. This is an emulator change behind the regression net (shared `*.fs`: coordinate first). It unblocks driving FORMAT (`$1ba72`, Write Track probably unimplemented) and the OVERWRITE? requester `$1bed4`.
4. **Mode-graph loose ends** (`py/fsm/mode_edges.py`, `fig/fsm.facts.md`): mode `$66`'s entry route; modes `$04`, `$64`, `$70` that nothing writes; the unreached write `$3c74`; and the claim that `$3c` is entered via the previous mode (trace one rout).
5. **Graphics cross-checks** (`port/SPEC.md` "Whether they still run"): the F# halves no longer compile (`walkQ0` is now `Fill.planQ0`; `EntityCtx.Zoom` and `EntityRec.B15` are missing). Fix and promote `order_test.fsx` and `baseline.fsx`; settle pm91's 3061 against 2881 px; re-export the `pm74_late`/`pm78_settle`/`pm119` inputs with `objs`. The Ruin overlay `$119b2` is not ported: capture at (22,46) or (29,63) on mission 1.
6. **UI leftovers.** The `$c5ee` entry contract; word `-36` in the sound pick; sound event 17 is queued and cleared but never played (`bp 12820`); the double handling of a captain-box click in transfer mode (`bpc 133d4 2`, watch `$2df96`); `$04` sent from a group that has a sender (by pigeon, inferred); the other `$7658` dialog ids; the person panel's Stock rows.
7. **Small checks.** The season after a LOAD (`$57fd0` writers); posture 5 from `$67d0` (`rand & 3` + 2); an exact water test in `stuck_census.py` (replay `$1648e`); an indexed-access scan for `$58054`; a pile record's words 8 and 28; the crack's `$b842` patch; the `$54` merchant loop `$15b0c`; health cap and food (`$5ccc`); `$4342`'s arrival branch.
8. **The stall on the original machine.** A Hatari run past clock 32768 with a camped group (low priority).

## Known traps

- **Parallel agents on shared docs: one writer per doc at a time.** Owners edit in place. Explorers write only under `scratchpad/pm150/<area>/` and report suggested prose. The orchestrator saves each report under `reports/` with its PENDING items, then hands a free doc to one merge agent with the report paths. Spot-check one claim per agent against the listing: every check held this pass.
- **Merge agents leave scratch citations.** Grep the docs for `scratchpad/pm150/.../*.py` before committing and repoint them to the promoted `py/` path. Data paths in scratchpad may stay.
- **`hits` can overcount by one** (now in CLAUDE.md). The "66 draws" and "`$57fec` 180" readings were this.
- **A save disk needs real geometry bytes** (now in CLAUDE.md): `py/saveload/mk_savedisk.py`.
- **REPL `m <addr> <len>` takes a decimal length**: `m 4f970 6c` aborts the REPL and loses the snapshot that follows.
- **Group frames.** Group views are `76 + 316*side + 2k`. `n(A1)` is the side-record frame and `n-76(A3)` the group-offset frame: `148(A1) = 72(A3)`, `136(A1) = 60(A3)`.
- **`py/cmdai/` scripts default to `PM_WORK=scratchpad/pmwork`.** Set `PM_WORK` explicitly for a rerun.
- **`gate_fsm15.py nat` reads `scratchpad/pm150/arms/nat/`.** Copy `nat/` along with it if `PM_WORK` changes.
- **The clock word.** `$2df72` is the low word of the long `$2df70`. A poked clock or a LOAD moves the stall onset.
- **A "never natural" census holds only for its sample and pool.** Count the eligible pool and the steps alive.
- **Runs past about 4.5G steps can have a stalled commander.**
- **Group fields are structure-of-arrays.** Word 28 is the owner, word 52 the men.
- **"Aggression" has two meanings:** the rank `+148` (display only) and the posture `+136`.
- **`callcap` masks interrupts.** It cannot run the disk transfer, and a sound wait spins unless `$2c993 := 0` (`gate_proj.py` lead kills).
- **A resumed snapshot may have no disk.** Make `disk scratchpad/powermonger.st` the first REPL line.
- **REPL `w` writes a longword.** Read the neighbours first. A longword `w` at an odd address kills the REPL.
- **Poking `$2df92`/`$2df94` does not stick.** Use mouse holds of at least one tick.
- **`hits` must start before the run it counts.**
- **Doc rewrites through `py/docs/doc_pieces.py`:** edit the pieces, not `out/joined/`.
- **Earlier traps still apply.**
  - The port stays a renderer.
  - The `port/` identifiers still say herd/shepherd, morale, `nation_kind`.
  - A full `pm_export.py` rerun regresses `entities.json`.
  - Do not reopen the SingleStepTests track.

## Next session

Pick Open 1: a drive that takes every lord of one AI side while its commander lives, then `bp 668c`, with a `hits 6522` control on a side that has no lords. Run Open 2's census in parallel, since it is cheap and pure Python over existing chunks. If an emulator session is free, Open 3 (save-disk geometry) is a small, well-scoped emulator fix. Keep the method of this pass: one owner per doc, reports saved to `scratchpad/pm<N>/reports/`, a spot check per agent, merge agents for free docs, and a scratch-citation grep before committing.
