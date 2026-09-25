# Cadaver: handoff

Updated 2026-09-25 by the session that ended at commit `05dffa8` (65th pass, following the 64th's
`3448983`), which closed Dave's explicit ask from the last handoff — the per-room terrain *pixel*
mosaic — from "not attempted" to "mechanism fully traced and live-confirmed, one real room rendered
and visually matched against `gameplay.png`." The first render had a real bug (opaque paste instead
of masked, §5i) that produced a comb of gaps — Dave caught it looked wrong on inspection even though
the overall two-wall silhouette was already correct; fixed same pass, see §5i for the two checks
that rule out a placement/direction bug specifically. Full writeup: `reversing/cadaver/graphics.md`
§5h/§5i (the new plain-English "How a room's walls and floor actually get to the screen" section
sits right after §5i for a non-code-level summary). Two lessons from the compositing bug and an
earlier pointer-vs-array trap were also folded into `.claude/skills/reverse-engineer-st-game/
SKILL.md` (commit `fd31b44`) since both are general enough to bite the next game, not just Cadaver.

## Resume point

- Last commit of this workstream: `05dffa8` "cadaver: fix mosaic compositing bug — mask the paste,
  don't paste opaque (65th pass cont.)" (`edb0b34` is the same pass's first mosaic commit, superseded
  in place by `05dffa8`'s fix, not left as a separate historical artifact — the committed
  `cavern_mosaic.png`/`room_mosaic.py` are already the fixed version). `fd31b44` "reverse-engineer-
  st-game skill: two lessons from cadaver's mosaic pass" is a shared-resource commit from the same
  session, not workstream-specific, left out of the working-data path below. No emulator source
  changed this pass (all static disassembly + REPL `kbd`/`bpc`/`snap`/`callcap` + Python reads), so
  no rebuild or regression-net run is needed before building on it.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). This pass's one durable
  addition worth keeping: `mid_cab6_cavern.snap` — a snapshot taken mid-room-entry (PC inside
  `$00d1f8`, right after the real `$00cab6` grid-walk that builds CAVERN's live draw-descriptor
  list), the only kind of snapshot this list can be read from (it's scratch data, rebuilt each room
  entry, unreadable from an ordinary steady-state snapshot — see graphics.md §5i). Recipe to
  reproduce it (also in `reversing/cadaver/py/room_mosaic.py`'s header): from
  `scratchpad/cadaver/room2_tunnel_entry.snap`, REPL `kbd ff 02` / `bpc cab6 1 3000000` (hits at step
  703,353) / `s 5000` / `snap scratchpad/cadaver/mid_cab6_cavern.snap`. Also left in scratchpad from
  an end-of-session exploratory detour (Dave asking "which tiles can sit next to each other" out of
  curiosity, not a work item): `tile_vjoin_top3.json` (an 80-tile vertical-join similarity ranking,
  normalized cross-correlation over the real overlap region) and `tile_families_ordered.png`/
  `cavern_mosaic_labeled.png` (a whole-catalog contact sheet reordered by visual similarity, and the
  CAVERN mosaic with every tile id labelled). **Not validated as a real prediction** — checked against
  the 56 real consecutive tile pairs from `mid_cab6_cavern.snap`'s own live list and only weakly beat
  chance (median rank ~32-36 of ~76, top-10 hit rate ~24% vs ~13% chance) — useful for browsing the
  catalog's visual families, not for reconstructing real placement choices; not reproduced by a
  script (was inline analysis), regenerate from this handoff's git history if wanted. Everything else
  in `scratchpad/cadaver/` carries over unchanged from the 64th pass.
- Start from: the same two snapshots as before for ordinary static/gameplay work —
  `gameplay_empire.snap` (CAVERN) / `room2_tunnel_entry.snap` (TUNNEL) — plus the new
  `mid_cab6_cavern.snap` specifically for re-reading or re-rendering the live tile-placement list.
- Uncommitted work left behind: none of this session's own. `sessions/README.md` may still carry a
  concurrent session's edit (not this one's — left alone per the "one writer per file" rule); check
  `git status` fresh rather than trusting this line, since that's someone else's in-flight work.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` §1-63 (movement collision/proximity, the icon-panel write chain, the full 72-room
world-map/adjacency graph, the door-connectivity walk, the swapped-disk side-count bug, the
Replicants/ST Amigos crack's Disk 2 swap, the two genuine emulator gaps behind the "crack dispatch
bug", the FDC "no data" workflow fix, the two-disk build's `$100`-shift bugs, a real CAVERN→TUNNEL
crossing driven live, Disk 2's one-time boot-time load with zero further FDC activity, CAVERN/TUNNEL
having no live-reachable third room) and `graphics.md` §5a-5g (the shared 80-tile terrain catalog,
its per-room RLE-compressed per-column tile-stack encoding, the `$cbd4` top-bit marker channel, no
runtime tile-adjacency rules).

**This pass (`mechanics.md` §39 continuation, `graphics.md` §5h/§5i)**:

- **§5h (mechanics.md §39, full transcription)**: `$00e7b0`'s nested placement-table loop, which the
  64th pass's own §39 had only summarized ("writes screen-buffer offsets... stepping A1 by
  $508/$4f8"), fully disassembled and closed into an exact formula: `screen_offset(row, col) =
  base_offset + row*$4f8 + col*$508`, row-major into `(A5)+2634`, `base_offset` = the same
  `$5a10`-lookup value already known to seed `(A5)+148`. **Checked against every cell, not
  sampled**: 15/15 TUNNEL cells, 100/100 CAVERN cells, both live off `(A5)+2634`, both match the
  Python-computed formula exactly. The two step constants decompose against the screen's 160-byte
  scanline stride as an 8-scanline-down, 16px-left-or-right diagonal step — a real isometric
  placement geometry, not a coincidence of the numbers.
- **§5i**: traced the draw pipeline past where §5c stopped (`A4 := tile_catalog + tile_id*$200`) —
  `$00cab6` writes that pointer into a draw-descriptor slot and calls `$00d1f8` (previously
  untraced), which looks up §5h's table, applies a sub-pixel shift (a second shift-mask table at
  `$5692`, same shape as the already-proven `$5870`), and appends a 16-byte descriptor to a list
  pointed to (not stored at) `(A5)+72`. `$00ddb6`/`$00dd1c` (both previously untraced) cull that list
  together with the persistent object array (`(A5)+76`, `mechanics.md` §37d) into one combined
  per-frame visible list, then hand every survivor to `$00014d64`'s already-proven
  masked-shift blitter (`graphics.md` §4b). This closes §4d's old inference ("tiles use the same
  blitter as sprites") into a fully-traced mechanism. **Confirmed live**, not just read statically:
  drove the proven TUNNEL→CAVERN crossing (`kbd ff 02` hold from `room2_tunnel_entry.snap`), caught
  `$00cab6` firing for real (step 703,353, `A6` = CAVERN's own room record), captured
  `mid_cab6_cavern.snap` mid-walk, and read 76 real tile-catalog pointers out of the dereferenced
  list — entries 0-2 are tile ids `55,56,57`, an independent match against `graphics.md` §5e's
  already-documented "CAVERN's width-pass column 0 is `[0x37,0x38,0x39]`". Rendered all 76 at their
  decoded screen positions: `reversing/cadaver/tiles/cavern_mosaic.png` — two isometric cave walls
  meeting at a corner, matching `gameplay.png`'s CAVERN room's shape and texture placement. **Two
  real debugging traps this pass, both worth remembering**: (1) `(A5)+72` is a *pointer* to the
  list, not the list's own address — `movea.l 72(A5),A3` dereferences it, and reading raw bytes
  starting at `(A5)+72` itself (this pass's first several attempts, and every steady-state-snapshot
  check before the live capture) finds a real but unrelated 134-entry structure that happens to live
  there and never holds a tile pointer; (2) the *first* rendered mosaic pasted each 32×32 tile
  opaquely, which — since this placement relies on ~50% column/row overlap (§5h) — let every tile's
  black background corners stomp over the previous tile's visible edge, leaving a comb of black gaps.
  It still had the right two-wall silhouette (right shape, wrong texture continuity), which is
  exactly why Dave caught it on a close look ("looks like the wrong side was drawn") when a coarser
  glance hadn't; masking the paste on palette index 0 (`sae.decode_st_interleaved(..., palette=None)`
  gives the raw index image for the mask) fixed it. Neither trap was a placement/direction bug — the
  column↔pass↔screen-side mapping was checked and is correct (`graphics.md` §5i has the two specific
  checks). Both traps cost real time; flagged in `graphics.md` §5i and
  `reversing/cadaver/py/room_mosaic.py`'s header so they aren't rediscovered.
- Added a plain-English "How a room's walls and floor actually get to the screen" section to
  `graphics.md` (right after §5i) — Dave's own ask mid-pass: a non-code-level narrative of the same
  mechanism (recipe → shared tile catalog → one-time placement arithmetic → per-room instruction
  list → shared blitter), for a reader who wants the mental model without the addresses.

## Open, in priority order

1. **Exact pixel-diff match count against `gameplay.png`**: the current mosaic decodes each
   descriptor's screen offset as `row = offset÷160, pixel_x = (offset mod 160)×2` and ignores
   `$00d1f8`'s own sub-pixel shift-table (`$5692`) adjustment — visually and structurally proven, not
   byte-exact. Incorporating that shift (the same `ror.l`/mask-table technique §4b already
   transcribes for `$5870`) into `room_mosaic.py`'s placement, then a real per-pixel diff against
   `gameplay.png`, is the concrete way to turn this pass's "clearly the same room" into a match
   count. Should be a short follow-up, not a new investigation — the hard part (finding and proving
   the pipeline) is done.
2. **The same live capture for TUNNEL.** This pass only got CAVERN (the TUNNEL→CAVERN crossing was
   already a proven recipe from `mechanics.md` §38; the reverse direction wasn't tried beyond one
   failed guess, `kbd ff 01` from `gameplay_empire.snap`, 0 hits of `$00cab6` in 3M steps). Finding
   the real CAVERN→TUNNEL key/route (check `mechanics.md`'s existing crossing notes for the door's
   world-coordinate side, or just try the other three directions with the same `bpc cab6 1 3000000`
   recipe) and rendering `tunnel_mosaic.png` would make this a 2/2 proof instead of 1/2.
3. **`$92e8`/`$cc2e`'s `bsr $d1f8`** (`graphics.md` §5f's `0xc2` sub-case) — note this is a
   *different* call site into `$d1f8` than the one §5i traces (the plain-tile placement case); still
   open whether it anchors an object to a grid position. `$92e8` itself has never been disassembled.
4. **Stack direction** (does per-column tile-stack index 0, §5e, sit at the floor or the ceiling) —
   the live mosaic didn't settle this either; would fall out of item 1's exact placement once the
   sub-pixel shift is in and each stack's actual on-screen vertical order can be read off directly.
5. **Does Disk 2 add reachable content beyond CAVERN/TUNNEL?** (64th pass, `mechanics.md` §63):
   still recommended closed for practical purposes; unaffected by this pass.
6. `2516(A5)`'s role still unconfirmed. Only worth resolving if another item needs a real
   day/progress counter.
7. `disk_layout.py`'s blank/data classifier only catches single-byte fills, not short-period
   repeats. No `.stx`→`.st` converter exists in `tools/`.

## Known traps

(Carried over from earlier passes — see git history for the full set: `ScreenBufferA/B` role-swap
framing is wrong, `movem` block-copy chunk reversal, `watch`'s step= counter is a lifetime counter
not local, one-shot breakpoint chase non-reproducibility, re-disassemble elided `...` excerpts in
full, `bpc` over `bp` for one-shot dumps, `bt depth>1` can crash the REPL, a `watch` range can
bracket multiple regions in one call, `gfxview.py`'s `st-interleaved` assumes 16px-wide masked
blits, movement is joystick port 1, player = sprite slot 0, use
`tools/find_ram_callers.py`/`find_field_writers.py`/`find_literal_ptr.py`/`find_jump_table_hit.py`,
the `moveq #0,Dn`-then-`move.b` zero-extend/condition-code trap, a byte's top bits gating a whole
different code path, a whole-image `disassemble.py --all` dump + call-site census to rule out a
dead type/case.)

