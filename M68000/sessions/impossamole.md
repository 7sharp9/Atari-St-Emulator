# Impossamole: handoff

Updated 2026-09-27 by the session that ended at commit `1bf12f7`.

## Resume point

- Last commit of this workstream: `1bf12f7` "record a bt/backtrace crash trap found this pass".
  Before it in the same pass: `0ccb003` (proves the hazard/collision mechanism end to end).
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image,
  `coldboot_census/` (the known-good from-cold-boot scripts and `at_gameplay_final.snap`/
  `klondike_plus_30M.snap`), and `gameplay_explore/` (movement-input trials from
  `at_gameplay_final.snap`, now including the hazard/damage-cycle scan and the post-death-reload
  run). See `scratchpad/ANCHORS.md` for the full indexed list. Real Hatari v2.6.1 at
  `~/Downloads/hatari-snapshot/Hatari.app`, source at `~/GitHub/hatari/`. TOS ROM at
  `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/gameplay_explore/ru_step8M.snap` — the furthest live, alive
  Amazon state this workstream has (hero standing on a ledge past totems/water, reached by holding
  right+up from `at_gameplay_final.snap`); this is the right starting point for item 1 below, the
  new top priority. `scratchpad/impossamole/gameplay_explore/after_reload_10M.snap` is a second,
  separate anchor — the Game Over screen's own idle loop, for anything about that screen itself.
  **Must be run with `--disk-a "scratchpad/impossamole/impossamole cr replicants - emotion cr
  replicants.st"`** (path relative to `M68000/`) on every `resume ... repl`, even when the stretch
  does no further disk I/O.
- Uncommitted work left behind: none from this pass. The pre-existing `M68000/sessions/README.md`
  whitespace-rewrap diff (predates this workstream, flagged unowned by several prior handoffs) is
  still there and still not this workstream's to fix. `.obsidian/` and `Cadaver/` at the repo root
  are also not this workstream's.

## Proven so far

See `reversing/impossamole/README.md`'s "Gameplay input" and "Past the first screen" sections for
full detail, match counts and the exact addresses:

- **The hazard/collision mechanism is proven end to end, not inferred from timing/visuals** (this
  pass). `$00b71a` is a generic, reusable proximity test any two objects can call (dozens of
  per-type handlers between `$013fe8`-`$017922` use it) — an *asymmetric single-radius* check per
  axis (compares the signed position gap against a radius byte taken from whichever side it points
  at, not the sum of both objects' radii), not a standard AABB-overlap test. `$00e80e` (hero-contact
  application, called after a successful `$b71a`) copies the *contacting object's own* struct offset
  `+104` damage value into a global pending-damage cell `$227f6` — live-checked, the green `type=1`
  object at `$1a5de` has `104(A0)=1`. `$00eafa` (once per frame) applies it to health `$bb74`;
  `$00ec50` handles death (respawn at half health in place if a "continue" flag is set, otherwise
  zero health, freeze input, start a death animation).
- **Pinned live with `callcap`, not just static disassembly.** Scanning 20 consecutive per-frame
  arrivals at `$eafa` exposed the exact cycle (contact sets `$227f6`; the *next* frame's `eafa` call
  is where health actually drops and a 7-frame hit-cooldown arms). Firing `callcap eafa` from that
  exact primed state gives the direct delta: `mem $00bb74 $04->$03`, `mem $01a5d8 $00->$07`, `mem
  $0227f6 $01->$00`.
- **The death->reload chain is resolved: it's a genuine Game Over, not a per-level retry.** `$ec50`
  returns with carry set, so the per-frame template's very next instruction (`bcs $b058`) fires;
  `$b058` tears down gameplay, calls `$b2d8` (re-unpacks the per-world resource pack — the "object
  array zeroes, PC transits `$1c6de`" symptom), then `jmp $17fe8`, which builds the Game Over
  screen's text+tombstone objects. Render-confirmed (not just code-shape inference): running the
  reload 10,000,000 steps further shows `GAME OVER` / `YOUR SCORE 000000` / `FINAL SCENE THE AMAZON`
  (`coldboot_amazon_game_over.png`). Same *category* of outcome as Klondike's unattended death, but
  not proven to share the literal `$1c3d8` address — that equivalence is still open, see below.
- Everything the earlier part of the 82nd pass proved (the `$b288` cold-boot timing fix, hero sprite
  renders, Klondike loads a real mine-cavern level, the green object's autonomous motion, the
  right+up jump avoiding the reload) is unchanged and still stands.

## Open, in priority order

1. **Continue driving with held right+up from `ru_step8M.snap`** into the terrain past the
   totems/water — the actual reverse-engineering goal (mapping Amazon's level content), now that the
   hazard/death mechanism blocking it is understood rather than just avoided.
2. Map the rest of the `$25000` tile-classification table's 256 entries — only categories `$4`
   (walkable, confirmed not hazardous) and `$9` (ground-hazard, read by `$eafa`'s own tile-sensor
   path, not yet seen triggering live) are characterized.
3. Identify the HUD/status-bar routine behind the screen-buffer writes (`$070xxx`/`$078xxx` region)
   the hit-reaction's `callcap` delta showed alongside the health decrement — presumably a
   lives/health indicator redraw, not yet named or proven.
4. Confirm whether Amazon's Game Over (`$b058`/`$b2d8`/`$17fe8`) and Klondike's unattended-death
   transition (reported reaching `$1c3d8`) are the *same* code path or two different routes to the
   same category of screen — not yet checked against each other directly.
5. The Klondike cold-boot run past ~9M steps with no input goes black and PC moves to `$1c3d8` —
   still not confirmed or rendered (may be the wrong screen buffer, see "Known traps" in the
   README). Driving Klondike with real movement input instead of leaving it idle is probably the
   fastest way to resolve this, and opens up actual Klondike mechanics, not examined at all yet.
6. Live-test the ladder-climb (`$c812`/`$227f3:=4`) and jump/attack (`$c742`/`$227f3:=2`) state
   transitions at the code level — this pass's jump input exercises the jump/attack path in
   practice but hasn't been read or proven at the disassembly level.
7. The `type=3` special case at `$bafc` — still never observed live.
8. Whether Orient/Ice Land/Bermuda Triangle load correctly in this emulator, from a fresh cold boot.
9. Classify the main game binary via the LINK-frame-count heuristic (§0 of the reversing skill) —
   not yet done.

## Known traps

All workstream-specific traps found so far are written up in `reversing/impossamole/README.md`'s own
"Known traps" section (disk-image reattachment on `resume ... repl`, the busy-poll false-"stuck"
read, screen double-buffering, imprecise sprite-position attribution, partial-memory-region checks,
and this pass's `bt`/backtrace crash on a mid-unpacker-loop snapshot) — read it there rather than
here, so there's one copy. The `callcap` register-preset syntax trap this pass also hit
(`callcap <addr> Rn=hexval` with no explicit `maxSteps` crashes the REPL) is now fixed at the source:
`.claude/skills/reverse-engineer-st-game/SKILL.md`'s §5.

## Next session

Start with Open item 1: resume `ru_step8M.snap` and continue holding right+up (or whatever the
terrain past the totems/water now demands) to keep mapping Amazon's level content — this is the
actual reverse-engineering goal, now unblocked by a proven rather than merely-avoided hazard
mechanism. Item 2 (finishing the `$25000` tile-classification table) is a natural side quest if a
new tile type comes up while driving further; items 4-5 (Klondike's own death screen and its
input-driven gameplay) are the next-highest-value work after Amazon's terrain is further mapped.
