# WORLD agent (Crude Buster): scripts

`world.md` is the reference text, `strings.md` the string list. Run everything from this directory: `./run.sh <lua> [secs]` wraps `reversing/crudebuster/cbmame.sh` with this agent's run dir (`CB_RUN`, default `./run`; a name without a slash is looked up in the shared `reversing/crudebuster/lua/`, then in `./lua`).

| script | what |
|---|---|
| `py/gates.sh` | demo streams (3798/3798 frames), fresh-game replay, pool C damage table (16 of 16), about 6 minutes |
| `py/cbrom.py` | ROM readers (`L/W/B`), used by every py script |
| `py/adis.py` | disassembly of a range with computed-jump tables decoded (`TABLE $x: ...`), uses `tools/disassemble.py` |
| `py/handler_summary.py` | per type-handler feature list (calls, spawns, sounds, flag writes) for pool A/B/C |
| `py/callers.py`, `py/d7callers.py` | callers of a routine with the D6/D7 immediates in front of the call (spawn helpers, text writers) |
| `py/flagops.py` | every bit operation on a flag cell in the linear listing |
| `py/scriptdump.py` | level script lists `$6c000`/`$6d000` (trigger, type, variant, x, y) |
| `py/scrollmaps.py` | decode of the per-level scroll page maps (`$8908`) |
| `py/text1c8a.py`, `text3370.py`, `text5878.py`, `text28fa.py`, `strings_dump.py` | the four text engines' string tables; `strings_dump.py` writes `strings.md` |
| `py/demostreams.py`, `py/demo_check.py`, `py/replay_check.py` | demo stream decode, stream vs attract log, fresh-game replay vs attract trajectory |
| `py/damage_tables.py` | pool C hit damage from `$fc34` and the `$fcba` tables vs the harness |
| `py/bcards.py`, `py/ccards.py`, `py/bnames.py` | pool B / C type tables of `world.md` (static + census + harness logs in `out/`) |
| `py/census_summary.py` | activation counts per pool/type of a census log |
| `py/force_summary.py`, `py/sheets.py`, `py/zoomrow.py`, `py/montage.py`, `py/transitions.py`, `py/ramview.py` | log summaries and contact sheets |
| `lua/census.lua` | start level `CB_LEVEL`, chase-and-punch bot with god mode, log activations of pools A/B/C, flag changes, player diffs (`CB_TAPS` write taps) |
| `lua/forcespawn.lua` | load a level state, poke one pool A/B/C record (`free`, `on` the player, `hit` = punches), log record, children, hp/score |
| `lua/clearpoke.lua` | load a state, poke `$80040` bit 4 (level cleared) and optionally clear it again (`CB_UNPOKE`) |
| `lua/streamplay.lua` | start a game at level `CB_LEVEL`, P2 flag poked on, feed the decoded demo streams through the ports |
| `d.sh` | one-line linear disassembly of the dump |
| `mont.sh` | contact sheet of PNGs |
