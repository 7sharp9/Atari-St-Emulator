# PowerMonger: handoff

Updated 2026-10-01 by the 135th pass (the audit sweep: byte 45 health, `$3f86c` altitude, byte 33 carried item, `$35f4` camp, `$127e6` sound).

## Resume point

- Last commit of this workstream: the 135th pass's handoff commit (`git log --oneline -4`); the work commit `a5f849c` is just before it.
- Working data: `M68000/scratchpad/` (gitignored; on the Mac copied from gpubox, CLAUDE.md "Shell pitfalls"), indexed in
  `scratchpad/ANCHORS.md`. `pm134/audit/report.md` (the audit agent's findings, the remaining doc corrections), `pm135/` (this pass's scratch:
  `m1_s0.snap`/`.ram`, `edit_*.py` doc-edit scripts, the `hp`/`alt_*` command files).
- Start from: `scratchpad/pm123/win/m1_ready.snap` (mission 1 conquered, base of the `$08` join), `pm123/win/m1_s0.snap` (settled, base of every order
  run), `pm123/win/m1_atk.snap` (mission-1 attack, a natural sound event at ~1.1M steps) or `pm121/run/k5_s4.snap` (land 5, gatherers running).
- Uncommitted work left behind: none from this workstream. Not this workstream's: `M68000/sessions/README.md` (an Obsidian line-rewrap),
  `.obsidian/`, `Cadaver/`.

## Proven so far

Gates (differential tests vs the real 68000 through `callcap`), unchanged and not re-run (no reference transcription or gate script
touched): entity FSM `scratchpad/pm98/repro93..97.py` 675/1335/413/85/99; `pm98/diff_pm98.py` 71/71; `pm99/diff_pm99.py` 1847/1847;
`pm115/diff_4bc8.py` 51/51 + `diff_4bc8_kind2.py` 20/20; `py/diff_1623c.py` 275/275; `py/diff_2776.py` 4119/4119; `py/diff_5cde.py`
768/768 + 85/85; `py/diff_revolt.py` 1778/1778; `py/diff_4f68.py` 1804/1804.

- **Byte 45 is health (135th).** `py/health_check.py`: 11 of 11 live `callcap $912a` calls with byte 45 poked to ten values (and byte 5 < 0) return
  `$a2dc + 9 + healthnames[(45 >> 4) & 7]` ("Very Sickly" ... "Very Strong", "Dead"); 203 of 225 live persons over `m1_s0`/`m1_ready`/`k5_s4` sit exactly
  on their `$5ccc` job cap (soldier 90, farmer 82, merchant 69, fisher 79, shepherd 72, leader 95). `$5c80` recovers health by one random bit per tick up to
  the cap, an age past `$3c` lowers the cap by 4 per unit and removes the man at 0. Melee drains it (`$1533c`). The docs' "morale/strength/food counter" is gone.
- **`$3f86c` is the altitude plane (135th).** `py/alts_render_check.py`: with the `$f890` camera cache zeroed to force one `$f898`/`$fec6` redraw, poking 39
  longwords of `$3c` under the camera raises a plateau, 10938 pixels differ against the same run without the poke (reproduced twice). `$ffa6` builds it
  (`$58148` random-walk steps adding `$5814b`, the low byte of the lord-count word `$5814a`, unless `$4592f` bit 1; clamp `>= 0`; `$10410` smoothing
  `$58150` times; static). Altitude 0 is sea: settlement placement refuses a cell whose four corner altitudes sum to 0 (`$2f72`, static); fishermen choose
  sprite `$70`/`$90` by the `+1`/`+64` neighbours (`$15bae`, static, 0 hits in `m1_s0`).
- **Byte 33 is the carried item code, `$35f4` makes the camp, `$127e6` is the sound dispatcher (135th).** Byte 33: 71/71 and 17/17 (134th). `$35f4` (group state 6,
  ring, camp marker; live state 3 → 6 in the `$08` run, 22 entries in 6M steps). `$127e6` picks the two best pending sounds from the `$3b`-entry table `$12952`
  and calls `$1ba3e`: 24 calls from `m1_atk` in 6M steps, one reaches `$128d2` and `$1ba3e`, 0 from `m1_ready`. strategy.md "`$127e6`", "Original names".
- **A man joins a group under order `$08` live (134th).** `py/join08_run.sh` from `m1_ready.snap` (`$1b2a` 2, `$1d70` 2, `$1501a` 5, group 26 → 28, `troops_field`
  5 → 3). Quota `46(lead) = troops_field >> (posture-2)`; later arrivals are refused and wait out `$2a`'s 50-tick dwell into `$3c08`.
