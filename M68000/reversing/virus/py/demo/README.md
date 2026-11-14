# reversing/virus/py/demo: the demo-mode experiments

Method and findings: `reversing/virus/demo.md`. Run from `M68000/`. Data (snapshots, logs) is not committed: it lives in
`scratchpad/virus/demo/` (`VIRUS_WORK` overrides `scratchpad/virus`). Every script finds the repo root by walking up to
`tools/rdis.py`; snapshot arguments are paths relative to `M68000/`. One emulator process at a time.

Build the captures once (about 6 minutes), after `bash reversing/virus/drive.sh`:

```
bash reversing/virus/py/demo/capture.sh        # writes scratchpad/virus/demo/ (S1b, fl/, c1/, ctl/)
bash reversing/virus/py/demo/gate_demo.sh      # the five checks below, each with its control (about 8 minutes)
```

| Script | What it does | Command |
|---|---|---|
| `drv.py` | REPL driver: `run(snap, cmds)` returns stdout lines, `mem(lines)` parses `m` rows (a library) | imported |
| `capture.sh` | builds the demo snapshots: flight 1 `S1b`, later flights `fl/`, the two restart-path scatter stops, a human game idled then a demo | see above |
| `gate_demo.sh` | prints the gate lines below with controls | see above |
| `traj.py` | samples tick, ship position and velocity, flag every N steps; apply REPL pokes first | `uv run python reversing/virus/py/demo/traj.py <snap> <n> <step> ["w 2706e d193a672" ...]` |
| `measure.py` | HUD measures (score, lives, rockets, wave, fuel, position) at ticks 200, 400, 700, 1000 and life losses | `uv run python reversing/virus/py/demo/measure.py <snap>...` |
| `flights.py` | chain of attract flights by ESC, natural and with the RNG seed poked at the scatter | `uv run python reversing/virus/py/demo/flights.py <S1b.snap> <outdir> 3 20000000` |
| `bisect2.py` | delta-debugs the bytes that make two scatter-stop snapshots produce the same object map | `uv run python reversing/virus/py/demo/bisect2.py <good.snap> <bad.snap>` |
| `bisect.py` | the same over a trajectory: bytes copied from a good start state into a bad one until its flight matches (slow, not in the gate) | `uv run python reversing/virus/py/demo/bisect.py <good.snap> <bad.snap> 400 70000 10` |
| `memdiff.py` | RAM diff of two snapshots over a range | `uv run python reversing/virus/py/demo/memdiff.py <a.snap> <b.snap> 400 70000` |
| `classify.py` | RAM diff of two snapshots with each differing byte assigned to a named region (RNG, pilot state, selectors, score block, pool, object map, stack, code, variables) | `uv run python reversing/virus/py/demo/classify.py <a.snap> <b.snap>` |
| `deaths.py` | flies a demo with a breakpoint on the life decrement `$25ba0` in 100M-step chunks and prints lives, wave, tick, score, fuel after each | `uv run python reversing/virus/py/demo/deaths.py <snap> 9` |
| `capture_death.sh` | builds the natural-game-over snapshots under `scratchpad/virus/demo/death/` (`long7`, `nB`, `N1`, `E1`, `N1z`), about 3 minutes | `bash reversing/virus/py/demo/capture_death.sh` |
| `gate_death.sh` | the natural-death gates below (about 14 minutes) | `bash reversing/virus/py/demo/gate_death.sh` |
| `chain.py` | an unpoked chain of complete games from a demo start: life-loss ticks, game-over tick, score and wave, start RNG, the `$27134` table and the high-score table per game (one REPL session, about 3 minutes a game) | `uv run python reversing/virus/py/demo/chain.py scratchpad/virus/demo/S1b.snap 6 scratchpad/virus/demo/chain/chain.jsonl` |
| `chain_table.py` | prints the per-game table and the rank correlations | `uv run python reversing/virus/py/demo/chain_table.py` |
| `queue_check.sh` | the infection target queue: first reader, held-queue watch with positive control | `bash reversing/virus/py/demo/queue_check.sh` |
| `sample.py` | long-run sampler (tick, ship, flag, score) every N steps | `uv run python reversing/virus/py/demo/sample.py <snap> <n> <step>` |

## Gate lines

Raw output of `gate_demo.sh` (each result is followed by its control):

