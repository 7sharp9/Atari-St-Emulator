# PowerMonger: handoff

Updated 2026-09-25 by the session that ended at commit `3a05c78` (the 126th PowerMonger pass, on the
Mac).

## Resume point

- Last commits of this workstream: `3a05c78` (design digest: revolt's park pulse is a garrison
  marker's own cycle, not player-reachable), `7bca7eb` (economy.md §3a / ai.md: `dwell := $ff9d`
  proven live, mode `$16` traced to a world-build garrison flag, not player dismiss).
- Working data: `M68000/scratchpad/` (gitignored; on the Mac copied from gpubox, CLAUDE.md "Shell
  pitfalls"). New this pass: `scratchpad/pm125b/` (the forced-`$57fd0`=0 isolation, the one-deserter
  end-to-end trace, and a natural no-click mode-`$16` capture), indexed in `scratchpad/ANCHORS.md`.
- Start from: `scratchpad/pm123/win/m1_s0.snap` (mission 1 settled: our 26-man group `$188` at
  (40,51), food 251, posture 3; lords 0/1 on side 2). Rebuild with `reversing/powermonger/py/drive_win.sh` (7 min) if missing.
- Uncommitted work left behind: none of this session's. Pre-existing, not this session's and not
  touched: `M68000/sessions/README.md` still carries an uncommitted pure line-rewrap (no content
  change) from Obsidian editing the repo (`.obsidian/` is untracked in the tree). Also untracked:
  `Cadaver/` (another workstream's game files). Not mine to resolve — flag to Dave or the cadaver
  session.

## Proven so far

Gates (differential tests vs the real 68000 through `callcap`), unchanged this pass, not re-run
(no reference transcription or gate script touched): entity FSM
`scratchpad/pm98/repro93..97.py` 675/1335/413/85/99; `pm98/diff_pm98.py` 71/71; `pm99/diff_pm99.py`
1847/1847; `pm115/diff_4bc8.py` 51/51 + `diff_4bc8_kind2.py` 20/20; `py/diff_1623c.py` 275/275;
`py/diff_2776.py` 4119/4119; `py/diff_5cde.py` 768/768 + 85/85; `py/diff_revolt.py` 1778/1778;
`py/diff_4f68.py` 1804/1804.

- **Every player order, food, group-record fields, conquest, the heartbeat revolt mechanism,
  starvation desertion**: see the 125th's summary in git history (`9964df2`'s parent) — unchanged
  this pass.
- **What sets `dwell := $ff9d`, live-confirmed (126th).** The write is `$015052`, inside entity
  mode `$16`'s handler (`$015042`), gated on `word[$57fd0] == 0`. Isolated with a forced-poke test:
  0/28 natural mode-`$16` entries parked while `$57fd0` stayed nonzero over 100M steps; forcing
  `word[$57fd0] := 0` (`w 57fd0 00000188`) on the same state made the very next entry park — 1/3
  over a further 150M steps, at the one step `$57fd0` read 0. economy.md §3a, `scratchpad/pm125b/`.
- **Mode `$16` is a garrison/neutral-village mechanism, not a player one (126th, live-traced).**
  `$3c08` only picks `prev_mode := $16` for a record whose flags byte has bit 0 set; the sole site
  that sets that bit anywhere in the image is `$002cd0`, a world-build site-scan for neutral
  villages/garrisons. Traced one starvation deserter (entity `$52462`) end to end from `$1b8c`
  through `$3c08`'s **"no flags set" default** (`prev_mode := $7e`) to arrival — it never touches
  `$16`. Mode `$7e` runs the same heartbeat body ungated but with no fresh dwell reset, so the
  `D5 == $ff9c` loyalty edge cannot fire for a unit that arrives this way — this is *why* the
  125th's dismiss/starve test saw zero loyalty adjustments over 104 pulses. The design digest's
  "revolt" bullet and ai.md's `$16`/`$7e` rows now reflect this. economy.md §3a, README.md "Design
  digest", `scratchpad/pm125b/`.

## Open, in priority order

1. **Does a settlement's own `$7c` marker ever cross loyalty 600 unassisted?** Now that the park
   write is pinned to mode `$16`'s `$57fd0`-gated branch and shown to be a garrison-marker cycle
   independent of player action, the open question is whether *revolt itself* is ever reachable at
   all, or only ever an inert cycle. Concretely: run 400M+ steps (several `$57fd0` rotations,
   ~110M steps each) from a snapshot with active garrison markers, watching `loyalty_pressure` on
   each lord across their marker's own `$7c` ⇄ `$16` transitions, and check whether it can reach
   600 without any player order ever touching that lord's town. A negative result over several
   rotations would mean "Revolt" needs re-labelling as effectively dead code in mission 1 rather
   than an inferred-reachable mechanic.
2. **A natural alliance by clicks** (strategy.md "Diplomacy"): carried goods are the tribute, and
   they now have a path: take equipment (`$10`) from an own town with goods, or trade (`$1c`).
   Mission 1's lord has no goods and no capital; try `l1_built.snap` (census the lords with
   `py/sides.py`). Proof: `$34a8` writes without pokes.
