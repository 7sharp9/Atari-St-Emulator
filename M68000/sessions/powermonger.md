# PowerMonger: handoff

Updated 2026-10-31 by the 168th session (Open 3's cheap checks and Open 2's residue).

## Resume point

- Last commit of this workstream: `5867b7d` (the 168th pass: divu overflow, conquest side, lord-slot census, posture-5 panels, dismiss and roster). Not pushed.
- `bin/Debug/net8.0/M68000.dll` as built 2026-10-26 by the emulator workstream; this session ran it unchanged.
- Working data: `M68000/scratchpad/pm168/` (gitignored): `divu/` (`revolt_divu.sh`: `p15826.snap`, the stop state, and the arms), `lordslots/` and `lordslots0/` (the census dumps, paged and Play Random Land rolls), `dismiss/` (`p5_dismiss.sh`), `roster/` (`p5_roster.sh`: `p{5,3}_100M.snap`, the two p5_fisher arms 100M steps in, and the dismiss watches); `apply_docs.py` is the doc-edit record. Older: `pm167/p5job/`, `pm166/` (`reports/`, `BRIEF.md`), `pm165`, `pm163`, `pm162`, `pm156`; earlier ones as the 167th handoff listed (git history of this file).
- Start from:
  - `scratchpad/pm142/rand1.snap`: Play Random Land with two player captains; the land ends about 676M steps in.
  - `scratchpad/pm162/posture/trade/at63f4.snap`: side 3 group 0 at the trade `$63f4`; `pm168/roster/p5_100M.snap`: its posture-5 arm 100M steps on (object 6 on side 2, group 0, flag bit 2 lost).
  - `scratchpad/pm150/small/camp/c12_0.snap` (lit camp fire), `pm148/arms/long/M2G_k118_c1.snap` (lit and put out), `pm162/g4a7a/nat/n4a7a_k120_a_1.snap` (`$4a7a` entry), `pm97/pm97_map0.snap`, `pm150/saveload/out/file.snap`, `pm123/win/m1_ready.snap`, `pm88_f1.snap` (clear `$2c993` first).
- Uncommitted work left behind: none from this workstream. Not this workstream's: `scratchpad/ANCHORS.md`, `Cadaver/`, other sessions' game files.

## Proven so far

Older gates carry over; the lists are in `strategy.md`, `ai.md`, `economy.md`, `system.md`, `graphics.md` and `port/SPEC.md`, reruns from the `py/README.md` table.

New in the 168th pass:

- **The heartbeat revolt's side can overflow** (`economy.md` §3 "The hunger revolt", `py/revolt_divu.sh`): `$158b6` divides all 32 bits of D0 after setting its low byte; the Ruin rebuild `$15846` in the same pulse leaves `cell / 10` in the high word, the quotient overflows and the side is `(cell / 10 + 1) & $ff` (`$c4` for cell 4513, control 2; 0 for cells 2550..2559, 5110..5119, 7670..7679). Latent: 10/10 natural revolts had high word 0 (`py/revolt_callers.py`), and a rebuild never completes in a normal run.
- **The conquest side is never 0** (`ai.md` `$54`): `$14b72` skips a side-0 record and nothing on mode `$2c`'s path to `$53f6` writes `5(A1)`; 17/17 natural conquests gave sides 2..4.
- **Lord slots lost to the `$2eac` corner test:** none on the briefing-preview roll (0/144 lands); on the Play Random Land roll 3/144 (k27, k69, k90), one slot each, the highest consumed (`strategy.md` "Towns, ranks and water", `py/worldbuild/lord_slots.sh`/`.py`).
- **Posture-5 panel text** (`strategy.md` "Posture 5 forced into the trade", `py/ui/posture5_panels.py`, 4/4): the captain panel reads "PowerMonger but sting", the alliance offer "dave, .. allian an".
- **Posture-5 dismiss lets one man in eight go** (`py/cmdai/posture/p5_dismiss.sh`): 1/6/12 of 12 at postures 5/3/2, shift 3/1/0 at `$1cec`.
- **The lost fisher flag outlasts the roster** (`py/cmdai/posture/p5_roster.sh`): dismissed from side 2's group 0, the posture-5 man gets prev `$7e`, the same snapshot with bit 2 put back `$5e` and one fishing trip in 60M steps.

## Running

Nothing running.

## Open, in priority order

