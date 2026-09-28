# Impossamole: handoff

Updated 2026-09-28 by the session that ended at commit (this pass's own commit, 90th pass;
workstream commit follows `5607940`).

## Resume point

- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image,
  `coldboot_census/` (from-cold-boot scripts and snapshots), `gameplay_explore/` (movement/hazard
  trials, now including the 90th pass's `pass90_*` snapshots/screenshots — no new arch dumps). See
  `scratchpad/ANCHORS.md` for the full indexed list. Real Hatari v2.6.1 at
  `~/Downloads/hatari-snapshot/Hatari.app`, source at `~/GitHub/hatari/`. TOS ROM at
  `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/gameplay_explore/pass90_wall_192.snap` (`x=192,y=144`, idle,
  `2/18` health) — the furthest-right safe ground position past the trunk, reached by a route that
  takes **zero** damage the whole way (superseding `pass86_left_settled.snap` as the resume point;
  that one is still valid too, just further back). Standing directly under the twin-fence-post
  item's crossbar. **Do not jump straight up from here without care**: `kbd ff`/`kbd 09` (up+right)
  takes a hit around 150,000-200,000 steps in — something in the crossbar's own height band deals
  contact damage, not yet pinned to an object slot (see Open item 2).
  `pass90_x96jump_land_130.snap` (`x=130,y=144`, `2/18`, also safe) is the earlier waypoint on the
  same route, useful if a different angle of approach to the item is wanted.
  **Must be run with `--disk-a "scratchpad/impossamole/impossamole cr replicants - emotion cr
  replicants.st"`** (path relative to `M68000/`) on every `resume ... repl`. The REPL's `snap
  <path>` command writes relative to the `dotnet` process's own working directory (`M68000/` if
  invoked from there) — give it the full path into `scratchpad/impossamole/gameplay_explore/`.
- Uncommitted work left behind: none from this pass. `pass90_x96jump_end.snap` (an intermediate,
  overshot/dead-hero snapshot from finding the safe route — the jump run past its idle-landing
  window into the same crossbar-height hazard) is left in `gameplay_explore/` but is **not** a
  resume point; don't reuse it. The pre-existing `M68000/sessions/README.md` whitespace-rewrap
  diff (predates this workstream, flagged unowned by several prior handoffs) is still there and
  still not this workstream's to fix. `.obsidian/` and `Cadaver/` at the repo root are also not
  this workstream's.

## Proven so far

See `reversing/impossamole/README.md`'s "Program classification", "Gameplay input" and "Past the
first screen" sections for full detail, match counts and exact addresses:

- **The program is hand-written 68000 assembly, not compiled C.** No decompile route — live
  `watch`/`bpc`/`callcap` plus `disassemble.py --all` is the only path.
- **The hazard/collision mechanism is proven end to end**: `$00b71a` (proximity) → `$00e80e`
  (copies the contacting object's `+104` damage into `$227f6`) → `$00eafa`'s fall-through
  (`$00eb8c`, applies it to health `$bb74`, arms a 7-frame hit-cooldown) → `$00ec50` (death
  handling) → `$b058`/`$b2d8`/`$17fe8` (reload into a real, rendered Game Over screen).
- **The hero's busy flag `$1a5d7` is the death-animation lock**, entered only once health hits
  zero *and* the hero is grounded — a fatal hit taken mid-air doesn't visibly lock the hero until
  it lands.
- **A real, table-driven jump mechanism exists**: `$00c742` is one-shot entry (facing latch,
  horizontal push magnitude committed at takeoff from `98(A0)` — unaffected by releasing/changing
  direction mid-air), falling through into `$00cbbc`, the real per-frame handler (a `$cd54`
  velocity table driving genuine `4(A0)` vertical displacement). The table returns the hero to an
  idle frame on landing before `$c742` retriggers a new jump if up is still held — **releasing up
  during that idle frame stops the retrigger and settles the hero there for good (90th pass)**.
- **Item 1 closed (90th pass): a route past the trunk that takes zero damage.** From
  `pass86_left_settled.snap` (`x=74,y=152`), plain held-right walks the hero to `x=96,y=152` and
  stops on its own — a stretch no prior pass ever walked, since every prior pass jumped straight
  from `x=74`. Jumping up+right from `x=96` instead of `x=74` reproduces the same arc 22px closer
  to the far side, clearing slot 9's `(x=66,y=98)`/16px hazard by a comfortable margin (`watch
  bb74`: zero writes). Releasing up at the arc's own idle-landing frame (relative step ~430,000)
  settles the hero at `x=130,y=144`, `2/18` health, undamaged — visibly past the trunk, at the
  base of two fence-post/crossbar structures with a green item on the first crossbar and a purple
  creature near the second post. From there, plain held-right at ground level is safe all the way
  to `x=192` (the same wall previous passes found from the dodge-landing route, now reached
  hazard-free).
- **The item is guarded, but by what is not yet proven (90th pass, opens item 2's next step).** A
  `kbd ff`/`kbd 09` jump straight up from `x=192` takes a hit (`$bb74` `2`→`1`) around 150,000-
  200,000 steps in, `y` climbing through the crossbar's own height band (`$68`-`$6c`). A `bpc e82e
  1 400000` (the 89th pass's own method for pinning a contact's `A0`) got **zero** hits in that
  window despite the health write happening — either the timing window was wrong, or this hazard's
  contact doesn't route through the same `$e82e` instruction the slot-9 one did. Not yet re-tried
  with a wider `maxSteps` or a `watch bb74` + immediate `bt`/register dump at the hit instead.
- The `$25000` tile-classification table, the HUD routine (`$00fdc4`), and the weapon/projectile
  system (`$00d37c`/`$00d3cc`, slots 16-19) are all unchanged from prior passes — see the README.

## Open, in priority order

1. **Identify the object guarding the item near `x=192-196`, height band `y=$68`-`$6c`.** From
   `pass90_wall_192.snap`, re-run the up+right jump with `bpc e82e 1` given more `maxSteps` (try
   600,000-800,000, since the hit landed around step 150,000-200,000 relative to jump start but the
   400,000 cap this pass used somehow still missed it — check whether `e82e` is even the right
   instruction for this hazard before assuming the census was just too short), or simpler: `watch
   bb74` to get the exact absolute hit step, then re-run to one step before it and `bt`/`r` to read
   `A0` directly at the `$00eb8c` write site. Once pinned, check if the purple creature visible in
   `pass90_wall_192.png` is really the culprit (position match, not just screen-area guess — see
   the "Known traps" reminder).
2. **Find a route to the item that avoids or survives that hazard.** Once it's pinned, the 90th
   pass's playbook (walk to a takeoff point 15-25px further from the hazard's center than the
   naive approach, jump, release the trigger direction at the arc's own idle-landing frame) is the
   template to try again — don't assume a straight jump from directly underneath is the only path.
3. **Find the projectile-vs-enemy damage path**, or confirm there isn't one in this build —
   unchanged from the 83rd pass. A `callcap` on `$00d3cc` from a primed state, then a live `watch`
   on the projectile slot while stepping past a nearby enemy, would settle it either way.
4. Identify what tile categories `$1`/`$2`/`$3` mean precisely (raw ids only known to map to
   ladder-climbable at the up-check).
5. Whether Orient/Ice Land/Bermuda Triangle load correctly in this emulator, from a fresh cold
   boot.
6. Classify the twin-tree screen's full hazard cluster (slots 8/9/10 known, now also the
   unidentified crossbar guard) — check for further slots nearby before assuming complete.

## Known traps

All workstream-specific traps are in `reversing/impossamole/README.md`'s own "Known traps" section
— read it there. Nothing new to fold in this pass; the existing "check health, not just position"
trap is exactly what this pass's method leaned on (`watch bb74` across the whole maneuver, not just
at the destination).

## Next session

Start with Open item 1: from `pass90_wall_192.snap`, pin the crossbar-height hazard's object slot
(wider `bpc e82e` cap, or a `watch bb74` + `bt`/`r` at the exact hit step) before trying any new
route to the item — don't guess the culprit from screen position alone.
