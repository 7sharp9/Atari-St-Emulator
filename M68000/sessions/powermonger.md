# PowerMonger: handoff

Updated 2026-09-25 by the session that ended at commit `bd63bc2` (the 125th PowerMonger pass, on the
Mac).

## Resume point

- Last commits of this workstream: `bd63bc2` (revolt digest line corrected), `0632e0a` (CLAUDE.md:
  grep topic docs before decoding a routine), `5ea6e25` (starvation desertion driven live; hunger-
  revolt parking narrowed).
- Working data: `M68000/scratchpad/` (gitignored; on the Mac copied from gpubox, CLAUDE.md "Shell
  pitfalls"). New this pass: `scratchpad/pm125/starve/`, `pm125/starve2/` (the starvation run and
  its per-tick breakdown), `pm125/revolt/` (the dismiss-at-home negative result), indexed in
  `scratchpad/ANCHORS.md`.
- Start from: `scratchpad/pm123/win/m1_s0.snap` (mission 1 settled: our 26-man group `$188` at
  (40,51), food 251, posture 3; lords 0/1 on side 2). Rebuild with `reversing/powermonger/py/drive_win.sh` (7 min) if missing.
- Uncommitted work left behind: none of this session's. Pre-existing, not this session's and not
  touched: `CLAUDE.md` and `M68000/sessions/README.md` both had an uncommitted pure line-rewrap
  (no content change) at session start from Obsidian editing the repo (`.obsidian/` is untracked in
  the tree). `CLAUDE.md`'s copy is stashed (`git stash list`, "obsidian reflow of CLAUDE.md") so this
  session's own CLAUDE.md edit could land cleanly; `sessions/README.md`'s is still sitting
  uncommitted in the working tree, untouched. Also untracked: `Cadaver/` (another workstream's game
  files). Not mine to resolve — flag to Dave or the cadaver session.

## Proven so far

Gates (differential tests vs the real 68000 through `callcap`), unchanged this pass, not re-run
(no reference transcription or gate script touched — see "Known traps"): entity FSM
`scratchpad/pm98/repro93..97.py` 675/1335/413/85/99; `pm98/diff_pm98.py` 71/71; `pm99/diff_pm99.py`
1847/1847; `pm115/diff_4bc8.py` 51/51 + `diff_4bc8_kind2.py` 20/20; `py/diff_1623c.py` 275/275;
`py/diff_2776.py` 4119/4119; `py/diff_5cde.py` 768/768 + 85/85; `py/diff_revolt.py` 1778/1778;
`py/diff_4f68.py` 1804/1804.

- **Every player order, food, group-record fields, conquest, the heartbeat revolt mechanism**: see
  the 124th's summary in git history (`5ea6e25`'s parent) — unchanged this pass.
- **Starvation desertion, driven live (125th).** `m1_s0`, posture 2, `$12` drop food (empties the
  army to 0), `$02` march — 4 `$3f6a`/`$3f72` eat-and-clear ticks over 50M steps, `$1b8c` fires
  exactly once per desertion: roster 26 → 13 (per-tick 3/26, 5/23, 4/18, 1/14 — 13/81 total, 16.0%
  against the 1/8 rule, inside 1σ for four trials this small). Deserters are not lost: the local
  lord's `troops_field` rose 0 → 13, the same destination as an order-`$14` dismiss — starvation
  desertion is mechanically a forced dismiss, LCG-triggered. strategy.md "`$d322` + `$3e06`",
  economy.md §6. `scratchpad/pm125/starve/`, `pm125/starve2/`.
- **The `dwell := $ff9d` / `$ff9c` marker-parking gate, re-derived from disassembly and confirmed to
  match the existing 96th/97th pseudocode exactly** (economy.md §3a, ai.md) — no doc change needed
  there, but see "Known traps" for the time this cost.
- **Negative result: dismissal does not park a fresh marker (125th).** `m1_s0`, posture 2, `$06`
  took our own town's food to 0, `$14` dismissed all 26 men home (`troops_field` 0 → 26); 30M steps,
  104 `$163b8` settlement pulses, **zero** hunger/plenty loyalty adjustments. `loyalty_pressure`'s
  observed 0 → 16 is fully explained by `$06`'s own `+16 >> (posture-2)` order effect, not any
  pulse. Narrows the open "revolt by clicks" question: the parking trigger is not the dismiss order.
  economy.md §3a, `scratchpad/pm125/revolt/`.

## Open, in priority order

1. **What sets `dwell := $ff9d`** (economy.md §3a "still open"). Ruled out: the dismiss order.
   Likely site: `$3c08`'s arrival-mode dispatch (the `$57fd0`-off regroup path that switches an
   existing marker into mode `$7e`/`$16`/`$4e`/`$5e`/`$80` depending on the settlement's owner-
   category bits, `btst #4,7(settl)` etc. — not traced this pass) — or the mode-`$7e` handler's own
   entry code (spy arrival is `$3da4`, proven 124th to reach a gate-free pulse, but not proven to
   itself set `$ff9d` vs. just landing in a steady `D5==0` cycle). Concretely: watch `18(A1)` for a
   marker across a longer natural run to catch `$ff9d` appearing, or trace `$3c08`'s three call
   sites and the mode-`$7e`/`$16`/`$4e`/`$5e`/`$80` handlers each targets. Once found: reproduce the
   "hunger revolt by clicks" scenario (our own town, `troops_field·4 >= food`, force a park) end to
   end and watch `$158cc` fire.
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
  first). `drive_win.sh`'s `m:` tokens are dumps. `bpc <addr> <n>` counts hits **from the current
  position**, not cumulatively from cold boot — chaining `bpc addr 1`, `bpc addr 2`, `bpc addr 3` to
  get the 1st/2nd/3rd occurrence over a whole run is wrong; each call needs `n=1` (this pass caught
  it before running the (wrong) 30M-step version).
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

Open item 1: find what sets `dwell := $ff9d`. Start by tracing `$3c08`'s three call sites (grep
`bsr $3c08` / `jsr $3c08.l` in `scratchpad/pm122/game_all.asm`) and the mode handlers it hands off
to (`$7e`, `$16`, `$4e`, `$5e`, `$80` — their own entry code, not `$157e6` which only *consumes*
`18(A1)`), or watch `18(A1)` for several markers across a `pm97_map0`-style long natural run to
catch the moment it becomes `$ff9d`. Once found, reproduce a player-triggered hunger revolt on our
own mission-1 town end to end (`troops_field·4 >= food`, force the park, catch `$158cc`) and write
it into economy.md §3a / README.md's revolt digest line. Then item 2 (diplomacy) on `l1_built.snap`.
Re-run every gate before committing anything that touches a reference transcription.
