# PowerMonger: handoff

Updated 2026-10-13 by the 160th session (`aa19f3b` .. `a0ddb87`; CLAUDE.md/skill `2fdf420`), after the 159th (`6fe45f6` .. `43eccbb`).

## Resume point

- Last commits of this workstream: `aa19f3b` (sound slot), `b69fa6e` (`$c5ee`), `fba2240` (ack pick), `57121c2` (click timing), `ae21d9e` (`$04` by pigeon), `6bf245a` (Stock rows), `5b00a2a` (dialog ids), `8c52729` (`$1ac88`), `a0ddb87` (digest), then the handoff commit.
- `bin/Debug/net8.0/M68000.dll` is the 159th session's build (`a6eb21d`); no emulator change this session.
- Working data: `M68000/scratchpad/pm160/` (gitignored): `snd/` (dispatcher censuses, `lit.txt` and `drawscan.txt`: snapshots with a lit fire and which draw it), `xfer/` (click-timing arms, the `from1*.repl` drives), `ui/` (`req_panels.out`), `dlg/` (`dlg_ids.out`). Older: `pm159/` (`tree/`, `net/`, `bomb/`, `wprot/`), `pm158/`, `pm157/`, `pm156/` (`BRIEF.md`, the reusable agent brief), `pm150..155/`, `pm148/` (the long chunk series), `pm142/`, `pm143/`, `pm123/`.
- Start from:
  - `scratchpad/pm142/rand1.snap`: Play Random Land with two player captains (UI drives, dialog census).
  - `scratchpad/pm148/arms/sheep/k120_tree_c1.snap`: lit camp fire in view, sound slot empty.
  - `pm150/saveload/out/file.snap`: FILE panel open, slot A selected.
  - `pm123/win/m1_ready.snap`: mission 1 conquered (`sndpost.repl`, `req_panels.py`).
  - `pm88_f1.snap`: mission 1 at the port's pose; clear its stuck `$2c993` first (Known traps).
- Uncommitted work left behind: none from this workstream. Not this workstream's: `.obsidian/`, `Cadaver/`.

## Proven so far

Older gates carry over unchanged; the list is in `strategy.md`, `ai.md`, `economy.md`, `system.md`, `graphics.md` and `port/SPEC.md`, with reruns from the `py/README.md` table (entity FSM `py/fsm/repro93..97.py`, `diff_pm99.py` 1847/1847, `gate_orders.py` 61143/61143, commander AI `py/cmdai/` 323/323 + 280/280, `gate_fsm15.py` 18452/18452, `gate_proj.py` 5082/5082, `py/season/gate_1abaa.py` 1084/1084, the overlay and xcheck runs of `py/xcheck/`).

New in the 160th pass (Open 4 closed):

