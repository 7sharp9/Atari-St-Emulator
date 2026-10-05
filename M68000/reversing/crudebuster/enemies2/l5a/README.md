# L5A (Crude Buster level 5, pool A types $4a-$4d and the objects they spawn)

Reference: `l5a.md`. Everything here runs from this directory; the root is derived from `__file__` or `M68000_ROOT`. MAME runs use `run.sh` (own `CB_RUN`, default `run/`) or `run_job.sh <name> VAR=value ...`
(its own run dir `run/<name>`, log `out/<name>.log`, output `out/<name>/objlog.txt`). Python for the sheets is `M68000/.venv/bin/python` (PIL), everything else is plain `python3`.
zsh does not word-split variables: pass each `CB_*` word separately. macOS has no `timeout`.

## Scripts

| file | what | gate / use |
|---|---|---|
| `lua/drive5.lua` | level start + scripted pokes + per-frame log of pools A/B/C, taps `H` (health writes with writer PC, hit box type, owner type/state), `S` (hit box spawns), `Z` (sound latch writes). Env documented in its header: `CB_SPAWN`, `CB_PTR`/`CB_PTRB` (list pointers), `CB_SCROLL`, `CB_HOLDSCROLL(2)`, `CB_BOT` 0/1/2/5, `CB_FOLLOW(Y)`, `CB_BLOCK`, `CB_NOATK`, `CB_INJECT` (+`CB_INJAT`, `CB_INJSTATES`, `CB_INJOFS`, `CB_INJVAL`, `CB_INJREFILL`), `CB_SHOTS`, `CB_POOLB/C` | every log in `out/` |
| `lua/objlog.lua` | copy of the lead's logger (unmodified) | reference |
| `run.sh`, `run_job.sh` | wrappers around `reversing/crudebuster/cbmame.sh run` | |
| `py/loglib.py` | parser (F/A lines, episodes, state runs): `loglib.py <log> [type]` prints state runs | |
| `py/summ.py` | per type: frames per state, transitions, run lengths, hp changes, P1 score events | `summ.py out/kill_4a/objlog.txt 4a` |
| `py/events.py` | H (damage by writer, hit box type, owner), S (hit box spawns), Z (sounds) | |
| `py/dmg_check.py` | hit box damage table prediction (`table[ctype]*4`, dip `$80054`) vs live `H` lines | 9 of 9 hit box types match (`l5a.md` section 3) |
| `py/chooser.py` | decodes the `$2438a` tables T1/T2/T3 of a type into leaf routines and the states they set | `chooser.py 4c` |
| `py/chooser_check.py` | predicts each non-hit transition out of states 6-9 from positions and P1 state, compares with the log | 145/145 (`$4a`), 179/179 (`$4b`), 1804/1867 (`$4c`, 59 natural ends, 4 misses), 164/164 (`$4d`, 28 natural, 18 timeouts) |
| `py/inject_check.py` | immunity: synthetic hit outcome vs flag prediction (`+0` bit 3/6, `+17` bit 1, `$22ce4` grab states) | 0 wrong in 88/174/95/110 injections |
| `py/bodybox.py` | body (contact/hurt) boxes `$6b000[type][state]`, contact damage byte `$f78e`, reaction `$f7de` | |
| `py/speeds.py` | per-state mean dx/dy per frame, velocity field, y excursion | |
| `py/flags.py` | frames where `$80040`/`$80041`/`$80400` change | `$4d` only sets `$80400` bit 5 |
| `py/poolb.py` | pool B episodes (drops, effects) | no drops |
| `py/spawn_check.py` | script entries of level 5 list A vs first rows of live records | section 9 of `l5a.md` |
| `py/sheet.py` | contact sheets of screenshots | `out/sheet_*.png` |

## Commands that produced the main logs (CB_LEVEL=5 is added by `run_job.sh`)

