# Cadaver: handoff

Updated 2026-09-24 by the session that ended at this commit (40th pass). **Fully closed the `+4`/`+5`
width/height thread** (§38d vs §32a/§31c vs §31d's three separate "is this a conflict" questions):
every live read of room-record byte `+4` across the whole traced call graph (`$de5e`, `$e7b0`,
`$00cfc4`'s two sites) agrees it's the room's width, and the one read that looked like a fourth
meaning (`$cd62`) turns out to be dead code.

## Resume point

- Last commit of this workstream: `6d3c6b3` "cadaver: close the \$cd62 open item - dead read, two
  more live +4 sites confirm width (40th pass cont.)".
- Disk image: `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add`. Present on this Mac checkout, no
  rebuild needed.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored) — unchanged this pass, all
  prior-handoff snapshots still present. No new snapshots this pass; both §39 and §40 only needed
  static reads off already-present snapshots (`room2_tunnel_entry.snap`, `burst_end.snap`) plus
  disassembly (`disassemble.py --linear`), no live emulator run.
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry), same `kbd ff 02` crossing recipe.
  **Do not use `$5a99` to detect "crossing done"** — use `(A5)+1166` (§38b) instead.
- Uncommitted work left behind: none (this handoff and `mechanics.md` §39/§40 are all committed).

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` 1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35, 36, 37, 38. **New this session, `mechanics.md`
§39-40**:

- **§39.** `$0000e7b0` disassembled in full: computes `index = (width-3)*2 + (height-3)*16` from
  room-record bytes `+4`/`+5` (§38d's proven bounding-box width/height), indexes a lookup table at
  `$5a10.l`, and writes the result to `(A5)+148` — the field §31c saw written and inferred was an
  independent "quadrant/graphics-table index." Verified against both `room2_tunnel_entry.snap`
  (TUNNEL) and `burst_end.snap` (CAVERN): each snapshot's actual `(A5)+148` matches the computed
  lookup from its own `+4`/`+5` bytes exactly. Not a conflict — reused field, not a second one.
  `$e7b0`'s trailing loop (trip counts `width-1`/`height-1`) builds a per-tile screen-offset table
  at `2634(A5)+`.
- **§40.** Chased §31d's `$cd62` (inside `$00ccfe`, not a separate routine — a fallthrough label)
  read of the same byte `+4`: it's **dead code**, never consumed before the routine's `rts`
  (confirmed by full linear disassembly + grep over the whole `$ccfe`-`$cf80` span). The adjacent
  `$00cfc4` routine reads `+4` twice more, both live and both consistent with "width": `$d09a` uses
  `width+1` as a row-stride multiplier into a table at `84(A5)`; `$d06a` feeds an address
  computation that reads back **§39's own `2634(A5)+` table** — the consumer side of `$e7b0`'s
  screen-offset table, found by chasing this thread. No remaining candidate anywhere in the traced
  call graph for a conflicting reading of `+4`.

## Open, in priority order

1. What `$55b6` contains for a *different* transition (e.g. an actual LEVER-proximity icon-panel
   change, §7) — still zero-checked, only the plain crossing has been tried.
2. Reconcile the shifter-base-flip conflict: 4 independent checks (39th pass) never saw the base
   flip in one `kbd ff 02` crossing (`watch ffff8200 8` logged zero writes), but two older scratch
   snapshots (`watch_crossing_end.snap`, `mid_bank_copy.snap`) read shifter base `$19100` via the
   same `gfxview.py` helper. Not reconciled: either those came from a longer/different recipe, or a
   different crossing entirely.
3. The two-disk original (§30b): lower priority, would be a fresh subject.
4. Walk the full type-3 room table (72 populated slots) and decode every room's bounding-box
   rectangle (§38d) to build the complete world map / room-adjacency graph implied by the now-proven
   spatial resolver — would settle "how do all ~72 rooms connect" beyond the one TUNNEL/CAVERN pair
   checked so far. `$e7b0`'s own `$5a10` table (§39) could be walked the same way to check every
   populated room's `(width,height)` pair maps to a sane, in-range table entry — a cheap sanity
   check on §39's reconciliation before trusting it for rooms other than TUNNEL/CAVERN. This is now
   the natural next big-ticket item: the width/height field, its `$5a10`-derived screen layout, and
   the spatial door resolver are all proven mechanisms — decoding the other 70 rooms' rectangles
   would turn "TUNNEL/CAVERN connect" into "here is the whole map."

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
  Room-record byte `+4` looked, across three separate passes, like it might have up to four
  different meanings (§38d's bounding box, §31c's "graphics index", §31d's "type-5 resource key",
  and a candidate fourth site at `$cd62`). All four collapsed into one: it's the width, read at
  several call sites, one of which (`$cd62`) loads it into a register and never uses the value.
  Before chasing "what's this field's other meaning," grep the full disassembly of the routine
  between the read and its next `rts`/overwrite for any use of the destination register — a read
  with no following use isn't a second meaning at all.
- **A live snapshot's static memory alone can settle a "what does routine X compute" question**,
  without running the emulator forward — reading a room record's raw bytes, hand-computing a
  disassembled routine's arithmetic, and reading the routine's own output field back off the same
  snapshot is enough when the routine's inputs are just RAM values already sitting in the snapshot
  (no register-only intermediate state needed). Cheaper than `callcap`/`bpc` when it applies.
- `gfxview.load_ram(path)` returns `(ram_bytes, base)` — **that order**, not `(base, ram)`.
- `dotnet exec ... resume <snap> repl`'s printed `help` text does not list `kbd`/`mouse`/`disk`
  even though they exist and work (`Program.fs` line ~1396) — check the `parts.[0] = "<cmd>"`
  match arms, not `help`'s one-line summary, before concluding a command is missing.
- The REPL's `watch <addr> <len>` parses `<len>` as plain **decimal**, not hex (`watch 20e00 7d00`
  throws; use `watch 20e00 32000`). Only `<addr>` is hex.

## Next session

Start with Open item 1: check `$55b6`/the icon-panel path for a LEVER-proximity transition (still
untested — everything proven so far is the plain TUNNEL↔CAVERN crossing). Item 4 (decode all 72
rooms' rectangles into a world map, using §38d/§39's now-fully-reconciled width/height field) is the
higher-value target if the priority order changes — it turns three passes of "is this field
consistent" into a complete room-adjacency graph almost for free, since the spatial resolver and the
lookup tables are both proven mechanisms now. Prompt: `/resume cadaver`.
