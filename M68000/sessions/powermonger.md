# PowerMonger: handoff

Updated 2026-10-01 by the 136th pass (four parallel proofs of the audit rows: ledger/merchants, seasons/win state, equipment, terrain planes; `.sym` renames).

## Resume point

- Last commit of this workstream: the 136th pass's handoff commit (`git log --oneline -4`); the work commit `d958eac` is just before it.
- Working data: `M68000/scratchpad/` (gitignored; on the Mac copied from gpubox, CLAUDE.md "Shell pitfalls"), indexed in
  `scratchpad/ANCHORS.md`. `pm136/` holds this pass's evidence (`equip/`, `ledger/`, `season/`, `planes/` with their snapshots and run outputs,
  `BRIEF.md`, the `edit_*.py` doc-edit scripts); the reusable scripts are in `reversing/powermonger/py/` (README table).
- Start from: `scratchpad/pm123/win/m1_ready.snap` (mission 1 conquered, base of the `$08` join), `pm123/win/m1_s0.snap` (settled, base of every order
  run), `pm123/win/m1_atk.snap` or `pm121/run/k5_s4.snap` (land 5, gatherers, merchants and farmers running; the best snapshot for economy censuses).
- Uncommitted work left behind: none from this workstream. Not this workstream's: `M68000/sessions/README.md` (an Obsidian line-rewrap), `.obsidian/`, `Cadaver/`.

## Proven so far

Gates (differential tests vs the real 68000 through `callcap`), unchanged and not re-run (no reference transcription or gate script touched; only comments in
`tools/pm_render_ref.py`, `pm_fsm_ref.py`, `pm_export.py` changed): entity FSM `scratchpad/pm98/repro93..97.py` 675/1335/413/85/99; `pm98/diff_pm98.py` 71/71;
`pm99/diff_pm99.py` 1847/1847; `pm115/diff_4bc8.py` 51/51 + `diff_4bc8_kind2.py` 20/20; `py/diff_1623c.py` 275/275; `py/diff_2776.py` 4119/4119;
`py/diff_5cde.py` 768/768 + 85/85; `py/diff_revolt.py` 1778/1778; `py/diff_4f68.py` 1804/1804. `py/dither_atlas.py` rerun: 0 pixels differ against the reference renderer.

- **`troops_field` is the lord's men at home (136th).** `py/troops_audit.py`: 416 lord instances over 33 snapshots, 378 equal the live men of the lord (home settlement
  `34(man) -> $4f916+14`) with byte-7 bit 6 clear, leader-flag entities excluded, 416 within 1; `watch` 150M steps: `$152d4` (a man joins an army) `-1`, 19 events, the invariant
  tracks (k5_s4 16/16). Unsettled: why the lord's own bit-4 entity is counted for some lords (k25_s4 lords 1, 4, 10) and not others (13); what `$42be` really credits.
- **Merchants cycle `$4e -> $54 -> $10 -> $50 -> $52 -> $10 -> $4e`, destination always the home lord (136th).** `py/merch_census.py`: 1156 men in `$4e..$54`, all job 2,
  `$54/$4e` 639, `$52/$50` 404 with `46(man) ==` home lord 404/404; one merchant followed live through four identical 16M-step cycles. `$54`'s lord loop as encoded never leaves the home
  lord (`lea 32(A3),A0`, inferred); 0 of 136 merchants in transit carry anything, so the "goods circulation between lords" has no live observation.
- **Modes `$90` (`townee_g`) and `$8e` (`fight_ge`) are the equipment exchange (136th).** Natural capture `scratchpad/pm136/equip/e1_*`/`e2_*`: a farmer took a Plough from lord 8's `goods[3]` (4 -> 3);
  tail `$160f8` returns the old item, takes the best of bow/sword/pike, a farmer takes a Plough. `$16892` is the gate with the caller's `D2` (`$157d2` `$90`, `$4f82` `$8e`). A stale-D0 bug credits the
  returned item `128*(lord>>3)` bytes further on for lord index >= 8 (lord 8's Plough landed in lord 12's slot, live twice). Plough doubles farm food at `$1508a`: 2 of 73 returns in 40M steps.
- **`$1abaa` is `_seasons`, `$57ff6` the pixel-order LCG of the season tileset dissolve (136th).** `watch 57fd0` over 330M steps: three writes, period 118.44M steps = 512 calls x ~231k; `$57fec` counts the calls
  since the last change; `py/season_tilediff.py`: half summer/half autumn art at count 255, 79 pixels from the new art at 496; spring and autumn share one tileset (3 distinct, not 4).
