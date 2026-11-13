# Render-skip rollouts: the simulation without the renderer

**Question.** The commander's exact rollouts (`../README.md` "Forecaster", `../rollout.py`) cost about 84 s for a
1000-tick lookahead of 177M steps. If the renderer is stubbed in a rollout, does the simulation still reach the same
state at every game tick, and how many fewer instructions does a tick take?

**Answer.** It holds for every stub tried, on three start states, with and without injected orders: the simulation
state at tick 1, 10, 100, 300 and 1000 is byte-identical to the unstubbed run, and so is everything the rollout
scores. The saving is far larger than the 1.5x to 2x expected from the span filler's 40 %: stubbing `$f898` alone cuts
a tick from about 170,000 steps to about 39,000 on the two busy lands (4.2x to 4.5x) and from 230,000 to 25,600 on
the quiet tutorial land (9.0x); stubbing all seven drawing and frame-sync calls gives 6.2x to 6.8x and 19.6x. Wall
time follows the step count: through the rollout's own engine path (the REPL behind `loop.py`'s `Emu`), 1000 ticks
take 40.2 s unstubbed against 8.7 s with `$f898` stubbed and 5.9 s with all seven (land 2, median of 3 interleaved
runs). Nothing in `rollout.py` uses it yet: it counts steps, not ticks (see "Using it").

Checkout at commit `729e138` (scripts and docs read there); the emulators are the installed builds, not built for this
run: `server/bin/Debug/net8.0/stserver.dll` sha256 `1924f4dd976e315f9732cb881285a661fe9b743e401675c71ce80a7eff4721b5`
with its `M68000.dll` `a2dd7af2757557fb99b68cc42161518f0fffe4c27574e4804be3c5d485348e1d`; the REPL runs used
`bin/Debug/net8.0/M68000.dll` `d11a491e7b66f79a14e9fe79895897f53164a031e1984525207460ef021c1cae` (a different build;
both engines reach the same simulation bytes, below). Budgets are game ticks; every run is bounded by a 20M-step
`run` per tick. Bulky data (1 MB RAM dumps at every rung, logs) is in `scratchpad/insights/renderskip/2026-11-12/`;
the per-run rows and summaries are in `results/`.

## What a tick is, and what was stubbed

From the docs, not rediscovered: `strategy.md` "Where it runs" (the `$13000` listing) and "Measured cadence"; `graphics.md`
"The frame pipeline" and "`$f898` — the render entry"; `powermonger.sym` for the original names.

- **A tick** is one pass of `$13000` (`pm_tick`). It increments the sim clock `$2df70` at `$1302e` and the master tick
  `$4bb3e` at `$13034`, then calls the AI block, the four gated renderers (`$1870`, `$12ce0`, `$178ae`, `$f898`, behind the
  `$57ff0`/`$57fee` present-rate counter), then `$1abaa`, `$17878`, `$165b2`, `$14b62`, `$6a3a`, `$7a56`, `$d23a`, `$7202`
  (disassembled `$13058..$13100` from `pm123/win/m1_s0.ram`: the same list). The tick is compute-bound: `$1870` waits for
  one VBL edge, so a cheaper tick is a faster tick ("Measured cadence"), which is why the stub saves steps at all.
- **The rollout counts steps**, not ticks: `rollout.py` pokes action i at step `i*gap` (gap 400,000) and runs `bp d2c8 N`
  for N steps (40M by default; 177M for the quoted 1000 ticks).
- **The harness** (`renderskip.py`) loads a snapshot in `stserver`, pokes the arm, then runs to each arrival at `$13000`
  and reads `$2df70`; tick index k = clock − clock at the first arrival. At each rung it records the cumulative steps and
  dumps all 1 MB of RAM. Every arm runs from the same snapshot with the same inputs; only the pokes differ.

