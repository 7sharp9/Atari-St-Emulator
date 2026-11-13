# Tooling ideas for the emulator and its harness

Ideas for what to add to the emulator, `stserver` and the Python tooling, ranked by payoff over cost.
Nothing here is built or measured unless it says so. Each idea names the trap or slow loop it would
remove (with the file or commit that records it), the nearest tool that exists today, its cost, and
the smallest experiment that would show whether it pays. Game-AI ideas live in `reversing/ideas.md`;
work that starts from one of these moves into `sessions/emulator.md`.

The common thread: the largest cost in this project is not missing analysis power but sessions
driving games by hand and rebuilding state that broke. Ideas 1 to 4 are cheap and each removes a
trap recorded more than once. Ideas 5, 7 and 8 pay only once the driver library (2) and the memory
schema (4) exist.

## 1. Snapshot provenance and argv that cannot fall through

Every `snap`/`save` also writes `<snap>.prov.json`: the DLL's content hash and git commit, the
mounted disk's path and FNV hash, and the parent snapshot. `load`/`resume` warn on a build mismatch
and remount the recorded disk when `--disk-a` is missing and the hash matches. An argv that matches
no pattern exits with an error instead of booting into the REPL.

- **Evidence.** `ce1532e` (every cmd14 arm ran on the pre-merge build: `bin/`'s mtime is the compile
  time); `4026cfd` (Cadaver snapshots from builds `5636dc5..4e10c03` carry a phantom key);
  `sessions/emulator.md` "Known traps" ("tie every result to the DLL actually run"); CLAUDE.md
  "Running" (`resume` without `--disk-a`; a `run.ps1` alias passed to the raw binary). The fall-through
  is the final `| args ->` arm of `Program.fs` (about line 2033): it resets, runs 20,000 steps inside
  `try ... with _ -> ()` and enters the REPL. `tools/gates.py` records no DLL hash.
- **Exists.** The snapshot's `DSKA` section stores an image hash, only when the run wrote to the disk
  (DEVELOPING.md, "Snapshot / preview fidelity").
- **Cost.** Hours. No hot path. A sidecar rather than a snapshot section, because a build hash inside
  the `.snap` would make every cross-build `cmp` in `regress_net.sh` and the gates differ. The argv
  change is an interface change: scripts that pass odd argv need checking.
- **Built** (`Provenance` in `Program.fs`; DEVELOPING.md, Disk A and provenance paragraphs). Net
  identical against the base build and `gates.py run all` 49/49; a resume without `--disk-a`
  remounts the recorded disk, and a raw alias argv exits 2. `gates.py` still records no DLL hash
  (`sessions/emulator.md` Open 4).

## 2. One driver library over `stserver` with the evidence rules as defaults

A `tools/stdrive.py` over `stclient.py`: `hold(input, polls=k)` and `tap()` aligned to VBL boundaries
with the poll period as a parameter; `wait_until(addr, value, mask, budget)` on stop watches;
`ab(input, budget)`, which always runs the same-snapshot, same-budget control on a fork and returns
both; and an always-on journal so every drive replays. Per-game wrappers shrink to a field map.

- **Evidence.** 19 files under `reversing/` define their own `Repl`/`Repl2`/`ReplErr`/`Driver`/`Emu`
  class, most spawning `resume <snap> repl` with a `hits 0 fb98` end-of-reply sentinel; 16 use
  `stclient`. `sessions/impossamole.md` "Known traps": the boss `Repl` does not record. CLAUDE.md
  "Evidence rules" requires the control, the hold length and the poll cycle, and each script
  re-implements them.
- **Exists.** `stserver` has stop watches with value and mask, `fork`/`restore` and recordings;
  `stclient.py` is a thin `call()` wrapper. The gap is the client layer.