```
== timer: writers of $62a5f from the press page, no key (12M steps)
   1 WATCH: pc=$024d14 WriteByte $00062a5f <- $ff
-- control: SPACE held on the press page (a human game): the writer must be the key branch, value 0
  34 WATCH: pc=$024cfc WriteByte $00062a5f <- $0
== bisect2: minimal set making the two scatter stops agree (B from c1 vs A from fl)
bad as is: map equals good's: False                       <- control: no poke, the maps differ
all ranges poked: True
minimal: 1 ranges 2 bytes
  $06fffe..$06ffff good=30ac bad=5bee
== measure: flight 1 and the seed-poked later flights (control: they must differ from flight 1, equal each other)
Sp2 == Sp3 == Sp4 on every measure line: True (3 lines each)
control, flight 1 == Sp2: False
flight 1: T400: tick=400 score=84 lives=3 rockets=3 wave=0 fuel=3001 pos=(22919,65120,15938)
Sp2     : T400: tick=400 score=0 lives=3 rockets=3 wave=0 fuel=3050 pos=(12484,63049,37116)
== flight 1 vs a demo after an idled human game (seed poked at scatter B), 100 samples of 200k steps
flight 1 vs after-human-game demo: 100/100
control, flight 1 vs flight with the seed poked at scatter A (Sp2): 5/100
```

The 34 control lines are the key branch writing 0 once per loop pass while the key is held. In the bisect2 gate `good` is the
snapshot stopped at scatter B (`jsr $2336a` at `$230a6`, stack word `$30ac`) and `bad` the one stopped at scatter A (`$25be8`,
`$5bee`); both are given the seed by poke before running to `$230c0`. The measure table for flights 1 to 4 with natural RNG (from
`measure.py`, ticks 200/400/700, score): flight 1 0/84/116, flight 2 0/0/176, flight 3 0/82/82, flight 4 0/-5/8; lives 3 and
rockets 3 in all. These four were measured from `S1b` and `fl/S2..S4` (`py measure.py scratchpad/virus/demo/fl/S2.snap ...`).

## Natural death and game over (`gate_death.sh` after `capture_death.sh`)

```
== the natural game over reaches scatter A and B (stack words 5bee then 30ac) from the last life
00 01
--- breakpoint $000236f8 hit (1/1) after 133333 step(s) ---
5b ee
--- breakpoint $000230a6 hit (1/1) after 37709385 step(s) ---
--- breakpoint $000230c0 hit (1/1) after 12155999 step(s) ---
ff
== trajectories, 500 samples of 200,000 steps (100M steps), same seed poke at scatter B
flight 1 vs E1 (after an ESC): 500/500  first differing sample: None
flight 1 vs N1 (after a natural game over): 205/500  first differing sample: 110
flight 1 vs N1z (after a natural game over, 4 stale bytes zeroed (poke)): 500/500  first differing sample: None
== the four bytes: bisect.py E1 vs N1 over $27134..$271e3 (control: N1 as is differs)
bad as is matches good: False
all ranges poked matches good: True
minimal ranges: 4 bytes 4
  $027139..$027139 good=0000000000000000 bad=d9515d03e07cd94d
  $02713a..$02713a good=0000000000000000 bad=515d03e07cd94d15
  $027144..$027144 good=0000000000000000 bad=810e4cf203d88125
  $027147..$027147 good=0000000000fb5909 bad=f203d88125fb3209
== RAM diff classes, first demo start vs the one after the natural game over
   16988  variables $27000..$31d53   (first $02707b)
     308  pool $31d54..$32a2d   (first $031db8)
     150  code and tables $c000..$26fff   (first $017b4d)
      17  low RAM and TOS $400..$bfff   (first $000464)
      17  ship $270b0..$270d3   (first $0270b0)
      13  game words $32a2e..$32a57   (first $032a32)
      10  pilot state $270a2..$270af   (first $0270a2)
       6  score block $2708e..$270a0   (first $027090)
       5  stack $6e000..$6ffff   (first $06ff92)
       2  selectors $62a5b..$62a70   (first $062a5e)
total 17516 of 457728
== life-loss tables (chunks of 100M steps; life_loss=yes is a stop on the life decrement)
chunk 1: pc=0001acd6 life_loss=no lives=3 wave=1 tick=1793 score=1739 fuel=2783
chunk 2: pc=0002477a life_loss=no lives=3 wave=1 tick=4026 score=3966 fuel=47
chunk 3: pc=00025ba0 life_loss=yes lives=3 wave=1 tick=4186 score=3966 fuel=0
chunk 4: pc=0001a864 life_loss=no lives=3 wave=2 tick=6364 score=7266 fuel=1720
chunk 5: pc=00025ba0 life_loss=yes lives=3 wave=2 tick=7744 score=9809 fuel=0
chunk 6: pc=00026446 life_loss=no lives=3 wave=3 tick=9367 score=10868 fuel=3398
chunk 7: pc=00025ba0 life_loss=yes lives=3 wave=3 tick=10656 score=12830 fuel=0
chunk 8: pc=00025ba0 life_loss=yes lives=3 wave=3 tick=10812 score=15078 fuel=0
chunk 9: pc=00025ba0 life_loss=yes lives=2 wave=3 tick=11205 score=16038 fuel=0
game 2 (after the game over, 4 bytes zeroed) equals game 1 on lives, wave, tick, score, fuel at every chunk:
identical 9/9
```