The arms (each an `rts`, `$4e75`, at the routine's entry, applied right after load), named from their own code read to
the first branches:

| arm | stubs | what the body does |
|---|---|---|
| `f898` | `$f898` | `_draw_it`: first-call init of `$ffa2` and `bsr $fec6`; compares the camera cell `$4bb3a/$4bb3c`, yaw `$ff9a` and zoom `$fdec` with its copies `$f890..$f896`, on a change `bchg #7,$ffa5` and `bsr $fec6` (re-project), then the grid walk with the triangle fill and sprites inline |
| `gated` | + `$178ae`, `$12ce0` | `_do_bar`: reads the local side's group block and draws the bars and marker (`jsr $11f82`) into the buffer at `$2df7c`; `_copy_sc`: a 500-row `movem.l` copy from A0 to A1 (the `$e0d4` master into the compose buffer) |
| `draw` | + `$17878`, `$165b2` | `_do_nort`: picks a compass row from `$17ad8` by yaw and blits it (`jsr $122b6`) into `$2df7c`; `_show_pe`: the selected group's lead position and side from its object record, then the minimap dots |
| `drawall` | + `$7a56`, `$1870` | `_draw_re`: sets `$8834` = `$2df7c`+32000 and walks the four `$7a36` requester slots; `_wait_vb`: `tst.w $2df8c / beq / rts`, the VBL wait |
| `divider` | data: `$57fee` = `$57ff0` = `$7fff` | the tick's own present-rate counter: `$1870`, `$12ce0`, `$178ae` and `$f898` run once per 32,767 ticks instead of every tick, and the present flag `$12f58` stays 0, so the post-tick swap `$187a` / `$1a276` at `$13864` does not run either |
| `neg_1abaa` (control) | `$1abaa` | `_seasons`: steps the LCG `$57ff6` 16 times and the season count `$57fec` (`strategy.md` "RNG and determinism") |
| `neg_3e06` (control) | `$3e06` | `_everyti`: armies eat, the `$57fba` group term, animals, pigeons, projectiles |

`$1abaa` (the season LCG) and `$7202` (`_proc_re`: text panels, minimap, compass, captain boxes and the icon floor in
`strategy.md`'s listing, and the player's command path) are not drawing only, and stay in every arm.

## The equality signal

`compare.py` diffs two dumps over the simulation regions, each taken from a doc: lords `$4e514` (160 × 32), settlements
`$4f916` (400 × 18), groups `$51538..$51b66`, objects `$51b66..$57f98`, the globals `$57f98..$58200` (force totals
`$57fba`, ratio `$57fce`, `$57fec`, LCG `$57ff6`, command buffer `$58016`, acting words `$58042`, world seed `$580a0`, peace
bits), the 32-bit seed `$2df84`, the clocks `$2df70`, camera and master tick `$4bb3a..$4bb42`, the per-cell entity heads
`$47970..$4b970` and the terrain colour planes `$418ad..$45930`. The three RNG states (`$57ff6`, `$57fec`, `$2df84`) are
also reported on their own. Everything else that differs is listed as raw ranges, so "equal" is never "nothing looked
at". `forecast_check.py` adds the rollout's own reading: `rollout.summary()` (observation hash, per-side lords, men,
food, groups, and the score) on each dump.

The block `$58058..$58078` is left out of the globals: it is `_channel` (`powermonger.sym`), cleared by `_start_s`
`$126d6` and `_stop_so` `$12726` and used by the sound dispatcher `_do_soun` `$127e6`, the only code that holds the
address (raw scan of the text segment). The dispatcher stamps sound expiry from the VBL counter `$6f304`, which a stub
changes. With the injected orders it differed in 6 of 30 stub comparisons (at k = 10 and 300, never at 1000; for
example `l2o0 drawall k=300`: `$5805b..$58063` all 0 in the base against `01 58 13 .. 2c .. 3f .. 01`); the first pass of `compare.py`,
which counted it as simulation, is kept as `compare_v1_globals_incl_channel.jsonl` beside each ladder's `compare.jsonl`.
No other simulation byte differed in any comparison, before or after that change.

