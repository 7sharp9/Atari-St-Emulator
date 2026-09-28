# Impossamole: handoff

Updated 2026-09-28 by the session that ended at the 88th-pass commit (workstream commit).

## Resume point

- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image,
  `coldboot_census/` (from-cold-boot scripts and snapshots), and `gameplay_explore/` (movement/hazard
  trials, now including the 88th pass's `pass88_*` scripts/snapshots). See `scratchpad/ANCHORS.md` for
  the full indexed list. Real Hatari v2.6.1 at `~/Downloads/hatari-snapshot/Hatari.app`, source at
  `~/GitHub/hatari/`. TOS ROM at `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/gameplay_explore/pass86_left_settled.snap` (`x=74,y=152`, idle,
  trunk-blocked, `2/18` health) — **not** `pass87_jump_right_1M_settled.snap` any more; the 88th pass
  proved that landing spot (`x=152,y=144`) is a soft-lock (see "Proven so far"). The jump mechanism
  itself (`$c742`/`$cbbc`, `kbd ff`/`kbd 09` from `pass86_left_settled.snap`) is still proven and
  controllable; what's needed next is a jump that does **not** settle at exactly `x=152,y=144` —
  releasing "right" partway through the arc, or a shorter/longer hold, to land short of or past the
  fence-post structure's base instead of directly on it.
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
  input each frame) and indexes a signed-word vertical-velocity table at `$cd54` with a per-jump frame
  counter (`82(A0)`), adding the result straight into `4(A0)` — genuine vertical displacement, landing
  on a walkable ground sensor returns to idle (`$caba`) directly, and the table's `$7fff` sentinel
  forces a fall-state transition (`$cb2e`) if reached first. Live-confirmed from
  `pass86_left_settled.snap` (`x=74,y=152`, trunk-blocked): `kbd ff`/`kbd 09` (up+right) clears the
  trunk entirely, landing idle past it at `x=152,y=144` next to a fence-post/ladder structure with a
  visible green item.
- **That exact landing spot (`x=152,y=144`) is a soft-lock, not a lead (88th pass).** Right is
  wall-blocked (position and every forward sensor byte identical before and after 300,000 steps
  held). Up and up+right do **not** trigger a jump or a climb — despite `$00c49c`'s static reading
  (not-ladder unconditionally falls into `$c742`) predicting they should — the hero stays completely
  static (position, `$227f3`, every sensor byte unchanged) for the whole window tested, in both a
  fresh-edge up+right test and a plain up-only test. Root cause, pinned with a `hits` census: the
  hero's busy flag `$1a5d7` (`= $1a572+101`, the byte `$00c2fa`'s `tst.b 101(A0); bne $c486` tests)
  reads `$01` at load and never clears; `$00c2fa` (the per-frame hero dispatcher) takes the busy
  branch to `$00c486` — a bare `rts` — on every single main-loop iteration (4 hits/100,000 steps,
  matching `$00c2fa`'s own hit count exactly), so the entire chain downstream of it (`$00c308`/
  `$00c31e` joystick-byte caching, `$00c488`'s dispatch table, `$00c49c`/movement, `$00c742`/`$00cbbc`
  jump) shows **zero** hits the whole time. `$00caba` (the clean-landing state-0 transition) never
  writes offset `101(A0)` at all, ruling out the normal jump/landing state machine as what sets or
  should clear this flag. After roughly 500,000-600,000 steps stuck this way, the game force-reloads
  through the same fade/reload chain the hazard-death path uses (`$00b058`, return address
  `$0000b05e`, spin-waiting at `$0001c3d8` inside `cmpi.b #$2,$1a2e9.l`/`bne $1c3d0`) — reproduced
  identically twice, once holding `kbd 09` throughout and once with **no input at all**, both landing
  on the exact same PC; health (`$bb74`) stayed `18/18` the whole time in both trials, ruling out the
  ordinary hazard/health death path as the trigger. The main loop itself (disassembled this pass,
  `$00b1bc`-`$00b27e`) has at least two other `bcs $b058` exits (after calls to `$00df4a` and
  `$00eafa`) that were confirmed *not* firing during the stuck window, so the exact instruction that
  forces the eventual reload is still open.

