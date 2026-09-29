# impossamole scripts

Working data lives in `M68000/scratchpad/impossamole/` (gitignored); scripts here are the ones worth re-running.
Run from `M68000/` with `ATARI_NOTRACE=1`; `resume ... repl` needs `--disk-a` every time. The REPL stops reading at
the first unknown line, so `.repl` files hold commands only (no `#` comments).

| script | start snapshot | what it does |
|---|---|---|
| `twintree_item_route.repl` | `scratchpad/impossamole/gameplay_explore/pass96_doublejump_v2.snap` | Walks left to the ledge foot, hops up+right onto the step, hops up+left at the item, sampling slot 0 (`$1a2ea`), the hero (`$1a572`) and health (`$bb74`) every 50,000 steps. Expected output: three sample triples, hero `(152,109)`, `(148,97)`, `(144,91)`, health `01`, slot 0 `type` `1`,`1`,`0`. Reproduced identically twice (98th pass). |

```
cd M68000 && ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume \
  scratchpad/impossamole/gameplay_explore/pass96_doublejump_v2.snap repl \
  --disk-a "scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st" \
  < reversing/impossamole/py/twintree_item_route.repl
```

| script | what it does |
|---|---|
| `level_map.py <snap> <out.png> [--rooms] [--raw] [--x0 --x1 --scale]` | Renders the whole 1680x24 tile map (`$31800`) coloured by the `$25000` category; `--rooms` overlays room boundaries and exit triggers from `$c028`/`$e0aa`. Any snapshot in a world works: the map and tables are resident. Needs `uv run` (PIL). |
| `level_rooms.py <snap>` | Prints the current world's room graph (start room, every top/bottom exit with destination room and hero block-x). |
| `spawn_list.py <snap>` | Decodes the 256-record spawn list at `$27200` (column, y, type, allocator kind, descriptor, containing rooms). |
| `level_rooms.py <snap> --route S E` | Shortest exit sequence from the start room to a room containing blocks `S..E` (the boss room is `318 326`). |
| `boss_kill.py <snap> [pulses]` | Drives the boss fight with a live REPL: health poked full, real fire pulses, shot placed on the boss only while it is in its open animation. Needs `ATARI_NOTRACE=1`-style REPL access (it sets it) and the DLL in `bin/`. From `scratchpad/impossamole/pass99/boss_dead.snap` it took the boss from 16 hit points to 0 in about 20 pulses. |