## Results

Steps per tick are the steps from load to the k = 1000 arrival divided by 1000 (machine-independent). Every rung is
k = 1, 10, 100, 300, 1000; "equal" means every simulation region byte-identical to `base_a` at every rung and the
rollout's summary (score, observation hash, per-side totals) the same.

**No orders** (`run_ladder.sh`; `results/ladder_summary.txt`, `results/forecast_ladder.txt`):

| start | base | `f898` | `gated` | `draw` | `drawall` | `divider` |
|---|---|---|---|---|---|---|
| rand1 | 170,179 | 39,145 (4.35x) | 33,300 (5.11x) | 27,111 (6.28x) | 26,291 (6.47x) | 32,930 (5.17x) |
| l2o0 | 173,615 | 38,820 (4.47x) | 33,174 (5.23x) | 27,426 (6.33x) | 26,671 (6.51x) | 32,780 (5.30x) |
| m1s0 | 230,301 | 25,566 (9.01x) | 19,512 (11.80x) | 13,580 (16.96x) | 11,779 (19.55x) | 16,854 (13.66x) |
| simulation state | | equal | equal | equal | equal | equal |

**With orders** (`run_orders.sh`): rand1 with side 3 taken and the attack `$0c` on (15,92) at tick 2 (`gate_inject.sh`'s
order, `actions_rand1.json`); l2o0 with the first four decisions of the `cmd9` rollout run o0 for side 1 (take, posture,
get men, attack, at ticks 0 to 348, `actions_l2o0.json`), poked through `act.from_json` at tick arrivals.
`results/orders_summary.txt`, `results/forecast_orders.txt`:

| start | base | `f898` | `drawall` | `divider` |
|---|---|---|---|---|
| rand1 | 165,421 | 37,048 (4.47x) | 24,472 (6.76x) | 30,821 (5.37x) |
| l2o0 | 160,381 | 38,326 (4.18x) | 26,049 (6.16x) | 32,240 (4.97x) |
| simulation state | | equal | equal | equal |

The orders took effect: against the no-order run the order run's simulation regions differ at k = 10 (rand1: 3 group,
142 object bytes; l2o0: 2 lord, 7 group, 28 object bytes) and at k = 1000 (rand1: 3792 object bytes, l2o0 3088 and a
different `$2df84`). Over the 1000 ticks the unstubbed runs change thousands of simulation bytes (rand1 `base_a` k=1
against k=1000: 5065 object bytes, the season LCG wrapping to a new season, a new `$2df84`), so the equality is not of a
frozen state.

**Controls.**
- (a) Determinism: `base_b` against `base_a`, in all five ladders (three without orders, two with) at all 5 rungs: 0 bytes differ in the whole 1 MB RAM, and the
  same step count (`compare.py .../ladder/rand1/base_a_k1000.ram .../base_b_k1000.ram`: `total differing bytes 0;
  simulation regions EQUAL`, exit 0).
- (b) Wrong stubs are caught at every rung on every snapshot. `neg_1abaa` rand1 k=100: `globals 3 first [('0x57fed', 217,
  116), ('0x57ff6', 29, 20), ('0x57ff7', 112, 192)]`, `rng lcg_57ff6 a=1d70 b=14c0 DIFFER`, `rng season_57fec a=00d9
  b=0074 DIFFER`, exit 1. `neg_3e06` rand1 k=100: lords 5, settlements 39, groups 40, objects 1329, globals 13, seed 4,
  cell heads 228 bytes, `rng seed_2df84 a=6f8211bb b=bda0699f DIFFER`, exit 1; `forecast_check.py` reports its
  observation hash different from k=1. `neg_1abaa` changes no field the rollout scores (its summary is the same):
  the full-region compare catches it, the forecast check alone would not.
- (c) The RNG is in the compared set: `$57ff6` and `$57fec` (in the globals) and `$2df84` (`rng_seed`) are compared and
  printed; control (b) shows each one flagged when it diverges.

