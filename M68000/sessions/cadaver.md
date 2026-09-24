# Cadaver: handoff

Updated 2026-09-24 by the session that ended at commit `8032804`.

## Resume point

- Last commit of this workstream: `8032804` "cadaver: $0144b8 disassembled - reveals a third
  resident buffer at 120(A5), not a two-way swap".
- Disk image: `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add`. Present on this Mac checkout this
  session with no rebuild needed. If it's gone, pull it from `gpubox` (tar-over-ssh recipe,
  `CLAUDE.md`).
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). All snapshots from the prior
  handoff were still present this session (`room2_tunnel_entry.snap`, `gameplay_empire.snap`,
  `tunnel_return_cross.snap`, `tunnel_return_settled.snap`, `hit_014b28.snap`) — no rebuild needed.
  Nothing new was saved this session (only reads: raw hex, `watch`, `bpc`/`bt` register dumps,
  `gfxview.py` renders through a throwaway local `python3 -m http.server`, not committed).
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry, `(A5)=$18152` gives visible buffer
  `$19100`, its mirror half `$20f00`, and the separate `120(A5)` buffer `$2de08` in *this* snapshot —
  re-read all three live, they are not guaranteed stable across snapshots per README's own note).
  `kbd ff 02` reproduces the TUNNEL→CAVERN crossing. `gameplay_empire.snap` (CAVERN, day 1) for the
  reverse direction via the zigzag recipe. `hit_014b28.snap` for the specific PC `$014b28`.
- Uncommitted work left behind: none.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`.

- Collision, graphics compositing and the entity/object-verb bytecode interpreter are disassembled
  and documented (`mechanics.md` 1-6, 27).
- Type 3 (not type 8) is the real, populated room table, 72/100 slots (`mechanics.md` §31a).
- `$00014a90` fully disassembled (§32a) and its blit source pinned down live (§32b): `$014b28`'s
  source is a fixed, room-independent address (`$55b6` this session/last) — `$014a90` repaints a
  fixed status/icon-panel element at screen `(272,143)`, not room art. This session (§33a) read
  `$55b6`'s actual bytes directly from snapshot RAM: 96 bytes of solid zero for this call (a blank
  default-panel state, not a glyph — refines §32b, doesn't overturn it).
- The entity/sprite-list renderer is now live-traced twice (§33b, §34b): entry `$007f60`/`$0150b4`-
  family, called from a null-terminated pointer-list walk at `$00d900`-ish (`A3` = per-entity record,
  `A6=$00038338` = §21a's sprite-object-array base at the call). Confirmed not the room-art source —
  it draws sprites at their own screen positions, not a room-sized background. `$00bf72` (README's
  long-named blitter "sibling") writes a small ~700-byte sprite-bitmap-cache region (`$2ca84`-
  `$2cd42`), also not room art (two orders of magnitude too small).
- **New this session (§34a): `$0144b8` itself finally disassembled — the long-assumed "two
  role-swapping screen buffers" model (`(A5)` vs some second pointer field, per §32a's own comment)
  was wrong.** `(A5)+0` and `(A5)+$7d00` (32000) are the two halves of *one* 64000-byte double-buffer
  feeding the shifter directly (`$0144bc: movea.l 120(A5),A0` = source; `$0144c0/c2: movea.l
  (A5),A1 ; adda.l #$7d00,A1` = dest, pre-decrementing back down into the `(A5)+0` half). `120(A5)`
  is a **separate, third resident buffer** (`$2de08` this session) that the flip reads from — the
  real candidate for "where room art lives before the flip runs," not a peer of `(A5)`.
- **New this session (§34b): `120(A5)`'s buffer inspected live (idle, before any crossing) — not
  blank, but not a clean 320×200×4bpp frame under the standard decode either** (structured row
  banding, not uniform noise, not a recognisable room). Two nearby writers during a live crossing
  are confirmed to be the already-known entity/sprite systems (previous bullet), not a new painter.

## Open, in priority order

