# Carrier Command infographics

One explanatory figure per algorithm, computed from the proven model or the game's own captured values, as blog
material (`7sharp9.github.io/IDEAS.md` entry 9). Each `gen_*.py` writes `<name>.svg` to
`scratchpad/carrier/infographics/` and prints every number it draws; `<name>.facts.md` maps each fact in the
figure to its doc section or computation and flags what the work found wrong or unclear in the docs.
PNG: `cd M68000/scratchpad/carrier/infographics && rsvg-convert -z 2 <name>.svg -o <name>.png`.
Run from `M68000/` with `uv run python reversing/carriercommand/py/infographics/<script>`. Each figure opens with a
lead paragraph, gives every panel a "How to read" and "Takeaway" caption and ends with a "How we know" strip;
`igtext.py` wraps that prose (Helvetica metrics via PIL). The prose's sources are in each facts file's "Prose added"
table.

| Figure | Script | Doc | Evidence it computes or re-runs |
|---|---|---|---|
| An arctangent from one table | `gen_atan.py` | `vehicles.md` 2 | error from the port (529/529 grid); worst 27 units, table 13.7, -32768 bug in 27/529 |
| Packets that route themselves | `gen_routing.py [drive]` | `economy.md` 3, 4 | `drive` re-runs the emulator (about 5 min): matrix 41/41 and 129/129 dumps, hops 14/14 twice |
| BSP trees in 1988 | `gen_bsp.py`; `bsp_order_all.sh` first | `render.md` 4, 6 | draw order 1264/1264 draws of 6 models (`bsp_order.py`, `bsp_order_sum.py`; `bsp_survey.py`, `bsp_which.py` probes) |
| A filler that rewrites itself per colour | `gen_span.py [--emu]` | `render.md` 5 | patch bytes 64/64, rows 2183/2183 (control 531/2183); cache `span_emu.json` |
| Distance without a multiply | `gen_octdist.py` | `ai.md` 1, 2 | 11.8% worst; scores 64/64 on `ai/nat/d1`; picks 11/11 on `ai/nat2` |
| Taking off from a moving deck | `gen_takeoff.py` | `vehicles.md` 5 | 42/42 twice, 43/43 with the launch tick (stserver) |
| Backwards in-place depack | `gen_depack.py` | `packer.md` | output sha256, live margin 219 (control 220 corrupts 5 bytes), ratios (needs lz4, gzip, zstd, xz) |
