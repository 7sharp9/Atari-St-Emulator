# Cadaver: handoff

Updated 2026-09-25 by the session that ended at commit `3448983` (this pass, following the 64th's
`37ff4b8`), which found and extracted the room terrain tile system: `graphics.md` §37's own "a
room's background is just its object array" was wrong — the walls/floor are a separate, shared,
boot-loaded 80-tile catalog, indexed per room by a small compressed tile-ID stream. Full writeup:
`reversing/cadaver/graphics.md` §5 (5a-5g). Prompted directly by putting the already-proven 22-entry
sprite/object catalog's own contact sheet next to a gameplay screenshot and noticing nothing in it
was wall-scale — a five-second visual check four earlier passes' worth of code tracing had skipped
(now a checklist item in the `reverse-engineer-st-game` skill).

## Resume point

- Last commit of this workstream: `3448983` "cadaver: shared 80-tile room-terrain catalog found and
  extracted". (`1127533` and `68119b5` are shared-resource commits from the same session —
  `DEVELOPING.md`'s tools index and the `reverse-engineer-st-game` skill — not workstream-specific,
  left out of the working-data path below.) No emulator source changed this pass, so no rebuild or
  regression-net run is needed before building on it.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). This pass's additions:
  `cavern_grid.json`/`tunnel_grid.json` (the decoded per-room tile-id column-stacks, reproducible
  any time with `reversing/cadaver/py/room_tile_grid.py --room-slot 0|1`). Everything else carried
  over unchanged from the 64th pass (see prior git history for the full list) — none of it was
  touched this pass.
- Start from: same two snapshots as before, both still valid — `scratchpad/cadaver/
  past_wall_mounted_90M.snap` (fresh CAVERN start, disk 2 not yet mounted) or `scratchpad/cadaver/
  gameplay_empire.snap` (CAVERN, already resident, one-disk Empire build — this is the snapshot this
  pass's tile-catalog work used) / `scratchpad/cadaver/room2_tunnel_entry.snap` (TUNNEL). This pass
  did no live stepping at all — everything was static reads off these two existing snapshots plus
  one whole-image `disassemble.py --all 0x0 0x20000` dump (not saved; cheap to reproduce).
- Uncommitted work left behind: none of this session's own. `sessions/README.md` is still modified
  (a concurrent session's whitespace-wrap edit, not this one's — left alone per the "one writer per
  file" rule) and `.obsidian/`/`Cadaver/` are untracked and not this session's to manage.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` §1-63 (movement collision/proximity, the icon-panel write chain, the full 72-room
world-map/adjacency graph, the door-connectivity walk, the swapped-disk side-count bug, the
Replicants/ST Amigos crack's Disk 2 swap, the two genuine emulator gaps behind the "crack dispatch
bug", the FDC "no data" workflow fix, the two-disk build's `$100`-shift bugs, a real CAVERN→TUNNEL
crossing driven live, Disk 2's one-time boot-time load with zero further FDC activity, and the
64th pass's finding that CAVERN/TUNNEL have no live-reachable third room).

**This pass (`graphics.md` §5)**: the room terrain/tile system, found and proven by direct render:

- **§5a**: type 2 (255-entry resource-manager capacity) has no live caller anywhere in the loaded
  program — a whole-image caller census of `$00c5a8`, not a spot check. Dead end, ruled out cleanly.
- **§5b/5c/5d**: a room's wall/floor layout is a tiny compressed byte stream (resource type 1, 42
  bytes for TUNNEL, 122 for CAVERN), RLE-decoded (`$00add0`-`$00ae62`) into a live table at
  `(A5)+2914`, consumed (`$00cab6`-`$00cb28`) as a flat lookup into a **shared, boot-time-loaded,
  80-tile, 32×32, 4bpp catalog** at `$03e77e` (stride `$200`, size confirmed live via `(A5)+24 =
  40960 = 80×512`, not approximated). Rendered all 80 — clean, unambiguous cave-wall/floor art,
  zero-fill past index 79 confirming the boundary exactly. `reversing/cadaver/tiles/` (80 PNGs,
  `contact_sheet.png`, `manifest.csv`).
- **§5e**: the decoded table is two ragged per-column tile stacks (a wall height-field), not a
  rectangular grid — proven by rendering both rooms' real stacks against the real catalog
  (`reversing/cadaver/tiles/cavern_grid.png`/`tunnel_grid.png`, `reversing/cadaver/py/
  room_tile_grid.py`). CAVERN's width-pass reads as a visually coherent wall elevation matching
  `gameplay.png`'s uneven skyline.
- **§5f**: `$cbd4` (the top-bit-set grid-byte handler) traced in full — mostly an inert no-op
  (`0x82`/`0x86`/`0xc6` in the two grids sampled all fail its own bit6/bit2 gate), with one live
  sub-case (`0xc2`-shaped bytes) that writes sprite/object-array-shaped struct fields, not tile
  pixels — reframed as a probable object-anchor channel, not proven past the struct-field writes.
- **§5g**: no tile-adjacency/compatibility ruleset exists in the decoder or the consumer — wall/floor
  composition is level data (a fixed per-room byte stream), not an engine-enforced rule, the same
  way `mechanics.md` §37d's object placement is a fixed list.

## Open, in priority order

Dave's explicit ask for the next session: **room layout/floor/mosaic understanding** — reconstruct
how the tile catalog actually composes into each room's visible screen image, not just prove the
catalog and the per-column sequence (both done this pass).

1. **Full per-room pixel mosaic**: place §5e's per-column tile stacks at their real screen
   coordinates and pixel-diff the result against `gameplay.png`/`room2_tunnel_entry.png`. Needs the
   `2634(A5)+` per-cell screen-offset table's own placement math — `$00e7b0`'s nested `dbf` loop
   (`graphics.md`/`mechanics.md` §39) was read for its width/height indexing but its actual
   iso-projection arithmetic (the `$508`/`$4f8` per-column/row strides mentioned there) was never
   fully transcribed. This is the concrete way to turn the already-proven "the walls are these
   tiles, in this sequence" into "and here is exactly where each one lands," and to settle item 2.
2. **Stack direction**: does column-stack index 0 (§5e) sit at the floor or the ceiling of that
   column's wall face? Assumed consistent from a visual read this pass, not proven. Falls out of
   item 1 for free once the screen-offset math is in hand — a wrongly-oriented stack would show up
   immediately as an upside-down wall in the mosaic.
3. **`$cbd4`'s live `0xc2` sub-case** (§5f): does it really anchor a sprite/object-array entry to a
   grid position, or something else? `$92e8` and `$cc2e`'s `bsr $d1f8` are unread past the struct
   offsets they write. A `callcap`/`watch` on a room whose grid actually reaches this sub-case (not
   yet identified — check other rooms' type-1 streams for a `& $44 == $40` byte, or just census the
   ones this session already has) would settle it, and matters for item 1 too: if this channel
   places props, then a mosaic built from §5e's tile stacks alone will be missing them.
4. **Does Disk 2 add reachable content beyond CAVERN/TUNNEL?** (64th pass, `mechanics.md` §63):
   four independent subsystems agree it doesn't from these two rooms; recommended closed for
   practical purposes unless Dave wants the open-ended push into a new starting state or the
   type-8 registration trigger. Superseded in priority by the room-mosaic work above, not by new
   evidence.
5. No calibration between `world_map.py`'s coarse world-grid room rectangles and the player bbox's
   own coordinate scale — likely subsumed by item 1's screen-offset math once that's derived.
6. `2516(A5)`'s role still unconfirmed (reads `100` in the known snapshots, not a small day-count
   index). Only worth resolving if item 1 or item 4 needs a real day/progress counter.
