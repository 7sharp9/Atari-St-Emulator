# PowerMonger: handoff

Updated 2026-09-30 by the 130th pass (a hidden-features audit by a subagent, re-checked by the parent, a
terrain-dither deep dive, and the `load_ram` water-tick fix). The 129th's alliance item 1 is still the next
game-mechanics step; the unfinished half of the audit is item 2.

## Resume point

- Last commit of this workstream: the 130th pass's handoff commit (`git log --oneline -3`; the pass itself is
  `11d91bb`); before it the 129th, "natural alliance completes end to end" (`f0cb17c`).
- Working data: `M68000/scratchpad/` (gitignored; on the Mac copied from gpubox, CLAUDE.md "Shell
  pitfalls"). New this pass, indexed in `scratchpad/ANCHORS.md`: `pm129/` (about 46 MB, `.ram` beside each
  `.snap`): `wp5_45M.snap` is the launch point for the `$1e` offer click on land 25's lord 15, and
  `env5_12M.snap` is the post-alliance state. `pm130/audit/` holds the audit's scripts, whole-image listing
  and raw output; `pm130/dither/dither_data.json` the infographic's data (both in `ANCHORS.md`).
- Start from: `scratchpad/pm129/env5_12M.snap` for anything about the alliance's effects;
  `scratchpad/pm123/win/m1_s0.snap` (mission 1 settled) for work not touching the live goods economy
  (mission 1 has no goods anywhere).
- Uncommitted work left behind: none in this repo. Pre-existing and not this workstream's:
  `M68000/sessions/README.md` carries an uncommitted line-rewrap from Obsidian (`.obsidian/` is untracked),
  and `Cadaver/` is untracked.

## Proven so far

Gates (differential tests vs the real 68000 through `callcap`), unchanged this pass, not re-run
(no reference transcription or gate script touched): entity FSM
`scratchpad/pm98/repro93..97.py` 675/1335/413/85/99; `pm98/diff_pm98.py` 71/71; `pm99/diff_pm99.py`
1847/1847; `pm115/diff_4bc8.py` 51/51 + `diff_4bc8_kind2.py` 20/20; `py/diff_1623c.py` 275/275;
`py/diff_2776.py` 4119/4119; `py/diff_5cde.py` 768/768 + 85/85; `py/diff_revolt.py` 1778/1778;
`py/diff_4f68.py` 1804/1804.

- **Terrain fill fully characterised (130th).** `py/dither_atlas.py` rebuilds mission 1 and a coast scene from
  (triangle, colour byte, slot): 0 pixels differ from `pm_render_ref`, 94.6 % / 95.6 % equal the game's frame (rest
  sprites); season fade model equals `pm74_late`'s live slots byte for byte. Table layout, ramp structure, the
  forced-`0x1c`-only slot and the tick-minus-one buffer lag are in graphics.md "The pattern fill";
  `dither_infographic.html` is the interactive version. `tools/pm_render_ref.py` `load_ram` now returns
  `tick = (counter - 1) & 3` (`ram_tick` is the raw counter): mission-1 and `pm74_late` scores unchanged
  (94.6 / 94.4 %), water scenes 90-100 % (`k5_x1` 95.6, `k60_iso` 91.7, `k5_22_0` 100.0, `k5_22_2` 99.9).
- **No hidden keys or debug commands (130th audit)**, with the exceptions and the uncovered list in strategy.md
  "Hidden features audit": arrow keys scroll the camera cell ungated (graphics.md camera loop corrected), dormant
  word `$5809a` draws all sides' markers when set, startup command-line string `$123c` reaches the serial-link role
  parser `$12d88`.
- **A natural alliance completes end to end (129th, land 25, no pokes).** After a second `$10`
  take-equipment (5 pots) and an `$02` waypoint at (40,28) round a water strip, order `$1e` on lord 15's
  ungarrisoned lone town gives `$33b0` 1, `$34a8` 1, `$c9f8` 1 hit, `$c706`/`$cada`/`$4c2a` 0; peace bits
  `$580cc`/`$5812c` go to `$12`/`$12` and stay there for 30M further steps. Control: 3 pots gives `$33b0`
  1, `$cada` 1 (refusal), `$34a8` 0 (v = -8 + 6 - 2 = -4). The earlier "envoy always dies to `$4c2a`" was
  specific to garrisoned lord 4. strategy.md "Diplomacy"; `scratchpad/pm129/run4/8/9.cmds` and `.out.txt`.
- **A straight-line `$1e` march can stall on terrain (129th):** the lead sat in mode `$48` at a type-0
  (water) strip at (38..39,29) for 60M steps and starved; an `$02` waypoint first fixes it
  (`py/terrain.py`).
