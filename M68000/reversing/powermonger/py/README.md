# PowerMonger working scripts

Run everything from `M68000/`. Shell scripts write under `$PM_WORK` (default
`scratchpad/pmwork`, gitignored). Snapshots need the Replicants disk
`scratchpad/powermonger.st`, which the scripts mount.

| script | what it does |
|--------|--------------|
| `build_land.sh <k> [steps] [season]` | builds land `k` (0-143) from `pm67_ok_pre.snap` through the briefing-OK poke, optionally in season 0-3, settles, snaps at `$f898`, prints the census (`../README.md` "Driving a later land") |
| `s40_symbols.py [disk.st] [ram.snap]` | unpacks `DATA\SPRITE40.DAT` from the disk image (the developer build with its linker symbols), checks its text against a RAM snapshot (28,936 of 28,942 windows at offset `$10a6`) and writes `../powermonger_orig.sym` (`../strategy.md` "Original names") |
| `job_census.py [snap...]` | job (soldier, farmer, merchant, fisher, shepherd, leader) of every live man per entity mode: `$56..$62` are all fishers, `$4e..$54` all merchants (`../strategy.md` "Original names") |
| `tree_census.py <snap>... \| --chain [glob]` | `$4d252` is the tree array: every live entry sits on a byte6 4 (tree/building frame) record, none on byte6 8 (animals); `--chain` lists the jobs of the men in the gather modes `$3e/$40/$42/$44/$46/$6a` over all snapshots (`../economy.md` section 2) |
| `join08_run.sh <name> <steps> [w:addr:long ...]` | order `$08` (get men) live from `pm123/win/m1_ready.snap` (conquered lord 0's town, 5 side-1 men): arm icon, click the town, run to the lead's arrival, count the join path (`$15122`, `$34f2`, `$1501a`, `$15282`, `$1b2a`, `$1d70`, `$3c08`, `$35f4`) and dump lead/group/lord/recruits before and after; helpers `join08_cmds.py`, `join08_watch.py`, `join08_report.py`; poke `w:516fc:000p0000` sets the posture (`../strategy.md` "What each order does") |
| `health_check.py <snap>...` | byte 45 is health: 11 of 11 live `callcap $912a` calls return the `healthnames` string for the poked `(45 >> 4) & 7` ("Dead" for byte 5 < 0), and 203 of 225 live persons over three snapshots sit exactly on their `$5ccc` job cap (`../strategy.md` "Original names", ai.md `$5c80`) |
| `alts_render_check.py [snap]` | `$3f86c` is the terrain altitude plane (the colour planes `0`/`-8257` are slope shades derived from it, `../graphics.md`): poking 39 longwords under the camera raises a plateau, 10938 pixels differ against the same forced `$f898`/`$fec6` redraw without the poke (`../economy.md` section 5, `../graphics.md`) |
| `plane_ab.py [snap]` | poke-and-render A/B of the other `$438ee` planes under the camera (same forced `$f898` redraw as `alts_render_check.py`): the `-8257` and `0` colour planes change the tone of single triangles (2236 / 2124 pixels), the altitude plane a plateau (10938), geometry only for the altitude plane (`../graphics.md`) |
| `flag_census.py <snap>...` | the four `$438ee` planes (altitude `-16514`, colour B `-8257`, colour A `0`, flags `+8257`): flag-bit counts, bit 1 against the settlement claim sets (m1_s0 28 of 28 inside, k5_s4 232 of 506 outside), colour histograms (0 = open sea) |
| `mode_census.py <snap>...` | live men in modes `$12`/`$34`/`$36` (+`$10`): count, previous-mode byte, job, dwell (`$12`: prev `$58`/`$42`/`$44`; `$34` seen in 274 snapshots, `$36` never; `../ai.md` mode table) |
| `troops_audit.py <snap>...` | `troops_field` against the live men of each lord by home settlement (`34(man)` → `$4f916+14`) with byte-7 bit 6 clear: 416 lord instances over 33 snapshots, 378 exact, 416 within 1 (`V=-v` per lord; `../economy.md` section 1) |
| `probe42be.py <snap> land\|launch <n>` | stops at the n-th pigeon landing (`$4244`/`$42c8`) or launch (`$16336`/`$16372`) and dumps the pigeon record, entity table, lords and settlements to `scratchpad/probe42be/` |
| `pigeon_ledger.py <land.json>...` | each lord's `troops_field` against the live-man rule before and after a pigeon landing: exact for every lord, only the home lord's `+1` changes (5 of 5 landings, `../economy.md` section 1) |
| `troops_rule.py <snap>...` | `troops_field` against three candidate rules per lord: bit 6 clear (C), minus leader-flag men (A), A plus leader-flag men with `42(man) == 0` (D): D exact 2280 of 2280 over the game snapshots (the 242 misses are pre-game map snapshots with garbage tables), A 2136, C 1406 (`../economy.md` section 1) |
| `merch_census.py <snap>...` | merchants (modes `$4e..$54`, all job 2): mode, prev, dwell, `46` (destination lord) against the home lord: 404 of 404 `$52/$50` men have 46 equal to the home lord (`../ai.md` `$52`/`$54` rows) |
| `gate_equip.py [substr] [reuse]` | differential gate of `pm_fsm_ref.call_160f8`/`call_160e4`/`call_160f2`/`call_16892(D2)` (the equipment exchange incl. the stale-D0 credit) against `callcap`: 201 states (48 natural, 135 synthetic, 8 stubs, 10 `$16892`), 385/385 tracked bytes, D0.w/D1.w 201/201; the man is copied onto record slot 511 so the tail's `bra $1622c` returns (`../economy.md` section 3) |
| `doc_coverage.py [--min N] [--out file]` | the developer-named routines (`powermonger_orig.sym`) whose addresses no doc, script or port file mentions: totals, the largest by size, bytes per 4 KB page (29498 bytes unmentioned before the 139th pass, 28632 after; most of the rest is data). Read the first lines of a hit before calling it code |
| `gate_jobs.py [substr]` | differential gate of `call_2a98` (the job pick) and its arms `call_2b08`/`call_2b68`/`call_2c5a`/`call_2d0e`/`call_2e1e` against `callcap 2a98`: **3310/3310** tracked bytes and D0 over 146 states (70 natural entries of land 0's build, synthetic RNG seeds, full pools, a leader, D1 over `$80`); corpus recipe in the docstring (`../economy.md` 5a) |
| `gate_pop.py [substr]` | differential gate of the whole `call_2984` (the world-build population) against `callcap 2984` on the build of lands 0, 1, 5, 10, 25, 60, 100, 142: **29860/29860** tracked bytes over 1026 men |
| `pop_census.py <ram>...` | the model's census of one land's starting population: men by job, free field sites before and after, animals, catch markers, why each merchant is one, stale-D1 farmer failures (1234 of 1234); the table in `../economy.md` 5a |
| `town_layouts.py [snap-or-ram]` | the building names (`housenam`, `$a15a`) and the six town layouts `$2eac`/`$2fc0` place a lord's buildings from (`$3078`), each as records and a picture (`../economy.md` "Buildings and town layouts") |
| `build_series.py <k> [count] [step] [out]` | builds land `k`, waits for `$2984` to return, then snapshots every `step` steps: the time series `gate_shepherd.py` and `gate_animals.py` read |
| `gate_shepherd.py [substr]` | differential gate of the shepherd modes `$80`/`$82`/`$84`/`$86`/`$88` (`pm_fsm_ref.h_mode80..88`, in `reconstruct`) against `callcap 14b62` with one record live: **1043/1043** tracked bytes over 198 states (natural shepherds of two lands plus synthetic `$88`/`$82`/arrival/none/no-chain) (`../ai.md` "Shepherds, animals and carrier pigeons") |
| `gate_animals.py [substr]` | differential gate of `call_animals` and `call_pigeons` (moves, re-steers, the `$41dc` arrival's bucket effect) against `callcap 3e06`, comparing the animal pool and the bucket chains of the cells touched: **45094/45094** over 55 snapshots (5 with a live projectile excluded: `$596a` is not modelled) |
| `export_equip_corpus.py [out.json]` | writes the `gate_equip.py` states with the real callcap results (and the native e1/e2 exchange) as JSON for the F# port's gate (`scratchpad/pm138/equip_corpus.json`) |
| `equip_check.fsx [corpus.json]` | `dotnet fsi` gate for `port/godot/logic/Equipment.fs`: `Original` against the real 68000 on 202 cases (bytes and D0.w/D1.w), `Corrected` by properties (equal to `Original` for lord < 8, only the own lord's goods change, goods plus items held conserved); needs `dotnet build` of `PmLogic.fsproj` first |
| `equip_census.py <snap>...` | farmers carrying the Plough (byte 33 `== 8`), men by weapon byte 44 and each lord's `goods[]`: the census behind the equipment exchange `$160f8` (`../economy.md` section 3) |
| `season_tilediff.py <ram>...` | live tileset `[$ff9e]+3712` against the three season source tilesets (`$1aba2`): 0 pixels differ from summer at count 118/489, half summer half autumn at 255, 79 from the new art at 496 (`../strategy.md` "What `$1abaa` actually is") |
| `family_distinct.py [snap]` | the 27-frame prop sheet `$37c7c`: each `{r7, r7+3, r7+6, r7+9}` family has four different pictures (12 of 12 on `k5_s4`); the terrain tables are the ones with three distinct sets (`../economy.md` "Reading") |
| `group_states.py <snap>...` | group state (+0), men (-24) of every live group of sides 1..5: the player's group is state 6 (idle) in 6 of 6 snapshots, AI groups 3 (get men) or 8 (march and engage) (`../strategy.md` pseudocode `IDLE`) |
| `census_8a.py` | men in mode `$8a` over the snapshots: 660 of 661 have byte 7 `== $10` (the captain at rest, `../ai.md` `$8a` row) |
| `townmen.py <ram> [lord...]` | each lord's house chain as `$34f2` walks it: every townsman's side, flags, mode, arrival mode, dwell and `46`, plus the selected group and its lead |
| `s40_orphans.py [ram] [listing]` | routine starts of `powermonger_orig.sym` that no operand, literal pointer, relative word or table word names: 978 starts, 97 direct orphans, 14 after the table scan |
| `census.py <snap-or-ram>...` | byte6 histogram of the whole-map `$47970` bucket walk (what `$115e0` can draw), season and world parameters |
| `recs.py <snap> <b6,b6,...>` | every render record of those categories: address, cell, first 34 bytes |
| `capture.sh <snap> <name> <cx> <cy> <n> [settle] [yaw]` | pokes the camera centre, settles, snapshots `n` consecutive `$f898` frames and dumps each (`dump_frame.py`) |
| `dump_frame.py <ram> <json>` | one captured frame's inputs + the game's screen, for `score.fsx` |
| `score.fsx a.json+b.json ...` | port frame from state `a` vs the game's screen in `b` (the next frame), at all 4 water ticks, per category; `PLACE=<b6>` prints blits, `PORT_OUT=<bin>` writes the port frame, `NO_WEATHER=1` |
| `sbs.py <port.bin> <json> <png> x0 y0 x1 y1` | game / port / diff side by side |
| `view.py <json> <png>` | the game's screen from a frame dump; `frames.py <png> <hex>...` decodes `$33000` frames |
| `runland.sh <snap> <name> <stretches> <steps>` | runs forward in stretches with the REPL `hits` census over the combat / AI / economy routines (`EXTRA="addr ..."` adds more), a snapshot per stretch |
| `hits_table.py <run-dir> <name>...` | tabulates `runland.sh` output |
| `track.sh <snap> <name> <n> <addr:len>...` | dumps memory ranges at each of `n` consecutive frames |
| `season_check.fsx <ram>...` | `Season.table`/`fading` vs the RAM's `$2e000` table |
| `parity.py <ram> <port.bin>` | `pm_render_ref.py` vs the F# port, pixel for pixel |
| `diff_1623c.py` | the `$1623c` differential-test gate (275/275; corpus in `scratchpad/pm121/corpus_1623c`) |
| `diff_2776.py` | the `$2776` group-dissolve gate (4119/4119 over 28 states; corpus in `scratchpad/pm122/agents/dissolve/`) |
| `diff_5cde.py` | the `$5cde` work-order gate (768/768 over 47 states + returned D2/D3/D4 85/85; corpus in `scratchpad/pm122/agents/herdop/corpus`) |
| `diff_revolt.py` | the `$550e` → `$5c2c` → `$25d6` revolt-chain gate (1778/1778 over 49 states; corpus in `scratchpad/pm122/agents/revolt/`) |
| `diff_4f68.py` | the mode-`$2c` target picker `$4f68` + conquest arm `$539a` → `$550e` gate (1804/1804 over 192 states, 170 natural; corpus in `scratchpad/pm124/conquest/`; `nat` runs the natural states only) |
| `snap2ram.py <snap>...` | writes `<name>.ram` beside each snapshot |
| `dither_atlas.py [out.json]` | rebuilds the terrain frame from (triangle, colour byte, pattern slot) for mission 1 and a coast scene, asserts 0 pixels differ from `pm_render_ref`, asserts the season-fade model reproduces `pm74_late`'s live slots, writes `../dither_atlas.png`, `../dither_triangles.png` and `../dither_infographic.html` (from `dither_infographic.tmpl.html`) |
| `drive_win.sh` | mission 1 (campaign land 0) won with real clicks from `pm67_ok_pre.snap`: sword icon + minimap attack, 50M steps, options → GAME → RETIRE (victory, `$3f2a0[0] := 1`), Continue Conquest, land 1 built; snapshots in `$PM_WORK/win` (strategy.md "How a land ends") |
| `clicks.py <x,y\|home\|cmd>...` | REPL commands for absolute clicks at 320 × 200 (pointer homed with a large negative move, 1:1 after); other tokens pass through with `:` for spaces |
| `iconmap.py <ram>` | the icon floor's hit-test (`$13506`, edges `$12e6a`/`$12ee4`) run over the screen: each `$19bde` icon's slot, id and centre (strategy.md "The player's commands") |
| `panels.py <ram>` | every `$7202` text panel expanded as `$a91a` does, with each button's code D3 |
| `sides.py <ram>` | local side, ratio `$57fce`, `$57fba` totals, the `$4e514` lords, the command slots |
| `order_run.sh <name> <steps> <clicks...>` | one player order from mission 1 settled (`pm123/win/m1_s0.snap`, or `SNAP=`): clicks, runs, snapshots, prints the lords and the selected group; `strategy.md` "What each order does" |
| `group.py <ram> [settl]` | the selected group's fields (state, men, food, posture, carried goods), its lead and roster, food piles; `settl` adds every settlement |
| `shot.sh <snap> <png>` | screenshot from the shifter base (`$ffff8201/03`), macOS-safe form of the old `scratchpad/pmshot.sh` |
| `census_lords.py <ram> start_x start_y [r]` | live entities by owner within `r` of each foreign lord and along the straight corridor from cell (x,y): the target-choice census before sending an envoy (129th) |
| `terrain.py <ram> x0 x1 y0 y1` | the `$438ee` colour plane A for a cell window (colour 0 = open sea) with entities marked: explains a `$48` obstacle-avoidance stall |
| `rel.py <ram>...` | each side's `assess` relation bytes (`$580a6 + 32*side`), the `$33b0` attitude term |
