# virus: the demo mode and its autopilot

The question: Virus's demo mode is said to be self-learning. This doc records who flies the ship in the demo, what
that pilot reads, and every test run for state that makes a later attract flight differ from an earlier one.

**Verdict, as far as the evidence goes.** The demo is a rule-based autopilot that steers by the live game state
(the ship, the terrain under it, the nearest record of the shared pool). Everything it keeps between ticks (the
controller word `$270a2`, the target pointer `$270a6`, the launch countdown `$62a60`) is re-initialised at game
start, and `$270a6` is rewritten from the live pool every eighth tick. No state was found that makes a later
attract flight better than an earlier one. Two flights differ only through the RNG state at the scatter that builds
the map and through stale buffer bytes; with the seed restored and four stale bytes cleared, a second game after a
natural game over repeats the first (lives, wave, tick, score and fuel at nine checks, five life losses). The demo
was run to its natural end: it loses its lives by itself, and a chain of six complete games with no pokes shows no trend
in survival or score (game-over tick 12088, 12894, 15018, 7106, 8178, 13052; rank correlation with the game number
-0.03; six games is a weak test). What persists across a natural game over is listed under "What persists"; none of it
is read by the pilot's own routines, and the one carried table that reaches the game (the infection target queue) can
only change which target a homing enemy steers to. The limits are in "Not tested" at the end.

Evidence labels: **gated** (a command below with a match count and a control), **poked** (reached through a named
poke), **read** (from `code.lst` or the disassembly only, not run). Addresses are runtime absolute. Commands run
from `M68000/`. The scripts are in `reversing/virus/py/demo/` (`py/demo/README.md` has the table); the captures
they read are built by `bash reversing/virus/py/demo/capture.sh` into `scratchpad/virus/demo/` and need
`bash reversing/virus/drive.sh` first.

## How the demo is entered

The title and "Press R" pages hand over to the attract loop `$24baa`. It runs a flying-camera scene one frame per
pass, counting D3 down from `$300` (`move.w #$300,D3` at `$24c1c`, `dbf D3` at `$24d10`: 769 passes, read). Inside the
loop the first of these that fires wins (read):

- key `$1f9ed` (SPACE) or the mouse button read by `$1fa54` goes to `$24cfc` and writes `$62a5f = 0`, a human game;
- the counter running out falls through to `$24d14`, which writes `$62a5f = $ff` (and `$62a6e = $ff`, which makes the
  camera height climb by `$180` a pass until it passes `$3200`, at `$24d28`), and the game starts at `$230c0`
  with the autopilot selected.

**Gated (a watch):** from `g_press.snap` with no key, `watch 62a5f 1` over 12M steps prints exactly one write,
`pc=$024d14 WriteByte $00062a5f <- $ff` (and the same single write from `g_title.snap` in 40M steps). Control in the
same gate: SPACE held on the press page gives the key branch's write of 0 instead (`pc=$024cfc`).
Command: `bash reversing/virus/py/demo/gate_demo.sh` (first section). The `g_game1/2.snap` snapshots of `drive.sh` are a
human game with no input (`$62a5f` = 0), not the demo. A third writer toggles the flag in play: key `$1f9d4`
(scancode `$20`) does `eori.b #$ff,$62a5f` at `$23274` (read, not driven). `$26050` clears it on the game-over path
(read).

A demo ends by itself when its last life is lost (next section); ESC ends it at once (`$232b8` branch to `$25bc0`).
The demo keeps `$2709a` (the HUD high score) at 0: `py/sample.py`, 80 samples at 5M steps over 400M steps.

## Where the inputs enter

The main loop `$23198` calls `$255c2` (`Ship_Tick`) each tick. `$255c2` tests `$62a5f`: nonzero calls `$2538c`
(autopilot), zero calls `$254aa` (mouse). Both return D0 (steer), D1 (pitch or magnitude) and D2 (bit 0 fire,
bit 1 thrust); control then reaches `$255d4`, where the flight model (`README.md`, "Flight model") takes over.
`$254aa` tests `$62a5f`'s neighbour `$62a5b`: nonzero goes to the keyboard reader `$2554a` (`$1f7d2..$1f7ee` hold the
bound-key pointers; it adds `$600` to D0 on one key, subtracts it on the opposite, steps D1 by `$c00`, and sets D2 bits 0
and 1 from two more keys); zero reads the mouse through `jsr $1fa54`, which returns the accumulated x and y in D0 and
D1 and the buttons in D2 (state words at `$1fa4a`, buttons byte `$1fa4e`) and converts the offsets from `$80` to an
angle and a magnitude with `$d8fa` and `$d9fa`. All read.

