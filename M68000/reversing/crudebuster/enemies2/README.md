# ENEMIES2 (Crude Buster pool A types of levels 3 to 5, bosses, level end, ending)

Reference: `enemies2.md` (integration). Group documents: `grunts/grunts.md`, `special34/special34.md`, `l5a/l5a.md`, `l5b/l5b.md`, each with its own `README.md`/`py/README.md`. `BRIEF2.md` is the brief the groups worked from (its errors are listed in `enemies2.md` section 5).
Setup: `export M68000_ROOT=<M68000 dir>`; Python is `$M68000_ROOT/.venv/bin/python`; MAME runs use `CB_RUN=<dir>/run` (never share) through `reversing/crudebuster/cbmame.sh run <lua> <seconds>`.

| file | what |
|---|---|
| `py/scripts_dump.py` | parses list A (`$6c000`) and list B (`$6d000`), every entry of the six levels and a type/variant count per level (`out/scripts.txt`); `entries(base, level)` is imported by the other scripts |
| `py/type_by_level.py` | the type/variant by level count table (`out/type_by_level.md`) |
| `py/census.py <objlog> <level>` | pool A activations of a run against the script entries (type, variant, x and y within 2), dynamic spawns, flag/scroll events |
| `py/census_table.py A\|B <level> [names.json]` | markdown census table with the scroll at which each entry was first seen in `out/l<level>/objlog.txt` (`out/census_tables_A.md`, `_B.md`, `out/names.json`) |
| `py/lockmap.py` | the camera cell maps of the six levels with the meaning of the words (`out/lockmap.txt`) |
| `py/flag_setters.py` | every writer of `$80040` bits 2 to 4, `$80041` bit 7, `$80400` bits 5 to 7 with its owner handler (`out/flag_setters.txt`) |
| `py/spawn_graph.py A\|B\|C` | static spawn graph of `$21eb6` / `$21efa` / `$21e72` callers (`out/spawn_graph_A.txt`) |
| `py/handler_tables.py <lo> <hi>` | decodes the `lea / movea.l 0(A0,D0.w)` longword state tables of the handlers (`out/tables_all.txt`: 58 dispatch tables of `$10778-$22000`) |
| `py/ai_tables.py <type> [T1\|T2\|T3]` | dumps the `$2438a` chooser tables of a type (routines, not outcomes; see `grunts/py/chooser.py`, `special34/py/ai_summary.py` for expanded outcomes) |
| `py/tables_decode.py [type..]` | damage column (WRONG as a per-owner-type table, see `enemies2.md` section 5), reaction byte, score row of a type |
| `py/lst.py <lo> <hi>` | slice of the linear listing `scratchpad/crudebuster/all_lin.txt` |
| `lua/objlog.lua` | level start plus per-frame log of pool A/B/C records (`CB_POOLB`, `CB_POOLC`), `CB_X` extra cells, `CB_W lo-hi` write tap lines, bots: `CB_BOT=1` walk and attack, `2` plus unstick jumps, `3` teleport bot (`CB_EHP` health clamp, `CB_LANEY`/`CB_YREL`, `CB_STALL` stall breaker that clears pool A completely and the boss locks, `CB_PARK_AT` park at the scroll trigger without attacking, `CB_CLR81E03` release the five-enemy block each frame) |
| `lua/wtap.lua` | start a level and log every write to a RAM range with the PC (`CB_WLO`, `CB_WHI`, `CB_F0`) |
| `out/l3`, `out/l4`, `out/l5` | census logs (teleport bot, `CB_EHP=1`): level 3 complete, level 4 up to the descent, level 5 to the crate at scroll `$c01`; `out/l3b` (writers of `$80040`/`$80041` around the level end), `out/l3c`, `out/l3d` (camera freeze at the boss arena, with and without `$81e03` cleared) |

Reproduce the headline items:

- level 3 census: `CB_LEVEL=3 CB_STOP=6500 CB_BOT=3 CB_EHP=1 CB_LANEY=448 CB_STALL=100000 CB_OUT=<dir> CB_X="80400:b,80401:b,80402:b,8044e:w,81e12:b,81e03:b" cbmame.sh run lua/objlog.lua 130`, then `py/census.py <dir>/objlog.txt 3` (32 of 32).
- camera freeze: same with `CB_PARK_AT=5f0 CB_STOP=3700` (add `CB_CLR81E03=1` for the control run).
- level end writers: `CB_W=80040-80041 CB_WF0=5900 CB_STOP=6500` on the level 3 run: the lines not from `pc=007982` are `$23e2e/$23e54/$23e5c` at frame 6007 (bit 2 cleared, `$80041` bit 7 cleared, bit 3 set) and `$c86a` at 6263 (bit 4).
