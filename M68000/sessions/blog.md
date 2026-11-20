# Blog: handoff

Updated 2026-11-20 by the session that ended at commit `e180f79` (master; the blog repo at `3443c14`, untouched).

The blog workstream curates and extends posts for 7sharp9.dev from the game research. Each game is reversed in its
own workstream; this one reads their docs, checks the claims a post would rest on, and feeds corrections back to the
game docs. Dave's standing direction: posts explain algorithms the games use and their relevance today, not emulator
fixes (2026-11-11); one infographic per interesting algorithm (2026-11-12); topic docs stay compressed, clarity goes on
figures, posts and README openings by `reversing/WRITING.md` (2026-11-15); an ML / AI-engineering slant, new games and a
long pipeline welcome (2026-11-16). The shape that fits the blog: a game's algorithm ported to idiomatic F#, proven
against the game, ending in a visual the game could not make. Dave (2026-11-18): build "Virus flown by optimisation", a
real learner, player-view first. This session (2026-11-20) Dave also asked for the 100-game demo chain and an
eight-agent coverage fan-out of Virus, both done and committed (Virus game work done from here, see Waiting on Dave).

## Resume point

- Last commit of this workstream: `e180f79` (virus mpc re-stop bound). Before it: `fa8d8a7` (eight promoted areas and
  gates), `35169db` (docs, `objects.png`, 143 names), `89a25fb` (`merge_sym.py`), then `a75d51b` (CLAUDE.md and skill).
  Master is 5 ahead of origin before this file's commit; the blog repo is 5 ahead of its remote. Neither pushed.
