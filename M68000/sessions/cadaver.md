# Cadaver: handoff

Updated 2026-09-26 by the session that ended at commit `e6e9ad3` (69th pass, following the 68th's
`854cd34`), which closed both of the previous handoff's open items: rendering `room_mosaic.py`'s
one dropped `0xc2` item-catalog overlay, and cross-checking type 2's catalog against §3's 22-entry
object array field-for-field. Full writeup: `reversing/cadaver/graphics.md` §5f/§5a-2.

## Resume point

- Last commit of this workstream: `e6e9ad3` "cadaver: cross-check type-2's catalog against section 3's
  object array field-for-field (69th pass)". `1e7745e` "cadaver: render room_mosaic.py's dropped 0xc2
  item-catalog overlay (69th pass)" is this same session's other commit. No emulator source changed
  this pass (Python tooling + doc edits only, reusing existing snapshots), so no rebuild or
  regression-net run is needed before building on it.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored) — unchanged this pass, nothing
  newly captured; `gameplay_empire.snap`, `mid_cab6_cavern.snap`, `mid_cab6_tunnel.snap`,
  `room2_tunnel_entry.snap` (all pre-existing) were re-read, not re-captured.
- Start from: `gameplay_empire.snap` (CAVERN) / `room2_tunnel_entry.snap` (TUNNEL) for ordinary
  static/gameplay work; `mid_cab6_cavern.snap` / `mid_cab6_tunnel.snap` specifically for re-reading
  either room's live tile-placement/draw-descriptor list (a scratch buffer, unreadable from a
  steady-state snapshot).
- Uncommitted work left behind: none of this session's own. `M68000/sessions/README.md` still carries
  the pre-existing line-wrap-only edit noted in the last several handoffs (not this session's, left
  alone per "one writer per file" — check `git status` fresh rather than trusting this line if it's
  been a while). `Cadaver/` (game disk images) and `.obsidian/` (an Obsidian vault config) are
  untracked, predate this session, and aren't part of any workstream — left alone.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` §1-63 (movement collision/proximity, the icon-panel write chain, the full 72-room
world-map/adjacency graph, the door-connectivity walk, the swapped-disk side-count bug, the
Replicants/ST Amigos crack's Disk 2 swap, two genuine emulator gaps behind the "crack dispatch bug",
the FDC "no data" workflow fix, the two-disk build's `$100`-shift bugs, a real CAVERN→TUNNEL crossing
driven live, Disk 2's one-time boot-time load with zero further FDC activity, CAVERN/TUNNEL having no
live-reachable third room), `graphics.md` §5a-5j (the shared 80-tile terrain catalog, its per-room
RLE-compressed per-column tile-stack encoding, the `$cbd4` top-bit marker channel fully resolved
including its `0xc2` sub-case, no runtime tile-adjacency rules, the per-cell screen-placement formula,
the full draw pipeline, both known rooms scored ~96% pixel-exact against their reference screenshots)
and the 68th pass's closed palette-formula item (neither reference screenshot is an authentic Hatari
render, so `--palette-formula {ste,st}` per-reference selection is the permanent answer).

**This pass (`graphics.md` §5f/§5a-2)**:
- `room_mosaic.py` now renders the terrain grid's one non-tile (`0xc2`-sourced) descriptor entry
  instead of silently dropping it: its `ptr` field is already the item's own address past its
  0x24-byte header, and its `w_field`/`h_field` give the real size directly, so it composites
  through the exact same clip/mask/paste pipeline as a tile. TUNNEL's mosaic score is now
  **10604/11069 (95.8%)** against `room2_tunnel_entry.png` (up from 9534/9932 tile-only; the
  percentage dip is newly-covered area occluded by the player sprite in the reference frame, not a
  regression). CAVERN's capture has zero non-tile entries, so its score (19079/19749, 96.6%) is
  unchanged. Script: `reversing/cadaver/py/room_mosaic.py`.
- Cross-checked type 2's 255-slot catalog against §3's 22-entry per-room object array, field for
  field: all 20 state-5 (static room-dressing) slots' `+52` bitmap pointers land at the exact byte
  address of a type-2 catalog payload, matching width/height too; three spot-checks (torch, boat,
  chest) decode pixel-identical on both sides, **0 different pixels each**. Type 2 is confirmed the
  literal shared template catalog for per-room static dressing, not just a conceptually similar
  pool. The one exception, slot 16 (the goblet, the array's own previously-flagged `+42` state-4
  outlier), decodes to real art via its own struct fields but its address falls inside type 2's
  data span without landing on any of the 255 enumerated entries — genuine art from elsewhere,
  giving the state-4 anomaly a concrete structural correlate for the first time. Script:
  `reversing/cadaver/py/cross_check_type2_objects.py`.

## Open, in priority order

1. **The goblet's (§3 slot 16, state 4) actual art source** — narrowed this pass (§5a-2 ruled out
   type 2's 255-slot table specifically) but not identified; low priority, a one-off curiosity. If
   pursued: check the other resource-manager types (0,1,3-7) the same way `cross_check_type2_objects
   .py` checks type 2, or `watch (A5)+52` on that slot across a state transition if one is ever
   observed.
