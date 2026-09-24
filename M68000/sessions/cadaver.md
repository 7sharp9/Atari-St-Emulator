# Cadaver: handoff

Updated 2026-09-24 by the session that ended at this commit (41st pass). Closed the standing open
item on whether `$014a90`/`$014b28` (the room-crossing icon/status-panel redraw, §32b/§33) is also
what paints the LEVER-specific icon pair on a same-room proximity change — it is not: zero hits
across a full proximity approach that visibly changed the icon panel and status text.

## Resume point

- Last commit of this workstream: `85cf7f9` "cadaver: close open item 1 - $014a90/$014b28 never fire
  for a same-room LEVER-proximity icon change (41st pass)".
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
`mechanics.md` 1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35, 36, 37, 38, 39, 40 (the `+4`/`+5` width/height
thread, fully closed). **New this session, `mechanics.md` §41**:

- **§41.** Rebuilt the missing `room2_lever_boundary.snap` and re-ran the LEVER-proximity approach
  with `bpc 014a90 20 1500000` armed for the *whole* Left-hold approach (not just the settled
  boundary, which is all §32b/§33 ever tested). Zero hits over the full 1.5M-step budget, despite
  the icon panel and status-bar text visibly changing (confirmed by `snap_render.py` + a pixel diff
  of the bottom UI strip against the idle `room2_tunnel_entry.snap` render). Settles that
  `$014a90`/`$014b28` is a room-crossing-only redraw, never invoked by a same-room proximity change
  — closes the original open item cleanly (as "no", not "untested"). The real proximity-icon writer
  is a new, narrower, still-open question (see below).

## Open, in priority order

1. **What actually paints the LEVER-specific icon pair on proximity** (new, from §41's negative).
   §41's pixel diff shows the change lands in the bottom-left icon-box region, distinct from
   `$014a90`'s own confirmed target (272,143) on the right/status side — so this is very likely a
   *different* fixed-position blit, keyed off whatever proximity-detection field the game already
   uses to set the "LEVER" name-hotspot (see `mechanics.md` §7/§14's collision/obstacle-check
   algorithm, `$008870`, for where that detection already lives). Proof recipe: `watch` the
   bottom-left icon-box screen memory region (need its exact screen offset first — diff the two
   renders' raw pixel rows, not just the PNG bbox) across a fresh Left-hold approach from
   `room2_tunnel_entry.snap`, and read off the writer PC(s).
2. What `$55b6` contains for a *different* object's proximity transition (e.g. CAVERN's BOAT,
   11th pass) — untested; would show whether the (now-ruled-out) `$014a90` mechanism's fixed source
   is reused identically for every object or varies, though given item 1's finding this is lower
   priority than finding the real icon writer.
3. Reconcile the shifter-base-flip conflict: 4 independent checks (39th pass) never saw the base
   flip in one `kbd ff 02` crossing (`watch ffff8200 8` logged zero writes), but two older scratch
   snapshots (`watch_crossing_end.snap`, `mid_bank_copy.snap`) read shifter base `$19100` via the
   same `gfxview.py` helper. Not reconciled: either those came from a longer/different recipe, or a
   different crossing entirely.
4. The two-disk original (§30b): lower priority, would be a fresh subject.
5. Walk the full type-3 room table (72 populated slots) and decode every room's bounding-box
   rectangle (§38d) to build the complete world map / room-adjacency graph implied by the now-proven
   spatial resolver (§39) — would settle "how do all ~72 rooms connect" beyond the one TUNNEL/CAVERN
   pair checked so far. This remains the highest-value big-ticket item once items 1-2 (both
   proximity-icon-panel questions) are settled: the width/height field, its `$5a10`-derived screen
   layout, and the spatial door resolver are all proven mechanisms.

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

## Next session

Start with Open item 1: find the LEVER icon-panel's real writer PC via a targeted `watch` on the
bottom-left icon-box screen region (get its exact offset from a raw pixel-row diff first, not just
the PNG bbox) across a fresh Left-hold approach from `room2_tunnel_entry.snap`. Item 5 (decode all
72 rooms' rectangles into a world map) remains the higher-value target once the proximity-icon
questions (items 1-2) are closed, since the spatial resolver and lookup tables are both proven
mechanisms now. Prompt: `/resume cadaver`.
