# Cadaver: handoff

Updated 2026-09-24 by the session that ended at this commit (43rd pass). Closed the open item the
42nd pass left standing: traced `$009440`'s caller (live `bpc`/`bt`) to the per-frame movement
handler, then read `$008870` (the movement collision test) in full and found it builds the
nearby-object list in-line, via a per-room bounding-box overlap scan of the room's object-placement
table against the candidate move position — proximity here is the same rectangle test already used
to decide whether a step is blocked, not a separate distance routine.

## Resume point

- Last commit of this workstream: `f290d2f` "cadaver: close open item 1 - $008870 builds $009440's
  nearby-object list (43rd pass)".
- Disk image: `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add`. Present on this Mac checkout.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). No new snapshots this pass —
  reused `room2_tunnel_entry.snap` (fresh TUNNEL entry) with the same `kbd ff 04` Left-hold recipe
  as the 42nd pass.
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry) or `room2_lever_boundary_new.snap` for
  lever-proximity work directly. **Do not use `$5a99` to detect "crossing done"** — use
  `(A5)+1166` (§38b) instead.
- Uncommitted work left behind: none of this session's own. `M68000/sessions/README.md` and
  `M68000/sessions/powermonger.md` show as modified in `git status` but were not touched by this
  session — they belong to a concurrent session's workstream and were left alone per the
  shared-resources rule.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` 1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35, 36, 37, 38, 39, 40, 41, 42 (the `+4`/`+5`
width/height thread, `$014a90`'s room-crossing-only scope, and the LEVER-proximity icon-panel write
chain down to `$009440`/`$00946a`, all fully closed). **New this session, `mechanics.md` §43**:

- **§43.** Closed §42's remaining open item: what builds the object-index list fed to `$009440`'s
  `(A0)`. Live `bpc 009440 1 250000` + `bt 1` from `room2_tunnel_entry.snap` (same Left-hold input)
  traced the caller to `$0073b2`, inside the per-frame movement handler, reached only when
  `jsr $008870.l` (the movement collision test, called with D0/D1 = the candidate new position)
  returns a non-blocked result. Full disassembly of `$008870` shows it builds `92(A5)`'s list itself
  as a side effect: a bounding-box overlap scan of the room's object-placement table (`56(A5)`,
  stride `$46`, count `1152(A5)`) against a margin box derived from the candidate position, appending
  each in-range object's placement pointer (`10(A6)`) and a running count into the same `92(A5)`
  buffer `$009440` later reads (`move.b (A0),D7` = the count, `movea.l (A0)+,A6` per entry). No
  separate distance/proximity routine exists — proximity is the same rectangle test the game
  already uses to decide whether a step is blocked. Proof: live register capture confirming the
  call site and pointer identity, plus full disassembly of both routines' header/count/pointer
  layout agreeing byte-for-byte.

## Open, in priority order

1. What `$55b6` contains for a *different* object's proximity transition (e.g. CAVERN's BOAT, 11th
   pass) — untested; would show whether §43's bounding-box-scan mechanism is generic across objects
   or has per-object special-casing. Lower priority now that the mechanism itself is proven generic
   (it iterates the whole room object table, not a per-object special path), but not directly
   checked against a second object.
2. Reconcile the shifter-base-flip conflict: 4 independent checks (39th pass) never saw the base
   flip in one `kbd ff 02` crossing (`watch ffff8200 8` logged zero writes), but two older scratch
   snapshots (`watch_crossing_end.snap`, `mid_bank_copy.snap`) read shifter base `$19100` via the
   same `gfxview.py` helper. Not reconciled: either those came from a longer/different recipe, or a
   different crossing entirely.
3. The two-disk original (§30b): lower priority, would be a fresh subject.
4. Walk the full type-3 room table (72 populated slots) and decode every room's bounding-box
   rectangle (§38d) to build the complete world map / room-adjacency graph implied by the now-proven
   spatial resolver (§39) — would settle "how do all ~72 rooms connect" beyond the one TUNNEL/CAVERN
   pair checked so far. This is now the highest-value big-ticket item: the width/height field, its
   `$5a10`-derived screen layout, the spatial door resolver, and the proximity-icon-panel mechanism
   (§42/§43) are all proven and closed.

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
  sitting in the snapshot. Cheaper than `callcap`/`bpc` when it applies.
- **A `bpc` armed only at the settled boundary can miss a mechanism that fires during the approach,
  not at the final position** — §41's key methodological fix over §32b/§33 was arming the
  breakpoint *before* injecting the movement input that drives the whole approach, not just at the
  end state. When re-testing "does routine X fire for event Y", cover the whole transition window,
  not just the post-transition snapshot.
- **A one-deep `bt 1` from a `bpc` hit is enough to find a routine's caller and the gating condition
  around the call site** — read the caller's own disassembly around the return address rather than
  chasing a deeper backtrace; `bt` with depth > 1 reliably crashes the REPL on this game anyway
  (§43 found `$008870` this way in two REPL round-trips).
- `gfxview.load_ram(path)` returns `(ram_bytes, base)` — **that order**, not `(base, ram)`.
- `dotnet exec ... resume <snap> repl`'s printed `help` text does not list `kbd`/`mouse`/`disk`
  even though they exist and work (`Program.fs` line ~1396) — check the `parts.[0] = "<cmd>"`
  match arms, not `help`'s one-line summary, before concluding a command is missing.
- The REPL's `watch <addr> <len>` parses `<len>` as plain **decimal**, not hex (`watch 20e00 7d00`
  throws; use `watch 20e00 32000`). Only `<addr>` is hex.
- `kbd`/other REPL input commands only *enqueue* IKBD bytes for delivery during subsequent `s`/`bp`/
  `bpc` steps — issue them **before** the step/breakpoint command that should consume them, not
  after; queuing input after a `bpc` call wastes that call's whole step budget on the pre-input
  state (hit this pass rebuilding `room2_lever_boundary_new.snap`).
- **`watch`'s log reports the exact address each write landed at, so a "coarse" watch range
  (covering both live screen-buffer candidates, or a whole UI strip wider than the true target) is
  fine to arm** — filter the resulting hit log by exact address/PC afterward rather than trying to
  pre-compute a minimal contiguous byte range. A tight rectangular pixel bbox is *not* contiguous in
  planar screen memory once it spans more than one row (each row is a fixed 160-byte stride with
  unrelated columns in between), so don't try to watch "just the bbox" as one range spanning
  multiple rows — watch the enclosing full-row range (or the whole screen) and filter by
  `(addr - base) % row_bytes` afterward instead (§42).
- **A continuously-firing PC group in a `watch` log (thousands of hits) is very likely the known
  full-buffer copy/flip routine, not new content** — group hits by PC first and prioritise the rare
  groups (tens of hits, not thousands) as the actual event-driven writer (§42 found the real icon
  writer this way, buried under the `$014696`-family buffer copy's much higher hit count).
- `bt` with no depth argument defaults to depth 8 and reliably crashes the REPL process on this
  game (confirmed again this pass) — always pass `bt 1` (or just read the return address off the
  `bpc` hit's own register dump / stack) when only the immediate caller is needed.

## Next session

Item 4 (decode all 72 rooms' rectangles into a world map) is now the highest-value target: the
spatial resolver, lookup tables, and the proximity-icon-panel mechanism are all proven mechanisms
with nothing else blocking it. Item 1 (cross-check §43's mechanism against a second object, e.g.
CAVERN's BOAT) is a cheap sanity check if a quick session is wanted first. Prompt: `/resume cadaver`.
