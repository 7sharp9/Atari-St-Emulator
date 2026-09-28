# Impossamole: handoff

Updated 2026-09-28 by the session that ended at commit `14c2c27` (97th pass).

## Resume point

- Last commit of this workstream: `739ccfb` impossamole: 97th pass -- disassemble the x=192 wall,
  it's not tile collision.
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image,
  `coldboot_census/` (from-cold-boot scripts and snapshots), `gameplay_explore/` (movement/hazard
  trials). See `scratchpad/ANCHORS.md` for the full indexed list. Real Hatari v2.6.1 at
  `~/Downloads/hatari-snapshot/Hatari.app`, source at `~/GitHub/hatari/`. TOS ROM at
  `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/gameplay_explore/pass90_wall_192.snap` (`x=192,y=144`, idle,
  `2/18` health, standing at the wall right under the crossbar). **`pass94_dodge_item_landed.snap` is
  not a resume point** — it is state-for-state identical to `pass90_wall_192.snap` (the 94th pass's
  own trigger never fired, see "Proven so far"). `pass95_realdodge_300k_30khold.snap` and
  `pass96_doublejump*.snap` are confirmed dead-end reference pins, not resume points.
  **Must be run with `--disk-a "scratchpad/impossamole/impossamole cr replicants - emotion cr
  replicants.st"`** (path relative to `M68000/`) on every `resume ... repl`. The REPL's `snap <path>`
  command writes relative to the `dotnet` process's own working directory (`M68000/` if invoked from
  there) — give it the full path into `scratchpad/impossamole/gameplay_explore/`.
- Uncommitted work left behind: none from this session. The pre-existing `M68000/sessions/README.md`
  whitespace-rewrap diff (predates this workstream, flagged unowned by several prior handoffs) is
  still there and still not this workstream's to fix. `.obsidian/` and `Cadaver/` at the repo root
  are also not this workstream's.

## Proven so far

See `reversing/impossamole/README.md`'s "Program classification", "Gameplay input" and "Past the
first screen" sections for full detail, match counts and exact addresses:

- **The program is hand-written 68000 assembly, not compiled C.** No decompile route — live
  `watch`/`bpc`/`callcap` plus `disassemble.py --all` is the only path.
- **The hazard/collision mechanism is proven end to end** (`$00b71a` proximity → `$00e80e` scan →
  `$00e82e` damage copy → `$00eb8c` apply → `$00ec50` death → `$b058` reload) and **the object array's
  stride and base are proven** (108 bytes/entry, base `$1a2ea`, hero index 6 at `$1a572`).
- **A real, table-driven jump mechanism exists**: `$00c742` one-shot entry falling through into
  `$00cbbc`, the per-frame handler (a `$cd54` velocity table, terminal sentinel `$7fff`). The arc's
  vertical shape is fixed once triggered.
- **Item 1 (route past the trunk): closed (90th pass)** — walk to `x=96`, jump up+right, clears
  slot 9, lands at `x=130,y=144`, then plain held-right reaches `x=192` clean.
- **Item 2 (what guards the crossbar item): closed (93rd pass).** Slot 12 (`$1a7fa`) is a small
  flying creature (not the static saw-wheel/prop it visually overlapped), proven by tracked drift
  (`~-0.126px/step` x, confirmed via `watch`) across two idle snapshots.
