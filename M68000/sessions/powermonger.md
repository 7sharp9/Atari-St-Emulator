# PowerMonger: handoff

Updated 2026-10-01 by the 134th pass (the original names audited: the tree array, the farmer cycle, the live join under order `$08`).

## Resume point

- Last commit of this workstream: the 134th pass's handoff commit (`git log --oneline -4`); the work commit is just before it.
- Working data: `M68000/scratchpad/` (gitignored; on the Mac copied from gpubox, CLAUDE.md "Shell pitfalls"), indexed in
  `scratchpad/ANCHORS.md`. `pm134/trees/` (tree-felling run from `pm121/run/k5_s4.snap`), `pm134/join/` (order `$08` runs),
  `pm134/audit/` (`report.md` = the audit agent's findings, `all.asm`, census scripts, `live/` callcaps).
- Start from: `scratchpad/pm123/win/m1_ready.snap` (mission 1 conquered: lord 0's town is the player's, 5 men in its houses; the base of
  the `$08` join) or `pm123/win/m1_s0.snap` (settled, the base of every order run) or `pm121/run/k5_s4.snap` (land 5, gatherers running).
- Uncommitted work left behind: none from this workstream. Not this workstream's: `M68000/sessions/README.md` (an Obsidian line-rewrap),
  `.obsidian/`, `Cadaver/`.

## Proven so far

Gates (differential tests vs the real 68000 through `callcap`), unchanged and not re-run (no reference transcription or gate script
touched): entity FSM `scratchpad/pm98/repro93..97.py` 675/1335/413/85/99; `pm98/diff_pm98.py` 71/71; `pm99/diff_pm99.py` 1847/1847;
`pm115/diff_4bc8.py` 51/51 + `diff_4bc8_kind2.py` 20/20; `py/diff_1623c.py` 275/275; `py/diff_2776.py` 4119/4119; `py/diff_5cde.py`
768/768 + 85/85; `py/diff_revolt.py` 1778/1778; `py/diff_4f68.py` 1804/1804.

- **A man joins a group under order `$08` live (134th).** `py/join08_run.sh` from `m1_ready.snap`, rerun by the lead (the agent's counts
  reproduced: `$1b2a` 2, `$1d70` 2, `$1501a` 5, group 26 → 28, `troops_field` 5 → 3). Quota `46(lead) = troops_field >> (posture-2)`
  (aggressive 5 joins, neutral 2, passive 1, `troops_field` 7 poked: 3); every arrival decrements it first, so later men are refused and wait out
  `$2a`'s 50-tick dwell into `$3c08`. strategy.md "What each order does", ai.md `$2a`/`$14`.
- **`$4d252` is the tree array, not animals (134th).** 203 of 203 (land 0 settled) and 154 of 154 live entries sit on byte6-4 records, 0 on
  byte6-8 animals (`py/tree_census.py`). The gather chain `$3e`→`$44`→`$46`→`$42` felled 3 trees in 10M steps from land 5 (`$155ac` 28,
  `$156be` 24, `$15736`/`$60dc` 25 hits, `$5ec6` 0; one goods credit, the throttle); men of every job run it. economy.md §2 rewritten
  (kind table `$6062`, read from the code: kinds 4 and `$c` not run live).
- **`$1d70` is `_rerank`, a rank former by weapon class** (`$1e8c` maps weapon code 2/4/6 to P/S/B, read from RAM; agent's `callcap` with a
  poked mix placed swords row 0, bows row -2, pikes the rest), not a terrain route; it runs on every join and roster change.
- **Farmer cycle `$18`→`$0c`→`$0e`→`$24`→`$16` (audit agent)**: 275 of 281 `$0e` men are farmers, hits over 40M steps from `m1_s0`: `$15042` 10, `$150b0` 11,
  `$14e56` 11, `$151c2` 11. Mode `$68` is camp rest (118 of 123 byte6 14, rechecked by the lead). strategy.md "Original names".
- Earlier: the developer symbols from `DATA\SPRITE40.DAT`, order `$08` = get men, fishermen `$56..$62` (133rd); serial-link roles, ESC and
  chat (132nd); alliance effects (131st); no hidden keys (130th); a natural alliance (129th); every player order, revolt, starvation (125th/126th).

## Open, in priority order

1. **Finish the sweep of the audit's doc corrections.** `scratchpad/pm134/audit/report.md` lists them with line numbers: byte 33 = carried
   item code (modes `$02`/`$8c` boating, 71/71 and 17/17), byte 45 = health (`healthnames` at `$a2dc`; the docs say strength/morale in ~25 places),
   `$3f86c` = altitude plane (`_alts`; economy.md and ai.md still say "control byte"/"influence"), `$35f4` makes the camp, `$127e6`/`$178ae`/`$17878` labels,
   `$52`/`$54` merchant modes, `$16892`/mode `$90` equipment pickup, `$2984` is the village population, `troops_field` = the lord's men at home.
   The 134th applied only the farmer, camp, `$1d70`, tree and `$08` rows plus the "Original names" summary. Each static claim needs one live count
   (byte 45: `watch` on a melee, the `$912a` panel read; `$35f4`: `hits` on a natural camp; `$3f86c`: the writers of `$ffa6`, then the renderer's reads).
2. **Audit the rest of the 79 clashes in `powermonger.sym`**: the agent triaged them (most are synonyms); rename the `.sym` entries it marked D/R
   (`$002984`, `$014e70`, `$015042`, `$016048`, `$0161b2`, `$001d70`, `$001e9e`, `$3f86c`, `$00ffa6`, `$0127e6`, `$0178ae`, `$017878`, `$0157ba`, `$0157e6`),
   then `tools/merge_sym.py --write` to bring `powermonger_orig.sym` names in for unnamed addresses.
3. **What `$4c5f4` (`_birds`) shows on screen**: the markers are cosmetic (`$4342` is a no-op in natural captures); render one (byte6 `$16`, `$117b0`) and compare.
   Also who creates the byte6-8 animals (3 in `m1_s0`, 40 in `env5_12M`).
4. **The orders not yet seen naturally**: `$04` transfer (two captains), `$0e` on a real capital (now known to start the gather chain, `$5fa0`→`$5cde`), `$10`/`$06`
   on a food pile, the `$1a` supply line over several loops. The `$1b2a` other-side rule (read from the code, not run).
5. **What refills health** (byte 45, drained by `$5c80`): watch it over a march with and without food.
6. `$1b8c` via `$5778`; `$4342`'s arrival/unlink branch (`scratchpad/pm113/diff_4342.py`); `$4f68` arms not covered; weather not in the Godot view; the crack's
   `$b842` patch; the link handshake only if Dave wants multiplayer; a deeper game summary (the README digest is current).

## Known traps

- **`hits` after a `u` span starts counting at the end of that span.** Put `hits` straight after `u 13b9a`.
- **A refused click leaves `$57fd4` armed**: "`$57fd4` still equals the icon id and the order's `$6bxx` executor has 0 hits" is the refusal signal.
- **Mission 1's own town has no inhabitants, lord 0's town does only after conquest** (`m1_ready.snap`): a get-men test needs a populated town of the commander's side.
- **A `hits` run started from `clicked.snap` shows `$15122` 0**: the lead had already arrived; the hit is in the stage that ran to the arrival.
- **One entity tick (a dwell step) is about 200k steps, not a frame**: a 50-tick wait is ten million steps.
- **Negative record indices in a `callcap` JSON `mem` list are the call's own stack bytes.**
- **A symbol's address space depends on its type.** Text: offset + `$10a6`; bss (type `$a100`): value + `$1c48e`. Labels are the authors' words, not proof: the
  tree array shows a doc name and an original label can both be half right; settle with a census against an independent record set.
- **An unreferenced file on the disk may be a program.** A routine that runs once at startup cannot be tested by patching its input in a snapshot.
- **`$6a3a` dispatches slot state through the word table at `$6a80`, and the static listing around it is out of phase**; read tables from RAM (`m 6a80 14`). The order table is `$6b5a + word[$6b5a + type]`.
- **A make and break `kbd` pair sent together can vanish**: send the make, run to the checkpoint, then the break.
- **A raw `dotnet exec ... resume <snap> repl` needs `--disk-a <file.st>`, not `-DiskA`**; and `ATARI_NOTRACE=1`.
- **`sides.py`/`group.py`/`snap2ram.py` need a flat `.ram` image**; `py/snap2ram.py <snap>` converts.
- **Census the target's neighbourhood before choosing a route** (`census_lords.py`), and check a march's food-to-men ratio with a short probe first.
- **A subagent's "static" claim is a hypothesis**: the audit's weapon-class and camp claims held on a spot check, but its report is not a proof; re-count the one number each doc line rests on.
- `py/clicks.py`: the pointer moves 1:1 and clamps at 0; an order posted by a click runs during the click's settle steps. Group offsets: `side*$13c + $4c + 2k`; the local group on `m1_s0` is `$188`.
- Mission 1's player town is kind 11, not a capital, so `$5cde` refuses order `$0e` there. Land 60 cannot be won. Play Random Land leaves `$14e4e = 0`. A full `pm_export.py` rerun
  regresses `entities.json` and `sprite_triggers.json`. Do not reopen the SingleStepTests track or `$4342`'s 8 proven branches.
- Port traps (`port/stepper`): `--shot`/`--selfcheck` prove one instant, not a loop over time (use `--playtest`); Mibo's `GameTime` has no F#-callable constructor.

## Next session

Item 1: sweep the audit corrections through the docs (the line list is `scratchpad/pm134/audit/report.md`, regenerate from the agent's findings if the scratchpad is
lost: the claims are in this file and in strategy.md "Original names"), one live count per static claim, starting with byte 45 and `$3f86c` since they touch the most doc lines.
Then item 2 (the `.sym` renames). The `port/` and `tools/pm_fsm_ref.py` identifiers still say herd/shepherd; rename them only with a gate rerun.
