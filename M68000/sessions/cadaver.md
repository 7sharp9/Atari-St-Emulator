# Cadaver: handoff

Updated 2026-09-24 by the session that ended at commit `92a0c74` (no new mechanics.md-worthy proof
landed this pass; see "Open" below for why).

## Resume point

- Last commit of this workstream: `f831474` "cadaver: 120(A5) is a cache, not the source - $0144b8
  runs backwards to refresh it on crossings" (unchanged this session).
- Disk image: `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add`. Present on this Mac checkout,
  no rebuild needed.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). All snapshots from the prior
  handoff still present. New this session: `watch_crossing_end.snap` (end-of-run state after an
  8M-step `kbd ff 02` crossing from `room2_tunnel_entry.snap`, `$5a99=1` confirming CAVERN reached).
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry). **Re-read `(A5)`, `120(A5)` and
  `$5a99` live — see the correction below, they are not stable even within one continuous run, not
  just across snapshots.**
- Uncommitted work left behind: none (only file changed under version control this session is this
  handoff, committed with it).

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Unchanged this
session — everything below is carried over from the prior handoff (`mechanics.md` 1-6, 27, 31a,
32a/b, 33b/34b, 34a, 35, 36).

## Correction from this session (not yet folded into mechanics.md — needs one more pass to nail down)

