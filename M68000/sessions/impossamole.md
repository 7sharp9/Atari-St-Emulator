# Impossamole: handoff

Updated 2026-09-28 by the session that ended at commit `785f400` (91st pass; skill fix at `232ec63`).

## Resume point

- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image,
  `coldboot_census/` (from-cold-boot scripts and snapshots), `gameplay_explore/` (movement/hazard
  trials, now including the 91st pass's `pass91_*` scripts/snapshots — no new arch dumps). See
  `scratchpad/ANCHORS.md` for the full indexed list. Real Hatari v2.6.1 at
  `~/Downloads/hatari-snapshot/Hatari.app`, source at `~/GitHub/hatari/`. TOS ROM at
  `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/gameplay_explore/pass90_wall_192.snap` (`x=192,y=144`, idle,
  `2/18` health) — still the best resume point: the furthest-right safe ground position past the
  trunk, standing directly under the item's crossbar, reached by a route that takes zero damage.
  `pass90_x96jump_land_130.snap` (`x=130,y=144`, `2/18`, also safe) is the earlier waypoint on the
  same route. `pass91_from130_end.snap` (`1/18`, mid-air at `(192,112)`, 900,000 steps into a jump
  from the `x=130` waypoint that took the item-guard's hit) is a second, damaged waypoint — not yet
  confirmed landed/idle, don't treat it as settled.
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
- The `$25000` tile-classification table, the HUD routine (`$00fdc4`), and the weapon/projectile
  system (`$00d37c`/`$00d3cc`, slots 16-19) are all unchanged from prior passes — see the README.

## Open, in priority order

1. **Find a route to the item that survives or avoids slot 12's hazard.** Its radius is tight
   (`4/4/4`) and it sits close to the item, and taking off further back (the slot-9 playbook)
   doesn't dodge it. Untried: a shorter/lower jump that doesn't climb as far into the `y=104-115`
   band before reaching the item's own `x`; approaching from the *right* side of the hazard
   (already past it) rather than jumping up through it; or just taking the one hit (`2/18`→`1/18`)
   and confirming what's on the other side — `pass91_from130_end.snap` shows the arc continuing
   past the hazard rather than dying there, but isn't yet confirmed landed/idle or what the hero
   can reach from there. Check health throughout any new attempt, not just the destination.
2. **Confirm what slot 12 actually is.** Not yet checked whether the visible purple creature next
   to the second fence post is really this slot (position match, not just screen-area guess — see
   "Known traps"), or whether its drifting position rules that out in favour of something else on
   the crossbar (e.g. the item's own idle-sway animation, if the item and the hazard turn out to
   be related).
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
and "roughly the right screen area is not proof" traps are exactly what this pass leaned on and
still hasn't fully closed (item 2 above). The one generalizable lesson this pass produced — pin a
detect-then-apply hit at the *detect* site, not the *apply* site, since `A0` differs between them —
went into `.claude/skills/reverse-engineer-st-game/SKILL.md` directly (commit `232ec63`), not here.

## Next session

Start with Open item 1: from `pass90_wall_192.snap` (or the `x=130` waypoint), try a shorter/lower
jump or an approach from the hazard's far side before accepting the one hit as the cost of reaching
the item. `pass91_from130_end.snap` is unexplored past the hit — worth a quick look at what's there
before designing a fresh attempt.
