# Impossamole: handoff

Updated 2026-09-28 by the session that ended at commit `6833e8c` (94th pass).

## Resume point

- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image,
  `coldboot_census/` (from-cold-boot scripts and snapshots), `gameplay_explore/` (movement/hazard
  trials, now including the 94th pass's `pass94_*` scripts/snapshots). See `scratchpad/ANCHORS.md`
  for the full indexed list. Real Hatari v2.6.1 at `~/Downloads/hatari-snapshot/Hatari.app`, source
  at `~/GitHub/hatari/`. TOS ROM at `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/gameplay_explore/pass94_dodge_item_landed.snap` (`x=192,y=144`,
  idle, `2/18` health) — the timing-dodge landing spot: same position as `pass90_wall_192.snap`
  (still the pre-dodge waypoint below it), reached by idling 300,000 steps then triggering the
  item-guard's jump with zero contact. `pass94_confirm.txt` in the same directory is the exact
  REPL script that reproduces it from `pass90_wall_192.snap`. **Confirmed (95th pass) not to have
  collected the item** — it's still the furthest-progressed safe position, not a finish line.
  `pass90_wall_192.snap` itself (`x=192,y=144`, idle, `2/18`, standing at the wall right under the
  crossbar) is still valid as the pre-dodge reference point. `pass91_from130_end.snap`,
  `pass92_arc600k.snap`, `pass92_earlyrelease.snap`, `pass93_e82e_pin.snap` are all **confirmed dead
  ends or reference-only pins**, not resume points — see the 92nd/93rd pass rows in
  `scratchpad/ANCHORS.md`.
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
- **Item 3 (dodge the guard's hazard): closed (94th pass).** The guard's jump arc is fixed in
  absolute time from trigger while the guard itself keeps drifting, so an idle wait before the
  trigger is the only lever needed — no new arc shape. Idling 250,000-450,000 steps (five values,
  50,000 apart) before `kbd ff`/`kbd 09`, held 15,000 steps then released to `kbd ff`/`kbd 08`, is a
  fully clean, zero-damage dodge, formula-confirmed at the margin (e.g. delay `0`'s contact: hazard
  `(217,115)` vs hero `(194,112)` gives `dx=15`/`dy=3` against thresholds `16`/`24`, both still
  in range) and re-checked clean (zero `$e82e` hits from any object) to 1,300,000-1,615,000
  post-trigger steps — see the README's 94th-pass paragraph for the full data. **Bonus finding**:
  three other delays (`200,000`, `500,000`-`550,000`, `600,000`) also clear slot 12 but were first
  misread as slot-12 catching up late; reading `A0` at the actual hit showed a different object,
  slot 8 (`$1a64a`) — closing the 84th pass's long-open "may still be a hazard, unconfirmed" flag on
  that object. `pass94_dodge_item_landed.snap` is the resume point.
- **The dodge does not collect the item (95th pass).** A whole-frame pixel diff between
  `pass90_wall_192.snap` (pre-jump, item still on the crossbar) and `pass94_dodge_item_landed.snap`
  (post-dodge landing) matches on `63,454`/`64,000` pixels; every differing pixel falls inside the
  drifting-hazard sprites' own band, and the item's own on-screen region is byte-identical between
  the two frames — see `coldboot_amazon_twintree_slot12dodge_landed.png`. An object-array dump of
  both snapshots (20 slots, `$1a2ea` base, 108-byte stride) explains why: the hero's own struct
  lands at the exact same `x=192,y=144` it took off from, so the dodge's arc never advances the
  hero's position at all, let alone up onto the crossbar where the item sits. *Why* some delays land
  at the crossbar height (`y=112`) while others fall through to the ground (`y=144`) is still
  unexplained (Open item 1) — reaching the item likely needs whatever maneuver gets the hero to stop
  *at* the crossbar height instead of just passing through it, or a distinct route entirely.
- The `$25000` tile-classification table, the HUD routine (`$00fdc4`), and the weapon/projectile
  system (`$00d37c`/`$00d3cc`, slots 16-19) are all unchanged from prior passes — see the README.

## Open, in priority order

1. **What decides the arc's landing height (`y=112` crossbar-rest vs `y=144` full ground) for a
   given pre-jump idle delay?** The same one-shot arc is fixed in time from trigger (92nd pass), yet
   delay `200,000` lands at `y=112` and delay `250,000` (only 50,000 steps later) lands at `y=144` —
   not yet mechanized, only observed as a real split in this pass's data (README 94th-pass paragraph).
   Raised in priority by the 95th pass's negative result: the dodge never advances the hero's
   position at all (it lands back at its exact takeoff spot, proven by object-array dump and a
   63,454/64,000-pixel render match against the pre-jump frame), so reaching the item likely needs a
   maneuver that actually stops the hero at the crossbar height rather than passing through it —
   understanding what controls landing height is the natural next lever to try, not just what keeps
   `250,000`-`450,000` clear of slot 8.
2. **Find a maneuver that actually reaches the item.** No trial so far advances the hero's `x`/`y`
   past its `pass90_wall_192.snap` takeoff spot at all (95th pass) — every dodge variant tried is a
   same-spot up+right hop. Worth trying: a run-up (held right into the jump, rather than a standing
   jump) for horizontal reach, or approaching from a different position/route than directly under the
   crossbar. No address for the item's own pickup/inventory state is known yet, so confirm any
   success the same way the 95th pass ruled failure out — a render/pixel diff against a frame where
   the item is still visible, not just "reached the crossbar" read as "got the item".
3. **Slot 8's own velocity field reads nonzero (`+2` in `x`) at its confirmed contact** — the
   83rd/84th passes' "static" read of it was on sight, never re-checked live the way slot 12's drift
   was (93rd pass). Worth a `watch`/two-pin drift check the same way, now that it's confirmed to be a
   real, live hazard rather than an unconfirmed one.
4. **Find the projectile-vs-enemy damage path**, or confirm there isn't one in this build —
   unchanged from the 83rd pass. A `callcap` on `$00d3cc` from a primed state, then a live `watch`
   on the projectile slot while stepping past a nearby enemy, would settle it either way.
5. Identify what tile categories `$1`/`$2`/`$3` mean precisely (raw ids only known to map to
   ladder-climbable at the up-check).
6. Whether Orient/Ice Land/Bermuda Triangle load correctly in this emulator, from a fresh cold
   boot.
7. Classify the twin-tree screen's full hazard cluster (slots 8/9/10/12 known, two of them — 8 and
   12 — now known to move rather than sit fixed) — check for further slots nearby before assuming
   complete, and check whether slots 9/10 also move given 8 and 12 turned out to.

## Known traps

All workstream-specific traps are in `reversing/impossamole/README.md`'s own "Known traps" section
— read it there, including the new one this pass added: a `bp`/`watch` check that finds nothing
inside its own step budget is not proof a maneuver is safe past that budget, *and* a hit inside a
wider budget is not proof it's the hazard you were aiming at — read `A0` at the stop, don't assume
identity from which trial you were running. Both halves folded into `CLAUDE.md` too, since they're
general methodological traps, not specific to this game.

## Next session

The 95th pass closed the item-pickup question negatively: `pass94_dodge_item_landed.snap`'s dodge
does not collect the crossbar item (a 63,454/64,000-pixel render match against the pre-jump frame
shows the item's own on-screen region untouched), and an object-array dump shows why — the hero
lands at the exact spot it took off from, never advancing toward the item at all. Start with Open
item 1 (what decides the arc's landing height) since it's the likeliest lever for actually stopping
the hero at the crossbar instead of passing through it; Open item 2 (try a run-up jump or a different
approach route) is the direct follow-on once landing height is understood.
