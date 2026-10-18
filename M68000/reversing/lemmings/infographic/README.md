# Inside Lemmings infographic

`gather.py` turns the `py/skilldrive.py` runs (output under `scratchpad/lemmings/blk/<run>/frames.txt`, plus the
blocker trajectories `outB.txt`/`outC.txt`) into `data.json`; `template.html` is the page, with `/*DATA*/` replaced by
that JSON. Run from `M68000/`: `python3 reversing/lemmings/infographic/gather.py` (it reads and writes under
`scratchpad/lemmings/`), then substitute the data into the template. Published as an artifact.
