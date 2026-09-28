# Impossamole: handoff

Updated 2026-09-28 by the session that ended at commit `739ccfb` (97th pass).

## Resume point

- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image,
  `coldboot_census/` (from-cold-boot scripts and snapshots), `gameplay_explore/` (movement/hazard
  trials, now including the 94th pass's `pass94_*` scripts/snapshots). See `scratchpad/ANCHORS.md`
  for the full indexed list. Real Hatari v2.6.1 at `~/Downloads/hatari-snapshot/Hatari.app`, source
  at `~/GitHub/hatari/`. TOS ROM at `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/gameplay_explore/pass90_wall_192.snap` (`x=192,y=144`, idle,
  `2/18` health, standing at the wall right under the crossbar). **`pass94_dodge_item_landed.snap` is
  not a further resume point — 95th-pass correction: it is state-for-state identical to
  `pass90_wall_192.snap`**, because the `kbd ff`/`kbd 09` trigger it used (delay `300,000`, 15,000-step
  hold) never actually registered (see "Proven so far" below); keep `pass94_confirm.txt` only as a
  worked example of the input-timing bug, not as a reproducible dodge. `pass95_realdodge_300k_30khold.snap`
  (a real jump, properly held, paused at its *second* hit from slot 8) is a confirmed dead end, kept
  as a reference pin, not a resume point. `pass91_from130_end.snap`, `pass92_arc600k.snap`,
  `pass92_earlyrelease.snap`, `pass93_e82e_pin.snap` are all **confirmed dead ends or reference-only
  pins** too — see the 92nd/93rd pass rows in `scratchpad/ANCHORS.md`.
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
- **Item 3 (dodge the guard's hazard): reopened (95th pass retraction) — the 94th pass's "closed"
  verdict was a measurement artifact, not a real dodge.** The 94th pass read five idle delays
  (`250,000`-`450,000`) that left the hero exactly where it started, undamaged, as a clean zero-damage
  dodge. A `watch` on the jump routine's own frame counter (`$1a5c4`) shows the jump's entry point was
  **never reached at all** for those five delays (zero writes, vs 17 for every delay confirmed to
  fire) — the `kbd ff`/`kbd 09` packet is enqueued with no lead-in gap, and the game only samples it on
  its own ~24,000-step poll cycle; a 15,000-step hold is shorter than that cycle, so whether the poll
  falls inside the hold window depends on the idle delay's phase, and `250,000`-`450,000` all land in
  the same dead band. Holding 30,000 steps instead (longer than one full poll cycle) makes the jump
  fire reliably even at delay `300,000` — but the result still isn't a lasting safe landing: it lands
  clean at `y=112` for 700,000 steps, then a further `bp e82e` window catches a hit from slot 8 after
  `360,435` more steps, and a second hit `251,999` steps after that
  (`pass95_realdodge_300k_30khold.snap`). **No delay/hold combination tried so far produces a
  genuinely, indefinitely safe rest position at the crossbar** — every real jump takes a hit from
  either slot 12 (mid-air, delays `0`-`150,000`) or slot 8 (at rest, delays `200,000`/`500,000`-
  `550,000`/`600,000`, and now also the properly-held `300,000`). This also answers the 94th pass's
  "what decides landing height" question: there is no variable height — a real jump always lands at
  `y=112`; `y=144` only ever meant no jump ran at all. Closes the 84th pass's long-open "may still be a
  hazard, unconfirmed" flag on slot 8 (`$1a64a`) as a real, live, and — per the 30,000-step-hold
  retest — apparently patrolling hazard, not the static prop it looked like on sight.
- **The dodge does not collect the item (95th pass) — for a different reason than first written up.**
  A whole-frame pixel diff between `pass90_wall_192.snap` and `pass94_dodge_item_landed.snap` matches
  on `63,454`/`64,000` pixels, every differing pixel inside the drifting-hazard sprites' own band, and
  the item's own on-screen region byte-identical between the two frames — see
  `coldboot_amazon_twintree_slot12dodge_landed.png`. That render-diff result is real and stands. The
  explanation first given for it (a completed round-trip jump landing back at its takeoff spot) does
  not: per the retraction above, no jump ran at all for this snapshot's delay, so the match is simply
  because nothing moved. Reaching the item still needs a maneuver that gets the hero onto the crossbar
  top *and* off it again before slot 8 arrives — not yet found.
- **The "wall" at `x=192` is disassembled and confirmed to be uncrossable by any jump/walk shape at all
  (97th pass) — not a tile-collision wall, a hardcoded per-frame position correction.** `$00c450` checks
  every frame whether the hero's `x > 192` ($c0); if so it computes `min(x-192, 2)` as a shared delta
  (`$1883c`) and arms a gate (`$227f1` bit 3). `$00bb3a`-`bb68` then walks all 20 object-array slots and
  subtracts that shared delta from `2(A0)`/`48(A0)` for any slot whose `30(A0)` word reads exactly
  `$00ff` — true for the hero and every hazard slot checked (7/8/9/10/12), so it's a uniform
  camera-follow-style correction across every flagged object, not a per-object wall test. Live-confirmed
  against the mechanism, not just the disassembly: a genuine jump that *passes* the jump-state's own
  tile-forward gate (`$00cc60`, checked via `hits` — entered 15 times, its add at `$00ccc4` reached 7 of
  those) and writes `x=194` still gets pulled straight back to `192` by `$00bb5c` a few thousand steps
  later, every time, across four consecutive real hits. **This is the actual root cause of every failed
  escape in the 96th pass — no timing, hold, or arc shape can ever get the hero's `x` past 192 on this
  screen**, independent of tile collision entirely. Open question, not yet checked: `$1883c` has exactly
  one reader (`bb5c`) and no second consumer was found that would shift a background/tile scroll offset
  to match — if this screen is meant to scroll here, that half of the mechanism may be unimplemented in
  this port (unconfirmed against real Hatari).
- The `$25000` tile-classification table, the HUD routine (`$00fdc4`), and the weapon/projectile
  system (`$00d37c`/`$00d3cc`, slots 16-19) are all unchanged from prior passes — see the README.

## Open, in priority order

1. **Find the real route to the item — it is not rightward jumping/walking past `x=192` on this
   screen, closed as impossible (97th pass).** `$00c450`/`$00bb3a`-`bb68` (disassembled and
   live-confirmed, see "Proven so far") pull the hero's `x` back down by up to `2`/frame whenever it
   exceeds `192`, every frame, independent of tile collision — a genuine jump that passes its own
   tile-forward gate and briefly reaches `194` gets reverted a few thousand steps later regardless.
   This is the root cause of all three 96th-pass escape failures and closes off any further "jump
   timing/shape" search as a way past the crossbar. Two real leads instead: (a) approach from a
   different direction/height entirely — the left tree's ladder was a dead end from ground level (86th
   pass) but was never tried after climbing from a higher entry point, and a route that never needs the
   hero's `x` to exceed 192 on *this* screen sidesteps the correction entirely; (b) check whether this
   screen is supposed to scroll when the `$00c450` trigger fires and the corresponding background/tile
   shift is simply missing in this port — `$1883c` (the shared correction delta) has exactly one reader
   found so far (`$00bb5c`); if a second consumer that shifts a screen/tile scroll offset exists and
   hasn't been found, or if real Hatari visibly scrolls this exact screen and this emulator doesn't,
   that would be a genuine emulator bug worth its own investigation, not a level-design dead end.
2. **Characterize slot 8's own drift/patrol rate**, the way slot 12's was pinned in the 93rd pass — the
   30,000-step-hold retest shows it reliably reaches the crossbar rest spot within roughly 360,000-
   620,000 steps of a jump landing there, but the underlying rate/cycle isn't measured. Needed to know
   whether there's a timing window at the crossbar itself, the way slot 12 had one in the air.
3. **Find the projectile-vs-enemy damage path**, or confirm there isn't one in this build —
   unchanged from the 83rd pass. A `callcap` on `$00d3cc` from a primed state, then a live `watch`
   on the projectile slot while stepping past a nearby enemy, would settle it either way.
4. Identify what tile categories `$1`/`$2`/`$3` mean precisely (raw ids only known to map to
   ladder-climbable at the up-check).
5. Whether Orient/Ice Land/Bermuda Triangle load correctly in this emulator, from a fresh cold
   boot.
6. Classify the twin-tree screen's full hazard cluster (slots 8/9/10/12 known, two of them — 8 and
   12 — now known to move rather than sit fixed) — check for further slots nearby before assuming
   complete, and check whether slots 9/10 also move given 8 and 12 turned out to.

