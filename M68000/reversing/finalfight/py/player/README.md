# Player-side scripts (agent F)

Drive Cody from the saved state `scratchpad/finalfight/ff_enemies.sta`, log the player record every frame, and check the results against numbers derived
from the ROM. Findings are in `../../player.md`. Everything derives the repo root from `__file__` / the script directory. MAME needs a private run
directory (cfg, nvram, states collide between two runs): `FFP_RUN` (default `scratchpad/finalfight/p3/f/run`, must hold `sta/ffightuc/ff_enemies.sta`;
`gates.sh` copies it) and `FFP_OUT` for logs (default `scratchpad/finalfight/p3/f/out`). Both wrappers keep `SDL_VIDEODRIVER=dummy`. Character index: 0 Guy, 1 Cody, 2 Haggar.

Quick start: `sh gates.sh` (about 6 minutes, regenerates every log, prints 19 PASS lines), or `python3 gates.py [combo jump special weapon items grapple thrown kills walk drop death hist life]` on existing logs.

| file | what it is / proves | how to run |
|---|---|---|
| `ffrun.sh`, `ffmame.sh` | MAME wrappers (no debugger / debugger harness) with `FFP_RUN`, `FFP_OUT` | `ffrun.sh <script.lua> [emu seconds]`; `FF_MAMEARGS="-debug -debugger none"` for `pbp.lua` |
| `pdrive.lua` | loads a state, applies a plan and pokes, writes one log line per frame (state, subs, boxes, hp, score, grapple and timer fields) | env `FF_LOAD FF_PLAN FF_POKES FF_N FF_LOG FF_KILL FF_KEEP FF_EHP FF_GOD FF_HEAL FF_EXTRA`, through `run.sh` |
| `ptap.lua`, `pbp.lua` | `pdrive.lua` plus write/read taps with PC (`FF_W`, `FF_R`), or debugger breakpoints that log registers (`FF_BPS=bps/*.lua`) | set `DRV=ptap.lua` or `DRV=pbp.lua` for `run.sh` |
| `run.sh`, `itemrun.sh` | one named run (`run.sh <name> <plan> <frames> [VAR=value]` writes `$FFP_OUT/<name>.txt`); one item pickup run | see `gates.sh` for the invocations |
| `plans/*.lua`, `pokes_*.lua`, `bps/*.lua`, `extra_*.lua` | inputs (frame-relative levels), RAM pokes, breakpoint sets, per-frame extra loggers (enemy records, pools, dummy enemy, prop follower, continue scene) | used by `gates.sh` |
| `gates.sh`, `gates.py` | 19 gates: combo ids, damage, types, scores 4/4; jump attacks 4/4; special 3/3 and cost 1/1; weapons 3/3; item heal and score by type 24/24; grapple strikes, slam, back throw, thrown landing rule 4/4; kill awards by kind 5/5; walk speed 2/2; kill-frame drop 1/1; death 60 frames, lives, blink 179/179; sub-state histogram; extra life | `sh gates.sh` |
| `ffchar.py` | ROM readers: per-character data, attack boxes, damage rows, award codes, strike damage, chain limit, thrown-victim rule | `python3 ffchar.py` prints the per-character constants |
| `boxes.py`, `dmg.py` | attack/hurt box descriptors and damage rows of a character | `boxes.py cody attack 14`, `dmg.py cody 0b` |
| `anim.py` | decodes animation scripts (frame durations, hurt and attack box ids) | `anim.py 12128 121cc 12284` |
| `rdis.py` | recursive-descent listing that does not decode data tables as code, resolves word dispatch tables (`<addr>:<count>` overrides a table size) | `rdis.py a500 f800 a7a6:18 a558 a144` (hex seeds) |
| `tab.py` | prints the targets of a word or long jump table | `tab.py a7a6 18`, `tab.py c3d6 3 l` |
| `seg.py`, `cols.py`, `hits.py`, `hitlog.py`, `b45map.py`, `scdelta.py` | analysis of a `pdrive` log: constant-state segments, selected columns, hit-reaction episodes, damage events on a dummy with the player's state, attack-box ids per sub-state, score changes | `seg.py <log> [st,sub,ss,s5,m66]`, `cols.py <log> <lo> <hi> <step> col,col`, `hitlog.py <log> [record]` |
