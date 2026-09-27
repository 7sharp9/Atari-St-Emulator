# Impossamole: handoff

Updated 2026-09-28 by the session that ended at commit `4076b7e` (workstream commit; the repo's
latest commit `5a0eebb` is a shared `CLAUDE.md` fix from the same session, see below).

## Resume point

- Last commit of this workstream: `4076b7e` "84th pass -- corrects the twin-tree hazard attribution
  and rules out plain up-holding as a ladder climb".
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image,
  `coldboot_census/` (from-cold-boot scripts and snapshots), and `gameplay_explore/` (movement/hazard
  trials, now including the 84th pass's `pass84_*` telemetry/breakpoint scripts). See
  `scratchpad/ANCHORS.md` for the full indexed list. Real Hatari v2.6.1 at
  `~/Downloads/hatari-snapshot/Hatari.app`, source at `~/GitHub/hatari/`. TOS ROM at
  `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/gameplay_explore/ru_step12M.snap` — unchanged from the 83rd
  pass: the furthest live, alive Amazon state this workstream has (hero standing at the twin-tree/
  vine/totem-ladder screen). This is still the right starting point for the top open item below.
  `ru_step16M.snap`, `ru12_fire_1M/2M/3M.snap`, `pass84_t2_5M.snap`, `pass84_t3_5M.snap` and
  `pass84_uponly_4_8M.snap` are all dead ends (post-death or slower-death states), kept only as
  reference for what "died again" looks like at the PC/memory level under different inputs.
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

- **The hazard/collision mechanism is proven end to end** (82nd pass, unchanged since): `$00b71a`
  (generic asymmetric-radius proximity test) → `$00e80e` (copies the contacting object's own `+104`
  damage value into `$227f6`) → `$00eafa` (applies it to health `$bb74`, arms a 7-frame hit-cooldown)
  → `$00ec50` (death/respawn) → `$b058`/`$b2d8`/`$17fe8` (reload into a real, rendered Game Over
  screen).
- **The `$25000` tile-classification table is fully mapped** (83rd pass): six distinct categories —
  `$0` (off-map), `$4` (walkable), `$9` (ground-hazard), and `$1`/`$2`/`$3` still semantically
  unidentified (no known caller reads them).
- **The HUD routine is `$00fdc4`** (83rd pass): builds a 17-tile health-pip string from `$bb74`/
  `$bb75` and blits it to both screen buffers.
- **A real weapon/projectile system is proven from disassembly** (83rd pass): `$00d37c` edge-detects
  the fire bit and gates a shot on a 6-frame cooldown and not being airborne; `$00d3cc` spawns
  `type=3` projectile objects into slots 16-19 with a damage field equal to the equipped weapon.
  **Not yet found**: the routine that checks a projectile for contact against an enemy and applies
  damage the other way.
- **The twin-tree screen's real hazard is identified precisely (84th pass), correcting the 83rd
  pass's attribution**: a live `bpc e82e 1` (the exact `move.b 104(A0),$227f6.l` instruction inside
  `$e80e`) from `ru_step12M.snap` under held right+up catches the first hit at step 1,596,247 with
  `A0=$0001a722` — object-array slot 10, a static `type=1` prop (`+8`/`+10` offsets both `0`) at
  `x=190,y=151`, radius bytes all `$10`, damage `1`. The `type=2` slot 8 object at `$1a64a` the 83rd
  pass named as the hazard from screen-area proximity was never actually caught doing the damage;
  it should be treated as unconfirmed. Exact contact geometry at the hit: hero `x=196,y=128` gives
  `dx=-14` (hero's own radius threshold `16`) and `dy=23` (threshold `24`) — both axes inside range,
  the same `$b71a` test already proven, just a different, previously-unexamined slot as `A0`.
- **Plain up-holding (no right) delays the hits but is not a fix, and never reaches the ladder-climb
  state either way (84th pass)**: from `ru_step12M.snap`, `kbd ff`/`kbd 01` takes two hits
  (`3→2→1`) over 4,800,000 steps, vs. three hits to death (`3→2→1→0`) by ~2,900,000 steps under
  held right+up (a corrected, more precise timing than the 83rd pass's "~2,500,000/one drop"
  estimate). In both runs the hero's movement state `$227f3` stays at `2` (jump/attack) at every
  checkpoint taken — it never reaches `4` (the ladder-climb state `$00c49c`'s up-handler sets when
  its ladder-above sensor `$227ea` classifies the tile above as climbable). So the visible
  totem/ladder structure on this screen is not proven climbable from this resume point/approach.
- **`CLAUDE.md`'s sprite-attribution trap generalized** (84th pass, its own small commit): the
  "roughly the right screen area" caution now explicitly covers attributing *which object* satisfies
  a shared per-frame mechanism (proximity/damage checks), not just which object rendered a sprite —
  pin the real object with a breakpoint on the mechanism's own write site instead of inferring it
  from nearby coordinates.

## Open, in priority order

1. **Get past the twin-tree screen's real hazard (`$1a722`, slot 10) alive**, from `ru_step12M.snap`.
   The 84th pass narrowed this from "some hazard near the totem/ladder area" to an exact static
   object and its exact contact geometry at the moment of the first hit (`x=190,y=151`, radius
   `$10`/`$10`/`$10`) — the next attempt should dodge *that* position specifically (a different
   jump arc/timing that keeps the hero's own `dx`/`dy` outside `16`/`24` of it), not the `type=2`
   object at `$1a64a`. Re-run `pass84_bp2.txt`'s `bpc e82e 1` pattern to re-catch the exact
   dx/dy at any new attempt's first near-miss or hit.
2. **Find the projectile-vs-enemy damage path**, or confirm there isn't one in this build — unchanged
   from the 83rd pass. The write side (`$00d3cc` spawning a `type=3` slot with a damage field) is
   proven; nothing yet found reads a projectile slot to damage an enemy. A `callcap` on `$00d3cc`
   from a primed state, then a live `watch` on the new projectile slot while stepping past a nearby
   enemy, would settle it either way — and would also settle whether firing at the `$1a722` hazard
   is even a viable strategy for item 1.
3. Identify what tile categories `$1`/`$2`/`$3` mean (10/10/13 raw IDs each) — no known caller reads
   them yet.
4. Confirm whether Amazon's Game Over (`$b058`/`$b2d8`/`$17fe8`) and Klondike's unattended-death
   transition (reported reaching `$1c3d8`) are the same code path.
5. The Klondike cold-boot run past ~9M steps with no input goes black and PC moves to `$1c3d8` —
   still not confirmed or rendered.
6. **Find an actual climbable ladder column and prove the climb state (`$c812`/`$227f3:=4`)** — the
   84th pass ruled out plain up-holding from `ru_step12M.snap`'s current horizontal position as a way
   to trigger it; this needs either a different X alignment on the twin-tree screen or a different
   screen entirely where the ladder-above sensor `$227ea` genuinely classifies as ladder.
7. Whether Orient/Ice Land/Bermuda Triangle load correctly in this emulator, from a fresh cold boot.
8. Classify the main game binary via the LINK-frame-count heuristic (§0 of the reversing skill) —
   not yet done.

## Known traps

All workstream-specific traps found so far are written up in `reversing/impossamole/README.md`'s own
"Known traps" section — read it there rather than here, so there's one copy. This pass's one new
generalizable trap (attributing a shared mechanism's contact to the wrong nearby object instead of
pinning it with a breakpoint on the mechanism's write site) has already been folded into
`CLAUDE.md`'s rule list, not left here.

## Next session

Start with Open item 1: resume `ru_step12M.snap` and try to dodge the now-precisely-located `$1a722`
hazard (static, `x=190,y=151`, radius `$10`) — a jump arc or timing that keeps the hero's `dx`/`dy`
outside its threshold, verified with the same `bpc e82e 1` technique this pass used to find it.
Item 2 (does a fired shot actually damage an enemy) is worth settling alongside this, since it
directly affects whether "shoot past it" is viable for item 1 too. Item 6 (ladder climb) is a natural
side quest if a new screen or a different X alignment on this one turns up a genuine ladder-above
sensor hit.
