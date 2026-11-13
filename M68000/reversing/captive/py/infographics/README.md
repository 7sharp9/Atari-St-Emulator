# Captive infographics

One explanatory figure per algorithm, computed from the proven model or the game's own captured values, as blog
material (`7sharp9.github.io/IDEAS.md` entry 9). Each `gen_*.py` writes `<name>.svg` to
`scratchpad/captive/infographics/` and prints every number it draws; `<name>.facts.md` maps each fact in the
figure to its doc section or computation and flags what the work found wrong or unclear in the docs. Each figure opens with a lead
paragraph and gives every panel a "How to read" and a "Takeaway", with a "How we know" strip that explains the proof
labels, gates and snapshot names; the facts file's "Explanatory text" table sources each of those sentences. Cached
emulator results and helper inputs live in `scratchpad/captive/infographics/data/`. gen_trail, gen_digger and
gen_lock recreate a missing cache themselves (gen_lock's `--emu` also needs the curios helper scripts, `HELPERS`,
default `scratchpad/captive/agents/curios/`); gen_universe's three callcap deltas are made by the command in its
docstring and `universe.facts.md`.
PNG: `cd M68000/scratchpad/captive/infographics && rsvg-convert -z 2 <name>.svg -o <name>.png`; the committed copies
are `reversing/captive/infographic_<name>.png`.
Run from `M68000/` with `uv run python -I reversing/captive/py/infographics/<script>`.

| Figure | Script | Doc | Evidence it computes or re-runs |
|---|---|---|---|
| Follow the footprints | `gen_trail.py [--emu]` | `ai.md` "Decision rule", "The trail"; `mapgen.md` "The flow field (plane 2)" | decision model 3000/3000 on `p2.snap` and `base1/in.snap` (control 2974/3000), drains of the dig tree, footprints, 0 bits-3-5 changes over 12M steps; `--emu` re-runs `gate_decide.py` and `track.py` (about 20 s); cache `data/trail_emu.json`, `data/track_end.snap` |
| A turtle that digs a perfect maze | `gen_digger.py` | `mapgen.md` "The digger and rooms", "The flow field (plane 2)" | port = emulator on the whole 13,756-byte block for seed 5; flow field 915/915; loop census over the 1000 captured seeds (about 3 min); `data/seed5.json` from `gen.py` when missing |
| A galaxy from one number | `gen_universe.py` | `world.md` 1 | tables 51/51, 100/100, 150/150 for missions 1, 2, 8; draw counts and final D0 = callcap D0; screen fit 50/51; grid lines; one name on screen; callcap deltas `data/cc_m{0,1,7}.json` |
| The die that knows the code | `gen_lock.py [--emu]` | `ai.md` "Getting into a base"; `mapgen.md` "After the flow field" | lock model = emulator on 24,576 presses (6144 sequences), die hint 1080/1080 (control 72/72 random), RATT note = code 8; `--emu` re-runs the stserver census and the curios scripts (about 20 s); cache `data/lock_emu.json`, `data/lock_runs/`, `data/compound.json` |
