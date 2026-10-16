# PowerMonger: handoff

Updated 2026-10-16 by the 163rd session (`5e7b2cd` .. `2a08938`; CLAUDE.md `f2c6019`), after the 162nd (`fc5956a` .. `f87aa4f`).

## Resume point

- Last commits of this workstream: `5e7b2cd` (byte6 36/38/42 under the bus-error model), `604403d` (posture-5 trade forward, melee formula fix), `2a08938` (design digest), then the handoff commit.
- `bin/Debug/net8.0/M68000.dll` is built from master `d6e6646`, which includes the bus-error change `90ea349` (`$400000..$f9ffff` and writes to `$0..$7` bus-error; a fault while stacking a group-0 frame halts the CPU). Dave merged it via `origin/master`; this session fast-forwarded and rebuilt.
- Working data: `M68000/scratchpad/pm163/` (gitignored): `p5fwd/` (the `trade5_fwd.sh` 2x2: `x_<arm>.out`, `x_<arm>_{30,60}.snap/.ram`, `drain.out`; `fwd.sh` with `p5x.fwd`/`p3x.fwd`, the plain arms over 100M), `p5fwd_first/` (the first 2x2, identical), `old/`. `pm156/overlay/cap/b6_NN_halt.snap` are the new bomb_check end states. Older: `pm162/` (`posture/trade/at63f4.snap`, the trade state), `pm161/`, `pm160/`, `pm156/`, `pm148/`, `pm142/`, `pm143/`, `pm123/`.
- Start from:
  - `scratchpad/pm142/rand1.snap`: Play Random Land with two player captains; the land ends about 676M steps in.
  - `scratchpad/pm162/posture/trade/at63f4.snap`: side 3 group 0 at the trade `$63f4` (A3 = `$51938`); the posture-5 arms start here.
  - `scratchpad/pm150/small/camp/c12_0.snap`: a lit camp fire in view; `pm148/arms/long/M2G_k118_c1.snap`: lit and put-out fires.
  - `scratchpad/pm162/g4a7a/nat/n4a7a_k120_a_1.snap`: the k120 sword click at `$4a7a`'s entry.
  - `scratchpad/pm97/pm97_map0.snap` (forest animator), `pm150/saveload/out/file.snap` (FILE panel), `pm123/win/m1_ready.snap` (mission 1 conquered), `pm88_f1.snap` (clear `$2c993` first).
- Uncommitted work left behind: none from this workstream. Not this workstream's: `.obsidian/`, `Cadaver/`.

## Proven so far

Older gates carry over unchanged; the list is in `strategy.md`, `ai.md`, `economy.md`, `system.md`, `graphics.md` and `port/SPEC.md`, with reruns from the `py/README.md` table. The 162nd pass's (camp markers, exact water, `$54`, posture-5 writers, piles, `$58054`, `$4a7a`) are in those docs.

New in the 163rd pass:

- **Byte6 36/38/42 halt the CPU** (port/SPEC.md §6, README "Bug 7"): `$1162e`'s first word `$065c` (`addi.w #$01aa,(A4)+`, A4 = `$fff95600`) bus-errors; the game's vector-2 handler `$112a` (`clr.l $2c1ba / rte`) pops the 14-byte frame as a 6-byte one and re-faults (235 laps at `$f95600`, 663 at `$f90000`), SSP walks onto the handler by step 113,936, and the push to `$6` double-faults at step 145,342. `$11640` and `$20` 0 hits, no TOS bombs; 3/3, end RAM equal but the poked byte `$51c98` (`py/xcheck/overlay/bomb_check.sh`, rewritten).
- **The forced posture-5 trade's byte-44 codes decide the next fight** (strategy.md "Posture 5"): `$63e8` writes `$84` (9 men) / `$92` (3); the signed `cmp.b #6 / blt` at `$1533c` passes them and `lsr.b` drains `$43`/`$4a`. 2x2 over 60M (posture 5/3 by codes kept/poked): with the codes the 12 men end at health `$56..$5a`, 0 dead, at either posture; without, `$1e..$58` with 1-2 dead; 60 sampled drains 26 x `$43`, 5 x `$4a`, 29 x `$01` (`py/cmdai/posture/trade5_fwd.sh`, deterministic over two runs).
- **Melee drain formula fixed in economy.md and strategy.md**: `((s8(v) < 6 ? v : 0) >> 1) + 1`, so a bow drains 1, not 4 (`ai.md` had it right).

## Open, in priority order

1. **Port residue.** The port tests `record[44] >= $e` unsigned where the game is signed: a forced posture-5 trade now produces `$84`/`$92` (no natural writer), and such a man draws the siege overlay in the port but not the game; decide whether the port follows the game (signed) and gate it on `x_P3B84_30` with a frame capture. Natural byte6 18 and 28 are unseen in play. The camp-marker screen pixel match of `$111`/`$112..$115` (blit position from `$11f78`'s D0/D1 on `M2G_k118_c1`) is not done.
2. **Posture 5 downstream, the rest.** The melee frame `$80 + code * 8 + (side-1) * 4` for a `$84` man (`$11c8a`, code read; capture a frame from `x_P5B84` mid-melee, chunk 4); the trade's clear of object 6 bytes 6..7 (`00 04` to 0 via `84(A3, 12 x $41)`) and of object 7 bytes 40..41 not followed; no natural posture-5 reader in about 444k steps; `$150f2`, `$1ce6`, `$3110`, `$90fe`, `$c77e` at posture 5 code read only.
3. **Small checks.** `$4a7a`'s foreign-man arm has no natural entry (a sword click on a lone enemy man via `capture_clicks.sh`); natural class `$a` (click a forest marker mid-walk, `bp 4eca`); what ends the class-`$a` shoot (`bp 35f4` from `classa/p16_c1`); the pile's catapult/cannon arm `$3a8e..$3aa4` and add-to-pile arm `$3a18`; a generic `8(An)` reader of chain records; whether anything writes 0 to a lord's nation while his town has merchants (the `$54` hang); the M2G_k90 empty lord slot 12 (`bp 2eac` at world build); natural winter snow under the `$1abaa` gate; a pile/`$58054` LOAD differing slot; the crack's `$b842` patch and `$3c12`'s `nop`; health cap and food (`$5ccc`); rout fates on a third land; a natural `$66`; the dialog buttons `$04`, `$08`'s `$71` and `$131`.
4. **No current check exercises vector 4 on the unassigned `ImmediateToEa`/`BitOp` encodings** (README "Bug 7"): byte6 36-42 now bus-error first. An emulator-workstream item; a poke of `$0608` at a live PC would do.
5. **A player route to `$668c`** (low value) and **the stall on the original machine** (a Hatari run past clock 32768 with a camped group; Dave's go-ahead given).

## Known traps

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

Take Open 1: decide the port's signed `record[44]` test (likely follow the game), change `port/godot/logic/` if so, gate it with a frame capture from `x_P3B84_30` (or a `pm88_f1` poke of `$84`), and rerun `py/xcheck/run.sh` and `overlay/score_cases.sh`. Then Open 2's `$84` melee frame capture, and a batch of Open 3's small checks through parallel agents with `scratchpad/pm162/BRIEF.md` (one emulator each; spot-check one claim per report and rerun every gate from its promoted path).