- **`$4d252` is the tree array (134th)**: 203/203 and 154/154 on byte6-4 records, 0 on animals (`py/tree_census.py`); the gather chain felled 3 trees live.
  `$1d70` is `_rerank`, a rank former by weapon class. Farmer cycle `$18`→`$0c`→`$0e`→`$24`→`$16`: 275 of 281 `$0e` men farmers; `$68` is camp rest.
- Earlier: developer symbols from `DATA\SPRITE40.DAT`, order `$08` = get men, fishermen `$56..$62` (133rd); serial-link roles, ESC and chat (132nd); alliance
  effects (131st); no hidden keys (130th); a natural alliance (129th); every player order, revolt, starvation (125th/126th).

## Open, in priority order

1. **Finish the sweep of the audit's doc corrections** (the 135th did byte 45, `$3f86c`, byte 33, `$35f4`, `$127e6`, the farmer and `$178ae`/`$17878` labels; each
   remaining row needs one live count, the line numbers shift so grep the claim):
   - `$52`/`$54` are merchant modes: `$54` chooses the destination lord and sets off, `$52` waits 50 ticks after the `$50` deposit and heads home (ai.md ~702-703; census says 115 of 115 merchants, the mode roles are static).
   - `$16892` non-winter sends a man to his lord's cell (prev `$90`, mode `$90` equipment pickup); `$160f2` (`townee_g`) returns the old weapon and takes the best (bow > sword > pike); a farmer swaps in a Plough from `goods[3]` (static, 0 hits in 40M): ai.md ~341-344, 723, economy.md ~401-404.
   - economy.md ~78: `troops_field` is the lord's men at home (52 of 90 lords equal the live chain men with bit 6 clear, 85 within 1; the agent's count, re-run it), `$1b8c += 1` on leaving a group.
   - ai.md ~655, ~643: `$34` shooting cool-down after `$5150`, `$36` goto_ani chases `48(A1)`, `$12` is the moving leg between `$10` re-plans.
   - `$4bc8` is `_setup_fight` (sets men to `$2c` via `$4dae`); `$34f2` rallies the town's men of any job; `$311a` sets the hate byte (±100); `$57fce` win state (4 = victory); `$57fd0` season word 0 winter, 2 spring, 4 summer, 6 autumn; `$57fec` per-season tick counter.
   - `$1abaa` seasons/weather and the `$57ff6` season-dissolve LCG against the docs' "sound-only LCG" (README ~442, ~455, strategy.md ~923); strategy.md ~395 lists "strength" in the captain-info panel: check which panel string it is (probably the health word).
   - Remaining farmer/patrol wording: ai.md `$7c` rows ("settlement heartbeat" = per-man winter state), strategy.md ~943 ("standing patrol objective"), 1433-1437 pseudocode `PATROL`.
2. **Audit the rest of the 79 clashes in `powermonger.sym`** (`scratchpad/pm134/audit/clashes.txt`): rename the `.sym` entries marked D/R (`$002984`, `$014e70`,
   `$015042`, `$016048`, `$0161b2`, `$001d70`, `$001e9e`, `$3f86c`, `$00ffa6`, `$0127e6`, `$0178ae`, `$017878`, `$0157ba`, `$0157e6`; `pm_flag_health` for `$3e06` is
   already right), then `tools/merge_sym.py --write` to bring `powermonger_orig.sym` names in for unnamed addresses.
3. **Plane layout around `$438ee`**: graphics.md reads `-8257($438ee)` as the height byte and `$3f86c` as the projector's height source; `$3f86c` is `$438ee - 2*8257`, so
   there are planes at -16514 (altitude), -8257, 0 (type) and +8257 (flags, bit 1 claimed by settlements). Settle what `-8257` holds by a poke-and-render like `py/alts_render_check.py`.
4. **What `$4c5f4` (`_birds`) shows on screen**; who creates the byte6-8 animals (3 in `m1_s0`, 40 in `env5_12M`).
5. **The orders not yet seen naturally**: `$04` transfer, `$0e` on a real capital, `$10`/`$06` on a food pile, the `$1a` supply line over several loops; `$1b2a`'s other-side rule.
6. **What refills health** is answered (the cap table); what is open is whether food or a captain's position changes the cap: watch byte 45 over a march.
7. `$1b8c` via `$5778`; `$4342`'s arrival/unlink branch; `$4f68` arms not covered; weather not in the Godot view; the crack's `$b842` patch; the link handshake only if Dave wants multiplayer.

