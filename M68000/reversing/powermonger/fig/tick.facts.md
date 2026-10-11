# Facts behind `tick.svg` (generator `py/build_tick.py`)

| label | source |
|---|---|
| call order `$13026` pause, `$1302e` sim clock `$2df70`, `$13034` master tick `$4bb3e`, `$1303a` running gate, `$127e6`, `$6522`, `$d322`, `$3e06`, divider `$57ff0/$57fee`, `$1870`, `$12ce0`, `$178ae`, `$f898`, `$1abaa`, `$17878`, `$165b2`, `$14b62`, `$6a3a`, `$7a56`, `$130d4`, `$d23a`, `$7202` | strategy.md "Where it runs" listing (code read) |
| running gate reads `46($14e20)` = `$14e4e` | strategy.md listing; ai.md "The simulation tick" |
| `$57fee` = 1 at normal speed | strategy.md "Where the calls sit" |
| 13 ticks per 250 VBLs, ~2.6 Hz, ~19 VBLs of instructions per tick; `$6522/$d322/$3e06/$6a3a` 13 each, `$14b62` 14 | strategy.md "Measured cadence" (live, 3M-instruction trace) |
| about 200k to 230k steps per tick | ai.md `$2a` note ("about 200k steps per tick"); economy.md 2b/3a (`$57fec` / `$1abaa` calls, ~231k steps each, once per tick) |
| `$3e06` runs animals `$4044`, pigeons `$416e`, arrows `$596a`, forest `$4342`, army food | strategy.md listing comment; ai.md animals/pigeons block; economy.md `$4342` heading, section 1 (`$3f6a`) |
| iterator prologue `$14b62..$14bb0`, byte 5 gate, anim-frame rule, D6/D7, jump | ai.md "The iterator" listing |
| `$1623c`: count `18` down from `$a0`, then byte 6 `$0a` or `$20` | ai.md iterator epilogue table and `$5590` outcomes |
| epilogues `$161c4`, `$16202`, `$16228`, `$1622c` | ai.md epilogue table |
| record array `$51b66`, stride `$32`, slots 1..511, end `$57f66` | ai.md object record heading; `$1622c` row |
| handler block `$14c48..$1620e` | ai.md "every valid entry ... resolves inside the handler block" |
| pools: animals `$4ccd6` 40 x 20; pigeons `$4c112..$4c5f2` 48 x 26; arrows `$4be00..$4c110` 49 x 16; trees `$4d252` stride 12; forest markers `$4c5f4` stride 22; buckets `$47970` | ai.md shepherds/animals/pigeons block and `pm_effect`; economy.md section 2 headings |
| ~50 of 511 slots active, ~26 reach a handler per tick | ai.md iterator section (mission-1 settled view) |
| proven counts: 675/675, 1335/1335, `$1623c` 275/275, animals/pigeons 45094/45094, arrows 4210/4210, `$4342` 8/9 | pm_fsm_ref index; ai.md Proven blocks |

Evidence colours: proven = gated routines; live = the four routines counted in the trace; code read = the rest of the call listing.

## Flags

- The assignment names the iterator `$1622c`. The code and ai.md: the iterator is `$14b62`; `$1622c` is its loop tail (next record).
- README "The simulation: entities, scheduler, combat" says every man, boat, **animal, projectile** and pending order is a 50-byte object record. ai.md (scope, "What the loop actually is", the animals/pigeons block) says animals (`$4ccd6`), arrows (`$4be00`) and pigeons (`$4c112`) are separate pools moved by `$3e06`. The figure follows ai.md. README needs the correction.
- Steps per tick is quoted as "about 200k" (ai.md `$2a`), "~216k" (ai.md `$34` watch) and "~231k" (economy.md, `$1abaa` period / 512). Not contradictory (different lands and phases), but no doc states the range; the figure says 200k to 230k.
