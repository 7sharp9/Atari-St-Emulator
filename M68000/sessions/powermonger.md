# PowerMonger: handoff

Updated 2026-10-01 by the 138th pass (the pigeon landing is not a manpower leak; the equipment exchange ported to F# with a credit-mode flag; no emulator change).

## Resume point

- Last commit of this workstream: the 138th pass's commit (`git log --oneline -3`).
- Working data: `M68000/scratchpad/` (gitignored; on the Mac copied from gpubox, CLAUDE.md "Shell pitfalls"), indexed in `scratchpad/ANCHORS.md`.
  `pm137/` holds this pass's evidence (`A_equip/`, `B_42be/`, `C_modes/` with their dumps and run scripts, `equip_gate/` the gate's corpus, `BRIEF.md`);
  the reusable scripts are in `reversing/powermonger/py/` (README table).
- Start from: `scratchpad/pm123/win/m1_ready.snap` (mission 1 conquered), `pm123/win/m1_s0.snap` (settled), `pm121/run/k5_s4.snap` (land 5, gatherers, merchants, farmers; the best
  snapshot for censuses; goods non-zero), `pm136/equip/e1_before.snap`/`e2_before.snap` (just before a natural equipment exchange).
- Uncommitted work left behind: none from this workstream. Not this workstream's: `M68000/sessions/README.md` (an Obsidian line-rewrap), `.obsidian/`, `Cadaver/`.

## Proven so far

Gates (differential tests vs the real 68000 through `callcap`): entity FSM `scratchpad/pm98/repro93..97.py` 675/1335/413/85/99; `pm98/diff_pm98.py` 71/71 (rerun this pass after `call_16892`
gained the `D2` parameter); `pm99/diff_pm99.py` 1847/1847; `pm115/diff_4bc8.py` 51/51 + `diff_4bc8_kind2.py` 20/20; `py/diff_1623c.py` 275/275; `py/diff_2776.py` 4119/4119;
`py/diff_5cde.py` 768/768 + 85/85; `py/diff_revolt.py` 1778/1778; `py/diff_4f68.py` 1804/1804; **new: `py/gate_equip.py` 385/385 bytes and D0.w/D1.w 201/201 over 201 states** (48 natural, 135 synthetic,
8 stubs, 10 `$16892`; every arm, lord < 8 and >= 8).

- **The equipment tail `$160f8` is in `tools/pm_fsm_ref.py` (`call_160f8`, `call_160e4`, `call_160f2`, `call_16892(m, A1, D2)`), stale-D0 bug included (137th).** The credit rule is exact only with D0 tracked: a returned weapon is
  misdirected for lord >= 8 (41 states); the farmer's item return reuses the left-over D0.w (correct after a take, misdirected with no take and no weapon return, correct for lords 8..15 after a weapon return without a take). 3 of 48 natural men
  carry a weapon and belong to a lord >= 8. Port decision, not made: keep the bug or flag it.
- **The equipment exchange is ported (138th): `port/godot/logic/Equipment.fs`, `CreditMode = Original | Corrected`** (Dave chose "faithfully, with the flag"). `Original` = the 68000 on 202 of 202 cases, 1451038 bytes and D0.w/D1.w (`py/equip_check.fsx`, corpus from `py/export_equip_corpus.py`; negative control with `Corrected` in the `Original` slot fails 64); `Corrected` has no oracle, only properties (equal to `Original` for lord < 8 in 89 of 89, only the own lord's goods change and goods plus held items are conserved in 192 of 192). The port has **no entity simulation** (the stepper replays one frame's draw order, PmLogic renders static records), so nothing calls it and `$3c08` is a parameter of `arriveGoods`.
- **The pigeon landing is not a manpower leak (138th, 5 of 5 landings, `py/pigeon_ledger.py` on `py/probe42be.py` captures of `k5_s4` and `m1_ready`):** every lord's `troops_field` equals the live-man rule count before and after the `$4244` arm, and only the home lord's `+1` changes, so the death had already taken the man off the count (the KILL tail `$567e`, `word[leader+8] -= 1` for a man in no group roster, proven by the 95th `$5590` gate; `economy.md` section 6's closed list had omitted it and now carries it). Not counted: a man who died inside a group roster (`$5658` -> `$1b8c`, out of the `$5590` gate's scope); the invariant held at all 5 hits whichever path the rider took.
- **`$42be` is the player's pigeon landing, a dead man revived (137th, counted 6 of 6 hits, `scratchpad/pm137/B_42be/probe42be.py`).** Sole caller of `$3e06` is `$13052`; only effect record `$4c112` takes the `$4244` arm; the record at
  `20(pigeon)` (a dead man whose `$1623c` countdown served the request) becomes a live man of its home settlement at the landing point, home lord `troops_field += 1`; live persons +1, one entity record changed at every hit.
  Not a kill credit and not a settlement birth; the "no birth term" statements carry this exception.