**What else differs** (`outside.py`, rand1 k=1000): the two compose buffers `$1c700` and `$24400` (14,022 bytes for
`f898`, 30,870 for `drawall`), the poked entry words, the renderer's own variables (`$f1e2`; `$8836` and `$e3e3` in the
wider arms), the 256 bytes `$1c49e..$1c59d` just below the first buffer (written on the drawing path, not identified),
about 100 stack bytes at `$2c803..$2c94f`, the VBL counters `$6f304`/`$6f308` (base `$012868`, `f898` `$00fdc0`: 10,920
fewer VBLs, which is (170.2M − 39.1M) / 12,000), the timer handler's word `$1af3c`, and for `divider` `$12f58` and the
VBL flag `$2df8c`. None of it reached a simulation region in 1000 ticks, and `observe.py` reads none of it.

**Wall time**, interleaved, one emulator of mine at a time, arm order rotated each round, 1000 ticks, uptime per run in
each row. The machine was shared with other sessions; load averages (1 min) per run are in the rows.

Through the rollout's engine path, the REPL (`repl_ab.py`: `Emu`, the arm as a REPL `w`, `bp d2c8 <steps>` for the arm's
k=1000 step count; `results/repl_ab.jsonl`):

| start | base median (min) | `f898` median (min) | `drawall` median (min) | base/`f898` per round | base/`drawall` per round | load1 |
|---|---|---|---|---|---|---|
| rand1 | 40.38 s (39.11) | 8.89 s (8.87) | 5.84 s (5.82) | 2.65, 4.55, 4.40 | 4.26, 6.91, 6.72 | 19 to 33 in round 1, 3.5 to 5.4 after |
| l2o0 | 40.16 s (40.05) | 8.69 s (8.67) | 5.90 s (5.88) | 4.43, 4.62, 4.62 | 6.86, 6.81, 6.72 | 3.7 to 17.8 |
| m1s0 | 50.48 s (50.13) | 5.33 s (5.31) | 2.50 s (2.50) | 9.45, 9.43, 9.58 | 20.22, 20.03, 19.84 | 3.5 to 9.3 |

Round 1 on rand1 ran under load 19 to 33 and is the outlier. The REPL runs' end states match the `stserver` dumps at
k = 1000 in every simulation region (0 differing bytes, all 9 round-1 runs), so the two builds agree. Per-step speed is
about the same in every arm (4.2 to 4.8M steps/s at low load), so the wall-time gain is the step-count gain, slightly
more.

Through `stserver` (`run_timing.sh`, also arm `gated`; `results/timing_summary.txt`), under heavier load (8.6 to 68.7):
l2o0 base 43.80 s median (41.23 min), `f898` 9.61 (9.44), `gated` 7.93 (7.72), `drawall` 6.93 (6.19); m1s0 base 60.14
(58.78), `f898` 7.19 (6.70), `drawall` 3.20 (3.07); rand1's rounds were the noisiest (base/`gated` 4.49, 1.62, 9.61 at
loads 24, 66, 21). Use the step counts and the REPL table, not these.

## What the data covers, and what it does not

Measured: three start states (rand1, Play Random Land settled 30M steps, 4 lords, a season change inside the window;
l2o0, campaign land 2 at the start of the `cmd9` seed runs; m1s0, campaign land 0, the quiet tutorial land), 1000 ticks
from each, no input and two order scripts poked at tick arrivals, in the iso view each snapshot was saved in.

Not covered:
- A camera that moves, rotates or zooms during the rollout. The stub also skips `$f898`'s re-projection `$fec6`; no
  simulation routine was seen to need it here, but the camera was still in all runs.
- Mouse input or open dialogs. The player's click on the map goes through screen-space hit tests that may read what the
  renderer leaves behind. The commander pokes `$58016` and does not click, so its rollouts do not depend on this.