- **A struct field documented as "an array at `(A5)+N`" may actually be a pointer *to* that array,
  not the array's own address** — check whether the code that reads it uses `movea.l N(A5),Ax`
  (dereference) or `lea N(A5),Ax`/direct-offset addressing (literal) before reading raw memory at
  `(A5)+N` yourself. This pass spent most of its live-verification time reading real-but-irrelevant
  bytes starting at `(A5)+72` itself, across eight different snapshots, before checking which
  addressing mode `$00cae4`'s `movea.l 72(A5),A3` actually uses. Cheap to check up front: grep the
  routine's own disassembly for whether the field is loaded with `movea`/`move.l ...,Ax` (pointer) or
  used directly as a base displacement (`N(A5)` in an addressing mode, not loaded into a register
  first) before trusting either reading.
- **Compositing overlapping sprite/tile art needs a transparency mask, not an opaque paste, whenever
  the placement relies on tiles overlapping** (isometric "brick" stacking, §5h/§5i: neighbouring
  cells here overlap by half a tile both horizontally and vertically by design). Each 32×32 tile
  is a cube shape on a black (palette index 0) background, not full-square art; pasting it as an
  opaque square lets every later tile's black corners erase part of the previous tile in the overlap
  region, producing a comb of gaps that still roughly outlines the right shape — plausible enough at
  a glance to pass a quick look, wrong enough to fail a close one. Get a mask from
  `sae.decode_st_interleaved(ram, addr, w, h, bpp, palette=None)` (the "L"/raw-index mode, index 0
  everywhere the art is background) and paste with it (`Image.paste(img, pos, mask)`), don't paste
  the RGB conversion directly.
