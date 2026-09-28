# Impossamole: handoff

Updated 2026-09-28 by the session that ended at commit `f532138` (92nd pass).

## Resume point

- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image,
  `coldboot_census/` (from-cold-boot scripts and snapshots), `gameplay_explore/` (movement/hazard
  trials, now including the 92nd pass's `pass92_*` scripts/snapshots — no new arch dumps). See
  `scratchpad/ANCHORS.md` for the full indexed list. Real Hatari v2.6.1 at
  `~/Downloads/hatari-snapshot/Hatari.app`, source at `~/GitHub/hatari/`. TOS ROM at
  `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/gameplay_explore/pass90_wall_192.snap` (`x=192,y=144`, idle,
  `2/18` health) — still the best resume point: the furthest-right safe ground position past the
  trunk, standing directly under the item's crossbar, reached by a route that takes zero damage.
  `pass90_x96jump_land_130.snap` (`x=130,y=144`, `2/18`, also safe) is the earlier waypoint on the
  same route. `pass91_from130_end.snap`, `pass92_arc600k.snap` and `pass92_earlyrelease.snap` are
  all **confirmed dead ends** (92nd pass): continuing the item-guard hit's arc with "up" held, or
  releasing "up" right at the arc's own peak, both still take the hit and then die to a second hit
  shortly after — kept only in `ANCHORS.md` as "already tried" reference, not resume points.
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

- **The program is hand-written 68000 assembly, not compiled C.** No decompile route — live
  `watch`/`bpc`/`callcap` plus `disassemble.py --all` is the only path.
- **The hazard/collision mechanism is proven end to end**: `$00b71a` (proximity) → `$00e80e`
  (proximity-scan block; `$00e82e` copies the *contacting object's own* `+104` damage into
  `$227f6`, `A0` = that object) → `$00eafa`'s fall-through (`$00eb8c`, applies it to health
  `$bb74` — by this point `A0` has been re-pointed at the *hero*, `$1a572`, not the attacker) →
  `$00ec50` (death handling) → `$b058`/`$b2d8`/`$17fe8` (reload into a real, rendered Game Over
  screen).
- **The object array's stride and base are proven**: 108 bytes/entry, base `$1a2ea` (hero is index
  6 at `$1a572` = `$1a2ea + 6*108`) — the same formula located every hazard slot found so far
  (7=`$1a5de`, 8=`$1a64a`, 9=`$1a6b6`, 10=`$1a722`, 12=`$1a7fa`).
- **The hero's busy flag `$1a5d7` is the death-animation lock**, entered only once health hits
  zero *and* the hero is grounded — a fatal hit taken mid-air doesn't visibly lock the hero until
  it lands.
- **A real, table-driven jump mechanism exists**: `$00c742` one-shot entry (facing latch,
  horizontal push committed at takeoff) falling through into `$00cbbc`, the per-frame handler (a
  `$cd54` velocity table). Releasing up during the arc's own idle-landing frame stops a retrigger
  and settles the hero there for good.
- **Item 1 closed (90th pass): a route past the trunk that takes zero damage** — walk right to
  `x=96` first (not `x=74`), then jump up+right; clears slot 9's `(x=66,y=98)`/16px hazard by a
  comfortable margin, lands idle at `x=130,y=144`, then plain held-right reaches `x=192` clean.
