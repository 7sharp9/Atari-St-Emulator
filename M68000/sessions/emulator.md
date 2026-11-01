# Emulator and tooling: handoff

Updated 2026-11-01 by the session that merged the worktree branch (merge `7df69a2`) and ran the net on master.

## Resume point

- Last commit of this workstream: `7df69a2` Merge branch `claude/emulator-keyinject-journal-7765eb` (`dabdd67` the
  checkpoint carries the unfired `ATARI_KEY_INPUT` groups; `cac70ad` record and replay; `4e10c03` the IKBD burst
  phantom key), cut from `367ece7`.
- Net on the merge against pre-merge master `ce7cc93` (`tools/regress_net.sh`, both sides built with `-o`,
  `CADAVER_SNAP=scratchpad/cadaver/s96/r6/s3_flask.snap`, `CADAVER_ST=../Cadaver/*[one disk].st`): verify PASS both,
  30M snapshot, Cadaver game snapshot, 25 watch lines and 11 DMA lines identical, selftest 0 wrong 9 skip. Installed
  into `bin/` (byte-identical to the netted build), then `gates.py run all -j 2` 49/49 PASS. Logs were in the
  session scratchpad and are not kept.
- `server/bin/` rebuilt from master after the merge: `server/smoke.py` ALL PASS (11 checks) and `server/replay_proof.py`
  12/12 on it. `bin/` and `server/bin/` both hold the gated `M68000.dll` (copied from the netted build: see Known traps).
- Working data: none. Proofs start from PowerMonger's `scratchpad/cmd10/leadkill/pre_pick.snap` (made by
  `reversing/powermonger/commander/leadkill/gate_leadkill.sh`).
- Uncommitted work left behind: none.

## Proven so far

- MMU memory hooks and `stserver` (JSON-RPC and MCP): DEVELOPING.md "Memory hooks and the `stserver` process";
  `server/smoke.py` all pass (11 checks), 31 tools in `tools/list`.
- The in-memory checkpoint (`Capture`/`Restore`, so `Preview`, `detcheck`, `fork`; `callcap` alongside) carries the
  unfired `ATARI_KEY_INPUT` groups: `detcheck 100000` across a fired group diverged before and passes after
  (DEVELOPING.md "Snapshot / preview fidelity"). Net and `gates.py run all` 48/48 on that build.
- Record and replay (DEVELOPING.md "Record and replay"), all from `pre_pick.snap`: `server/replay_proof.py` 12/12
  byte-identical snapshots (9/12 with the journal re-apply removed); `server/last_writer_proof.py` 20/20 against a REPL
  `watch 53006 2` (16/20 without the backward search); `server/divergence_proof.py` 8/8 (the `r39` poke found at its
  step, `$521cd` the only differing byte; identical runs equal; 4 fail with an off-by-one search). Net against the
  Open 1 build identical; REPL input commands (`w`, `kbd`, `mouse`, `wprot`, `disk`) give identical results.
- A `$FFFC02` read that empties the IKBD FIFO withdraws the pending ACIA interrupt (DEVELOPING.md "IKBD command
  interpreter"): Cadaver's `kbd ff 08` from `scratchpad/cadaver/s96/r6/s3_flask.snap` moves the hero x 29 -> 41
  again (29 -> 29 before; the split-byte control 29 -> 41 on both). Net identical, gates 48/48, proofs unchanged.
- Gate manifests: Black Tiger 15, Midwinter 8, PowerMonger 20, Super Sprint 6 (49 in all).

## Running

Nothing running.

## Open, in priority order

1. Recording on disk: checkpoints past a memory budget spill to `SaveState` files (`base.snap`, `journal.jsonl` with a
   disk swap as path plus FNV hash, `ck_<step>.snap`), `record_load` reads it back, so a recording outlives the
   process and a 1G-step run fits. Proven by `replay_proof.py` passing on a saved-then-loaded recording, and a
   `first_divergence` between two recordings from different processes.
2. Seed gate manifests for Cadaver, Populous, Lemmings, Impossamole from counts their docs record (check each work dir
   exists on this machine first; an ERROR for a missing prerequisite is not a pass).
3. Executed-PC coverage per game (16M-bit set merged across runs) to seed `rdis.py`/Ghidra roots past longword state
   tables; proven when it recovers Crudebuster's 67 callers `rdis.py` missed. A recording can now produce it by replay.
4. Ghidra import of snapshot RAM + `.sym` + coverage behind pyghidra-mcp (not installed or checked).
5. Model gaps from the MAME comparison (no HBL, coarse FDC, no IKBD power-up traffic) and the ACIA FIFO pop on read
   (CLAUDE.md "Emulator behaviours"), each an emulator change behind the net.

## Known traps

- `stserver.dll` is not built by `dotnet build M68000.fsproj`; each checkout needs `dotnet build -c Debug M68000/server/StServer.fsproj`
  before the `.mcp.json` entry works, and a running Claude session does not pick it up. The main checkout's
  `server/bin/` predated snapshot format v12 on 2026-10-31 (its snapshots are one byte short).
- `dotnet build StServer.fsproj` also rebuilds `M68000.fsproj` and installs it into `bin/`: after the merge that build
  differed from the gated one in 28,575 bytes with no source change, so the gated DLL was copied back over both.
  Build the server before gating, or re-gate after it.
- Two `Debug` builds of one source were byte-identical once (`-o` dirs `open1bin` and `new`) and differed another time
  (`rec3` against `bin/`, same size, with mutant builds sharing `obj/` in between and no source edit this session
  tracked): tie every result to the DLL actually run, and re-run the proofs on the build that is gated.
- For the supersprint workstream, not fixed here: `sound.md:58` and `secrets.md:97` give liveproof's Q as 15559/15559, while the
  script prints 15559/15560 over 15560 ISR invocations (as `sound.md:82` says).

## Waiting on Dave

Nothing.

## Next session

Open 1: the saved form of a recording (spill and `record_load`), proven
by `replay_proof.py` on a loaded recording. A game session can already use `record_start`/`last_writer` through
`stserver` for "who wrote X" questions.
