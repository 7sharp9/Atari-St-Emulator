# PowerMonger: handoff

Updated 2026-10-12 by the 152nd session, a single-session pass on Open 3 (save-disk geometry), which needed an emulator change: `8fd3fe4` (emulator), `e86ef4c` (CLAUDE.md), `f107d9d` and `2b69d55` (PowerMonger docs and `py/saveload/format_proof.sh`), then the handoff commit.

## Resume point

- Last commits of this workstream: `8fd3fe4`, `e86ef4c`, `f107d9d`, `2b69d55`, then the handoff commit.
- Working data: `M68000/scratchpad/pm152/` (gitignored): `format/` and `format2/` the FORMAT drives (`proof_*.snap`, `req.png` the save-disk requester, `p_ow.png` the OVERWRITE? requester, `zero.st`), `regress/old|new/` the game snapshot compare of the emulator change. The 151st pass's data is in `pm151/` (`ab/` the reverse A/B, `r1/` the unaided 1G run of `pm142/rand1`); the 150th in `pm150/` (`BRIEF.md`, `reports/`, `arms/nat/`, `saveload/out/`).
- Start from:
  - `scratchpad/pm142/rand1.snap`: Play Random Land with two player captains. Unaided, side 3 sweeps the land and the player's group dissolves near 650M steps (`pm151/r1/`).
  - `pm143/run/rand1_s1.snap`: the FILE-panel drives.
  - `pm150/saveload/out/file.snap`: FILE panel open, slot A selected (start of `format_proof.sh` and `roundtrip.sh`).
  - `pm123/win/m1_ready.snap`: mission 1 conquered.
  - `pm148/arms/long/M2G_k34_c5.snap`: `bp 668c` after 233,300,606 steps.
- Uncommitted work left behind: none from this workstream. Not this workstream's: `.obsidian/`, `Cadaver/`.

## Proven so far

Older gates carry over unchanged; the list is in `strategy.md`, `ai.md` and `economy.md`, with reruns from the `py/README.md` table. A sample: entity FSM `py/fsm/repro93..97.py`, `diff_pm99.py` 1847/1847, `gate_orders.py` 61143/61143 over 2273 states (the 13 strategy rows plus the 6 economy rows), `gate_pop.py`, `gate_equip.py`, the commander AI `py/cmdai/` 323/323 + 280/280, and `gate_fsm15.py` 18452/18452.

New in the 152nd pass:

- **The emulator runs the game's own FORMAT** (`8fd3fe4`). `LoadDiskA` uses Hatari's geometry rule (BPB only when its total sectors match the file, else from the size), and Write Track on an `.ST` parses the ID and data fields into sectors. `py/saveload/format_proof.sh` on a zeroed disk: 80 Write Track commands, 10 sectors each, 0 skipped; SAVE A, then SAVE A again shows OVERWRITE? (`$1bed4` 1 hit), OK saves; LOAD A equals the second save in **101,376/101,376** bytes (the saves differ in 2,048). Regression net: verify PASS, diskless 30M identical, selftest 0 wrong 9 skip, `rand1` +30M and six `rt3` round-trip snapshots identical to the old build; the `pm147` save disk goes from 3 failed reads to 0. system.md "The save-disk code", README "Bug 6".

Carried from the 151st pass:

- **`$5778` on a group 0 costs the escort** (`py/cmdai/ab_5778.py` reverse mode `snap:s:k:val`, 200M steps, one word poked): `X10G_k25_c1` side 3 escort 46 → 0, attack 0 → 7, kills 0 → 18; `M2G_k14_c3` side 4 escort 247 → 0, attack 0 → 3; the third case's group never decided (2 bytes differ). The freed groups attack instead of escorting. No natural state combines it (k25 side 2's group 0 holds an offset for 10G steps but its only other group dies fighting). strategy.md "What the overwrite costs".
- **A drained side still attacks before it transfers** (by the gated predicate): the transfer needs a `D7 != 0` group of 1 to 4 men, which comes from a defector when the AI side *gains* a lord, or a land with no weak enemy lord. `$6522` has no lord test. Unaided `rand1` 1G: `$668c` 0, side 3 takes 13 of 14 lords. strategy.md "Why a drained side is not enough".

The 150th pass's results (all still current; detail in the topic docs):

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

