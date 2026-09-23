# Populous: handoff

Updated 2026-09-23 by the session that ended with the handoff commit after `c478455` (first session
on Dave's Intel Mac Pro).

## Resume point

- Last commits of this workstream: `e8a9071` (town take-over modelled), then the handoff commit.
  `f1d88d4` (DEVELOPING macOS notes) and `c478455` (CLAUDE.md macOS lines) are shared-file commits.
- `bin/` is built from HEAD on macOS; no `*.fs` has changed since `5c32af8`, so it is the same
  emulator every earlier count ran on.
- Working data: `$POP_WORK` = `M68000/scratchpad/pop/`, rebuilt on this Mac this session. Source
  files: `~/Library/CloudStorage/Dropbox/Daves/ST games/` (the Populous zip, hash in the README;
  `hatari-v2.6.1-480/tos100uk.img` copied to `M68000/TOS100UK.IMG`). Present: `files/`,
  `pop_ad58.img`, `pop_ad58.asm` (whole-image listing), `pop_ad58.c` (Ghidra 12.1.4, 231 functions),
  `pop_auto.st`, `repro`/`game_start` (= repro)/`g90`/`late1..4.snap`, `walker/snaps/near`, `front`,
  `gather1`, `fight1`. Everything else in `ANCHORS.md` (drive/A, ai/cg1, cg2, M1, powers/snaps,
  systems/spawn, swamp208, endgame) is **not** rebuilt here yet.
- Start from: `walker/snaps/fight1.snap` (frame 2665) for combat and take-overs.
- Uncommitted work left behind: none.

## Proven so far

Five topic docs, each count in the table at the top of `reversing/populous/README.md`; the README's
**Design digest** restates the rules (its combat line was updated this session).

- Graphics: frame rebuilt from RAM 64000/64000 on 12 frames; trail sprites 32/32; mouse UI 17/17.
- Terrain: generator byte-identical for 3 worlds; six powers + `$fe00`/`$feca`/`$108b8` under
  callcap **2670/2670** (`py/powers/pw_diff.py 40 2026` + `40 77`, re-run this session on macOS).
- Mechanics: settlements, mana, spawns; walker direction 2400/2400 + 8000/8000 live; knight
  154/154 live; combat `$1063a` every live call, rounds 97/97, resolutions 19/19; **town take-over**
  (`$108b8` non-knight branch, `$10366` claim/release, `$10068` settlement kill): live **7/7** from
  `fight1` (`py/powers/live.py fight1.snap 1500 fight resolve`, `mechanics.md` 3.5, 4.3), callcap
  **240/240** (settle 196 incl. 57 castles, stays walker 44). Armageddon brawl 441/441; score.
- AI: 4800/4800 decision routines; natural runs 1854/1854, 2766/2766; flood/armageddon casts.
- Systems: trails 400/400 + 400/400 callcaps, 394/394 live; the pop-208 swamp spawn 400/400 and
  237/238 frames; its edge is interrupt stack debris at `$3f418` (`systems.md` 1.3).
- The emulator is deterministic across Windows and macOS on the recipe path: `repro` frame 285 and
  late1..4 frames 835/1328/1763/2161, evil mana 7485, as documented.

## Open, in priority order

1. **`$ef4c`'s post-decision writes** (settle, merge, fight start `$10e7e`, occupancy and visit
   counts) diff-tested on their own; a knight merging into a friendly walker live. Callcap corpus in
   the style of `pw_diff.py`, then a live pass from `fight1`/`gather1`.
2. **The swamp208 237/238 frame**: `trail_ref.py` skips a settlement on a marked cell because
   `$10366` was not modelled; `powers_ref.claim_land` now is. Wire it in and re-run
   `py/systems/trailrun.py` from `swamp208/p_spawn.snap` (needs `swamp208.py poke` on this Mac
   first) for 238/238; same for the `$12f84` corpus exclusion (`systems.md` 1.4).
3. Smaller loose ends: sounds 5/6 and the `$37e78` bits (`systems.md` 6); the command that sets
   `$3c4e4`; `$135fc`'s second call site `$e580` live; the `$f6b2` swamp raise live; a full SAVE/LOAD
   round trip on a disk with space; PAINT MAP, RESTART/NEXT MAP; SPR_320 frames 9 and 11 live; a
   pop-208 spawn on edge 1 or a stale cell (poke `$3f418`); a live "winner stays a walker" take-over.
4. Lowest: the serial link (`$19652`, needs a second emulated machine); the LORD/MOUTHS speech.

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
- On this Mac the emulator runs about 28M steps a minute (drive recipe 78M steps in 2:45, measured);
  `live.py fight` and `resolve` over 1500 frames run fine as two parallel processes.
- A fresh checkout's `fight1` chain: drive recipe -> `repro`; one REPL `s 60000000` x4 -> late1..4;
  `campaign.py` (-> near) -> `campaign2.py` (-> front) -> `mkmode.py front mode_fight fight1`.

## Next session

Item 1: build a callcap corpus for `$ef4c`'s post-decision writes (settle, merge, `$10e7e` fight
start, occupancy/visit counts) against `walker_ref.py`, then check it live from `fight1.snap` and
`gather1.snap`. Rebuild any other `ANCHORS.md` snapshot on demand from its recipe.
Prompt: `/resume populous`.