- **`(A5)+0` is not a fixed "first half" pointer — it live-flips between (at least) two addresses
  every so often, not just across snapshots.** Read live via `gfxview.py`'s `live screen: base`
  (the shifter's own hardware register, ground truth for what's *displayed*) versus `m <A5> 4`
  (the game's own inactive-half pointer):
  - `room2_tunnel_entry.snap` (TUNNEL, start): `(A5)+0 = $19100` (inactive), shifter base =
    `$20f00` (active).
  - `watch_crossing_end.snap` (CAVERN, after the crossing, 8M steps later): `(A5)+0 = $20f00`
    (inactive), shifter base = `$19100` (active).
  - So the two live addresses observed so far are `$19100` and `$20f00`, and they swap
    active/inactive roles between these two snapshots (ordinary page-flip, expected) — but
    **their difference is `$8200` (33280 bytes), not the documented `$7d00` (32000, `mechanics.md`
    §34a's `adda.l #$7d00,A1`)**. Not yet reconciled: either there's a third region/stride between
    the two halves that the docs don't account for, or `+$7d00` is a real in-code offset that
    doesn't equal "distance between the two observed live pointers" for some reason not yet
    understood (e.g. the two pointers might not always be exactly one buffer-size apart, or my
    two data points are a coincidence of which physical slot each pointer landed in). **Don't
    treat `$7d00` as validated between arbitrary live pointer pairs until this is resolved** — it
    is still correct as the literal immediate in `$0144c2`'s `adda.l #$7d00,A1`, only the
    "distance between the two live (A5)+0 values across a crossing" claim is now in question.
- **120(A5) did not change value across the crossing** (`$2de08` both before and after) — only its
  *contents* change (per §35/36), the pointer itself is stable, unlike `(A5)+0`.

## Open, in priority order

1. **Find what writes new CAVERN art into the display buffer's inactive half.** This session armed
   `watch <freshly-computed (A5)+0+$8200-ish inactive-half address>, 32000` across the *entire*
   `kbd ff 02` crossing (8M steps, ~166 frames, confirmed by `$5a99: 0→1`) and found **no
   unattributed one-off 32000-byte write** — every write in the region was one of:
   - the known per-frame `$0144xx` flip (`ScreenFlip_ScanlineCopy`, dest = whichever half is
     currently inactive, source = `120(A5)`), running once every ~48000 steps (once per VBL),
     continuously, both before and after the crossing — this is *routine* refresh from the
     already-current cache, not new content;
   - a **new, not-yet-identified** smaller recurring copy, same `$0144xx`-family PC pattern (same
     `movem` idiom, fewer chunks: ~246-568 vs the full 571), landing in a ~6900-byte sub-region
     (`$21c98-$27ede` this run) — also periodic, not obviously crossing-specific. Candidate: an
     animated layer (water?) or a secondary sprite using the same block-copy trick. Not chased down
     this session;
   - the already-known sprite/panel blit family (`$007f60`/`$0150b4`/`$0080cc`, and a small new
     panel-write cluster at `$00be46-$00be9e` / `$00d31e`/`$00d350`, all localized to small regions,
     consistent with UI/icon-panel redraw, not room art).
   
   **Conclusion: the actual new-room paint isn't a write into the currently-inactive-at-watch-time
   half at all** — most likely it happens directly into whichever half is inactive *at the exact
   crossing frame*, and since that pointer flips every frame (this session's correction above), a
   flat 8M-step watch on one address range can miss it if the "inactive" role moves between the two
   physical addresses mid-run. **Next concrete step**: single-step frame-by-frame with `bpc $0144b8
   1 <n>` (breaking on next VBL flip) across the crossing, reading `(A5)+0` fresh at *each* stop
   (not once at the start) and re-arming `watch` on whichever address is inactive *right then* —
   or, per the `reverse-engineer-st-game` skill's note that one `watch <lo> <len>` call can bracket
   multiple regions, watch a single span covering both `$19100` and `$20f00`'s 32000-byte extents at
   once (`watch 19100 16800` is too narrow; use `watch 19100 <len covering both>` or two adjacent
   calls, bucketing hits by destination as §33b's "bucket A" trick did) so the flip doesn't matter.
2. What `$55b6` contains for a *different* transition (e.g. an actual LEVER-proximity icon-panel
   change, §7) — still zero-checked, only the plain crossing has been tried.
3. Room-record bytes `+0..+3` (still unknown; `+4`/`+5` are the graphics-table index, `+$c0` is the
   mask table per §32a).
4. How the ~72 real rooms connect in ordinary play (`$007104` is not it: both branches `bra $69da`,
   §31b).
5. The two-disk original (§30b): lower priority, would be a fresh subject.

## Known traps

(Unchanged from the prior handoff except the new entry at the end — see that file's git history for
the full carried-over list: `ScreenBufferA/B` role-swap framing is wrong, `movem` block-copy chunk
reversal, `watch`'s step= counter is a lifetime counter not local, one-shot breakpoint chase
non-reproducibility across separate invocations, re-disassemble elided `...` excerpts in full,
`bpc` over `bp` for one-shot dumps, `bt depth>1` can crash the REPL, a `watch` range can bracket
multiple regions in one call, `gfxview.py`'s `st-interleaved` assumes 16px-wide masked blits (not
this game's 32px-wide family), movement is joystick port 1, player = sprite slot 0, use
`tools/find_ram_callers.py`/`find_field_writers.py`.)

- **`(A5)+0` (the inactive-half pointer) changes value across a single continuous run, not just
  across snapshots — confirmed it flips between `$19100` and `$20f00` across one 8M-step `kbd ff 02`
  crossing.** Don't compute "the inactive half" once at the start of a long watch and assume it
  holds for the whole run; re-read it at each point of interest, or watch a span wide enough to
  cover every value it can take (see Open item 1's `watch` note above).
- `dotnet exec ... resume <snap> repl`'s printed `help` text does not list `kbd`/`mouse`/`disk`
  even though they exist and work (confirmed working, `Program.fs` line ~1396) — don't conclude a
  REPL command is missing just because `help`'s one-line summary omits it; check `Program.fs` for
  the `parts.[0] = "<cmd>"` match arms.
- The REPL's `watch <addr> <len>` parses `<len>` as a plain **decimal** integer, not hex (`watch
  20e00 7d00` throws a `FormatException` on `7d00`; use `watch 20e00 32000`). Only `<addr>` is hex.

## Next session

Start with Open item 1's concrete step: frame-step through the crossing with `bpc $0144b8 1 <n>`
(or two `watch` calls bracketing both `$19100` and `$20f00`'s extents at once) instead of a flat
long-step watch, since this session proved the "inactive half" pointer itself flips mid-run and a
single flat watch window can watch the wrong (currently-active) address for part of the run. Start
from `room2_tunnel_entry.snap`, same `kbd ff 02` recipe (confirmed still reproduces the crossing,
`$5a99: 0→1` within 8M steps). Prompt: `/resume cadaver`.
