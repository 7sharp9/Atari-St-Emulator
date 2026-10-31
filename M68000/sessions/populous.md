# Populous: handoff

Updated 2026-10-31 by the session that ended at commit `30cb24f` (hidden hooks run live).

## Resume point

- Last commits of this workstream: `30cb24f` (hidden hooks live, `py/hooks/`), `e77989a` (fight start / join live, knight cast from `fight1`),
  `564f233`..`c0b9ad7` (the swamp-monster edge measured on real Hatari), `a74f2ae` (docs audit).
- `bin/` is built from HEAD (`249562d`, 2026-10-25). The emulator changed a lot since `a74f2ae` (MFP
  vector base and pending-clear, bus errors above `$400000`, `hits`/`bpc` count instruction starts,
  stserver). Re-checked on it this session: `postdecide_diff.py 400 8080` 800/800, `fight1`/`gather1`
  and the `knight_fight.py` cast all run; other counts were taken on the older emulator and not re-run.
- Working data: `$POP_WORK` = `M68000/scratchpad/pop/`, rebuilt on this Mac. Source files:
  `~/Library/CloudStorage/Dropbox/Daves/ST games/` (the Populous zip, hash in the README;
  `hatari-v2.6.1-480/tos100uk.img` copied to `M68000/TOS100UK.IMG`). Present: `files/`,
  `pop_ad58.img`, `pop_ad58.asm` (now the whole text segment $ad58..$21464, regenerated with
  `disassemble.py --rom pop_ad58.img --base ad58 --all ad58 21464`; the old file stopped at $1d462 and
  `py/fieldxref.py` and `py/ai/asm.py` read it), `pop_ad58.c` (Ghidra 12.1.4, in `ghidra121/`), `pop_auto.st`, `repro`/`game_start`/`g90`/
  `late1..4.snap`, `walker/snaps/near`, `front`, `gather1`, `fight1`, `hooks/paint1.snap` (paint-map
  mode in a custom game, built by `py/hooks/paint_mana.py`; not yet in `ANCHORS.md`, which holds another
  session's uncommitted edit). Everything else in
  `ANCHORS.md` (drive/A, ai/cg1, cg2, M1, g40, powers/snaps, systems/spawn, swamp208, endgame) is
  **not** rebuilt here yet; `ai_diff.py` lists `g40.snap` and `agents/` captures that are absent.
- Start from: `walker/snaps/fight1.snap` (frame 2665) for combat and take-overs;
  `powers/snaps/knight_s3000_after.snap` (`knight_fight.py 3000`) for a long-lived knight.
- Uncommitted work left behind: none from this workstream (`Cadaver/` belongs to another session).

## Proven so far

Five topic docs, each count in the table at the top of `reversing/populous/README.md`; the README's
**Design digest** restates the rules (unchanged this session).

- Graphics: frame rebuilt from RAM 64000/64000 on 12 frames; trail sprites 32/32; mouse UI 17/17.
- Terrain: generator byte-identical for 3 worlds; six powers + `$fe00`/`$feca`/`$108b8` under
  callcap **2670/2670** (`py/powers/pw_diff.py 40 2026` + `40 77`).
- Mechanics: settlements, mana, spawns; walker direction 2400/2400 + 8000/8000 live; knight
  154/154 live; combat `$1063a` rounds 97/97, resolutions 19/19; town take-over live 7/7, callcap
  240/240; **`$ef4c`'s post-decision writes (settle, merge, fight start `$10e7e`, join `$11006`,
  occupancy) callcap 1600/1600** over two seeds (`py/walker/postdecide_diff.py`, model in
  `walker_ref.apply_decision`), nothing excluded now that `fight_start` runs `powers_ref.anim_advance`
  for its two `$101a0` calls (dropping one fails 55/400). Live (`py/powers/live.py <snap> <frames>
  fightstart join`): fight start **117/117**, join **3/3**; a UI-cast knight (`py/powers/knight_fight.py
  3000`, 2000 frames) **41/41** fight starts, wins and razes, plus the first both-die round 1/1
  (`mechanics.md` 3.3, 3.5). Armageddon brawl 441/441; score.
