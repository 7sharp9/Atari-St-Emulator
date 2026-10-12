# PowerMonger: handoff

Updated 2026-10-12 by the 155th session (a short pass: when the minimap is baked, `fd8a1a0`; lessons into CLAUDE.md and the skill, `8f96013`; `py -3` docstrings, `132c826`), after the 154th (graphics cross-checks promoted and rerun, Ruins ported, live-play pending census, FORMAT's ARE YOU SURE: `d5186d9`, `71bc060`, `ae188b6`, `b95f2f0`, `deb2304`, `bc3aac4`).

## Resume point

- Last commits of this workstream: `fd8a1a0` (minimap bakes), `d5186d9` (py/xcheck), `71bc060` (Ruins), `ae188b6` + `b95f2f0` (pending census), `deb2304` (ARE YOU SURE), `bc3aac4` (capture.sh), then the handoff commit.
- Working data: `M68000/scratchpad/pm155/minimap/` (the k60 revolt rerun `pre`/`post`, the mode-3 click and its 50M-step run); `M68000/scratchpad/pm154/` (gitignored): `frames/` the re-exported frame JSONs, `ruin/` and `xcheck/ruin/` the Ruin captures, `format/`, `format2/` the FORMAT drives, `pm83/ pm90/ pm91/` the first fixed copies. The scratch-only F# scripts of passes 83-119 and their inputs were streamed from gpubox into `scratchpad/pm118/`, `pm118b/`, `pm119/` and `scratchpad/pm8x_*`, `pm9x_*`; the frame RAMs `run.sh` reads are now on the Mac. Earlier passes: `pm153/`, `pm152/`, `pm151/`, `pm150/`.
- Start from:
  - `scratchpad/pm142/rand1.snap`: Play Random Land with two player captains.
  - `pm143/run/rand1_s1.snap`: the FILE-panel drives.
  - `pm150/saveload/out/file.snap`: FILE panel open, slot A selected (`format_proof.sh`, `format_sure.sh`, `roundtrip.sh`).
  - `pm123/win/m1_ready.snap`: mission 1 conquered.
  - `pm88_f1.snap`: mission 1 at the port's pose; clear its stuck `$2c993` first (Known traps).
- Uncommitted work left behind: none from this workstream. Not this workstream's: `.obsidian/`, `Cadaver/`.

## Proven so far

Older gates carry over unchanged; the list is in `strategy.md`, `ai.md` and `economy.md`, with reruns from the `py/README.md` table. A sample: entity FSM `py/fsm/repro93..97.py`, `diff_pm99.py` 1847/1847, `gate_orders.py` 61143/61143 over 2273 states, `gate_pop.py`, `gate_equip.py`, the commander AI `py/cmdai/` 323/323 + 280/280, `gate_fsm15.py` 18452/18452, `py/season/gate_1abaa.py` 1084/1084 calls.

New in the 155th pass:

- **The minimap is baked, never tinted, and shows no ownership.** `$107d6` runs only from the land build, the mode-strip click, `click_pr` and `_draw_ca` (from `_add_cap`/`_remove_` when the captain is on the player's side `$57ffe`); modes 0 and 2 stay exact, mode 3 (lord supply) goes stale: on `k60_s1` a strip click bakes mode 3 once, then 50M steps run with 0 bakes, the picture unchanged and 38 of 8064 pixels off a fresh bake (`py/maps/minimap_stale.py`). An AI-to-AI revolt does not re-bake. graphics.md "The minimap and the conquest map".

New in the 154th pass:

- **Every graphics cross-check of the port reruns from the repo**: `py/xcheck/run.sh` (port/SPEC.md "Re-running the cross-checks"). Synthetic quadrant walks 4/4 identical (1020 px each); synthetic blits 12/13 (the melee case differs by design: the port draws `$11c8a`, `pm_render_ref` skips it); real record stream 3061/3061, superseding the first run's 2881 (the current output matches the game's screen at 1889 px against 1182); baseline 162/162; the §6 draw-order table reproduced; `score.fsx` on 14 frames 99.64-99.99% (`pm78_settle` 94.62%).
- **Two exporter gaps fixed**: `dump_frame.py` now exports the 32x32 sheet (zoom 1-3: 95.02-99.06% -> 99.79-99.91%, same frames), and `pm_render_ref.load_ram` walks the `2*[$fdec]` window instead of a fixed 11x11 (zoom 7 95.86 -> 99.89%, zoom 6 98.74 -> 99.93%). Zoom 1-7 terrain away from sprites 99.78-99.95%, sprites 98.2-100%.
- **The port draws Ruins** (`$117e4`: frame `$0a` plus the `$119b2` overlay, frame `word[12] mod 10`, top rows cut by `record[16]`). Mission 1 on each Ruin 98.31 -> 99.82% and 98.41 -> 100.00%; the overlay at counters 70 and 100 752/752 and 783/783 px, with wrong-frame and no-overlay controls at 97.68-98.27% (`py/xcheck/ruin_capture.sh`). `EntityRec` gained `B16`/`W12`; both `entities.json` patched from their source RAMs; stepper 23/23 on both asset sets, Godot builds, walkthrough verifies.
- **Pending census over live play only** (`pending_census.py` skips frozen chunks, `--all` keeps them): 357 words in 183 snapshots, 70 flying, 142 dead-sender, 141 orphan, 4 queued. 11 of the 12 "inherited" words on live-commander sides were frozen post-game RAM; live play has 1 there plus 8 on dead-commander sides. strategy.md "The pending word", README bugs list, `fig/order_pipeline`.
- **FORMAT's ARE YOU SURE is live** (`py/saveload/format_sure.sh`): with the game disk in, `$1bd38` finds it and `$1bec2` asks; CANCEL runs `$1beec` with no write, OK formats it (80 Write Track commands). system.md "The save-disk code".

Carried from the 153rd pass:

- **`$1abaa` (seasons and weather) is gated.** `py/season/gate_1abaa.py` diffs `model_1abaa.py` (dissolve, wrap, weather, rain and snow blit, tree regrowth, sample-player state) against callcaps over every changed byte of the 1 MB: **1084/1084 calls, 735,679/735,679 bytes** in four arms (m1 420, rand1 420, wrapw 240 and felled 4 under labelled pokes), rerun from fresh captures at the promoted path. A call copies about 9 pixels, not 16 (`$1ac04`: steps with `x >> 4 >= $120` copy nothing); winter's season cue is the stop sequence. strategy.md "What `$1abaa` actually is".
- **Inherited pending words, a second pigeon-path bug** (watch-proven on k98 and k118). `$2776` dissolves a group without clearing its pending word, and `$25d6` builds the next captain's group in that slot without clearing it; the new group is never ordered. In live play it accounts for 9 stuck words (1 on a live-commander side, 8 on dead-commander sides; the 154th pass's frozen filter). strategy.md "The pending word", README bugs list.
- **Mode-graph loose ends** (`py/fsm/mode_write_scan.py`, whole image). Nothing writes `$04`, `$64` or `$70`. `$66` is entered only through the `$161f0` water veto (a `$36` step onto water, then a `$10` arrival copies prev `$66`); live 1 of 1 under a one-byte prev poke, 0 unaided in 6 x 200M steps; `fsm_army` gains the dashed edge `$36 -> $66`. `$3c74` is unreached behind a `nop` (an inferred patched `bra.s`; 0 hits in 4.1G steps; reached under `w 3c10 6e026060`). A routed group member never enters `$3c` (`$1b8c`'s `$3c08` call resets the prev); a lone man does (`py/fsm/rout_fate.py`: 23 of 44 on `rand1`). ai.md, `fig/fsm.facts.md`.

Carried from the 152nd pass:

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

1. **Port checks still not run.** Category `byte6` 18, 28, 34, 36, 38, 42 never seen drawn; the plough and siege-engine overlays never seen on screen (a capture of a ploughing farmer or a siege engine, scored by `score.fsx`). The Python reference `pm_render_ref` still skips melee frames; bring it level if the parity checks are to cover them.
2. **A player route to `$668c`.** The route is a drained side *gaining* a lord whose settlement holds a man: let one of the player's lords fall to a drained AI side (in `pm151/r1` side 2 took player lord 10 in chunk 2), then `bp 668c`; `py/side_dump.py` per chunk. Low value unless the drive is cheap; five natural hits already prove the arm.
3. **Mode-graph residue.** An unaided `$66` entry needs a lone man (word 28 = 0), or a Boat follower who lands before the camp, chasing an animal across water: search the `W5G_k108` and long-arm chunk series with `scratchpad/pm153/modes/py/natrun.sh`, grepping `pc=$014fdc` writes of `$66`. Whether the rout stamps that reach no arrival (18 of 44 on `rand1`, 34 of 89 on `k48`) are re-engagements (`$5708`) or run ends: extend `rout_fate.py` with the last writer.
4. **Pending-word residue.** 81 live "unknown" orphans on dead-commander sides (`stuck_classes.py`): the sender record was revived (the player's landing `$4244`) or reused; the k4 inheritance and the k104 `-4` pigeon launch are snapshot reads (`bpc 45a8` with `watch 4c146 26` from `lands/k104.snap` around step 793.8M).
5. **UI leftovers.** The `$c5ee` entry contract; word `-36` in the sound pick; sound event 17 is queued and cleared but never played (`bp 12820`); the double handling of a captain-box click in transfer mode (`bpc 133d4 2`, watch `$2df96`); `$04` sent from a group that has a sender (by pigeon, inferred); the other `$7658` dialog ids; the person panel's Stock rows.
6. **Small checks.** `$4a7a` has no model gate, and opponent class `$a` is unseen. The season after a LOAD (`$57fd0` writers); natural winter snow under the `$1abaa` gate (a lineage one wrap before `pm143/run/rand1_s4`); the divide by zero at `$1ac88` on an empty tree array (a `felled`-style arm with `$4e512 < 12`); posture 5 from `$67d0`; an exact water test in `stuck_census.py` (replay `$1648e`); an indexed-access scan for `$58054`; a pile record's words 8 and 28; the crack's `$b842` patch (and whether `$3c12`'s `nop` is the crack's or the developers'); the `$54` merchant loop `$15b0c`; health cap and food (`$5ccc`); `$4342`'s arrival branch.
7. **The stall on the original machine.** A Hatari run past clock 32768 with a camped group (low priority; Hatari through an agent has Dave's go-ahead).
8. **FORMAT's write-protect requester** `$1bf04` needs a write-protect flag in `MMU.fs` (emulator change, low value).

## Known traps

- **`pm88_f1.snap` has a stuck sample-busy flag.** `$2c993 = $ff` with Timer A stopped (TACR 0), so a camera move that queues a sound waits at `$1ae40` forever; it looks like a dead snapshot. Clear it first with `w 2c990 a8100000` (keeps `$2c990..92`). A pan from the same snapshot may not queue a sound and runs fine, which hides the cause.
- **`zoom_check.fsx` scores sprites as terrain when a sheet is missing.** Its "terrain away from sprites" counts a building it cannot draw as a terrain miss; frames need `sheet_prop32`/`sheet_prop16` from the current `dump_frame.py`.
- **`pm121/flip/k60_flip_pre`/`_post` do not straddle the revolt**: the settlement owner byte is already 3 in both (they sit between `$5538` and `$25d6`, about 300 steps apart). For a before/after pair rerun from `run/k60_s3.snap`: `$550e` at step 4,509,545 (`scratchpad/pm155/minimap/pre.snap` is step 4,400,000).
- **Files streamed from gpubox are CRLF.** `before.txt` differed on all 162 lines from the Mac rerun only by line ending; `tr -d '\r'` before diffing.
- **Parallel agents on shared docs: one writer per doc at a time.** Owners edit in place. Explorers write only under `scratchpad/pm15x/<area>/` and report suggested prose. The orchestrator saves each report under `reports/` with its PENDING items, then hands a free doc to one merge agent with the report paths. Spot-check one claim per agent against the listing: every check held this pass.
- **Merge agents leave scratch citations.** Grep the docs for `scratchpad/pm15x/.../*.py` before committing and repoint them to the promoted `py/` path. Data paths in scratchpad may stay.
- **The pm148 chunk series is half post-game RAM.** 157 of the 340 `*_c[2468].snap` chunks ran no `$6522` (the game is back at the main menu), so their groups and pigeons are frozen. `pending_census.py` now skips them; any new census over the series must use `stuck_classes.frozen()` too.
- **A scan for a group-field writer needs both frames.** The pending word is `-72(A3)` in the group-offset frame and `4(A1)` in the side-record frame; a `-72(Ax)` scan finds only the clears `$4220`/`$6b20`, while `$683e` sets it through the other base. Confirm a "never writes" with a `watch`.
- **The season wrap is driven by `$57ff6`, not `$57fec`.** Poke `$57ff6 := $0681` to wrap on the next call; a wrap call under `callcap` needs `$2c993 := 0` (`w 2c992 01000055` keeps the neighbours).
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

Open 3's unaided `$66` search and Open 4's revived-sender orphans are agent-sized and need long emulator runs; Open 1's remaining port checks need captures of a ploughing farmer or a siege engine (`py/capture.sh`, then `score.fsx`). Rerun `py/xcheck/run.sh` (after `ruin_capture.sh` once) after any change to `port/godot/logic/`.
