# PowerMonger: handoff

Updated 2026-09-25 by the session that ended at commit `37212b7` (a Mac-side pass on the port's
frame stepper and the blog draft, not the game-mechanics thread below -- see "Proven so far").

## Resume point

- Last commits of this workstream: `37212b7` (port README: index `--playtest`), `338fae8` (stepper:
  wire in `Weather.fs`, fix continuous play, add `--playtest`) -- this pass, tooling only. Last
  commits touching the **game-mechanics thread** (unchanged this pass, still current): `53c5408`
  (ANCHORS: index the 127th's organic take-equipment state), `79e1c3f` (strategy.md: natural
  alliance test, take-equipment confirmed, envoy dies to contact twice), `816c786` (README: correct
  stale revolt bullet, add topic-doc index table), `b31c50f` (economy.md: revolt reachability was
  already proven, "still open" was stale).
- Working data: `M68000/scratchpad/` (gitignored; on the Mac copied from gpubox, CLAUDE.md "Shell
  pitfalls"). New this pass: `scratchpad/pm127/diplo3/` (`equip_probe.snap`/`.ram` — land 25's
  side-1 group after a real, unpoked take-equipment click; `alliance1.snap` — the same group after
  dying to hostile contact en route to a foreign lord), indexed in `scratchpad/ANCHORS.md`.
  `pm127/diplo/` and `pm127/diplo2/` are dead ends (mission 1 has zero goods anywhere; a 450M-step
  march on land 0 starved a group to death) — not reusable, left as-is.
