# Emulator and tooling: handoff

Updated 2026-11-03 by the session that merged ideas 1-4 of `M68000/tooling-ideas.md` (four worktree agents) and ran the
net on master.

## Resume point

- Last commit of this workstream: `93bee98` stclient: a server that exits reports it. The merge is `fb97a4c..ffad571`
  (provenance sidecar and argv, `CLAUDE.md` "Running", `last_reg_change` + `tools/provenance.py`, `tools/stdrive.py`,
  `tools/layout.py` + `snapdiff.py`, `tooling-ideas.md`), applied as patches from master `97fe3c4`.
- Net on the merge against pre-merge master `97fe3c4` (`tools/regress_net.sh`, `CADAVER_SNAP=scratchpad/cadaver/s96/r6/s3_flask.snap`,
  one-disk Empire `.st`): verify PASS both, 30M snapshot, game snapshot, 25 watch and 11 DMA lines identical, selftest
  1,000,051 pass 0 wrong 9 skip; `gates.py run all -j 1` 49/49 at `ffad571`. `bin/` and `server/bin/` hold the same
  `M68000.dll` (SHA-256 `2915e6b0…`), server built first. Logs were in the session scratchpad and are not kept.
- Working data: none. Proofs start from PowerMonger's `scratchpad/cmd10/leadkill/pre_pick.snap` (made by
  `reversing/powermonger/commander/leadkill/gate_leadkill.sh`) with `scratchpad/powermonger.st`.
- Uncommitted work left behind: none. The agents' worktrees and branches are removed.

## Proven so far

- MMU memory hooks and `stserver`: DEVELOPING.md "Memory hooks and the `stserver` process"; `server/smoke.py` all pass,
  32 tools in `tools/list`.
- Record and replay (DEVELOPING.md "Record and replay"), from `pre_pick.snap`: `server/replay_proof.py` 12/12,
  `last_writer_proof.py` 20/20, `divergence_proof.py` 8/8 (agent run; on the merge the last three checks were captured, all PASS).
- `last_reg_change`: `server/last_reg_change_proof.py` 412/412 against a per-step brute force (251/412 with the backward
  search removed). `tools/provenance.py` backward slice: `server/provenance_proof.py` 178/178 links against REPL
  `watch`/`bp`, `set_reg` and poke controls reach "input". Value rules REPL-scored only for `move`, `addi`, `sub`,
  `subi`, `lea`, `adda`; 50 arithmetic links carry no value check.
- Snapshot provenance sidecar (DEVELOPING.md, Disk A and provenance paragraphs): a resume without `--disk-a` remounts
  the recorded disk (DMA reads succeed; the same snapshot without a sidecar gets `no data`); a raw alias argv exits 2.
- `tools/stdrive.py`: Impossamole's `py/boss/boss_stdrive.py --delay 700000` ends byte-identical to
  `pass108/boss/kill_d700000_end.snap` and its journal replays to the same bytes (re-run by this session);
  `tools/stdrive_check.py` 5/5 (agent run); one fight about 8 s, same as the REPL script.
- `tools/layout.py`/`snapdiff.py` (DEVELOPING.md "Memory layouts and the semantic snapshot diff"):
  `reversing/cadaver/py/snapdiff_proof.sh` names hero x 29 -> 41 with input and no field in the control;
  `reversing/impossamole/py/boss/layout_crosscheck.py` 39/39 twice, control 8/13 mismatch.
- Gate manifests: Black Tiger 15, Midwinter 8, PowerMonger 20, Super Sprint 6 (49).

## Running

Nothing running.

## Open, in priority order

1. Recording on disk: checkpoints past a memory budget spill to `SaveState` files (`base.snap`, `journal.jsonl`,
   `ck_<step>.snap`), `record_load` reads them back. Unblocks Go-Explore (idea 7) and slicing a stdrive drive (its
   journal cannot feed `last_writer` today, and `restore` is refused while a recording is active). Proven by
   `replay_proof.py` on a saved-then-loaded recording and a `first_divergence` across two processes.
2. Executed-PC coverage and comparison log (`tooling-ideas.md` idea 5, which replaces the old coverage item: that one's
   proof used Crude Buster, a MAME game this emulator cannot run). Positive controls: a PowerMonger longword-table
   handler `rdis.py` misses; blind rank of Black Tiger's `$85`/`$17826` compare and Impossamole's `LUMBAJAK`. Hot path:
   null-checked hook, interleaved A/B with no hook set (falsifier: slower by more than 3% in every pair).
3. Gate manifests for Cadaver, Populous, Lemmings, Impossamole from counts their docs record (check each work dir
   exists first; an ERROR for a missing prerequisite is not a pass). Candidates already scripted: `snapdiff_proof.sh`,
   `layout_crosscheck.py`, `boss_stdrive.py --delay 700000` (cmp against `kill_d700000_end.snap`).
4. `gates.py` records the DLL's SHA-256 in its summary, so a gate run is tied to its build like a sidecar snapshot.
5. `stserver` `read` cost: uncached reads made the boss fight about 3x slower than REPL `m`; the per-byte `sprintf` in
   `Server.fs` `read` is a hypothesis. Prove with an interleaved A/B of a 64 KB read loop before and after.
6. Go-Explore over forks (idea 7) after 1, from `scratchpad/impossamole/pass108/nohop/BEST/seg3_pit_a.snap`; route
   repair (idea 8) belongs to the cadaver workstream's leg-25 item and uses `stdrive` plus `layout.toml`.
7. Ghidra import of snapshot RAM + `.sym` + coverage (not installed or checked); MAME model gaps (no HBL, coarse FDC,
   no IKBD power-up traffic), each an emulator change behind the net.

## Known traps

- `stserver.dll` is not built by `dotnet build M68000.fsproj`: build `M68000/server/StServer.fsproj` per checkout. That
  build also reinstalls `M68000.fsproj` into `bin/`, so build the server first and gate the DLL left in `bin/`
  (cmp `bin/` against `server/bin/`). A running Claude session's MCP `stserver` keeps the build it started with:
  restart the session after a server rebuild to see new tools (`last_reg_change`).
- Two `Debug` builds of one source have differed with no source edit: tie every result to the DLL actually run
  (its SHA-256; a sidecar now records it per snapshot).
- A worktree's `checkpoint.txt` is a symlink to the main checkout's: `N checkpoint` there writes through to MAIN.
- `stdrive.replay` and `stdrive_check.py` need `--dll` in a checkout without its own `server/bin/`.
- For the supersprint workstream, not fixed here: `sound.md:58` and `secrets.md:97` give liveproof's Q as 15559/15559,
  while the script prints 15559/15560 over 15560 ISR invocations (as `sound.md:82` says).

## Waiting on Dave

- Push: master is ahead of origin by the merge commits and this handoff.
- For the impossamole workstream (not edited here): `sessions/impossamole.md` "Known traps" says the boss `Repl` does not
  record and a fight takes 40 s; `boss_stdrive.py` journals every input and a fight takes about 8 s.

## Next session

`/resume emulator`. Restart the Claude session first if the MCP `stserver` predates `ffad571`. Then Open 1 (recording
on disk), proven by `replay_proof.py` on a loaded recording; it unblocks idea 7 and slicing stdrive drives. Open 2 is
next and needs its hot-path A/B.