Virus installs its own IKBD handler: `$1f8c4` is stored into the kbdvbase vector at offset 32 (`$1f858`), the old vector
is kept at `$1fa34` and restored by `$1f8a0`. It reads `$fffc02`; scancodes below `$f6` go to a 128-byte key table at
`$1f9b4` (`$ff` held, 0 released) and the last make code to `$62a65`/`$62a66`; the packet headers `$f6..$ff`
select a length from `$1f99e` and the 1-3 byte mouse packet is added into `$1fa4a` (x, y words, start `$80`) with the
button byte at `$1fa4e`. Read. Keys the code tests directly: `$1f9ed` SPACE, `$1f9c7` R (redefine), `$1f9b5` ESC,
`$1f9d4` demo toggle. The attract and game-over loops poll the buttons with `$1fa66`.

## The pilot (read, plus one gated launch branch)

`$2538c` (`Input_Autopilot`) and its callees, each named from its body:

- `$2529a` (`Target_FindNearest`): scans the 20-byte records of the pool `$31d54` (count `$32a3e`) and returns the
  one with the smallest Manhattan distance to the ship (`$270b0`: x, y, z words, then vx, vy, vz at +6, +8, +10), skipping
  a record whose y word is `$f100` or whose long at +16 is `$228de`. Which kinds of record it picks (enemy, particle,
  emitter) is not established; the wave-start routine `$20e74` creates its records with y = `$f100`, so those are
  skipped.
- `$2538c`: while `$62a60` (set to 5 at `$2315c`) is nonzero it decrements it and returns D2 = 2 (thrust), D0 = D1 = 0.
  Otherwise, every eighth tick (`$32a44 & 7 = 0`) it calls `$2529a` and stores the pointer at `$270a6`. It loads the
  record's position and velocity, forms position + 4 x velocity (the record's) minus 4 x the ship's velocity, keeps that
  aim point at `$270aa`, takes the ground height under the ship with `$24754` (`byte[$42a58 + (z & $ff00) + (x >> 8)] * 8
  - $298`, so `Landscape_HeightAt`), and calls `$22c1e` to update the controller word at `$270a2`.
- `$22c1e` (`Autopilot_Steer`): builds the attitude matrix for the angles held in `$270a2` (`$1f646`) and, from the sign of
  two dot products of the relative vector with matrix rows, moves a turn byte by plus or minus 2 per tick (capped at
  `$3f`, floored at 0) and a second field by plus or minus `$700` per tick; bits 10 to 12 of the low word record the
  signs, and bits 10 and 11 are forced on when the ship's y word is below `$c900`.
- Output rules at `$25430..$254a6` (D4 = |dx| + |dy| + |dz| from the ship to the aim point, saturating to `$7fff`):
  thrust is the default; it is cleared when D4 >= `$3200` and the height term is at least `$600`, and when
  `$270a2` bit 11 is set; fire (bit 0) is set when D4 < `$900`; D0 comes from the controller word, forced to `$2000` at
  D4 >= `$2800`, to `$3500` with thrust forced on at D4 >= `$5a00`, and to `$1000` when the height term is at least `$c400`
  and D4 >= `$c00`; if the height term minus 4 x the ship's vertical velocity word is `<= $400`, thrust is forced on and
  D0 = `$400` (a ground-avoid reflex). `$255d4..` then clears thrust when the ship's y word, signed, is below `$c900`.
  Which sign of y is up was not worked out.

**Gated:** `callcap 2538c` from the first demo tick (the `$62a60` countdown branch): D2 `$7e9c` to 2, D0 and D1 to 0,
`$62a60` 5 to 4, 10 steps (one capture; not a model gate). The branch rules above are read, and there is no Python
model of a pilot tick gated against `callcap`. Poked, from `README.md`: with `wb 62a5f ff` on `fl/f1.snap`, 300,000 steps
call `$2538c` 10 times and `$254aa` 0 times, and the flight model matches 119/119.

