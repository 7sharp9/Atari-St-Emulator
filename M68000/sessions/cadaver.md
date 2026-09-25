# Cadaver: handoff

Updated 2026-09-25 by the session that ended at commit `0d4424d` (67th pass, following the 66th's
`c364dd2`), which closed out the previous handoff's top item — trace `$92e8`/`$d1f8`'s `0xc2`
object-anchor sub-case — completely, and in doing so found and fixed the *actual* explanation for
TUNNEL's low room-terrain mosaic score, which turned out to be unrelated to `0xc2`. Full writeup:
`reversing/cadaver/graphics.md` §5a/§5f/§5i-3.

## Resume point

- Last commit of this workstream: `76a4abf` "cadaver: 0xc2 sub-case resolved (resource type 2,
  generic item overlay); TUNNEL's mosaic score was a palette-formula bug, not a content gap (67th
  pass)". `0d4424d` "reverse-engineer-st-game skill: a palette-formula lesson from cadaver's TUNNEL
  pixel-diff pass" is a shared-resource commit from the same session, its own small commit per the
  sessions/README.md rule. No emulator source changed this pass (static disassembly + Python reads
  of live snapshots only), so no rebuild or regression-net run is needed before building on it.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored) — unchanged this pass, nothing
  new added. `mid_cab6_cavern.snap`/`mid_cab6_tunnel.snap` (66th pass) were re-read, not re-captured.
- Start from: `gameplay_empire.snap` (CAVERN) / `room2_tunnel_entry.snap` (TUNNEL) for ordinary
  static/gameplay work; `mid_cab6_cavern.snap` / `mid_cab6_tunnel.snap` specifically for re-reading
  either room's live tile-placement list (the list is a scratch buffer, unreadable from a
  steady-state snapshot).
- Uncommitted work left behind: none of this session's own. `M68000/sessions/README.md` carries a
  pre-existing line-wrap-only edit that predates this session (not this session's, left alone per
  "one writer per file" — check `git status` fresh rather than trusting this line if it's been a
  while). `Cadaver/` (game disk images) and `.obsidian/` (an Obsidian vault config) are untracked,
  predate this session, and aren't part of any workstream — left alone.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` §1-63 (movement collision/proximity, the icon-panel write chain, the full 72-room
world-map/adjacency graph, the door-connectivity walk, the swapped-disk side-count bug, the
Replicants/ST Amigos crack's Disk 2 swap, two genuine emulator gaps behind the "crack dispatch bug",
the FDC "no data" workflow fix, the two-disk build's `$100`-shift bugs, a real CAVERN→TUNNEL crossing
driven live, Disk 2's one-time boot-time load with zero further FDC activity, CAVERN/TUNNEL having no
live-reachable third room) and `graphics.md` §5a-5j (the shared 80-tile terrain catalog, its per-room
RLE-compressed per-column tile-stack encoding, the `$cbd4` top-bit marker channel now fully resolved,
no runtime tile-adjacency rules, the per-cell screen-placement formula, the full draw pipeline).

**This pass (`graphics.md` §5a, §5f, §5i-3)**:

- **§5a, corrected: resource type 2 is not dead.** The 24th-pass census that concluded "type 2 is
  never referenced" only checked callers of the generic `(type,index)` fetch `$00c5a8`; type 2 is
  actually reached through a second, dedicated primitive, `$00c576` (hardcodes `moveq #2,D0`, a
  different index-table slot encoding), with **28 call sites** — more than any other single type's
  own direct callers. Its 255-slot table is real: 102 distinct entries (the rest alias one shared
  empty placeholder), rendered and committed — `reversing/cadaver/items/` (`contact_sheet.png`,
  `manifest.csv`, `reversing/cadaver/py/resource2_export.py`) — a general small-object/icon catalog
  (boat, barrels, chests, keys, gems, a dragon, two wall-panel graphics).
