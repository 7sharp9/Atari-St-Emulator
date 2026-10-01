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
| `terrain.py <ram> x0 x1 y0 y1` | the `$438ee` terrain-type plane for a cell window (type 0 = water) with entities marked: explains a `$48` obstacle-avoidance stall |
| `rel.py <ram>...` | each side's `assess` relation bytes (`$580a6 + 32*side`), the `$33b0` attitude term |
