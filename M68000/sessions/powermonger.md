# PowerMonger: handoff

Updated 2026-09-23 by the session that ended at commit `c4e9804` (the 122nd PowerMonger pass;
migrated into the handoff regime from `scratchpad/pm123/NEXT_SESSION.md`, the memory RESUME block and
the PowerMonger lines of the root `next_session.md`).

## Resume point

- Last commits of this workstream: `863ef32` (how a land ends, the campaign, `$2776`/`$5cde`/`$550e`
  proven), `60ea3e9` (`tools/capture_hits.py`, `disassemble.py --all`), `c4e9804` (skill additions).
- Working data: `M68000/scratchpad/` (gitignored). Disk `scratchpad/powermonger.st` (Replicants
  crack); every REPL command takes `--disk-a scratchpad/powermonger.st`. Reusable snapshots are
  indexed in `scratchpad/ANCHORS.md` (pm120, pm121, pm122 rows). A whole-image listing is at
  `scratchpad/pm122/game_all.asm` (from `pm121/run/k25_s4.snap`; regenerate with
  `tools/disassemble.py --snap <snap> --all 400 20000`).
- Start from: `scratchpad/pm121/run/k60_s2.snap` or `k0_s2.snap` (later lands, 50M steps in, the
  player's army still alive), `scratchpad/pm122/end/lose_d2c8.snap` (at the end-of-land verdict),
  `scratchpad/pm122/end/map_cont.snap` (the conquest map).
- Uncommitted work left behind: none. (`CLAUDE.md`, `*.fs`, Populous and Cadaver files that show as
  modified belong to other sessions.)

## Proven so far

Differential tests against the real 68000 through `callcap`; reconstructions in
`tools/pm_fsm_ref.py`, gates in `reversing/powermonger/py/` and `scratchpad/pm9x/`:

- Entity FSM `$14b62` handlers ($12/$68/$8a, $06/$08/$0e/$10, $32 melee, $7c heartbeat):
  `scratchpad/pm98/repro93..97.py` 675/1335/413/85/99.
- `$3c08` regroup 71/71 (`scratchpad/pm98/diff_pm98.py`); its teardown `$37c2`/`$1d70`/`$1b8c`
  1847/1847 (`scratchpad/pm99/diff_pm99.py`); `$4bc8` 51/51 + 20/20
  (`scratchpad/pm115/diff_4bc8.py`, `diff_4bc8_kind2.py`); `$4342` 8/9 branches (113th).
- `$1623c` dying entity 275/275 (`py/diff_1623c.py`); `$2776` group dissolve 4119/4119, 28 states
  (`py/diff_2776.py`); `$5cde` the lord's work order 768/768, 47 states (`py/diff_5cde.py`); the
  revolt chain `$550e` → `$5c2c` → `$25d6` 1778/1778, 49 states (`py/diff_revolt.py`).
- Renderer and port pixel-exact: 27 later-land frame pairs at 100.00% (`py/score.fsx`,
  `port/SPEC.md` §6); seasons, weather, zoom (`port/SPEC.md`).
- How a land ends (strategy.md "How a land ends"): command `$2e` → `$d2c8`, victory iff
  `$57fce == 4`. Defeat observed naturally (land 60) and by retiring; victory only by poking the ratio.
- The campaign (strategy.md "The campaign"): 13 × 15 conquest map `$3f2a0`, per-land table `$3f428`
  (mission 1 = entry 0); only the map carries between lands; the `$67d0` hook is dead code; the Play
  Random Land route still runs the real manual-lookup protection check.
- Emulator: selftest 1000051 pass / 0 wrong / 9 skip; no emulator change since the 120th pass.

## Open, in priority order

1. **The player's commands, then a natural victory.** Decode the options-panel buttons (`$7202`,
   `D3` codes at `$7700..$7a20`) and the map clicks (`$13212`, `$13892`) into a table
   button → order byte → executor case (`disassemble.py --jumptable 6b5a 26`). Issue real orders on a
   run land, follow them with `hits`/`watch`, and drive the player's army until `$57fce` reaches 4,
   then retire. Proof: a natural `$3f2a0` write and a campaign step (Continue Conquest → pick a
   neighbour → build). This unblocks everything about how the game is played.
