# PowerMonger: handoff

Updated 2026-10-01 by the 133rd pass (the developer symbol table found in `DATA\SPRITE40.DAT`). The names are
in hand and have corrected the docs in three places; checking the old `.sym` names and the docs' roles against
them is item 1.

## Resume point

- Last commit of this workstream: the 133rd pass's handoff commit (`git log --oneline -4`); the work is
  `ba6beb9` (symbols, order `$08`) and `4cd7081` (fishermen), the skill lesson `384f0c2`; before them the 132nd
  (`38ce8e2`, `1efce1c`).
- Working data: `M68000/scratchpad/` (gitignored; on the Mac copied from gpubox, CLAUDE.md "Shell pitfalls"),
  indexed in `scratchpad/ANCHORS.md`. `pm133/` holds the unpacked `sprite40_inner.prg`, the `hits`/`callcap`
  runs of this pass and `o08*` (order `$08`). `pm129/env5_12M.snap` is the post-alliance state.
- Start from: `scratchpad/pm123/win/m1_s0.snap` (mission 1 settled; the base of every order run) or
  `scratchpad/pm129/env5_12M.snap` (alliance effects).
- Uncommitted work left behind: none from this workstream. Not this workstream's: `M68000/sessions/README.md`
  (an Obsidian line-rewrap), `.obsidian/`, `Cadaver/`.

## Proven so far

Gates (differential tests vs the real 68000 through `callcap`), unchanged and not re-run (no reference
transcription or gate script touched): entity FSM `scratchpad/pm98/repro93..97.py` 675/1335/413/85/99;
`pm98/diff_pm98.py` 71/71; `pm99/diff_pm99.py` 1847/1847; `pm115/diff_4bc8.py` 51/51 + `diff_4bc8_kind2.py` 20/20;
`py/diff_1623c.py` 275/275; `py/diff_2776.py` 4119/4119; `py/diff_5cde.py` 768/768 + 85/85;
`py/diff_revolt.py` 1778/1778; `py/diff_4f68.py` 1804/1804.

- **`DATA\SPRITE40.DAT` is the game build with its linker symbols (133rd).** A self-extracting GEMDOS program,
  137,652 bytes unpacked; 28,936 of 28,942 unique 16-byte text windows sit in RAM at offset `$10a6`, 2,855 absolute
  operands differ by exactly `$10a6`. 1,639 symbols (1,196 unique, 978 routine starts), names cut to 8 characters; bss
  symbols are bss-relative (address = value + `$1c48e`). `py/s40_symbols.py` regenerates `powermonger_orig.sym`.
  Every known variable lands exactly on a symbol start (`$51b66 _sprites`, `$4e514 _towns`, `$51538 _kings`, `$58016 _packets`,
  `$2de6c _key_on`, `$57fd0 _season` ...). strategy.md "Original names".
- **Order `$08` is get men, not besiege (133rd).** `$3154` and `$3248` accept only the commander's own side;
  live, the armed icon clicked on enemy lord 0's town posted nothing (`$57fd4` stayed 8, 0 `$6bea`, 0 `$3154` in 60M
  steps); on the own town it ran `$15122` and left the lead in mode `$28`. `callcap $34f2` on lord 0's town sends 4 men
  (records 2, 3, 5, 7: `31 := $10`, `30 := $14`). `$69b4(D1)` picks the best **own** lord (`D1` 6 food, 8 men):
  `callcap` 3/3. Not observed: a man actually joining (`$15282`, `$1b2a` 0 hits; mission 1's own town has no
  inhabitants). strategy.md "What each order does", ai.md modes `$1c`/`$28`/`$2a`.
- **Modes `$56..$62` are the fishermen, `$60`'s food += 4 is the catch (133rd).** `py/job_census.py` over seven
  snapshots: 93 of 93 men in those modes are job 4 (fisher); `$4e..$54` 115 of 115 merchants; `$80..$88` shepherds;
  `$0e` 202 of 208 farmers. ai.md, economy.md "The flows".
- **Data loads and dead code are closed (133rd).** `$df52` has 16 resource indices and 17 literal call sites; a land
  build loads only indices 1 and 8 from the cache (`hits`, 2 hits); `CAP_SPR` (6) has no caller, `BITMAP` (7) only the
  never-taken fixed-map branch; `MAP0000.DAT`, `B_FLOOD.ECH` have no reference of any kind. Of 978 routine starts,
  97 lack a direct reference, 14 survive the table scan, 13 of those explained; `_how_far` (`$10cae`, 0 hits in 120M
  steps) is the one probable dead routine (`py/s40_orphans.py`). strategy.md "Hidden features audit".
- Earlier: serial-link roles, ESC abort and chat (132nd); the alliance's effects hold from the natural state (131st);
  no hidden keys or debug commands (130th; the debug monitor was stripped to four `rts` stubs, `$1ba62..$1ba70`);
  terrain fill fully characterised (130th, `py/dither_atlas.py`); a natural alliance completes end to end (129th); every
  player order, group-record fields, conquest, the revolt mechanism, starvation desertion (125th/126th).

## Open, in priority order

