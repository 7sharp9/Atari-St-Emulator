# PowerMonger: handoff

Updated 2026-09-23 by the session that ended at commit `6b02d71` (the 123rd PowerMonger pass, the
first on the Mac).

## Resume point

- Last commits of this workstream: `2b41237` (the player's commands, the executor table corrected,
  mission 1 won by clicks), `eb3332c` (diplomacy), `0b69940` (`tools/pm_fsm_diff.py` runs without
  pwsh), `6b02d71` (CLAUDE.md / DEVELOPING macOS lines).
- Working data: `M68000/scratchpad/` (gitignored). On the Mac it was copied from gpubox (CLAUDE.md,
  "Shell pitfalls"); present: `powermonger.st` (Replicants, sha256 `2099be89…`), `pm67_ok_pre`,
  `pm69.st`, `pm73`/`pm74`/`pm78`/`pm88` anchors, `pm92..pm99`, `pm113`, `pm115`, `pm120..pm123`.
  Anchors indexed in `scratchpad/ANCHORS.md`. Whole-image listing `scratchpad/pm122/game_all.asm`.
- Start from: `scratchpad/pm123/win/m1_s0.snap` (mission 1 settled, player 26 : enemy 20, nothing
  ordered) for following the player's icon orders; `pm123/win/l1_built.snap` (land 1 of the
  campaign, just built); `pm121/run/k60_s2.snap` for 4-side work. Rebuild the win snapshots with
  `reversing/powermonger/py/drive_win.sh` (7 min, byte-identical across runs).
- Uncommitted work left behind: none.

## Proven so far

Gates (differential tests vs the real 68000 through `callcap`), all re-run fresh on macOS this pass
with the same counts: entity FSM `scratchpad/pm98/repro93..97.py` 675/1335/413/85/99; `$3c08`
`pm98/diff_pm98.py` 71/71; `$37c2`/`$1d70`/`$1b8c` `pm99/diff_pm99.py` 1847/1847; `$4bc8`
`pm115/diff_4bc8.py` 51/51 + `diff_4bc8_kind2.py` 20/20; `py/diff_1623c.py` 275/275;
`py/diff_2776.py` 4119/4119; `py/diff_5cde.py` 768/768; `py/diff_revolt.py` 1778/1778.

- Renderer and port pixel-exact (27 later-land frame pairs, `py/score.fsx`, `port/SPEC.md` §6).
- The player's commands (strategy.md "The player's commands"): every text panel and button
  (`py/panels.py`), the minimap / compass / captain boxes, and the 20 floor icons with screen
  positions (`py/iconmap.py`); orders go straight into the local slot `[$58034]`. The executor table
  is based at `$6b5a` (the old doc was one entry off): 12/12 dispatches checked on the real CPU.
- A natural victory by clicks only (strategy.md "How a land ends"): sword + minimap on lord 0 →
  8 engages, one `$550e` defection, ratio 4 → RETIRE → `$d304` writes `$3f2a0[0]` → Continue
  Conquest → land 1 built. Control run with no order: no fight, no defection, ratio 2.
- Diplomacy (strategy.md "Diplomacy"): alliance = peace bits `+6`; offered only by the player (order
  `$1e`, envoy → `$33b0`, tribute from carried goods), accepted via `$2a` → `$34a8` (reproduced
  byte-identical, forced arrival), broken by any contact (`$4c2a`). It changes only `$3154`'s
  friendly test (order `$06` refused → accepted, 1/1 each) and the pointer test `$1394c`. Three
  relation-byte bugs (`$311a` off-by-one + unsigned, `$33b0`, `$68fe`). Report
  `scratchpad/pm123/diplo/REPORT.md`.
- The campaign, how a land ends, defeat both ways (122nd; strategy.md).

## Open, in priority order

1. **Name the undecoded icon orders**: `$02` `$3888`, `$04` `$1c18`, `$06` `$38ce`, `$10` `$6128`,
   `$12`/`$18` `$39d4`, `$14` `$1cc4`, `$16` posture `$35a0`, `$1a` `$390e`, `$20` `$1d36`. On
   `pm123/win/m1_s0.snap`, arm each with `py/clicks.py` (icon centres in strategy.md), click a target
   (own / enemy settlement, a man), follow with `watch` on the group `$51538+$13c` and `hits` on the
   handler; name each from its effect (goods, men, equipment). This unblocks food, supply and a
   natural alliance.
2. **Conquest in the field, mode `$2c`**: the win's defection came from `$550e` only after the attack
   (loyalty 608 alone does nothing). Decode the `$4fa2` table (`$152f6` → `$4f68`), prove `$539a`
   (the `$550e` arm) with a callcap gate over natural states (`tools/capture_hits.py` on
   `pm123/win/m1_atk.snap`, returns at `$53fa`).
3. **A natural alliance by clicks**: icon `$1e` on an enemy settlement with goods carried
   (`supply_acc`, filled by item 1's supply order), the envoy reaching the lord without contact.
   Proof: `$34a8` writes without pokes. The panel-`$1a` branch (an envoy to the player) is static
   only and probably needs linked play.
4. **Food**: what refills `byte45` (drain `$5c80`), what the HUD food shows, what `$5bd2` needs.
   Likely falls out of item 1.
5. **`$1b8c` via `$5778`**: a callcap gate over natural `$5778` states.
6. **`$4342` arrival/unlink branch**: hangs under synthesised pokes (`scratchpad/pm113/diff_4342.py`);
   try natural states from `capture_hits.py`.
7. Smaller: weather in the stepper/Godot view; where the crack writes its `$b842` patch; the
   fixed-map `$df52(7)` branch; `$2df98` is "the other button" (inferred right).

## Known traps

- `py/clicks.py`: the pointer moves 1:1 and clamps at 0; `home` re-homes it. An order posted by a
  click is executed during the click's own settle steps, so start `hits`/`watch`/`bp` before the
  click, not after the snapshot (the `$6c32` and `$d2c8` counts were missed that way).
- `py/iconmap.py`'s edge loops count the edge they stop at (the game does `addq` before the
  compare); without that every icon is one tile off.
- Land 60 cannot be won (player 14 vs enemy 142 in the field); use mission 1 / campaign lands.
- Land 60's first run stretch starts at `scratchpad/pm120/k60_iso.snap`; there is no `pm121/k60.snap`.
- Play Random Land leaves `$14e4e = 0` (AI block off); use campaign or poked lands, or poke
  `$14e4e := $2c`.
- The object table is `$51b66`, stride 50; `$4c12c`, stride 26, is the small-object pool.
- `$2776` reads the command slot at `$58016 + 3*side`; `$5c2c` sets D2, not D3 (game bugs, transcribed).
- Byte6 18 is unreachable; do not chase it. A full `pm_export.py` rerun regresses `entities.json` and
  `sprite_triggers.json` (restore with `git checkout`). Do not reopen the SingleStepTests track or
  `$4342`'s 8 proven branches.

## Next session

Open item 1: on `scratchpad/pm123/win/m1_s0.snap`, click each undecoded icon (`py/clicks.py`,
centres in strategy.md "The player's commands") onto a sensible target and name its order from what
the group and ledgers do; write the table into strategy.md. Then item 2 as a parallel subagent (brief
from `scratchpad/pm123/diplo/BRIEF.md` as the template). Re-run every gate fresh before committing.
