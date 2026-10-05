# ENEMIES1 working directory

Deliverable: `enemies1.md`. Everything runs from this directory; paths derive from `__file__` (`M68000_ROOT` overrides). Python is `M68000/.venv/bin/python` for scripts that import PIL
(`expP.py`, `portraits.py`, `sheet.py`); the others use system `python3`. MAME runs use their own run dir under `run/<name>`.

Pictures: `portraits_l0.png`, `portraits_l1.png`, `portraits_l2.png` (crops from natural runs, `portraits.py`), `enemies_sheet_ground.png` (ground types alone on the street, `expP.py`; the boss tiles in it are empty because the lab cannot move the camera).

## Lua (`lua/`)

| file | what |
|---|---|
| `enemylog.lua` | start a level (`CB_LEVEL`), play it with a bot (`CB_BOT` 1 lane-filtered fighter, 0 walk, 2 idle, 3 walk only, 4 walk then stand), keep P1 alive (`CB_GOD` 1 before, 2 after the log line), optional assist hits (`CB_ASSIST` frames), portrait snapshots (`CB_PORTRAIT`), state saves (`CB_SAVES name:frame`), state load (`CB_LOAD`). Logs F (frame, scroll, flags, `$80400`, `$81e02`), P (P1 record), R (pool A), H (pool C) lines |
| `lab.lua` | controlled experiments: loads state `lab0` (level 0, frame 1000, nothing alive), runs a plan (`labrun.py` writes it): spawn, hit poke, kill, key, pin P1, god, script off |

## Python (`py/`)

| file | what |
|---|---|
| `scripts.py`, `census_static.py` | parse `$6c000` / `$6d000`, per-level type counts |
| `census.py` | script entries against a natural run: which spawned when, at which scroll position, non-script records |
| `states.py`, `fingerprint.py`, `showtype.py` | state tables of the 80 pool A handlers (longword dispatch that `rdis.py` does not follow), per-state fingerprint (velocities, spawns, next states), annotated listing |
| `lst.py` | slice of `scratchpad/crudebuster/all_lin.txt` by address |
| `brain.py`, `brain_probs.py` | decode of the `$2438a` decision tables; `brain_probs.py` turns them into exact next-state probabilities per type, table and distance bucket (`--json` for the infographic) |
| `boxes.py`, `cboxes.py`, `cdamage.py` | body boxes `$6b000`, attack boxes `$69000`, damage per C type and difficulty |
| `scrollmap.py` | per-level scroll/lock map `$8908` |
| `loglib.py`, `labana.py`, `bosslog.py`, `statetab.py`, `trans.py` | log parser and views (timeline, hp drops, per-state table, transition census) |
| `labrun.py`, `../labrun.sh`, `../run.sh` | run drivers (parallel MAME runs, own run dirs) |
| `expA.py`, `expA_agg.py`, `expA_sum.py` | approach and attack of each type at four offsets; aggregated per state |
| `expB.py`, `expB_sum.py`, `expB_kd.py` | hit pokes (`$80 $81 $82 $84 $88`), reaction classification |
| `expC.py`, `expC2.py` | bosses with and without hits |
| `expD.py` | measured speeds per (type, var, state) |
| `expE.py` | score per hit against the `$24952` table |
| `expF_contact.py` | contact events: 1 hp to P1, 1 hp to the enemy |
| `expP.py`, `portraits.py`, `sheet.py` | portrait sheets |

## Reproduce

```
cd reversing/crudebuster/enemies1
./run.sh nat0 $PWD/lua/enemylog.lua CB_STOP=26000 CB_LEVEL=0 CB_ASSIST=1500 CB_GOD=2     # natural level 0 (clears at frame 14882)
python3 py/census.py 0 out/nat0/enemylog.txt
SECS=600 ./run.sh lab $PWD/lua/enemylog.lua CB_STOP=1010 CB_LEVEL=0 CB_BOT=2 CB_GOD=0 CB_SAVES=lab0:1000   # makes run/lab/sta/cbuster/lab0.sta
python3 py/expA.py && python3 py/expA_agg.py ; python3 py/expB.py && python3 py/expB_kd.py ; python3 py/expD.py ; python3 py/expE.py ; python3 py/expF_contact.py ; python3 py/expC.py
```

Gotchas found: writing `$80113` = `$40` or more corrupts the tilemap RAM (the bar routine, `enemies1.md` 2.4); `-seconds_to_run` counts emulated time from the machine start, so
a state loaded from frame 12000 needs `SECS` above 210; a state loaded in `run` mode keeps the saved frame counter; a hit-object record is never alive at a frame end, attribute damage to the parent's state and animation frame.
`out/` holds the logs the doc cites (about 180 MB, gitignored with the rest of `scratchpad/`).