- **§5f, `0xc2` fully traced and closed out.** `$92e8`/`$00c576` decode into a 16-byte draw
  descriptor with the *same* field layout §5i's plain-tile path uses (`+2/+3` w/h, `+10` source
  pointer, `+14` byte size), then call the *same* `$d1f8` placement/clip routine — i.e. the grid's
  `0xc2` marker paints one of §5a's type-2 catalog items into a cell through the identical pipeline
  ordinary tiles use, not a separate object-instantiation path as an earlier pass guessed (that guess
  read only half of `$cbe0`-`$cc42` and conflated `$92e8`'s own bookkeeping fields with the actual
  draw descriptor). Real and generic, index = `(marker & 0xf) - 1`, with a one-slot row/col nudge.
- **§5i-3, TUNNEL's real score: 96.0% (9534/9932), in line with CAVERN's 96.6% — not 19.7%.** The
  66th pass's "left wall renders as generic art, `0xc2` is the leading suspect" reading was wrong:
  the actual cause was that `room_mosaic.py`'s palette conversion (`gfxview.ste_colour`,
  `gun*255//7`) disagrees with `snap_render.py`'s (`st_colour`, `gun*36`), and TUNNEL's reference
  screenshot happened to be made with the latter while CAVERN's used the former — a pure tooling
  artifact, not a content or placement gap. `room_mosaic.py` now takes `--palette-formula {ste,st}`;
  `tunnel_mosaic.png` was regenerated with the matching one and re-committed. TUNNEL's one live
  `0xc2` cell is real but sits on the wall that was already matching, so it explains at most a small
  fraction of the old (now-closed) gap, not the bulk of it.

## Open, in priority order

1. **Unify `gfxview.ste_colour`'s `gun*255//7` and `snap_render.py`'s `st_colour`'s `gun*36`
   palette-to-RGB formulas** (`graphics.md` §5i-3). Neither was checked against Hatari's real STF
   DAC conversion this pass (no local Hatari source checkout found on this machine — only the app
   bundle in `~/Downloads/hatari-snapshot`); find or clone Hatari source and read `video.c`/
   `screen.c`'s palette conversion before picking a default, rather than preferring whichever a given
   screenshot happens to match. Affects every future `--diff`-style pixel comparison in this repo,
   not just cadaver.
2. **Render `room_mosaic.py`'s one still-dropped `0xc2`-sourced entry** for TUNNEL (small, 48×57px,
   `graphics.md` §5f/§5i-3) — cosmetic completeness now that it's not blocking the match score.
3. **Cross-check type-2's catalog (`items/`, §5a) against §3's 22-entry sprite/object array
   field-for-field** — same conceptual role (small-object art); is type 2 literally the template
   catalog §3's per-room instances draw their art from, or a separate, overlapping pool? Not
   confirmed either way.
4. **Stack direction** (does per-column tile-stack index 0 sit at the floor or the ceiling, §5e) —
   still not proven either way; the room-terrain rendering work being fully proven now (both rooms
   ~96%) hasn't settled this.
5. **The CAVERN mosaic's own ~3.4% overlap-edge residual** (§5i-2, confirmed unrelated to the
   palette-formula bug above, since its reference already used the matching formula) — small,
   visually negligible, cause not identified.
6. **Does Disk 2 add reachable content beyond CAVERN/TUNNEL?** (64th pass, `mechanics.md` §63): still
   recommended closed for practical purposes; unaffected by this pass.
7. `2516(A5)`'s role still unconfirmed. Only worth resolving if another item needs a real day/progress
   counter.
8. `disk_layout.py`'s blank/data classifier only catches single-byte fills, not short-period repeats.
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

## Next session

Item 1 (unify the two palette formulas) is cheap groundwork if a Hatari source checkout can be found
or cloned — otherwise skip straight to item 3 (cross-check the type-2 catalog against §3's object
array) or item 4 (stack direction), both self-contained. With the room-terrain rendering work now
solidly proven for both known rooms (~96% each), this is also a reasonable point to step back from
graphics micro-proof and revisit a broader open thread (e.g. item 6's Disk 2 question, or a fresh
subsystem) if Dave would rather redirect. Prompt: `/resume cadaver`.