- **Every player order, food, group-record fields, conquest, the heartbeat revolt mechanism,
  starvation desertion, what sets `dwell := $ff9d`, mode `$16` as a garrison/neutral marker,
  weather in the port stepper**: see the 125th/126th/port-pass summaries in git history — unchanged
  this pass.
- **Revolt reachability was already proven, and the "still open" framing in economy.md/README was
  stale (127th).** The 122nd pass's `diff_revolt.py` (1778/1778 over 49 states) already showed the
  settlement heartbeat's `$7c`/`$16` self-cycle crossing loyalty 600 unassisted: 11 of 27 natural
  `$550e` defections on four 200M-step no-input land runs came from the heartbeat at loyalty
  600-608 (`ai.md` "The revolt chain"). Fixed in `economy.md` §3a and the README design digest. The
  narrower question — is the settlement's own `$7c` marker literally the same object that feeds the
  mode-`$16` traffic — stays open (unchanged from before).
- **Take-equipment genuinely fills a group's `carrying[]`/`supply_acc[]` from a real stockpile, no
  pokes (127th, live).** Land 25's side-1 group (8 men) sent to its own lord 7's town with order
  `$10` came back carrying 3 pots pulled from lord 7's actual `goods[]` — confirms economy.md §2c's
  `$61f8`/`$6352` claim under fully organic conditions. `scratchpad/pm127/diplo3/equip_probe.snap`.
- **An unescorted natural-goods envoy dies to contact before offering an alliance — confirmed four
  times independently now (123rd forced-goods, 127th fully organic, 128th's two land-25 probes).**
  Every attempt: hostile contact fires `$4c2a` (not `$33b0`/`$34a8`) before the envoy arrives.
  strategy.md "Diplomacy".

## Open, in priority order

1. **The alliance's effects from the natural state.** From `pm129/env5_12M.snap`: order `$06`/`$10` on
   lord 15's town should be accepted like an own town (`$3154`'s peace-bit filter), and a `$1e` click
   there should no longer be accepted by the `$1394c` pointer test. Then a side-3 alliance with 3 pots
   (formula predicts v = 4, not run) needs an escort past lord 4's 18-entity garrison; not a fix found yet.
2. **The rest of the secrets audit** (strategy.md "Hidden features audit" lists what was and was not covered).
   In order of likely payoff, each with how to prove it:
   - `$5809a` (dormant "draw all sides' markers" word): find register-relative writers
     (`find_field_writers.py`, it sits just below the `$5809c`/`$580a0` briefing variables, so check whether a
     block copy or a save covers it); prove by setting it through that path and counting `$16738`/`$e6ee` hits.
   - Link mode: the ESC abort (`$1c34e` receive, `$1c39e..$1c3ae` send), the chat command `$26` (`$d13e`), and the
     startup string `$123c` reaching `$12d88` (states 6 and 8). Patch `$123c` to `S` and `M` in a snapshot and
     watch what the side records and `$d13e` do; the parse is inferred, not traced.
   - Unreferenced data: `DATA\SPRITE40.DAT` (on disk, not in the `$e0c4` loader table), `B_FLOOD.ECH` (`$1adaa`),
     `DATA/MAP0000.DAT` (`$e388`, the fixed-map branch `$df52(7)`), and whether `BITMAP.DAT` loads at mission 1
     (`$13c0e`, needs `$58148 < $100`). Prove with `hits` on the loader `$df52` and its index argument over a
     land build.
   - Dead-code triage: about 100 of 117 unreferenced routine starts are untriaged (`$503c`, `$15a60`, `$10458`,
     `$90ca` regions are big). The reachability walk in `scratchpad/pm130/audit/reach_scan.py` misses dispatch
     tables (it called the live `$b892` an orphan), so improve it with the `movea.l <field>(A5),A6 / jmp (A6,Dn)`
     rule before trusting its list, then run the orphans under `hits` through a land build and a few minutes of play.
   - The crack's own stage (title, cracktro, `MREP`, packed `WAR`) was not audited; one byte at `$27028` changes
     when `$2a` (left shift) is pressed and is unexplained; `$58000` and `$4bb48` are read-only absolutes.
3. **The orders not yet seen naturally**: `$04` transfer (needs two captains, a later land), `$0e`
   on a real capital (does the work order produce pots naturally?), `$10`/`$06` on a food pile, the
   `$1a` supply line over several loops (food delivered per loop).