- **`$57fce` is the 0..4 force ratio, tested `== 4` by the end-of-land verdict `$d2c8` (136th)**: m1_s0 2, m1_ready 4; not "UI only". Panel 2's "Strength:" row prints the health word (`$912a`).
- **The `$438ee` planes (136th, `py/plane_ab.py`, `py/flag_census.py`):** altitude `-16514` (`$3f86c`, plateau 10938 px), colour B `-8257` and colour A `0` (slope-shade bytes built from the altitude by `$10058`, 0 = sea; poking either retones one triangle,
  2236/2124 px, geometry unchanged), flags `+8257` (bit 7 diagonal; bit 1 pins the altitude against the `$10410` smoothing, 232 of 506 bit-1 cells in k5_s4 are outside settlements). The doc and tool labels "type plane"/"height plane" are corrected; identifiers `typ`/`hgt`/`HeightPlane` in the port are not renamed.
- **Modes `$12`, `$34`, `$36` (136th, `py/mode_census.py`):** `$12` is the moving leg between `$10` re-plans (33 of 33 men in k5_s4 have prev `$42`/`$44`); `$34` is the shot cool-down (seen in 274 snapshots); `$36` chases entity `48(A1)` and overwrites the target's byte 7 (code read only, 0 men in any snapshot).
- **`.sym`:** 13 renames from the audit (the `h_mode0e_in_flight`, `pm_rerank`, `g_alts`, `pm_fill_alts`, `pm_do_sound`, `pm_do_bars` family) with corrected comment heads, 940 original developer names appended (`merge_sym` reports 0 new names).
- Earlier: byte 45 health, `$3f86c` altitude, byte 33 carried item, `$35f4` camp, `$127e6` sound (135th); a man joins under order `$08`, `$4d252` trees (134th); developer symbols, order `$08` = get men (133rd); every player order, revolt, starvation (125th/126th).

## Open, in priority order

1. **Finish the audit sweep's last rows** (each needs one live count, line numbers shift so grep the claim): ai.md `$7c` wording and strategy.md ~943 ("standing patrol objective"), ~1433-1437 pseudocode `PATROL`; economy.md ~547/~576 and `pm114_tileset_families.png` say "four" tileset families while only three distinct tilesets exist (check against the family table); `$0161b2` (`h_mode8a_garrison` vs `captain_`) is the one audit clash left unrenamed; the `$4bc8` label `_setup_fight` is consistent with `$4dae` setting men to `$2c` (settled by the 115th/116th proofs, no live count needed); `$34f2`/`$311a` were already documented.
2. **`pm_fsm_ref.py` against the new facts:** `call_16892` takes one `D2`; `$4f82`'s `D2 = $8e` caller and the `$160f8` tail (with the stale-D0 bug) are not in the reference model. If the port wants men to equip, transcribe `$160f8` and gate it with `callcap` on `e2_before.snap`. Also `$54`'s non-advancing loop (`$15b0c`): a `callcap $159de` with a lord's `goods[]` poked would show whether a merchant ever carries anything.
3. **`$42be` (`troops_field += 1` for the object's own settlement's lord):** trace its caller (`$3e06` tail); decide man-created versus kill-credit. Also the leader-flag discriminator for the `troops_field` residual.
4. **The `$36` goto_ani chase** observed live (a driven fight through order `$0a`/`$08` and `$4f68` mode `$08`); and whether `$34` decrements its dwell byte or word (`$57f0`).
5. **What `$4c5f4` (`_birds`) shows on screen**; who creates the byte6-8 animals (3 in `m1_s0`, 40 in `env5_12M`); the tree-record conversion at a season wrap (`byte7 == $d`) is dormant in the snapshots seen (inferred).
6. **The orders not yet seen naturally**: `$04` transfer, `$0e` on a real capital, `$10`/`$06` on a food pile, the `$1a` supply line over several loops; `$1b2a`'s other-side rule.
7. Whether food or a captain's position changes the health cap (`$5ccc`): watch byte 45 over a march. `$1b8c` via `$5778`; `$4342`'s arrival/unlink branch; `$4f68` arms not covered; weather not in the Godot view; the crack's `$b842` patch; the link handshake only if Dave wants multiplayer.

## Known traps