Nothing the pilot reads is stored from an earlier run: `$270a2`, `$270a6`, `$62a60` and `$270aa` are initialised at
`$230c0` (`clr.l $270a2`, `$270a6 := $31d54`, `$62a60 := 5`). **Gated (a watch with its positive control):** `watch 270a6 4`
over 3M steps of a demo prints writes from `pc=$023132` (the initialiser) and `pc=$0253a4` (the eighth-tick update) only, 7
lines in that window. The RAM diffs between flight starts below (`$400..$70000`) differ in the code region only at `$17b45`, `$24933`,
`$24a87` and `$26b71`, none of them in the pilot routines (`$2529a`, `$2538c`, `$22c1e`, `$24754`, `$1f646`); that is a
comparison of start states, not a write-watch over a whole flight.

## What differs between flights

Fixed-budget runs from snapshots, REPL `s`/`m` samples, same step budget, one named variable changed.

**Determinism control (gated).** `S1b.snap` (flight 1) flown twice, 40 samples of 200,000 steps (tick, ship position
and velocity, flag): 40/40 identical. Command: `uv run python reversing/virus/py/demo/traj.py scratchpad/virus/demo/S1b.snap 40 200000`
twice and `cmp`.

**Flights 2 to 4 differ from flight 1 and from each other (natural RNG).** The RNG at `$2706e/$27072` is seeded once at
power-up (`$2300a`) and not again, so the object scatter (`$236f8`, README) places objects differently at every restart.
Score `$2708e` at tick 400: flight 1 84, flight 2 0, flight 3 82, flight 4 -5 (`py/measure.py`; the table is in
`py/demo/README.md`). No trend; lives stay 3 and rockets 3 in every window measured, and no life was lost in any of the
seven flights measured up to tick 700 or 1000 (so no crash was met; this is the only evidence on survival).

