# Emulator and tooling: handoff

Updated 2026-10-31 by the session that ended at commit `cac70ad` on branch `claude/emulator-keyinject-journal-7765eb`
(a worktree; not merged, not pushed).

## Resume point

- Last work commits of this workstream, on `claude/emulator-keyinject-journal-7765eb` (base `367ece7`, master's tip
  when cut): `dabdd67` the checkpoint carries the unfired `ATARI_KEY_INPUT` groups; `cac70ad` record and replay
  (journal, `replay_to`, `last_writer`, `first_divergence`). Dave merges; after the merge, build into `bin/` and
  `server/bin/` and re-run the net against a pre-merge master build (`tools/regress_net.sh`).
- Working data: none kept in the repo. The worktree's `M68000/scratchpad/` is an APFS clone (`cp -cR`) of the main
  checkout's, made so `gates.py run all` could run against the worktree's own `bin/`; it is disposable.
- Start from: master once the branch is merged; the proofs start from PowerMonger's
  `scratchpad/cmd10/leadkill/pre_pick.snap` (made by `reversing/powermonger/commander/leadkill/gate_leadkill.sh`).
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
- Gate manifests: Black Tiger 15, Midwinter 7, PowerMonger 20, Super Sprint 6 (48 in all).

## Running

Nothing running.

## Open, in priority order

1. Phantom key after a multi-byte IKBD burst (regression from `5636dc5`, on master; reported by the Cadaver session,
   mechanism read in `MMU.fs`'s `$FFFC02` read, not yet driven here). The read re-raises channel 6 while bytes remain
   (for Super Sprint's one-byte-per-interrupt ISR `$104b6`); an ISR that loops on GPIP bit 4 (Cadaver `$1535a`) drains
   the burst in one entry, the pending re-raise re-enters it with the FIFO empty, and the empty read now returns the
   latched last byte (it returned 0 before v12), stored as a make. Evidence: `scratchpad/cadaver/s96/r6/s3_flask.snap`,
   `kbd ff 08` + `s 300000` moves the hero x 29->41 on `0b92317` and 29->29 on current `bin/`. Fix candidate: drop the
   re-raised request at interrupt acknowledge when the FIFO has emptied (level-triggered, as a 6850 IRQ is). Proven by
   that Cadaver test moving the hero again, Super Sprint's gates still 6/6 (its burst ISR), and the full net.
2. Recording on disk: checkpoints past a memory budget spill to `SaveState` files (`base.snap`, `journal.jsonl` with a
   disk swap as path plus FNV hash, `ck_<step>.snap`), `record_load` reads it back, so a recording outlives the
   process and a 1G-step run fits. Proven by `replay_proof.py` passing on a saved-then-loaded recording, and a
   `first_divergence` between two recordings from different processes.
3. Seed gate manifests for Cadaver, Populous, Lemmings, Impossamole from counts their docs record (check each work dir
   exists on this machine first; an ERROR for a missing prerequisite is not a pass).
4. Executed-PC coverage per game (16M-bit set merged across runs) to seed `rdis.py`/Ghidra roots past longword state
   tables; proven when it recovers Crudebuster's 67 callers `rdis.py` missed. A recording can now produce it by replay.
5. Ghidra import of snapshot RAM + `.sym` + coverage behind pyghidra-mcp (not installed or checked).
6. Model gaps from the MAME comparison (no HBL, coarse FDC, no IKBD power-up traffic) and the ACIA FIFO pop on read
   (CLAUDE.md "Emulator behaviours"), each an emulator change behind the net.

## Known traps

- `stserver.dll` is not built by `dotnet build M68000.fsproj`; each checkout needs `dotnet build -c Debug M68000/server/StServer.fsproj`
  before the `.mcp.json` entry works, and a running Claude session does not pick it up. The main checkout's
  `server/bin/` predated snapshot format v12 on 2026-10-31 (its snapshots are one byte short).
- A worktree has no untracked inputs: link `TOS100UK.IMG`, `tests` and `checkpoint.txt` from the main checkout's
  `M68000/` (`verify` fails with "No checkpoint.txt found" otherwise), and clone the scratchpad with `cp -cR` (APFS,
  no space used) before `gates.py run all`, since every gate script reads `<root>/bin/` and `<root>/scratchpad/`.
  The worktree already holds a tracked `scratchpad/ANCHORS.md`, so `cp -cR <main>/scratchpad ./scratchpad` nests the
  copy one level down; copy its contents instead.
- Two `Debug` builds of one source were byte-identical once (`-o` dirs `open1bin` and `new`) and differed another time
  (`rec3` against `bin/`, same size, with mutant builds sharing `obj/` in between and no source edit this session
  tracked): tie every result to the DLL actually run, and re-run the proofs on the build that is gated.
- For the supersprint workstream, not fixed here: `sound.md:58` and `secrets.md:97` give liveproof's Q as 15559/15559, while the
  script prints 15559/15560 over 15560 ISR invocations (as `sound.md:82` says).

## Waiting on Dave

- Merge `claude/emulator-keyinject-journal-7765eb` (two commits on `367ece7`); then rebuild `bin/` and `server/bin/`
  in the main checkout, which the 13 game sessions share.
- Proposed CLAUDE.md line for "Emulator changes" (not made: other sessions were live): "A worktree runs `gates.py run
  all` against its own `bin/` after linking `TOS100UK.IMG`, `tests` and `checkpoint.txt` from the main `M68000/` and
  cloning the scratchpad's contents with `cp -cR` (APFS, no space); `--root` would run the main checkout's DLL."
  The trap is under "Known traps" until then.

## Next session

After the merge, rebuild `bin/` and `server/bin/` and re-run the net against pre-merge master. Then Open 1 (the IKBD burst phantom key, a regression on master), then Open 2: the saved
form of a recording (spill and `record_load`), proven by `replay_proof.py` on a loaded recording. A game session can
already use `record_start`/`last_writer` through `stserver` for "who wrote X" questions.
