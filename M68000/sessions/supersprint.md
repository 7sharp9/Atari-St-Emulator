# Super Sprint: handoff

Updated 2026-10-31 by the session that ended at commit `f2b180c`.

## Resume point

- Last commit of this workstream: `f2b180c` supersprint: bot-driven human lead A/B, real session end and SSPRINT.HSC save, lap records never set from shipped zeros.
- Working data: `M68000/scratchpad/supersprint/` (rebuild recipe: `reversing/supersprint/py/README.md`, "Rebuild the work directory"). It exists on the Mac. Agent scratch and condensed reports are under `agents/<area>/`; this session's outputs are `agents/livetests/data/bot_{ctl,bot}.json`, `bot_bot_end.snap` and `agents/livetests/session_end/`.
- Start from: `scratchpad/supersprint/ss_prep.snap` (live Track-1 race, one joystick player joined; `sscfg.SNAP_RACE`), or `agents/livetests/data/lead_base.snap` (that race +1M steps, human idle at the grid, the base of every `livetests/` A/B and the bot). `agents/livetests/data/bot_bot_end.snap` is race 2 in progress after the bot's race-1 win.
- Uncommitted work left behind: none from this workstream.

## Proven so far

Detail and scripts in `reversing/supersprint/{mechanics,tracks,graphics,sound,secrets}.md` (each ends with a proof table) and `py/README.md` (areas table).

- Round 1: car model 700/700 frames; drone AI 576/576; winner's circle 46/46; all 8 tracks rebuilt exactly; 20 blitters; Timer D tracker 7200/7200.
- Prepare-screen crash was an emulator bug, fixed in `6a1d544` (`secrets.md`).
- Collision on all 8 tracks matches live play (700/700 random, 1500 and 2500 chase); plane 2 decoded 512000/512000 (`py/collide/`).
- Gates: route 3 open / 2 closed, a lane hop, 40/40 natural, 7/7 flip A/B; a drone can be trapped at a closed gate (`py/livetests/`).
- No rubber-banding with a real lead: the steering bot (`livetests/bot.py`) wins Track 1, leads 1151/1277 frames; 0 cap/divisor writes before the finish; the untouched drone equals the control 1277/1277 frames, the other two diverge first on a car-car bump (`livetests/bot_ab.py`, `bot_cmp.py`; `mechanics.md`, "Difficulty").
- Real session end and save: entry screen `$172f0` after every race; natural score 2760 beats no row, `$15ffe` blanks it, the save writes 4 sectors with `SSPRINT.HSC` unchanged; a poked 050000 enters at row 18 (AAA on timeout) and the saved file has exactly that shift (`livetests/session_end.py nat|hi`; `secrets.md`, "High scores").
- Lap records `-8066(A4)` can never be set from the shipped zeros (signed `bge` at `$1aa0a`): store `$1aa2a` 0 calls vs 1 with records poked to `$7fff` (`livetests/lap_record.py`; `mechanics.md`, "Race rules").
- Economy, HUD, unused data, tune 906: as in the round-2 rows of `py/README.md`.

## Running

Nothing running.

## Open, in priority order

1. **Unported race pieces**: spawn/expiry `$abd4`/`$ae0e` (wrench and bonus cells, RNG), tornado position `$b100`, banner/ramp `$b36a`/`$b5f8`, smoke spawn condition `$a65c` and status bit `$800`. Needed for a complete game model; prove each against live frames from `lead_base.snap` as `collide/traj_track.py` does.
2. **Undecoded SUPER1.DAT chunks**: `0x2e5e-0x2ee0`, `0x38e0-0x3a98`, `0x3d60-0x4280`; re-poison with a snapshot taken before boot-time consumers (`unused/flow.py`).
3. **Coverage not yet run**: natural crashes, spin-outs, hazards and pickups on every track; 2- and 3-human winner's circle; anim 3 frame 15; slot-3 word `-3954[3]` reading 1 in every race. `bot.py` now gives a driven human on any track (its path comes from the track's own table; only Track 1 tried).
4. **Audible game**: Timer D delivery in the emulator (regression net; emulator session's worktree, message live sessions before building).
5. Gate-trap frequency over full races and its effect on `sim_lap` T5 lap times; the bot can drive those tracks for a human-present run.
6. A bot-driven multi-race session that earns a table score unpoked (needs > 28730, about 1500 per win): would replace the poke in `session_end.py hi`.

## Known traps

- The emulator never raises Timer D: the game is silent; sound proofs use the tick injection in `py/engine/psg_capture.py`.
- Re-driving the same input from a snapshot is deterministic; two cold-boot drives of one track differ in bytes: compare behaviour.
- `lt.F` keys `qy`/`qx` are swapped names: `-3738` is Q x, `-3746` Q y (live `-3738/8` = screen X). `bot.py` uses offsets.
- The bot's last packet stays latched: send `kbd fe 00` before handing a bot snapshot to an idle run (`session_end.py` does).
- `u <addr>` output is "reached PC=$... after N step(s)" or "gave up after N step(s)"; `hits` lines start with two spaces and `$`.
- Disk writes live only in the snapshot's `DSKA` journal; `session_end.py` applies it to a copy and extracts the file.
- `ss_attract.snap` takes about 75 s; a race plus results about 20M steps; the bot's 2400 frames about 15 s.
- Slot labels: 0 blue (keyboard), 1 red (joystick 0), 2 yellow (joystick 1), 3 green, a drone in real races.

## Waiting on Dave

Nothing.

## Next session

Take open item 1 (unported race pieces) if a complete game model is wanted, using `bot.py` to put a driven human into the
live comparison; otherwise item 3's coverage runs with the bot on Tracks 2-8. Start by checking `bot.py` laps Track 3 or 5
(gates) from a `tracks/` race snapshot. The prompt that starts it is `/resume supersprint`.
