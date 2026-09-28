# Impossamole: handoff

Updated 2026-09-28 by the session that ended at commit `bbe9a72` (workstream commit; the repo's
latest commit `d8a2bc5` is a shared `CLAUDE.md` fix from the same session, see below).

## Resume point

- Last commit of this workstream: `bbe9a72` "86th pass -- left-retreat lead disproven; hero settles
  at x=74 against the tree trunk, not x=142, and $227ea never classifies as ladder there".
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image,
  `coldboot_census/` (from-cold-boot scripts and snapshots), and `gameplay_explore/` (movement/hazard
  trials, now including the 86th pass's `pass86_*` scripts/snapshots). See `scratchpad/ANCHORS.md`
  for the full indexed list. Real Hatari v2.6.1 at `~/Downloads/hatari-snapshot/Hatari.app`, source
  at `~/GitHub/hatari/`. TOS ROM at `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/gameplay_explore/pass85_dodge1_1_5M_more.snap` — the twin-tree
  hazard crossed alive (one hit taken, health `2/18`), hero landed and settled at `x=192,y=144`. This
  is still the right resume point for anything past the original hazard; the left-retreat lead from
  here is now a proven dead end (see below), so the next idea needs a fresh approach from this same
  spot, not a further push left. `pass86_left_settled.snap` (`x=74,y=152`, idle, wall-blocked by the
  tree trunk) is the reference for why left doesn't work, not a resume point in its own right.
  **Must be run with `--disk-a "scratchpad/impossamole/impossamole cr replicants - emotion cr
  replicants.st"`** (path relative to `M68000/`) on every `resume ... repl`. Note: the REPL's `snap
  <path>` command writes relative to the `dotnet` process's own working directory (`M68000/` if
  invoked from there) — give it the full path into `scratchpad/impossamole/gameplay_explore/`.
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
- **The `$25000` tile-classification table drives both the ladder-climb check and forward-movement
  collision, through the shared `$be96` lookup** (83rd pass, sharpened 86th): `$00c49c`'s up-handler
  climbs (`$227f3:=4`) only when the sensor directly overhead (`$227ea`) classifies as category `1`
  or `2`; `$00c3a6`'s forward-movement gate blocks walking (in either direction) when any of its three
  body-height sensors classify at category `>=4`. Category `0` (off-map/open sky) and `4` (proven
  86th pass: the tree trunk itself, i.e. solid) are both directly confirmed live; `1`/`2`/`3`/`9`'s
  exact meanings are still not independently pinned beyond `1`/`2`=ladder-climbable.
- **The HUD routine is `$00fdc4`** (83rd pass). **A real weapon/projectile system is proven from
  disassembly** (83rd pass): `$00d37c`/`$00d3cc` spawn `type=3` projectiles into slots 16-19 with a
  damage field equal to the equipped weapon. **Not yet found**: the routine that checks a projectile
  for contact against an enemy and applies damage the other way.
- **The twin-tree screen's real hazard is identified precisely (84th pass)**: a live `bpc e82e 1`
  from `ru_step12M.snap` under held right+up catches the first hit with `A0=$0001a722` — object-array
  slot 10, a static `type=1` prop at `x=190,y=151`, radius bytes all `$10`, damage `1`.
- **A dodge that survives the crossing is proven (85th pass)**: held right+up until the hero's own
  state flips from `2` (jump) to `3` (fall, ~step 1,400,000-1,500,000 past `ru_step12M.snap`), then
  switching to right-only right at that transition falls the hero straight through the hazard's
  contact band in one pass instead of bouncing back into it — one hit (`3→2`) instead of three,
  landing alive at `x=192,y=144`, `2/18` health, idle (`pass85_dodge1_1_5M_more.snap`).
- **The left-retreat lead is a disproven dead end (86th pass)**: held left from the landing spot does
  not stop at `x=142` as an earlier fixed-step-count snapshot suggested (that was mid-walk,
  `$227f3=1`) — it continues to a real, confirmed-static stop at `x=74,y=152`, blocked by the tree
  trunk itself (`$227e2` classifies as category `4`, the forward-gate's own blocking threshold). At
  that resting spot `$227ea` (the up-climb sensor) reads category `0`, never ladder, even after
  2,700,000 steps holding up (which only produces a stationary jump/attack bob, `$227f3=2`, `y`
  oscillating `112↔120`, `x` fixed). The hero is one column short of wherever the ladder's own tile
  column would be, and cannot walk further left to reach it. `pass86_left_settled_zoom.png` shows a
  branch/platform jutting right from the trunk above head height — the next visual lead, but reaching
  it needs a real controlled jump, which is not proven to exist yet (the only jump-shaped state found
  so far, `$227f3=2` from `$c742`, is stationary here, not a displacement jump).

## Open, in priority order

1. **Find whether a real controlled jump exists, and if so what triggers it.** Every up-press tried
   so far (at two different x positions, `x=192` and `x=74`) lands in `$227f3=2` (`$c742`,
   "jump/attack") with no net horizontal or vertical displacement — a bob/attack animation, not a
   platforming jump. Disassemble `$c742` fully (only its header has been read) and check whether it
   ever applies a velocity/displacement to `2(A0)`/`4(A0)` under some condition (e.g. fire+direction,
   a different state precondition, or momentum carried from the earlier fall) that these two static
   tests didn't hit. If a real jump exists, the branch/platform in `pass86_left_settled_zoom.png` is
   the concrete target to try reaching from the trunk-blocked position.
2. **Find the projectile-vs-enemy damage path**, or confirm there isn't one in this build — unchanged
   from the 83rd pass. A `callcap` on `$00d3cc` from a primed state, then a live `watch` on the
   projectile slot while stepping past a nearby enemy, would settle it either way.
3. Identify what tile categories `$1`/`$2`/`$3` mean precisely (raw ids only known to map to
   ladder-climbable at the up-check; category `9`'s "ground-hazard" naming from the 83rd pass and
   category `4`'s "walkable" naming are now contradicted by the 86th pass's live proof that `4` is
   what blocks the forward-movement gate — worth reconciling with a few more classified sensor reads
   next time either category is read).
4. Confirm whether Amazon's Game Over (`$b058`/`$b2d8`/`$17fe8`) and Klondike's unattended-death
   transition (reported reaching `$1c3d8`) are the same code path.
5. The Klondike cold-boot run past ~9M steps with no input goes black and PC moves to `$1c3d8` —
   still not confirmed or rendered.
6. Whether Orient/Ice Land/Bermuda Triangle load correctly in this emulator, from a fresh cold boot.
7. Classify the main game binary via the LINK-frame-count heuristic (§0 of the reversing skill) —
   not yet done.

## Known traps

All workstream-specific traps found so far are written up in `reversing/impossamole/README.md`'s own
"Known traps" section — read it there rather than here, so there's one copy. This pass's
generalizable lesson (a fixed-step-count snapshot isn't proof of a rest position; check the mover's
state byte) has already been folded into `CLAUDE.md`, not left here.

## Next session

Start with Open item 1: disassemble `$c742` in full from a fresh `--linear` dump (its header is
already known: `moveq #1,D0; jsr $1c840; move.b #2,$227f3` then per-direction animation setup) to
see whether it ever moves `2(A0)`/`4(A0)`, and under what precondition. If a real jump turns up, try
it from `pass85_dodge1_1_5M_more.snap` (`x=192,y=144`) or from the trunk-blocked `pass86_left_settled
.snap` (`x=74,y=152`) toward the branch/platform visible in `pass86_left_settled_zoom.png`. Item 2
(does a fired shot actually damage an enemy) is a good side quest if the jump lead stalls.
