# PowerMonger: handoff

Updated 2026-10-17 by the 166th session (seven parallel agents on the small checks; commit below), after the 165th (`a8e23a4`).

## Resume point

- Last commits of this workstream: the 166th pass's docs-and-scripts commit (`git log --oneline -3 -- sessions/powermonger.md`), after `a8e23a4`. Not pushed.
- `bin/Debug/net8.0/M68000.dll` is built from master `d6e6646`, which includes the bus-error change `90ea349` (`$400000..$f9ffff` and writes to `$0..$7` bus-error; a fault while stacking a group-0 frame halts the CPU). Dave merged it via `origin/master`; this session fast-forwarded and rebuilt.
- Working data: `M68000/scratchpad/pm166/` (`reports/<area>.md` summaries of the seven agents, raw runs under `clockA/ clockB/ orders/ piles/ lords/ posture5/ camp/`; `apply_docs.py` is the doc-edit record); `pm162/g4a7a/nat/` now also holds the `n4a7a_man_*` corpus. Older: `M68000/scratchpad/pm165/real84/` (the first capture `mb_0/1`, the 60M men watch `watch.err`), `pm165/gate/` and `pm165/gate2/` (the promoted gate's reruns, `gate2` with `WINDOW=1`). Older: `M68000/scratchpad/pm156/overlay/cap/{siege84,msiege84,msiege92}_*` (the new overlay captures) and `pm164/xcheck/` (the `run.sh` output). `M68000/scratchpad/pm163/` (gitignored): `p5fwd/` (the `trade5_fwd.sh` 2x2: `x_<arm>.out`, `x_<arm>_{30,60}.snap/.ram`, `drain.out`; `fwd.sh` with `p5x.fwd`/`p3x.fwd`, the plain arms over 100M), `p5fwd_first/` (the first 2x2, identical), `old/`. `pm156/overlay/cap/b6_NN_halt.snap` are the new bomb_check end states. Older: `pm162/` (`posture/trade/at63f4.snap`, the trade state), `pm161/`, `pm160/`, `pm156/`, `pm148/`, `pm142/`, `pm143/`, `pm123/`.
- Start from:
  - `scratchpad/pm142/rand1.snap`: Play Random Land with two player captains; the land ends about 676M steps in.
  - `scratchpad/pm162/posture/trade/at63f4.snap`: side 3 group 0 at the trade `$63f4` (A3 = `$51938`); the posture-5 arms start here.
  - `scratchpad/pm150/small/camp/c12_0.snap`: a lit camp fire in view; `pm148/arms/long/M2G_k118_c1.snap`: lit and put-out fires.
  - `scratchpad/pm162/g4a7a/nat/n4a7a_k120_a_1.snap`: the k120 sword click at `$4a7a`'s entry.
  - `scratchpad/pm97/pm97_map0.snap` (forest animator), `pm150/saveload/out/file.snap` (FILE panel), `pm123/win/m1_ready.snap` (mission 1 conquered), `pm88_f1.snap` (clear `$2c993` first).
- Uncommitted work left behind: none from this workstream. Not this workstream's: `.obsidian/`, `Cadaver/`.

## Proven so far

Older gates carry over unchanged; the list is in `strategy.md`, `ai.md`, `economy.md`, `system.md`, `graphics.md` and `port/SPEC.md`, with reruns from the `py/README.md` table. The 162nd pass's (camp markers, exact water, `$54`, posture-5 writers, piles, `$58054`, `$4a7a`) are in those docs.

New in the 166th pass (all in the topic docs; reruns from the `py/README.md` rows):

- **`$13baa` runs only at land build** (`fig/clock_stall.facts.md`): once in a build, 0 in 200M play steps and 0 in 750M of `rand1`; a LOAD and the land-end flow not measured. **`$65b4` per chunk** is 1467..1503 (k80) and 1836..1851 (k108), so 1500/1843 are chunk-1 values (`W5G_*` logs; chunk 15 re-executed).
- **Foreign-man arm of `$4a7a` entered by a natural click** (k56 (29,35), 99/99); the gate is 2030/2030 over 26 states. **Class `$a`** is reached by a click after a labelled `worker_obj` poke; its shoot ends only by an arrow's `neg.b 5(A3)` at `$5b7e`, and an arrived marker is never hit (`strategy.md` "The opponent class").
- **Piles:** neither the `$3a8e` nor the `$3a18` arm has a natural entry (25 `$39d4` calls, 17 piles); both match under labelled pokes. `$ab34` is the generic offset-8 reader (callcap 64/64); a LOAD restores the pile pool and `$58054` by DMA (3/3).
- **`$54` hang has no natural path:** only `$2ef4` and `$5516` write a lord's byte 0, always 1..4 (code census plus 1,600M watched steps). **Lord slot 12 on k90** is `$2eac`'s `add.b` corner test wrapping on four `$40` corners (`strategy.md` world build).
- **Posture 5:** the trade's clear of object 6 bytes 6..7 turns a fisherman's job 4 to 0, `$3c08` then gives prev `$7e` for `$5e` (2/2); object 7's clear was already 0; per-reader behaviour in `strategy.md` "Posture 5 forced into the trade".
- **Camp markers:** the port's blit matches the game's screen, 88/88 pixels in 35 draws (`port/SPEC.md`).

The 165th pass's:

- **The `$84`/`$92` melee frame matches in the real posture-5 trade run** (port/SPEC.md §6 "Men", `py/xcheck/overlay/real_melee84.sh`; `WINDOW=1` reproduces the window): from `at63f4.snap` the 12 men fight (byte 31 `$32`, 37 writes) from 864.84M to 866.61M cumulative steps, byte 44 never rewritten. One frame (camera poke only) has six in melee, three `$84` and three `$92`; on the pixels that depend on byte 44 the true render is the game's 35/35 (byte 44 + 1), 43/43 and 33/33 (aligned weapon-0 frame), every altered render 0. `diff.fsx` takes `WRONG_SIDE=ctl` to score one capture against itself.
- **The word blitter ORs its planes unmasked too, with no effect** (port/SPEC.md "Frame index per category"): every row loop (`$123ac`, `$1241a`, `$12460`, `$124a8`, `$12576`, `$12628`) writes `plane | (screen & mask)`, but no frame of `$312a0`/`$37c7c`/`$3af1c` has a plane bit under the mask (`py/xcheck/sheet_mask_scan.py`, 0 rows on `at63f4` and `pm88_f1`; control frame `$ab` found), so `decodeFrameWord` needs no change.

The 164th pass's:

- **The port follows the game for byte 44 >= `$80`** (port/SPEC.md §6 "Men" and "The mini-sprite blitter"): the siege test is signed (`$11cb4`, `$11e78`); `$11f82` makes the frame a byte offset with `mulu #$37 / adda.w` (16-bit wrap, sign-extended, so a `$84`/`$92` melee frame reads 55 misaligned bytes, below `$33000` into the `$312a0` sheet's tail for side-2 `$84`); the planes are ORed in unmasked, so a mask-1 pixel with plane bits k draws `background | k` (one pixel of the real sheet, frame `$ab`). Labelled pokes on `pm88_f1`: walk `$84` 0/0, melee `$84` 32/32 and `$92` 35/35 (before: 3/32, 3/35; wrong-frame control 9/32, 22/35); the 16 earlier cases unchanged (`py/xcheck/overlay/run_cases.sh`, `score_cases.sh`); `py/xcheck/run.sh` at the documented scores, synthetic blits 17/17 with `blit_py.py` mirroring the OR.

The 163rd pass's (byte6 36/38/42 halt, posture-5 trade codes decide the next fight, melee formula fix) are in port/SPEC.md §6, README "Bug 7" and strategy.md "Posture 5".

## Open, in priority order

1. **Port residue.** Natural byte6 18 and 28 are unseen in play. The camp-marker catch marker `$110` and other zooms are not pixel-matched (needs a snapshot with a drawn byte6 24 record, `pm160/snd/drawscan.txt`).
2. **Posture 5 downstream.** Whether the fisherman-to-job-0 change has a lasting effect (watch `51cb0` past 892M, `hits` `$157e6` against `$15b5e`/`$15b94` by A1); name `$5f78` from its body; `$1ce6` needs a player dismiss order; render the `$90fe`/`$c77e` panel text at posture 5; a whole-image `7(An)` read census.
3. **Residue of this pass's checks.** A LOAD and the land-end flow for `$13baa` and for a zeroed lord side; the conquest path `$53f6` with a zero side and the `$158b6` `divu` quotient (`bp`); a census over the 144 lands of `$4f914/32` against filled lord slots (how many lose a lord to the `$2eac` wrap); whether an arrow can hit a still-walking class-`$a` marker; a natural `worker_obj` writer (`watch` tree word 2 over a Play Random Land run); a natural add-to-pile (drive `$12`/`$18` twice on one cell); the byte 44 `>= $12` overrun, the `$ab34` categories `$12 $16 $1a $1c $22`, and a per-site run of the chain walkers with a pile in the chain; the natural `$3aee` arm (once at 98M steps of `p0k60_s1`); the chunk-end clock values `$2df72` in `W5G_*_cN.snap`.
4. **Small checks.** Natural winter snow under the `$1abaa` gate; the crack's `$b842` patch and `$3c12`'s `nop`; health cap and food (`$5ccc`); rout fates on a third land; a natural `$66`; the dialog buttons `$04`, `$08`'s `$71` and `$131`.
5. **No current check exercises vector 4 on the unassigned `ImmediateToEa`/`BitOp` encodings** (README "Bug 7"): byte6 36-42 now bus-error first. An emulator-workstream item; a poke of `$0608` at a live PC would do.
6. **A player route to `$668c`** (low value) and **the stall on the original machine** (a Hatari run past clock 32768 with a camped group; Dave's go-ahead given).

## Known traps

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

## Next session

Open 2 (posture 5's lasting effect, `$5f78`) and the cheapest of Open 3 (`bp 158b6`, `bp 53f6` drive, the 144-land `$2eac` census) through parallel agents with `scratchpad/pm166/BRIEF.md` (one emulator each; spot-check one claim per report and rerun the gate from its promoted path). Merges write current-state prose only (CLAUDE.md "Docs").
