# Impossamole: handoff

Updated 2026-09-28 by the session that ended at commit `a7fad32` (workstream commit;
`fe769fb` is a small separate skill-file commit from the same session).

## Resume point

- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image,
  `coldboot_census/` (from-cold-boot scripts and snapshots), `gameplay_explore/` (movement/hazard
  trials, now including the 89th pass's `pass89_arch/` — watch/bpc logs and a whole-image
  disassembly, no new snapshots). See `scratchpad/ANCHORS.md` for the full indexed list. Real
  Hatari v2.6.1 at `~/Downloads/hatari-snapshot/Hatari.app`, source at `~/GitHub/hatari/`. TOS
  ROM at `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/gameplay_explore/pass86_left_settled.snap` (`x=74,y=152`,
  idle, trunk-blocked, `2/18` health) — **unchanged from last handoff**, but the jump that was
  documented as "clears the trunk cleanly" from here (`kbd ff`/`kbd 09`, up+right) is now known to
  be fatal: it clips a hazard mid-arc for 2 damage, exactly consuming this snapshot's `2/18` health
  margin. Do not reuse `pass87_jump_right_1M_settled.snap` or any `pass88_*` snapshot as a resume
  point — the hero is dead-but-not-yet-reloaded in all of them.
  **Must be run with `--disk-a "scratchpad/impossamole/impossamole cr replicants - emotion cr
  replicants.st"`** (path relative to `M68000/`) on every `resume ... repl`. The REPL's `snap
  <path>` command writes relative to the `dotnet` process's own working directory (`M68000/` if
  invoked from there) — give it the full path into `scratchpad/impossamole/gameplay_explore/`.
- Uncommitted work left behind: none from this pass. The pre-existing `M68000/sessions/README.md`
  whitespace-rewrap diff (predates this workstream, flagged unowned by several prior handoffs) is
  still there and still not this workstream's to fix. `.obsidian/` and `Cadaver/` at the repo root
  are also not this workstream's.

## Proven so far

See `reversing/impossamole/README.md`'s "Program classification", "Gameplay input" and "Past the
first screen" sections for full detail, match counts and exact addresses:

- **The program is hand-written 68000 assembly, not compiled C (89th pass)**: zero `4e56` (LINK
  A6) words across the ~260KB loaded image explored so far (`$2000`-`$42e00`). No decompile route
  for this game — `disassemble.py --all` plus live `watch`/`bpc`/`callcap` is the only path, as
  every pass has already been doing.
- **The hazard/collision mechanism is proven end to end** (82nd pass, unchanged since): `$00b71a`
  (generic asymmetric-radius proximity test) → `$00e80e` (copies the contacting object's own `+104`
  damage value into `$227f6`) → `$00eafa`'s fall-through (`$00eb8c`, applies it to health `$bb74`,
  arms a 7-frame hit-cooldown at `102(A0)`) → `$00ec50` (death handling) → `$b058`/`$b2d8`/`$17fe8`
  (reload into a real, rendered Game Over screen).
- **The hero's busy flag `$1a5d7` (`=$1a572+101`) is the death-animation lock, fully traced (89th
  pass)**: set once, at `$00ecce` inside `$00ec50`, only once health (`$bb74`) is zero *and* the
  hero is grounded (`$227f3<=1`) — so a fatal hit taken mid-air (state `2`/jump) does not visibly
  lock the hero until it lands. Cleared again at `$01ab66`, inside the already-proven `$b058`/
  `$1c3d8` reload chain. `$00c2fa` (movement dispatch, `jsr` from the main loop at `$00b20e`) and
  `$00eafa` (hit/death check, `jsr` at `$00b238`) are two separate main-loop call sites both gated
  on this same flag, branching differently while it is set.
- **A third hazard object exists at slot 9 (`$1a6b6`, `x=66,y=98`, radius `16`, `type=1`, static),
  between the twin-tree screen's known slot-8 (`$1a64a`) and slot-10 (`$1a722`) hazards** — the
  87th pass's "clean" trunk-clearing jump (`kbd ff`/`kbd 09` from `pass86_left_settled.snap`) clips
  its 16px radius twice during the ascent, costing exactly the `2/18` health the hero had, which is
  what the 88th pass mistook for an unexplained soft-lock (its "health unchanged at 18/18" read was
  wrong — that was `$bb75`, the max-health constant).
- **The `$25000` tile-classification table drives both the ladder-climb check and forward-movement
  collision, through the shared `$be96` lookup** (83rd pass, sharpened 86th): `$00c49c`'s up-handler
  climbs (`$227f3:=4`) only when the sensor directly overhead (`$227ea`) classifies as category `1`
  or `2`; `$00c3a6`'s forward-movement gate blocks walking when any of its three body-height sensors
  classify at category `>=4`. Category `0` (open sky) and `4` (tree trunk, solid) are directly
  confirmed live; `1`/`2`/`3`/`9`'s exact meanings beyond `1`/`2`=ladder-climbable are still open.
- **The HUD routine is `$00fdc4`** (83rd pass). **A real weapon/projectile system is proven from
  disassembly** (83rd pass): `$00d37c`/`$00d3cc` spawn `type=3` projectiles into object-array slots
  16-19 with a damage field equal to the equipped weapon. **Not yet found**: the routine that checks
  a projectile for contact against an enemy and applies damage the other way.
- **A dodge that survives the twin-tree crossing is proven (85th pass)**: held right+up until the
  hero's own state flips from `2` (jump) to `3` (fall), then switching to right-only right at that
  transition falls the hero through the hazard's contact band in one pass instead of bouncing back
  — one hit instead of three, landing alive at `x=192,y=144`, `2/18` health.
- **A real, table-driven jump mechanism exists and reaches past the trunk** (87th pass, unchanged):
  `$00c742` is one-shot entry, falls through into `$00cbbc`, the real per-frame handler (a `$cd54`
  velocity table driving genuine vertical displacement, plus a facing-locked horizontal push from
  `98(A0)` latched at takeoff). Confirmed live from `pass86_left_settled.snap` — but this exact
  jump is the one that clips the slot-9 hazard above.

## Open, in priority order

1. **Find a jump/route past the trunk that survives slot-9's hazard** (`$1a6b6`, `x=66,y=98`,
   16px radius) from `pass86_left_settled.snap` (`2/18` health, no margin for two hits). Either an
   arc that clears the radius entirely (a shorter hop, releasing "right" earlier so the ascent stays
   lower/further right sooner) or one that only clips it once — `watch bb74` across the attempt
   before trusting a landing spot, per the new "Known traps" entry in the README and the skill.
2. **Identify the green item visible near the fence-post landing spot** (`pass86_left_settled_zoom.png`,
   `coldboot_amazon_twintree_jump_landed.png`) — plausibly a health pickup, which would remove the
   health-margin problem in item 1 if reachable without dying first. Check its object-array slot and
   type once a survivable route to it exists.
3. **Find the projectile-vs-enemy damage path**, or confirm there isn't one in this build — unchanged
   from the 83rd pass. A `callcap` on `$00d3cc` from a primed state, then a live `watch` on the
   projectile slot while stepping past a nearby enemy, would settle it either way.
4. Identify what tile categories `$1`/`$2`/`$3` mean precisely (raw ids only known to map to
   ladder-climbable at the up-check).
5. Whether Orient/Ice Land/Bermuda Triangle load correctly in this emulator, from a fresh cold boot.
6. The Klondike cold-boot run past ~9M steps with no input reaches the shared reload region
   (`$1c3d8`-ish) — now well-explained by the same generic hazard-death/reload mechanism this pass
   re-confirmed; worth a quick render check but no longer a priority mystery.
7. Classify the twin-tree screen's full hazard cluster (slots 8/9/10 now known) — check for further
   slots nearby before assuming the cluster is complete.

## Known traps

All workstream-specific traps are in `reversing/impossamole/README.md`'s own "Known traps" section
— read it there. This pass added one, also folded into the `reverse-engineer-st-game` skill (§2):
**a maneuver proven to reach a target position is not proven safe** — check health and other
per-object status across the whole run, not just the destination, since a delayed visible symptom
(a death animation gated on landing) can look like an unrelated bug at the destination instead of a
consequence of the maneuver itself.

## Next session

Start with Open item 1: from `pass86_left_settled.snap`, try jump variants (shorter hold, earlier
release of "right", or a different up/right timing) that keep the arc clear of `(x=66,y=98)`'s 16px
radius, checking `$bb74` across the whole attempt with `watch` before trusting any landing spot as a
new resume point. If no arc avoids it cleanly, check whether taking exactly one hit (`2/18→1/18`)
and landing alive is survivable enough to then reach the green item (item 2) as a possible health
refill.