- Working data: `scratchpad/virus/` (`chain/long100/` 100 start snapshots and `chain.jsonl`, `ANCHORS.md` row; one
  `<area>/gate/` per promoted gate), `scratchpad/virus/mpc/` (pilot records; README "chaos/" holds the divergence
  record, scripts `mpc/chaos/fan.py`, `div.py`, `summ.py`, outputs `r2/`, `r1/` void), `scratchpad/overseer/virus8/`
  (the fan-out: `BRIEF.md`, `agents/<area>/report.md`, `merge/` with each area's promotion notes and both gate runs).
- Start from: `scratchpad/virus/chain/long100/starts/main_g050.snap` (reaches wave 5 and the mothership) or a seeded
  start (`duel/starts.py` on `demo/fl/Q1.snap`) for pilot work.
- Gates: `uv run python tools/gates.py run virus -j 8`: 14/14 PASS at `35169db` (about 6 min); `mpc_flight` and
  `mpc_shot` PASS again at `e180f79`. Dry run 0 MISSING, 0/14 declare no inputs (was 0/6).
- Uncommitted work left behind: none (`.obsidian/` is Dave's).

## Proven so far

- **100 unpoked attract games** (`demo.md` "A hundred games", `py/chain/chain.py`): games 1 to 24 repeat the old table
  24/24; final wave 1/2/3/4/5 in 2/21/69/7/1 games; wave rank trend +0.19, p 0.052 (not read as a trend). The life
  budget carried into wave 3 decides a long game: 4 of 13 games holding 4 or 5 lives at the first wave-3 death reach
  wave 4, against 4 of 64 holding 1 to 3.
- **Divergence** (record, `scratchpad/virus/mpc/README.md` "chaos/", r2): one-unit nudges never separate the ship by 160
  units open loop; closed loop x+16 reaches 1,024 units in 8/8 seeds (about 200 ticks); one-tick heading/tilt ±64 are
  absorbed 0/8. The pilot's threshold decisions amplify, the physics does not.
- **The fan-out** (`reversing/virus/README.md`, `behaviours.md`, `frontend.md`; one gate each, `py/<area>/`): no slope
  shading, slope table 16320/16320, spans 1440/1440; depth buckets 39523/39523 and paint order 1262/1263; mouse
  180/180, `$270d4` explained 119/119; wave table pools 141/141, bonus 7/7, landscape 1 natural; object types 1 to 12
  by render diff, falling infection 8319/8319; mothership 27 launches and 30-hit kill, chaser 4064/4064; HUD 12/12,
  sound sites 5531/5531, hall of fame 10/10; census: 217 routines run, 101 named (89% of calls), 27.2% of the code
  executes, no new routine after wave 3.
- Earlier pilot records and the radar/3D-view gates: unchanged (`scratchpad/virus/mpc/README.md` "duel/pv/").

## Running

Nothing running. The `stserver.dll` (pid 92780) predates this session and is not this session's.

## Open, in priority order

1. **Fix the 64-step bound in the scratchpad pilots.** `replay.py` and `gate_danger.py` now take a re-stop under 2,000
   steps as the same tick; `duel/baseline2.py`, `duel/fly_v7.py`, the frozen `pv/fly_*.py` and `sens*` still use 64,
   so their tick counts can include an extra tick per interrupt re-stop (r1: 11 of 136 branches). Fix `fly_v7.py` as a
   new tag and re-run seeds 1 to 8 before any new pilot result is compared with an old one.
2. **The patrol, from what a player sees** (unchanged from the last handoff): check the held-out failures
   (`pv/diag.py`, `pv/look.py` on `pv/d2_s10*.json`), then a pursuit model for the `b` class as one change, judged on
   seeds 1 to 8 and once on a fresh held-out set (109 to 116). The new `behaviours.md` "The mothership and the gated
   chasers" and the gated chaser model help here; the pursuer `$21f00` and patrol states are still ungated.
3. **Fast simulator**: tick, shot, seeder, chaser, mothership chaser and the wave rules are now exact functions or
   gated rules; gate `$21f00` and the patrol states (`behaviours.md` Open 3), then port to F# and gate against a
   recorded game. This is what makes a learner affordable (150 ticks/s in the emulator).
4. **Pass conversion as the learning target** (seed 106): check on a second seed (`order_of.py` on `sens1/s101_*.json`).
5. Virus loose ends from the fan-out, each with its owner doc's Open list: the model drawers `$26296`/`$264e2`/`$26780`
   (README Open 1, the way to render Virus's 3D models outside the emulator), landscape 2 naturally (Open 2), the enemy
   exit writer (Open 3), the sound record fields (`frontend.md` Open 1, the way to render the effects as audio), the
   rocket `$25306` and whether the pilot can ever kill the mothership (`behaviours.md` Open 1, 2).
6. F# port and TorchSharp (check macOS x64 support first; gpubox is the fallback); Paint It Black's two TODOs and
   Mountains of the Moon line 50; the carried post ideas in IDEAS.md.

## What would be good next (not necessarily this workstream)

- **Post: "Why the demo sometimes goes far."** The 100-game wave distribution, the lives-at-wave-3 table and the
  divergence fan (`mpc/chaos/r2/fan.png`) make one self-contained post with two figures; the code is the chain
  runner and the divergence harness, ported to F#. It needs no new emulator work and answers a question a player has.
- **Post or sidebar: Virus's sound and 3D models rendered outside the game.** Decode the 18-byte effect records
  (`frontend.md` "Sound") and the model drawers, then render effects to WAV and models to SVG in F#: a visual and an
  audible payoff the blog shape asks for. Start with the sound: the driver is small and fully located.
- **The player-view learner** (Open 1 to 4) stays the main line for "Virus flown by optimisation".
- **Refresh `sessions/virus.md`** (another workstream): it predates `py/mpc/`, the radar and view gates and this
  fan-out; a `/resume virus` should start from `git log -- reversing/virus`.
- New game workstreams queued in memory: Populous II, Captain Blood (`future-game-candidates`).

## Known traps

- `tools/gates.py` takes an `expect` entry only as an `a/b` count or `re:<regex>`; copy it from the printed output
  (now in the skill, 3c).
- An agent's "returns at once, skipping X" from reading a branch needs the branch target read: `$2337c` skips only the
  height loop, not the object-map clear (README "Landscape selection by wave").
- `merge_sym.py` before `89a25fb` crashed on `$`-prefixed `.sym` files (virus.sym); fixed.
- Settings tuned on eight seeds did not hold on eight others; a version is judged on a held-out set once.
- `run_seeds.sh` runs the frozen `pv/fly_<tag>.py`: copy to a new tag and point its `here` line one directory up.
- Kills in the pilot's JSON are score steps (the last includes the wave bonus); a cruising patrol is on the radar only;
  poking the RNG at `S1b.snap` changes only later draws (`Q1.snap` for a new layout); the league caps at 2000 ticks.
- A control word under 64 does nothing (the sine table has 1024 entries for a `$10000` turn): nudge headings by 64.
- `scratchpad/virus/mpc/replay/` and `shot/` are pre-promotion copies; use `reversing/virus/py/mpc/`.

## Waiting on Dave

- This session did Virus game work (fan-out, promotion, docs) under the blog workstream because Dave asked here.
  Should `sessions/virus.md` be rewritten from this work (a `/resume virus` pass), or Virus stay under blog?
- Push master (6 ahead after this file) and the blog repo (5 ahead).
- Whether the Virus post is one post (planning, the player-view tier as a negative result) and a learning sequel, or
  waits for a player-view pilot that finishes a wave; and whether "Why the demo sometimes goes far" goes first.
- Carried: IDEAS.md rewrite around the ML ranking; Captain Blood prior art; Midwinter line 50; Captive keys figure;
  Carrier Command series; "proven" vs "observed" in Crude Buster and Final Fight; Lemmings artifact republish; Hugo upgrade.

## Next session

`/resume blog`. Decide with Dave between the demo-variance post and the pilot line. For the post: read `demo.md` "A
hundred games" and `scratchpad/virus/mpc/README.md` "chaos/", scaffold with `dave-post`, and draw the wave histogram and
the fan figure. For the pilot: Open 1 first (a fixed `fly_v7.py` tag re-run on seeds 1 to 8), then Open 2.
