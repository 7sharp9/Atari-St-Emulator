# Inside Lemmings infographic

`build.sh` rebuilds the page from the emulator in one step (from `M68000/`, with `scratchpad/lemmings/sel.snap` and
`lemmings.st` in place): `runs.sh` re-runs every `py/skilldrive.py` run the plates use plus `py/stepsweep.sh` into
`scratchpad/lemmings/info/runs/`, `blockerarms.py` writes the two blocker arms, and `gather.py` turns them into
`data.json` and substitutes it for `/*DATA*/` in `template.html`, writing `scratchpad/lemmings/info/inside_lemmings.html`.
The eight skill runs and both blocker arms regenerate byte for byte from `sel.snap` (the emulator is deterministic).
`runs.sh` and `py/stepsweep.sh` start all their emulators at once; `JOBS=2 infographic/build.sh` caps them at two when
other sessions share the machine.

## Keeping it current

The plate text, the state-bit list and the driven/read labels are written by hand in `template.html`; only the frames,
the blocker trajectories and the step sweep are data. When a skill, a bit role or a collision claim changes in
`mechanics.md`, edit the matching plate, rebuild, and republish the file with the artifact URL below so the link
survives. The exit and trap table and the trap-busy caption are static text from `py/objdrive.py` and `py/trapbusy.py` runs. Checked only in light mode at a desktop
width; the preview pane renders local files as static light snapshots, so dark mode and phone width are unchecked
(the new step-sweep SVG scales with its panel, so its labels shrink on a phone).

Published: https://claude.ai/artifact/3M9FDun4B75R8QL7mofGaC (private; share from the page's Share menu).