**With the RNG seed poked at the scatter the flights stop differing (poked).** Stopping at the first `$236f8` after an
ESC and poking `$2706e = $1234abdf`, `$27072 = $5678e7f2` (the seed the first flight's scatter used), flights 2, 3 and 4
(`Sp2`, `Sp3`, `Sp4`) are identical on every measure line printed (ticks 200, 400 and 700: score, lives, rockets, wave, fuel, position;
3/3 lines each) and differ from flight 1 (gate below). So a later flight does not differ from an earlier one through anything it
carried over, but through where the RNG stands.

**Which scatter builds the map (bisection, poked).** A restart runs two scatters (see "Natural death and game over"): A inside
`$25bc0` (stack word `$5bee`) and B at `$230a6` (`$30ac`); the next flight's map is B's. `Sp2` (seed poked at A) differs from
flight 1 from tick 12 and its map differs in 9,191 of 65,536 bytes, because B then ran with the RNG advanced by A, the
enemy spawn `$20e74` and the game-over screen. Two snapshots stopped at a scatter call after an ESC (`fl/Q1`, a 60,000-step
key hold, so the stop is scatter A; `c1/Q`, a 400,000-step hold that lets A run first, so the stop is scatter B) differ in 237
bytes outside the RNG. With the seed poked into both and the run continued to `$230c0` the maps differ, copying the 237 bytes
makes them agree, and delta debugging reduces the set to **2 bytes: `$06fffe..$06ffff`, `$30ac` against `$5bee`**, the lowest
return address on the stack (`watch 6fffe 2` from each snapshot shows only `jsr` pushes writing it). Poking `$30ac` over
`$5bee` makes A's scatter return into B's code, so one seeded scatter builds the map, which is why two bytes suffice; the
other 235 differing bytes (map cells, pool records, buffers) are consequences. Poking the seed at B reproduces flight 1's map
because B with the seed is the same call as the boot-time scatter. Command: `bash reversing/virus/py/demo/gate_demo.sh`
(bisect2 section). Without the poke the maps differ.
An earlier bisection of `S1b` against `Sp2` over all RAM found the 20 bytes that mattered for the first 10 trajectory
samples: pool record 0 (`$31d54..$31d5f`) and map cells `$32f61` and `$33352..$33358`, which are the same
consequences (`py/bisect.py`, not in the gate; about 2 minutes).

**A human game in between changes nothing (gated, control only).** From `g_press.snap` with SPACE held, the game starts at
`$230c0` with `$62a5f = 0` (`ctl/H`). Idle 20M steps with no input, ESC (the 400,000-step hold lets A run, so the stop is scatter B), seed poked at
B, run to `$230c0`: the demo then flies identically to flight 1 for all 100 samples of 200,000 steps (gate
below), and a flight with the seed poked at A instead (`Sp2`) does not (5/100). A mouse-flown game was tried
(thrust held and mouse nudges for 20M steps, then ESC and Return) but did not return to a demo within 150M steps, so it
is not tested.

## HUD and game-state fields

Named from the code that reads and writes them (read; the first two also from the runs above):

| Address | Meaning | Evidence |
|---|---|---|
| `$2708e` | score (long); cleared at `$2301e` and `$230cc`; awards added at `$1ffd6`, `$20066`, `$20240`, `$210c6`, `$216dc`, `$22180` (sign-extended word from A0); minus 1 per shot at `$25752`, so it goes negative | `$25f0c` compares it with the high score and stores it there |
| `$2709a` | high score; updated only when `$62a5f` = 0 (`$25f04`) | read; 0 after 400M steps of demo |
| `$27092`, `$27096` | last score seen and the next extra-life threshold (steps of `$1388`); crossing it adds one to `$32a54` and `$32a40` (`$24974`) | read |
| `$32a54` | lives; decremented at `$25ba0` after the crash animation, 0 goes to `$25bc0` (game over) | read; 3 in every measured window |
| `$32a40` | rockets | read; 3 in every measured window |
| `$32a50` | wave number; the HUD draws it plus 1 (`$24906`) | `README.md`; 0 in every measured window |
| `$32a2e` | fuel; `$e00` at `$23118`, `$1000` cap, refilled by `$19` a tick while landed (`$25a9e..$25aae`) | the other analysis's name; falls from 3269 to 2112 over 1000 ticks of flight 1 |

`$25f04`, `$25f3c` and `$260f4` are the only other tests of `$62a5f`: they skip the high-score update, the score line
and the name entry for a demo. No test of `$62a5f` guards collision or fuel (read: the whole listing has four reads of
the byte), so the demo is not made immune by that flag, and it does crash (next section).

## Natural death and game over

**Read.** A crash enters at `$25ad2` (from the collision tests at `$25804`, `$25862`, `$25874` and the ground tests of
`$25c28`: `$25c3e..$25c4e`). It lowers y by `$56`, clears `$62a5d` and `$62a62`, sets `$62a63` and `$62a5e`, zeroes the fuel
`$32a2e` (`$25af6`), calls the explosion `$202a4`, then runs a 50-frame loop (`$25b12..$25b9c`; SPACE leaves it early) and
reaches `$25ba0`: lives `$32a54` minus 1, HUD `$247d2`. With lives left it calls `$211da` and jumps to `$2310c`, the middle of
the game-start code, which re-initialises the ship, the fuel (`$e00`), `$270a2`, `$270a6`, `$62a60` and the flags (read:
`$2310c..$23192`) and keeps the wave, landscape and object map. With no lives left it goes to `$25bc0`, the same routine
ESC enters, which runs the game over in this order:

1. `$32a52 = $32a50` (the wave reached; no reader found in the routines read), scatter A (`jsr $2336a` with D0 = 0 at
   `$25be8`, return address `$25bee`), `$32a50 = 0`, the wave start `$20e74(0)`, then the game-over screen at `$25e44`.
2. `$260f4` (the score line) returns at once for a demo (`$62a5f` test, `$26178`). The score `$2708e` is compared with the
   tenth entry of the high-score table at `$25ccc` (10 entries of 28 bytes: a long score, then a name field), for any game,
   demo included, and inserted by shifting the lower entries down (`$25e60..$25eb8`). A human game then updates `$2709a`
   (`$25f04`) and runs the name entry; a demo copies the stock name at `$25e14` into the entry (`$2607c`).
3. `$26048` waits up to `$3e8` (1000) frames for the button or SPACE (`$1f7ee`). A key clears `$62a5f` and starts a human game
   at `$230c0` (`$26050`). A timeout runs `$230a4`: scatter B (`jsr $2336a` at `$230a6`, return `$230ac`), `$20e74(0)`, and a jump
   to the attract loop `$24baa`, whose timer starts the next demo at `$230c0` (`$62a5f = $ff`). The map of the next flight is
   the one scatter B builds.

Writes on this path that are not plain re-initialisation: the high-score table (`$25ccc..$25de3`, in the code image, so it
persists for the rest of the session), `$32a52`, and the human-only `$2709a`. Everything else it writes is cleared or
rebuilt before the next demo's first tick (`$2708e`, `$27092`, `$27096`, `$270a2`, `$270a6`, `$62a5d`, `$62a5e`, `$62a63`,
`$32a54`, `$32a40`, `$32a2e`, `$32a50`), by the code at `$230c0..$23192` (read) and, for the first six, observed
differing in the RAM diff below.

