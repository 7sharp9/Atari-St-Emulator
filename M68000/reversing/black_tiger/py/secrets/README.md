# py/secrets

Run from `M68000/` with `ATARI_NOTRACE=1` and the venv. Inputs under `$BT_WORK` (default `scratchpad/black_tiger`: `play_start.snap`,
`agents/systems/lvl*.snap`, `agents/systems/cmd_play.asm`, `agents/graphics/png/level_N_map.png`, `files/`); outputs under `$BT_WORK/agents/secrets/`.
Repo root: `M68000_ROOT` or the enclosing `M68000` directory.

| script | what it proves | expected output | runtime |
|---|---|---|---|
| `run_all.py [name...]` | runs each drive twice from its start snapshot and compares md5: `door_in`, `door_out`, `checkpoint`(+`_control`), `levelskip`(+`_control_nojoy`), `pause`(+`_control`), `ending`; logs in `drive/<name>_N.log` hold the `m` / `hits` readings quoted in `secrets.md` | 9 lines ending `IDENTICAL` | about 1 min |
| `reach.py` | reachability census of the code area `$c470..$10786` from the whole-image listing (direct flow, plus roots from every 4-byte literal in the text segment) | `instructions 4306 tierA 2719 tierB 4192 unreached 114`, then the unreached ranges | seconds |
| `rootlits.py` | which literal locations root the table-reached routines | list of `addr <- literal at ...` | seconds |
| `strrefs.py` | literal references to every string in `$17200..$17d00` | `refs=NONE` only for `$17315` ("Black Tiger 1 Feb 90") | seconds |
| `anchors.py` | anchors A/B/C, doors and exit per level from the map files | 8 lines; files 6, 7 have no `$1b/$1c/$3e` | seconds |
| `secrets_map.py [n...]` | overlays the invisible markers on the graphics agent's level renders (`map_L<n>.png`) | colours in the docstring | seconds |
| `drive_trainer_T.txt` | trainer T path: REPL script for `d2b.snap` (poke `w c658 60144e71`), ends with `$1f002`=`$3800`, `$1f00c`=`$03e8` | log lines `38 00`, `03 e8` | about 60 s |
| `drive_ending.txt` | ending sequence from `agents/systems/lvl7.snap` (poke `w 1eeb8 00010000`), snapshots at each text page | `end_p*.snap` | seconds |
| `skull.txt` | Spinning Skull: from `agents/systems/lvl2.snap`, wake the skull at `$1f0d0`, break at `$e47e`, then `s 4` lands at `$e50e` | PC `$e50e` for A3=`$1f0d0` | seconds |
