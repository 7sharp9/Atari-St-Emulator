# PowerMonger: handoff

Updated 2026-10-12 by the 158th session (`74b1ea0`, `7afc599`, `2fe9c7e`; skill `4abb821`; digest in the handoff commit), after the 157th (`f3426c8` .. `8046cc8`, skill `cbaf949`).

## Resume point

- Last commits of this workstream: `2fe9c7e` (`$66` sweep), `7afc599` (k112/k96 revived watches), `74b1ea0` (rout re-engager targets; the dump-pairing fix), then the handoff commit (with a one-line digest refinement).
- `bin/Debug/net8.0/M68000.dll` is the 157th session's build (`0687622`, illegal immediate encodings take vector 4); no emulator change this session. The pre-fix DLL is at `scratchpad/pm157/net/oldbin/`.
- Working data: `M68000/scratchpad/pm158/` (gitignored): `rout/run/{k48t,rand1t}.*` (`routrun.sh ... 46-49` watches with word 48), `rout/caller/k48.fill` (the four skipped k48 stamps), `pending/runs/k112*`, `k96*` (revived and `_g0` watches), `modes66/run/b2_*` (the wait sweep). `scratchpad/pm157/`: `overlay/cap/` (byte6 36/38/42 captures, `_trap`/`_bomb` snapshots), `rout/caller/` (`rand1`/`k48` `.hits`, `.calls`, `.rout`, `.after`), `k25/` (home-settlement watches). `scratchpad/pm156/`: `BRIEF.md` (reusable agent brief), `agents/<area>/report.md`, `rout/run/` (the `routrun.sh` watches the rout scripts join against), `modes66/`, `pending/`, `overlay/`, `regate/`. Older: `pm155/minimap/`, `pm154/` (frames, Ruin, FORMAT), `pm118*/`, `pm119/`, `pm8x_*`, `pm9x_*` (streamed from gpubox), `pm150..153/`.
- Start from:
  - `scratchpad/pm142/rand1.snap`: Play Random Land with two player captains.
  - `pm143/run/rand1_s1.snap`: the FILE-panel drives.
  - `pm150/saveload/out/file.snap`: FILE panel open, slot A selected (`format_proof.sh`, `format_sure.sh`, `roundtrip.sh`).
  - `pm123/win/m1_ready.snap`: mission 1 conquered.
  - `pm88_f1.snap`: mission 1 at the port's pose; clear its stuck `$2c993` first (Known traps).
- Uncommitted work left behind: none from this workstream. Not this workstream's: `.obsidian/`, `Cadaver/`.

## Proven so far

Older gates carry over unchanged; the list is in `strategy.md`, `ai.md` and `economy.md`, with reruns from the `py/README.md` table. A sample: entity FSM `py/fsm/repro93..97.py`, `diff_pm99.py` 1847/1847, `gate_orders.py` 61143/61143 over 2273 states, `gate_pop.py`, `gate_equip.py`, the commander AI `py/cmdai/` 323/323 + 280/280, `gate_fsm15.py` 18452/18452, `py/season/gate_1abaa.py` 1084/1084 calls.

New in the 158th pass:

