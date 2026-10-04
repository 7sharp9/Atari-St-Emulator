# py/systems: Black Tiger systems scripts

Run from `M68000/` with `source .venv/bin/activate`; paths come from `btcommon.py` (`M68000_ROOT`, `BT_WORK`; data under
`$BT_WORK/agents/systems/`). Every script sets `ATARI_NOTRACE=1`.

| script | what it proves / does | expected output | runtime |
|---|---|---|---|
| `btcommon.py` | paths, `run_repl`, `level_snap`, level-exit and shop cells parsed from `agents/mechanics/special_items.txt` | (library) | - |
| `gates.py all` | eight gates for `system.md`: container offset `a-$c228`, BTSND header, demo stream 65/65/65, Timer A title 5348/5348/5348 and 0 in play, 49/49 five-VBL frames, copy-protection stub | all lines `PASS` | about 1 min |
| `drive_levels.py [n] [wait]` | built-in level skip: no pokes, snapshots `lvl1..7.snap` (level indexes 1..7) and the GEMDOS Fopen/Fread list | 13 Fopen lines (`1`..`7`, `t2`..`t7`); two runs `cmp`-identical | 40 s |
| `drive_boss.py [0-7] [fight]` | labelled hero-position poke onto the level-exit cell; `boss<L>_trigger/_fight.snap/.png`, `boss/boss_table.txt` | `$1eeb8`=1 on all 8 levels (30,000 to 90,000 steps); 16 snapshots identical on a second run | about 5 min |
| `drive_shop.py [level] [index] [steps]` | labelled poke onto a kind-$11 shop-man cell; shop screen `$f690` | `$ea7c` 1/1 at 1,402,480 steps, `$f690` 1/1 at 1,436,161, `shop0_0.snap` identical on rerun | 30 s |
| `drive_ending.py` | labelled "boss killed" poke on level index 7; `end1/end2/endprompt/endafter` | Fopen `bt5` ($1504 bytes), disk-A prompt, `btspr`, `bt4`, `BT000.pi1`; identical on rerun | 2 min |
| `evt_stats.py`, `evt_frame.py`, `frame_census.py` | call/interrupt/trap census and one-frame call tree from an `ATARI_TRACE_EVENTS` log | see `system.md` section 6 | seconds |
| `sheet.py out.png in...` | labelled contact sheet | PNG | - |

Boss/shop/ending table: `$BT_WORK/agents/systems/boss/README.md`.