4. **What refills strength** (lead/man byte 45, the captain panel's "Strength:", drained by `$5c80`);
   the old "food" item 4 reads byte 45 wrongly. Watch byte 45 of a man over a march with and without
   food.
5. `$1b8c` via `$5778` (a gate over natural `$5778` states); `$4342`'s arrival/unlink branch
   (`scratchpad/pm113/diff_4342.py`, natural states from `capture_hits.py`); `$4f68` arms not covered
   (`$51dc` finding an ally's target, `$548a`'s `39 == 2`).
6. Smaller: weather is now in the stepper (`C` key, this pass) but still not in the Godot view
   (`godot/game/TerrainView.cs` has no `Weather` reference); where the crack writes its `$b842`
   patch; the fixed-map `$df52(7)` branch; `$2df98` is "the other button" (inferred right); the port
   and stepper still use the old names (`troops_reserve`, budget, discipline) if they model them.
7. **A deeper game summary/mechanics writeup**, if Dave wants to keep extending it toward
   populous's depth: the README now opens with a doc-index table (added 127th) and the Design
   digest is current; a further step would be an explicit "architecture" thread (per-tick dispatch,
   core data structures, which mechanics are instances of a shared idiom) the way
   `reverse-engineer-st-game`'s §7 describes, if the topic docs don't already read that way on a
   fresh pass.

## Known traps

- **A subagent's "the docs are wrong" claim gets one live check before it goes into a doc.** The 130th audit's
  arrow-key finding contradicted graphics.md; a 3-command REPL run (`kbd 4b`, `s 500000`, `m 4bb3a 4`: X `$28` to
  `$26`) confirmed it before the correction was written. The same agent's reachability walker also called a live
  routine an orphan, so its derived lists need the same treatment.
- **A raw `dotnet exec ... resume <snap> repl` needs `--disk-a <file.st>`, not `-DiskA`** (that is `run.ps1`'s form,
  DEVELOPING.md). With the wrong flag the REPL printed all-zero memory instead of failing, which reads like an
  empty camera cell, not a bad argv.
- **Compare a water frame against the game's buffer with `tick = counter - 1`** (now done in `load_ram`); raw
  counter scores of 40-70 % on a coast are this offset, not a renderer bug.
- **Census the target's own neighbourhood before choosing a route, not the nearest one by distance.** The
  129th's `census_lords.py` found the far lone town (lord 15) clear while the near capital (lord 4) held 18
  entities. Stalls are then terrain, not enemies: check the `$438ee` plane (`py/terrain.py`) before blaming a garrison.
- **"Pick a different land/target" as a fallback needs checking, not assuming.** Land 5 looked like
  a ready-made escort source (three side-1 group slots vs. land 25's one) purely from a slot count;
  live census (`census_groups.py`) showed the other two are `owner 1, men 0` from the land's own
  start — dead captain records. Before treating an alternate land or target as a fix, census it
  live the same way you'd census the one that just failed.
- **An order's target-cell filter can't be inferred from the order table's own wording.** `$0c`'s
  "any cell" meant "no friend/foe ownership filter" (true, it's what distinguishes it from the
  `$3154`-routed orders), not "works on empty ground" — tested live, it silently refuses to commit
  against a cell holding nothing the game tracks. Test a targeted order against the actual cell you
  intend to use it on, not just against a cell of the right *kind* documented elsewhere in the table.

- **A `--shot`/screenshot-style headless check on `port/stepper` proves rendering at one instant,
  not a game-loop behavior over time or input.** Two real continuous-play bugs this pass (P not
  sustaining, camera changes re-pausing it) both passed `--shot`/`--selfcheck` and were only caught
  because Dave ran the interactive window himself. `--playtest` now exists for this; extend it
  rather than reaching for another screenshot when the next interactive bug shows up.
- **Mibo's `GameTime` (`port/stepper`, Mibo.Raylib 4.5.3) has no constructor callable from F#
  outside the Mibo assembly**, even though reflection shows a public one (an F# record's IL
  constructor is public but the compiler still refuses it: `FS1133 No constructors are available`).
  Don't hand-roll a tick loop by constructing `GameTime` and calling `update` directly -- use
  `Mibo.Elmish.HeadlessProgram.mkHeadless`/`withTick` plus `new HeadlessRunner<_,_>(program)` (omit
  the optional `width`/`height` args positionally rather than passing `None` -- F# optional
  constructor params want the raw value or to be omitted, not wrapped). This drives the real
  `ElmishLoop`/subscription machinery, not an approximation, and is what caught the second bug
  (`--shot` and a first hand-rolled test both missed it) once the test dispatched an actual
  camera-change key mid-loop.
- **Grep the topic docs for a routine's address before disassembling it.** This pass spent a full
  read of `$157e6`'s body only to reproduce, line for line, the pseudocode economy.md §3a and
  ai.md already had from the 96th/97th pass (now in `CLAUDE.md`'s Rules).
- **Grep for a retired "still open" framing before re-scoping a live test for it — the same rule
  bites at the doc level, not just within one doc.** The 127th nearly re-ran the 126th's planned
  400M-step revolt-reachability census, which would have been pure waste: `ai.md`'s "revolt chain"
  section (122nd pass) already answered it. Read the *other* topic docs' proofs, not just the one
  the open item lives in, before planning a new test.
- **Before committing a long march to a step budget, check the group's food-to-men ratio can
  survive the distance, or probe with a short step count first.** A natural corpus's own marching
  pace (~13-14M steps/cell, from a group under contested/wandering conditions) is much slower than
  a short mission-1 test's (~5M steps/cell), and a starving group deserts and can fully disband
  before arriving. This pass burned a 450M-step run on land 0 (13 men, food 46) to watch it starve
  33 of 69 cells short and never arrive; the very next attempt (land 25, 8 men, food 97, 17 cells,
  probed with 80M steps first) succeeded cleanly. Cheap insurance: run a modest step count, check
  `group.py`'s position/food/men, then extend only if it's still alive and progressing.
- **A side's own captain groups wander far from home under autonomous AI orders in an unplayed
  natural corpus** — even side 1 (the player's side) gets `$6522`/`$6564`-issued orders when nobody
  is clicking, so "our" group in a `pm121/run/<land>_s4` snapshot is often nowhere near our own
  settlements. Census every side-1 group (`0x51538 + 0x13c + 0x4c + 2k`, k=0..5) before planning a
  march, not just the currently-selected one (`$57fd2`).
- Group offsets: `D2` / `42(obj)` / `$57fd2` = `side*$13c + $4c + 2k`; a group field `x` is the
  side array at `$4c + x`. The local group on `m1_s0` is `$188`, so its food is `$516e4`.
- `scratchpad/pm98/repro93..97.py` hardcode `reuse_json=True`: they re-run only the reference side.
  The `py/` gates and pm98/pm99/pm115 `diff_*` re-run callcaps unless given `reuse`.
- REPL `m addr len` only dumps; `w addr long` writes a big-endian longword (read the neighbouring word
  first) — this pass used it to poke `word[$57fd0]` alone: `w 57fd0 00000188` keeps `$57fd2`'s `$0188`
  intact. `bpc <addr> <n>` counts hits **from the current position**, not cumulatively from cold boot —
  chaining `bpc addr 1`, `bpc addr 2`, `bpc addr 3` to get the 1st/2nd/3rd occurrence over a whole run
  is wrong; each call needs `n=1`.
- **`sides.py`/`group.py`/`snap2ram.py` need a flat `.ram` image, not a `.snap`** (the `.snap`
  format has a ~340-byte header the scripts' hardcoded absolute addresses don't account for, and
  reading it directly throws a `struct.error` well into the output, not a clean early failure).
  `reversing/powermonger/py/snap2ram.py <snap>...` converts.
- Mission 1's player town is kind 11, not a capital, so `$5cde` refuses order `$0e` there.
- `py/clicks.py`: the pointer moves 1:1 and clamps at 0; `home` re-homes it. An order posted by a
  click runs during the click's own settle steps, so start `hits`/`watch`/`bp` before the click. For a
  census of the arrival, arm the icon, then `mouse down`, `hits ...`, `mouse up` (see the `o0e` run in
  strategy.md "What each order does"). A raw REPL token can be passed through with `:` for spaces
  (e.g. `"hits:30000000:158cc:163b8"`); only one `watch` range is live at a time. The order-icon
  screen coordinates and the minimap's direct cell-click mapping (`(x, y-6)` for `x<64, 6<=y<134`)
  are in strategy.md "The player's commands".
- `py/iconmap.py`'s edge loops count the edge they stop at; without that every icon is one tile off.
- The listing mis-disassembles data as code around `$6b5a`, `$14bb4`, `$4fa2`: resolve jump tables
  from a RAM image (`table + word[table + index]`).
- Land 60 cannot be won; its first run stretch starts at `scratchpad/pm120/k60_iso.snap`. Play Random
  Land leaves `$14e4e = 0` (AI off). The object table is `$51b66`, stride 50. Byte6 18 is unreachable.
  A full `pm_export.py` rerun regresses `entities.json` and `sprite_triggers.json`. Do not reopen the
  SingleStepTests track or `$4342`'s 8 proven branches.

## Next session

Open item 1: from `scratchpad/pm129/env5_12M.snap`, test the alliance effects on lord 15's town (`$06`/`$10`
accepted, `$1e` refused by the pointer test), watching `$31a6`/`$31b2`/`$31cc` and `$139da`/`$13b1e` with
`hits`. If that confirms the documented behaviour, take item 2 (the rest of the secrets audit), starting with the
`$5809a` writers and the link-mode/startup-string path, then item 3 (orders not yet seen naturally).