- **Every re-engager was already on the routed man** (`py/fsm/rout_target.py` over `routrun.sh <snap> <tag> 100000000 46-49`): his word 48 last named the man before the stamp, 52/52 (`$1538e` retaliation 29, `$5350` the `$4f68` pick's chase 23); 48 stayed in `$32` with no mode write to the re-engage (the `$15368` ones), the four `$15332` ones are chasers arriving. A `$32`/`$2e` man is on every re-routed man at +200 steps, 18/18 and 34/34. The 157th pass's "10 k48 men with nobody on him" was an artifact: `rout_caller.sh`'s `s 200` loop skipped 5 of 89 k48 stamps and `rout_after.py` paired dumps by index; it now pairs by step, and `rout_caller.sh ... fill <i>...` dumps the skipped ones. ai.md "`$5590`, outcomes".
- **The frozen revived words are watched live** (`py/arms/revived/watches.sh k112 k96`, `g0own.sh k112 k96`): both games end inside chunk 1, so the 18 frozen words are copies of three live ones (k112 side 2 group 1, k96 side 4 groups 1 and 2). k112: `$55f2` kills `$5417c` at 714,966,150, `$28ae` clears the owner word 5,230 steps later, `$4258`/`$42ac` revive him 143.1M later on side 3 (from 2); k96: `$54d66` killed at 723,779,890, cleared 8,384 later, revived 54.7M later on side 4. Nine lineages watched. strategy.md "The pending word".
- **No unaided `$66` in a pre-click wait sweep** (`py/fsm/m66/batch2.sh`): k56 (26,28) and k80's two sheep sites, waits 0 to 20M, 40M steps each: 8 of 15 runs chase, 11 to 14 of 14 chasers water-vetoed, 0 arrive as `$66`, the four k80 arrivals come as `$20`. ai.md the `$36` row.

Carried from the 157th pass:

- **Byte6 36/38/42 crash the game with four TOS bombs** (`py/xcheck/overlay/bomb_check.sh`, from the `run_cases.sh` captures): the word `$0608` at `$11640` takes vector 4 108,268 steps after the frame driver; TOS's handler writes `$380 = $12345678`, `$3c4 = 4` and four bombs at row 100 of the game's screen (481 of 512 bytes changed), then returns into the vector table at `$20`, where the emulator throws on `$08fc` (a real ST would fault again: inferred). 3/3, end states equal apart from the poked byte. port/SPEC.md §6.
- **Who re-engages a re-routed man** (`py/fsm/rout_caller.sh`, `rout_caller.py`; joins against `pm156/rout/run/`): never the striker, 52/52 (`$5590` returns to `$153a2`, which sets the striker to `$2c`); `$15368` (melee) 48, `$15332` (`$2e` arrival) 4; every `$5708` write joined to its call, 76/76 and 124/124, per-site split equal to `hits`. `$5590` callers: melee `$1539c` 85 + arrow `$5b58` 5 (`rand1`), melee 91 (`k48`), `$5a5a` 0. The four escapes: two non-group men recalled while prev `$3c` (`$357e`, `$38c0`), one group member routed by an arrow with nobody on him, one by a lone striker. ai.md "`$5590`, outcomes"; README digest corrected.
- **k25's revived commander follows his home settlement** (`py/arms/revived/home_side.sh`): `$50468` revolts 4 → 2 (`$5538`, 787.6M) before the revival copies its side at `$42ac`, and 2 → 3 (960.65M), which he adopts at `$16874`; word 34 unchanged. strategy.md "The pending word".

Carried from the 156th pass (four agents, every headline rerun from the promoted path):

- **Rout stamps that never arrive are re-routes** (`py/fsm/routrun.sh` + `rout_fate.py`). A routed group member is unlinked, `$3c08` resets his prev 41-145 steps later, which drops the `$1534c` break-off mark; `$56a6` re-engages him (`$5702`/`$5708`, `$32`) and `$5590` routs him again: 18 of 18 (`rand1`) and 34 of 34 (`k48`), second stamps arrive as `$3c` 52/52, 0 died, 0 run end. Reproduces 44/23/3/18 and 89/54/1/34. ai.md "`$5590`, outcomes".
- **No unaided `$66`** (`py/fsm/m66/`): 0 arrivals over 22 runs (L2G_k108's only natural `$5100` chase rerun under a watch; 11 sheep-click chases) and the pm148 long pool (130G live steps). Bound by the code: a Boat-less follower goes `$0a` → `$08` (`$14e36`); the vetoed lead walks to the order cell, unreachable for an island sheep (k56 click (26,28): 115M steps in `$48`); the camp rewrites the prev before a Boat man lands. ai.md the `$36` row.
- **The last 99 pending words are revived senders** (`py/arms/stuck_classes.py` class `revived`, `py/arms/revived/watches.sh`): the dead commander's corpse is brought back by the slot-0 pigeon landing `$4244` (`$4258` neg side, `$42ac` side := home settlement's), so the dead-sender test sees a live record. 51 revived/seen, 48 revived/unseen (30 live, 18 frozen); 0 of 406 unknown. All 7 unseen lineages watched; k104's `-4` launch (`$45a8` `$fc` at 794,192,700) and k4's inheritance (0 writes in 170M) watched. strategy.md "The pending word".
- **Port overlays and byte6 18/28/34 match the game under labelled pokes** (`py/xcheck/overlay/run_cases.sh`, `score_cases.sh`, from `pm88_f1`): plough 16/16 px, siege `$e..$11` walking 98/98, 22/22, 38/38, 50/50, in melee 65/65, 32/32; byte6 18 15/15, 28 18/18 and 20/20 (negative side), 34 19/19; wrong-frame controls 0-34 of the same pixels. `Sprites.fs` gained 18 (`$11c36`) and 34 (`$11ab8`) and a signed 28 test (`$11b14`). Byte6 36/38/42 jump into the dispatch table and crash the game (157th pass, above). `tools/pm_render_ref.py` draws melee: blits 17/17; quad 4/4, ent 3061/3061, baseline, score.fsx 14 frames unchanged; stepper selfcheck 23/23 on both asset sets. port/SPEC.md §6.

Carried from the 155th pass:

- **The minimap is baked, never tinted, and shows no ownership.** `$107d6` runs only from the land build, the mode-strip click, `click_pr` and `_draw_ca` (from `_add_cap`/`_remove_` when the captain is on the player's side `$57ffe`); modes 0 and 2 stay exact, mode 3 (lord supply) goes stale: on `k60_s1` a strip click bakes mode 3 once, then 50M steps run with 0 bakes, the picture unchanged and 38 of 8064 pixels off a fresh bake (`py/maps/minimap_stale.py`). An AI-to-AI revolt does not re-bake. graphics.md "The minimap and the conquest map".

Carried from the 154th pass:

- **Every graphics cross-check of the port reruns from the repo**: `py/xcheck/run.sh` (port/SPEC.md "Re-running the cross-checks"). Synthetic quadrant walks 4/4 identical (1020 px each); synthetic blits 12/13 (the melee case differs by design: the port draws `$11c8a`, `pm_render_ref` skips it); real record stream 3061/3061, superseding the first run's 2881 (the current output matches the game's screen at 1889 px against 1182); baseline 162/162; the §6 draw-order table reproduced; `score.fsx` on 14 frames 99.64-99.99% (`pm78_settle` 94.62%).
- **Two exporter gaps fixed**: `dump_frame.py` now exports the 32x32 sheet (zoom 1-3: 95.02-99.06% -> 99.79-99.91%, same frames), and `pm_render_ref.load_ram` walks the `2*[$fdec]` window instead of a fixed 11x11 (zoom 7 95.86 -> 99.89%, zoom 6 98.74 -> 99.93%). Zoom 1-7 terrain away from sprites 99.78-99.95%, sprites 98.2-100%.
- **The port draws Ruins** (`$117e4`: frame `$0a` plus the `$119b2` overlay, frame `word[12] mod 10`, top rows cut by `record[16]`). Mission 1 on each Ruin 98.31 -> 99.82% and 98.41 -> 100.00%; the overlay at counters 70 and 100 752/752 and 783/783 px, with wrong-frame and no-overlay controls at 97.68-98.27% (`py/xcheck/ruin_capture.sh`). `EntityRec` gained `B16`/`W12`; both `entities.json` patched from their source RAMs; stepper 23/23 on both asset sets, Godot builds, walkthrough verifies.
- **Pending census over live play only** (`pending_census.py` skips frozen chunks, `--all` keeps them): 357 words in 183 snapshots, 70 flying, 142 dead-sender, 141 orphan, 4 queued. 11 of the 12 "inherited" words on live-commander sides were frozen post-game RAM; live play has 1 there plus 8 on dead-commander sides. strategy.md "The pending word", README bugs list, `fig/order_pipeline`.
- **FORMAT's ARE YOU SURE is live** (`py/saveload/format_sure.sh`): with the game disk in, `$1bd38` finds it and `$1bec2` asks; CANCEL runs `$1beec` with no write, OK formats it (80 Write Track commands). system.md "The save-disk code".

Carried from the 153rd pass:

- **`$1abaa` (seasons and weather) is gated.** `py/season/gate_1abaa.py` diffs `model_1abaa.py` (dissolve, wrap, weather, rain and snow blit, tree regrowth, sample-player state) against callcaps over every changed byte of the 1 MB: **1084/1084 calls, 735,679/735,679 bytes** in four arms (m1 420, rand1 420, wrapw 240 and felled 4 under labelled pokes), rerun from fresh captures at the promoted path. A call copies about 9 pixels, not 16 (`$1ac04`: steps with `x >> 4 >= $120` copy nothing); winter's season cue is the stop sequence. strategy.md "What `$1abaa` actually is".
- **Inherited pending words, a second pigeon-path bug** (watch-proven on k98 and k118). `$2776` dissolves a group without clearing its pending word, and `$25d6` builds the next captain's group in that slot without clearing it; the new group is never ordered. In live play it accounts for 9 stuck words (1 on a live-commander side, 8 on dead-commander sides; the 154th pass's frozen filter). strategy.md "The pending word", README bugs list.
- **Mode-graph loose ends** (`py/fsm/mode_write_scan.py`, whole image). Nothing writes `$04`, `$64` or `$70`. `$66` is entered only through the `$161f0` water veto (a `$36` step onto water, then a `$10` arrival copies prev `$66`); live 1 of 1 under a one-byte prev poke, 0 unaided in 6 x 200M steps; `fsm_army` gains the dashed edge `$36 -> $66`. `$3c74` is unreached behind a `nop` (an inferred patched `bra.s`; 0 hits in 4.1G steps; reached under `w 3c10 6e026060`). A routed group member enters `$3c` only after a second rout (156th pass, above). ai.md, `fig/fsm.facts.md`.

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

