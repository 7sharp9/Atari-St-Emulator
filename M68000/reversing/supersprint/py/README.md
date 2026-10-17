# Super Sprint reproduction scripts

Run everything from `M68000/`. The game files are commercial and are not in the repo: the scripts read and write the
untracked work directory `scratchpad/supersprint/` (`sscfg.WORK`, override with `SS_WORK`; `SS_DLL` points at a scratch build of the
emulator; `M68000_ROOT` overrides the repo root). Each area keeps its snapshots, logs and PNGs under
`scratchpad/supersprint/agents/<area>/` (`snap/`, `data/`, `png/`, `tmp/`); the committed PNGs are in `../png/`.

## Rebuild the work directory

```
cp "<Super Sprint.zip>" scratchpad/supersprint/ && (cd scratchpad/supersprint && unzip -o "Super Sprint.zip")   # sha256 in ../README.md
python3 tools/extract_disk.py "scratchpad/supersprint/Super Sprint.ST" scratchpad/supersprint/files
python3 tools/prg2img.py scratchpad/supersprint/files/AUTO/SSPRINT.PRG scratchpad/supersprint/ss.img 0xa304
python3 tools/disassemble.py --rom scratchpad/supersprint/ss.img --base 0xa304 --linear 0xa304 40000 > scratchpad/supersprint/ss.asm
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll 40000000 snapshot scratchpad/supersprint/ss_attract.snap \
  --disk-a "scratchpad/supersprint/Super Sprint.ST"                      # about 75 s
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/supersprint/ss_attract.snap repl \
  --disk-a "scratchpad/supersprint/Super Sprint.ST" < reversing/supersprint/py/drive.repl    # about 90 s
```

`drive.repl` produces the anchors that every script starts from (`sscfg.py` names them): `ss_select.snap` (SELECT TRACK),
`ss_prep.snap` (a live Track-1 race, one joystick player joined, just started), `ss_race0.snap` (the winner's circle 20M steps
later). The decompile (`ss.c`) is in `../README.md`, "Decompile". Always run the emulator with `ATARI_NOTRACE=1`; `repl.py`
sets it for its child. Each area has its own snapshot builders (`prerace.py`, `drive_track.py`, `build_snaps.py`) for the
snapshots its proofs need; they run from the anchors.

## Areas

| dir | scripts | headline proof (run from `M68000/`) |
|---|---|---|
| `physics/` | `ssport.py` (the Python port of the car physics), `pl.py` harness, `test_*.py`, `fuzz_df18.py`, `rebuild_*.py`, `*_trace.py`, figures | `uv run python reversing/supersprint/py/physics/test_trajectory.py 700 3` (700/700 frames); `sh .../physics/run_proofs.sh` runs all (about 10 min) |
| `ai_econ/` | `drone_model.py`, `drone_diff.py`, `upgrade_diff.py`, `coast_diff.py`, `winner_diff.py`, `sim_lap.py`, `watch_caps.py`, `select_track.py`, `hazard_by_R.py` | `python3 .../ai_econ/drone_diff.py --samples 24 --variants 012345` (576/576); `python3 .../ai_econ/prerace.py` first, then `winner_diff.py 40 6` needs `pre_winner.py` (46/46) |
| `tracks/` | `trackdata.py`, `trackrender.py`, `collision.py`, `attrmap.py`, `occlusion.py`, `roadmask.py`, `trackpath.py`, `drive_track.py`, hazard/wrench/gate probes | `uv run python .../tracks/drive_track.py 0 1 2 3 4 5 6 7` then `prove_all.py` (all 8 tracks exact); `render_all.py` writes the PNGs |
| `collide/` | `traj_track.py` (port vs live on any track), `gateanim.py` (`$aa60`, race-end freeze), `signanim.py` (`$b24e`, `$1432e`), `plane2_decode.py`, `leader_fuzz.py`, `leader_hud.py`, `sign_solid.py`, `t6_nojoin.py`, `run_all_tracks.sh`, `summarize.py` | `uv run python .../collide/plane2_decode.py` (512000/512000); `sh .../collide/run_all_tracks.sh 700 3 random 1` then `summarize.py` (all 8 tracks exact); `leader_fuzz.py <snap> 300 1` (300/300) |
| `engine/` | `rle.py`, `tiles.py`, `cars.py`, `sprites.py`, `hud.py`, `text.py`, `sound_model.py`, `sound_render.py`, `proof_*.py` | `uv run python .../engine/run_proofs.py` (about 130 s; all blit, sound and RNG proofs) |
| `residual/` | `tune.py` `liveproof.py` `bugfx.py` (sound), `lap.py` `hud_rebuild.py` `blink.py` (HUD), `smoke.py`, `proof_ring.py`, `proof_flags.py`, `live_raceend.py`; `data/` holds the tune note and register logs | `bash .../residual/run_all.sh` (about 10 min; `liveproof.py` Q 15559/15560, J 1187/1187, M 125/125; `proof_lap.py` 60/60; `proof_blink_sweep.py 0 1 2` 240/240 snapshots) |
| `secrets/` | `ssh.py` (a Repl subclass, not the ssh program), `reach.py`, `scan_keys.py`, `f5_winner.py`, `isr_proof.py`, `poison.py`, `bootpoison.py`, `run_all.py` | `python3 .../secrets/run_all.py` (quick proofs); `scan_keys.py <snap> <tag> --steps 3000000 --pre 500000` (expect 4/117 in attract) |
| `unused/` | `flow.py` (A/B poison harness), `scan.py`, `drive_pre.py`, `drive_pre_n.py`, `census_*.py`, `heli_flows.py`, `poison_rows.py`, `render_*.py`, `tile_usage.py`, `overlap.py`, `run_all.sh` | `.venv/bin/python .../unused/scan.py race_start_t5 pre_5.snap 's 3000000;!dump'` (after `unused/drive_pre.py 5`; expect `f400 f800 fc00 1b000 1b400 1b800`); `sh .../unused/run_all.sh` runs all (about 25 min); PNGs in `../png/unused/` |
| `livetests/` | `lead_ab.py`+`lead_cmp.py`, `gate_nat.py`+`gate_nat_an.py`, `gate_ab.py`, `gate_geom.py`, `wrench_ab.py`, `shop_wrench.py`, `shop_score.py`, `items_ab.py`, `r_inc.py`, `hazard_seeds.py`, `demo_caps.py` | `python3 .../livetests/r_inc.py` (8/8); `hazard_seeds.py 50` (1400/1400); `lead_ab.py <ctl\|pos> 12000000 0 9000000` then `lead_cmp.py` (3000/3000 drone-frames identical); `gate_ab.py 4 1271 2 5 220` (nat traps, flip and hold do not). Needs `ai_econ/prerace.py` first. The tracks agent's `race_N.snap` are paused at `$beb2` inside `$be40`: run about 3M more steps before sampling a race (`gate_nat.py` does) |

`physics/rebuild_planes02.py` is superseded by `collide/plane2_decode.py` (its 7583 cleared pixels were the decode's 6793 plus 790 HUD digit stamps); it is kept unchanged.

Re-run results when these were promoted: drone_diff 576/576, test_trajectory 700/700, winner_diff 46/46, prove_all (8 tracks exact),
f5_winner (D0 = 5 gives animation 3, 10/10), engine run_proofs (sound 7200/7200). The scripts are as the five analysis agents wrote
them; the ones that only print a table or draw a figure have no count.
