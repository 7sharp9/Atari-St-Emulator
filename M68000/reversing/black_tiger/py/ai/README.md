# py/ai: Black Tiger enemy / AI gates

Run from `M68000/` with `export ATARI_NOTRACE=1` and `source .venv/bin/activate`; scripts find the repo root
from `__file__` (override `M68000_ROOT`), read inputs from `$BT_WORK` (default `scratchpad/black_tiger`) and
write under `$BT_WORK/agents/ai/`. They use `dotnet exec bin/Debug/net8.0/M68000.dll` and never build.
All gates start from `play_start.snap` and need `bt_auto.st`; `drive_boss.py` also needs
`agents/systems/lvl1..7.snap`; `type_table.py` needs the graphics decoder (`py/graphics/sprites.py` or
`agents/graphics/py/sprites.py`).

| script | what it proves | expected output | runtime |
|---|---|---|---|
| `btai.py` | the transcriptions: `rng`, `tile_class`, `db1c`, `df74`, `AI` (= `$dbde` and its helpers), `cd58`, `d65a`, `c972`, `ca48`, `e7e2`, `d40a`, `df26`, shot spawns | library | |
| `btharness.py`, `btram.py` | callcap batch harness (pokes by longword, resets between states), snapshot RAM helpers | library | |
| `gate_dbde.py 2500 11` | `$dbde` actor AI step vs `callcap dbde` (types 1..19, branch counters printed) | `MATCH 2500 / 2500` | ~5 min |
| `gate_spawn.py` | `$cd58` vs `callcap` on the live level and the 8 level files | `MATCH 9 / 9` | ~30 s |
| `gate_amb.py 800 5` | `$c972` and `$ca48` | `MATCH 800 / 800` | ~2 min |
| `gate_window.py 2` | activation window of `$e19e` | `window prediction MATCH 160 / 160` | ~1 min |
| `gate_urn.py 12` | urn burst drop roll (`$d4ae`) | `MATCH 96 / 96` | ~1 min |
| `gate_events.py 600 4` | `$e7e2` event attacks (hags, fire mummy, demon, boss dragons) | `MATCH 600 / 600` | ~1 min |
| `census.py` | per-level actor / object census from the level files (`spawn_census.txt`) | 8 levels | seconds |
| `type_table.py` | actor type table (`type_table.txt`) and `img/ai/actor_types.png` | 19 rows + PNG | seconds |
| `drive_boss.py [250000]` | boss snapshots `boss0..7.snap` (labelled pokes: hero x:y and camera onto the exit cell) | 8 lines, `$1eeb8=1`, hp 16*(L+1) | ~1 min |
| `boss_watch.py LEVEL` | per-frame boss state / position / shot-table samples (`boss/watch<N>.txt`) | one line per sample | ~15 s |
| `lst.py LO HI` | print a range of the static listing `bt_c470.asm` | | |
