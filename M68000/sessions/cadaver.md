# Cadaver: handoff

Updated 2026-09-25 by the session that ended at commit `c364dd2` (66th pass, following the 65th's
`05dffa8`), which closed the previous handoff's explicit next step — an exact pixel-diff match count
for the CAVERN mosaic — and then extended the same live-capture technique to TUNNEL. CAVERN: the
mosaic's placement was already byte-exact (the draw descriptor's own `x0`/`y0` fields, not a separate
shift-table correction as assumed), scoring 96.6% pixel-exact against `gameplay.png`
(`reversing/cadaver/graphics.md` §5i-2). TUNNEL: found the real CAVERN→TUNNEL crossing route, captured
its own mid-room-entry snapshot, and proved the *same* placement mechanism is correct there too (table
byte-identical across two independent captures; a full live re-render of the capture reproduces the
reference screenshot pixel-for-pixel) — but the tile-only render still only scores 19.7% against
`room2_tunnel_entry.png`, isolated to one wall that carries decorative detail the base 80-tile catalog
doesn't have (§5i-3). Full writeup: `reversing/cadaver/graphics.md` §5i-2/§5i-3. A general RE lesson
(grid-search to cheaply tell a placement bug from missing content) was folded into
`.claude/skills/reverse-engineer-st-game/SKILL.md` §4b (commit `0339e90`).

## Resume point

- Last commit of this workstream: `c364dd2` "cadaver: TUNNEL's room-terrain mosaic captured live,
  mechanism confirmed generic (66th pass cont.)" (`d2f2ece` is the same pass's first commit, the
  CAVERN pixel-diff score). `0339e90` "reverse-engineer-st-game skill: a grid-search lesson from
  cadaver's pixel-diff pass" is a shared-resource commit from the same session, left out of the
  working-data path below. No emulator source changed this pass (all static disassembly + REPL
  `kbd`/`bpc`/`snap` + Python reads), so no rebuild or regression-net run is needed before building
  on it.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). This pass's one durable
  addition worth keeping: `mid_cab6_tunnel.snap` — TUNNEL's own mid-room-entry snapshot, captured via
  the CAVERN→TUNNEL crossing (recipe below), analogous to the 65th pass's `mid_cab6_cavern.snap`.
  `tunnel_settled_check.snap` (this pass, `mid_cab6_tunnel.snap` + 1M steps, used only to prove the
  crossing settles to the reference frame pixel-for-pixel) is disposable, not needed again.
- Start from: `gameplay_empire.snap` (CAVERN) / `room2_tunnel_entry.snap` (TUNNEL) for ordinary
  static/gameplay work, as before; `mid_cab6_cavern.snap` / `mid_cab6_tunnel.snap` specifically for
  re-reading or re-rendering either room's live tile-placement list (§5i/§5i-3 — the list is a scratch
  buffer, unreadable from a steady-state snapshot).
- Uncommitted work left behind: none of this session's own. `sessions/README.md` carries a
  concurrent/other session's line-wrap-only edit (not this one's — left alone per the "one writer per
  file" rule); check `git status` fresh rather than trusting this line. Two unrelated untracked items
  sit in the repo root (`Cadaver/` — game disk images and extracted files, `.obsidian/` — an Obsidian
  vault config) that predate this session and aren't part of any workstream; left alone.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` §1-63 (movement collision/proximity, the icon-panel write chain, the full 72-room
world-map/adjacency graph, the door-connectivity walk, the swapped-disk side-count bug, the
Replicants/ST Amigos crack's Disk 2 swap, the two genuine emulator gaps behind the "crack dispatch
bug", the FDC "no data" workflow fix, the two-disk build's `$100`-shift bugs, a real CAVERN→TUNNEL
crossing driven live, Disk 2's one-time boot-time load with zero further FDC activity, CAVERN/TUNNEL
having no live-reachable third room) and `graphics.md` §5a-5i (the shared 80-tile terrain catalog, its
per-room RLE-compressed per-column tile-stack encoding, the `$cbd4` top-bit marker channel, no runtime
tile-adjacency rules, the per-cell screen-placement formula, the full draw pipeline traced from the
tile-grid consumer through to the shared `$14d64` blitter and confirmed live for CAVERN).

**This pass (`graphics.md` §5i-2, §5i-3)**:

- **§5i-2, CAVERN pixel-diff, 96.6% (19079/19749 covered pixels) against `gameplay.png`.** The
  descriptor's own `x0`/`y0` fields (bytes 4-6/0) are already the exact absolute screen position — no
  `$5692` shift-table correction needs applying on top, contrary to the previous handoff's assumption;
  checked across all 76 real entries (`x0 == (offset%160)*2` and `y0 == offset//160` exactly) and by a
  global `(dx,dy)` grid search (`(0,0)` already optimal). `y0,y1` are a real on-screen clip window, not
  just metadata: a partially-clipped tile (`y1-y0 < 32`) shows its *bottom* `y1-y0` rows, which
  `room_mosaic.py` (rewritten this pass, gained a `--diff` option) now crops correctly. The residual
  3.4% is confirmed not a paint-order bug (natural list order beats every row-sorted alternative, and
  reverse order scores far worse) — clusters at inter-tile overlap edges, cause not identified.
