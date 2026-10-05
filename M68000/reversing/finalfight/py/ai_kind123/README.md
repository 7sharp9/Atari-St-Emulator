# Kinds 1, 2 and 3 (J, TWO.P; AXL, SLASH; the ANDOREs): harness and gates

Method and results: `../../ai.md`, section "Kinds 1, 2 and 3". Everything runs MAME 0.289 headless through `run.sh` (SDL dummy driver, own run
directory). `AI123_RUN` is the MAME run directory (cfg, nvram, `sta/ffightuc/`, snapshots; default `<M68000>/scratchpad/finalfight/p3/b/run`), `AI123_OUT`
the output directory (records, logs, RAM dumps; default `.../p3/b/out`); two runs must not share an `AI123_RUN`. The repo root is derived from `__file__`.
Python needs only the standard library (the HUD name crops need Pillow: `../../../../.venv/bin/python`). `run.sh` copies `scratchpad/finalfight/ff_enemies.sta`
into the run directory on first use; the ROM image `scratchpad/finalfight/ff_main.bin` comes from `lua/dumprom.lua`.

The kinds are not live in any saved state, so `fdrive.lua` loads `ff_enemies` and emulates the tag-2 allocator `$3892` (`FF_SPAWN`). A freed record keeps `+78`
(effect group handle): zeroing it faults the first hit spark in `$7b78`. `FF_KILL`/`FF_NOSCRIPT` give a clean arena (no stage-script spawns).
`gates.py` redoes every gate with fresh runs (about 15 minutes); `gates.py <name> ...` runs a subset.

| file | what it proves / does | how to run |
|---|---|---|
| `run.sh` | MAME wrapper: loads `ff_enemies`, runs `$LUA` (default `fdrive.lua`) to a frame, per-frame records to `$AI123_OUT/<tag>_rec.txt` | `run.sh <tag> <stop> [ENV=VAL ...]`, `LUA=hits.lua` and `FF_MAMEARGS="-debug -debugger none"` for breakpoint runs |
| `fdrive.lua` | harness around `ffdrive.lua`: `FF_SPAWN="frame:kind:sub:b21:dx:dy:rank,..."` (position relative to Cody), `FF_KILL`, `FF_NOSCRIPT`, `FF_KEEPHP`, `FF_KEEPEHP`, `FF_POKE`, `FF_HOLD`, `FF_COPYP2`/`FF_P2DX` (clone P1 into P2), `FF_REC` (+`FF_RECHUD`, `FF_RECPROPS`), `FF_WATCH` write taps, `FF_SAVE` | via `run.sh` |
| `hits.lua` | `fdrive.lua` plus breakpoint counters/logs with a register (`FF_ADDRS="28f48@d0,73e4"`, `FF_HIT_OUT`, `FF_HIT_LOG`) | `LUA=hits.lua` |
| `pcprobe.lua`, `crashprobe.lua` | PC/register per frame; stop at the exception vectors `$719bc-$71a20` (found the `+78` spawn fault) | `LUA=...` with `FF_MAMEARGS` |
| `plans/tap12.lua`, `tap25.lua`, `right.lua` | Cody input plans: mash Button 1 every 12 / 25 frames; hold Right (walks into the enemy: grab) | `FF_PLAN=<path>` |
| `gates.py` | names 9 of 9 (HUD object's name entry pointer and its text), damage on Cody against the `$2fa2` rows, slot geometry, target rule, guard roll rate and dodge length, `ff_kinds123` determinism | `python3 gates.py [names damage slots target guard determinism]` |
| `recs.py`, `hist.py`, `edges.py`, `trans.py`, `dmglog.py` | record-file reader; state histogram; transition counts; state changes with fields; Cody's health drops per attack id | `python3 hist.py <rec> <idx> [lo hi]`, `edges.py <rec> <idx> [lo hi] [states to expand]` |
| `names.py` | the HUD name table `$5b640`: names per (kind, subtype) | `python3 names.py` |
| `script_scan.py`, `spawntable.py` | stage-script walker (table `$5f7e` is the live one: `$726e0` = 2) and the kinds 1-3 spawn entries | `script_scan.py 5f7e > $AI123_OUT/script_5f7e.txt; spawntable.py` |
| `anim.py`, `setters.py` | animation script decoder (`$3b10/$3b3c`): steps with timer, flag, hurt and attack box; every setter in a range | `python3 setters.py 28f00 29130` |
| `boxes.py`, `statstable.py`, `ranktab.py`, `atkscripts.py` | hurt/attack boxes with health, defence, damage by rank; the three rank bytes of `$281da`/`$2a3c8`; the combo script tables | `python3 statstable.py`, `atkscripts.py 28df0 2` (kind 3: `atkscripts.py 2e790 5 2e79a`) |
| `flow.py`, `seqdiff.py`, `cmpkinds.py` | control-flow listing with dispatch tables resolved (`FLOW_TABLES=T:n` forces a table length); kind 1 versus kind 2 diff | `python3 flow.py 2813a 2a310 2813a`; `seqdiff.py <flowA> <baseA> <flowB> <baseB>` |
| `hudname.py` | HUD name crops from snapshots (`FF_SHOT_LO/HI/STEP`) stacked into a PNG | `python3 hudname.py <snapdir> <tag> <lo> <hi> <step> <out.png>` |

Saved state `ff_kinds123.sta` (frame 4300, built by `gates.py determinism`) stays in `scratchpad/finalfight/` (see `scratchpad/ANCHORS.md`).