1. **Port residue.** Natural byte6 18 and 28 are unseen in play. The camp-marker catch marker `$110` and other zooms are not pixel-matched (needs a snapshot with a drawn byte6 24 record, `pm160/snd/drawscan.txt`).
2. **Consequences of a garbage lord side** (the `$158b6` overflow): what a lord and settlement of side `$c4` (or 0) do to the readers that index side tables (`side * $13c`, `$580a6[side]`), and whether men copying their home settlement's side (`$42ac`, `$16874`) can take side 0 (never stepped, `$14b72`) or a negative one. Labelled from `pm168/divu/p15826.snap` with the `revolt_divu.sh` pokes; a `watch` on the side bytes and `hits` on the side-indexed readers over 50M steps against the control.
3. **Residue of the 166th pass's checks.** A LOAD and the land-end flow for `$13baa` and for a zeroed lord side; whether an arrow can hit a still-walking class-`$a` marker; a natural `worker_obj` writer (`watch` tree word 2 over a Play Random Land run); a natural add-to-pile (drive `$12`/`$18` twice on one cell); the byte 44 `>= $12` overrun, the `$ab34` categories `$12 $16 $1a $1c $22`, and a per-site run of the chain walkers with a pile in the chain; the natural `$3aee` arm (once at 98M steps of `p0k60_s1`); the chunk-end clock values `$2df72` in `W5G_*_cN.snap`.
4. **Posture 5 residue.** Whether any AI issue site posts the dismiss `$14` (a whole-image scan of the slot writers' type bytes); the true-screen render of the alliance offer's `$f0 $e6` bytes at posture 5 (a frame capture after a labelled offer, `py/ui/req_panels.py` route).
5. **Small checks.** Natural winter snow under the `$1abaa` gate; the crack's `$b842` patch and `$3c12`'s `nop`; health cap and food (`$5ccc`); rout fates on a third land; a natural `$66`; the dialog buttons `$04`, `$08`'s `$71` and `$131`.
6. **No current check exercises vector 4 on the unassigned `ImmediateToEa`/`BitOp` encodings** (README "Bug 7"): an emulator-workstream item; a poke of `$0608` at a live PC would do.
7. **A player route to `$668c`** (low value) and **the stall on the original machine** (a Hatari run past clock 32768 with a camped group; Dave's go-ahead given).

## Known traps

- **Lands named `M2G_k<n>` are Play Random Land builds (`PAGES0=1`, `$5809c = 0`), not `build_land.sh`'s default paged roll.** A census of k90 on the paged roll found 9 lord slots and none empty where the doc's land 90 (`M2G_k90`) has 13 with slot 12 empty: run a positive control on the land a claim was made on before trusting a 144-land negative (`py/worldbuild/lord_slots.sh`, both rolls).
- **A group's men word read long after an order is not the order's result.** Forty million steps after the dismiss the group had refilled (12 -> 11 at posture 3 where 6 went); read it at the routine's exit (`p5_dismiss.sh` stops 400K steps after `$1cec`).
- **A bash heredoc inside `$( ... )` breaks on an apostrophe in the heredoc body** ("unexpected EOF while looking for matching"), even with a quoted delimiter: put the Python in its own file (`p5_roster.py`).
- **The REPL `watch` labelled a `move.b` as `WriteWord`.** `move.b #$e,6(A1)` at `$15180` (and `move.b #0,6(A1)` at `$3cdc`) printed `WriteWord $00051c98`; `stserver` reports the same step as width 1 and byte 7 unchanged, and byte 7's later values confirm it. Count watch lines by address, and check a surprising width with `stserver` `watch_add`. Not yet reported to the emulator workstream as a bug (the label code in `MMU.fs` `SetWatch` looks right, so the cause is unknown).
- **The trade run's 30M/60M snapshots show no melee.** `pm163/p5fwd/x_P5B84_{30,60}` hold all 12 men at byte 31 `$2c`/`$10`; the fight is the 864.84M..866.61M window between them, found only by watching the records (`real_melee84.sh WINDOW=1`). Run `real_melee84.sh` (it lands at about 865.5M) rather than a fixed-offset snapshot.
- **A subagent's gate needs a promoted corpus path.** `gate_4a7a_nat.py` reads `${PM_WORK:-scratchpad/pm162}/g4a7a/nat/`; the foreign-man corpus was copied there by hand (gitignored), so a fresh checkout rebuilds it with `py/orders/man_click.sh`. `py/xcheck/campframe/pixels/cmp.fsx` needs `PmLogic.dll` built.
- **Agent reports carry the doc prose; the harness does not save them.** Save each report's summary under `scratchpad/pm166/reports/` when it arrives and apply the edits with one exact-match script (`apply_docs.py` fails if a quoted old string is not unique), not by hand across docs.
- **`SendMessage` to a session started with `start_session` takes its id or its `ListAgents` title**, not the short `name` the start returned ("No agent named 'pm-doc-cleanup' is reachable").

- **A port frame past its sheet draws nothing, silently.** `blitEntity` drops an out-of-range frame, so a divergence predicted from reading the code can score 0/0 by accident: SPEC said a `$84` man "would draw the siege overlay in the port", but the port's struct frame `$1b + ($84-$e)*4` was off the sheet and dropped. Run the labelled poke before writing such a prediction.
- **`py/xcheck/blit_{fs.fsx,py.py}` is a mirror check.** Its random-byte sheet puts plane bits under the mask everywhere, so any blit-semantics change moves both halves or breaks it (3/17 after the OR change until `blit_py.py` mirrored it). It proves port = Python model, not port = game; the game-side proof is an overlay capture.

- **Bus errors are real now.** Since `90ea349`, a read or write of `$400000..$f9ffff` bus-errors and a fault while stacking a group-0 frame halts the CPU (stderr `double bus fault: ... CPU halted`); `hits` then keeps counting the halted PC every step, and `u`/`bp` give up "still at" it. Find the halting step by bisecting on that stderr line (`bomb_check.sh`). A poke that sends the game off the rails may now halt where it used to loop.
- **Pairing grep'd register dumps from a `bp` series picks up the stop before it.** `grep -E '^D0|^A0' | paste - -` over a REPL log pairs the `bp 6500` dump with the first `bp 15380` line; `grep -A8 'breakpoint $<addr>'` first (`trade5_fwd.sh`).
- **A handoff that cites a note outside the repo loses it.** The bus-error trace `bus-error-double-fault.md` lived in the emulator worktree's memory and was gone; re-derive, and cite only repo paths.

- **A promoted gate that reads its corpus from `$PM_WORK` fails under a fresh `PM_WORK`.** `py/orders/class_a.sh` and `gate_4a7a_nat.py` read `${PM_WORK:-scratchpad/pm162}/g4a7a/nat/`, `py/fsm15/poke54.py` reads `.../merchant/cap/rand1_1.snap`: rerun them with the default PM_WORK (copy the old outputs aside first) or pass the corpus explicitly (`gate54.py cap/*.json`).
- **`scratchpad/pmwork/aggr/pm_all.asm` is misaligned at `$4a78..$4a7c`** (no `$4a7a` line): list a routine with `disassemble.py --all <entry> <end>`; for a writer census also run an every-even-address decode (`py/cmdai/posture/raw_scan.py`).
- **`callcap 14f08` (a mover that relinks) needs `A2 = $47970`**, the bucket base set at `$14b68`, or the relink at `$1644e` writes through a stale A2 and the call runs off (`py/fsm/gate_probe.py`).
- **`pm143/run/rand1_s1.snap` draws no `a_object`** (`$117b0` 0 hits in 3M steps): for camp-marker frames use `pm150/small/camp/c12_0` (lit) or `pm148/arms/long/M2G_k118_c1` (lit and out).
- **`pm142/rand1`'s land ends about 676M steps in.** From there the tick `$6522` never runs and the RAM is post-game, so a long census from rand1 reads 0 for everything after that (the seed watch's `end.snap`). Bound a long run with a `hits ... 6522` liveness count per window.
- **`mk_savedisk.py` slot fills are `A=<ram>`**, not `slotA=`; the letter is the slot.
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

## Waiting on Dave

- The blog session (archived before the reply could land) asked which figures Paint It Black should quote. The per-capture table is `port/walkthrough/walkthrough.md` "Draw order" (inline render 94.62% to 99.99%, pm78_settle the low one; terrain only 84.8 to 94.6%); `port/SPEC.md` quotes terrain away from sprites at 99.7-99.96% and whole frames at zooms 1-7 at 99.79-99.99%. A "99.7-99.99%" headline mixes those measures.

## Next session

Open 2 first (the consequences of a garbage lord side, from `pm168/divu/p15826.snap`), then the cheapest of Open 3 (the arrow on a walking class-`$a` marker, the natural add-to-pile drive). One emulator per agent, at most two agents while other sessions share the machine; spot-check one claim per report and rerun each gate from its promoted path. Merges write current-state prose only (CLAUDE.md "Docs").