- AI: 4800/4800 decision routines; natural runs 1854/1854, 2766/2766; flood/armageddon casts.
- Swamp-monster entry edge: south on 75.9% of frames over ten Hatari cold boots against 69-70% here;
  the gap is interrupt timing (`systems.md` 1.3, `py/systems/hatari_edges.py`).
- Systems: trails 400/400 + 400/400 callcaps, 394/394 live; the pop-208 swamp spawn 400/400 and
  237/238 frames (`systems.md` 1.3).
- Hidden hooks (`mechanics.md` 7, `graphics.md` Scrolling), run live with controls: F6/F7 in paint-map
  mode post `cmd_misc` subs 9/10, **52/52** calls match the mana model (`py/hooks/paint_mana.py 1200000`);
  sub 15 from a poked record sets `$3c4e4` = arg+1, CHEAT once, capacity-50 line 3/4 hits, control 0
  (`py/hooks/sub15_poke.py`); the keypad-`*` branch passes its guard 4/4 with the pointer at (316,15),
  0/4 at (200,100), never reaches `cmd_misc` (`py/hooks/star_key.py`). No code on one machine posts sub
  15 (byte-store census, `mechanics.md` 7); only the serial unpack `$183b4` could carry it.
- Docs audit: the three audits' "checked and sound" lists are the evidence for everything not
  corrected; `postdecide_diff.py 400 <seed>` reproduced on this Mac, 800/800 for each of seeds 8080 and
  77 (1600/1600). `landscape_infographic.py --check` gives 375/375 here.
- Landscape infographic `reversing/populous/landscape_infographic.html` (this session): JS port of
  the terrain code, **375/375** random cases against `popgen`, `powers_ref`, `pop_render`,
  `popdrive` (`uv run python reversing/populous/py/landscape_infographic.py --check`, from
  `M68000/`; needs node). A raise at (11,16) on a generated GENESIS changes 134 corners, the
  emulator's count. The check was mutation-tested (7 of 8 deliberate bugs caught).
- The emulator is deterministic across Windows and macOS on the recipe path: `repro` frame 285 and
  late1..4 frames 835/1328/1763/2161, evil mana 7485.

## Running

Nothing running.

## Open, in priority order

1. **The swamp208 237/238 frame**: `trail_ref.py` skips a settlement on a marked cell because
   `$10366` was not modelled; `powers_ref.claim_land` now is. Wire it in and re-run
   `py/systems/trailrun.py` from `swamp208/p_spawn.snap` (needs `swamp208.py poke` on this Mac
   first) for 238/238; same for the `$12f84` corpus exclusion (`systems.md` 1.4).
2. **Staged scenes for the callcap-only branches** (`mechanics.md` 10): a knight merging into a
   friendly walker, a take-over whose winner stays a walker, a castle claimed after a take-over,
   `$10068` killing a settlement outside a fight. Natural play did not reach them (0 of 391 merges
   with a knight mover, 0 of 25 take-overs). Stage with labelled pokes: a friendly walker placed on
   the `knight_s3000` knight's next cell; a building overlay next to a take-over winner. Low value:
   `pw_diff.py` already covers them on the full state.
3. Smaller loose ends: sounds 5/6 and the `$37e78` bits (`systems.md` 6); `$135fc`'s second call
   site `$e580` live; the `$f6b2` swamp raise live; a full SAVE/LOAD round trip on a disk with
   space; the paint-map edits (F1..F5, F8, Delete, from `hooks/paint1.snap`), RESTART/NEXT MAP; SPR_320 frames 9 and 11 live; a pop-208 spawn on edge 1 or a
   stale cell (poke `$3f418`). Infographic: the minimap colour of shapes above `$2e` (rocks,
   swamp, ruins) has no traced table entry, so the page draws them as plain land.
4. Lowest: the serial link (`$19652`, needs a second emulated machine; it would also show sub 15
   arriving through `$183b4`); the LORD/MOUTHS speech.

For the emulator workstream: Timer A is a stub (64 interrupts per frame), so sampled sound plays at
the wrong rate (`systems.md` 6.2).

## Audit findings still needing an emulator run

