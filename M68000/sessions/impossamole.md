# Impossamole: handoff

Updated 2026-09-26 by the session that ended at commit `dac1c49`.

## Resume point

- Last commit of this workstream: `dac1c49` (movement mapping proven; a first, unverified visual
  claim about the hero sprite was retracted after Dave questioned it — see "Proven so far"; the
  underlying lesson generalized into the reverse-engineer-st-game skill).
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image plus the
  full snapshot chain. New this session: `test_dirbit3_A.snap`/`test_dirbit3_B.snap` (bit 3/right
  held 200k then 2M steps from `after_amazon_load2.snap`), `test_dirbit2_left.snap` (bit 2/left,
  2M steps). The `test_*.snap` files timestamped before `after_confirm_screen.snap` are leftover
  exploration from the *prior* session (input probing before the Klondike-Mine loop-back was found);
  harmless, not cleaned up, safe to ignore or delete.
- Start from: `scratchpad/impossamole/after_amazon_load2.snap` to continue exploring the Amazon
  level, or `test_dirbit3_B.snap` (hero mid-walk-cycle, position `$1a574 = $00c0`) to continue from
  after a confirmed move. **Must be resumed with `--disk-a "impossamole cr replicants - emotion cr
  replicants.st"`** (see README's "Known traps") — path relative to `M68000/`.
- Uncommitted work left behind: `M68000/sessions/README.md` still has the pre-existing whitespace-
  only rewrap edit noted by the last two handoffs (predates this workstream, no live session claims
  it — `ListAgents` showed only an unrelated "GPU training optimization research" session, idle).
  Also `.obsidian/` and `Cadaver/`, untracked at the repo root, not this workstream's.

## Proven so far

See `reversing/impossamole/README.md` for the full writeup and screenshots.

- Disk boot → crack menu → trainer skip → title screen → joystick-1 fire → world-select screen →
  held-fire confirm on a settled, unlocked icon → Klondike Mine loops back to world-select (broken
  data) → The Amazon loads for real and reaches a first gameplay frame: unchanged from the previous
  handoff, still holds.
- **Gameplay uses the exact same joystick-1 bit layout as the world-select screen** (bit 7 = fire,
  bits 0-3 = up/down/left/right), read from `$1c4c1` by the per-frame dispatcher `$c2fa`, which the
  `$b1b6` template calls every frame. The prior handoff's "a single right packet produced no visible
  change" was a false negative: `$c2fa` skips reading `$1c4c1` entirely on any frame where the hero
  object's busy flag (`$1a572+101` = `$1a5d7`) is set, and the observable effect (a walk cycle) takes
  several frames to complete, so a one-packet/one-frame test can miss it even when the mapping is
  right. **Proven live**: from `after_amazon_load2.snap` (busy flag clear, state `$227f3=$00`,
  position `$1a574=$0080`), `kbd ff`/`kbd 08` (bit 3, right) + 2,000,000 steps drives `$227f3`
  `$00→$01→$00` (a completed walk cycle) and `$1a574` `$0080→$00c0` (+64, 4 discrete 16px steps);
  `kbd ff`/`kbd 04` (bit 2, left) over the same window drives `$1a574` `$0080→$0076` (-10). A
  same-length **no-input control** leaves both fields unchanged, isolating input as the cause.
  `snap_render.py` on the bit-3 run against that control (`amazon_walk_right.png` vs
  `amazon_noinput_2M.png`), not against the original 0-step frame, shows most of the terrain
  redrawn and a pillar that was off-screen right now well inside view on the left — a real,
  isolated scene scroll. **Not settled**: which sprite is the hero. A small humanoid figure visible
  in both frames shifts by roughly the same amount and direction as the pillar, i.e. it moves *with*
  the background rather than staying camera-locked — so `2(A0)`/`$1a574` reads more like a
  world/camera-scroll value than a hero sprite's own screen X, and the actual hero sprite (if
  rendered separately) hasn't been found. (First pass at this called it "the hero sprite in a
  different pose" and "camera-relative movement" without isolating the no-input case or checking
  which sprite actually corresponds to this field — Dave caught it: the sprites zoomed into for that
  claim were background/enemy art, not a verified hero. Corrected in the same session before
  handoff.) Up/down (ladder climb, `$c488`'s bit-0/bit-1 handlers → `$227f3:=4`) and the jump/attack
  state (bit 0 when no ladder sensed → `$227f3:=2`, via `$c742`) are read statically only, not yet
  live-tested. Full detail: README's "Gameplay input" section.
- **Lesson applied to CLAUDE.md**: a per-object busy flag can gate a whole frame's input read, and
  an input's effect can take several frames to become visible — check both before concluding an
  input is unmapped from a single-packet test (CLAUDE.md's `kbd`/`mouse` raw-level bullet, extended;
  commit `06c5938`).

## Open, in priority order

1. **Identify the actual hero sprite, and whether `2(A0)`/`$1a574` is camera-scroll or hero
   world-position.** The visible humanoid figure in `amazon_walk_right.png` moves with the
   background rather than staying screen-fixed, so it's probably not a camera-locked player sprite.
   `find_ram_callers.py`/a targeted `bp` on the object-render loop (`$1ac34`'s 20-slot, 108-byte-
   stride array starting `$1a2ea`) for whichever slot actually draws a humanoid blit, cross-checked
   against which slot's fields correlate with `$1c4c1` input, would settle it. This blocks trusting
   any future "the hero does X" visual claim.
2. **Live-test ladder climbing and the jump/attack state.** `$c488`'s bit-0 handler checks a
   ladder-above sensor (`$227ea`, classified via `$be96`) and either climbs (`$227f3:=4`, `$c812`)
   or falls into a jump/attack branch (`$c742`); bit-1 is the ladder-below mirror (`$227eb`). Find a
   snapshot near an actual ladder tile (or force the sensor byte and step) to prove the climb state
   and see what the jump/attack branch actually does — both are read statically only so far.
3. **Map what `$be96` classifies.** The three-sensor "walkable" test that gates left/right movement
   (`$227e0-2`/`$227e4-6`, compared against thresholds 2/4/5/6/7 throughout `$c2fa`'s callees) reads
   through `$be96`; it's almost certainly a tile-type lookup. Finding its table would unlock reading
   collision/ladder/hazard tiles directly from the level data instead of inferring them from sensor
   behaviour.
4. Explore the Amazon level with movement now working: walk further than one screen, map what tile/
   sprite formats the visible terrain and (once identified) hero sprite use (`gfxview.py --contact`/
   `--html` on `test_dirbit3_B.snap` or a fresh longer walk), and check what stops movement (the
   `$1c`/`$104` position-word bounds in `$c2fa` suggest a screen-relative clamp, not a world edge).
5. Why Klondike Mine specifically fails (zero disk reads where Amazon has 30+): check whether its
   `.DAT` pair (`MINES22.DAT`/`MINES33.DAT`) is truncated/corrupt in this crack, or whether the
   engine silently swallows a disk-read error for it; also worth confirming Orient/Ice Land/Bermuda
   Triangle load correctly (Amazon alone doesn't prove all four).
6. Classify the main game binary via the LINK-frame-count heuristic (§0 of the reversing skill) —
   not yet done; would confirm hand-written-asm vs compiled-C and whether the decompile route (§3b)
   is worth taking for the remaining engine code.

## Known traps

- `resume <snap> repl` does not reattach a disk image — `--disk-a` must be passed again on every
  resume for a disk-booted game, or floppy reads silently fail (see README's "Known traps").
- A busy-poll "wait for next interrupt and consume it" utility reads as stuck if you only sample the
  field it polls at rest. Also in the README.
- A `kbd`/`mouse` status byte is a raw level in RAM, not an edge-latched event, and a per-object busy
  flag can suppress a whole frame's input read on top of that — both now in CLAUDE.md and the
  README's "Known traps"/"Gameplay input" sections; no longer workstream-only.
- Diffing a held-input frame against the *pre-input* frame (rather than a same-length *no-input
  control*) reads ordinary per-frame animation as input-driven movement and doesn't identify which
  sprite actually moved — generalized into the reverse-engineer-st-game skill's cracktro A/B lesson;
  no longer workstream-only.

## Next session

Start at `scratchpad/impossamole/after_amazon_load2.snap` (`--disk-a` attached). Pick open item 1
first (identify the hero sprite vs camera-scroll) — it's cheap relative to its payoff, since every
later visual claim about the hero depends on knowing which object it actually is. Items 2 (ladder/
jump-attack) and 3 (`$be96`'s tile classification) are independent and can follow in either order.
Screenshot before and after any input change **against a same-length no-input control, not the
original 0-step frame** — this session's own first pass at the movement proof got that wrong and had
to be corrected before handoff — and hold packets a full VBL frame past any busy flag as CLAUDE.md
now documents.
