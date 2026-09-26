# Cadaver: handoff

Updated 2026-09-26 by the session that ended at commit `854cd34` (68th pass, following the 67th's
`76a4abf`), which closed the previous handoff's top open item — unify the two disagreeing
palette-to-RGB formulas — by finding that item couldn't be done as framed. Full writeup:
`reversing/cadaver/graphics.md` §5i-3 addendum.

## Resume point

- Last commit of this workstream: `854cd34` "cadaver: retire the palette-formula 'unify' open item
  -- neither reference screenshot is an authentic Hatari render (68th pass)". `9230514`
  "reverse-engineer-st-game skill: a lesson from cadaver's 68th pass..." is a shared-resource
  commit from the same session, its own small commit per the sessions/README.md rule. No emulator
  source changed this pass (Python tooling + doc edits only, reusing existing snapshots), so no
  rebuild or regression-net run is needed before building on it.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored) — unchanged this pass, nothing
  new captured; `mid_cab6_cavern.snap`/`mid_cab6_tunnel.snap` (66th pass) were re-read, not
  re-captured, to re-score `room_mosaic.py` against the new `hatari` palette-formula option.
- Start from: `gameplay_empire.snap` (CAVERN) / `room2_tunnel_entry.snap` (TUNNEL) for ordinary
  static/gameplay work; `mid_cab6_cavern.snap` / `mid_cab6_tunnel.snap` specifically for re-reading
  either room's live tile-placement list (the list is a scratch buffer, unreadable from a
  steady-state snapshot).
- Uncommitted work left behind: none of this session's own. `M68000/sessions/README.md` still
  carries the pre-existing line-wrap-only edit noted in the last several handoffs (not this
  session's, left alone per "one writer per file" — check `git status` fresh rather than trusting
  this line if it's been a while). `Cadaver/` (game disk images) and `.obsidian/` (an Obsidian
  vault config) are untracked, predate this session, and aren't part of any workstream — left
  alone.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` §1-63 (movement collision/proximity, the icon-panel write chain, the full 72-room
world-map/adjacency graph, the door-connectivity walk, the swapped-disk side-count bug, the
Replicants/ST Amigos crack's Disk 2 swap, two genuine emulator gaps behind the "crack dispatch bug",
the FDC "no data" workflow fix, the two-disk build's `$100`-shift bugs, a real CAVERN→TUNNEL crossing
driven live, Disk 2's one-time boot-time load with zero further FDC activity, CAVERN/TUNNEL having no
live-reachable third room) and `graphics.md` §5a-5j (the shared 80-tile terrain catalog, its per-room
RLE-compressed per-column tile-stack encoding, the `$cbd4` top-bit marker channel fully resolved
including its `0xc2` sub-case, no runtime tile-adjacency rules, the per-cell screen-placement formula,
the full draw pipeline, both known rooms scored ~96% pixel-exact against their reference screenshots).

**This pass (`graphics.md` §5i-3 addendum)**: cloned Hatari source (`hatari/hatari`) and read
`conv_st.c`'s `ConvST_SetupRGBTable`, the real STF `$0RGB`→RGB conversion (`gun*34` for a plain
3-bit register — confirmed `Screen_MapRGB` packs 8-bit channels directly, no further rescaling).
Added it to `room_mosaic.py` as `--palette-formula hatari` and re-scored both known-good mosaic
captures against it: **0/19749 exact for CAVERN (`gameplay.png`), 0/9932 exact for TUNNEL
(`room2_tunnel_entry.png`)** — not a rounding-level miss, a complete non-match against both. This
proves neither reference screenshot was ever rendered by Hatari's real conversion; both are
artifacts of this repo's own historical tooling (one `gun*255//7`-equivalent, one
`gun*36`-equivalent). There is no ground truth for the two in-repo formulas to converge on, so
"unify" was the wrong frame for the previous handoff's top item — the existing
`--palette-formula {ste,st}` per-reference selection (default `ste`) is already the correct
permanent answer. Generalized as a new bullet in `.claude/skills/reverse-engineer-st-game/SKILL.md`
§4b (commit `9230514`).

## Open, in priority order

1. **Render `room_mosaic.py`'s one still-dropped `0xc2`-sourced entry** for TUNNEL (small, 48×57px,
   `graphics.md` §5f/§5i-3) — cosmetic completeness now that it's not blocking the match score.
2. **Cross-check type-2's catalog (`items/`, §5a) against §3's 22-entry sprite/object array
   field-for-field** — same conceptual role (small-object art); is type 2 literally the template
   catalog §3's per-room instances draw their art from, or a separate, overlapping pool? Not
   confirmed either way.
3. **Stack direction** (does per-column tile-stack index 0 sit at the floor or the ceiling, §5e) —
   still not proven either way; the room-terrain rendering work being fully proven now (both rooms
   ~96%) hasn't settled this.
4. **The CAVERN mosaic's own ~3.4% overlap-edge residual** (§5i-2, confirmed unrelated to the
   palette-formula question, since its reference already matches `room_mosaic.py`'s default
   formula) — small, visually negligible, cause not identified.
5. **Does Disk 2 add reachable content beyond CAVERN/TUNNEL?** (64th pass, `mechanics.md` §63): still
   recommended closed for practical purposes; unaffected by this pass.
6. `2516(A5)`'s role still unconfirmed. Only worth resolving if another item needs a real day/progress
   counter.
7. `disk_layout.py`'s blank/data classifier only catches single-byte fills, not short-period repeats.
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

With graphics/rendering work now solidly proven for both known rooms (~96% each) and the palette
question fully closed, items 1 and 2 are the natural next self-contained steps (render the dropped
`0xc2` entry, then cross-check the type-2 catalog against §3's object array). This is also a
reasonable point to step back from graphics micro-proof and revisit a broader open thread (item 5's
Disk 2 question, or a fresh subsystem) if Dave would rather redirect. Prompt: `/resume cadaver`.