3. **The orders not yet seen naturally**: `$04` transfer (needs two captains, a later land), `$0e`
   on a real capital (does the work order produce pots naturally?), `$10`/`$06` on a food pile, the
   `$1a` supply line over several loops (food delivered per loop).
4. **What refills strength** (lead/man byte 45, the captain panel's "Strength:", drained by `$5c80`);
   the old "food" item 4 reads byte 45 wrongly. Watch byte 45 of a man over a march with and without
   food.
5. `$1b8c` via `$5778` (a gate over natural `$5778` states); `$4342`'s arrival/unlink branch
   (`scratchpad/pm113/diff_4342.py`, natural states from `capture_hits.py`); `$4f68` arms not covered
   (`$51dc` finding an ally's target, `$548a`'s `39 == 2`).
6. Smaller: weather in the stepper/Godot view; where the crack writes its `$b842` patch; the
   fixed-map `$df52(7)` branch; `$2df98` is "the other button" (inferred right); the port and stepper
   still use the old names (`troops_reserve`, budget, discipline) if they model them.

## Known traps

- **Grep the topic docs for a routine's address before disassembling it.** This pass spent a full
  read of `$157e6`'s body only to reproduce, line for line, the pseudocode economy.md §3a and
  ai.md already had from the 96th/97th pass (now in `CLAUDE.md`'s Rules).
- Group offsets: `D2` / `42(obj)` / `$57fd2` = `side*$13c + $4c + 2k`; a group field `x` is the
  side array at `$4c + x`. The local group on `m1_s0` is `$188`, so its food is `$516e4`.
- `scratchpad/pm98/repro93..97.py` hardcode `reuse_json=True`: they re-run only the reference side.
  The `py/` gates and pm98/pm99/pm115 `diff_*` re-run callcaps unless given `reuse`.
- REPL `m addr len` only dumps; `w addr long` writes a big-endian longword (read the neighbouring word
  first) — this pass used it to poke `word[$57fd0]` alone: `w 57fd0 00000188` keeps `$57fd2`'s `$0188`
  intact. `bpc <addr> <n>` counts hits **from the current position**, not cumulatively from cold boot —
  chaining `bpc addr 1`, `bpc addr 2`, `bpc addr 3` to get the 1st/2nd/3rd occurrence over a whole run
  is wrong; each call needs `n=1`.
- **A bounded-window negative result over a `$57fd0`-gated routine proves nothing on its own.**
  `$57fd0` cycles `{0,2,4,6}` roughly once per 110M steps, so a window has to be sized (or `$57fd0`
  forced) relative to that period before "0 hits in N steps" can be read as "this path is dead" —
  this pass's first mode-`$16` breakpoint run (150M steps, 0 hits) was actually just a window that
  never crossed `$57fd0 == 0`, not a real negative result; the forced-poke re-run caught it.
- Mission 1's player town is kind 11, not a capital, so `$5cde` refuses order `$0e` there.
- `py/clicks.py`: the pointer moves 1:1 and clamps at 0; `home` re-homes it. An order posted by a
  click runs during the click's own settle steps, so start `hits`/`watch`/`bp` before the click. For a
  census of the arrival, arm the icon, then `mouse down`, `hits ...`, `mouse up` (see the `o0e` run in
  strategy.md "What each order does"). A raw REPL token can be passed through with `:` for spaces
  (e.g. `"hits:30000000:158cc:163b8"`); only one `watch` range is live at a time.
- `py/iconmap.py`'s edge loops count the edge they stop at; without that every icon is one tile off.
- The listing mis-disassembles data as code around `$6b5a`, `$14bb4`, `$4fa2`: resolve jump tables
  from a RAM image (`table + word[table + index]`).
- Land 60 cannot be won; its first run stretch starts at `scratchpad/pm120/k60_iso.snap`. Play Random
  Land leaves `$14e4e = 0` (AI off). The object table is `$51b66`, stride 50. Byte6 18 is unreachable.
  A full `pm_export.py` rerun regresses `entities.json` and `sprite_triggers.json`. Do not reopen the
  SingleStepTests track or `$4342`'s 8 proven branches.

## Next session

Open item 1: settle whether revolt is ever reachable at all. From a snapshot with several live
garrison/neutral markers (not `m1_s0` alone — census `$002cd0`'s targets first, or use a later,
busier land), run 400M+ steps with a `hits`/`watch` census on `$015042`/`$015052`/`$158a8`/`$015886`
(the mode-`$16` entry, the park write, and the loyalty `+2`/`-1` sites) spanning several `$57fd0`
rotations, and see whether any lord's `loyalty_pressure` crosses 600 unassisted. A clean negative
over multiple rotations is as valuable a result as a positive — it means "Revolt" belongs in the
design digest as an inferred-dead mechanic in mission 1, not an open trigger. Then item 2
(diplomacy) on `l1_built.snap`. Re-run every gate before committing anything that touches a
reference transcription.