1. **Audit the old names and roles against the original ones.** 153 of the 232 names in `powermonger.sym` land exactly
   on an original symbol; the other 79 are mid-routine or differ. Run `tools/merge_sym.py powermonger.sym
   powermonger_orig.sym` (reports clashes), settle each in the code, and read the docs' mode and routine roles that
   disagree with the labels (the 133rd found three: `$08`, `$56..$60`, `$14e4e`). Candidates: `$0e` (the docs say
   "patrol / neutral garrison", the census says farmers), `$0c`/`$18`, `$7c`/`$7e` (`in_winte`, `stay_at_`), `$2c` `set_figh`,
   `$3e..$44` shepherds, `$1d70` (`_rerank`) vs the documented route expander, `$34f2` (`_come_ho`).
2. **See a man join under order `$08`.** Needs a side with a town that has inhabitants and a group of the same side
   (the player's town in a later land, or an AI group). Run `hits` on `$1501a`, `$15282`, `$1b2a`, `$1d70` and read the
   group's men count before and after; that also settles the quota rule (`46(lead)`, posture shift).
3. **The orders not yet seen naturally**: `$04` transfer (two captains, a later land), `$0e` on a real capital, `$10`/`$06`
   on a food pile, the `$1a` supply line over several loops.
4. **What refills strength** (man byte 45, drained by `$5c80`): watch it over a march with and without food.
5. `$1b8c` via `$5778`; `$4342`'s arrival/unlink branch (`scratchpad/pm113/diff_4342.py`); `$4f68` arms not covered.
6. Smaller: weather is not in the Godot view; where the crack writes its `$b842` patch; the crack's own title stage and
   `MREP`; the one byte at `$27028` that changes with left shift; the fixed-map branch `$df52(7)`. The link handshake
   (`$6eb6`, `_connect`, `_do_seri`) only if Dave wants multiplayer.
7. **A deeper game summary**, if Dave wants populous's depth: the README digest is current; an explicit architecture
   thread is the next step.

## Known traps

- **`hits` after a `u` span starts counting at the end of that span.** The first land-build run counted 0 at `$13c0e`
  because `u 13ce6` had already run through it; put the `hits` straight after `u 13b9a`.
- **A refused click leaves `$57fd4` armed.** For a targeted order, "`$57fd4` still equals the icon id and the order's
  `$6bxx` executor has 0 hits" is the refusal signal (pointer-test filter), not a missed click.
- **Negative record indices in a `callcap` JSON `mem` list are the call's own stack bytes**, not object records
  (`(addr - $51b66) // 50` goes negative below the table).
- **A symbol's address space depends on its type.** Text: offset + `$10a6`; bss (type `$a100`): value + `$1c48e`. Names are
  8-character truncations and two routines can share one. A label is the authors' word, not proof of behaviour; the
  behaviour proofs in the docs win, and a clash gets one live check.
- **An unreferenced file on the disk may be a program** (see the skill): read its first bytes before calling it data.
- **A routine that runs once at startup cannot be tested by patching its input in a snapshot**; call it with
  `callcap <addr> <steps> - A0=<scratch>` and read the delta.
- **`$6a3a` dispatches slot state through the word table at `$6a80`, and the static listing around it is out of phase**;
  read tables from RAM (`m 6a80 14`). The order table is `$6b5a + word[$6b5a + type]` (the old `$6b5c` base was 2 off).
- **A make and break `kbd` pair sent together can vanish**: send the make, run to the checkpoint, then the break.
- **A raw `dotnet exec ... resume <snap> repl` needs `--disk-a <file.st>`, not `-DiskA`**; the wrong flag prints all-zero
  memory instead of failing.
- **`sides.py`/`group.py`/`snap2ram.py` need a flat `.ram` image**; `py/snap2ram.py <snap>` converts.
- **Census the target's neighbourhood before choosing a route** (`census_lords.py`), and check a march's food-to-men ratio
  with a short probe first.
- `py/clicks.py`: the pointer moves 1:1 and clamps at 0; an order posted by a click runs during the click's settle steps,
  so `hits` started after the click misses the posting (it still sees the arrival). A raw REPL token passes through with `:`
  for spaces; only one `watch` range is live. Group offsets: `side*$13c + $4c + 2k`; the local group on `m1_s0` is `$188`.
- Mission 1's player town is kind 11, not a capital, so `$5cde` refuses order `$0e` there. Land 60 cannot be won. Play Random
  Land leaves `$14e4e = 0` (protection unanswered: no AI). A full `pm_export.py` rerun regresses `entities.json` and
  `sprite_triggers.json`. Do not reopen the SingleStepTests track or `$4342`'s 8 proven branches.
- Port traps (`port/stepper`): `--shot`/`--selfcheck` prove one instant, not a loop over time (use `--playtest`); Mibo's
  `GameTime` has no F#-callable constructor (use `HeadlessProgram.mkHeadless` + `HeadlessRunner`).

## Next session

Item 1: merge `powermonger_orig.sym` into the working picture (`tools/merge_sym.py`), settle the 79 clashes and the
docs' roles that disagree with the labels, one live check each. Item 2 (a live join under `$08`) is the cheapest
mechanics proof and closes the one unverified half of the order `$08` correction. Item 3 is the mechanics
alternative.