Controls are in the lines: `N1` as is against `N1z` (the four bytes cleared: 205/500 against 500/500), `bisect.py`'s "bad as is
matches good: False", and `E1` (an ESC instead of a death) against the natural game over. The three `pc=` values that differ
between the two tables at cap-stops are removed by the `sed` in the last comparison; they are not game fields.

## Unpoked chain and the target queue

```
game | RNG at start     | $27134 entries 0,1 (x,y,z)        | life-loss ticks                         | over tick | over score | wave | losses | top-4 table at start
   1 | d193a672a21d3bc3 | 000000000000 000000000000                    | 4186,7744,10656,10812,11205,12088        |     12088 |      17526 |    3 |      6 | [20000, 10000, 7500, 5000]
   2 | 2da5930571fadfd1 | 515d03e07cd9 515d03e07cd9                    | 4580,8356,8791,10759,12196,12894         |     12894 |      19770 |    3 |      6 | [20000, 17526, 10000, 7500]
   3 | db4eaf97f2298c8f | 5a54043870a3 5a54043870a3                    | 4880,6119,7109,10047,13961,15018         |     15018 |      16984 |    3 |      6 | [20000, 19770, 17526, 10000]
   4 | 682ecd748cc4fb3f | 9e2f02902405 b2f40248422d                    | 3266,3948,5640,7106                      |      7106 |       9763 |    2 |      4 | [20000, 19770, 17526, 16984]
   5 | 3203c31d9cfe70a6 | 80790268c16e 80790268c16e                    | 4590,5723,7134,7936,8178                 |      8178 |      13302 |    3 |      5 | [20000, 19770, 17526, 16984]
   6 | d85fac8d5c8af760 | 99b80298331d 99b80298331d                    | 4752,8111,10768,11715,12044,13052        |     13052 |      19369 |    3 |      6 | [20000, 19770, 17526, 16984]
first life-loss tick by game : [4186, 4580, 4880, 3266, 4590, 4752]  rho vs game number = 0.37
game-over tick by game       : [12088, 12894, 15018, 7106, 8178, 13052]  rho = -0.03
game-over score by game      : [17526, 19770, 16984, 9763, 13302, 19369]  rho = -0.26
life losses per game         : [6, 6, 6, 4, 5, 6]  rho = 0.09
```

```
== N1, tick 1: the advance routine $232e6 reads the map cell under entry 0 (D3 low byte after the mask at $23314)
D0:0000515d D1:000003e0 D2:00007cd9 D3:00007d01
51 5d 03 e0 7c d9
== writes to entries 0..2 ($27134, 18 bytes): N1 over 60M steps (a held queue writes nothing), E1 over 3M steps (positive control)
N1: 0 writes
E1: 441 writes
== first call of the homing behaviour $21d62 (reads $27134 as the target): tick and the 24 table bytes
N1:
01 0a
51 5d 03 e0 7c d9 51 5d 03 e0 7c d9 4d 15 03 e0 81 0e 56 5f 04 58 53 5c
E1:
01 0a
51 b5 03 c0 47 d2 51 b5 03 c0 47 d2 51 b5 03 c0 47 d2 56 5f 04 58 53 5c
```

The `$27134` columns in the table are the first two of the four entries (x, y, z words each).

Gate manifest: not added to `reversing/virus/gates.toml` (another session's file); an entry would be
`cmd = "bash py/demo/gate_demo.sh"` with `expect` the five result lines above (about 2 minutes after `capture.sh`'s 2 minutes);
`gate_death.sh` is 14 minutes and is not meant for the routine gate run.
