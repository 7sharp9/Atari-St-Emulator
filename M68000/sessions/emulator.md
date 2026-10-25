# Emulator and tooling: handoff

Updated 2026-10-25 by the session that ended at commit `19914a2`.

## Resume point

- Last commit of this workstream: `19914a2`, the merge of the doc address lint and gate runner (`232e9f3`), after `249562d`, the
  merge of stserver and the MMU memory hooks.
- Working data: none kept; the net and smoke outputs were session scratch (rebuild with `tools/regress_net.sh`, `server/smoke.py`).
- Start from: master; `bin/` and `server/bin/` built from `249562d`.
- Uncommitted work left behind: none. Nothing pushed.

## Proven so far

- MMU memory hooks (`MMU.AddHook`: many ranges, read/write, PC, step, width, source cpu/dma/host) and `stserver`
  (JSON-RPC 2.0 and MCP over stdio, registered in `.mcp.json`): `DEVELOPING.md` "Memory hooks and the `stserver` process".
  `server/smoke.py` 12 of 12 on the merged build (25 watch events at writer PC `$01529c`, fork/restore replay identical).
- The merge keeps the REPL `watch` output of master: per-sector `DMA read sector` lines, not per-byte DMA hook events.
  Against a pre-merge master build: verify 5000000 PASS, 30M diskless snapshot, Cadaver `gameplay_empire.snap` 2M-step
  snapshot, its 25 `WATCH` lines and a cold-boot DMA watch (11 lines) all byte-identical; selftest 1000051 pass, 0 wrong,
  9 skip (`tools/regress_net.sh`).
- No-hook speed cost within noise (interleaved A/B, 5 pairs: boot 6.94 vs 6.97 s median, Cadaver 10M 2.29 vs 2.29 s; DEVELOPING.md "Hot path").
- Game-level check of the hooks merge: `tools/gates.py run all` (manifests `reversing/{black_tiger,powermonger}/gates.toml`)
  passes all 35 gates (Black Tiger 15, PowerMonger 20) on `bin/` built from `249562d`, as on the pre-merge DLL; each gate drives
  the REPL, the 0-1 s ones are short `callcap`s. After the second merge, `run black_tiger` 15/15 again from master.
- `tools/doc_addrs.py` (every doc mention of an address or `N(An)` field; `--check <game>` against the `.sym`). Its PowerMonger
  findings (`graphics.md:617` `$14bba` vs `$14bb4`, `strategy.md:1365` `pm_30fe` vs `pm_get_posture`, `ai.md:705` 74 vs 75 FSM
  entries) are for the powermonger workstream, unchecked.

## Open, in priority order

1. Make `gates.py run all` part of the section 6 net (skill) and seed manifests for the other games (Cadaver, Populous, Lemmings,
   Impossamole, Super Sprint) from the counts their docs cite.
2. Record and replay on top of the hooks: checkpoints every N steps plus inputs, replayed to answer "last writer of X before step S"
   and "first divergence of two runs". Proven when it reproduces a known `watch` result outside a recorded window
   (PowerMonger's `commander/leadkill/gate_leadkill.sh win` melee at 1457M).
3. Executed-PC coverage per game (a 16M-bit set merged across runs), used to seed `rdis.py`/Ghidra roots past longword state
   tables. Proven when it recovers Crudebuster's 67 callers `rdis.py` missed.
4. Ghidra import of snapshot RAM + `.sym` + coverage behind pyghidra-mcp (not installed or checked yet).
5. The known model gaps from the MAME comparison (no HBL, coarse FDC, no IKBD power-up traffic) and the ACIA FIFO pop on read
   (`CLAUDE.md`, "Emulator behaviours"): each an emulator change behind the net.

## Known traps

- `stserver.dll` is not built by `dotnet build M68000.fsproj`; each checkout needs `dotnet build -c Debug M68000/server/StServer.fsproj`
  before the `.mcp.json` entry works, and a running Claude session does not pick it up.
- `dotnet build ... -o <scratch>` of `StServer.fsproj` (a ProjectReference to the core) did not touch `bin/` here (mtime checked).

## Next session

Add `gates.py run all` to the skill's section 6 and seed one more game's manifest (Open 1). Then design record/replay (Open 2) as a DEVELOPING.md section before code, using the hook API and `AtartSt.Capture/Restore`.