**Gated.** From `S1b` with no input the demo loses its lives by itself. Stops on `$25ba0` (`py/demo/deaths.py`, chunks of 100M
steps; `life_loss=yes` rows; values read before the decrement): tick 4186 (wave index 1, score 3966), 7744 (wave 2, 9809),
10656 (wave 3, 12830), 10812 (wave 3, 15078), 11205 (wave 3, lives 2, 16038); the sixth stop at lives 1 (tick 12088,
score 17526; `chain.py`) is the last life, after which the game over ran unaided and the next demo started. Lives rise back to 3 as the
score crosses the `$1388` steps (so lives were 3, 3, 3, 3, 2, 1 at the six stops). Fuel at tick 4026 was 47 and the first
loss is at 4186, which is consistent with the ship running out of fuel and falling (inferred: the crash code itself zeroes the
fuel, so a fuel of 0 at a stop shows nothing; the cause of the later losses was not examined).

The high-score table changed: after the game over its second entry holds 17526 (the last life's score) with the stock name
`David`, where the first demo's start state had 10000 and `Me...`; the lower entries moved down one place, so the tenth now
holds 500 `Cabbage` where it held 0 `Suicidal` (RAM at `$25ccc..$25de3` of `N1` against `S1b`; `py/demo/memdiff.py` over
`c000..27000` lists differences at `$25cea`, `$25d5a` and `$25dca`); the first entry, 20000 `Acceptable`, is unchanged. So a demo's score is recorded for the rest of the session; nothing the pilot reads depends on the table.

**Flights after a natural game over.** `N1` is the next demo start after the unaided game over, with the seed poked at scatter
B; `E1` is the same after an ESC at about the first demo's tick 70 (scatter B, same poke). Against flight 1, 500 samples of
200,000 steps (100M steps, about 2,000 ticks):

| start | identical samples | note |
|---|---|---|
| `E1` (ESC) | 500/500 | |
| `N1` (natural game over) | 205/500 | first difference at sample 110: the tick counter is one higher at the same ship position |
| `N1z` (`N1` with four bytes cleared: poke) | 500/500 | |

Delta debugging of `N1` against `E1` over `$27134..$271e3` (`py/demo/bisect.py`, 125 samples, the byte-level run with
`BGAP=0`) leaves four bytes, `$27139`, `$2713a`, `$27144` and `$27147`, nonzero in `N1`. They belong to a table described
under "The carried-over table" below. They are residue and perturb the run; `N1` (without the poke) has its first life loss at
tick 5237 against 4186 for flight 1, then 7348, 9267, 9489 and 10498 (lives 3, 3, 3, 2, 2 at the stops; wave 1 to 3), a
different play-through. With the four bytes cleared (`N1z`) the nine 100M-step checks of lives, wave, tick, score and fuel
equal flight 1's exactly (9/9), including the five life losses. At the same cap-stops the PC differs in 3 of 9 chunks while
those fields agree, so some instruction-level offset (a hardware phase outside RAM) is left that did not change any measured
field.

RAM diff at the start of the first demo (`S1b`) against the one after the game over (`N1`), bytes by region
(`py/demo/classify.py`, `$400..$70000`): 17,516 of 457,728 differ, of which 16,988 are in `$27000..$31d53` (variables and
buffers), 308 pool, 150 code and tables (the high-score table, in three ranges, and a few buffer words), 17 low RAM, 17 ship, 13 game words, 10 pilot state (`$270a2..$270af`, all zero at `S1b` and all rewritten at
`$230c0..$23192`: read), 6 score block, 5 stack, 2 selectors (`$62a5e`, `$62a63`, both rewritten at game start). The 2,974
bytes between `S1b` and `E1` fall in the same regions. The pilot, selector, score and RNG regions were compared at `$230c0`
only; a write-watch across the whole death and game over was not run.

## A chain of games with no pokes

`py/demo/chain.py` runs one REPL session from `S1b`: the demo flies with nothing poked or injected, each life loss is a stop on
`$25ba0`, the last life ends the game, and `bp 230c0` runs the game over and the attract loop to the next demo start; six
complete games (about 18 minutes, 3.3 billion steps), `py/demo/chain_table.py` prints the table:

| game | start RNG `$2706e` | life-loss ticks | over tick | over score | wave | losses | high-score table's top four at the start |
|---|---|---|---|---|---|---|---|
| 1 | `d193a672a21d3bc3` | 4186, 7744, 10656, 10812, 11205, 12088 | 12088 | 17526 | 3 | 6 | 20000, 10000, 7500, 5000 |
| 2 | `2da5930571fadfd1` | 4580, 8356, 8791, 10759, 12196, 12894 | 12894 | 19770 | 3 | 6 | 20000, 17526, 10000, 7500 |
| 3 | `db4eaf97f2298c8f` | 4880, 6119, 7109, 10047, 13961, 15018 | 15018 | 16984 | 3 | 6 | 20000, 19770, 17526, 10000 |
| 4 | `682ecd748cc4fb3f` | 3266, 3948, 5640, 7106 | 7106 | 9763 | 2 | 4 | 20000, 19770, 17526, 16984 |
| 5 | `3203c31d9cfe70a6` | 4590, 5723, 7134, 7936, 8178 | 8178 | 13302 | 3 | 5 | 20000, 19770, 17526, 16984 |
| 6 | `d85fac8d5c8af760` | 4752, 8111, 10768, 11715, 12044, 13052 | 13052 | 19369 | 3 | 6 | 20000, 19770, 17526, 16984 |

The `$27134` table at each game's start (`chain.jsonl`) is all zero for game 1 and the previous game's last queue for games 2 to 6.
Fuel used per game was not recorded (the crash code zeroes the fuel, so the value at a life loss says nothing). Rank correlation
with the game number: first life-loss tick 0.37 (4186, 4580, 4880, 3266, 4590, 4752), game-over tick -0.03, game-over score -0.26,
life losses 0.09. Game 4 is the shortest and game 3 the longest. With six games and this spread none of these is a trend: the
test could only have detected a very large effect, and a rank correlation of 0.37 or -0.26 on six points is well inside chance.
It shows no improvement with experience; it cannot exclude a small one.

## The carried-over table

`$27134..$2714b` is four entries of three words (x, y, z) at `$27134`, `$2713a`, `$27140`, `$27146`. The only code that writes it is
`$232e6` (shifts the queue) and `$206ac` (writes the last entry); the only code that reads entry 0 as data is `$21d62` and `$232e6`
(grep of `code.lst` for the four addresses; read). By their bodies:

- `$205f6` (`Infection_Plant`, D0 = x, D2 = z): if the ground at (x, z) is land (`$24754`, not water, not `$420`), it clears the
  minimap bits for that cell in the planes at `$2f6f6` and sets them again in the cell's colour (`$20642..$20676`), sets bit 5
  of the object-map byte (`$20696`, `bset #5,(A3)`), and, when the cell's low five bits are an object type 1 to 3, stores
  (x, y - `$b8`, z) as the queue's last entry (`$206ac`). `$206b8` calls it after adding a random offset (the RNG, `>> 4`) to x and z
  (`Infection_PlantJittered`); the names are inferred from the bit-5 write and the minimap update, not confirmed on screen.
- `$232e6` (`InfectionQueue_Advance`, once per tick from `$231c4`): looks at the map cell under entry 0. If the cell's low five
  bits are zero, or bit 4 is set, it shifts the queue down (entry 1 to 0, 2 to 1, 3 to 2); otherwise it returns and keeps entry 0.
  So entry 0 is held while an object of types 1 to 15 without bit 4 is still on that cell.
- `$21d62` is inside a pool-record behaviour that integrates the record's position and velocity (1/32 drag and the gravity word
  `$32a3a`). On every fourth frame (`$32a48 & 3 = 0`) it calls the steering routine `$22c1e` with A2 = `$27134`, i.e. it steers the
  record toward entry 0, computes the Manhattan distance to it and calls `$22e38` when that is at most `$a00`; on the other frames it
  calls `$22d04` (read). `$22c1e` is the same routine the autopilot calls with its aim point at `$270aa`. So the table is a target
  queue for homing pool records: a short list of places a record steers toward. What those records look like on screen was not
  checked.