- **The sound slot** (`py/ui/snd_slot.sh`, strategy.md `$127e6`): one slot `$58058`, entries 5..63 scanned, the second-best never used; a same-id flag-`$20` sound is not restarted, and `$1ba3e` drops the flags, so it plays once. Event 17 (camp fire) pending and chosen 60/60, played once, 158 of 160 later dispatches skip it, replayed after event 20 displaced it. README bug list.
- **`$c5ee`** (strategy.md panel table, `py/ui/req_panels.py` 8/8): D0 = the side that is not the local one, hooks `$c628`; "The alliance between A and B is broken may a million fleas infest your undergarments."
- **Order-ack pick** (`py/ui/sndpost.repl`, strategy.md `$6e6e`): `31 + (state + first_man) mod 6`, so it keeps the state's parity; live 1/1 (state 7, object 47, event 36).
- **Clicks seen twice** (`py/captain2/xfer_timing.sh`, strategy.md tick tail): the press stamp `$2df74` and the per-pass clock `$1302e` let a press landing before the UI sections act on two passes (about 177k of a pass's 177.5k steps); poked before `$130fc`: `$133d4` 2, `$04` then `$22` (dropped); at `$1373c`: 1, `$04` only. The game's, not the emulator's.
- **`$04` from a subordinate goes by pigeon** (`py/captain2/xfer_pigeon.repl`): `$4562` takes the local slot, `$1c18` 9.99M steps later from the executor (`$6bba`) with 1, 2, 0.
- **House Stock rows** (`py/ui/gate_panels.py`): 103/103 with Stock compared (19 houses with stock), 4/4 with poked goods; the model's item-name offset was wrong (+18, the code reads +19).
- **Dialog buttons** (`py/ui/dlg_ids.py`): 17/17 by `callcap` through a frame stub; MULTI PLAY and PAUSE leave the panel open.
- **`$1ac88` cannot divide by zero in play** (strategy.md, tree regrowth): every writer of `$4e512` and every caller of the clear listed.

## Open, in priority order

1. **Port residue.** The port tests `record[44] >= $e` unsigned where the game is signed (differs only for `>= $80`, never written). Natural byte6 18, 28 and the overlays are still unseen in play (36/38/42 crash the game). The camp-marker frame `$111` from `$117b0` has not been captured. The birds sit still in the port because its seed is a constant; whether the game's seed `$2df84` moves in long play decides whether the port should advance it: `watch 2df84 4` over a long run.
2. **Emulator gap: no bus error on an unmapped write** (not this workstream's alone). After the byte6 36 bombs the vector-4 entry stacks at SSP `$4e73203c`; a real ST should double-fault and halt (inferred). A fix belongs in `MMU.fs` behind the regression net; read the BusError history in `MMU.fs` first (it regressed cold boot once); Hatari could confirm.
3. **Small checks.** `$4a7a` has no model gate, and opponent class `$a` is unseen. The season after a LOAD (`$57fd0` writers); natural winter snow under the `$1abaa` gate (a lineage one wrap before `pm143/run/rand1_s4`); posture 5 from `$67d0`; an exact water test in `stuck_census.py` (replay `$1648e`); an indexed-access scan for `$58054`; a pile record's words 8 and 28; the crack's `$b842` patch (and whether `$3c12`'s `nop` is the crack's or the developers'); the `$54` merchant loop `$15b0c`; health cap and food (`$5ccc`); `$4342`'s arrival branch; rout fates on a third land (`routrun.sh`). A natural `$66` needs an AI sheep chase across a narrow channel with a Boat chaser landing first (37 runs, 0 arrivals). The dialog buttons still code read: `$04`, `$08`'s `$71` (SELECT MAP) and `$131` (SEND MESSAGE).
4. **A player route to `$668c`.** Let a player lord fall to a drained AI side (`pm151/r1` side 2 took player lord 10 in chunk 2), then `bp 668c`. Low value: five natural hits prove the arm.
5. **The stall on the original machine.** A Hatari run past clock 32768 with a camped group (low priority; Hatari through an agent has Dave's go-ahead).

## Known traps

- **An edited drive script can diverge.** Deleting the `hits` lines of `py/captain2/from1`-style drives removed their settles and the first click no longer selected the captain; a second edit that kept the step counts still posted no `$04` (cause not found). Keep a working drive verbatim and change only what follows its last action (`xfer_pigeon.repl` was made that way).
- **The camp-fire sound needs a lit fire in view.** `pm143/run/rand1_s1.snap` draws none now (`$117b0` 0 hits); `pm148/arms/sheep/k120_tree_c1` and `pm150/small/camp/c12_*` do (`scratchpad/pm160/snd/drawscan.txt` lists the 20 that draw it out of 659 with a lit fire record).
- **`callcap` into the dialog handlers needs the frame stub** (`py/ui/dlg_ids.py`): the shared exit `$7a22` pops 14 registers.
- **`showboat verify --output` rewrites prose.** On `port/walkthrough/walkthrough.md` it dropped the paragraph after an image line; patch a changed quoted block by hand and rerun `uvx showboat verify` (exit 0).
- **`EntityCtx` has a `Seed` field.** Every constructor (`py/score.fsx`, `py/xcheck/*.fsx`, `port/stepper/Load.fs`, `port/walkthrough/probe.fsx`, `TerrainView.cs`) sets it; a JSON without `seed` reads 0 (birds at the wrong offsets).
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

Open 4 is closed. Open 1's seed question is one long `watch 2df84 4` run and decides a port change; do it first. Then Open 3's small checks, each a single bounded REPL test (start with the season after a LOAD and `$4342`'s arrival branch). Open 2 is an `MMU.fs` change: read the BusError history first. Rerun `py/xcheck/run.sh` and `overlay/score_cases.sh` after any change to `port/godot/logic/`.
