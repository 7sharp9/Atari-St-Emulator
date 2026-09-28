# Impossamole: handoff

Updated 2026-09-28 by the session that ended at commit `dcaea2f` (workstream commit; `5602fad` is a
shared skill-file lesson from the same session, see below).

## Resume point

- Last commit of this workstream: `dcaea2f` "87th pass -- real jump mechanism proven, clears the
  trunk-blocked spot".
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image,
  `coldboot_census/` (from-cold-boot scripts and snapshots), and `gameplay_explore/` (movement/hazard
  trials, now including the 87th pass's `pass87_jump_right_*` scripts/snapshots). See
  `scratchpad/ANCHORS.md` for the full indexed list. Real Hatari v2.6.1 at
  `~/Downloads/hatari-snapshot/Hatari.app`, source at `~/GitHub/hatari/`. TOS ROM at
  `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/gameplay_explore/pass87_jump_right_1M_settled.snap` — the hero
  landed idle at `x=152,y=144`, past the tree trunk that blocked the 86th pass's ground-level
  approach, standing near a fence-post/ladder structure with a visible green item, not yet explored.
  `pass86_left_settled.snap` (`x=74,y=152`, trunk-blocked) is still useful as the "before" reference
  for the jump proof, not a resume point in its own right anymore.
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
  body-height sensors classify at category `>=4`. Category `0` (off-map/open sky) and `4` (the tree
  trunk, solid) are both directly confirmed live; `1`/`2`/`3`/`9`'s exact meanings are still not
  independently pinned beyond `1`/`2`=ladder-climbable.
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
- **The left-retreat lead is a disproven dead end (86th pass)**: held left from the landing spot
  settles at a real, confirmed-static stop at `x=74,y=152`, blocked by the tree trunk itself
  (`$227e2` classifies as category `4`). `$227ea` (the up-climb sensor) reads category `0` there,
  never ladder, even after 2,700,000 steps holding up (stationary jump/attack bob only).
- **A real, table-driven jump exists and clears the trunk (87th pass)**: `$00c742` is one-shot
  jump-state entry (sound, latch facing into `$227f4`, fire once if armed), not the per-frame jump
  logic; it falls through into `$00cbbc`, the real per-frame handler, proven by a `hits` census to
  run repeatedly across a held jump (42 hits over 1,000,000 steps vs. `$c742`'s 3). `$cbbc` applies a
  fixed facing-locked horizontal push (`98(A0)`, snapshotted at jump entry — not re-read from current
  input each frame, so the horizontal component is committed at takeoff) and indexes a signed-word
  vertical-velocity table at `$cd54` with a per-jump frame counter (`82(A0)`), adding the result
  straight into `4(A0)` — genuine vertical displacement, landing on a walkable ground sensor returns
  to idle (`$caba`) directly, and the table's `$7fff` sentinel forces a fall-state transition
  (`$cb2e`) if reached first. Live-confirmed from `pass86_left_settled.snap` (`x=74,y=152`,
  trunk-blocked): `kbd ff`/`kbd 09` (up+right) clears the trunk entirely, landing idle past it at
  `x=152,y=144` next to a fence-post/ladder structure with a visible green item
  (`pass87_jump_right_600k.snap`/`coldboot_amazon_twintree_jump_midair.png` mid-air,
  `pass87_jump_right_1M_settled.snap`/`coldboot_amazon_twintree_jump_landed.png` landed). This
  resolves the "no jump mechanism proven" gap the 86th pass left open — the two prior static up-only
  tests never combined the jump with a held direction, so they only ever saw the stationary bob.

## Open, in priority order

1. **Explore past the trunk from the new landing spot.** `pass87_jump_right_1M_settled.snap`
   (`x=152,y=144`, idle) stands near a fence-post/ladder structure with a visible green item
   (`coldboot_amazon_twintree_jump_landed.png`). Drive further right/up from here (the jump mechanism
   is now proven and controllable via `kbd ff`/`kbd 09` etc.) and see what's next — a new hazard, the
   level's actual ladder, a pickup, or a screen transition.
2. **Find the projectile-vs-enemy damage path**, or confirm there isn't one in this build — unchanged
   from the 83rd pass. A `callcap` on `$00d3cc` from a primed state, then a live `watch` on the
   projectile slot while stepping past a nearby enemy, would settle it either way.
3. Identify what tile categories `$1`/`$2`/`$3` mean precisely (raw ids only known to map to
   ladder-climbable at the up-check).
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
generalizable lesson (a state-transition's entry code can be a different address from the real
per-frame handler it falls through into; confirm the per-frame body with a `hits` census, not by
reading the entry's linear continuation alone) has already been folded into the
`reverse-engineer-st-game` skill, not left here.

## Next session

Start with Open item 1: from `pass87_jump_right_1M_settled.snap` (`x=152,y=144`, idle, past the
trunk), explore the fence-post/ladder structure and green item visible in
`coldboot_amazon_twintree_jump_landed.png`. The jump is now a proven, controllable move
(`kbd ff`/`kbd 09` etc. via `$c742`/`$cbbc`) — use it freely rather than treating it as an
open question. Item 2 (does a fired shot actually damage an enemy) is a good side quest if this
screen stalls.