2. **Stack direction** (does per-column tile-stack index 0 sit at the floor or the ceiling, §5e) —
   still not proven either way; the room-terrain rendering work being fully proven now (both rooms
   ~96%, including the item overlay) hasn't settled this.
3. **The CAVERN mosaic's own ~3.4% overlap-edge residual** (§5i-2, confirmed unrelated to the
   palette-formula question, since its reference already matches `room_mosaic.py`'s default
   formula) — small, visually negligible, cause not identified.
4. **Does Disk 2 add reachable content beyond CAVERN/TUNNEL?** (64th pass, `mechanics.md` §63): still
   recommended closed for practical purposes; unaffected by this pass.
5. `2516(A5)`'s role still unconfirmed. Only worth resolving if another item needs a real day/progress
   counter.
6. `disk_layout.py`'s blank/data classifier only catches single-byte fills, not short-period repeats.
   No `.stx`→`.st` converter exists in `tools/`.

## Known traps

(Carried over from earlier passes — see git history for the full set: `ScreenBufferA/B` role-swap
framing is wrong, `movem` block-copy chunk reversal, `watch`'s step= counter is a lifetime counter not
local, one-shot breakpoint chase non-reproducibility, re-disassemble elided `...` excerpts in full,
`bpc` over `bp` for one-shot dumps, `bt depth>1` can crash the REPL, a `watch` range can bracket
multiple regions in one call, `gfxview.py`'s `st-interleaved` assumes 16px-wide masked blits, movement
is joystick port 1, player = sprite slot 0, use
`tools/find_ram_callers.py`/`find_field_writers.py`/`find_literal_ptr.py`/`find_jump_table_hit.py`,
the `moveq #0,Dn`-then-`move.b` zero-extend/condition-code trap, a byte's top bits gating a whole
different code path, a whole-image `disassemble.py --all` dump + call-site census to rule out a dead
type/case, a struct field documented as "an array at `(A5)+N`" may actually be a pointer to it, mask
overlapping tile/sprite art rather than pasting it opaquely, a scratch/display-list buffer generally
can't be read from a steady-state snapshot, a `bpc <addr> 1 <budget>` armed per zigzag leg catches a
one-shot room-entry routine without knowing in advance which leg crosses the door, a clustered (not
uniform) pixel-diff mismatch points at missing content over a placement bug.)

- **Two lookalike routines sitting next to each other in the image can be genuinely different
  primitives, not the same routine reached two ways** — `$00c576` and `$00c5a8` (§5a) are adjacent,
  share the same outer `(A5)+96 → row[type]` addressing shape, and differ only in their first
  instruction (`moveq #2,D0` vs none) and their slot-decode tail; a caller census that only grepped
  for one of them (the 24th pass's `$c5a8` census) silently missed the other's 28 call sites and
  wrongly concluded a whole resource type was dead. When a `(type,index)`-style fetch has one known
  entry point, check the disassembly immediately around it for a second one before trusting a "no
  caller sets D0=N" census as exhaustive.
- **A low, spatially-uneven pixel-diff score against an independently-generated reference screenshot
  can be a cross-tool palette-rounding mismatch, not missing render content** — now in
  `.claude/skills/reverse-engineer-st-game/SKILL.md` §4b in detail (the diagnostic: sample a few RGB
  pixels at the same coordinate in both images; a consistent small integer offset, e.g. 182 vs 180,
  is a formula bug, not a wrong tile). Cost the 66th pass a wrong conclusion and the 67th pass a
  detour through a real-but-irrelevant mechanism (`0xc2`) before finding the actual cause.
- **Tracing only "the first half" of a routine that both reads and writes through a shared pointer
  can misattribute a callee's own internal bookkeeping fields to the caller's real output struct** —
  the earlier `0xc2` reading (`52(A5)`/`2209(A5)` "look like" object-array fields) came from not
  following the call into `$92e8`/`$c576` far enough to see they're scratch cells the *caller* reads
  back out afterward, not the actual draw-descriptor write. Trace a callee fully before trusting a
  struct-shape resemblance.
- **Before spending a pass chasing an external "authoritative" formula to resolve an internal tooling
  mismatch, confirm your own reference assets actually came from that authority** — now in
  `.claude/skills/reverse-engineer-st-game/SKILL.md` §4b (the diagnostic: re-score a known reference
  against the real formula; a clean 0/N exact match rules it out as the source instantly, no
  rounding-level ambiguity). Cost nothing this pass only because it was checked before touching
  either tool's default — the previous handoff had explicitly flagged the risk of picking a side
  without checking.

## Next session

Both of the previous handoff's open items are closed, and both known-good mosaics now render every
descriptor-list entry (tiles and item overlays alike). The remaining open items are all small and
independent (goblet's art source, stack direction, CAVERN's residual 3.4%) — pick whichever interests
Dave, or step back to a broader thread (item 4's Disk 2 question, or a fresh subsystem) if he'd rather
redirect. Prompt: `/resume cadaver`.
