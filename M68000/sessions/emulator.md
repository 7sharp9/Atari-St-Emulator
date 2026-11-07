# Emulator and tooling: handoff

Updated 2026-11-07 by the session that built recordings on disk (Open 1 of the previous handoff).

## Resume point

- Last commit of this workstream: `7993e58` record: recordings on disk (record_start dir/keep, record_load). Commits
  `70c05c1`/`0ca35a5` (comment and dead-code cleanup, Dave's) were netted in worktree `agent-af7707af89a8b6449`: its
  `scratchpad/gates/*/last_run.json` read 49/49 PASS at 18:06 on 2026-11-03.
- Net on `7993e58` against a build of `0ca35a5` (`tools/regress_net.sh`, `CADAVER_SNAP=scratchpad/cadaver/s96/r6/s3_flask.snap`,
  `CADAVER_ST` = the root `Cadaver/` one-disk Empire `.st`): verify PASS both, 30M snapshot, game snapshot, 25 watch and
  11 DMA lines identical, selftest 1,000,051 pass 0 wrong 9 skip; `gates.py run all -j 1` 49/49. `bin/` and
  `server/bin/` hold the same `M68000.dll` (SHA-256 `8ec1f644…`), server built first. Logs were in the session
  scratchpad and are not kept.
- Working data: none. Proofs start from PowerMonger's `scratchpad/cmd10/leadkill/pre_pick.snap` (made by
  `reversing/powermonger/commander/leadkill/gate_leadkill.sh`) with `scratchpad/powermonger.st`.
- Uncommitted work left behind: none. Two agent worktrees remain (Dave to remove or keep): `agent-a6ad815bd9bc05d59`
  holds `893d133`, an earlier draft of master's `6cc74e9` (12 wording lines differ; master's is final), and
  `agent-af7707af89a8b6449` holds only the net run above (linked `tests`, cloned scratchpad, gate logs).

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
- Recording on disk (DEVELOPING.md "Record and replay", "A recording on disk"): `server/record_disk_proof.py` 9/9:
  12/12 replays in-process with 4 of 6 checkpoints evicted to file, 12/12 after `record_load` in a fresh process, a
  flipped RAM byte in one checkpoint file changes only the replay after it, and recordings from two processes diverge
  at the poke step (`$521cd`). Not exercised: a checkpoint taken while the CPU is `Stopped` (the manifest carries the
  flag) and a run that writes disk A (refused by `record_load` by design).
- Gate manifests: Black Tiger 15, Midwinter 8, PowerMonger 20, Super Sprint 6 (49).

## Running

Nothing running.

## Open, in priority order

1. Executed-PC coverage and comparison log (`tooling-ideas.md` idea 5, which replaces the old coverage item: that one's
   proof used Crude Buster, a MAME game this emulator cannot run). Positive controls: a PowerMonger longword-table
   handler `rdis.py` misses; blind rank of Black Tiger's `$85`/`$17826` compare and Impossamole's `LUMBAJAK`. Hot path:
   null-checked hook, interleaved A/B with no hook set (falsifier: slower by more than 3% in every pair).
2. `tools/stdrive.py` records to disk: pass `dir` to `record_start` so a drive's journal and checkpoints feed
   `last_writer`/`provenance.py` after the drive ends (`restore` is still refused while a recording is active, so a
   drive that forks must stop and restart its recording). Proven by slicing a byte at the end of
   `boss_stdrive.py --delay 700000` from the loaded recording against a REPL `watch`.
3. Gate manifests for Cadaver, Populous, Lemmings, Impossamole from counts their docs record (check each work dir
   exists first; an ERROR for a missing prerequisite is not a pass). Candidates already scripted: `snapdiff_proof.sh`,
   `layout_crosscheck.py`, `boss_stdrive.py --delay 700000` (cmp against `kill_d700000_end.snap`); the `server/*_proof.py`
   scripts (including `record_disk_proof.py`) are not gates yet.
4. `gates.py` records the DLL's SHA-256 in its summary, so a gate run is tied to its build like a sidecar snapshot.
5. `stserver` `read` cost: uncached reads made the boss fight about 3x slower than REPL `m`; the per-byte `sprintf` in
   `Server.fs` `read` is a hypothesis. Prove with an interleaved A/B of a 64 KB read loop before and after.
6. Go-Explore over forks (idea 7), now unblocked by recordings on disk, from
   `scratchpad/impossamole/pass108/nohop/BEST/seg3_pit_a.snap`; route repair (idea 8) belongs to the cadaver
   workstream's leg-25 item and uses `stdrive` plus `layout.toml`.
7. Ghidra import of snapshot RAM + `.sym` + coverage (not installed or checked); MAME model gaps (no HBL, coarse FDC,
   no IKBD power-up traffic), each an emulator change behind the net.

## Known traps

- `stserver.dll` is not built by `dotnet build M68000.fsproj`: build `M68000/server/StServer.fsproj` per checkout. That
  build also reinstalls `M68000.fsproj` into `bin/`, so build the server first and gate the DLL left in `bin/`
  (cmp `bin/` against `server/bin/`). A running Claude session's MCP `stserver` keeps the build it started with:
  restart the session after a server rebuild to see new tools (`record_load`).
- Two `Debug` builds of one source have differed with no source edit: tie every result to the DLL actually run
  (its SHA-256; a sidecar now records it per snapshot).
- A worktree's `checkpoint.txt` is a symlink to the main checkout's: `N checkpoint` there writes through to MAIN.
- `stdrive.replay` and `stdrive_check.py` need `--dll` in a checkout without its own `server/bin/`.
- For the supersprint workstream, not fixed here: `sound.md:58` and `secrets.md:97` give liveproof's Q as 15559/15559,
  while the script prints 15559/15560 over 15560 ISR invocations (as `sound.md:82` says).

## Waiting on Dave

- Push: master is ahead of origin.
- The two leftover agent worktrees (Resume point): remove or keep.
- For the impossamole workstream (not edited here): `sessions/impossamole.md` "Known traps" says the boss `Repl` does not
  record and a fight takes 40 s; `boss_stdrive.py` journals every input and a fight takes about 8 s.

## Next session

`/resume emulator`. Restart the Claude session first if the MCP `stserver` predates `7993e58` (it lacks `record_load`).
Then Open 1 (executed-PC coverage), which needs its hot-path A/B first; Open 2 (stdrive recording to disk) is small and
can go before it if a slicing question is waiting.