- Start from: `scratchpad/pm123/win/m1_s0.snap` (mission 1 settled: our 26-man group `$188` at
  (40,51), food 251, posture 3; lords 0/1 on side 2), unchanged this pass. For anything touching the
  live goods economy, mission 1 itself has **no goods anywhere** (every lord's `goods[]` is zero) —
  use a natural land corpus instead (`scratchpad/pm121/run/`, `ANCHORS.md`).
- Uncommitted work left behind: none in this repo. Outside this repo: the blog draft
  `~/GitHub/7sharp9.github.io/content/Programming/2026-09-22-paint-it-black.md` (+4 images in
  `static/images/posts/powermonger/`) had its factual claims (match percentages, the six-capture
  table) brought current against `port/SPEC.md`; the personal TODOs (motivation, the extra-row
  bug's cost, the Godot-route verdict) are still Dave's to fill in. Committed in that repo
  (`4701fbc`) but not pushed as of this pass — that repo's `git status`/`git log
  origin/master..HEAD` will show if it still needs a push.
- Pre-existing, not this session's and not touched: `M68000/sessions/README.md` still carries an
  uncommitted pure line-rewrap (no content change) from Obsidian editing the repo (`.obsidian/` is
  untracked in the tree). Also untracked: `Cadaver/` (another workstream's game files). Not mine to
  resolve — flag to Dave or the cadaver session.

## Proven so far

Gates (differential tests vs the real 68000 through `callcap`), unchanged this pass, not re-run
(no reference transcription or gate script touched): entity FSM
`scratchpad/pm98/repro93..97.py` 675/1335/413/85/99; `pm98/diff_pm98.py` 71/71; `pm99/diff_pm99.py`
1847/1847; `pm115/diff_4bc8.py` 51/51 + `diff_4bc8_kind2.py` 20/20; `py/diff_1623c.py` 275/275;
`py/diff_2776.py` 4119/4119; `py/diff_5cde.py` 768/768 + 85/85; `py/diff_revolt.py` 1778/1778;
`py/diff_4f68.py` 1804/1804.

- **This pass's own work is the port's frame stepper, not the game-mechanics thread**: `Weather.fs`
  (rain/snow, `$1a856`) is now wired into `port/stepper` for the first time anywhere (it existed but
  nothing rendered it, not the stepper, not Godot's `TerrainView.cs`) -- `C` toggles it, kind picked
  by season. Continuous play (`P`) now actually loops instead of stopping dead at the end of the
  frame, and survives a pan/rotate/zoom/season change instead of silently re-pausing (`withView` no
  longer forces `Playing = false`); `Space` single-steps instead of duplicating `P`. Both bugs were
  only caught by Dave running the interactive window and reporting the console trace / what he saw
  -- `--shot`/`--selfcheck` alone didn't catch either. New `--playtest` (`port/stepper/Program.fs`)
  drives Mibo's real `HeadlessRunner`/`ElmishLoop` through two loops, a camera/season change
  mid-loop, and a manual step, and is now the regression check for this. Commits `338fae8`/`37212b7`.
- **Every player order, food, group-record fields, conquest, the heartbeat revolt mechanism,
  starvation desertion, what sets `dwell := $ff9d`, mode `$16` as a garrison/neutral marker**: see
  the 125th/126th's summaries in git history — unchanged this pass.
- **Revolt reachability was already proven, and the "still open" framing in economy.md/README was
  stale (127th).** The 122nd pass's `diff_revolt.py` (1778/1778 over 49 states) already showed the
  settlement heartbeat's `$7c`/`$16` self-cycle crossing loyalty 600 unassisted: 11 of 27 natural
  `$550e` defections on four 200M-step no-input land runs came from the heartbeat at loyalty
  600-608 (`ai.md` "The revolt chain"). The 125th/126th passes re-opened this as a fresh question
  without checking the existing proof; caught per CLAUDE.md's rule to grep for a retired framing
  before reusing it, no new emulator run needed. Fixed in `economy.md` §3a and the README design
  digest. The narrower question — is the settlement's own `$7c` marker literally the same object
  that feeds the mode-`$16` traffic — stays open (unchanged from before).
- **Take-equipment genuinely fills a group's `carrying[]`/`supply_acc[]` from a real stockpile, no
  pokes (127th, live).** Land 25's side-1 group (8 men) sent to its own lord 7's town with order
  `$10` came back carrying 3 pots pulled from lord 7's actual `goods[]` — confirms economy.md §2c's
  `$61f8`/`$6352` claim under fully organic conditions. `scratchpad/pm127/diplo3/equip_probe.snap`.
- **An unescorted natural-goods envoy dies to contact before offering an alliance — confirmed twice
  independently (123rd forced-goods, 127th fully organic).** Same group, still carrying its 3 pots,
  sent toward the nearest foreign lord (7 cells) with order `$1e`: hostile contact at 13M steps
  (`$4c2a` fired, not `$33b0`/`$34a8`) wiped it out, goods dropped as a ground pile. strategy.md
  "Diplomacy".

## Open, in priority order

1. **A natural alliance completing end to end** (strategy.md "Diplomacy"): the tribute side is now
   proven organic (take-equipment genuinely loads `carrying[]`); what's missing is the envoy
   surviving the walk. Two natural corpora both had it killed by unrelated hostile contact first.
   Next attempt needs either an **escort** (a second, stronger group clearing/holding the corridor
   ahead of the envoy) or a **much earlier snapshot** (before a land's territory has had 100M+ steps
   to become contested) — proximity to a goods-bearing lord alone isn't enough. `$34a8` firing
   without any poke is the proof bar.
2. **The orders not yet seen naturally**: `$04` transfer (needs two captains, a later land), `$0e`
   on a real capital (does the work order produce pots naturally?), `$10`/`$06` on a food pile, the
   `$1a` supply line over several loops (food delivered per loop).
3. **What refills strength** (lead/man byte 45, the captain panel's "Strength:", drained by `$5c80`);
   the old "food" item 4 reads byte 45 wrongly. Watch byte 45 of a man over a march with and without
   food.
4. `$1b8c` via `$5778` (a gate over natural `$5778` states); `$4342`'s arrival/unlink branch
   (`scratchpad/pm113/diff_4342.py`, natural states from `capture_hits.py`); `$4f68` arms not covered
   (`$51dc` finding an ally's target, `$548a`'s `39 == 2`).
5. Smaller: weather is now in the stepper (`C` key, this pass) but still not in the Godot view
   (`godot/game/TerrainView.cs` has no `Weather` reference); where the crack writes its `$b842`
   patch; the fixed-map `$df52(7)` branch; `$2df98` is "the other button" (inferred right); the port
   and stepper still use the old names (`troops_reserve`, budget, discipline) if they model them.
6. **A deeper game summary/mechanics writeup**, if Dave wants to keep extending it toward
   populous's depth: the README now opens with a doc-index table (added 127th) and the Design
   digest is current; a further step would be an explicit "architecture" thread (per-tick dispatch,
   core data structures, which mechanics are instances of a shared idiom) the way
   `reverse-engineer-st-game`'s §7 describes, if the topic docs don't already read that way on a
   fresh pass.

## Known traps

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

This pass's own work (stepper weather, continuous-play fixes, the blog draft) is committed/wrapped
and does not block the game-mechanics thread below.

Open item 1: a natural alliance completing end to end. Start from
`scratchpad/pm127/diplo3/equip_probe.snap` (land 25, our 8-man group already carrying 3 pots, no
pokes) — either build a second, stronger group and send it ahead as an escort to clear the corridor
toward the nearest foreign lord before sending the envoy, or find/build an earlier land snapshot
(before ~100M steps of natural drift) where the same lord pairing hasn't gone hostile yet. Watch
`33b0`/`34a8`/`c706`/`4c2a` with `hits` to see which one fires. A clean "the escort worked, `$34a8`
fired with real, unpoked tribute" is the target; a second contact-death is still useful negative
data for strategy.md. If that stalls, item 2 (the orders not yet seen naturally) is next.
