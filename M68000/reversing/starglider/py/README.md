# Starglider scripts

Run from `M68000/` with `python3` unless a row says otherwise. Each script finds the repo by walking up to
`tools/rdis.py` and shares paths through `sgcommon.py`. Data (captures, snapshots, renders) goes under
`$STARGLIDER_WORK/<area>/` (default `scratchpad/starglider/<area>/`). Start snapshots come from `../drive.sh`.
Each script runs its own emulator process (REPL or `stserver`), one at a time. `../gates.toml` lists the gated
commands and their expected lines. The broken-model flags (`--broken`, `--break`, `--control`) give the controls
quoted in the topic docs.

| script | what it does | doc |
|---|---|---|
| `sgcommon.py` | paths (`ROOT`, `WORK`, `DLL`, `DISK`), anchor snapshots, `load_ram` | |
| `flight/models.py` | Python models of `$12340` (flight step), `$d29a` (key commands) with the RNG, and the IKBD handler `$b7be` | flight.md |
| `flight/gate_integrator.py [N] [--broken]` | `$12340` on N random states vs the model | flight.md §3 |
| `flight/gate_controls.py [N] [--broken]` | `$d29a` on random key arrays vs the model | flight.md §2 |
| `flight/gate_isr.py [N] [--broken]` | random IKBD byte streams through `kbd` vs the model | flight.md §1 |
| `flight/gate_energy.py`, `gate_laser.py`, `gate_messages.py`, `gate_letters.py`, `gate_cheat.py` | energy, shield, laser, messages, letter commands, practice mode, driven in flight | flight.md §2, §4, §5 |
| `flight/gate_definekeys.py` | DEFINE AGAV CONTROLS from `g_title`, then the user keys in flight | flight.md §2 |
| `flight/fly.py [--snap S]` | flight driver (`Flight().hold`, `.mouse`, `.ab`); with no arguments prints the input A/B table | flight.md §3 |
| `flight/run_all.sh` | every flight gate and control | |
| `render/rref.py` | Python reference of the pipeline (matrices, transforms, clips, Bresenham, dots, dust, object draw) | graphics.md |
| `render/gate_math.py`, `gate_line.py`, `gate_obj.py`, `gate_obj_all.py`, `gate_frame.py`, `gate_clear.py`, `gate_dot.py`, `gate_dust.py`, `gate_bearing.py`, `gate_text.py` | each pipeline stage vs `rref.py` (`N=` env or a count argument) | graphics.md |
| `render/models.py` | renders every model as `models.png` (needs the `.venv` python, PIL) | graphics.md §3 |
| `objects/objpass.py` | Python model of the AI pass `$125e0` with the RNG and the bearing | objects.md §3 |
| `objects/objpass_gate.py N [--break]` | poked per-type states and natural hits vs the model | objects.md §3 |
| `objects/collide.py`, `laser.py`, `project.py`, `nearlist.py`, `impact.py` | collision, laser hit test, projection and lists, impact consequences | objects.md §4 |
| `objects/rng_gate.py`, `levelinit.py`, `names_gate.py` | both RNGs, level initialisation, database names | objects.md §2, §5, §7 |
| `objects/census.py [snap]`, `levels.py [-v]` | decode the live pool and draw a map; list each level's object list | objects.md §1, §5 |
| `frontend/ice_depack.py in out` | the game's Pack-Ice depacker | frontend.md §1 |
| `frontend/tra_render.py [--check]` | render the `.TRA` pictures; `--check` proves the format against RAM (`.venv` python) | frontend.md §2 |
| `frontend/hud_poke.py [name ...]` | poke a global and diff the rendered HUD against a control | frontend.md §6 |
| `frontend/export_samples.py` | write the sampled sounds as WAVs (amplitude approximate) | frontend.md §3 |
| `frontend/screens_*.py`, `text_census.py`, `fe_repl.py` | screen drivers for the title, launch, docked, interrogate, controls, game over and high scores; a `$bcba` stop census | frontend.md §4, §6 |
| `curios/gallery_keys.py` | the model viewer's keys from `g_title` (practice flag poked), each against a no-key control; renders every model | frontend.md §4 |
| `curios/level_from_score.py [taps] [--crash]` | practice-mode N taps vs a control: score and level; `--crash` goes to level 32 and the next collision | objects.md §5, §4 |
| `curios/shield_level.py [levels]`, `shield_crash.py` | the collision shield cost per level (wild pointer from level 16) and the bus error at levels 32 and 34 | objects.md §4 |
| `curios/rating_stale.py` | a no-shot game graded on a stale accuracy: CHEAT!?! vs the ROOKIE control | frontend.md §4 |
