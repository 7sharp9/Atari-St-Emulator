# PowerMonger working scripts

Run everything from `M68000/`. Shell scripts write under `$PM_WORK` (default
`scratchpad/pmwork`, gitignored). Snapshots need the Replicants disk
`scratchpad/powermonger.st`, which the scripts mount.

| script | what it does |
|--------|--------------|
| `build_land.sh <k> [steps] [season]` | builds land `k` (0-143) from `pm67_ok_pre.snap` through the briefing-OK poke, optionally in season 0-3, settles, snaps at `$f898`, prints the census (`../README.md` "Driving a later land") |
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
| `snap2ram.py <snap>...` | writes `<name>.ram` beside each snapshot |
