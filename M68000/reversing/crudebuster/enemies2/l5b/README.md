# l5b: end of level 5, final boss, ending

Reference: `l5b.md`. `export M68000_ROOT=<M68000 dir>` first; Python is `M68000/.venv/bin/python`; MAME runs use their own `CB_RUN` under `run/<name>`.

| file | what |
|---|---|
| `lua/objlog.lua` | the lead's `objlog.lua` plus: `CB_KILL` (deactivate pool A types each frame), `CB_BTYPES` (teleport bot also hits pool B barriers), `CB_PREF` (bot target priority), `CB_EHPT` (restrict the health clamp to types), `CB_LOAD` (load a state, frame number comes back with it), `CB_TAP` (log writes to ranges with PC, `W` lines), `CB_HPTAP` (log every P1 health drop with the pool C / pool A records alive, `H` lines), `CB_P2` (two-player start), `CB_PLR` (player and `$80400` dump), `CB_POKES` |
| `run.sh <name> <lua> env...` | one MAME run in `run/<name>`, output `out/<name>` |
| `py/full.sh [name]` | the whole level-5 run from cold boot to the attract restart (about 22,500 frames): `out/full/objlog.txt` |
| `py/runload.sh <name> <state> <stop> env...` | the approach setup from a saved state (`s4770`, `s8100`, `s10100`, `s13000`, `s18600` in `run/{c,e,f}/sta/cbuster`; states made by `CB_SAVE`) |
| `py/levelend.sh <level> <0|1>` | poke `$80040 = $88` at frame 1500 and log the bit 4 writer (section 1 matrix) |
| `py/setters.py` | every writer of `$80040` bits 2, 3, 4 and `$80041` bit 7 with its handler type, shared routine users and level spawns |
| `py/milestones.py log [types]` | first/last frame, states, last health, position per pool A record segment |
| `py/states.py log f0 f1 [types]` | state change timeline (`S18=0` to ignore `+18`) |
| `py/actions.py log type offset [variant]` | run-length statistics and transition counts of one record byte |
| `py/ftrans.py log f0 f1 cols` | F-line changes in chosen columns (flags, `$80016`) |
| `py/wdedupe.py log [f0 f1]` | collapse `W` lines (writes with PC) |
| `py/scrollmap.py [level]` | the scroll permission grid of `$8876` (`$89a8` for level 5) |
| `py/sheet.py out cols pngs...` | contact sheet |
| `out/sheet_*.png` | 4f, scientist and boss entrance, boss fight, ending screens |