- Past a land end. `$b306..$b322` (inside `click_pr` `$b2d4`, the land set-up and briefing entry in `powermonger.sym`) adds the VBL counter `$6f304` and the
  video counter `$ff8205` into the world seed `$580a0`, and a stub changes `$6f304`, so a stubbed run that went on into
  a new land's build would build a different land. A rollout stops at `$d2c8`, the verdict, before that.
- Horizons beyond 1000 ticks, other lands, the serial link, and orders poked mid-tick at a step count rather than at a
  tick arrival (as `rollout.py` does now).

## Using it

`rollout.py` was not changed. To use the stub it would have to:
- poke `$f898` (or the seven `drawall` entries) to `$4e75` after `resume`, as `repl_ab.py` does through `Emu`;
- count ticks, not steps: a stubbed 40M steps is about 1000 ticks rather than 230, so N and `gap` become tick counts
  (stop on the `$13000` arrival with `$2df70` = start + N, as `renderskip.py` does, or `bp` that address per tick);
- keep scoring from the RAM: the screen in a stubbed rollout's end snapshot is stale.

On land 2, a 1000-tick lookahead then costs about 8.7 s (`f898`) or 5.9 s (`drawall`) against 40.2 s here (all
measured by `repl_ab.py` on this machine; the 84 s in `../README.md` was measured at 2.1M steps/s on a loaded machine). The safest arm is `f898`: one routine, and the largest share of the gain. `drawall` adds about 1.5x more on the
busy lands, but it also skips the VBL wait, so a tick no longer lines up with a VBL; the data shows no effect on the
simulation, but it is the arm furthest from the shipped program.

## Files and commands

All from `M68000/`, with `ATARI_NOTRACE=1` set by the scripts; output under `scratchpad/insights/renderskip/2026-11-12/`.

| file | does | command for the numbers above |
|---|---|---|
| `renderskip.py` | one arm from one snapshot to tick rungs in `stserver`: steps, wall, RAM dumps; `--actions` pokes orders at tick arrivals | `uv run python reversing/powermonger/commander/renderskip/renderskip.py run <snap> <arm> <outdir> --rungs 1,10,100,300,1000 --dump` |
| `compare.py` | simulation-region diff of two dumps, RNG fields, the rest as ranges; exit 1 when a simulation region differs | `python3 .../compare.py <base_a_kN.ram> <arm_kN.ram> [--ignore 57fee:4 for divider]` |
| `outside.py` | the non-simulation differences attributed to buffers, stack and counters | `python3 .../outside.py <a.ram> <b.ram>` |
| `forecast_check.py` | `rollout.summary()` per dump against `base_a` | `uv run python .../forecast_check.py scratchpad/insights/renderskip/2026-11-12/ladder 1` |
| `run_ladder.sh` | the no-order ladder: 3 snapshots × (base twice, 5 arms to k = 1000, 2 controls to k = 100), 4 at a time, then `compare.py` | `bash .../run_ladder.sh scratchpad/insights/renderskip/2026-11-12/ladder` |
| `run_orders.sh` | the ladder with `actions_rand1.json` / `actions_l2o0.json` | `bash .../run_orders.sh scratchpad/insights/renderskip/2026-11-12/orders` |
| `recompare.sh` | re-runs `compare.py` over a finished ladder | `bash .../recompare.sh <ladder_dir> rand1 l2o0 m1s0` |
| `run_timing.sh` | interleaved `stserver` wall-time runs, 3 rounds, 1000 ticks | `bash .../run_timing.sh scratchpad/insights/renderskip/2026-11-12/timing 3 1000` |
| `repl_ab.py` | interleaved wall-time runs through `loop.py`'s `Emu` (the rollout's path), with the cross-engine state check | `uv run python .../repl_ab.py scratchpad/insights/renderskip/2026-11-12/ladder scratchpad/insights/renderskip/2026-11-12/repl 3` |
| `summarise.py` | the tables in `results/*_summary.txt` | `uv run python .../summarise.py ladder <dir>` / `timing <dir>` |