- **The item's guarding object is identified (91st pass), and the slot-9 dodge playbook is proven
  not to generalize to it.** Breaking on `$00e82e` (not `$00eb8c`, which by then reads the hero's
  own base) pins the contact as object-array index 12, base `$1a7fa`: `type=1`, hit radius
  `4/4/4(A0)` (far tighter than slot 9's 16px), damage `1`. Unlike the other `type=1` props its
  position isn't fixed — two pins from different takeoff points read `(217,115)` and `(211,119)`,
  a few pixels of drift despite zero velocity fields (inferred: script-driven sway, not proven).
  Taking off from `x=130` instead of `x=192` (the maneuver that dodged slot 9) still takes the hit
  — same `A0=$1a7fa`, confirmed via the same `e82e` pin — so out-running this hazard the way slot
  9 was out-run doesn't work; it sits too close to the item itself.
- **The jump is fully committed once triggered; releasing "up" mid-arc does not help (92nd pass).**
  Continuing `pass91_from130_end.snap`'s arc with "up" still held re-triggers `$c742` a second time
  and lands a fatal second hit — the ordinary hazard-death cycle, not a new mechanism. A fresh,
  finely-sampled jump from `x=192` shows the arc peaking (`y≈104`) around step 250,000-300,000 then
  descending into the first hit (`$bb74` `2→1`) around step 450,000 at `y≈109-112`. Releasing "up"
  right at the peak — well before any idle-landing frame, ruling out a held-input retrigger as the
  cause — does not abort or shorten the arc: the hero takes the same first hit, then a second,
  fatal one shortly after while still descending. This rules out an early-release dodge; the arc's
  shape and duration are fixed once `$c742` fires, only a *new* jump's trigger is input-gated.
  `coldboot_amazon_twintree_guard_hit.png` (rendered just after the first hit) shows a black winged
  creature circling near the crossbar/item — an unconfirmed candidate for slot 12's identity; a cold
  struct read of object 12 well after the contact gave coordinates inconsistent with the live-pinned
  `(217,115)`/`(211,119)`, so this needs a fresh `e82e`-pinned check, not a cold read, to settle.
- The `$25000` tile-classification table, the HUD routine (`$00fdc4`), and the weapon/projectile
  system (`$00d37c`/`$00d3cc`, slots 16-19) are all unchanged from prior passes — see the README.

## Open, in priority order

1. **Find a route to the item that survives or avoids slot 12's hazard.** Its radius is tight
   (`4/4/4`) and it sits close to the item; neither taking off further back (the slot-9 playbook,
   91st pass) nor releasing "up" mid-arc at the peak (92nd pass) dodges it — the arc's shape is
   fixed once triggered. Taking the one hit and continuing is also confirmed fatal now: holding
   through re-triggers a second, deadly jump (92nd pass). Untried: a jump triggered from a
   different `x`/timing so the hazard's own sway (open item 2) isn't in the way when the hero's
   arc passes through `y≈104-119`; a wholly different (non-jump) approach to the crossbar if one
   exists; or accepting the health cost as permanent (start the item route at `3/18`+ instead of
   `2/18`, if that's achievable) rather than trying to avoid the hit at all.
2. **Confirm what slot 12 actually is.** The 90th pass's "purple creature near the second post's
   base" guess looks wrong: `coldboot_amazon_twintree_guard_hit.png` (92nd pass) shows a black
   winged creature circling near the top of the crossbar instead, closer to the hazard's own `y`
   band, but this is still a visual guess — a cold struct read of object 12 didn't match the
   live-pinned contact position. Settle it with a fresh `bpc e82e 1` pin on slot 12 and a render
   taken at that exact step (see "Known traps" — a screen-area match alone isn't proof).
3. **Find the projectile-vs-enemy damage path**, or confirm there isn't one in this build —
   unchanged from the 83rd pass. A `callcap` on `$00d3cc` from a primed state, then a live `watch`
   on the projectile slot while stepping past a nearby enemy, would settle it either way.
4. Identify what tile categories `$1`/`$2`/`$3` mean precisely (raw ids only known to map to
   ladder-climbable at the up-check).
5. Whether Orient/Ice Land/Bermuda Triangle load correctly in this emulator, from a fresh cold
   boot.
6. Classify the twin-tree screen's full hazard cluster (slots 8/9/10/12 known) — check for further
   slots nearby before assuming complete.

## Known traps

All workstream-specific traps are in `reversing/impossamole/README.md`'s own "Known traps" section
— read it there. Nothing new to fold in this pass; the existing "check health, not just position"
and "roughly the right screen area is not proof" traps are exactly what the 91st and 92nd passes
leaned on and still haven't fully closed (item 2 above). The 91st pass's generalizable lesson — pin
a detect-then-apply hit at the *detect* site, not the *apply* site, since `A0` differs between them
— already went into `.claude/skills/reverse-engineer-st-game/SKILL.md` (commit `232ec63`), not here.

## Next session

Start with Open item 2: pin slot 12 live with `bpc e82e 1` and render at that exact step to settle
what it actually is (the 92nd pass's visual guess — a winged creature — isn't proven). That identity
may explain why the hazard can't be dodged by timing alone (item 1), and suggest a real fix (e.g. if
it's a flying creature with its own patrol/sway cycle, waiting for a specific phase before jumping,
or finding whether its cycle has a period long enough to read from a `watch`/`hits` census).
