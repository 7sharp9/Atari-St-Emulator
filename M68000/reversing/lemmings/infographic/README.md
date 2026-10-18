# Inside Lemmings infographic

`gather.py` turns the `py/skilldrive.py` runs (output under `scratchpad/lemmings/blk/<run>/frames.txt`, plus the
blocker trajectories `outB.txt`/`outC.txt`) into `data.json`; `template.html` is the page, with `/*DATA*/` replaced by
that JSON. Run from `M68000/`: `python3 reversing/lemmings/infographic/gather.py` (it reads and writes under
`scratchpad/lemmings/`), then substitute the data into the template. Published as an artifact.

## Keeping it current

The page is a point-in-time rendering of `mechanics.md`: its plate text, the state-bit list and the proven/read
labels are written by hand in `template.html`, and its data comes from runs under `scratchpad/lemmings/blk/`, which
are not committed. When a skill, a bit role or a collision claim changes, edit the matching plate, regenerate the
data (re-run the `skilldrive.py` command for that skill, then `gather.py`) and republish the artifact (URL below) with
the same file path so the link survives. A future step is to make the page build entirely locally: `gather.py` writing
`inside_lemmings.html` itself, with the run commands in one script, so no hand step sits between a run and the page.

Published: https://claude.ai/artifact/3M9FDun4B75R8QL7mofGaC (private; share from the page's Share menu).
