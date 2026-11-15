# Carrier Command infographics

One explanatory figure per algorithm, computed from the proven model or the game's own captured values, as blog
material (`7sharp9.github.io/IDEAS.md` entry 9). Each `gen_*.py` writes `<name>.svg` to
`scratchpad/carrier/infographics/` and prints every number it draws; `<name>.facts.md` maps each fact in the
figure to its doc section or computation and flags what the work found wrong or unclear in the docs.
PNG: `cd M68000/scratchpad/carrier/infographics && rsvg-convert -z 2 <name>.svg -o <name>.png`.
Run from `M68000/` with `uv run python reversing/carriercommand/py/infographics/<script>`. Each figure opens with a
lead paragraph and a key line (addresses are citations; proven, observed, inferred), gives every panel a "How to read" and "Takeaway" caption and ends with a "How we know" strip;
`igtext.py` wraps that prose (Helvetica metrics via PIL). The prose's sources are in each facts file's "Prose added"
table.

| Figure | Script | Doc | Evidence it computes or re-runs |
|---|---|---|---|
| An arctangent with no floating point | `gen_atan.py` | `vehicles.md` 2 | error from the port (529/529 grid); worst 27 units, table 13.7, -32768 bug in 27/529 |
| How goods find their way across the islands | `gen_routing.py [drive]` | `economy.md` 3, 4 | `drive` re-runs the emulator (about 5 min): matrix 41/41 and 129/129 dumps, hops 14/14 twice |
| How a 1988 game drew solid 3D without a depth buffer | `gen_bsp.py`; `bsp_order_all.sh` first | `render.md` 4, 6 | draw order 1264/1264 draws of 6 models (`bsp_order.py`, `bsp_order_sum.py`; `bsp_survey.py`, `bsp_which.py` probes) |
| Fast polygon fill: a routine that rewrites itself | `gen_span.py [--emu]` | `render.md` 5 | patch bytes 64/64, rows 2183/2183 (control 531/2183); cache `span_emu.json` |
| A cheap distance that is up to 11.8% too long | `gen_octdist.py` | `ai.md` 1, 2 | 11.8% worst; scores 64/64 on `ai/nat/d1`; picks 11/11 on `ai/nat2` |
| Taking off from a moving, turning deck | `gen_takeoff.py` | `vehicles.md` 5 | 42/42 twice, 43/43 with the launch tick (stserver) |
| Unpacking a program inside its own memory | `gen_depack.py` | `packer.md` | output sha256, live margin 219 (control 220 corrupts 5 bytes), ratios (needs lz4, gzip, zstd, xz) |