1. **Port residue.** The control frame of the overlay checks misses 22 px in tree `$4d762`'s box (frame `$13` at (131,95)), the same in every run: `watch` the screen words during the frame. The port tests `record[44] >= $e` unsigned where the game is signed (differs only for `>= $80`, never written). Natural byte6 18, 28 and the overlays are still unseen in play (36/38/42 crash the game, so a natural one would be a visible bug). The camp-marker frame `$111` from `$117b0` has not been captured.
2. **Emulator gaps (not this workstream's to fix alone).** Static `BSET`/`BCHG`/`BCLR` to a non-alterable destination (`$08fc`) throws in `Cpu.BitOp` instead of taking vector 4 (a task chip was raised; the `ImmediateToEa` half landed as `0687622`); after it, rerun `bomb_check.sh` (the byte6 36 crash then faults again at `$20`). FORMAT's write-protect requester `$1bf04` needs a write-protect flag in `MMU.fs`. Both go behind the regression net.
3. **A player route to `$668c`.** Let one of the player's lords fall to a drained AI side (`pm151/r1` side 2 took player lord 10 in chunk 2), then `bp 668c`; `py/side_dump.py` per chunk. Low value: five natural hits already prove the arm.
4. **UI leftovers.** The `$c5ee` entry contract; word `-36` in the sound pick; sound event 17 is queued and cleared but never played (`bp 12820`); the double handling of a captain-box click in transfer mode (`bpc 133d4 2`, watch `$2df96`); `$04` sent from a group that has a sender (by pigeon, inferred); the other `$7658` dialog ids; the person panel's Stock rows.
5. **Small checks.** `$4a7a` has no model gate, and opponent class `$a` is unseen. The season after a LOAD (`$57fd0` writers); natural winter snow under the `$1abaa` gate (a lineage one wrap before `pm143/run/rand1_s4`); the divide by zero at `$1ac88` on an empty tree array (a `felled`-style arm with `$4e512 < 12`); posture 5 from `$67d0`; an exact water test in `stuck_census.py` (replay `$1648e`); an indexed-access scan for `$58054`; a pile record's words 8 and 28; the crack's `$b842` patch (and whether `$3c12`'s `nop` is the crack's or the developers'); the `$54` merchant loop `$15b0c`; health cap and food (`$5ccc`); `$4342`'s arrival branch. Rout fates on other lands (death or run end while re-routing: `routrun.sh` on a third land). A natural `$66` now needs an AI sheep chase across a narrow channel with a Boat chaser landing before the first slaughter (37 runs, 0 arrivals).
6. **The stall on the original machine.** A Hatari run past clock 32768 with a camped group (low priority; Hatari through an agent has Dave's go-ahead). Hatari could also confirm what the ST does after the byte6 36 bombs (the handler's return to `$20` with SSP `$4e73203c`; inferred: a double fault halts it).

## Known traps

- **`rout_caller.sh`'s `.after` loop skips stamps.** Its `bp 561c` / `s 200` / dump passes over a stamp within 200 steps of the previous one; join its dumps by step (`rout_after.py`, `rout_target.py` do) and dump the skipped ones with `fill`.
- **`revived/watches.sh` watches record bytes 4..7**, at the record base + 4 (`$54180` for `$5417c`). Watching the base sees only the bucket-link words 0..3.
- **There is no `<N> resume <snap> snapshot <path>` argv.** It falls through silently with an empty log; run `resume <snap> repl` with `s N` / `snap <path>` on stdin. `s 1` prints nothing: follow it with `r`.
- **Do not pipe a capture script into `head`.** `py/xcheck/overlay/poke_capture.sh | head` dies of SIGPIPE before the `_1` dump and leaves a stale JSON from an older run that the scorer reads without complaint.
- **The machine may be shared with another project's jobs.** This pass two ML jobs held 14 of 16 cores; agents ran one emulator each, and a 100M-step run took about 4 minutes.

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

The pending-word, rout and `$66` tails are closed. The biggest remaining item is the port residue (Open 1): the 22-px tree miss is one `watch` of the screen words during the control frame from the `py/xcheck/overlay/` captures. Open 2 (the `Cpu.BitOp` vector-4 fix) is an emulator change: coordinate with live sessions, run the regression net, then `bomb_check.sh`. Rerun `py/xcheck/run.sh` and `py/xcheck/overlay/score_cases.sh` after any change to `port/godot/logic/`. The brief at `scratchpad/pm156/BRIEF.md` is reusable for parallel agents.