## Known traps

- **The terrain redraw is gated**: `$f898` re-projects (`$fec6`) only when the camera cache `$f890/$f892`, `$ff9a` or `$fdec` changed, so poking terrain data and running steps shows nothing.
  Zero the cache (`w f890 00000000`) in both runs of an A/B (`py/alts_render_check.py`). The mouse moves of an idle snapshot do not scroll it.
- **`callcap <addr> <steps> - A3=<hex>` calls a panel routine with a made-up frame**; poke `64(A3)` for the record offset and read the result from the `regdelta` line (`A5 ->`). The call restores the snapshot, so pokes between calls are cheap.
- **Entity records are only the first 512 at `$51b66` (stride 50)**: beyond that the bytes are other data and "live record" counts over the whole range are junk (2448 vs 21 live persons in `m1_s0`). Use side 1..127, category byte 6 = 0, as `py/job_census.py`.
- **A Bash command containing a stray `cat > file` waits on stdin until the tool timeout**; keep doc-edit Python in a script file (`scratchpad/pm135/edit_*.py` pattern: `edit(file, [(old, new)])` with exact-match counts asserted).
- **`hits` after a `u` span starts counting at the end of that span.** Put `hits` straight after `u 13b9a`.
- **A refused click leaves `$57fd4` armed**: "`$57fd4` still equals the icon id and the order's `$6bxx` executor has 0 hits" is the refusal signal.
- **Mission 1's own town has no inhabitants, lord 0's town does only after conquest** (`m1_ready.snap`): a get-men test needs a populated town of the commander's side.
- **A `hits` run started from `clicked.snap` shows `$15122` 0**: the lead had already arrived; the hit is in the stage that ran to the arrival.
- **One entity tick (a dwell step) is about 200k steps, not a frame**: a 50-tick wait is ten million steps.
- **Negative record indices in a `callcap` JSON `mem` list are the call's own stack bytes.**
- **A symbol's address space depends on its type.** Text: offset + `$10a6`; bss (type `$a100`): value + `$1c48e`. Labels are the authors' words, not proof: the tree array
  shows a doc name and an original label can both be half right; settle with a census against an independent record set.
- **An unreferenced file on the disk may be a program.** A routine that runs once at startup cannot be tested by patching its input in a snapshot.
- **`$6a3a` dispatches slot state through the word table at `$6a80`, and the static listing around it is out of phase**; read tables from RAM (`m 6a80 14`). The order table is `$6b5a + word[$6b5a + type]`.
- **A make and break `kbd` pair sent together can vanish**: send the make, run to the checkpoint, then the break.
- **A raw `dotnet exec ... resume <snap> repl` needs `--disk-a <file.st>`, not `-DiskA`**; and `ATARI_NOTRACE=1`. macOS has no `timeout`.
- **`sides.py`/`group.py`/`snap2ram.py` need a flat `.ram` image**; `py/snap2ram.py <snap>` converts.
- **Census the target's neighbourhood before choosing a route** (`census_lords.py`), and check a march's food-to-men ratio with a short probe first.
- **A subagent's "static" claim is a hypothesis**: the audit's claims held on every spot check so far (health, altitude, camp, sound), but its report is not a proof; re-count the one number each doc line rests on.
- `py/clicks.py`: the pointer moves 1:1 and clamps at 0; an order posted by a click runs during the click's settle steps. Group offsets: `side*$13c + $4c + 2k`; the local group on `m1_s0` is `$188`.
- Mission 1's player town is kind 11, not a capital, so `$5cde` refuses order `$0e` there. Land 60 cannot be won. Play Random Land leaves `$14e4e = 0`. A full `pm_export.py` rerun
  regresses `entities.json` and `sprite_triggers.json`. Do not reopen the SingleStepTests track or `$4342`'s 8 proven branches.
- Port traps (`port/stepper`): `--shot`/`--selfcheck` prove one instant, not a loop over time (use `--playtest`); Mibo's `GameTime` has no F#-callable constructor.
  The `port/` and `tools/pm_fsm_ref.py` identifiers still say herd/shepherd, morale and survivability; rename them only with a gate rerun.

## Next session

Item 1: continue the audit sweep with the rows listed above, one live count per static claim (start with `troops_field`, the `$52`/`$54` merchant modes and the `$57fd0`
season word, they touch the most doc lines). Then item 2 (the `.sym` renames and `merge_sym.py --write`), then item 3 (the `-8257` plane, a poke-and-render check).
