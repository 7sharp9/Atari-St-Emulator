# Emulator and tooling: handoff

Updated 2026-10-25 by the session that ended at commit `6824746` (this handoff is the commit after it).

## Resume point

- Last work commit of this workstream: `6824746`, Super Sprint `gates.toml` and the record/replay design in DEVELOPING.md;
  before it `1f90b6f`, `gates.py run all` as step 5 of the skill's section 6 net.
- Working data: none kept. Gate logs are under `scratchpad/gates/<game>/` (rebuild: `uv run python tools/gates.py run <game>`).
- Start from: master; `bin/` and `server/bin/` built from `249562d` (no core change since).
- Uncommitted work left behind: none. Nothing pushed.

## Proven so far

- MMU memory hooks and `stserver` (JSON-RPC and MCP): DEVELOPING.md "Memory hooks and the `stserver` process"; `server/smoke.py`
  12 of 12; REPL `watch` output, verify, 30M snapshot, Cadaver snapshot and DMA watch byte-identical to pre-merge master;
  selftest 1000051 pass, 0 wrong, 9 skip (`tools/regress_net.sh`). No-hook speed cost within noise (5-pair interleaved A/B).
- Section 6 of the skill now ends with `tools/gates.py run all` (every gate PASS); CLAUDE.md's net summary says the same.
- Gate manifests: Black Tiger 15, PowerMonger 20 (35/35 pass on `249562d`), Super Sprint 6 (`reversing/supersprint/gates.toml`:
  trajectory 700 frames, drone_diff 576/576, winner_diff 46/46, plane2 512000/512000, hazard_seeds 1400/1400, liveproof
  Q 15559/15560, J 1187/1187, M 125/125), 6/6 pass at `7302198` in about 5 min. `plane2` runs no emulator (reads saved snaps).
  Black Tiger plus PowerMonger take about 14 min at `-j 1`.
- Record/replay is designed (DEVELOPING.md "Record and replay (designed, not built)"): an input journal in `AtartSt`,
  checkpoints every N steps, `replay_to`/`last_writer`/`first_divergence` as `stserver` methods, three pre-registered proofs
  from PowerMonger's `commander/leadkill/pre_pick.snap`. The old proof target (the 1457M melee) was dropped: `loop.py --replay`
  already reproduces it.
- Found, not fixed: `MachineCheckpoint` lacks `keyInjectGroups` (`Program.fs:180`, popped at `:439-441`), so `Restore`,
  `Preview` and `detcheck` across a fired `ATARI_KEY_INPUT` group do not re-inject it. REPL `kbd` is unaffected.

## Open, in priority order

1. Add `keyInjectGroups` to `MachineCheckpoint` (Capture/Restore), behind the section 6 net including `gates.py run all`.
   Proven by a `detcheck` across an armed `ATARI_KEY_INPUT` schedule that fails before the change and passes after.
2. Build record/replay as designed; proven by the three pre-registered tests in that section (replay_to byte-identical at
   11 steps, last_writer 20/20 against a full `watch 53006 2` list, first_divergence at the journalled `w 521cc` step).
3. Seed gate manifests for Cadaver, Populous, Lemmings, Impossamole from counts their docs record (check each work dir
   exists on this machine first; an ERROR for a missing prerequisite is not a pass).
4. Executed-PC coverage per game (16M-bit set merged across runs) to seed `rdis.py`/Ghidra roots past longword state tables;
   proven when it recovers Crudebuster's 67 callers `rdis.py` missed. A recording (item 2) can produce it by replay.
5. Ghidra import of snapshot RAM + `.sym` + coverage behind pyghidra-mcp (not installed or checked).
6. Model gaps from the MAME comparison (no HBL, coarse FDC, no IKBD power-up traffic) and the ACIA FIFO pop on read
   (CLAUDE.md "Emulator behaviours"), each an emulator change behind the net.

## Known traps

- `stserver.dll` is not built by `dotnet build M68000.fsproj`; each checkout needs `dotnet build -c Debug M68000/server/StServer.fsproj`
  before the `.mcp.json` entry works, and a running Claude session does not pick it up.
- `dotnet build ... -o <scratch>` of `StServer.fsproj` (a ProjectReference to the core) did not touch `bin/` here (mtime checked).
- For the supersprint workstream, not fixed here: `sound.md:58` and `secrets.md:97` give liveproof's Q as 15559/15559, while the
  script prints 15559/15560 over 15560 ISR invocations (as `sound.md:82` says).

## Next session

Do Open 1 (`keyInjectGroups` in the checkpoint) as a small emulator change behind the full net, which is also the first real use
of step 5. Then start Open 2 in an `isolation: "worktree"` agent or here: the journal in `AtartSt` first, then `replay_to` and
its byte-identity proof before the two search queries.
