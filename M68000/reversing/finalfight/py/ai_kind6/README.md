# Kind-6 (ROXY, POISON) harness and gates

Method and results: `../../ai.md`, section "Kind 6". Everything runs MAME 0.289 headless through `ffrun_k6.sh` (SDL dummy, own run directory).
`K6_RUN_DIR` is the MAME run directory (cfg, nvram, `sta/ffightuc/<state>.sta`, snapshots, frame logs); default
`<M68000>/scratchpad/finalfight/p3/d/run`. Large outputs stay there. Repo root is derived from `__file__`. Python needs only the standard library.

First `make_pre.sh` (cold boot to frame 1900, saves state `k6_pre`; work RAM md5 `9cc4bdf8...` over 3 boots). `run_checks.sh` redoes every
gate with fresh runs (about 15 minutes).

| file | what it proves / does | how to run |
|---|---|---|
| `ffrun_k6.sh` | MAME wrapper (no focus), `FF_MAMEARGS="-debug -debugger none"` for breakpoint runs | `ffrun_k6.sh <script.lua> [seconds]` |
| `make_pre.sh` | builds the `k6_pre` state (frame 1900, no enemies) | `make_pre.sh [name]` |
| `k6run.lua` | harness: loads `K6_LOAD` (default `k6_pre`), spawns kind 6 through the real script engine (`K6_SPAWN="char:sub:x:y,..."`, `K6_REL=1` x relative to camera) or from a ROM group (`K6_NATURAL=<hex trigger>`, `K6_CAMX`), forces attacks (`K6_FORCE="rel:id:dx"`, `K6_APPROACH`, `K6_F161`), pokes (`K6_POKE`, `K6_RAM`), bot/immortal/respawn, screenshots, `K6_SAVE`; writes `<tag>_frames.bin` (per frame: pool 2, players, `A5` low `$200`) | `K6_TAG=x K6_FRAMES=300 K6_SPAWN="0:0:300:48" K6_REL=1 ffrun_k6.sh k6run.lua` |
| `k6hit.lua` | `k6run.lua` plus debugger breakpoints printing registers (`K6_BP`, `K6_HIT_OUT`) | as above with `FF_MAMEARGS`, script `k6hit.lua` |
| `runids.sh` | one forced run per attack id 0..15 for a character | `runids.sh <char> 48` |
| `gate_dmg.py` | Cody's health drops equal the damage table (85 of 85) | `python3 gate_dmg.py` |
| `gate_score.py` | state-6 entries award 2000 (ROXY) / 3000 (POISON) (15 of 16 in the two bot runs; the 16th is an off-screen cull) | `python3 gate_score.py <frames.bin>...` |
| `stat.py` | state histograms, transitions, ids, hurt types, deaths | `python3 stat.py <frames.bin>` |
| `decide2.py` | attack trigger paths A/B/C and id in the `$3abee` row | `python3 decide2.py <frames.bin>` |
| `hitlog.py` | dodge check (`$3a454`: evaluations, dodges, prediction from mask and rnd) and attack-start mask check (`$3a516`, dead per-character pointer) from `k6hit.lua` logs | `python3 hitlog.py dodge\|mask <hits file>` |
| `walk.py`, `score.py`, `summ2.py` | pauses, speeds, stand-offs; score changes; per-id summary | `python3 summ2.py <char>` |
| `tl.py`, `fa.py`, `poke_tl.py`, `findst.py`, `ramq.py` | state timelines, per-frame views, poke timelines, find sub-state entries, RAM dump query | `python3 tl.py <frames.bin>` etc. |
| `rd_trace.py` | recursive-descent ROM lister (resolves `jmp`/`jsr N(PC,Dn.w)` tables) | `python3 rd_trace.py <lo> <hi> <entry>...` |
| `scripts.py` | stage-script parser (tables `$5f5e`/`$5f7e`), lists spawn entries; entry addresses and fields are right, but its `stage`/`area` labels are not: the parse follows jump commands past an area's end, so assign an entry to the area whose pointer range (tables `$5f5e`/`$5f7e`) contains its address | `python3 scripts.py 2 6` |