1. **A player route to `$668c`, restated.** Taking an AI side's lords does not do it (above). The route is a side that has drained its own lords *gaining* a lord whose settlement holds a man (`$550e` then `$5c2c`/`$25d6` gives it a 1..4-man group). A player-caused version: let one of the player's lords fall to a drained AI side (in `pm151/r1` side 2 took player lord 10 in chunk 2), then `bp 668c`; `py/side_dump.py` per chunk shows when a side is drained and which groups can decide. Low value unless the drive is cheap; the five natural hits already prove the arm.
2. **The 19 stuck pending words on sides whose first group is alive.** `watch` the pending word and the pigeon slots from one such snapshot (`py/arms/pending_census.py` lists them).
3. **Mode-graph loose ends** (`py/fsm/mode_edges.py`, `fig/fsm.facts.md`): mode `$66`'s entry route; modes `$04`, `$64`, `$70` that nothing writes; the unreached write `$3c74`; and the claim that `$3c` is entered via the previous mode (trace one rout).
4. **Graphics cross-checks** (`port/SPEC.md` "Whether they still run"): the F# halves no longer compile (`walkQ0` is now `Fill.planQ0`; `EntityCtx.Zoom` and `EntityRec.B15` are missing). Fix and promote `order_test.fsx` and `baseline.fsx`; settle pm91's 3061 against 2881 px; re-export the `pm74_late`/`pm78_settle`/`pm119` inputs with `objs`. The Ruin overlay `$119b2` is not ported: capture at (22,46) or (29,63) on mission 1.
5. **UI leftovers.** The `$c5ee` entry contract; word `-36` in the sound pick; sound event 17 is queued and cleared but never played (`bp 12820`); the double handling of a captain-box click in transfer mode (`bpc 133d4 2`, watch `$2df96`); `$04` sent from a group that has a sender (by pigeon, inferred); the other `$7658` dialog ids; the person panel's Stock rows.
6. **Small checks.** `$4a7a` has no model gate, and opponent class `$a` is unseen. The season after a LOAD (`$57fd0` writers); posture 5 from `$67d0` (`rand & 3` + 2); an exact water test in `stuck_census.py` (replay `$1648e`); an indexed-access scan for `$58054`; a pile record's words 8 and 28; the crack's `$b842` patch; the `$54` merchant loop `$15b0c`; health cap and food (`$5ccc`); `$4342`'s arrival branch.
7. **The stall on the original machine.** A Hatari run past clock 32768 with a camped group (low priority).
8. **FORMAT's other branches.** ARE YOU SURE (`$1bec2`): run `format_proof.sh`'s first two clicks with `disk scratchpad/powermonger.st` mounted instead of `zero.st` (`$1bd38` then opens `SPRITE8.DAT`). The write-protect requester `$1bf04` needs a write-protect flag in `MMU.fs` (emulator change, low value).

## Known traps

- **Parallel agents on shared docs: one writer per doc at a time.** Owners edit in place. Explorers write only under `scratchpad/pm150/<area>/` and report suggested prose. The orchestrator saves each report under `reports/` with its PENDING items, then hands a free doc to one merge agent with the report paths. Spot-check one claim per agent against the listing: every check held this pass.
- **Merge agents leave scratch citations.** Grep the docs for `scratchpad/pm150/.../*.py` before committing and repoint them to the promoted `py/` path. Data paths in scratchpad may stay.
- **`hits` can overcount by one** (now in CLAUDE.md). The "66 draws" and "`$57fec` 180" readings were this.
- **The options panel moves after a requester.** After FORMAT or an OVERWRITE? requester, FILE is at (111,92); after a plain SAVE or LOAD it is at (142,92). Render a frame before trusting a click position.
- **Disk writes live only in process memory** (the host `.st` is never written, and a snapshot does not hold the disk): a FORMAT-then-SAVE proof must run in one process.
- **REPL `m <addr> <len>` takes a decimal length**: `m 4f970 6c` aborts the REPL and loses the snapshot that follows.
- **Group frames.** Group views are `76 + 316*side + 2k`. `n(A1)` is the side-record frame and `n-76(A3)` the group-offset frame: `148(A1) = 72(A3)`, `136(A1) = 60(A3)`.
- **`py/cmdai/` scripts default to `PM_WORK=scratchpad/pmwork`.** Set `PM_WORK` explicitly for a rerun.
- **`gate_fsm15.py nat` reads `scratchpad/pm150/arms/nat/`.** Copy `nat/` along with it if `PM_WORK` changes.
- **The clock word.** `$2df72` is the low word of the long `$2df70`. A poked clock or a LOAD moves the stall onset.
- **A "never natural" census holds only for its sample and pool.** Count the eligible pool and the steps alive.
- **Runs past about 4.5G steps can have a stalled commander.**
- **The lord record's side is byte 0** (`$4e514`, 32 bytes), its cell the word at +4. Reading byte 5 as the side (from `$69b4`'s `cmp.b 5(A2)`, a different base) gives garbage sides; use `py/side_dump.py`.
- **`ab_5778.py`'s `$65f4` counts every side.** A case whose poked side never decides still shows escorts (`M2G_k14_c1`: 49/49 from another side); read the end-state diff before crediting a hit change to the poke.
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

Open 2 (the 19 stuck pending words on sides whose first group is alive: one `watch` drive from a snapshot `py/arms/pending_census.py` lists) or Open 3 (mode-graph loose ends from `py/fsm/mode_edges.py`). Open 8's ARE YOU SURE branch is a cheap drive if a short task is wanted. Open 1 only if a cheap drive of a player lord falling to a drained AI side turns up. Hatari is available for Open 7 through an agent (Dave's go-ahead, 2026-10-12).
