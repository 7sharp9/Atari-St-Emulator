# Emulator and tooling: handoff

Updated 2026-11-12 by the session that built execution profiles, drive recordings to disk, gate DLL hashes and a
faster `stserver` `read` (Open 1, 2, 4 and 5 of the previous handoff).

## Resume point

- Last commit of this workstream: `1cd2453` server: bench_ab.py ...; the work is `1428261` (profiles), `b4a68cd`
  (stdrive recordings), `4067b77` (gates.py hashes), `019669a` (read).
- Installed build: `bin/` and `server/bin/` `M68000.dll` SHA-256 `a2dd7af2…` (source of `7993e58`, embedding commit
  `5b9c6a3`), `stserver.dll` `1924f4dd…` (HEAD's `Server.fs`). `uv run python tools/gates.py run all -j 1` 54/54 on
  `a2dd7af2…` with `stserver.dll` `94d3c74f…` (HEAD minus the read change; Super Sprint's two gates re-run under `uv`);
  on `1924f4dd…`: `smoke.py` ALL PASS, `profile_proof.py` 5/5, `stdrive_check.py` 5/5, `stdrive_record_check.py` 5/5,
  `record_disk_proof.py` 9/9, `provenance_proof.py` 178/178, gate `midwinter/period` PASS. 30M boot and a 10M Black
  Tiger resume byte-identical between `8ec1f644…` and `a2dd7af2…`.
- Working data: none. Proofs start from Black Tiger `scratchpad/black_tiger/play_start.snap` (`bt_auto.st`),
  Impossamole `agents/unpoked/hop4s/none/shop/seg5_pit_exit.snap` and `agents/secrets/data/name_entry.snap`, PowerMonger
  `scratchpad/cmd10/leadkill/pre_pick.snap` with `scratchpad/powermonger.st`.
- Uncommitted work left behind: none. `master` is 17 commits ahead of `origin/master` before this file's commit (5 of them this session's), not pushed.

## Proven so far

- Execution profiles (DEVELOPING.md "Execution profile"; tooling-ideas.md idea 5): `server/profile_proof.py` 5/5
  (Black Tiger level skip, `cmp.b #$47` `$c6c8` rank 1, `cmp.b #$85` `$c6d6` rank 2; 0 flag mismatches in 245,325);
  `reversing/impossamole/py/secrets/cheat_profile.py` (`--text LUMBAJAK`: `cmp.l` `$18358`/`$18364` ranks 1 and 2).
  No-profile cost within noise (`server/bench_ab.py step`), profile running about 1.5x.
- Drive recordings: `tools/stdrive_record_check.py` 5/5 (slice of `$1a645` = the REPL watch's last 12 writes).
- `stserver` `read`: `server/bench_ab.py read` 0.946 s -> 0.071 s median for 20 x 64 KB, same bytes.
- Earlier, unchanged: memory hooks and `stserver` (`smoke.py`), record and replay (`replay_proof.py` 12/12,
  `last_writer_proof.py` 20/20, `divergence_proof.py` 8/8, `record_disk_proof.py` 9/9), `last_reg_change` 412/412,
  `provenance.py` 178/178, snapshot provenance sidecar, `stdrive.py` (`stdrive_check.py` 5/5), `layout.py`/`snapdiff.py`
  (`snapdiff_proof.sh`, `layout_crosscheck.py` 39/39). DEVELOPING.md sections of the same names.
- Gate manifests: Black Tiger 15, Carrier Command 5, Midwinter 8, PowerMonger 20, Super Sprint 6 (54).

## Running

Nothing running.

## Open, in priority order

1. Gate manifests for Cadaver, Populous, Lemmings, Impossamole from counts their docs record (check each work dir
   exists first; an ERROR for a missing prerequisite is not a pass). Scripted candidates: `snapdiff_proof.sh`,
   `layout_crosscheck.py`, `boss_stdrive.py --delay 700000` (cmp `kill_d700000_end.snap`), `cheat_profile.py`; and a
   home for the `server/*_proof.py` and `tools/stdrive*_check.py` scripts, which are not gates yet.
2. Go-Explore over forks (idea 7) from `scratchpad/impossamole/pass108/nohop/BEST/seg3_pit_a.snap`, now with profiles
   (coverage as the novelty signal) and drive recordings; route repair (idea 8) belongs to the cadaver workstream.
3. Coverage against a static listing: a snapshot where PowerMonger's `a_worksh` `$1192e` runs (its `jsr 0(A1,D2.w)`
   table at `$11970` is the one form `rdis.py` misses); show covered handlers `$11898..$1191e` absent from `rdis.py`.
4. `sub`/`subq` then branch is not in the compare log; add it only when a hunt needs it.
5. Ghidra import of snapshot RAM + `.sym` + coverage (not installed or checked); MAME model gaps (no HBL, coarse FDC,
   no IKBD power-up traffic), each an emulator change behind the net.

## Known traps

- `stserver.dll` is not built by `dotnet build M68000.fsproj`: build `server/StServer.fsproj`, which also reinstalls
  the core into `bin/`; cmp `bin/` against `server/bin/` at resume. A running session's MCP `stserver` keeps the build
  it started with: restart the session to get new tools (`profile_start`).
- `M68000.dll` embeds HEAD's commit (`1.0.0+<sha>`), so a rebuild after any commit changes its SHA-256 (and about 29k
  bytes) with no source edit. Tie results to the DLL run, and settle "same source?" from `git log -- '*.fs'` plus a
  30M boot snapshot compare.
- Run `tools/gates.py` with `uv run python`: under the system `python3` the Super Sprint gates ERROR on `numpy`.
- A worktree's `checkpoint.txt` is a symlink to the main checkout's: `N checkpoint` there writes through to MAIN.
- `stdrive.replay` and `stdrive_check.py` need `--dll` in a checkout without its own `server/bin/`.
- For the supersprint workstream, not fixed here: `sound.md:58` and `secrets.md:97` give liveproof's Q as 15559/15559,
  while the script prints 15559/15560 over 15560 ISR invocations (as `sound.md:82` says).

## Waiting on Dave

- Push: `master` is 18 commits ahead of `origin/master` (with this file's commit), only on this Mac.
- For the impossamole workstream (not edited here): `sessions/impossamole.md` "Known traps" says the boss `Repl` does not
  record and a fight takes 40 s; `boss_stdrive.py` journals every input, records with `--record`, and a fight takes
  about 8 s on an idle machine (13 to 16 s at load average 20 to 30).

## Next session

`/resume emulator`; restart first if the MCP `stserver` lacks `profile_start`. Then Open 1 (gate manifests), which
turns this session's proofs into gates; Open 2 next if a search workload is waiting.