- **REPL `w` takes longwords at even addresses only**; poking the odd-addressed `-8257` plane means aligning down and rewriting the neighbours. A flag-plane poke overwrites the other flag bits (the 136th's `+8257` pokes were not clean tests).
- **`merge_sym.py --write` used to drop every comment**; fixed in the 136th (it now keeps existing lines and appends). Check `grep -c '#'` on a `.sym` before and after any tool rewrite.
- **A subagent's report is worth one spot check of its load-bearing claim against the listing** (the stale-D0 bug and the `-8257` painter read both held when re-read in `all.asm`); the agents hit their timebox at 30-40 tool calls and each separated "code read" from "counted", which is the label to keep.
- **The terrain redraw is gated**: `$f898` re-projects (`$fec6`) only when the camera cache `$f890/$f892`, `$ff9a` or `$fdec` changed, so poking terrain data and running steps shows nothing.
  Zero the cache (`w f890 00000000`) in both runs of an A/B (`py/alts_render_check.py`, `py/plane_ab.py`). The mouse moves of an idle snapshot do not scroll it.
- **`callcap <addr> <steps> - A3=<hex>` calls a panel routine with a made-up frame**; poke `64(A3)` for the record offset and read the result from the `regdelta` line (`A5 ->`). The call restores the snapshot, so pokes between calls are cheap.
- **Entity records are only the first 512 at `$51b66` (stride 50)**: beyond that the bytes are other data and "live record" counts over the whole range are junk. Use side 1..127, category byte 6 = 0, as `py/job_census.py`.
- **A Bash command containing a stray `cat > file` waits on stdin until the tool timeout**; keep doc-edit Python in a script file (`scratchpad/pm136/edit_*.py` pattern: `edit(file, [(old, new)])` with exact-match counts asserted; a failed run leaves earlier files edited, so split the script per file before rerunning).
- **`hits` after a `u` span starts counting at the end of that span.** Put `hits` straight after `u 13b9a`.
- **A refused click leaves `$57fd4` armed**: "`$57fd4` still equals the icon id and the order's `$6bxx` executor has 0 hits" is the refusal signal.
- **Mission 1's own town has no inhabitants, lord 0's town does only after conquest** (`m1_ready.snap`): a get-men test needs a populated town of the commander's side.
- **A `hits` run started from `clicked.snap` shows `$15122` 0**: the lead had already arrived; the hit is in the stage that ran to the arrival.
- **One entity tick (a dwell step) is about 200k steps, not a frame**: a 50-tick wait is ten million steps. A `$1abaa` call is ~231k steps; a season is 512 calls.
- **Negative record indices in a `callcap` JSON `mem` list are the call's own stack bytes.**
- **A symbol's address space depends on its type.** Text: offset + `$10a6`; bss (type `$a100`): value + `$1c48e`. Labels are the authors' words, not proof: the tree array
  shows a doc name and an original label can both be half right; settle with a census against an independent record set.
- **An unreferenced file on the disk may be a program.** A routine that runs once at startup cannot be tested by patching its input in a snapshot.
- **`$6a3a` dispatches slot state through the word table at `$6a80`, and the static listing around it is out of phase**; read tables from RAM (`m 6a80 14`). The order table is `$6b5a + word[$6b5a + type]`.
- **A make and break `kbd` pair sent together can vanish**: send the make, run to the checkpoint, then the break.
- **A raw `dotnet exec ... resume <snap> repl` needs `--disk-a <file.st>`, not `-DiskA`**; and `ATARI_NOTRACE=1`. macOS has no `timeout`.
- **`sides.py`/`group.py`/`snap2ram.py` need a flat `.ram` image**; `py/snap2ram.py <snap>` converts.
- **Census the target's neighbourhood before choosing a route** (`census_lords.py`), and check a march's food-to-men ratio with a short probe first.
- `py/clicks.py`: the pointer moves 1:1 and clamps at 0; an order posted by a click runs during the click's settle steps. Group offsets: `side*$13c + $4c + 2k`; the local group on `m1_s0` is `$188`.
- Mission 1's player town is kind 11, not a capital, so `$5cde` refuses order `$0e` there. Land 60 cannot be won. Play Random Land leaves `$14e4e = 0`. A full `pm_export.py` rerun
  regresses `entities.json` and `sprite_triggers.json`. Do not reopen the SingleStepTests track or `$4342`'s 8 proven branches.
- Port traps (`port/stepper`): `--shot`/`--selfcheck` prove one instant, not a loop over time (use `--playtest`); Mibo's `GameTime` has no F#-callable constructor.
  The `port/` and `tools/pm_fsm_ref.py` identifiers still say herd/shepherd, morale, survivability, type/height plane; rename them only with a gate rerun.

## Next session

Item 1 (the remaining audit rows, a short pass), then item 2: transcribe the `$160f8` equipment tail into `tools/pm_fsm_ref.py` and gate it against `callcap` on `scratchpad/pm136/equip/e2_before.snap`
and the `$4f82` caller, since it is the one behaviour this pass found that a port would currently get wrong (the stale-D0 credit for lord index >= 8 is the original's bug and should be kept or flagged). Then item 3 (`$42be`).
Run subagent proofs under the same timebox and `scratchpad/pm136/BRIEF.md` shape; every agent kept to 30-40 tool calls and reported "code read" separately from "counted".