1. **Decode `120(A5)`'s buffer's actual layout, then find its writer.** This is the sharpened form
   of the long-standing "room background painter" question — §34a establishes this buffer, not
   `(A5)` itself, is what actually needs to hold room art before `$0144b8` copies it onto the visible
   double-buffer. Two sub-steps, in order:
   - (a) **Decode first.** The buffer (`$2de08` in `room2_tunnel_entry.snap`) is real, non-empty data
     with consistent structure (not random), but doesn't resolve as a plain 320×200×4bpp
     st-interleaved raster. Try alternate widths/row-strides/bpp in `gfxview.py` against this exact
     snapshot before assuming it needs a custom decoder — the known trap below (32px-per-longword
     planar order) is one candidate layout to try directly. A resolved image (even a garbled one) is
     worth more here than more live captures.
   - (b) **Then find the writer**, once you know what a "correct" render looks like well enough to
     recognise a change: `watch 2de08 32000` (or wherever `120(A5)` points in whatever snapshot you
     resume from) across a full room-load sequence, starting well before the first crossing (ideally
     from a cold boot or very early save, since this session's idle snapshot already had *some*
     content there — its origin is unknown and might predate any watch window you can arrange).
2. What `$55b6` contains for a *different* transition (e.g. an actual LEVER-proximity icon-panel
   change, §7) — §33a only checked the plain crossing this and the prior pass both used, and found
   zero. Lower priority than item 1.
3. Room-record bytes `+0..+3` (still unknown; `+4`/`+5` are the graphics-table index, `+$c0` is the
   mask table per §32a).
4. How the ~72 real rooms connect in ordinary play (`$007104` is not it: both branches `bra $69da`,
   §31b).
5. The two-disk original (§30b): lower priority, would be a fresh subject.

## Known traps

- **The Cadaver disk image is not in the usual Dropbox ST-games folder** — it's only on `gpubox`.
  Pull it with the tar-over-ssh recipe (CLAUDE.md) before assuming the workstream is blocked.
- **The "`ScreenBufferA`/`B` role-swap" framing in older passes (and this file, before §34a) is
  wrong** — don't reuse it. There are three regions, not two: `(A5)+0` and `(A5)+$7d00` are static
  halves of one double-buffer (dest of `$0144b8`'s flip, whichever half isn't currently the live
  shifter output — check `load_video_regs`/the shifter registers for ground truth on which), and
  `120(A5)` is a separate resident buffer (`$0144b8`'s source) that is the real room-art candidate.
  All three addresses are per-snapshot, not fixed constants (README already warned of this for the
  two it knew about; it now applies to `120(A5)` too).
- **Prefer `bpc <addr> 1 <maxSteps>` over `bp <addr> <maxSteps>` for a one-shot reliable register
  dump.**
- **`bt <depth>` with `depth` > 1 can throw an unhandled `Atari.AddressError` and kill the REPL
  process** if the return-address chain doesn't follow the A6 link-frame convention past the first
  frame. Use `bt 1` first; only widen once you've confirmed the caller actually uses linked A6
  frames.
- **A `watch` range can cover multiple regions of interest in one call** — `watch <lo> <len>` takes
  a single contiguous span, but nothing stops that span from being wide enough to bracket two or
  more buffers at once (e.g. `watch 19100 117504` covered both `$19100` and `$2de08`'s 32000-byte
  extents plus the gap between them in one run this session) — then bucket the resulting hits by
  destination-address range in a script. Cheaper than multiple separate `watch` runs when you need
  to compare several regions' write traffic from the same replay.
- `gfxview.py`'s `st-interleaved` layout renders standard 16-pixel word-interleaved planes
  correctly, but this game's masked-blit routines (`$014ee4`/`$007f60`/`$14f4a`/`$0150b4` family)
  read source data as **4 consecutive longwords per row** (one plane per 32-bit longword, 32 pixels
  wide, no inter-plane stride) — different in-memory order than word-interleaved for any width other
  than exactly 16px. Rendering one of these blit sources through the HTML viewer's normal controls
  produces noise; read the raw bytes directly from the snapshot instead (parse the `A68S` header per
  `gfxview.py`'s own `load_ram()`, then slice `ram[addr:addr+width*rows]`).
- Movement is joystick port 1 (`kbd ff 01/02/04/08` = up/down/left/right). One packet is a
  self-terminating multi-substep move needing 60k-100k steps.
- Player = sprite-array slot 0 (`$038338`, +42 = 0); `A5 = $18152`.
- Use `tools/find_ram_callers.py` and `tools/find_field_writers.py` for "who calls / writes X".

## Next session

Start with item 1(a): try alternate `gfxview.py` layouts/widths against `120(A5)`'s buffer
(`$2de08` in `room2_tunnel_entry.snap`) to get it to resolve into a recognisable image — it's real,
structured data, just not a plain 320×200×4bpp raster under the default decode. Once you know what a
correctly-decoded frame looks like, move to 1(b): `watch` that address across a room-load sequence
(starting earlier than this session's captures) to catch its actual writer. Prompt: `/resume
cadaver`.
