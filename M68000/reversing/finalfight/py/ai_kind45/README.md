# ai_kind45: live checks and decoders for the pool-2 kinds 4 and 5

Method and results are in `../../ai.md`, section "Kinds 4 and 5". Traces are per-frame dumps of work RAM `$ff8000-$ffbfff` (players,
pools 2, 6, 4, 8, props) of one fighter spawned into `ff_enemies`; they live under `$AI45_OUT` (default
`scratchpad/finalfight/p3/c/out`, gzip). The MAME run directory is `$AI45_RUN` (default `scratchpad/finalfight/p3/c/run`); two MAME runs
at once need two directories. `ff_main.bin` (`scratchpad/finalfight/`) is the ROM image. Every script derives the repo root from `__file__`.

Quick start: `AI45_OUT=<dir> AI45_RUN=<dir> ./runs.sh` (about 10 minutes), then `./gates.sh`.

| file | what it proves / does | how to run |
|---|---|---|
| `run.sh` | headless MAME wrapper (SDL dummy so it does not take focus): `drive <script.lua>` (no debugger) or `callcap` (`CALLCAP_SPEC`) | `./run.sh drive drv.lua` |
| `drv.lua` | loads a saved state, spawns one fighter (`FF_SPAWN="kind:+20:+21:level:x:y@frame"`, replicates `$3892` + `$5ee6`), orphans live enemies (`FF_KILL`), keeps Cody alive (`FF_HEAL`), Cody inputs (`FF_PLAN`), pokes, screenshots, gfx RAM dumps (`FF_GFXDUMP`), state save (`FF_SAVE_AT`, `FF_SAVE_NAME`); writes the per-frame trace | env vars, see the file header; used by `runs.sh` |
| `runs.sh` | regenerates all traces, the baseline `e900`, and the saved states `p3c_k4_goriber`, `p3c_k5_hollywood` | `./runs.sh` |
| `plan_tap.lua`, `plan_g1..g6.lua` | Cody inputs: Button 1 every 24 frames; walk into the enemy to grab, then release, throw, or grapple | `FF_PLAN=<file>` |
| `gates.sh` | runs every gate below over the traces with the expected counts | `./gates.sh` |
| `gate_dmg.py` | each drop of Cody's health while the fighter's attack box is active equals the ROM damage byte (record + `$60` + level + box row): 151 of 151 | `gate_dmg.py <trace> ff8c28 <kind> <sub> [level]` |
| `gate_zone.py`, `gate_zone4.py` | kind 5 attack zone `$36aec` (20 of 22 in zone followed by `+3 = 2`); kind 4 near and mid zones of `$32a88` (6 of 6, 8 of 8) | `gate_zone.py 5 <traces>`, `gate_zone4.py <traces>` |
| `gate_names.py` | the HUD enemy-name tiles in gfx RAM equal the expected name (5 of 5) | `gate_names.py <trace> <frame> <name>` |
| `gate_caps.sh` | `$3e88` accepts a spawn one below the per-kind cap and refuses one at the cap, kinds 4 and 5, ranks 0, 4, 11, 19 (callcap, fresh MAME call each) | `./gate_caps.sh` |
| `boxmap.py`, `hist.py`, `ops4.py`, `trk.py` | attack box per `+4`; state histograms; kind-4 script picks and ops; transition list of one record | `<script> ff8c28 ...`, see headers |
| `fr.py` | trace reader (`.bin`, `.bin.gz`) | import |
| `anim.py`, `chars.py` | decode animation lists and the character records (health, class, boxes, damage) from the ROM | `anim.py <setter> [sub]`, `chars.py` |
| `script.py`, `script_ents.py` | decode the stage spawn script set `$5f7e`; list the entries of one tag and kind | `script_ents.py 2 5` |
| `mklist.py` | recursive-descent listing of a ROM range with dispatch tables resolved (data is not decoded as code) | `mklist.py <lo> <hi> <root...>` |