**Does the pilot read it?** The pilot's own routines (`$2529a`, `$2538c`, `$22c1e`'s call from `$2538c`) never reference
`$27134`; it reaches the pilot only through the positions of the records that use it, which `$2529a` can pick as a target. Whether
it does was not measured.

**Why it carries over.** Nothing clears it: no store to `$27134..$2714b` exists outside the two writers above, and the game-start
code `$230c0..$23192` does not touch it, for a demo or a human game (read). Game 1 sees zeros because the machine started
cleared. **Gated observation** (`py/demo/queue_check.sh`): in `N1` the map cell under the stale entry 0 has low byte 1 at tick 1
(D3 at `$23314`), so `$232e6` returns every tick and holds the stale position: 0 writes to `$27134..$27145` over 60M steps (about
1,300 ticks), against 441 writes in 3M steps for `E1` (zero entries, shifted every tick), the positive control. The first call
of the homing behaviour at tick 266 then uses entry 0 = (`$515d`, `$03e0`, `$7cd9`) in `N1` and a freshly planted position in
`E1`. That call is the first reader of the table in both runs; the first difference in the ship's trajectory is later (tick 443 against 444
at the same ship position, sample 110), so the table is shown to differ from the first reader on, not shown to cause that difference by itself
(the 4-byte poke above does: `N1z` 500/500). In `N1` the map is the same one game 1 had, so the stale position still
holds an object; with a different map (the unpoked chain) the stale entry is usually flushed within the first ticks (not
measured).