- **A scratch/display-list-style buffer (rebuilt each use, `-1`/sentinel-terminated, referenced only
  by a pointer field) generally can't be read "for free" from a steady-state snapshot** — by the time
  ordinary gameplay has settled, it may hold the last unrelated thing that reused the same memory,
  not stale copies of its own intended content. If a whole-image `disassemble.py --all` + call-site
  census shows a routine has exactly one live caller (`graphics.md` §5i: `$00cab6`'s only caller is
  `$00ccd4`, called only from `$00e968`), and a `callcap`/steady-state `bpc` census on it comes back
  empty, the routine likely only fires at a specific state transition (here: room entry) — find that
  transition's own real trigger (a `kbd` hold reproducing a proven crossing, `mechanics.md` §38) and
  catch it live with `bpc <addr> 1 <budget>` plus a few thousand more steps and a `snap`, rather than
  concluding from static reads alone that the routine's target buffer is unreachable or misidentified.

## Next session

Item 1 (exact pixel-diff match count) is the natural next step and should be quick: extend
`reversing/cadaver/py/room_mosaic.py` to apply `$00d1f8`'s `$5692` sub-pixel shift table (transcribed
in `graphics.md` §5i, same technique as the already-proven `$5870` table in §4b) before pasting each
tile, then diff the result against `gameplay.png` for a real match count. `mid_cab6_cavern.snap` is
already captured and ready to use — no new live driving needed for this step. Item 2 (TUNNEL's own
mosaic) needs one new live capture: try the other three `kbd ff 01/04/08` directions from
`gameplay_empire.snap` with the same `bpc cab6 1 3000000` recipe used for CAVERN, or check
`mechanics.md`'s door-connectivity notes for TUNNEL's actual world-coordinate approach direction
first rather than guessing all four.
Prompt: `/resume cadaver`.
