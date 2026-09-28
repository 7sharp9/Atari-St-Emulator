# Impossamole: handoff

Updated 2026-09-28 by the session that ended at commit `57855ef` (workstream commit; the repo's
latest commit `7b58f98` is a shared skill fix from the same session, see below).

## Resume point

- Last commit of this workstream: `57855ef` "85th pass -- survives the twin-tree hazard crossing
  (one hit instead of three) and finds a safe leftward retreat toward the visible ladder".
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image,
  `coldboot_census/` (from-cold-boot scripts and snapshots), and `gameplay_explore/` (movement/hazard
  trials, now including the 85th pass's `pass85_*` dodge scripts). See `scratchpad/ANCHORS.md` for
  the full indexed list. Real Hatari v2.6.1 at `~/Downloads/hatari-snapshot/Hatari.app`, source at
  `~/GitHub/hatari/`. TOS ROM at `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/gameplay_explore/pass85_dodge1_1_5M_more.snap` — the twin-tree
  hazard crossed alive (one hit taken, health `2/18`), hero landed and settled at `x=192,y=144`.
  This supersedes `ru_step12M.snap` as the resume point for anything past the original hazard: it
  already carries the one unavoidable hit, so anything further that stays alive is real progress.
  `ru_step12M.snap` (pre-dodge) is still the right starting point if re-deriving the dodge itself.
  `pass85_jump2_end.snap`/`pass85_shorthop_end.snap` (any further jump from the landing spot is
  fatal) and `pass85_left_x142.snap` (a safe leftward retreat, health unchanged) are dead-end/lead
  references, not resume points in their own right — see `scratchpad/ANCHORS.md`.
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
- **The HUD routine is `$00fdc4`** (83rd pass). **A real weapon/projectile system is proven from
  disassembly** (83rd pass): `$00d37c`/`$00d3cc` spawn `type=3` projectiles into slots 16-19 with a
  damage field equal to the equipped weapon. **Not yet found**: the routine that checks a projectile
  for contact against an enemy and applies damage the other way.
- **The twin-tree screen's real hazard is identified precisely (84th pass)**: a live `bpc e82e 1`
  (the exact `$e80e` damage-write instruction) from `ru_step12M.snap` under held right+up catches the
  first hit with `A0=$0001a722` — object-array slot 10, a static `type=1` prop at `x=190,y=151`,
  radius bytes all `$10`, damage `1`. The `type=2` slot 8 object at `$1a64a` the 83rd pass named as
  the hazard from screen-area proximity was never actually caught doing the damage; treat it as
  unconfirmed. Plain up-holding (no right) delays the hits but never reaches the ladder-climb state
  either (`$227f3` stays `2`, never `4`) — the visible totem/ladder structure isn't proven climbable
  from `ru_step12M.snap`'s horizontal position.
- **A dodge that survives the crossing is proven (85th pass)**: held right+up until the hero's own
  state flips from `2` (jump) to `3` (fall, ~step 1,400,000-1,500,000 past `ru_step12M.snap`), then
  switching to right-only (dropping "up") right at that transition falls the hero straight through
  the hazard's contact band in one pass instead of bouncing back into it — one hit (`3→2`) instead of
  the original three, landing alive at `x=192,y=144`, `2/18` health, idle
  (`pass85_dodge1_1_5M_more.snap`, `coldboot_amazon_twintree_dodge_landed.png`, which also shows a
  real ladder on the left tree trunk). **The landing spot is still boxed in**: right goes nowhere for
  1,500,000 steps (a wall), and any further jump — held or a brief 30,000-step tap — is fatal at
  `2/18` health (`pass85_jump2_end.snap`, `pass85_shorthop_end.snap`). **Left is safe and open**:
  from the landing spot, holding left walks the hero to `x=142` with health unchanged
  (`pass85_left_x142.snap`, `coldboot_amazon_twintree_dodge_left.png`) — the first safe horizontal
  move off the hazard's danger corridor, and visibly closer to the ladder. Not yet followed up:
  whether `$227ea` classifies as ladder from `x=142`, or what's further left/up from there.
- **`CLAUDE.md`/the reversing skill gained two generalized lessons this pass** (their own small
  commits): attributing a shared mechanism's contact to the wrong nearby object instead of pinning it
  with a breakpoint on the mechanism's write site (84th pass), and releasing a held input at the
  game's own state transition rather than a guessed step count when the hold keeps re-triggering a
  hazard-revisiting state (85th pass).

## Open, in priority order

1. **Follow the left-retreat lead toward the ladder**: from `pass85_dodge1_1_5M_more.snap`
   (`x=192,y=144`, `2/18` health), hold left to `x=142` (already proven safe) and check `$227ea`
   there — does it classify as ladder now that the hero is under a different tile column? If so, this
   is the first real chance to prove the ladder-climb state (`$c812`/`$227f3:=4`) live, and a
   plausible route past the rest of the screen. If not, keep going left/explore what's further that
   direction (a different, unexamined part of the screen).
2. **Find the projectile-vs-enemy damage path**, or confirm there isn't one in this build — unchanged
   from the 83rd pass. A `callcap` on `$00d3cc` from a primed state, then a live `watch` on the
   projectile slot while stepping past a nearby enemy, would settle it either way.
3. Identify what tile categories `$1`/`$2`/`$3` mean (10/10/13 raw IDs each) — no known caller reads
   them yet.
4. Confirm whether Amazon's Game Over (`$b058`/`$b2d8`/`$17fe8`) and Klondike's unattended-death
   transition (reported reaching `$1c3d8`) are the same code path.
5. The Klondike cold-boot run past ~9M steps with no input goes black and PC moves to `$1c3d8` —
   still not confirmed or rendered.
6. Whether Orient/Ice Land/Bermuda Triangle load correctly in this emulator, from a fresh cold boot.
7. Classify the main game binary via the LINK-frame-count heuristic (§0 of the reversing skill) —
   not yet done.

## Known traps

All workstream-specific traps found so far are written up in `reversing/impossamole/README.md`'s own
"Known traps" section — read it there rather than here, so there's one copy. This pass's two new
generalizable lessons (mechanism-contact attribution via breakpoint, and input-release timed to a
state transition) have already been folded into `CLAUDE.md` and the reversing skill, not left here.

## Next session

Start with Open item 1: resume `pass85_dodge1_1_5M_more.snap` (already past the original hazard,
alive at `2/18` health) and hold left toward `x=142`, then check `$227ea`/try `up` to see if the
ladder is finally climbable from that column. Item 2 (does a fired shot actually damage an enemy) is
a good side quest if the ladder lead stalls — it also bears on whether "shoot the hazard" was ever a
viable alternative to dodging it.
