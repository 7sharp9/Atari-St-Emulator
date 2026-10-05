# agents/player: Crude Buster player mechanics and combat engine

Result document: `player.md` (field map, move table, damage and score formulas, join/continue/timer, bot, errors). Everything here derives its paths from `__file__` or `$M68000_ROOT`; MAME runs
need their own run directory (`CB_RUN`), which `env.sh` (`cbrun <script|run> <lua> <seconds>`, `RUNX=run2` for a second process) and `py/gates.sh` take care of. Runs write only under this directory.

Re-run every check from scratch: `py/gates.sh` (about 1.5 minutes, up to 5 MAME processes in parallel, output under `out/g_*`, result in `out/gates_run.txt`).

## Lua drivers (`lua/`, all run with `cbmame.sh run`, level 0 = the first stage, started like `startlevel.lua`)

| script | what it does |
|---|---|
| `bot.lua` | the reusable bot (item 5): plays level `CB_LEVEL`, god mode, saves states (`CB_SAVEAT`, `CB_STOPAT`), screenshots, resumes from a state (`CB_LOAD`), optional P2. Header lists all variables. CSV `bot.csv` every `CB_LOG` frames |
| `reclog.lua` | start a level, play a plan, log byte regions per frame (`CB_REGIONS`), poke every frame (`CB_POKES`), spawn pool A / B records (`CB_SPAWNS`, `CB_SPAWNSB`), log writes with pc (`CB_TAPS`), log every call of the melee test (`CB_FA10=1`), resume a state (`CB_LOAD`) |
| `dmglab.lua` | one enemy type after another in front of an idle vulnerable player; logs every health write with its writer pc and the attacker's pool and type (`dmg.txt`) |
| `hitlab.lua` | invulnerable player taps b1 (jab) or b3 (grab and throw, `CB_BTN=b3`) at an enemy of each type; logs the enemy's HP, state, hit byte and the score changes (`hit.txt`) |
| `carrylab.lua` | pool B props in front of the player: grab (b3), swing (b1), throw (b3); logs the carry flags (`carry.txt`) |
| `contlab.lua` | coins, start, deaths, continue prompt, 2-player join; logs changes of the credit, lives, health, mode and score bytes (`cont.txt`) |
| `dumpram.lua`, `shots.lua` | work RAM dump at chosen frames, screenshots at chosen frames |
| `plans/*.lua` | input plans (`{frame, field, level}`), made by `py/mkplan.py` or by hand: `moves1`, `moves2` (move suites), `chain` (second-tap window), `spam` (b1 every 6 frames), `grab2` (can pick-up and throw from the saved state `l1_wall`), `twop1-4`, `canhit`, `dash`, `weapon`, `walk2`, `ud` |

## Python (`py/`; run with `M68000/.venv/bin/python`)

| script | purpose | gate result in `player.md` |
|---|---|---|
| `gates.sh` | runs everything below from fresh runs | all lines PASS or counts |
| `romlib.py` | read words and bytes of the decrypted image (`romlib.py addr n l`, `w`, or `b`) | |
| `mkplan.py` | `"frame buttons hold; ..."` to a Lua plan | |
| `recview.py`, `seq.py`, `pos.py`, `boxes.py`, `sheet.py` | log viewers: changed bytes, selected bytes per frame, x/y deltas, attack boxes relative to the player, contact sheet of screenshots | |
| `fieldscan.py` | usage count of every `N(A6)` offset in a code range of the linear listing | |
| `gate_move.py` | walking speed, jump formula and duration, forward jump step, jab-chain flags and length | 372 of 372 |
| `movetable.py` | frame data table of the moves from the standard logs | move table |
| `atkbox.py` | static attack-box table `$67000[pose][variant][frame][facing]` | rows equal the live boxes |
| `hitbox_gate.py` | player attack versus enemy body box (`$f82e`/`$f8ba`) | 397 tests, 71 hits, 0 disagreements |
| `melee_gate.py` | enemy melee box versus player body box (`$fa10`/`$fb8c`) per logged call | 2628 calls, 13 hits, 0 disagreements |
| `dmg_check.py` | every player health decrement against the ROM damage tables | 83 of 83 (lab runs), 35 of 35 (gates) |
| `gate_score.py` | score awards against `$24952` and `$4016` (jab and throw runs) | 6 + 4 trials, 0 mismatches |
| `gate_throw.py` | carried, flying, dead with HP-4 for grabbed enemies | 4 of 4 |
| `gate_pickup.py` | can pick-up and throw (+26, +58, +92, 4 px/frame) | 5 of 5 |
| `gate_canhit.py` | thrown can hits a grunt: +6 = `$88`, HP-4 | 1 of 1 |
| `gate_lives.py` | lives 2, 1, 0, continue prompt, 126-frame digits, game over, attract; continue effects | 5 of 5 |
| `gate_2p.py`, `p1p2_compare.py` | join-in, partner grab and throw, no friendly fire; P1 equals P2 | 8 of 8; 136 of 136 |
| `tables.py` | prints the player-side ROM tables (score, damage by difficulty, contact, reaction codes, pickup flags, lives, timers) | |

Extra runs behind numbers in `player.md` that `gates.sh` does not repeat: `out/dmg_all.txt` is `cat out/dmg3/dmg.txt out/dmg4/dmg.txt out/g_dmg/dmg.txt` (dmglab over 80 types, 83 decrements);
`out/contact2` (contact trade: `reclog.lua` with `CB_TAPS=81005:1,8013c:4,80113:1`), `out/wall` (rubble wall record during the can's flight), `out/b53`, `out/held`, `out/held2`, `out/timer`, `out/carry1`, `out/ud1-5`, `out/botL1-5`.
Older exploratory logs sit beside them under `out/`.

## Traps found on the way

- `cpu.state["A6"]` inside a write tap is the register at the write: the attacker of `$fc9e` is a pool C record, not the enemy that owns it.
- Taps see the Lua script's own writes: filter the pc range `$bbe-$bd4` (the main-loop wait where `frame_done` runs).
- Pool C hit-box records live only inside one frame (`$22526` clears them after the test): an end-of-frame snapshot never sees them; use a read tap on the table access of `$fbdc`.
- Edge-latched inputs are lost when a logic step spans two VBLs (continue screen): press with an odd period.
- `screen:frame_number()` is restored by a state load: plan frames after `CB_LOAD` are the original run's frames.
- zsh does not split `$VAR`: use `${=VAR}` or pass the words one by one.
