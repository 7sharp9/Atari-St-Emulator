# Super Sprint: handoff

Updated 2026-10-17 by the session that ended at commit `81af442`.

## Resume point

- Last commit of this workstream: `81af442` supersprint: round 2 (docs, promoted scripts, PNGs). Emulator fix `6a1d544` (MFP IERA/IERB write clears the latched pending slot) is on master and built into `bin/`.
- Working data: `M68000/scratchpad/supersprint/` (rebuild recipe: `reversing/supersprint/py/README.md`, "Rebuild the work directory"). Round-2 agent scratch and reports (`report.md`, condensed) are under `agents/{unused,fragile,livetests,collide,residual}/`; snapshots in `agents/*/snap`.
- Start from: `scratchpad/supersprint/ss_prep.snap` (live Track-1 race just started, one joystick player joined; `sscfg.SNAP_RACE`). `agents/tracks/snaps/race_0..7.snap` are paused at `$beb2` inside `$be40`: run about 3M more steps before sampling a race.
- Uncommitted work left behind: none from this workstream.

## Proven so far

Detail and scripts in `reversing/supersprint/{mechanics,tracks,graphics,sound,secrets}.md` (each ends with a proof table) and `py/README.md` (areas table, one row per directory incl. the round-2 `collide/ livetests/ residual/ unused/`).

- Round 1: car model 700/700 frames; drone AI 576/576; winner's circle 46/46; all 8 tracks rebuilt exactly; 20 blitters; Timer D tracker 7200/7200.
- Prepare-screen crash: an emulator bug (MFP pending latch survived an IER disable, Timer B taken into the junk `$120` at the `$f956` Supexec). Fixed in `6a1d544`; ten key-phase offsets reach `$df18`, held ESC 6.25M vs 9.74M steps (`secrets.md`).
- Collision on all 8 tracks matches live play (700/700 random, 1500 and 2500 chase, R=8/17 with signs) once the gate animator `$aa60`, the sign group `$b24e` (solid in plane 1) and the race-end freeze are ported; plane 2 records decoded 512000/512000 (`py/collide/`).
- Gates: route 3 = open, 2 = closed, a lane hop; 40/40 natural, 7/7 flip A/B; a drone can be trapped at a closed gate (T5, 267 frames). A human leading changes nothing in the drones (0 cap writes, 3000/3000 drone-frames) (`py/livetests/`).
- Economy: per-car 6-digit score exists (+10/64 frames, pickups, bars; shop item 3 pays +3000, its level has no consumer); wrench cost 4, gate `> 3`, one item per visit; race counter +1 on a human win, drone win nets 0 (8/8); hazard rules 1400/1400 over 50 seeds.
- HUD: lap panel `$158ea` and the whole band pixel-exact; the leader's panel blinks (240/240); race-end phase pseudocoded with live counts; smoke `$afc6` ported (`py/residual/`).
- All seven "unused" `SUPER.DAT` blocks are consumed (select, shop, tracks 5-8 start, crash helicopter, winner's circle); real unread bytes are zero pads; the green human car is drawn only in the attract demo (`py/unused/`).
- Unused tune 906 runs 64.49 s (waits hold w+1 steps), register stream 15559/15559 ISR ticks; `-150/-148` are protection flags (`sound.md`, `secrets.md`).

## Open, in priority order

1. **Drive a human that actually leads** (steering bot), not poked counters; run the drone A/B on a full lap. Proof: `py/livetests/lead_ab.py` extended with a bot arm; drones equal to a control in every frame.
2. **Score to hi-score hand-off**: trace `$17b32-$17ccc` to `-7956(A4)`; `$174a6` clears slot 1's score after the winner's circle, so check whether "entry needs a non-drone with a non-zero score" (`secrets.md`) holds in a real session end; also prove the `SSPRINT.HSC` save now that bin is fixed (emulator may not persist disk writes).
3. **Unported race pieces**: spawn/expiry `$abd4`/`$ae0e` (wrench and bonus cells, RNG), tornado position `$b100`, banner/ramp `$b36a`/`$b5f8`, smoke spawn condition `$a65c` and status bit `$800`.
4. **Undecoded SUPER1.DAT chunks**: `0x2e5e-0x2ee0`, `0x38e0-0x3a98`, `0x3d60-0x4280`; the "never read" claim for that range is round 1's, re-poison it with a snapshot taken before boot-time consumers.
5. **Coverage not yet run**: natural (unforced) crashes, spin-outs, hazards and pickups on every track for the helicopter sheets; 2- and 3-human winner's circle; anim 3 frame 15; slot-3 word `-3954[3]` reading 1 in every race.
6. **Audible game**: Timer D delivery in the emulator (regression net; message live sessions before building). Rendered tune WAVs exist only as scratchpad.
7. Gate-trap frequency over full races and its effect on `sim_lap` T5 lap times.

## Known traps

- The emulator never raises Timer D: the game is silent; sound proofs use the tick injection in `py/engine/psg_capture.py` (`py/residual/liveproof.py`).
- Re-driving the same input from a snapshot is deterministic, but two cold-boot drives of one track differ in bytes: compare behaviour, not snapshot bytes.
- `ss_attract.snap` takes about 75 s; a race plus results about 20M steps; a same-snapshot scancode scan 2-3 minutes per screen.
- Scripts write scratch under `scratchpad/supersprint/agents/<area>/`; promoted ones derive paths from `sscfg.py`.
- Slot labels: 0 blue (keyboard), 1 red (joystick 0), 2 yellow (joystick 1), 3 green, a drone in real races.
- Round-1 "never consumed" and "key X crashes the prepare screen" findings are suspect unless re-checked after `6a1d544` and with a before-consumer snapshot.
- Condensed agent reports are in `scratchpad/supersprint/agents/<area>/report.md` (untracked); their contradiction lists are already folded into the docs.

## Next session

Take open item 1 (a bot-driven lead) and item 2 (score to hi-score, real session end, save). Both are same-snapshot A/Bs on the existing harness (`py/livetests/`, `py/ai_econ/`). Then item 3 if a complete game model is wanted. The prompt that starts it is `/resume supersprint`.
