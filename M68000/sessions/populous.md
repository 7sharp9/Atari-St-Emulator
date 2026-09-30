# Populous: handoff

Updated 2026-09-30 by the session that ended at commit `509283d` (landscape infographic). The
previous handoff (2026-09-23) was stale: two later sessions committed without updating it, so this
rewrite folds in their results (`014c25c`, `a2e901b`, `0dcc1bc`, `ebcffc5`).

## Resume point

- Last commits of this workstream: `509283d` (landscape infographic), `a2e901b` (CHEAT hooks are
  not dead), `014c25c` ($ef4c post-decision writes proven), then the handoff commit.
- `bin/` is built from HEAD on macOS; no `*.fs` has changed since `5c32af8`, so it is the same
  emulator every earlier count ran on.
- Working data: `$POP_WORK` = `M68000/scratchpad/pop/`, rebuilt on this Mac. Source files:
  `~/Library/CloudStorage/Dropbox/Daves/ST games/` (the Populous zip, hash in the README;
  `hatari-v2.6.1-480/tos100uk.img` copied to `M68000/TOS100UK.IMG`). Present: `files/`,
  `pop_ad58.img`, `pop_ad58.asm` (**truncated at $1d462, under 40% of the image: never use it for
  a "no writer" claim**), `pop_ad58.c` (Ghidra 12.1.4), `pop_auto.st`, `repro`/`game_start`/`g90`/
  `late1..4.snap`, `walker/snaps/near`, `front`, `gather1`, `fight1`. Everything else in
  `ANCHORS.md` (drive/A, ai/cg1, cg2, M1, powers/snaps, systems/spawn, swamp208, endgame) is **not**
  rebuilt here yet.
- Start from: `walker/snaps/fight1.snap` (frame 2665) for combat and take-overs.
- Uncommitted work left behind: none from this workstream (`M68000/sessions/README.md` and
  `Cadaver/`, `.obsidian/` belong to other sessions).

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
  `walker_ref.apply_decision`; two `$101a0` fighter-animation bytes excluded, no model). Armageddon
  brawl 441/441; score.
- AI: 4800/4800 decision routines; natural runs 1854/1854, 2766/2766; flood/armageddon casts.
- Systems: trails 400/400 + 400/400 callcaps, 394/394 live; the pop-208 swamp spawn 400/400 and
  237/238 frames (`systems.md` 1.3).
- Hidden hooks: the two "CHEAT" prints are **not** dead code. `$37eae` has a writer in
  `ikbd_read_byte` (`$02004e`); `$3c4e4` is set by command 14 sub 15 (`$01fbc4`), and the same
  dispatcher's sub 10 doubles the local mana. Found with `tools/find_field_writers.py`, after a
  grep of the truncated `pop_ad58.asm` had said otherwise (`graphics.md` Scrolling, `mechanics.md`
  section 7). Not triggered live yet.
- Landscape infographic `reversing/populous/landscape_infographic.html` (this session): JS port of
  the terrain code, **375/375** random cases against `popgen`, `powers_ref`, `pop_render`,
  `popdrive` (`uv run python reversing/populous/py/landscape_infographic.py --check`, from
  `M68000/`; needs node). A raise at (11,16) on a generated GENESIS changes 134 corners, the
  emulator's count. The check was mutation-tested (7 of 8 deliberate bugs caught).
- The emulator is deterministic across Windows and macOS on the recipe path: `repro` frame 285 and
  late1..4 frames 835/1328/1763/2161, evil mana 7485.

## Open, in priority order

1. **Post-decision branches live** (`mechanics.md` 10): fight start, join fight and a knight merging
   into a friendly walker have only run under callcap; take-over "winner stays a walker"
   (`$18206` = 0), a castle claimed by `$10366`, `$10068` killing a settlement outside a fight are
   modelled but never compared live. Live pass from `fight1`/`gather1` with `py/powers/live.py`,
   and a model of `$101a0`'s two fighter-animation bytes to drop the exclusion.
2. **How command 14 sub 15 and sub 10 are issued** (the cheat path): trace `FUN_0001a01e` and its
   guard `DAT_0003c4e0` (keystrokes through `ikbd_read_byte` into the sub-dispatcher), name what text
   the game compares, then trigger it live (and the `$b9fa` print via scancode `$66` with the mouse
   in the top-right corner in query mode). This would settle whether the game has a cheat code.
3. **The swamp208 237/238 frame**: `trail_ref.py` skips a settlement on a marked cell because
   `$10366` was not modelled; `powers_ref.claim_land` now is. Wire it in and re-run
   `py/systems/trailrun.py` from `swamp208/p_spawn.snap` (needs `swamp208.py poke` on this Mac
   first) for 238/238; same for the `$12f84` corpus exclusion (`systems.md` 1.4).
4. Smaller loose ends: sounds 5/6 and the `$37e78` bits (`systems.md` 6); `$135fc`'s second call
   site `$e580` live; the `$f6b2` swamp raise live; a full SAVE/LOAD round trip on a disk with
   space; PAINT MAP, RESTART/NEXT MAP; SPR_320 frames 9 and 11 live; a pop-208 spawn on edge 1 or a
   stale cell (poke `$3f418`). Infographic: the minimap colour of shapes above `$2e` (rocks,
   swamp, ruins) has no traced table entry, so the page draws them as plain land.
5. Lowest: the serial link (`$19652`, needs a second emulated machine); the LORD/MOUTHS speech.

For the emulator workstream: Timer A is a stub (64 interrupts per frame), so sampled sound plays at
the wrong rate (`systems.md` 6.2).

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
- Scripts spawn the emulator with cwd `M68000/`: pass absolute snapshot paths.
- On this Mac the emulator runs about 28M steps a minute; `live.py fight` and `resolve` over 1500
  frames run fine as two parallel processes.
- A fresh checkout's `fight1` chain: drive recipe -> `repro`; one REPL `s 60000000` x4 -> late1..4;
  `campaign.py` (-> near) -> `campaign2.py` (-> front) -> `mkmode.py front mode_fight fight1`.
- Browser-pane screenshots lag one action behind: after a click or a JS state change, read the
  state through JS (or take a second screenshot) before judging the picture.
- The infographic's dark theme is unverified visually (the pane renders local files light only); its
  tokens are copied from PowerMonger's `dither_infographic.html`.

## Next session

Item 1: a live pass for the post-decision branches from `fight1.snap`/`gather1.snap` (fight start,
join fight, knight merge, take-over "winner stays"), plus a `$101a0` fighter-animation model to drop
the two excluded bytes. If Dave wants the hidden-feature question answered first, item 2.
Rebuild any other `ANCHORS.md` snapshot on demand from its recipe.
Prompt: `/resume populous`.