## Known traps

All workstream-specific traps are in `reversing/impossamole/README.md`'s own "Known traps" section
— read it there, including two this pass added or corrected:
- a `bp`/`watch` check that finds nothing inside its own step budget is not proof a maneuver is safe
  past that budget, *and* a hit inside a wider budget is not proof it's the hazard you were aiming at
  — read `A0` at the stop, don't assume identity from which trial you were running;
- a fixed-length `kbd`/`mouse` hold shorter than the game's own poll cycle can silently never register
  at all, and the hero ending up where the maneuver would have left it is not proof the maneuver ran —
  watch a signal that only changes if the mechanism actually fired (here, the jump's own frame counter)
  before trusting a position/damage check that a no-op would also pass.

Both folded into `CLAUDE.md` too, since they're general methodological traps, not specific to this
game.

## Next session

The 95th pass retracted the 94th pass's headline claim: the "safe, zero-damage timing dodge past slot
12" never actually dodged anything for five of its nine delays, because the trigger packet's 15,000-step
hold was shorter than the game's own ~24,000-step poll cycle and simply never registered — confirmed by
a `watch` on the jump routine's frame counter (`$1a5c4`) showing zero activity for those five delays.
Fixing the hold to 30,000 steps makes the jump fire reliably, but even then slot 8 eventually catches
every landing at the crossbar rest spot (`y=112`) — so Item 3 (dodge the guard) is open again, not
closed, and `pass94_dodge_item_landed.snap` is not a valid resume point (it's identical to
`pass90_wall_192.snap`). The 96th pass then ruled out three escapes: holding right through the landing
doesn't walk the hero any further (the same ground-level wall blocks at the crossbar height too);
chaining a second jump only 50,000 steps after the first never fires (confirmed cause: `$227f3` was
still `2`/jump, not `0`/idle — `$00c742` requires idle to retrigger); and a correctly-timed second jump
(after waiting the full ~500,000 steps for idle) does fire but nets back to the exact same resting
spot, undamaged.

The 97th pass then found and disassembled *why*: `$00c450` and `$00bb3a`-`bb68` pull the hero's `x`
back down by up to `2`/frame whenever it exceeds `192`, every frame, completely independent of tile
collision — live-confirmed by watching `$1a574` catch a genuine, tile-check-passed jump push get
reverted a few thousand steps later, four times in a row. **This closes off "jump timing/shape past the
crossbar" as a line of attack entirely — no maneuver of that kind can ever work here.** Start next
session on the two real leads this opens: (a) a route to the item that doesn't require the hero's `x`
to exceed 192 on this screen at all (try climbing the left tree's ladder from a higher entry point,
since the 86th pass only tried it from ground level); (b) whether this screen is *meant* to scroll when
`$00c450` triggers and the corresponding background/tile shift is missing from this port (`$1883c` has
only one confirmed reader, `$00bb5c`) — worth a quick real-Hatari cross-check on this exact screen
before assuming either way. Slot 8's own drift rate (Open item 2) only matters once something can
actually get past `x=192`.
