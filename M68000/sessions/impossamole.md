# Impossamole: handoff

Updated 2026-09-28 by the session that ended at commit `c3db349` (93rd pass).

## Resume point

- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image,
  `coldboot_census/` (from-cold-boot scripts and snapshots), `gameplay_explore/` (movement/hazard
  trials, now including the 93rd pass's `pass93_*` scripts/snapshots). See `scratchpad/ANCHORS.md`
  for the full indexed list. Real Hatari v2.6.1 at `~/Downloads/hatari-snapshot/Hatari.app`, source
  at `~/GitHub/hatari/`. TOS ROM at `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/gameplay_explore/pass90_wall_192.snap` (`x=192,y=144`, idle,
  `2/18` health) — still the best resume point: the furthest-right safe ground position past the
  trunk, standing directly under the item's crossbar, reached by a route that takes zero damage.
  `pass90_x96jump_land_130.snap` (`x=130,y=144`, `2/18`, also safe) is the earlier waypoint on the
  same route. `pass91_from130_end.snap`, `pass92_arc600k.snap`, `pass92_earlyrelease.snap` and the
  93rd pass's `pass93_e82e_pin.snap` are all **confirmed dead ends or reference-only pins**, not
  resume points: continuing the item-guard hit's arc with "up" held, or releasing "up" right at the
  arc's own peak, both still take the hit and then die to a second hit shortly after.
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
  zero *and* the hero is grounded.
- **A real, table-driven jump mechanism exists**: `$00c742` one-shot entry falling through into
  `$00cbbc`, the per-frame handler (a `$cd54` velocity table). The arc is fully committed once
  triggered — releasing "up" mid-arc does not abort or reshape it (92nd pass); only whether a *new*
  jump retriggers at the idle-landing frame is input-gated.
- **Item 1 (route past the trunk): closed (90th pass)** — walk right to `x=96` first, then jump
  up+right; clears slot 9's hazard by a comfortable margin, lands idle at `x=130,y=144`, then plain
  held-right reaches `x=192` clean.
- **Item 2 (what guards the item at the crossbar): closed (93rd pass).** Slot 12 (`$1a7fa`) is a
  small flying creature, not a static prop. Re-pinning the 91st pass's `bpc e82e`-equivalent
  contact (`bp e82e 491000` from `pass90_wall_192.snap`) is fully deterministic: step 490,587,
  `A0=$1a7fa`, `x=217,y=115`, `type=1`, radius `4/4/4`, damage `1`. Two totally-idle snapshots
  1,000,000 steps apart (no input at all) proved this object's position is **not** static: it
  drifts continuously (`(188,161)` → `(62,240)`, off the bottom of the visible screen) at
  `~-0.126px/step` x / `~+0.079px/step` y, a rate confirmed by a live `watch 1a7fc 4` (214 writes,
  all from `$019aba`/`$019abe` — not the velocity-integration fields at `8`/`10(A0)`, which read
  `0` at every struct snapshot taken). A same-fixed-screen-region comparison between the two idle
  renders (`reversing/impossamole/coldboot_amazon_twintree_slot12_drift.png`) isolates the one
  sprite that actually moves — a small winged creature — from everything else on screen (saw-wheel
  structure, crossbar, item, hero, the separate "purple creature" prop), all pixel-identical across
  the gap. This also reconciles the 91st pass's "a few pixels of drift between two pins" as real:
  at this rate, two pins close together in elapsed steps land only a few pixels apart. **Open
  sub-question**: idle struct reads show `type=0` where the live contact pin reads `type=1` —
  possibly an activation/danger-range flag, not confirmed.
- The `$25000` tile-classification table, the HUD routine (`$00fdc4`), and the weapon/projectile
  system (`$00d37c`/`$00d3cc`, slots 16-19) are all unchanged from prior passes — see the README.

## Open, in priority order

1. **Find a route or timing past slot 12's hazard, now that its motion is characterized.** It's a
   flying creature drifting at a known, roughly constant rate (`~-0.126px/step` x, `~+0.079px/step`
   y while unobstructed), not a static prop — the untried idea is to search for a takeoff `x`/delay
   whose jump-arc crossing of the hazard's `y`-band (`y≈104-119`, from the 92nd pass) lands outside
   its combined hitbox with the hero (`dx` within hero's own `12(A1)=16`, `dy` within `13(A1)=24`)
   given where the drift has carried it to at that elapsed step count. Concretely: from
   `pass90_wall_192.snap`, `watch 1a7fc 4` through several different takeoff delays (a few seconds
   of idle wait before triggering the jump) and check whether the creature's position at the
   predicted arc-crossing step ever clears the hero's hitbox. Taking the one hit and continuing is
   confirmed fatal (92nd pass: holding through retriggers a second, deadly jump) — a dodge, not a
   tank-the-hit plan, is the target.
2. **Find the projectile-vs-enemy damage path**, or confirm there isn't one in this build —
   unchanged from the 83rd pass. A `callcap` on `$00d3cc` from a primed state, then a live `watch`
   on the projectile slot while stepping past a nearby enemy, would settle it either way.
3. Identify what tile categories `$1`/`$2`/`$3` mean precisely (raw ids only known to map to
   ladder-climbable at the up-check).
4. Whether Orient/Ice Land/Bermuda Triangle load correctly in this emulator, from a fresh cold
   boot.
5. Classify the twin-tree screen's full hazard cluster (slots 8/9/10/12 known, one of them —
   slot 12 — now known to be mobile rather than fixed) — check for further slots nearby before
   assuming complete, and check whether any of 8/9/10 also move given 12 turned out to.

## Known traps

All workstream-specific traps are in `reversing/impossamole/README.md`'s own "Known traps" section
— read it there. Nothing new to fold in this pass that isn't already covered by the existing
"prove a static-looking value live before trusting it" and "detect-site vs apply-site" traps: this
pass's slot-12 finding is exactly an instance of the first one (a struct read that looked
*approximately* static across widely-spaced pins turned out to be continuously moving), not a new
failure mode.

## Next session

Start with Open item 1: use the known drift rate to search for a takeoff timing (idle delay before
the jump trigger) that puts slot 12 outside the hero's hitbox at the moment the arc crosses its
`y`-band. `watch 1a7fc 4` from `pass90_wall_192.snap` through a few different idle delays before
`kbd ff`/`kbd 09` will show where the creature actually is at each trial's arc-crossing step;
compare against the hero's own `12(A1)`/`13(A1)` thresholds (`16`/`24`) rather than guessing visually.
