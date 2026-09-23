# PowerMonger: handoff

Updated 2026-09-24 by the session that ended at commit `f298bdc` (the 124th PowerMonger pass, on the
Mac).

## Resume point

- Last commits of this workstream: `72edd33` (every player order named; lord `+6` is food; the
  "objective slots" are the side's groups), `15cda1b` (how land changes side: conquest `$539a` and
  the heartbeat revolt, `$4f68` decoded and gated), `9e89ccb` (CLAUDE.md / skill lessons), `f298bdc`
  (group field 60 is the posture).
- Working data: `M68000/scratchpad/` (gitignored; on the Mac copied from gpubox, CLAUDE.md "Shell
  pitfalls"). New this pass: `scratchpad/pm124/` (one directory per order run, controls `ctl`/`ctl25`,
  `fooddrain/`, `conquest/` with the `$4f68` corpus and `REPORT.md`), indexed in `scratchpad/ANCHORS.md`.
- Start from: `scratchpad/pm123/win/m1_s0.snap` (mission 1 settled: our 26-man group `$188` at
  (40,51), food 251, posture 3; lords 0/1 on side 2). `pm123/win/l1_built.snap` is campaign land 1,
  just built. Rebuild the win snapshots with `reversing/powermonger/py/drive_win.sh` (7 min).
- Uncommitted work left behind: none.

## Proven so far

Gates (differential tests vs the real 68000 through `callcap`), all re-run this pass after the
`call_35f4` fix: entity FSM `scratchpad/pm98/repro93..97.py` 675/1335/413/85/99; `pm98/diff_pm98.py`
71/71; `pm99/diff_pm99.py` 1847/1847; `pm115/diff_4bc8.py` 51/51 + `diff_4bc8_kind2.py` 20/20;
`py/diff_1623c.py` 275/275; `py/diff_2776.py` 4119/4119; `py/diff_5cde.py` 768/768 + 85/85;
`py/diff_revolt.py` 1778/1778; **new** `py/diff_4f68.py` 1804/1804 over 192 states (170 natural).

- **Every player order** (strategy.md "What each order does"): each clicked on `m1_s0` against a
  no-order control, 1 run each, reproducible byte-identically with `py/order_run.sh`. An order's
  meaning is its lead's arrival mode; every amount is `x >> (posture - 2)`.
- **Food** (economy.md §1, §6): lord `+6` is the town's food store; group `+36` is the army's food
  (the captain panel labels it "Food:"). Orders `$06`/`$12` move exactly `food >> shift` between them
  (22 → 11 into the army, 258 vs the control's 247). An army eats `men/8 + 1` per period in `$3e06`
  (`watch $516e4`: 2/2 writes at `$3f6a`, 251 → 247 → 243).
- **`$51538` is one record per side**; its six-word arrays are the side's six groups (the captain
  panel `$9090` reads them). The AI's "budget" `+112` is the group's food; `$68ee` charges a march at
  the eating rate. Fixed in strategy.md: `$6564` besieges with fewer than 22 men; the escort step
  follows group 0; `$6762` emits its table's order type and sets the posture.
- **How land changes side** (economy.md §3, ai.md mode `$2c`): field conquest (`$4f68` → `$5240` →
  `$539a` → `$550e` when every man of the lord's settlements is dead or routed; the mission-1 win) and
  the heartbeat revolt (mode `$7c`, or `$7e` with no `$57fd0` gate; hunger +2, plenty −1, at 600 the
  side becomes `(x cell mod 4) + 1`; the spy run).
- Earlier: renderer/port pixel-exact (`py/score.fsx`), the UI (panels, icons, `py/iconmap.py`), the
  natural win, diplomacy, the campaign, defeat both ways.

## Open, in priority order

1. **Starvation and hunger, driven by the player.** Proven only statically: at food < 0 each man
   deserts with chance 1/8 (`$3f72..$3faa`). On `m1_s0`: posture 2 (97,156), drop food (142,193), march
   (order `$02`) and `watch $516e4` + `hits 3fa0 1b8c` until a desertion; count the men lost against
   the 1/8 rule. Then a revolt made by the player: take a town's food until `field·4 >= food`, then
   pulse it (a dismissed man at home or a spy, mode `$7e`) and catch `$158cc`.
2. **A natural alliance by clicks** (strategy.md "Diplomacy"): carried goods are the tribute, and
   they now have a path: take equipment (`$10`) from an own town with goods, or trade (`$1c`). Mission
   1's lord has no goods and no capital; try `l1_built.snap` (census the lords with `py/sides.py`).
   Proof: `$34a8` writes without pokes.
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

- Group offsets: `D2` / `42(obj)` / `$57fd2` = `side*$13c + $4c + 2k`; a group field `x` is the
  side array at `$4c + x`. The local group on `m1_s0` is `$188`, so its food is `$516e4`.
- `scratchpad/pm98/repro93..97.py` hardcode `reuse_json=True`: they re-run only the reference side.
  The `py/` gates and pm98/pm99/pm115 `diff_*` re-run callcaps unless given `reuse`.
- REPL `m addr len` only dumps; `w addr long` writes a big-endian longword (read the neighbouring word
  first). `drive_win.sh`'s `m:` tokens are dumps.
- Mission 1's player town is kind 11, not a capital, so `$5cde` refuses order `$0e` there.
- `py/clicks.py`: the pointer moves 1:1 and clamps at 0; `home` re-homes it. An order posted by a
  click runs during the click's own settle steps, so start `hits`/`watch`/`bp` before the click. For a
  census of the arrival, arm the icon, then `mouse down`, `hits ...`, `mouse up` (see the `o0e` run in
  strategy.md "What each order does").
- `py/iconmap.py`'s edge loops count the edge they stop at; without that every icon is one tile off.
- The listing mis-disassembles data as code around `$6b5a`, `$14bb4`, `$4fa2`: resolve jump tables
  from a RAM image (`table + word[table + index]`).
- Land 60 cannot be won; its first run stretch starts at `scratchpad/pm120/k60_iso.snap`. Play Random
  Land leaves `$14e4e = 0` (AI off). The object table is `$51b66`, stride 50. Byte6 18 is unreachable.
  A full `pm_export.py` rerun regresses `entities.json` and `sprite_triggers.json`. Do not reopen the
  SingleStepTests track or `$4342`'s 8 proven branches.

## Next session

Open item 1: on `scratchpad/pm123/win/m1_s0.snap`, starve our army (posture 2, drop food, march) and
watch the desertions against the 1/8 rule, then make a revolt by taking a town's food and pulsing it.
Write the result into economy.md §6 and strategy.md "`$d322` + `$3e06`". Then item 2 on
`l1_built.snap` as a parallel subagent (brief template: `scratchpad/pm124/conquest/BRIEF.md`).
Re-run every gate before committing.