2. **Conquest in the field, mode `$2c`.** `$152f6` → `$4f68`, jump table on `38(A1)` at `$4fa2`; the
   `38 == $12` arm (`$539a`) calls `$550e` and made 16 of the 27 natural lord defections. Decode the
   table, then prove `$4f68` (or `$539a`) with a callcap gate over natural states from
   `tools/capture_hits.py` (returns at `$53fa` mark the `$550e` arm).
3. **Diplomacy, the per-side block `$580a6`** (5 × `$20`, loaded per land from the campaign table).
   Map its writers and readers from the `--all` listing, diff the 195 table entries' blocks
   (`scratchpad/pm122/end/land1_pick_end.snap` holds the table at `$3f428`), `watch` the relation bytes
   `+15`/`+16` over a natural run, prove the per-tick writers (`$139dc`/`$13a3e`/`$13b20`) and
   `$311a`, and answer whether sides can ally and whether it changes `$68fe`/`$3154`. A good
   parallel-subagent task.
4. **Food.** What refills `byte45` (the drain is `$5c80`), what the HUD food display reads, and what
   `$5bd2` (wear/starvation removal, never fired in 800M steps) needs. Stop at 45 minutes if food turns
   out to be morale only, and list the writers.
5. **`$1b8c` via `$5778`**, the last Corroborated routine: a callcap gate over natural `$5778` states.
6. **`$4342` arrival/unlink branch**: hangs the real emulator under every synthesised poke tried in
   the 113th pass, not root-caused (repro `scratchpad/pm113/diff_4342.py`; regenerate its anchor pokes
   from the script). Try natural states from `capture_hits.py` first.
7. Smaller: draw weather in the stepper and Godot view (`Weather.draw` after `Scene.render`, phase
   from `$1aac8`, then stepper `--selfcheck` on `assets` and `assets_k60`); find where the crack writes
   its `$b842` patch on the campaign route but not on Play Random Land (`watch b842 4` from boot on
   each route); the Load Data Disk / fixed-map `$df52(7)` branch is unreached by any route found.

## Known traps

- Land 60's first run stretch starts at `scratchpad/pm120/k60_iso.snap`; there is no
  `pm121/k60.snap`.
- Play Random Land leaves `$14e4e = 0` (the uncracked protection check), so the tick skips the AI
  block (`$6522`/`$d322`/`$3e06`). Use campaign or poked lands for AI work, or poke `$14e4e := $2c`.
- The pointer's live position is `word[$1c492]`/`word[$1c494]`; clicks are down / `mouse move 0 0` /
  `s 300000` / up / `mouse move 0 0`. The Populous session's IKBD fix (absolute-mode `mouse move`)
  left the pm122 Continue Conquest and land-pick drives byte-identical.
- The object table is `$51b66`, stride 50; `$4c12c`, stride 26, is the small-object (pigeon/effect)
  pool.
- `$2776` reads the command slot at `$58016 + 3*side` (`mulu #3` at `$28e4`), not `6*side`; `$5c2c`
  sets D2, not D3, before `$25d6`. Both are transcribed as the code does them (game bugs, inferred).
- Byte6 18 is unreachable (`$245c` forces a lead's `44` to 6); do not chase it.
- A full `pm_export.py` rerun regresses `entities.json` and `sprite_triggers.json`: restore them with
  `git checkout` afterwards.
- Do not reopen the SingleStepTests CPU-accuracy track (100th-112th) or `$4342`'s 8 proven branches.

## Next session

Start with open item 1: decode the `$7202` button map and the map-click path into a command table in
strategy.md, then issue real player orders on `run/k60_s2.snap` and try for a natural victory. Run
item 3 (diplomacy) as a parallel subagent from a brief built from `tools/pm_fsm_ref.py` constants
(CLAUDE.md "Proving routines with parallel subagents"). Before committing, run every gate listed under
"Proven so far" fresh (no `reuse`). The prompt is `/resume powermonger`.
