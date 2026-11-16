# Emulator and tooling: handoff

Updated 2026-11-16 by the session that modelled the WD1772 busy search, motor-on bit and Read Track, and the MFP
in-service registers with paced IKBD bytes, and gated both.

## Resume point

- Last commit of this workstream: `8646fd2` gates: archipelagos unpoked and carriercommand mouse; the emulator work is
  `c859b89` (MFP in-service, IKBD pacing, snapshot v13), `09fbb9a` (FDC busy search, Force Interrupt, motor-on bit,
  ACSI bytes kept off drive A), `3b26da7` (Read Track), `8d9dc73` (CLAUDE.md), `37dd7d0` (Archipelagos README).
- Installed build: `bin/` and `server/bin/` `M68000.dll` SHA-256 `1620cb81…` (embedding commit `3b26da7`), `stserver.dll`
  `e0f474f6…`. `checkpoint.txt` was regenerated from this build (it now reads the motor-on bit at 5M steps: D0
  `$ffffff84`, D7 `$3cd33`); the previous one is `M68000/scratchpad/checkpoint.txt.pre-fdc-motor`.
- Working data: none. The pre-change build used as the control is `/private/tmp/claude-501/fdc/base/` (a 404b3c5
  build, outside the repo and not durable): rebuild one with `git worktree add` at `4419e9f` and
  `dotnet build -c Debug M68000.fsproj -o <dir>`.
- Uncommitted work left behind: none. The two agent worktrees and their branches (FDC tip `1df1410`, MFP tip
  `0a4c7f7`) were removed after `git merge-tree` showed master already holds both.

## Proven so far

- Net on the merged build (`tools/regress_net.sh` against the 404b3c5 build, Cadaver inputs): selftest 1,000,051 pass,
  0 wrong, 9 skip; Cadaver game and DMA watches identical (25 and 11 lines); `uv run python tools/gates.py run all -j 3`
  80/80 PASS on `1620cb81…`. The 30M diskless snapshot differs from the old build in 269 bytes; against the FDC branch
  alone in 1 byte (ISRB, TOS inside its Timer C handler) plus the version byte and the 4 appended bytes.
- FDC: Archipelagos loads without its pokes, gate `archipelagos/unpoked` (bp `$1301c` at 4,735,885 steps, RAM
  differences inside the poke ranges 4/4 and 9/9; the 404b3c5 build gives 4/60880 and 10/255347). Archipelagos README
  "The emulator gap and the two pokes"; DEVELOPING.md "Busy search and the motor-on bit".
- MFP: gate `carriercommand/mouse` (pointer (160,100) -> (160,45), `$1244 = ff`; old build (160,100) and `00`).
  Carrier README "Mouse input"; DEVELOPING.md "IKBD command interpreter".
- Read Track: Captive's Copylock still adds key 0 (`captive/system.md` 7); Carrier's `$2119e` returns in 41 steps with
  the synthesised track (Carrier README, "Read from code"). Not gated.
- Earlier, unchanged: execution profiles (`server/profile_proof.py` 5/5), drive recordings
  (`tools/stdrive_record_check.py` 5/5), `stserver` `read` speed (`server/bench_ab.py read`), record and replay,
  provenance, `layout.py`/`snapdiff.py`: DEVELOPING.md sections of the same names.
- Gate manifests: 82 gates in all, 76 declaring no inputs (`gates.py run all --dry-run`, 0 MISSING).

## Running

Nothing running.

## Open, in priority order

1. Cycle counting, stage 1: count 68000 cycles per instruction (Hatari's tables, which `68k.fs` already cross-checks
   in places) and report them only. Proof: byte-identical 30M snapshot and 82/82 gates; then measure instructions per
   frame in several games against the fixed 12,000. That number decides stage 2 (VBL, HBL and timers from cycles behind
   a flag; Midwinter's menu `$a5e0` without its `rte` poke is the test, `midwinter/README.md`). Dave asked about it; it
   changes every step-denominated rule, so stage 2 needs his go-ahead.
2. MFP arbitration order: Timer B should outrank the ACIA (DEVELOPING.md "IKBD command interpreter"). Proof: net plus a
   game that raster-splits while reading the keyboard.
3. FDC gaps left: spin-up and its status bit, the index bit, Record Not Found timing on a single-sector command, the
   sector register advancing in a multi-sector read, Read Track taking a revolution. Each only when a loader needs it.
4. Gate manifests for Cadaver, Populous, Lemmings, Impossamole from counts their docs record (check each work dir
   first); a home for `server/*_proof.py` and `tools/stdrive*_check.py`, which are not gates yet.
5. Go-Explore over forks (tooling idea 7) from `scratchpad/impossamole/pass108/nohop/BEST/seg3_pit_a.snap`; coverage
   against a static listing (PowerMonger `$1192e`, handlers `$11898..$1191e`); `sub`/`subq` in the compare log;
   Ghidra import; MAME model gaps (no HBL, no IKBD power-up traffic).

## Known traps

- A copy of `M68000.dll` alone does not run (`dotnet exec` exits 131): a control build is its whole `-o` directory.
- `stserver.dll` is not built by `dotnet build M68000.fsproj`: build `server/StServer.fsproj`, which also reinstalls the
  core into `bin/`; cmp `bin/` against `server/bin/`. A session's MCP `stserver` keeps the build it started with.
- `M68000.dll` embeds HEAD's commit, so a rebuild after any commit changes its SHA-256 with no source edit.
- Run `tools/gates.py` with `uv run python`: under the system `python3` the Super Sprint gates ERROR on `numpy`.
- A worktree's `checkpoint.txt` is a symlink to the main checkout's: `N checkpoint` there writes through to MAIN.
- `stdrive.replay` and `stdrive_check.py` need `--dll` in a checkout without its own `server/bin/`.
- Snapshots made before `c859b89`/`09fbb9a` resume with ISR zeroed and no FDC countdowns: a resume of a mid-load
  snapshot from an older build is not the run the new build would have made.

## Waiting on Dave

- Push: `master` is 15 commits ahead of `origin/master` with this file's commit, only on this Mac.
- Stale in other workstreams' handoffs (not edited here): `sessions/archipelagos.md` Open 1 (the emulator gap, now
  fixed and gated) and its "Both loader pokes applied" snapshots; `sessions/carriercommand.md` Open 6 (`$2119e` now
  returns); `sessions/captive.md` Open 5 (Read Track now modelled); for supersprint, `sound.md:58` and `secrets.md:97`
  give liveproof's Q as 15559/15559 where the script prints 15559/15560.

## Next session

`/resume emulator`. Check `bin/` still hashes `1620cb81…` (or re-run the net on whatever replaced it). Then Open 1
stage 1 (cycle counting with no behaviour change, then the instructions-per-frame survey), which decides whether the
timing rework is worth doing; Open 2 is the cheaper standalone fix if a raster game needs it.