- **`troops_field` residual closed (137th, `py/troops_rule.py`):** a lord's leader-flag man (byte 7 bit 4) is counted iff `42(man) == 0`; with that rule 2280 of 2280 lord instances are exact over the game snapshots (instances, not independent lords; the
  242 misses are pre-game map snapshots with garbage tables); the 136th rule alone 2136, bit 6 alone 1406. Why the count follows the group link is inferred.
- **Mode `$34`:** the dwell is a byte (`subi.b #1,18(A1)`, `$57f0` seeds it with `$14`), 5 byte writes seen by `watch`, one per ~216k steps; shooters are byte 7 `$10`. **Mode `$36`** is set only by `$50da` (`38(A1) == 8`, the objective class of a category-8
  animal record via `$4dae`; code read, 0 men in 400 snapshots); poke-driven 3 of 3: the target is slaughtered through mode `$38` (`$1547e`: byte 7 `:= $10`, side negated, category `$1c`, `+$b4` food to the home lord or the group). **Mode `$8a`** is the captain at rest
  (byte 7 `$10` in 660 of 661, `py/census_8a.py`); `.sym` `h_mode8a_captain_rest`.
- **Audit rows closed:** "PATROL" is group state 6 = idle (`py/group_states.py`: the player's group in 6 of 6 snapshots); the prop sheet has four distinct pictures per family (12 of 12, `py/family_distinct.py`) while the terrain colour tables are the three distinct sets.
- Earlier, unchanged: `troops_field` the lord's men at home, merchants `$4e..$54` with the home lord as destination, `$90`/`$8e` the equipment exchange, `$1abaa` `_seasons`, `$57fce` the force ratio, the `$438ee` planes, modes `$12`/`$34`/`$36` censuses (136th);
  byte 45 health, `$3f86c` altitude, byte 33 carried item, `$35f4` camp, `$127e6` sound (135th); a man joins under order `$08`, `$4d252` trees (134th); every player order, revolt, starvation (125th/126th).

## Open, in priority order

1. **Give the port an entity simulation, or leave `Equipment.fs` uncalled:** the port renders captured records and has no tick; `tools/pm_fsm_ref.py` (about 3000 lines, gated) is the model to transcribe, and the equipment module is the first piece done. Dave decides whether the port should simulate at all. Also the `$54` merchant loop (`$15b0c`): a `callcap $159de` with a lord's `goods[]` poked would show whether a merchant ever carries anything.
2. **A natural `$36` contact:** which callers produce a category-8 (animal) engagement (the `$4cb8` class table has bare `rts` for classes 8, `$a`, `$c` as the alerted party; only as the interloper does it reach `38 := 8`); and who creates the byte6-8 animals (3 in `m1_s0`, 40 in `env5_12M`). Also what `$4c5f4` (`_birds`) shows on screen; the tree-record conversion at a season wrap (`byte7 == $d`) is dormant in the snapshots seen (inferred).
3. **The `$42be`/`$3e06` neighbours:** `$41dc` (the other effect records, ~2 hits per 150M steps in `k5_s4`) is a fall-through that never touches `troops_field` (code read); name what those records are.
4. **The orders not yet seen naturally**: `$04` transfer, `$0e` on a real capital, `$10`/`$06` on a food pile, the `$1a` supply line over several loops; `$1b2a`'s other-side rule.
5. Whether food or a captain's position changes the health cap (`$5ccc`): watch byte 45 over a march. `$1b8c` via `$5778`; `$4342`'s arrival/unlink branch; `$4f68` arms not covered; weather not in the Godot view; the crack's `$b842` patch; the link handshake only if Dave wants multiplayer.

## Known traps

- **A routine's tail that ends in the iterator's `bra $1622c` cannot be `callcap`ed in place** (it runs on into the mode handlers). `py/gate_equip.py` copies the man's 50-byte record onto slot 511 (`$57f34`, the last record) with `w` pokes and calls `callcap 160f8 A1=57f34`, so `$1622c` reaches its `rts`; valid only when the tail reads the record alone.
- **REPL `w` takes longwords at even addresses only**; poking the odd-addressed `-8257` plane means aligning down and rewriting the neighbours. A flag-plane poke overwrites the other flag bits.
- **`merge_sym.py --write` used to drop every comment** (fixed 136th). Edit a `.sym` with the Edit tool or check `grep -c '#'` before and after any tool rewrite.
- **A subagent's report is worth one spot check of its load-bearing claim against the listing** (this pass: `$5100` the only `move.b #$36,31(A1)`, `$4244`'s body, the rule check rerun, the gate rerun fresh against the merged model all held). The agents used 20-44 tool calls and kept "code read", "poke-driven" and "counted" apart; keep that labelling.
- **Subagent scripts must be re-rooted when promoted:** `parents[N]` depends on the directory depth (scratchpad `pm137/<agent>/` and `reversing/powermonger/py/` are both 3 below `M68000`, but `sys.path` and output dirs still need a read).
- **Byte 38 is overloaded** (mode `$0c` saves D7 into it): a `38 == 8` census is not evidence of mode `$36`.
- **The terrain redraw is gated**: `$f898` re-projects only when the camera cache `$f890/$f892`, `$ff9a` or `$fdec` changed; zero the cache (`w f890 00000000`) in both runs of an A/B (`py/alts_render_check.py`, `py/plane_ab.py`).
- **`callcap <addr> <steps> - A3=<hex>` calls a panel routine with a made-up frame**; the call restores the snapshot, so pokes between calls are cheap. Negative record indices in a `callcap` JSON `mem` list are the call's own stack bytes.
- **Entity records are only the first 512 at `$51b66` (stride 50)**: use side 1..127, category byte 6 = 0 (`py/job_census.py`). Group fields are at negative offsets from `$51538 + side*$13c + $4c + 2k` and sides above 5 are garbage (`py/group_states.py`).
- **A Bash command containing a stray `cat > file` waits on stdin until the tool timeout**; keep doc-edit Python in a script or a quoted heredoc with exact-match counts asserted.
- **`hits` after a `u` span starts counting at the end of that span.** **A refused click leaves `$57fd4` armed.** **Mission 1's own town has no inhabitants, lord 0's town does only after conquest.** **A `hits` run from `clicked.snap` shows `$15122` 0.**
- **One entity tick is about 200k steps, not a frame**; a `$1abaa` call is ~231k steps; a season is 512 calls.
- **A symbol's address space depends on its type.** Text: offset + `$10a6`; bss (type `$a100`): value + `$1c48e`. Labels are the authors' words, not proof: settle with a census against an independent record set.
- **An unreferenced file on the disk may be a program.** `$6a3a` dispatches through the word table at `$6a80`; read tables from RAM (`m 6a80 14`). The order table is `$6b5a + word[$6b5a + type]`.
- **A make and break `kbd` pair sent together can vanish**; **a raw `dotnet exec ... resume <snap> repl` needs `--disk-a <file.st>` and `ATARI_NOTRACE=1`**; macOS has no `timeout`; `sides.py`/`group.py`/`snap2ram.py` need a flat `.ram` image.
- `py/clicks.py`: the pointer moves 1:1 and clamps at 0. Mission 1's player town is kind 11, not a capital, so `$5cde` refuses order `$0e` there. Land 60 cannot be won. Play Random Land leaves `$14e4e = 0`. A full `pm_export.py` rerun
  regresses `entities.json` and `sprite_triggers.json`. Do not reopen the SingleStepTests track or `$4342`'s 8 proven branches.
- Port traps (`port/stepper`): `--shot`/`--selfcheck` prove one instant, not a loop over time (use `--playtest`); Mibo's `GameTime` has no F#-callable constructor.
  The `port/` and `tools/pm_fsm_ref.py` identifiers still say herd/shepherd, morale, survivability, type/height plane; rename them only with a gate rerun.

## Next session

Item 2 (a natural animal contact) needs a driven fight with a category-8 record; check first whether any snapshot has one near a party. Run subagent proofs under the same `scratchpad/pm137/BRIEF.md` shape (about 35 tool calls, own directory, no git or build).
