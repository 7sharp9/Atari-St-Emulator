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
| `engine/` | `rle.py`, `tiles.py`, `cars.py`, `sprites.py`, `hud.py`, `text.py`, `sound_model.py`, `sound_render.py`, `proof_*.py` | `uv run python .../engine/run_proofs.py` (about 130 s; all blit, sound and RNG proofs) |
| `secrets/` | `ssh.py` (a Repl subclass, not the ssh program), `reach.py`, `scan_keys.py`, `f5_winner.py`, `isr_proof.py`, `poison.py`, `bootpoison.py`, `run_all.py` | `python3 .../secrets/run_all.py` (quick proofs); `scan_keys.py <snap> <tag> --steps 3000000 --pre 500000` (expect 4/117 in attract) |

Re-run results when these were promoted: drone_diff 576/576, test_trajectory 700/700, winner_diff 46/46, prove_all (8 tracks exact),
f5_winner (D0 = 5 gives animation 3, 10/10), engine run_proofs (sound 7200/7200). The scripts are as the five analysis agents wrote
them; the ones that only print a table or draw a figure have no count.