## What persists across a natural game over

- The high-score table `$25ccc..$25de3`: the game-over screen writes the score into it under the stock name `David`; the table is
  read only by the hall-of-fame display and by the next insertion, so it cannot change how the pilot flies.
- `$32a52` (the wave reached): written at `$25bdc`; no reader found in the code read, so it cannot change the pilot.
- The infection target queue `$27134..$2714b`: the last four planted positions; read by homing pool records (`$21d62`), so it can
  change which place a homing enemy steers to and, through that, the pool the autopilot reacts to, but it is the previous game's
  geometry, not an experience-dependent parameter.
- The RNG `$2706e/$27072`: never reseeded after power-up; it sets where the scatter puts the objects and enemies in the next game,
  so it changes the landscape objects and thus the flight, with no relation to how the last game went.

## Not tested

- A mouse-flown human game before an attract flight (the attempt did not return to a demo).
- Anything beyond six games in the unpoked chain, and a power test: six games cannot show a small trend. Fuel used and kills per
  game were not recorded.
- Whether the pilot picks the homing records that read `$27134` as its target, and what those records are on screen.
- Whether the stale queue is held through a game in the unpoked chain (measured only in `N1`, where the map equals game 1's).
- The cause of the life losses after the first (the fuel exhaustion reading is inferred for the first only).
- A write-watch across the whole death, game over and attract loop (the regions were diffed at the two start states).
- A Python model of one pilot tick gated against `callcap` (only the launch branch was captured). The rules above are
  read.
- The hardware phase offset that makes the PC at a cap-stop differ although the game fields agree (N1z against flight 1).
- Equality of flights beyond 100 samples of 200,000 steps (about 20M steps, a few hundred ticks), and any measure other
  than the printed ones (kills are only visible as score awards).
- What the pool records the autopilot targets are (`$2529a` skips y = `$f100` and pointer `$228de`).

## Gates

`bash reversing/virus/py/demo/gate_demo.sh` after `bash reversing/virus/py/demo/capture.sh` (timer, scatter bisection, flights
2 to 4, human game in between), and `bash reversing/virus/py/demo/gate_death.sh` after `bash reversing/virus/py/demo/capture_death.sh`
(natural death and game over, about 14 minutes), `chain.py` with `chain_table.py` (the unpoked chain, about 18 minutes) and
`queue_check.sh` (the target queue); the raw lines are in `py/demo/README.md`. The gates read snapshots and run the
emulator, so they are not in `gates.toml`. The `.sym` names for this doc are appended to `virus.sym`.
