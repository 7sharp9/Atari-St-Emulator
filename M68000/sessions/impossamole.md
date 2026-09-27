# Impossamole: handoff

Updated 2026-09-27 by the session that ended at commit `70b8c18` (workstream commit; the repo's
latest commit `80863e8` is a shared skill fix from the same session, see below).

## Resume point

- Last commit of this workstream: `70b8c18` "83rd pass -- maps the full $25000 tile table, names
  the HUD routine, and proves a real weapon/projectile system from disassembly".
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image,
  `coldboot_census/` (from-cold-boot scripts and snapshots), and `gameplay_explore/` (movement/hazard
  trials, now including the 83rd pass's continued right+up drive and fire probe). See
  `scratchpad/ANCHORS.md` for the full indexed list. Real Hatari v2.6.1 at
  `~/Downloads/hatari-snapshot/Hatari.app`, source at `~/GitHub/hatari/`. TOS ROM at
  `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/gameplay_explore/ru_step12M.snap` — the furthest live, alive
  Amazon state this workstream has (hero standing at the twin-tree/vine/totem-ladder screen, reached
  by continuing `ru_step8M.snap`'s held right+up another 4,000,000 steps). This is the right starting
  point for the top open item below: getting past the new hazard creature visible on that screen.
  `ru_step16M.snap` and `ru12_fire_1M/2M/3M.snap` are dead ends (post-death reload states), kept only
  as reference for what "died again" looks like at the PC/memory level.
  **Must be run with `--disk-a "scratchpad/impossamole/impossamole cr replicants - emotion cr
  replicants.st"`** (path relative to `M68000/`) on every `resume ... repl`, even when the stretch
  does no further disk I/O. Note: the REPL's `snap <path>` command writes relative to the `dotnet`
  process's own working directory (`M68000/` if invoked from there), not to any directory implied by
  context — give it the full path into `scratchpad/impossamole/gameplay_explore/` in the script
  itself, or `mv` the file afterward.
- Uncommitted work left behind: none from this pass. The pre-existing `M68000/sessions/README.md`
  whitespace-rewrap diff (predates this workstream, flagged unowned by several prior handoffs) is
  still there and still not this workstream's to fix. `.obsidian/` and `Cadaver/` at the repo root
  are also not this workstream's.

## Proven so far

See `reversing/impossamole/README.md`'s "Gameplay input" and "Past the first screen" sections for
full detail, match counts and exact addresses:

- **The hazard/collision mechanism is proven end to end** (82nd pass, unchanged this pass): `$00b71a`
  (generic asymmetric-radius proximity test) → `$00e80e` (copies the contacting object's own `+104`
  damage value into `$227f6`) → `$00eafa` (applies it to health `$bb74`, arms a 7-frame hit-cooldown)
  → `$00ec50` (death/respawn) → `$b058`/`$b2d8`/`$17fe8` (reload into a real, rendered Game Over
  screen). `callcap eafa` from a primed state gives the direct `$bb74`/`$1a5d8`/`$227f6` delta.
- **The `$25000` tile-classification table is fully mapped, not just probed** (83rd pass): read
  directly out of RAM (256 bytes, one category per raw tile ID), it has exactly six distinct values —
  `$0` (138, off-map), `$4` (79, walkable — the only category any known caller compares against
  besides `$9`), `$9` (6: IDs `$4f`-`$52`/`$f6`-`$f7`, every ground-hazard ID), and `$1`/`$2`/`$3`
  (10/10/13 entries, found but not yet semantically identified — no known caller reads them).
- **The HUD routine is identified**: `$00fdc4` builds a 17-tile health-pip string from `$bb74`/
  `$bb75` and blits it to both screen buffers via `$1c0aa` — this is what the hit-reaction's
  `$070xxx`/`$078xxx` screen writes were.
- **A real weapon/projectile system is proven from disassembly** (83rd pass, resolves the old "type=3,
  never observed live" item): `$00d37c` edge-detects the fire bit (`$227ef`/`$227f5`, previous-frame
  compare) and gates a shot on a 6-frame cooldown (`$227fd`) and not being airborne (`$227f3<3`);
  `$00d3cc` spawns four `type=3` projectile objects into object-array slots 16-19 (base `$1a9aa =
  $1a2ea + 16*108`, confirmed as a real code-recognised boundary by an independent `cmpa.l
  #$1a9aa,A1` loop bound at `$014d3a`) from a per-weapon 64-byte descriptor table at `$d4be` (indexed
  by equipped weapon `$bb72`), setting each projectile's own damage field `104(A1) := $bb72`.
  `$00bafc` is a separate, unrelated 5-slot (indices 7-11) type-3 draw-dispatch scan. **Not yet
  found**: the routine that checks a projectile for contact against an *enemy* and applies damage —
  the two `$b71a` call sites checked in the `$13fe8`-`$17922` per-type range are both enemy-vs-hero,
  not projectile-vs-enemy.
- **`type` is a rendering/behaviour class shared by hero and enemies, not a hero marker** (83rd pass,
  generalises the 82nd pass's `type=1` background-prop observation): a second `type=2` object (object
  array slot 8, base `$1a64a`) appears on the new twin-tree screen, with the same one-point `+104`
  damage field as the `type=1` hazard prop — proof the existing generic mechanism needs no new code
  to explain a second, different-looking enemy.
- **Continuing the held right+up drive from `ru_step8M.snap` another 8,000,000 steps reaches a new
  screen and a second death** (83rd pass): 12,000,000 steps in, a twin-tree/vine-curtain area with a
  totem/ladder structure and the new `type=2` hazard creature (`coldboot_amazon_twintree_ladder.png`);
  driving straight through it (even with fire held, which only fires once due to the edge-detection
  above) reproduces the same death→reload cycle by ~16,000,000 steps.

## Open, in priority order

1. **Get past the twin-tree screen's hazard creature alive**, from `ru_step12M.snap` — a different
   dodge timing (the right+up jump that cleared the first screen's ground hazard was driven straight
   through this one and died), or an actual landed weapon shot (see item 2). This is the actual
   reverse-engineering goal: mapping Amazon's level content past this point.
2. **Find the projectile-vs-enemy damage path**, or confirm there isn't one in this build. The write
   side (`$00d3cc` spawning a `type=3` slot with a damage field) is proven; nothing yet found reads a
   projectile slot to damage an enemy. Likely candidate: a per-type dispatch entry for `type==3`
   itself, parallel to how enemy types run their own hero-contact handler — not yet located. A
   `callcap` on `$00d3cc` from a primed state, then a live `watch` on the new projectile slot while
   stepping past a nearby enemy, would settle it either way.
3. Identify what tile categories `$1`/`$2`/`$3` mean (10/10/13 raw IDs each) — no known caller reads
   them yet, so this needs either a new caller search (`find_field_writers.py`/whole-image grep for
   `be96` callers not yet catalogued) or visual correlation with the totem/ladder/water tiles on the
   new screen.
4. Confirm whether Amazon's Game Over (`$b058`/`$b2d8`/`$17fe8`) and Klondike's unattended-death
   transition (reported reaching `$1c3d8`) are the same code path — not yet checked against each
   other directly.
5. The Klondike cold-boot run past ~9M steps with no input goes black and PC moves to `$1c3d8` —
   still not confirmed or rendered. Driving Klondike with real movement input instead of leaving it
   idle is probably the fastest way to resolve this, and opens up actual Klondike mechanics.
6. Live-test the ladder-climb (`$c812`/`$227f3:=4`) state transition — this pass's runs never
   actually climbed a ladder despite reaching a ladder structure.
7. Whether Orient/Ice Land/Bermuda Triangle load correctly in this emulator, from a fresh cold boot.
8. Classify the main game binary via the LINK-frame-count heuristic (§0 of the reversing skill) —
   not yet done.

## Known traps

All workstream-specific traps found so far are written up in `reversing/impossamole/README.md`'s own
"Known traps" section (disk-image reattachment on `resume ... repl`, the busy-poll false-"stuck"
read, screen double-buffering, imprecise sprite-position attribution, partial-memory-region checks,
and the `bt`/backtrace crash on a mid-unpacker-loop snapshot) — read it there rather than here, so
there's one copy. This pass's one new generalizable trap (a held fire button only edge-triggers once,
even though the raw IKBD byte is a level) has already been folded into
`.claude/skills/reverse-engineer-st-game/SKILL.md`'s "Drive it to gameplay" section, not left here.

## Next session

Start with Open item 1: resume `ru_step12M.snap` and find a way past the twin-tree screen's hazard
creature — try a different jump/dodge timing, or a deliberately-timed single shot (remember fire is
edge-triggered: send it as a fresh `kbd` packet, not a continuous hold) before walking into range.
Item 2 (does a fired shot actually damage an enemy) is worth settling alongside this, since it
directly affects whether "shoot past it" is even a viable strategy. Item 3 (the three
still-unidentified tile categories) is a natural side quest if a new tile type comes up while
exploring the new screen's totem/ladder/water tiles.
