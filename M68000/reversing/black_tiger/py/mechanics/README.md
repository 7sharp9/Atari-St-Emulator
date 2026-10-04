# py/mechanics: Black Tiger mechanics scripts

Run from `M68000/` with `source .venv/bin/activate`. All scripts derive the repo root from `__file__` (`M68000_ROOT` overrides), read `$BT_WORK`
(default `M68000/scratchpad/black_tiger`: `play_start.snap`, `bt_auto.st`, `files/`) and write under `$BT_WORK/agents/mechanics/` (snapshots in `snaps/`).
`btlib.repl` always sets `ATARI_NOTRACE=1` and runs the existing `bin/Debug/net8.0/M68000.dll` (no build). Fresh `callcap`s on every run (no cache).
Runtimes are wall clock on the Mac.

| script | what it proves | expected output | runtime |
|---|---|---|---|
| `btlib.py` | helpers: snapshot RAM reader, REPL runner | | |
| `levelmap.py` | model of the marker scanner `$cd58` (map object and actor records, anchors) | | |
| `player_model.py` | model of `$ec7c` (tile class) and `$d7b0` (jump, fall, ladder, landing, state byte) | | |
| `gate_loader.py` | `levelmap.scan` equals `callcap $cd58` on all eight original level files | `levels matching: 8/8` | 3 s |
| `gate_vertical.py N seed` | `player_model.step_vertical` equals `callcap $d7b0` on random states; class-3 states clear the alive flag | seed 7: `393/393`, death 7/7; seed 11: `391/391`, 9/9; seed 23: `396/396`, 4/4 (N = 400) | 10 s each |
| `gate_weapon.py` | weapon damage `2*level+1` and the dying state in `$e930` | `25/25 match` | 1 s |
| `gate_urn.py` | urn contents (lcg, `$17784`) and spawned actors in `$d4ae` | `160/160` | 2 s |
| `gate_shop.py` | shop purchase rules `$fa9c` over random inventories | `200/200 match` | 5 s |
| `gate_bonus.py` | level-clear bonus `$1025c` by level | `matches 8/8` | 1 s |
| `gate_rng.py` | the RNG `$cb6a`/`$fe1c` | `300/300` | 2 s |
| `killscore_check.py` | kill score table `$1775c` by actor type | `matches 18/19` (type 5 is never killed) | 7 s |
| `killdrop_check.py` | kill drop table `$1771c` | `kill-drop table matches 18/18` | 6 s |
| `pickup_check.py [kinds]` | measured effect of every map-object kind | one line per kind (section 8 of `mechanics.md`) | 40 s |
| `chest_check.py [N]` | chest contents by effect kind | `chest contents model: 30/30` | 60 s |
| `jump_trace.py` | live per-tick (x,y) for a straight, a diagonal and a delayed-right jump | `matches table sequence ...: True` | 10 s |
| `drive_vitality0.py` | vitality 0 is not a death condition | start 1 and 2 die, start 0 stays alive | 20 s |
| `drive_shop.py` | live shop purchases with the joystick (screenshots via `snaps/shop_live_*.snap`) | money 5000 -> 4900 (item 0), 2500 (item 2), refusal for item 3 | 15 s |
| `drive_exit.py` | exit trigger, boss spawn, level clear, bonus, disk prompt, next level | exit flag 1, money 200 -> 500, level index 1, hero (160,944) | 20 s |
| `collision_maps.py` | draws `levels_collision.png`; start-cell check | `8/8` start cells head 0, chest 0, feet 1 | 3 s |
| `census.py`, `special_items.py` | marker census and `special_items.txt` | | 1 s |
| `render_buffers.py snap prefix` | both screen buffers of a snapshot with the live palette | | 2 s |

Labelled pokes are listed in each script's docstring (hero position, actor or map-object records at `$1f670` / `$1ff48`, money, seeds, the C stack argument at `$1ee50`).
