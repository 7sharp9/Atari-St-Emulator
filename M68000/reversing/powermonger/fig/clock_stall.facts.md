# clock_stall.svg: facts and sources

From `reversing/powermonger/strategy.md` unless marked.

| fact in the figure | section |
|---|---|
| `$1302e addq.l #1,$2df70` once per sim tick | Where it runs (the `$13000` listing) |
| stamp `move.w $2df72.l,180(A3)` at `$3720`; `$3728` copies the state (live 1/1) | `$51538` group-order table (rows 256, 268); signed-clock stall evidence |
| compare `$65a0..$65a6`, D0 = `256() + $14`, signed | The commander AI `$6522`, "The signed-clock stall" |
| literal `$2df72` found at two instructions only (`find_field_writers.py`) | "Isolation by clock pokes", Status |
| stamp 2088 (k80) / 2038 (k108); clock 34104 / 34528 reads -31432 / -31008 | "The signed-clock stall", Evidence |
| wait about 34,800 ticks | "The signed-clock stall" |
| k143, k44 do not stall (stamps within 20 ticks) | "The signed-clock stall" |
| pokes: start `L2G_k80_c8.snap`, clock 11729, about 167k steps per tick, stamp + 20 = 2108 | Isolation by clock pokes |
| none 599 (last 99,872,563); `$7ff0` 15 (last 2,346,222); `$7000` 599; `$0800` 541 (first 9,711,010); `$ffe0` 555 (first 357,344,956), budgets 100M / 450M | Isolation by clock pokes (table) |
| `$6522` 604 against 599 in the `$7ff0` run | Isolation by clock pokes |
| W5G: 1500 / 1843 per chunk, then 168 / 93, then 0 (chunks 16..20 k80, 12..20 k108); crossing chunk ends at clock 32599 / 32674 | "The signed-clock stall", Evidence |
| onset 4.5G..4.75G (k108), 5.5G..5.75G (k80); loses decisions for the next 6G or so | "The signed-clock stall" |
| LOAD route (bottom box): a LOAD restores camp stamps, not the clock. `lo.st` into `rand1` (clock 441), stamp 2088, first `$65b4` predicted at clock 2108, about 279.2M steps, observed after 276,745,802 steps (0.9% early), `py/saveload/camp_stamps.py` | "A LOAD is a second way into the stall"; "The loaded camp stamps against the kept clock" |
| panel A shows only `$1302e` and `$13baa`; the copy and compare addresses `$12f6`/`$1352`/`$1373c` are in the `<desc>` | Status paragraph (the clock is the low word of the long `$2df70`) |
| Hatari / real ST not checked | Isolation by clock pokes, Status |

Code read added here (scan of `scratchpad/pm123/win/m1_map.ram` bytes `$0..$40000` for the long literal):
`$2df72` in the instructions at `$3720` and `$65a0`; `$2df70` in the instructions at `$12f6`/`$1352`
(`move.l $2df70,$2df74`), `$1302e` (the tick increment), `$1373c` (`move.l $2df70,D0`, then `cmp.l $2df74,D0`),
`$13baa` (`clr.l $2df70`); these are instruction addresses, not operand addresses. The 2,140-tick and 60-tick wait
figures are the doc's. The chunk-to-step mapping (chunk n covers 2G + (n-1) x 250M ..) is my arithmetic from
"2G + 5G steps, 20 chunks of 250M"; it reproduces the doc's 4.5..4.75G and 5.5..5.75G windows.

## Flags

- `$13baa` (`clr.l $2df70`) is the third instruction of the world-build dispatcher `$13b9a`, whose only call site in the
  image is the briefing-OK path at `$b878`. It ran once in a build from `pm67_ok_pre.snap` and never in the 1134 ticks
  over 200M further steps of that land, nor in the 4093 ticks over 750M steps of `pm142/rand1.snap`. A land clears the
  long clock `$2df70` only at its build; during play it is only incremented (`$1302e`). The count is bounded by those
  windows: a LOAD and the land-end flow were not measured.
- Decisions per 250M-step chunk (`$65b4` hits, `W5G_k80` / `W5G_k108`): 1467..1503 in chunks 1..14 of k80 (chunk 1 is
  1499) and 1836..1851 in chunks 1..10 of k108 (chunk 1 is 1841), so 1500 and 1843 are the chunk-1 values and the
  pre-crossing rate is flat to about 2%, as the figure draws it. `$6522` stays at 1468..1507 / 1838..1866 in every
  chunk, post-stall included. Chunk 15 of k80 re-executed from `W5G_k80_c14.snap` reproduces 1505 / 168.