From the docs audit; none changes a doc claim yet: the `$e012..$e058` water-raise block (`ai.md` 1,
not in the AI corpora; run a flood in a custom game with `join.py`); "260 frames" for run F in
`ai.md` 5 (the table shows about 399 `$13eda` calls); whether `swamp208.py run` from `cg2.snap`
reproduces run B's first 2997 frames; pause lengths (`$40` pauses 8 frames in the text, the
`t6 > 14` test gives 9; `$20` 15 or 16); trail-sprite frames 9 and 11 (`systems.md` 1.3 states a
sampling skip that the 8-tick sprite cycle does not guarantee); `graphics.md` "12 of 12" frames
(its table lists 10 plus a pointer variant); the strategy-note counts in `ai.md` 4 (16 of 19 swamp
decisions lost, volcano and knight timing, 4 quakes) have no script. Ghidra: this Mac's run fails 6
functions (`$ae14`, `$13dce`, `$188b0`, `$192ea`, `$20a66`, `$21244`), README now says so.

## Known traps

- A live compare over a call can catch Timer A ticks: the sample player's `$24952..$24963` changes
  while a sound plays (`live.py`'s `keep()` excludes it). Any new live harness needs the same
  exclusion, next to `$37f5a..$37f89` (trap wrappers' register save).
- `py/repl.py`'s `Repl` loses sync after a `bp`; use `py/powers/pwlib.Repl2`.
- `callcap` masks interrupts: a routine that waits for the VBL must be tested in two halves.
- The game runs in supervisor mode on one stack: interrupt handlers overwrite stack words below the
  main loop between frames (`systems.md` 1.3).
- `$14364` takes the view origin as pushed arguments: poke cx/cy before `$b6fc`, as `trailview.py`.
- A land click acts only when one of your entities is in view (`$3d54e`).
- `walker/snaps/*` rebuilt here differ from the Windows ones (fight1 frame 2665, not 2731): counts
  taken on the old states (8000/8000 decisions, 51863 cells) were not re-run on these.
- `pop_ad58.asm` was a strict prefix of the real listing; any other `<game>_ad58.asm` should be
  checked against the PRG header's text size before a "no writer" claim.
- Scripts spawn the emulator with cwd `M68000/`: pass absolute snapshot paths.
- `live.py` prints only the first 60 events per kind: to count a rare case (a knight mover, an
  entity index) add a tag in its kind branch rather than reading the event list.
- On this Mac the emulator runs about 28M steps a minute; `live.py fight` and `resolve` over 1500
  frames run fine as two parallel processes.
- A fresh checkout's `fight1` chain: drive recipe -> `repro`; one REPL `s 60000000` x4 -> late1..4;
  `campaign.py` (-> near) -> `campaign2.py` (-> front) -> `mkmode.py front mode_fight fight1`.
- Browser-pane screenshots lag one action behind: after a click or a JS state change, read the
  state through JS (or take a second screenshot) before judging the picture.
- The infographic's dark theme is unverified visually (the pane renders local files light only); its
  tokens are copied from PowerMonger's `dither_infographic.html`.

- GAME SETUP and OPTIONS items are hit only on their 8-pixel square (`x+16..x+24`, `y+16..y+24` of the
  `$22286` record, width field +4 = 8), not on the text; PAINT MAP needs CUSTOM GAME first.
- `$3c518/$3c51c` is the live pointer while a button latch is armed (VBL `$16c8e`), so a poke of it is
  overwritten within one VBL: move the pointer instead (`py/hooks/star_key.py`).
- `stserver`'s `mouse` clicks register in Populous (the menu drive in `paint_mana.py`), unlike Midwinter.

## Waiting on Dave

- Proposed skill line (`reverse-engineer-st-game`, naming rules): name a key scan code from the TOS key
  table in the ROM (TOS 1.00 UK file offset `$2034`, unshifted ASCII by scan code), not from memory. The
  docs called `$66` "unused by any physical key"; it is keypad `*`.

## Next session

Item 1, swamp208 238/238: run `swamp208.py poke` on this Mac to make `swamp208/p_spawn.snap`, wire
`powers_ref.claim_land` into `trail_ref.py`, re-run `py/systems/trailrun.py`; then the `$12f84` corpus
exclusion (`systems.md` 1.4). Rebuild any other `ANCHORS.md` snapshot on demand from its recipe.
Prompt: `/resume populous`.