```
# isolated kill runs (P1 stands beside the enemy, camera follows)
./run_job.sh kill_4a CB_STOP=5000 CB_BOT=2 CB_BLOCK=1 CB_FOLLOW=1 CB_POOLB=1 CB_SPAWN="800:4a:0:220:7c0"      # also 4b, 4c
./run_job.sh kill_4d2 CB_STOP=7000 CB_BOT=2 CB_BLOCK=1 CB_POOLB=1 CB_HOLDSCROLL="e20:100" CB_SPAWN="800:4d:0:ed8:1a0"
# idle player at cycling distances/lanes (AI census), no attacks
./run_job.sh wander_4a CB_STOP=6000 CB_BOT=5 CB_BLOCK=1 CB_FOLLOW=1 CB_SPAWN="800:4a:0:220:7c0"
./run_job.sh wander_4d2 CB_STOP=6000 CB_BOT=5 CB_BLOCK=1 CB_HOLDSCROLL="e20:100" CB_SPAWN="800:4d:0:ed8:1a0"
# immunity census (synthetic hits)
./run_job.sh inj3_4b CB_STOP=14000 CB_BOT=5 CB_BLOCK=1 CB_FOLLOW=1 CB_INJECT=1 CB_INJREFILL=1 CB_INJAT=3 CB_INJSTATES="b,c,d,e,f,10,11" CB_SPAWN="800:4b:0:220:7c0"
# throw hit (+17 bit 6) and strong hit (+6 |= $88) on 4a
./run_job.sh injx_4a_t17 CB_STOP=3500 CB_BOT=5 CB_BLOCK=1 CB_FOLLOW=1 CB_INJECT=1 CB_INJREFILL=1 CB_INJAT=3 CB_INJOFS=11 CB_INJVAL=40 CB_INJSTATES="6,7,b,c,d" CB_SPAWN="800:4a:0:220:7c0"
# natural script spawns (list A pointer poked to an entry, list B pointer to the terminator so the stage props do not block)
./run_job.sh nat4 CB_STOP=9000 CB_BOT=2 CB_POOLB=1 CB_PTR="799:6c96c" CB_PTRB="799:6d5a2" CB_HOLDSCROLL="e20:100" CB_HOLDSCROLL2="3500:f00:100"
./run_job.sh nat3 CB_STOP=9000 CB_BOT=2 CB_FOLLOW=1 CB_POOLB=1 CB_PTR="799:6c94c" CB_SCROLL="799:c00:100;3200:e20:100"
# variants of 0x44 (v44_<var>), 4a variant 1
./run_job.sh v44_0 CB_STOP=1400 CB_BOT=0 CB_BLOCK=1 CB_SCROLL="1000:500:700" CB_SPAWN="800:44:0:220:7c0"
./run_job.sh kill_4a_v1 CB_STOP=2500 CB_BOT=2 CB_BLOCK=1 CB_FOLLOW=1 CB_POOLB=1 CB_SPAWN="800:4a:1:220:7c0"
```
Note: the byte offsets of `CB_INJOFS` are hex (`+17` decimal is `11`).
Analysis: `M68000_ROOT=<M68000> python3 py/<script>.py out/<job>/objlog.txt <type hex>`.

## Gotchas found

* A hit box is a pool C record that is cleared in the frame it is created: use the `S`/`H` taps, not the pool C log.
* `CB_HP=1` writes P1's health from Lua; the tap ignores those writes (`inlua`), and the `H` lines with writer PC `$f76e` are body contact, `$fc9e` hit boxes, `$d442`/`$d544` the player's throw landing.
* A scroll poke that is applied every frame (`CB_HOLDSCROLL`, `CB_FOLLOW`) prevents the list A spawner from seeing triggers beyond it; `CB_FOLLOW` also makes enemies spawned to the left of the camera vanish.
* Pool B types `$45-$47` block list A spawns while on screen (`$2b238`); `CB_PTRB=...:6d5a2` skips the level 5 list B.
* `CB_SPAWN` of `$4d` must use its script position (y `$1a0`, scroll y `$100`): its states hard-code the lane `$1c0`.
