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