7. `disk_layout.py`'s blank/data classifier only catches single-byte fills, not short-period
   repeats. No `.stx`→`.st` converter exists in `tools/`.

## Known traps

(Carried over from earlier passes — see git history for the full set: `ScreenBufferA/B` role-swap
framing is wrong, `movem` block-copy chunk reversal, `watch`'s step= counter is a lifetime counter
not local, one-shot breakpoint chase non-reproducibility, re-disassemble elided `...` excerpts in
full, `bpc` over `bp` for one-shot dumps, `bt depth>1` can crash the REPL, a `watch` range can
bracket multiple regions in one call, `gfxview.py`'s `st-interleaved` assumes 16px-wide masked
blits, movement is joystick port 1, player = sprite slot 0, use
`tools/find_ram_callers.py`/`find_field_writers.py`/`find_literal_ptr.py`/`find_jump_table_hit.py`.)

- **A `moveq #0,Dn` immediately before `move.b (Ax)+,Dn` zero-extends Dn, but the condition codes
  after the `move.b` reflect only the byte** — `bmi`/`beq` right after test bit 7/zero-ness of that
  one byte, not of the zero-extended longword. Cadaver's terrain-grid consumer (`$00cb12`-`$00cb1c`)
  uses exactly this idiom to route top-bit-set grid bytes to a different handler; reading the
  registers as "D7 is a small non-negative int, so `bmi` can never fire" would be wrong.
- **A byte value's top two bits can gate a whole different code path** (`graphics.md` §5f: `btst
  #6,D7`/`btst #2,D7`) even when every example you happen to have looks like a simple "flag on an
  ordinary id" — check what the code actually branches on before assuming a masked-off low nibble is
  the real payload; two of Cadaver's four sampled bit7-set values turned out to be pure no-ops, not
  variants of anything.
- A whole-image `disassemble.py --all <lo> <hi>` dump plus a grep for a dispatch/resource function's
  call sites (and the selector set immediately before each) is a fast, complete way to rule out a
  type/case as dead — cheaper than reasoning from the data's own shape, and it's what caught type 2
  being unreferenced anywhere (`graphics.md` §5a). Now also in the `reverse-engineer-st-game` skill.

## Next session

Start from `gameplay_empire.snap` (CAVERN) and `room2_tunnel_entry.snap` (TUNNEL) — same two
snapshots this pass used, no rebuild needed. First step: disassemble `$00e7b0`'s nested `dbf` loop
in full (the part `mechanics.md` §39 read for width/height indexing but not for its own placement
arithmetic) to get the real per-column/per-row iso-projection math, then extend
`reversing/cadaver/py/room_tile_grid.py` to place each column-stack tile at its real screen offset
and composite it (through the same masked shift-blitter every other draw in this engine uses,
`graphics.md` §4b) against `gameplay.png`/`room2_tunnel_entry.png` for a real pixel match count —
that's Open item 1, and it resolves item 2 (stack direction) as a side effect. Item 3 (`$cbd4`'s
object-anchor sub-case) is the next thing worth a `callcap`/`watch` pass if item 1 turns up rooms
where tiles are visibly missing where a prop should be.
Prompt: `/resume cadaver`.