- **Cost.** One to two days; per-game migration optional. No emulator change.
- **Built** (`tools/stdrive.py`, self-check `tools/stdrive_check.py`). Proof: Impossamole's boss
  fight ported as `py/boss/boss_stdrive.py` (the 700,000-delay kill comes from `boss_dodge139.py`,
  a subclass of `boss_unpoked.py`'s fight; `--policy unpoked` reproduces the parent). The port's end
  snapshot is byte-identical to `pass108/boss/kill_d700000_end.snap`, its journal replays to the
  same bytes, and one fight takes about 8 s for both the original and the port (5 interleaved rounds).
  Reads go through a cache: uncached, the fight takes about twice as long (24 to 29 s against 13 to 16 s,
  three interleaved pairs; it was 50 to 54 s before `read` hexed its buffer in one call instead of a
  `sprintf` per byte, which made a 64 KB read about 13x faster). With
  `record=<dir>` a drive also leaves on-disk recording segments that `provenance.py --recording`
  slices after it ends (`tools/stdrive_record_check.py`, 5/5).

## 3. Backward slice: where a byte came from

`provenance(addr, step)` repeats one move until it reaches an input, a DMA sector, an immediate or the
base snapshot: `last_writer`, decode the writing instruction, compute its source from the registers
at `replay_to(step-1)`, and for a register source find the last step that changed that register (a new
server method that replays the interval comparing one register per step). Output: a chain of (step,
PC, instruction, value), each link found by replay.

- **Evidence.** CLAUDE.md: a dataflow chain is a hypothesis until each leg is driven. "Who writes X"
  censuses (PowerMonger's `$2452`/`$245c` case, the skill's "name a field from its writers") are done
  one hop at a time by hand.
- **Exists.** `last_writer`, one hop, 20/20 in `server/last_writer_proof.py`.
- **Cost.** Medium: one server method plus operand decoding reusing `tools/disassemble.py`. Replay
  only, no hot path.
- **Built** (`stserver` `last_reg_change`, `tools/provenance.py`). `server/last_reg_change_proof.py`
  412/412 against a per-step brute force (251/412 with the backward search removed);
  `server/provenance_proof.py` 178/178 links against REPL `watch` and `bp`, with a `set_reg` and a
  poke control each reaching "input". Value rules are scored against the REPL only for `move`,
  `addi`, `sub`, `subi`, `lea` and `adda`; `Scc`, `addx`/`subx`, `roxl`/`roxr`, `movep`, BCD and
  `rte`/`trap` stop with a reason.

## 4. A memory schema per game, and a semantic snapshot diff

`reversing/<game>/layout.toml`: globals, arrays (base, stride, count) and fields with widths and names.
Consumers: a snapshot differ that prints "slot 7 hp 12 -> 0, hero x 29 -> 41" instead of raw bytes,
named `first_divergence` output, the drivers of idea 2, and agent briefs.

- **Evidence.** Layouts live in `.sym` files (addresses only), `pm_common.py` and each driver's
  decoders (Impossamole `boss/repl.py` hard-codes `$1a2ea`, stride `$6c`). The skill, section 3c: a
  brief with the object table wrong made every agent correct it. `first_divergence` returns raw bytes.
- **Exists.** `.sym`, `tools/doc_addrs.py --check`, `pm_common.py`; `tools/gfxview.py` parses the
  `.snap` header. No struct layer.
- **Cost.** Small, Python only.
- **Built** (`tools/layout.py`, `tools/snapdiff.py`, `reversing/{cadaver,impossamole}/layout.toml`,
  format in DEVELOPING.md "Memory layouts and the semantic snapshot diff"). Cadaver's `kbd ff 08`
  names hero x 29 -> 41 and the same-budget control names no field
  (`reversing/cadaver/py/snapdiff_proof.sh`); Impossamole's slots decode 39/39 against
  `boss/repl.py` (`py/boss/layout_crosscheck.py`).

## 5. Differential execution profiles: coverage and comparison log

Behind a null-checked hook, record over a window the set of executed PCs and every compare-class
instruction (`cmp`/`cmpi`/`cmpm`/`tst`, `sub` then branch) with both operands. Run with an input and
the same-budget control from one fork, and diff. The coverage diff gives the code only that input
runs; the compare log ranks compares whose operand equals the injected scancode, its ASCII, or a table
entry (Redqueen's input-to-state correspondence). Unconventional.

- **Evidence.** The skill, section 2, prescribes a manual census of comparisons after the key-read
  service. Black Tiger's level skip (`black_tiger/secrets.md`), Impossamole's cheat names, Populous's
  F6/F7 hooks (`30cb24f`) and the Lemmings secrets hunt (`81e2ed5`) were each found by reading consumers.
- **Exists.** `hits` on named addresses; read watches.
- **Cost.** Medium. Built in `stserver`'s own step loops, so the core's `AtartSt.Step` is unchanged and
  the cost with no profile is one option test per server step.
- **Built** (`stserver` `profile_start`/`profile_stop`, `tools/profdiff.py`; DEVELOPING.md "Execution
  profile"). Blind ranks: Black Tiger's level skip puts `cmp.b #$47` (`$c6c8`) first and `cmp.b #$85`
  (`$c6d6`) second, and its coverage diff names the flag-setting block `$c6b8..$c6e6`
  (`server/profile_proof.py`, 5/5); Impossamole's `LUMBAJAK` puts the two `cmp.l` halves of the name
  compare (`$18358`, `$18364`) first and second with `--text`, and no byte value finds them
  (`reversing/impossamole/py/secrets/cheat_profile.py`). Every compare's operands are checked against
  the flags the instruction left: 0 mismatches in 245,325 checks (`profile_proof.py`) and 1,285,839
  (`cheat_profile.py`), 329 in the input run with a deliberately misread `cmpi.b` immediate. `sub` then branch is not logged. Not done: the PowerMonger control planned for coverage, a
  handler reached only through a longword table that `rdis.py` misses. PowerMonger's image has no
  `jsr (An)` table (the one `jmp (A0)`, `$12d34`, is the long-multiply return), and the one table form
  `rdis.py` does not resolve, `lea $11886,A1 / jsr 0(A1,D2.w)` at `$11970` (`a_worksh`'s goods icons,
  `graphics.md`), did not run in 3M steps from `pre_pick.snap`.

## 6. Cross-game routine fingerprints

Hash every named routine in every `.sym` with absolute operands and relocations masked, then scan a
new game's snapshot and propose names for shared routines (packers, IKBD handlers, crack menus,
Bullfrog engine code).

- **Evidence.** The `LSD!` depacker exists twice: `reversing/impossamole/py/secrets/lsd.py` and
  `tools/lsd_depack.py` (Midwinter). Populous and PowerMonger are both Bullfrog; the Replicants and
  Empire cracks recur. `doc_addrs.py` matches address text, not code.
- **Cost.** Small. Payoff speculative: how much code Bullfrog shared is unmeasured.
- **First experiment.** Fingerprint `populous.sym`, scan a PowerMonger snapshot; positive control is
  Impossamole's `LSD!` hook (`$242..$3c2`) found in Midwinter's menu. Read each match's body.

## 7. Go-Explore over forks in place of hand-written bots

An archive of `fork` checkpoints keyed by a coarse cell from the schema (room, x/16, health, item
bits); repeated expansion of promising cells with macro-actions (input held for k polls); several
`stserver` processes; output a journal that replays byte-identically. Unconventional for a
reversing harness.

- **Evidence.** Impossamole's start room is bound by a health budget, boss reliability comes from
  delay sweeps, and each segment needs a wait-point search (`sessions/impossamole.md`). Cadaver's
  routes are 29- to 42-leg hand scripts. Commander rollouts spawn one process per candidate
  (`sessions/commander.md`).
- **Exists.** `fork`/`restore` at about 1 MB per checkpoint (DEVELOPING.md "Record and replay").
- **Cost.** Medium; recording spill to disk (`sessions/emulator.md` Open 1) first, for memory.
- **First experiment.** From `pass108/nohop/BEST/seg3_pit_a.snap` (wx 692, health 12), the same
  wall time as one hand pass; furthest wx at each health level against `route_hop1_2.py`. Falsifier:
  no better than the hand route.

## 8. Routes as postcondition-checked legs that repair themselves

Each leg stores its input and a RAM postcondition (room, position band, item held). On replay after
an emulator change, a failing leg triggers a bounded local search (timing shifts of k frames, tap
counts plus or minus 1), and the rebuilt chain is checked with `cmp` twice.

- **Evidence.** `sessions/cadaver.md` Open 1: under `send_joy`, `route_pocket.py` leg 25 ends at 30,
  not 28, and the s95 lineage does not rebuild. CLAUDE.md: Crude Buster's `natbot.lua` lost the
  versions that worked.
- **Cost.** Small once 2 and 4 exist.
- **First experiment.** Postconditions on `route_pocket.py` legs 1-33; the repairer fixes leg 25;
  legs 25-33 plus `route_pocket2.py` replay twice with every snapshot equal.

## 9. Bind fields to the game's own UI text

For a game's string-draw and number-format routines, log every string drawn and, through read
watches with a PC range during the draw, the RAM addresses the printed numbers came from: a table
such as "Food: <- group+36" for every panel. Unconventional.

- **Evidence.** The rule "name a field from the game's own UI text" and its cases: PowerMonger's
  lord `+6` and group `+112` were misread until the captain panel `$921a` said "Food:".
- **Exists.** Read watches with `pc_lo`/`pc_hi` in `stserver`.
- **First experiment.** PowerMonger's captain panel: reproduce the "Food:" to group `+36` binding
  with no hint beyond `$921a`.

## 10. Infer structures from access patterns

A server-side histogram of writes per (PC, address) over a run; clustering by writer PC and
autocorrelating addresses yields array bases, strides and per-field writers, a draft for idea 4's
schema. Unconventional (the Howard/REWARDS line of data-structure inference).

- **Exists.** `find_field_writers.py` (static, one field), `sprite_array_export.py` (stride by hand).
- **First experiment.** Recover Impossamole's slot array (`$1a2ea`, stride `$6c`) and projectile
  slots (`$1a9aa`) from an unlabelled 2M-step run.

## 11. Timing-sensitivity harness

Builds with `instructionsPerFrame` and the HBL divisor moved a few percent (literals, so one `-o`
build per value), run through the gates and key routes, label each documented result robust or a
product of the 12,000-step frame model. Unconventional.

- **Evidence.** No cycle counting (DEVELOPING.md); the MAME comparison's three model gaps; an
  Impossamole lineage that never populated a sprite bank that different key timing did (skill,
  section 5).
- **Cost.** Small to build, large to run.
- **First experiment.** Variants at 11,400 and 12,600 through `gates.py run all`; report which gates move.

## 12. A lifter that writes Python transliterations as callcap references

A mechanical Python transliteration of a routine (registers, flags, memory as a dict) from the
disassembler's decode, passing its callcap gate from day one, then refactored toward readable code
under that gate. Unconventional.

- **Evidence.** Hand-written assembly games (Impossamole, Cadaver) get no Ghidra help; `lsd.py` was
  transcribed instruction by instruction; an "equivalent" two-lerp put one sprite in ten a pixel off
  (skill, section 4b).
- **Cost.** Medium to high. A lifter that copies a decoder bug passes falsely, so the control must
  come from the emulator.
- **First experiment.** Lift the `LSD!` hook `$242..$3c2`; byte-identical output on the files
  `lsd.py` handles.

## Not worth doing

- **Cycle accuracy, blitter, STE.** No game here needs them; the visible costs are Super Sprint's
  raster split wobbling a band (README "MFP Timer B raster split") and one menu layout. Idea 11 answers
  the real question, whether findings depend on the timing model.
- **A dynarec or JIT.** DEVELOPING.md "Performance" puts the remaining cost in allocation from the
  immutable `Cpu` record, not decode; the mutable `Cpu` is the next speed step. For search workloads,
  avoiding re-runs (7, 8) is worth more.
- **A gdb stub with reverse execution.** The users are headless agents and `replay_to`/`last_writer`
  already give time travel.
- **Lockstep co-simulation of the PowerMonger port.** The port has no entity simulation yet.
- **Many machines on threads in one process.** Safe with tracing off (every end state byte-identical to
  the single-thread reference), but under the default workstation GC 8 threads give 13.0M steps/s where
  8 processes give 23.9M, because each gen-0 collection stops every thread; server GC matches processes
  at about 2.5 GB resident against about 1 GB for 16 processes (`server/parallel/README.md`, measured
  through `fsi` on .NET 10). A process costs about 60 MB and under 2 s to start, so there is little to
  save. Two defects to fix first if it is ever built: `AtartSt.Restore` assigns the checkpoint's `Cpu`
  record with the MMU of the machine that captured it, and `IllegalEncodings` shares an unsynchronised
  `HashSet`.

## Measured elsewhere

- **Rollouts without drawing.** PowerMonger's simulation is byte-identical with the renderer stubbed and
  a tick costs 4.2x to 19.6x fewer steps (`reversing/powermonger/commander/renderskip/README.md`).
- **Snapshots as build products.** `tools/recipe.py` rebuilds a Carrier Command chain from a cold boot
  byte for byte (DEVELOPING.md "Snapshot recipes"). Open: inputs gated on game conditions, so a recipe
  survives an emulator timing change, which is also what idea 8 needs.
- **Documented counts without a gate.** `tools/doc_gates.py all`: 283 gated, 1,075 scripted and ungated,
  834 with no script, over 12 games; seven games have no manifest.

## Unmeasured

Skipping VBL waits that are provably idle (generalising `TryFastForwardTbdrPoll`) could speed up
search-heavy games. PowerMonger is fill-rate bound, so its gain would be small; Impossamole's and
Cadaver's share of time in waits is unknown. Measure with `hits` on their wait loops (Impossamole
`$1ab8a`, `$1c686`) before building anything.
