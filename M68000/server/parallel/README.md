# Many `AtartSt` machines in one process

The question: can one process step many independent `AtartSt` machines on parallel threads (the commander's
rollouts, a Go-Explore over forks) instead of one emulator process per candidate (about 36 at once,
`sessions/commander.md`), and is it worth it?

**Verdict: safe as is, but not worth doing for throughput or memory.** No shared state can change emulated
state with the trace variables unset: 482 end snapshots from threaded, sequential and multi-process arms (K up to 16,
two games mixed across threads, workstation and server GC) were byte-identical to the single-thread reference. But
under the emulator's own workstation GC, K threads in one process reach only about 55-60% of the throughput of K
processes at K = 8 and 16 (13.0 vs 23.9 and 15.3 vs 25.4 Msteps/s, medians), because every thread's allocation drives
one shared gen-0 heap and each gen-0 collection stops all threads. Server GC removes that (22.3 and 25.9 Msteps/s, level
with processes) but holds 2.3 to 2.7 GB resident for the process at every K, more than 16 real emulator processes take (61 MB
each, about 1 GB). What one process would still save is start-up and the copy of a checkpoint between processes; for
rollouts of 15 to 40 minutes each the start-up (under 2 s) does not matter.

The cheap knob that looked like the fix, a 256 MB gen-0 budget under workstation GC (`DOTNET_GCgen0size=10000000`), made
it worse (6.3 and 8.4 Msteps/s at K = 8 and 16): gen-0 count fell 12x but gen-1 collections rose from 2-3 to 419-837.

## Shared state (static audit)

Read from the source at `0ebb0ab` (`68k.fs`, `MMU.fs`, `Instructions.fs`, `Extensions.fs`, `Video.fs`, `Program.fs`,
`server/Server.fs`). Everything inside `type MMU(...)`, `type AtartSt(...)` and the `Cpu` record is per instance
(class `let` bindings and record fields); the list below is everything else that two machines in one process share.
`Instructions.fs` (active patterns), `Extensions.fs`, `CCR`, `ExtendedArith`, `Bcd` and `ImageHash` hold no state:
every `let mutable` in them is a local.

| State | Where | Written per step, trace off? | Can a race change emulated state? |
|---|---|---|---|
| `Trace.enabled` (`let mutable`, starts `true`) | `68k.fs:41` | No. Read at 111 gated sites in `68k.fs` and `Program.fs:719`; written only by `Main.main` (`Program.fs:2145`, under `ATARI_NOTRACE`), `stserver` `main` (`Server.fs:881`) and a script. | No: it gates text only. It is process-wide, so every machine traces or none does. A driver script must clear it itself: `Main.main` is not run when the DLL is `#r`'d, and `ATARI_NOTRACE` is read only in `Main.main` (`Program.fs:2144`), so setting the variable does nothing in a script. |
| `Console.Out` redirect to `TextWriter.Null` | `Program.fs:2146`, `Server.fs:880`, the script | No. Ungated `printfn` remain on rare paths (`68k.fs:937` odd branch target, `68k.fs:1197` invalid size/EA). | No: process-wide sink, thread-safe. |
| `Diag.resultOut` (`let mutable private`) | `68k.fs:31` | No (REPL replies only; set by `captureResultOut`). | No. |
| `Diag.traceGemdos`, `OsCalls.enabled`, `TraceEvents.enabled/path/logAll` (env read once at module init) | `68k.fs:23, 184, 94-96` | Read only. | No; but they are process-wide: one `ATARI_TRACE_*` setting applies to every machine. |
| `TraceEvents.writer`, `sinceFlush` (`let mutable private`, one `BinaryWriter`) | `68k.fs:98-99`, written from `AtartSt.Step` (`Program.fs:789`) | Only with `ATARI_TRACE_EVENTS` set; then every step of every machine. | Not emulated state, but K machines would interleave records into one file through an unsynchronised writer (a corrupt trace, possibly an exception out of `Step`). Off in all runs here. |
| `IllegalEncodings.taken`, `lastMessage`, `report`, `seen` (`HashSet<int>`, unsynchronised) | `68k.fs:57-60`, `note` at `68k.fs:62` called from `Cpu.Step`'s `IllegalEncoding` handler (`68k.fs:1524`) | Only when a decoder raises `IllegalEncoding` (an undecoded encoding taking vector 4): not on the normal path. | Counters and the "first 64 PCs" cap are diagnostics and become process-wide (one machine's PCs use up the others' report quota; `selftest`'s `taken` delta check at `Program.fs:1777` would see other threads' hits). The `HashSet.Add` from two threads at once is undefined: it can throw out of `Cpu.Step` and so end that machine's step. Not exercised by these snapshots (no `ILLEGAL:` line in any log). |
| `OsCalls` name tables (`dict`, read-only) | `68k.fs:235-436` | Read only under `ATARI_TRACE_OS`. | No. |
| `Provenance.dllSha256`, `gitCommit` (`lazy`) | `Program.fs:234-235` | No (`SaveState`/`LoadState`). | No: F# `lazy` is thread-safe. |
| `SelfTest.zeroRom` | `Program.fs:1713` | `selftest` only. | Not on the machine path. |
| Per-instance env reads: `ATARI_TRACE_EVENTS` basepage sidecar, `ATARI_GFX_SIDECAR`, `ATARI_FRAME_DIR`/`EVERY`, `ATARI_TRACE_FDC`, `ATARI_TRACE_IKBD` | `Program.fs:414, 441, 457-461`, `MMU.fs:104, 354` | Read at construction. | No; but the sidecar and frame paths are one path for all machines, so K machines with them set would overwrite one another's files (the constructor even deletes an existing sidecar). |
| ROM bytes | `Program.fs:283` (`IO.File.ReadAllBytes` per `AtartSt`) | Never written. | No sharing at all: each machine reads its own 192 KB copy. Sharing it would save 192 KB per machine, nothing worth a change. |
| `stserver` globals: `machine`, `watches`, `stopRequest`, `breakpoints`, `forks`, `recordings`, `profile` | `Server.fs:124-141, 367` | `watches` hooks fire per matching access; `stopRequest` from a hook. | Single machine by design; see the `stserver` outline below. |

