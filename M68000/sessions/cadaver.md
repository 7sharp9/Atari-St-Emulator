# Cadaver: handoff

Updated 2026-09-24 by the session that ended at commit `1c6d166`.

## Resume point

- Last commit of this workstream: `1c6d166` "cadaver: $55b6 decoded (blank mask), full-buffer watch
  rules out sprite draws as the room painter".
- Disk image: `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add`. Present on this Mac checkout this
  session with no rebuild needed. If it's gone, pull it from `gpubox` (tar-over-ssh recipe,
  `CLAUDE.md`).
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). All snapshots from the prior
  handoff were still present this session (`room2_tunnel_entry.snap`, `gameplay_empire.snap`,
  `tunnel_return_cross.snap`, `tunnel_return_settled.snap`, `hit_014b28.snap`) — no rebuild needed.
  Nothing new was saved this session (only reads: raw hex, `watch`, `bpc`/`bt` register dumps).
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry, `kbd ff 02` reproduces the
  TUNNEL→CAVERN crossing) or `gameplay_empire.snap` (CAVERN, day 1, the zigzag recipe for the
  reverse direction). `hit_014b28.snap` for the specific PC `$014b28`.
- Uncommitted work left behind: none.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`.

- Collision, graphics compositing and the entity/object-verb bytecode interpreter are disassembled
  and documented (`mechanics.md` 1-6, 27).
- Type 3 (not type 8) is the real, populated room table, 72/100 slots (`mechanics.md` §31a).
- The reverse TUNNEL→CAVERN crossing is real and reproducible: `$0144b8` `ScreenFlip_ScanlineCopy`
  fires ~64,000 word-writes on a genuine portal crossing, zero on blocked movement (§31e).
- `$00014a90` fully disassembled (§32a) and its blit source pinned down live (§32b): the source at
  `$014b28` is a **fixed, room-independent address** (`$55b6`), same in both CAVERN and TUNNEL —
  `$014a90` repaints a fixed status/icon-panel element at screen `(272,143)`, not room art.
- **New this session (§33a): `$55b6`'s actual bytes read directly from the snapshot's RAM (not
  through `gfxview.py`'s decoder) are 96 bytes of solid zero** — the blit source for this call is
  blank, consistent with "clear this panel to a default state," not a glyph. Rendered, it's a plain
  black rectangle: not informative as an image, but a real, independently-verified negative result.
- **New this session (§33b): a full-screen-buffer `watch` across a live TUNNEL→CAVERN crossing
  (`watch 19100 32000` + `kbd ff 02`, ~668k hits) was bucketed by PC. Every hit falls into either
  `$0144b8`'s flip (a larger PC range than previously named, `$0144ee`-`$0150d8`) or a second,
  newly-traced masked-blit call (`$007f60`, live-traced via `bpc`+`bt` to `$00d93c`'s `bsr $7dd6`,
  called from the sprite-object-array walk at `A6=$00038338`, §21a's already-known base) — the
  entity/sprite-list renderer, not a new routine.** No third, unidentified writer touched the buffer
  during this crossing.

## Open, in priority order

1. **Where the room's own background art actually gets painted** — now reframed twice over.
   `$014a90` is closed (§32b); the entity/sprite-draw system is now also ruled out (§33b, this
   session) since it draws sprites at their own positions, not a room-sized background, and no
   other PC wrote the buffer during the captured crossing window. Two live possibilities left,
   **try (a) first, it's cheaper and may close the item as a reframe rather than a new hunt**:
   - (a) The background is painted into the *other* (non-visible) screen-buffer role well before
     the crossing — e.g. when the room is first loaded/decoded into memory — and the crossing only
     ever flips an already-painted back buffer. Test: `watch` the non-visible buffer (the
     `ScreenBufferA/B` role-swap field's other half, `4(A5)`'s counterpart per §32a) from well
     before any movement, across an idle period with *no* crossing, and see whether it already
     holds the about-to-be-shown room's art before `$0144b8` ever runs. If confirmed, §31e's
     original premise ("something paints room art each crossing") needs correcting, not the search
     continued.
   - (b) The 34th pass's capture window (`kbd`-press to ~2.2M steps) didn't fully bracket the true
     paint moment — re-run with a wider or earlier-starting watch window if (a) comes back negative.
2. What `$55b6` contains for a *different* transition (§33a only checked the plain crossing this
   and the prior pass both used) — specifically, catch a `$014a90`/`$014b28` call during an actual
   LEVER-proximity transition (§7's "icon panel switches to a lever-specific icon pair") and see
   whether `A0` or the source bytes differ from this session's all-zero default-state read. Lower
   priority than item 1: this is about confirming a side-hypothesis, not the room-art blocker.
3. Room-record bytes `+0..+3` (still unknown; `+4`/`+5` are the graphics-table index, `+$c0` is the
   mask table per §32a).
4. How the ~72 real rooms connect in ordinary play (`$007104` is not it: both branches `bra $69da`,
   §31b).
5. The two-disk original (§30b): lower priority, would be a fresh subject.

## Known traps

- **The Cadaver disk image is not in the usual Dropbox ST-games folder** — it's only on `gpubox`.
  Pull it with the tar-over-ssh recipe (CLAUDE.md) before assuming the workstream is blocked.
- **Prefer `bpc <addr> 1 <maxSteps>` over `bp <addr> <maxSteps>` for a one-shot reliable register
  dump.** Root-caused this session's predecessor pass: not a real `bp` flakiness, `bpc` reproduces
  cleanly every time.
- **`bt <depth>` with `depth` > 1 can throw an unhandled `Atari.AddressError` and kill the REPL
  process** if the return-address chain doesn't follow the A6 link-frame convention past the first
  frame (seen this session reading the entity/sprite-draw call's backtrace — its second "frame" was
  actually entity-record data, not a real link). Use `bt 1` first and only widen the depth once
  you've confirmed the caller actually uses linked A6 frames; don't assume a deeper `bt` is safe to
  request blind.
- `gfxview.py`'s `st-interleaved` layout renders standard 16-pixel word-interleaved planes
  correctly, but this game's masked-blit routines (`$014ee4`/`$007f60`/`$14f4a` family) read source
  data as **4 consecutive longwords per row** (one plane per 32-bit longword, 32 pixels wide, no
  inter-plane stride) — a different in-memory order than word-interleaved for any width other than
  exactly 16px. Rendering one of these blit sources through the HTML viewer's normal controls
  produces noise; read the raw bytes directly from the snapshot instead (see §33a's approach: parse
  the `A68S` header per `gfxview.py`'s own `load_ram()`, then slice `ram[addr:addr+width*rows]`) to
  verify a fixed-address blit source like this workstream keeps finding.
- Movement is joystick port 1 (`kbd ff 01/02/04/08` = up/down/left/right). One packet is a
  self-terminating multi-substep move needing 60k-100k steps.
- Player = sprite-array slot 0 (`$038338`, +42 = 0); `A5 = $18152`.
- Use `tools/find_ram_callers.py` and `tools/find_field_writers.py` for "who calls / writes X".

## Next session

Test possibility (a) from open item 1 first: `watch` the non-visible screen-buffer role from an
idle, pre-crossing state (no `kbd` input at all) and check whether it already holds the next room's
art before any transition starts — if so, reframe the item around *when* that buffer gets painted
(most likely at room-load time, not crossing time) rather than continuing to hunt for a painter that
runs during the crossing itself. Prompt: `/resume cadaver`.