- **Item 3 (dodge the guard's hazard): retracted, then root-caused — closed as *impossible* by this
  route, not solved.** The 94th pass's "safe, zero-damage timing dodge" (five idle delays that left
  the hero undamaged at its takeoff spot) never actually dodged anything: a `watch` on the jump's own
  frame counter (`$1a5c4`) showed **zero** writes for those five delays vs 17 for every delay that
  genuinely fires — the trigger packet's 15,000-step hold was shorter than the game's own ~24,000-step
  poll cycle and simply never registered (95th pass). Holding 30,000 steps makes the jump fire
  reliably, but slot 8 (`$1a64a`, a previously-unconfirmed hazard, now closed as real and live) still
  eventually catches every landing at the crossbar rest spot `y=112`. The 96th pass ruled out three
  escapes (hold right through landing, retrigger a second jump too soon, retrigger it correctly-timed)
  — all three fail identically. **The 97th pass found why, by disassembly**: `$00c450` checks every
  frame whether the hero's `x` exceeds `192`; if so, `$00bb3a`-`bb68` subtracts the excess (capped at
  `2`/frame) from every object-array slot flagged `30(A0)=$00ff` (hero and every hazard checked all
  carry that flag) — a hardcoded per-frame position correction, live-confirmed to revert even a
  genuine, tile-check-passing `+2` push, independent of tile collision entirely. **No jump or walk
  shape can ever cross `x=192` on this screen.** Reaching the item needs a different approach
  entirely, not more input variations — see Open item 1.
- **The pickup snapshot never collected the item (95th pass)** — a whole-frame pixel diff against the
  pre-jump frame matched `63,454`/`64,000` pixels, item region byte-identical — but this is now
  understood as trivial: no jump ran for that snapshot's delay, so nothing could have reached the item
  regardless.
- The `$25000` tile-classification table, the HUD routine (`$00fdc4`), and the weapon/projectile
  system (`$00d37c`/`$00d3cc`, slots 16-19) are all unchanged from prior passes — see the README.

## Open, in priority order

1. **Find the real route to the item.** Rightward jumping/walking past `x=192` on this screen is
   closed as impossible (97th pass, see above) — do not re-attempt input-timing variations on that
   approach. Two real leads: (a) a route that never needs the hero's `x` to exceed 192 here at all —
   the left tree's ladder was a dead end from ground level (86th pass) but was never tried after
   climbing from a higher entry point; (b) check whether this screen is *meant* to scroll when the
   `$00c450` trigger fires and the corresponding background/tile shift is missing from this port
   (`$1883c`, the shared correction delta, has exactly one confirmed reader, `$00bb5c`) — a real-Hatari
   cross-check on this exact screen would settle whether this is a level-design dead end or an
   emulator gap.
2. **Characterize slot 8's own drift/patrol rate**, the way slot 12's was pinned in the 93rd pass —
   only matters once something can actually get past `x=192`.
3. **Find the projectile-vs-enemy damage path**, or confirm there isn't one in this build —
   unchanged from the 83rd pass. A `callcap` on `$00d3cc` from a primed state, then a live `watch`
   on the projectile slot while stepping past a nearby enemy, would settle it either way.
4. Identify what tile categories `$1`/`$2`/`$3` mean precisely (raw ids only known to map to
   ladder-climbable at the up-check).
5. Whether Orient/Ice Land/Bermuda Triangle load correctly in this emulator, from a fresh cold boot.
6. Classify the twin-tree screen's full hazard cluster (slots 8/9/10/12 known, 8 and 12 confirmed to
   move) — check for further slots nearby, and whether 9/10 also move.

## Known traps

All workstream-specific traps are in `reversing/impossamole/README.md`'s own "Known traps" section —
read it there. Two general-methodology lessons from this session are folded into `CLAUDE.md` (a fixed
input hold shorter than the target's poll cycle can silently no-op) and the `reverse-engineer-st-game`
skill (when several live trials fail the same way, disassemble the shared boundary instead of trying
more inputs) — not repeated here since they're no longer workstream-local.

## Next session

Start with Open item 1: `x=192` is a proven, unconditional per-frame position correction (`$00c450`/
`$00bb3a`-`bb68`), not a tile wall — no further jump-timing or arc-shape experiment on this approach
will succeed, so don't re-run that class of trial. Try the left tree's ladder from a higher jump-in
point (never attempted after climbing, only from ground level in the 86th pass), or spend a real-Hatari
cross-check confirming whether this screen is supposed to scroll at the `x=192` trigger and this
emulator is missing the matching background/tile shift.
