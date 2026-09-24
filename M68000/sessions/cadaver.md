# Cadaver: handoff

Updated 2026-09-24 by the session that ended at this commit (44th pass). Closed Open item 4: walked
the type-3 resource-manager table and decoded every populated room's world-grid rectangle, building
the full room-adjacency graph and confirming the spatial point-in-rectangle resolver (§38d) is
generic across the whole game, not a two-room coincidence.

## Resume point

- Last commit of this workstream: `ddb551c` "cadaver: decode all 72 rooms into a full world map
  (44th pass)".
- Disk image: `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add`. Present on this Mac checkout.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). No new snapshots needed this
  pass — `py/world_map.py` reads the resource-manager table directly from `room2_tunnel_entry.snap`
  (static game data, no emulator run required).
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry) or `room2_lever_boundary_new.snap` for
  lever-proximity work directly. **Do not use `$5a99` to detect "crossing done"** — use
  `(A5)+1166` (§38b) instead.
- Uncommitted work left behind: none of this session's own. `M68000/sessions/README.md` and
  `M68000/sessions/powermonger.md` still show as modified in `git status` — a concurrent session's
  workstream, left alone per the shared-resources rule (carried over from the last two handoffs
  unchanged).

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` 1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35, 36, 37, 38, 39, 40, 41, 42, 43 (the `+4`/`+5`
width/height thread, `$014a90`'s room-crossing-only scope, the LEVER-proximity icon-panel write
chain down to `$009440`/`$00946a`/`$008870`, all fully closed). **New this session, `mechanics.md`
§44**:

- **§44.** Closed Open item 4 (world map / room-adjacency graph): `py/world_map.py` walks all 100
  type-3 index-table slots (base `$4ac36`) and reads each populated slot's rectangle
  (`x0=+1,y0=+3,w=+4,h=+5`) off its record at `$6bf0a + offset`. **72/100 populated**, matching
  §38a's count exactly. Checking every pair of the 72 rectangles found **zero overlaps** — §38d's
  "non-overlapping rectangles on a shared world grid" claim, previously checked for only the
  TUNNEL/CAVERN pair, now holds for all 72. 99 pairs share a boundary edge (candidate
  doors/crossings), 18 touch only at a corner. TUNNEL/CAVERN's known edge (§38d) reproduces exactly
  as one case of the general script. Rendered map committed: `world_map.png`. Proof: script output
  (72/100 populated, 0/2556 overlapping pairs) plus the rendered map matching §38d's by-hand
  TUNNEL/CAVERN geometry.

## Open, in priority order

1. What `$55b6` contains for a *different* object's proximity transition (e.g. CAVERN's BOAT, 11th
   pass) — untested; would show whether §43's bounding-box-scan mechanism is generic across objects
   or has per-object special-casing. Lower priority — the mechanism itself is proven generic (it
   iterates the whole room object table, not a per-object special path) — but not directly checked
   against a second object.
2. Reconcile the shifter-base-flip conflict: 4 independent checks (39th pass) never saw the base
   flip in one `kbd ff 02` crossing (`watch ffff8200 8` logged zero writes), but two older scratch
   snapshots (`watch_crossing_end.snap`, `mid_bank_copy.snap`) read shifter base `$19100` via the
   same `gfxview.py` helper. Not reconciled: either those came from a longer/different recipe, or a
   different crossing entirely.
3. The two-disk original (§30b): lower priority, would be a fresh subject.
4. ~~Walk the full type-3 room table and decode every room's bounding-box rectangle~~ — **done, 44th
   pass, §44.** Now that the full 72-room adjacency graph exists, the next-order question (not yet
   scoped as an open item) is whether the door-descriptor bytes read at `$007250`/`$de5e` (§38c) ever
   select a *non-adjacent* target — i.e. whether every real portal in the game connects rectangles
   that are already edge-adjacent in the map, or whether some doors "teleport" across the grid. Would
   need a walk of every room's door-descriptor list (not yet located generically — only TUNNEL's two
   entries are known, §15th pass) cross-referenced against `world_map.png`'s adjacency graph.

## Known traps

(Unchanged from the prior handoff — see git history for the full carried-over list:
`ScreenBufferA/B` role-swap framing is wrong, `movem` block-copy chunk reversal, `watch`'s step=
counter is a lifetime counter not local, one-shot breakpoint chase non-reproducibility across
separate invocations, re-disassemble elided `...` excerpts in full, `bpc` over `bp` for one-shot
dumps, `bt depth>1` can crash the REPL, a `watch` range can bracket multiple regions in one call,
`gfxview.py`'s `st-interleaved` assumes 16px-wide masked blits (not this game's 32px-wide family),
movement is joystick port 1, player = sprite slot 0, use `tools/find_ram_callers.py`/
`find_field_writers.py`.)

- **`$5a99` is not a room-transition signal.** Use `(A5)+1166` (§38b) instead.
- **Struct field offsets get reused for different meanings at different call sites — but check
  whether an apparent second meaning is actually dead code before concluding it's a real conflict.**
  See §40's `$cd62` case for the worked example.
- **A live snapshot's static memory alone can settle a "what does routine X compute" question**,
  without running the emulator forward, when the routine's inputs are just RAM values already
  sitting in the snapshot. Cheaper than `callcap`/`bpc` when it applies — §44's whole-world-map decode
  needed zero emulator steps, just one snapshot read.
- **When checking adjacency between inclusive-coordinate rectangles read from game data, a real
  shared boundary is a gap of exactly 1, not an overlap.** §38d's TUNNEL/CAVERN pair sits with
  CAVERN's `y0` one past TUNNEL's `y1` (`17`/`18`) — a naive `a.y0 <= b.y1` overlap test misses every
  real edge-adjacent pair. Classify `min(a.x1,b.x1) - max(a.x0,b.x0)` (and the y equivalent): `>= 0`
  on both axes is true overlap, `== -1` on both is a corner touch, `== -1` on exactly one with `>= 0`
  on the other is a real shared edge (§44, `py/world_map.py`'s `adjacency()`).
- **A `bpc` armed only at the settled boundary can miss a mechanism that fires during the approach,
  not at the final position** — §41's key methodological fix over §32b/§33 was arming the
  breakpoint *before* injecting the movement input that drives the whole approach, not just at the
  end state. When re-testing "does routine X fire for event Y", cover the whole transition window,
  not just the post-transition snapshot.
- **A one-deep `bt 1` from a `bpc` hit is enough to find a routine's caller and the gating condition
  around the call site** — read the caller's own disassembly around the return address rather than
  chasing a deeper backtrace; `bt` with depth > 1 reliably crashes the REPL on this game anyway.
- `gfxview.load_ram(path)` returns `(ram_bytes, base)` — **that order**, not `(base, ram)`.
- `dotnet exec ... resume <snap> repl`'s printed `help` text does not list `kbd`/`mouse`/`disk`
  even though they exist and work (`Program.fs` line ~1396) — check the `parts.[0] = "<cmd>"`
  match arms, not `help`'s one-line summary, before concluding a command is missing.
- The REPL's `watch <addr> <len>` parses `<len>` as plain **decimal**, not hex (`watch 20e00 7d00`
  throws; use `watch 20e00 32000`). Only `<addr>` is hex.
- `kbd`/other REPL input commands only *enqueue* IKBD bytes for delivery during subsequent `s`/`bp`/
  `bpc` steps — issue them **before** the step/breakpoint command that should consume them, not
  after.
- **`watch`'s log reports the exact address each write landed at, so a "coarse" watch range is fine
  to arm** — filter the resulting hit log by exact address/PC afterward. A tight rectangular pixel
  bbox is *not* contiguous in planar screen memory once it spans more than one row, so watch the
  enclosing full-row range (or whole screen) and filter by `(addr - base) % row_bytes` afterward.
- **A continuously-firing PC group in a `watch` log (thousands of hits) is very likely the known
  full-buffer copy/flip routine, not new content** — group hits by PC first and prioritise the rare
  groups.
- `bt` with no depth argument defaults to depth 8 and reliably crashes the REPL process — always
  pass `bt 1`.

## Next session

Item 1 (cross-check §43's proximity mechanism against a second object) is the cheapest next step.
The world-map decode (item 4, now closed) opens a new, not-yet-scoped question: whether every real
door connects only edge-adjacent rectangles, or whether some "teleport" across the grid — worth
scoping as a new open item if pursued. Prompt: `/resume cadaver`.