One API hazard that is not a race: a `MachineCheckpoint` (`AtartSt.Capture`, `Program.fs:854`) holds the `Cpu`
record, and the `Cpu` record holds its `MMU` (`68k.fs:769`, `MMU: MMU`). `Restore` assigns it as is
(`Program.fs:857`, `cpu <- c.Cpu`), so restoring machine A's checkpoint into machine B makes B's CPU run on A's MMU
while B's own RAM is overwritten with the checkpoint: cross-talk through the public API. The checkpoint also carries
only the disk journal's length (`MmuSnapshot.DiskLogLength`), not the written sectors, so it rolls back a disk only on
the machine that wrote it (`MMU.fs:2043-2050`). A checkpoint is therefore only portable today as a snapshot file
(`SaveState`/`LoadState`, which carry the written sectors as `DSKA`).

## Equality (dynamic test)

What was run: DLL `scratchpad/insights/parallel/dll/M68000.dll`, a copy of `bin/Debug/net8.0` (sha256
`d11a491e7b66f79a14e9fe79895897f53164a031e1984525207460ef021c1cae`, built 2026-11-12 20:44; its informational version
names commit `b9e2f26`; the core source differs from `0ebb0ab` only in `MMU.fs`'s FDC step-in/out change `62219ec`).
`dotnet fsi` from SDK 10.0.303, so the .NET 10.0.11 runtime, not the 8.0.8 that `dotnet exec` uses. N = 20,000,000 steps
per machine. Snapshots, each with its disk passed to the constructor (`LoadState(snap, false)`, no sidecar remount):

- `pm`: PowerMonger `scratchpad/pm123/win/m1_s0.snap` (sha256 `dc821499...`) + `scratchpad/powermonger.st` (`2099be89...`)
- `pop`: Populous `scratchpad/pop/repro.snap` (`9788b6ca...`) + `scratchpad/pop/pop_auto.st` (`2d139cd4...`)

Machines alternate `pm,pop,pm,pop,...` across threads unless the tag says otherwise, so cross-talk between the two games
would show. Tracing is cleared the way `Main.main` does it (`Trace.enabled <- false`, `Console.SetOut(TextWriter.Null)`);
`ATARI_NOTRACE=1` is also set but has no effect in a script.

Command: from this directory, `python3 driver.py ../../scratchpad/insights/parallel/2026-11-12/eq --n 20000000 --phase
equality`, then `python3 compare.py ../../scratchpad/insights/parallel/2026-11-12/eq` (output `results/eq_compare.txt`).
Every run exited 0 and no log has an `ILLEGAL:` line (the `IllegalEncodings` path was not reached).

| Arm (tag) | GC | Machines matching the reference |
|---|---|---|
| positive control: `ref_pm_a` vs `ref_pm_b`, `ref_pop_a` vs `ref_pop_b` (sequential, one machine, two processes) | ws | identical (`b6202c86...`, `342bd696...`); each differs from its start snapshot |
| `eq_t1`, `eq_t2`, `eq_t4`, `eq_t8`, `eq_t16` (threads, mixed) | ws | 1/1, 2/2, 4/4, 8/8, 16/16 |
| `eq_t16_pm`, `eq_t16_pop` (16 threads, one game) | ws | 16/16, 16/16 |
| `eq_t8_r0` .. `eq_t8_r4` (K = 8 five times) | ws | 8/8 each |
| `eq_seq4` (4 machines one after another on one thread) | ws | 4/4 |
| `eq_srv_t8`, `eq_srv_t16` | server | 8/8, 16/16 |
| negative control `neg_extra_t4` (machine 2 runs N+1 steps) | ws | 3/4: only `neg_extra_t4_02_pm` differs |
| negative control `neg_poke_t4` (machine 1 gets byte `$5a` at `$380` before the run) | ws | 3/4: only `neg_poke_t4_01_pop` differs |

The scaling phase below also compared all of its 351 end states (threads under three GC settings and the separate
processes) with the same references: 351/351 match (`results/scale_compare.txt`). The runs were made with the machine's
load average between 10 and 72 from other sessions, which varies thread interleaving more than an idle machine would.

## Scaling: threads in one process against separate processes

Command: `python3 driver.py ../../scratchpad/insights/parallel/2026-11-12/scale --n 20000000 --rounds 3 --phase
memory,scaling`, then `python3 compare.py ../../scratchpad/insights/parallel/2026-11-12/scale
../../scratchpad/insights/parallel/2026-11-12/eq`. Three rounds; within a round each K runs every arm, in an order reversed
on alternate (round, K). Arms, all with the same mixed assignment and N:

- `threads_ws`: one fsi process, K threads, workstation GC (`DOTNET_gcServer=0`), concurrent GC on (the default).
- `threads_srv`: the same with server GC (`DOTNET_gcServer=1`).
- `threads_ws_g0` (K = 8, 16 only): `threads_ws` with `DOTNET_GCgen0size=10000000` (256 MB).
- `procs_ws`: K fsi processes started at once, one machine each, workstation GC.

`agg` is K x N over the wall time of the stepping loops (for `procs_ws`, the slowest process's loop; the loops start
within the processes' start-up spread, so this slightly flatters processes). `e2e` is K x N over the whole run, process
start to exit, which for `procs_ws` includes K concurrent fsi start-ups (about 2-3 s of compiler each), so it overstates
what real `dotnet exec` processes pay. Medians of three rounds, best (= shortest time) in brackets; gen-0, gen-1 and GC
pause are medians of the per-run sums over all processes of the arm.

| Arm | K | agg Msteps/s | e2e Msteps/s | per machine Msteps/s | gen-0 | gen-1 | GC pause ms |
|---|---|---|---|---|---|---|---|
| procs_ws | 1 | 4.0 (4.5) | 2.7 (2.9) | 4.04 | 729 | 0 | 547 |
| threads_ws | 1 | 3.9 (4.3) | 2.7 (2.8) | 3.95 | 729 | 0 | 924 |
| threads_srv | 1 | 3.4 (3.5) | 2.3 (2.5) | 3.38 | 4 | 1 | 89 |
| procs_ws | 2 | 7.3 (7.7) | 4.7 (5.1) | 3.88 | 1615 | 0 | 1607 |
| threads_ws | 2 | 7.2 (7.3) | 4.9 (5.1) | 3.63 | 1620 | 0 | 1058 |
| threads_srv | 2 | 7.0 (7.6) | 4.8 (5.2) | 3.55 | 45 | 1 | 268 |
| procs_ws | 4 | 14.0 (14.5) | 8.9 (9.1) | 3.89 | 3230 | 0 | 2944 |
| threads_ws | 4 | 12.2 (13.2) | 8.8 (9.3) | 3.08 | 3241 | 1 | 2004 |
| threads_srv | 4 | 14.0 (14.9) | 9.8 (10.4) | 3.54 | 127 | 1 | 571 |
| procs_ws | 8 | 23.9 (23.9) | 13.1 (13.3) | 3.08 | 6460 | 0 | 7869 |
| threads_ws | 8 | 13.0 (13.5) | 10.8 (11.0) | 1.63 | 6483 | 2 | 5966 |
| threads_srv | 8 | 22.3 (22.8) | 16.7 (17.0) | 2.86 | 293 | 1 | 1106 |
| threads_ws_g0 | 8 | 6.3 (6.4) | 5.8 (5.8) | 0.83 | 563 | 419 | 6164 |
| procs_ws | 16 | 25.4 (25.7) | 9.3 (9.6) | 1.63 | 12914 | 16 | 26855 |
| threads_ws | 16 | 15.3 (15.6) | 13.6 (13.8) | 0.96 | 12965 | 3 | 10244 |
| threads_srv | 16 | 25.9 (26.0) | 21.6 (21.7) | 1.64 | 628 | 2 | 3196 |
| threads_ws_g0 | 16 | 8.4 (8.4) | 7.9 (7.9) | 0.56 | 1051 | 837 | 11509 |

Load averages per run are in `results/scale_compare.txt` (1-minute values 9 to 72). The machine has 8 physical cores
(16 logical) and other sessions kept roughly 10 of them busy, so K = 16 is contended in every arm and the K = 16 rates
measure the share of the machine each design gets, not its ceiling. The workstation-threads deficit repeats in every
pair at K = 16 (threads against processes: 9.5/18.0, 15.3/25.7, 15.6/25.4 per round) and in two of three at K = 8
(13.5/23.9, 13.0/23.9); in K = 8 round 0, run at load average 25 to 56, every arm collapsed (threads 4.5, processes 4.8,
server-GC threads 6.4) and the gap was within noise. Gen-0 counts are the mechanism, read off
the data: under workstation GC the in-process gen-0 count is K x 729 (PowerMonger) to K x 885 (Populous), the same total as
K processes, but each collection now stops all K threads at once; with server GC it falls to 628 at K = 16. That the
deficit is the stop-the-world pause and not allocator lock contention is an inference: the pause totals (10 s of a
roughly 21 s loop at K = 16) account for most of it, and no allocation-lock measurement was made.

## Memory per machine

Maximum resident set size from `/usr/bin/time -l` (`results/*_results.jsonl`, `maxrss`; `results/rss_*.txt`):

| Design | Measured | Per machine |
|---|---|---|
| Real emulator process, `ATARI_NOTRACE=1 ATARI_ROM_PATH=<rom> dotnet exec scratchpad/insights/parallel/dll/M68000.dll 2000000 resume m1_s0.snap --disk-a powermonger.st` | 61.1 and 61.3 MB | 61 MB |
| `stserver` copy (`server/bin` copied to `scratchpad/insights/parallel/2026-11-12/rss/srv`, its own `M68000.dll` sha256 `a2dd7af2...`): `load`, `step 2000000`, `fork`, `shutdown` | 63.6 MB | 64 MB |
| fsi process, K machines constructed and loaded, no steps (`mem_k1`, `mem_k16`) | 239 MB, 274 MB | 2.3 MB marginal |
| fsi, K threads stepping, workstation GC (`threads_ws`, max over rounds) | K=1 242 MB, K=16 about 280 MB | 17 MB average at K=16, mostly fsi's own 237 MB |
| fsi, K threads stepping, server GC (`threads_srv`) | about 2,570 MB at K=1; 2,268 to 2,703 MB at K=16 | 161 MB average at K=16 |

So a machine's own state is about 2-3 MB (1 MB RAM, the disk image, ROM, device state) and a process costs about 60 MB
of runtime around it. Workstation-GC threads would save nearly all of that (16 machines in about 100 MB in a lean host
instead of about 1 GB), but run at about 60% of the speed; server-GC threads keep the speed and cost 2.6 GB. Server GC's
footprint can be capped (`GCHeapCount`, `GCConserveMemory`, `GCHeapHardLimit`) and the speed under such a cap was not
measured.

## What `stserver` would need for "run these J forks for N steps in parallel"

Outline only; nothing here is built.

- **A worker pool**: W extra `AtartSt` instances built once with the same ROM and disk as the main machine, each on its
  own dedicated thread (not the thread pool: each job runs for seconds to minutes). `par_run {forks: [ids], n, until_pc?,
  peek?: [{addr, width, count}]}` hands each fork to a free worker, blocks the JSON loop until all finish, and returns per
  fork its end `pc`, `step`, the requested peeks (so a rollout score needs no further round trips) and a new fork id
  holding the end state.
- **Portable checkpoints, one core change**: `AtartSt.Restore` must rebind the CPU to its own MMU,
  `cpu <- { c.Cpu with MMU = mmu }` (`Program.fs:857`), or a worker restoring a fork captured on the main machine runs on
  the main machine's MMU. A one-line change with no effect on the single-machine case (there `c.Cpu.MMU` is already
  `mmu`); it needs the regression net like any core change. Until then a server can do the rebind itself before calling
  `Restore`, since `Cpu` is a public record.
- **Disk state**: a checkpoint restores the disk only on the machine that wrote it (it carries `DiskLogLength`, not the
  sectors). Either refuse `par_run` when the main machine's disk journal is non-empty, or add the written sectors to
  `MachineCheckpoint` (as `SaveState` does for `DSKA`). A rollout that saves a game to disk inside a fork needs the second.
- **Per-worker watches and breakpoints**: `watches`, `stopRequest`, `breakpoints` (`Server.fs:135-138`) are process
  globals whose hook closures append to shared `ResizeArray`s. Either refuse `par_run` while any watch, breakpoint,
  recording or profile is active (the simple first version), or clone each watch per worker and merge events after.
- **Recording**: `record_*` and `replay_to` stay main-machine only; `par_run` refuses while recording.
- **GC setting**: per the measurement above, the server needs `System.GC.Server: true` in its runtimeconfig for
  `par_run` to pay off, with a heap cap if memory matters; with the current workstation default a parallel `par_run` at
  J = 8 would deliver about 13 Msteps/s where 8 processes deliver about 24.
- **Process-wide trace settings** (`ATARI_TRACE_EVENTS`, `_OS`, `_GEMDOS`, `ATARI_GFX_SIDECAR`, `ATARI_FRAME_DIR`) apply to
  all workers and share one file each: refuse `par_run` when any is set.

## Not covered

- The production runtime: fsi runs .NET 10.0.11, `dotnet exec` runs 8.0.8. Both arms here use .NET 10, so the comparison
  is controlled, but the absolute rates are not the production ones.
- An idle machine: every timing ran with other sessions loading 8 to 70 runnable threads.
- Server GC with a heap cap or fewer heaps; `GCgen0size` values other than 256 MB; non-concurrent workstation GC.
- The `IllegalEncodings` race and `ATARI_TRACE_EVENTS` writer race were read from source, not provoked: neither path was
  reached by these snapshots.
- A third game, and N beyond 20M steps per machine.
- The processes arm used fsi processes, not `stserver` or `dotnet exec` ones, so its `e2e` start-up share is fsi's.

## Files

| File | What |
|---|---|
| `par.fsx` | Loads K machines (one per `--assign` name), steps them on K threads (`--mode threads`) or one after another (`--mode seq`), saves each end snapshot, prints one JSON row (stepping time, gen-0/1/2 counts, GC pause, per-thread allocation, RSS). `--extra i=n` and `--poke i=addr=byte` are the negative controls. |
| `driver.py` | Runs every arm through `par.fsx` under `/usr/bin/time -l`, `uptime` before each run, one row per run in `<out>/results.jsonl`. `--phase equality,memory,scaling`. |
| `compare.py` | sha256 of every end snapshot against `ref_<game>_a`, the positive control, and the scaling table. |
| `global.json` | Pins the 10.0.303 SDK for `dotnet fsi`: the DLL references FSharp.Core 10.1, which the 8.0.402 fsi cannot load. |
| `results/` | Copies of the runs' `results.jsonl` and `compare.py` output. Snapshots and logs are in `scratchpad/insights/parallel/2026-11-12/`. |
