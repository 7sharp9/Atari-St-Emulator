# Cadaver: handoff

Updated 2026-09-24 by the session that ended at this commit (42nd pass). Traced the LEVER-proximity
icon-panel write end to end: a generic nearby-object hint scan (`$009440`/`$00946a`) builds the icon
list (`2303(A5)`/`$5ff6`), the same field driving the "LEVER" status-bar name; an input-driven
diff-redraw (`$00958e`→`$00bbd4`/`$00bca0`) then paints only the changed slots through the same
shared masked-blit primitive `$014a90` also uses for its own, unrelated room-crossing repaint.
Closes the open item the 41st pass left standing.

## Resume point

- Last commit of this workstream: `85cf7f9` "cadaver: close open item 1 - $014a90/$014b28 never fire
  for a same-room LEVER-proximity icon change (41st pass)". This pass's own findings (`mechanics.md`
  §42) are not yet committed — see "Uncommitted work left behind".
- Disk image: `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add`. Present on this Mac checkout.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). New this pass:
  `room2_lever_boundary_new.snap`, rebuilt from `room2_tunnel_entry.snap` because the original
  `room2_lever_boundary.snap` was missing on this Mac checkout (per-machine scratchpad split, not
  yet indexed in `scratchpad/ANCHORS.md` for cadaver at all — worth adding if this recurs).
  Rebuild recipe: hold Left (`kbd ff 04`) ~1.2-1.5M steps from `room2_tunnel_entry.snap` (13th
  pass's recipe, `mechanics.md` §41/README 13th-pass entry).
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry, same as before) or the new
  `room2_lever_boundary_new.snap` for lever-proximity work directly.
  **Do not use `$5a99` to detect "crossing done"** — use `(A5)+1166` (§38b) instead.
- Uncommitted work left behind: none (docs and this handoff are all committed).

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` 1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35, 36, 37, 38, 39, 40, 41 (the `+4`/`+5`
width/height thread, and `$014a90`'s room-crossing-only scope, both fully closed). **New this
session, `mechanics.md` §42**:

- **§42.** Traced the LEVER-proximity icon-panel write end to end via `watch` (restricted to the
  icon-box pixel bbox found by a raw-pixel diff of the idle vs. proximity renders) plus `bpc`/`bt`
  and a `hits` census of candidate call sites. The actual chain: a generic nearby-object hint scan
  (`$009440`, walks a caller-supplied object-index list, skips objects with bit 6 of `12(A4)` set)
  feeds `$00946a`, which sets the icon-panel table pointer, updates the status-bar name-id
  (`10(A4)` vs `1222(A5)` — **the same field driving "LEVER"/"TUNNEL" text**, confirming §7's paired
  behaviour is one write path) and builds the icon-index list (`2303(A5)`/`$5ff6`) from the object's
  type bits plus a verb→icon lookup table at `$5c1c`. An input-event dispatcher (`$00958e`, gated on
  `2499(A5)` bit 1) then calls a diff-based redraw (`$00bbd4`/`$00bca0`) that repaints only the
  changed panel slots through the *same* shared masked-blit primitive (`$014d7a`→`$0150e2`) that
  `$014a90` also uses for its own, unrelated room-crossing repaint. Confirmed the actual RAM content
  change directly: `2303(A5)` goes `1`→`3` and `$5ff6[0..2]` goes `ff ff ff`→`07 0b 06` between
  `room2_tunnel_entry.snap` and `room2_lever_boundary_new.snap`. Closes the open item cleanly.

## Open, in priority order

1. **What builds the object-index list fed to `$009440`'s `(A0)`** (new, narrower than §42's
   question — the actual room-proximity/distance test that decides an object like LEVER is "nearby"
   in the first place, as opposed to what happens once it's been decided). Likely near the
   collision/obstacle-check code at `$008870` (§7/§14) — not traced this pass. Proof recipe: `hits`
   or `bpc` on `$009440` itself across the same Left-hold approach to catch its caller and read off
   what populates `(A0)`'s object list.
2. What `$55b6` contains for a *different* object's proximity transition (e.g. CAVERN's BOAT,
   11th pass) — untested; would show whether the (now-ruled-out) `$014a90` mechanism's fixed source
   is reused identically for every object or varies. Lower priority than item 1 now that the real
   icon-panel writer (§42) is proven.
3. Reconcile the shifter-base-flip conflict: 4 independent checks (39th pass) never saw the base
   flip in one `kbd ff 02` crossing (`watch ffff8200 8` logged zero writes), but two older scratch
   snapshots (`watch_crossing_end.snap`, `mid_bank_copy.snap`) read shifter base `$19100` via the
   same `gfxview.py` helper. Not reconciled: either those came from a longer/different recipe, or a
   different crossing entirely.
4. The two-disk original (§30b): lower priority, would be a fresh subject.
5. Walk the full type-3 room table (72 populated slots) and decode every room's bounding-box
   rectangle (§38d) to build the complete world map / room-adjacency graph implied by the now-proven
   spatial resolver (§39) — would settle "how do all ~72 rooms connect" beyond the one TUNNEL/CAVERN
   pair checked so far. Remains the highest-value big-ticket item once the proximity-icon-panel
   thread (items 1-2) is settled: the width/height field, its `$5a10`-derived screen layout, and the
   spatial door resolver are all proven mechanisms.

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

Start with the new Open item 1: find what builds the object-index list `$009440` scans (the real
room-proximity/distance test), likely near `$008870`'s collision/obstacle-check code (§7/§14) — a
`bpc`/`hits` on `$009440` itself during the same Left-hold approach from `room2_tunnel_entry.snap`
should catch its caller. Item 5 (decode all 72 rooms' rectangles into a world map) remains the
higher-value target once the proximity-icon-panel thread (items 1-2) is closed, since the spatial
resolver and lookup tables are both proven mechanisms now. Prompt: `/resume cadaver`.