- **§5i-3, TUNNEL captured live (2/2 rooms) via the real CAVERN→TUNNEL crossing.** The route is
  `mechanics.md`'s documented zigzag (`kbd ff 08` 1.2M steps, `kbd ff 01` 0.5M, `kbd ff 08` 1.2M,
  `kbd ff 01` 1.2M, joystick port 1, from `gameplay_empire.snap`); arming `bpc cab6 1 <budget>` per
  leg catches the room-entry draw-list build 52,887 steps into the final leg. Two independent checks
  prove the placement mechanism (formula + table) is correct for TUNNEL too, not CAVERN-specific: its
  `(A5)+2634` table is byte-identical to `room2_tunnel_entry.snap`'s own, and stepping the capture
  forward 1M steps then `snap_render.py`-rendering it reproduces `room2_tunnel_entry.png`
  pixel-for-pixel (0/64000 diff — the emulator's own real render of this route lands on the same
  frame the 12th pass's milestone used). Despite that, the *tile-only* mosaic scores only 19.7%
  (1961/9932) against the same reference — not uniform, isolated to one wall (high tile ids, 31-78)
  that renders as generic catalog "cube" art where the reference shows pipe/machinery detail absent
  from the 80-tile catalog. Leading suspect: §5f's still-untraced `0xc2` object-anchor sub-case of
  `$d1f8`, which may overlay extra per-cell decoration on top of the base tile — not confirmed.

## Open, in priority order

1. **Trace `$92e8`/`$d1f8`'s `0xc2` object-anchor sub-case (`graphics.md` §5f).** Was already open as
   an isolated question; this pass's TUNNEL finding (§5i-3) makes it the leading explanation for why
   TUNNEL's left wall doesn't match a tile-only render, so it's now higher priority and has a concrete
   test: if tracing it and rendering its output onto `tunnel_mosaic.png` raises the TUNNEL match score
   materially, that confirms it; if not, the real explanation is still open. Static disassembly of
   `$92e8` (never done) plus a live capture of a `bsr $d1f8` hit from that call site (not the plain-
   tile one §5i-3 already traces) is the concrete next step.
2. **The CAVERN mosaic's own ~3.4% overlap-edge residual (§5i-2)** — small, visually negligible, cause
   not identified; a per-entry pixel-level comparison of a few mismatched tile pairs (values are the
   same palette entries, just shuffled by ~1px at the shared edge) would be the way in, but low
   priority given the size.
3. **Stack direction** (does per-column tile-stack index 0, §5e, sit at the floor or the ceiling) —
   still not proven either way.
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
can't be read from a steady-state snapshot.)

- **A `bpc <addr> 1 <budget>` armed just before a *leg* of a multi-leg movement recipe (zigzag) catches
  a one-shot room-entry routine mid-movement without needing to know in advance which leg crosses the
  door** — arm it fresh per leg (`kbd ff <dir>` then `bpc <addr> 1 <budget>`, repeated for each leg)
  rather than running the whole zigzag with plain `s` steps and hoping to catch the hit separately;
  this pass's TUNNEL capture found the crossing on the very first leg it happened to fall in (the
  final "Up" leg) this way, without first having to know that in advance from the docs.
- **When a hand-rolled render of an independently-proven-correct placement scores low against a
  reference screenshot, check whether the mismatch is uniform (global `(dx,dy)` search still finds
  `(0,0)` best) or spatially clustered before assuming the placement formula itself is wrong** — a
  clustered mismatch (one wall, one region) points at missing content (an un-rendered object/sprite
  layer, an untraced sub-case) rather than a placement bug; see `graphics.md` §5i-3 and the same
  lesson now in `.claude/skills/reverse-engineer-st-game/SKILL.md` §4b.

## Next session

Item 1 (the `0xc2` object-anchor sub-case) is the natural next step: disassemble `$92e8` statically
first (never done), then find a live `bsr $d1f8` hit from that call site specifically — not the plain-
tile placement call site §5i/§5i-3 already fully traces — probably via the same `bpc`-per-leg technique
used to catch TUNNEL's crossing, or a `find_ram_callers.py`/whole-image census first to locate where
`$92e8` itself is even reached from. If tracing it and adding its output to `tunnel_mosaic.png` raises
TUNNEL's match score materially, that closes both this item and §5i-3's open question in one shot.
Prompt: `/resume cadaver`.
