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
- **First experiment.** The argv error and the sidecar only; `gates.py run all` stays 49/49 and
  `regress_net.sh` identical.

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
  Reads go through a cache: uncached `stserver` reads made the fight about 3x slower.

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
- **Exists.** `hits` on named addresses; read watches. Coverage as a set is `sessions/emulator.md` Open 3.
- **Cost.** Medium. A per-instruction hook on the hot path, behind a null test like the memory hooks;
  needs an interleaved A/B with no hook set (falsifier: slower by more than 3% in every pair).
- **First experiment.** Rediscover blind Black Tiger's `$85` plus ClrHome flag `$17826` and
  Impossamole's `LUMBAJAK`; measure the rank of the real compare.

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

## Unmeasured

Skipping VBL waits that are provably idle (generalising `TryFastForwardTbdrPoll`) could speed up
search-heavy games. PowerMonger is fill-rate bound, so its gain would be small; Impossamole's and
Cadaver's share of time in waits is unknown. Measure with `hits` on their wait loops (Impossamole
`$1ab8a`, `$1c686`) before building anything.