## Open, in priority order

1. **Find a jump that lands somewhere other than exactly `x=152,y=144`.** From
   `pass86_left_settled.snap` (`x=74,y=152`, trunk-blocked), the jump (`kbd ff`/`kbd 09`) is proven
   and controllable — try releasing "right" partway through the arc, or a different hold length, to
   land short of or past the fence-post structure's base rather than directly on it, and check
   `$1a5d7` stays `$00` at the new landing spot before trusting it as a resume point.
2. **Find what sets `$1a5d7` (`$1a572+101`, the hero busy flag) and whether anything is meant to
   clear it.** Grep a whole-image `disassemble.py --all` listing for every writer of `101(A0)`, and
   separately for every writer that targets `$1a5d7` as a literal absolute address (the object base
   is not always addressed via `A0`). If a legitimate clear path exists but needs a precondition this
   landing spot never satisfies (e.g. contact with the green item, or a specific screen-edge trigger),
   that's the real "how to pass this screen" answer — the fence-post/ladder/green-item structure is a
   plausible in-game trap (stand near it too long, get captured), not just an emulator artifact, but
   that reading is not yet proven either way.
3. **Find the main loop's actual reload trigger for the stuck-busy-flag case.** The loop body at
   `$00b1bc`-`$00b27e` (disassembled this pass) has calls to `$00b4de`/`$00d140`/`$00c0d4`/
   `$0018f7e`/`$00198ea`/`$00bb22`/`$00b5f8`/`$00bafc`/`$00bada` not yet read — one of them likely
   carries a third `bcs $b058`-style exit, or there's a frame/elapsed-time counter checked separately,
   that's what actually forces the reload after ~500,000-600,000 stuck steps.
4. **Find the projectile-vs-enemy damage path**, or confirm there isn't one in this build — unchanged
   from the 83rd pass. A `callcap` on `$00d3cc` from a primed state, then a live `watch` on the
   projectile slot while stepping past a nearby enemy, would settle it either way.
5. Identify what tile categories `$1`/`$2`/`$3` mean precisely (raw ids only known to map to
   ladder-climbable at the up-check).
6. Confirm whether Amazon's Game Over (`$b058`/`$b2d8`/`$17fe8`) and Klondike's unattended-death
   transition (reported reaching `$1c3d8`) are the same code path — the 88th pass found Amazon can
   also reach `$1c3d8` via `$b058` independent of hazard/health, which is suggestive but not yet a
   direct proof they're triggered the same way in both games.
7. The Klondike cold-boot run past ~9M steps with no input goes black and PC moves to `$1c3d8` —
   still not confirmed or rendered; now worth revisiting given item 6's finding.
8. Whether Orient/Ice Land/Bermuda Triangle load correctly in this emulator, from a fresh cold boot.
9. Classify the main game binary via the LINK-frame-count heuristic (§0 of the reversing skill) —
   not yet done.

## Known traps

All workstream-specific traps found so far are written up in `reversing/impossamole/README.md`'s own
"Known traps" section — read it there rather than here, so there's one copy. This pass's
generalizable lesson (a state-transition predicted by static disassembly can silently never execute
if a per-object busy/gate flag never clears — confirm the actual per-frame dispatch chain with a
`hits` census before trusting what the handler code says it should do) is a sharper instance of the
87th pass's own lesson already in the `reverse-engineer-st-game` skill (entry vs. per-frame body); not
worth a second skill edit, but worth remembering when a static read of an input handler doesn't match
live behavior.

## Next session

Start with Open item 1: from `pass86_left_settled.snap` (`x=74,y=152`, trunk-blocked), try jump
variants that land away from `x=152,y=144` exactly (shorter hold, or releasing "right" mid-arc) and
check `$1a5d7` at the new landing spot before treating it as a resume point. Item 2 (find `101(A0)`'s
writer) is worth a parallel grep pass regardless of which landing spot works, since it may turn out
the fence-post structure is meant to be interacted with rather than avoided.
