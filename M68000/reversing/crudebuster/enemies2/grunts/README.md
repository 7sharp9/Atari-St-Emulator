# GRUNTS (ENEMIES2) scripts and runs

Reference document: `grunts.md`. Environment: `export M68000_ROOT=<M68000 dir>`; Python is `M68000/.venv/bin/python`; MAME runs need `run.sh` (own `CB_RUN=./run`).

| file | what it does |
|---|---|
| `run.sh <lua> <outname>` | wrapper: sets `CB_DIR`, `CB_RUN=./run`, `CB_OUT=./out/<outname>`, runs `cbmame.sh run lua/<lua>` |
| `exp.sh <name> <level> <type> <var> [stop] [bot]` | one isolated enemy (type/var hex) poked into pool A at frame 750, P1 at (PX,PY) (default `170,1c0`), scroll (SX,SY) (default `100,100`), enemy at (EX,EY) (default `1c0,1c0`); list A script disabled; env passes through (`CB_OR`, `CB_IN`, `CB_BTN`, `CB_SHOTS`, ...) |
| `lua/probe.lua` | the harness: level start, `CB_SPAWN/CB_PLAYER/CB_SCROLL/CB_POKES/CB_OR/CB_IN`, `CB_NOSCRIPT`, bot 0/1/2, logs `F A S D B I` lines (header of the file); damage lines carry the writer pc, pool C box type/frame and the owner |
| `lua/objlog.lua`, `lua/wtap.lua` | the lead's tools, unchanged copies; `lua/objlog_lead.lua` = the lead's teleport-bot version (CB_BOT=3) used for `out/l4bot`, `out/l5bot` |
| `py/stats.py <probe.txt> [type]` | state entries/frames, attack-box instances, P1 health drops by writer pc / box type / owner state, P1 score steps |
| `py/objsum.py <log> [types]` | one line per enemy life: spawn frame, position, health, state sequence with run lengths |
| `py/hpdrops.py` | every enemy health decrement with state change and hit flags (`+6`) |
| `py/trans.py <type> <logs>` | state transition counts |
| `py/speeds.py <logs>` | per (type, state) position step per frame |
| `py/immune.py`, `py/stagger.py` | `+0` bit 3 window lengths; state 1 run lengths (weak 15 vs roll 65+) by hit flags |
| `py/chooser.py <type> [target state] [sub]` | expands the attack chooser `$2438a` tables (T1/T2/T3) into the states they can start, with probabilities |
| `py/dmg.py` | player damage per pool C box type per dip column, score table, contact damage |
| `py/boxes.py <ctype...>` | attack boxes from `$69000` per facing and frame |
| `py/usage.py` | list A entries of the grunt types and carriers, counts per level |
| `py/spawners.py` | every `$21eb6` caller with D6/D7 and enclosing handler |
| `py/firstframe.py` | frames in which a type is in a state (for screenshots) |
| `py/lst.py ai_tables.py handler_tables.py tables_decode.py` | the lead's tools, unchanged copies (`tables_decode.py` damage column is by pool A type and wrong for damage, see grunts.md 1.3) |
| `out/*.txt`, `out/sheet_*.png` | `dmg.txt`, `usage.txt`, `spawners.txt`, `boxes.txt`, `chooser_<type>_sub{0,4}.txt`; sheets of the five types and of attack frames |
| `out/<run>/probe.txt` | raw logs: `p<type>_<var>` passive, `a*` bot attacks, `r*` strong hit/throw pokes, `k*` kills (drops), `c1a_*` carrier, `v*` variants, `led_L*`/`t3 t4` ledge sentry, `shake39*` cling release, `dd39` dip, `l4bot l5bot` natural runs |

Reproduce a headline number: `./exp.sh p35_0 3 35 0 2500 0` with `PX=180` (sentry hits, `py/stats.py out/p35_0/probe.txt`); `CB_OR="800:81006:88;880:81011:40" ./exp.sh r3f 3 3f 0 1100 0` (strong hit then throw poke).
