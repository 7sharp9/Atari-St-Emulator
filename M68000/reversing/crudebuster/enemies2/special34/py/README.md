# special34 scripts

Run from anywhere; paths derive from `__file__`. Python is `M68000/.venv/bin/python`; `export M68000_ROOT=<M68000>` for the table tools. MAME runs write only under `special34/run/<name>` and `special34/out/<name>`.

| script | what | used for |
|---|---|---|
| `py/run.sh <name> <lua> ENV=..` | one MAME run (own `CB_RUN`), objlog in `out/<name>/objlog.txt` | every live result |
| `py/probe.sh <name> <level> <type> <var> [frames]` | injects one pool A record at screen centre of an empty level (script list pointer at its terminator), idle P1; `HP=0` to let P1 take damage, `SHOT=` screenshot step | sections 4, 5, 8, 9 |
| `lua/objlog.lua` | lead's logger plus: `CB_WPOKES frame:addr:word`, `CB_SPAWN frame:type:var:x:y`, `CB_PPOS`, `CB_HOLD`, `CB_CLEARA frame` (clear pool A), `CB_IDLE=1`, `CB_SIDE=1`, `CB_TGT=hex,..` (teleport bot targets only these types), `CB_TELE_FROM=frame`; F lines carry P1 state, sub-state, score long, high score before the `CB_X` values | all |
| `lua/wtap.lua` | the lead's write tap, unchanged | not used |
| `py/ol.py` | objlog reader (`frames()`), `trace --type --fields --from --to --pool` | everywhere |
| `py/rectrace.py <log> <type> [from to max fields]` | one line per change of the chosen fields of one record type | state sequences (e.g. `rectrace.py out/b1f/objlog.txt 1f 800 4000 60 3,5`) |
| `py/flags.py <log> [from to]` | frames where `$80040`/`$80041`/level byte change | section 10 |
| `py/hpdrops.py <log>` | P1 health drops with the live records near P1 (run with `CB_HP=0`) | damage |
| `py/scores.py <log>` | P1 score changes and the live record types | score table |
| `py/typestates.py <type> [lo hi ..]` | handler, state tables, state -> routine, shared/own tag | state tables |
| `py/ai_summary.py <type>` | expands the `$2438a` chooser tables into state distributions | attack triggers |
| `py/spawners.py A|B|C|S` | every caller of `$21eb6` / `$21efa` / `$21e72` / `$24056` with D6/D7 immediates (hex and decimal mixed: check `moveq`) and owner type | children, boxes |
| `py/boxdmg.py [box ..]` | damage per pool C box type, reaction code, pool B damage byte | section 1 |
| `py/ptable.py <addr> <n>` | n longword code pointers | hand-written tables |
| `py/lst.py <lo> <hi>` | linear listing slice | reading |
| `py/sheet.py <out.png> <cols> <png..>` | contact sheet of snapshots | screenshots |

Reproductions (level start is about frame 720, injections at frame 800-802):

- 0x1f fight: `py/run.sh b1f objlog.lua CB_LEVEL=3 CB_STOP=2600 CB_BOT=3 CB_TGT=1f CB_SIDE=1 CB_HP=0 CB_POOLB=1 CB_CLEARA=799 CB_WPOKES=799:81e06:0006,799:81e08:c54e,800:8040a:0800,800:80108:0880,801:80108:0880 CB_SPAWN=802:1f:0:910:1c0` then `rectrace.py`, `scores.py`, `flags.py`.
- 0x12 boss body: same with `CB_LEVEL=4 CB_TGT=12 CB_SIDE=1 CB_SPAWN=802:12:2:910:2c0`, list pointer `c730`, scroll `0900`, `80406:0200`, P1 y `02c0`, `CB_STOP=6000`.
- 0x3a death: level 3, list pointer `c546` (the 0x17 var `$22` entry), scroll `0a00`, `CB_TGT=11,3a,0c,40`, `CB_POKES=1200:81045:20,1400:81005:03`, `CB_STOP=4500`.
- 0x1e morph: level 4, pointer `c628`, scroll `0500`, `80406:0100`, `CB_POKES=1100:810c5:20`.
