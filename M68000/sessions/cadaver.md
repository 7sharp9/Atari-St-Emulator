# Cadaver: handoff

Updated 2026-09-24 by the session that ended at this commit (39th pass). **Closed Open item 1**
(what writes new room art during a crossing) and **Open item 4** (room connectivity — it's a
spatial point-in-rectangle scan over the room table, not a graph, proven live end-to-end), all
written up in `mechanics.md` §37/§38 and folded into the README's "Next steps". Also corrected two
prior-pass claims about `$5a99` and the shifter base.

## Resume point

- Last commit of this workstream before this pass: `679c28d` "cadaver handoff after the (A5)+0
  live-flip correction and inactive-half watch (38th pass)".
- Disk image: `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add`. Present on this Mac checkout,
  no rebuild needed.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). All snapshots from prior
  handoffs still present. New this session (all reproducible from `room2_tunnel_entry.snap`,
  kept for convenience):
  - `watch_wide_crossing.snap` / `watch_wide.log`: full 8.2M-step `kbd ff 02` crossing with
    `watch 19100 64256` (covers both display halves in one call). 5,635,133 write events,
    237 distinct writer PCs.
  - `burst_end.snap`: snapshot right as `$0150b4`'s room-paint burst ends (`mechanics.md` §37c) —
    both display halves already ≈98% match the CAVERN reference here.
  - `watch_cache.log`, `watch_28c00.log`, `watch_5a99.log`, `watch_shifter.log` (zero writes),
    `idle_no_crossing.snap` (no-input control), `bba8_regs.log`, `watch_objcount` samples (watches
    `(A5)+1152`, the object-array population counter — confirmed grown one-at-a-time by
    `$0000ce2e`).
  - `full_10000_40000.asm`, `full_8000_10000.asm`, `full_40000_90000.asm`: whole-range linear
    disassembly dumps used to find `$144b8`'s only two callers; regenerable, not load-bearing.
  - Drive scripts for all of the above, plus the `$0150b4`/`$0000bba8`/`$0000de5e` register-capture
    and `hits`-census scripts used throughout — all named `drive_*.txt`, self-documenting.
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry), same `kbd ff 02` crossing recipe.
  **Do not use `$5a99` to detect "crossing done"** — use `(A5)+1166` (§38b, a clean single-write
  current-room-slot index: `1`=TUNNEL, `0`=CAVERN) instead.
- Uncommitted work left behind: none (this handoff, `reversing/cadaver/mechanics.md`, and
  `reversing/cadaver/README.md` are all committed with this session's work).

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` 1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35, 36. **New this session, `mechanics.md`
§37-38** (landed and written up, not leads):

- **§37 — the room painter.** A crossing re-populates the shared entity/object array (`56(A5)`,
  §21a) from the new room's own object list via a newly-found routine `$00cd50`-`$00cee0`, and the
  already-documented per-frame visible-object walker (§33b/34b's `$00d800`) then draws every
  newly-active object once through the ordinary masked-blit entity renderer (`$0150b4`-family) —
  the same pipeline used for real moving entities every frame, just invoked ~4,066 times in one
  burst. Proven: a snapshot at the burst's end (under 13% into the crossing) already matches the
  CAVERN reference to ≈98% in both display halves, vs ~18,300/32,000 bytes different at the start;
  a no-input idle control changes nothing over the same step count.
- **§38a — the resource manager decoded.** `(A5)+96` points to 18-byte type records
  (`[+0 index-table][+4 data-area][+16 count]`); `bsr $c5a8`/`$c52c`-family routines look up
  `(type, index)` pairs through it. Type 3 (100 slots, 72 populated) *is* the room table §31a
  already found from a different angle — its data area is exactly `(A5)+164`'s CAVERN address.
  Type 6 (1000 slots) is the object-template pool §37 uses. Byte-exact: **CAVERN is room slot 0**,
  **TUNNEL is room slot 1** (decoded from the type-3 index table's offsets).
- **§38b — `(A5)+1166` is the real "current room" field.** `1` in TUNNEL, `0` in CAVERN, matching
  the slot numbers exactly. A `watch` over the full crossing shows **exactly one write** (not
  toggling like `$5a99`), at `$0000727c`.
- **§38c/d — the door/portal resolver found and proven live, with an unexpected structure.**
  `$0000727c` sits inside `$007250`-`$0072c2`, which reads a door descriptor, calls `$0000de5e` to
  resolve it to a target room slot, and commits `(A5)+1166` if different — this is the
  room-transition trigger `mechanics.md` has been looking for since §9/§31b. **`$de5e` itself is
  not a graph/exit-table lookup — it's a spatial point-in-rectangle scan over every type-3 room
  record**, testing a world coordinate against each room's bounding box (fields `+1`/`+3` = x0/y0,
  `+4`/`+5` = width/height) until one contains the point. TUNNEL's rect `[19,12]`-`[22,17]` and
  CAVERN's rect `[12,18]`-`[22,28]` are adjacent and touch exactly where the two rooms connect.
  **Proven live, end to end**: `bpc 727c 1` (the exact commit instruction) during the crossing
  shows `D6=0` (CAVERN's slot) with `D0=$14,D1=$11` (world coordinate `20,17`, on the shared
  boundary edge) right before it writes `(A5)+1166`. **Conflicts with §32a's existing claim that
  record `+4`/`+5` are "the graphics-table index"** — not reconciled, see Open item 2.

## Open, in priority order

1. **Reconcile §38d's room-record `+4`/`+5` = width/height against §32a's claim that they're "the
   graphics-table index".** One of the two is wrong, or they describe different record variants.
   Check against a room whose graphics-table index is independently known.
2. Identify room-record byte `+4` read into D6 *before* the object-population loop at `$cd62` (a
   separate `bsr $c5a8` call with `D0=5`, different from the `+4`/`+5` bounding-box fields §38d
   found — the field number is reused for two different purposes at two different call sites in
   the routine; check carefully which `+4` read is which before conflating them).
3. What `$55b6` contains for a *different* transition (e.g. an actual LEVER-proximity icon-panel
   change, §7) — still zero-checked, only the plain crossing has been tried.
4. Reconcile the shifter-base-flip conflict: this session's 4 independent checks never saw the
   base flip in one `kbd ff 02` crossing (`watch ffff8200 8` logged zero writes), but two older
   scratch snapshots (`watch_crossing_end.snap`, `mid_bank_copy.snap`) read shifter base `$19100`
   via the same `gfxview.py` helper. Not reconciled: either those came from a longer/different
   recipe, or a different crossing entirely.
5. The two-disk original (§30b): lower priority, would be a fresh subject.
6. Walk the full type-3 room table (72 populated slots) and decode every room's bounding-box
   rectangle (§38d's fields) to build the complete world map / room-adjacency graph implied by the
   now-proven spatial resolver — would settle "how do all ~72 rooms connect" beyond the one
   TUNNEL/CAVERN pair checked this session.

## Known traps

(Unchanged from the prior handoff except the new entries at the end — see that file's git history
for the full carried-over list: `ScreenBufferA/B` role-swap framing is wrong, `movem` block-copy
chunk reversal, `watch`'s step= counter is a lifetime counter not local, one-shot breakpoint chase
non-reproducibility across separate invocations, re-disassemble elided `...` excerpts in full,
`bpc` over `bp` for one-shot dumps, `bt depth>1` can crash the REPL, a `watch` range can bracket
multiple regions in one call, `gfxview.py`'s `st-interleaved` assumes 16px-wide masked blits (not
this game's 32px-wide family), movement is joystick port 1, player = sprite slot 0, use
`tools/find_ram_callers.py`/`find_field_writers.py`.)

- **`$5a99` is not a room-transition signal.** It's local scratch state for `$0000bba8` and
  toggles on and off within ~1,200 steps every time that one wrapper runs (4 times per crossing,
  not sticky). Use `(A5)+1166` (§38b, a clean single-write current-room-slot index) instead.
- **Struct field offsets get reused for different meanings at different call sites in the same
  routine** — `$00cd50`'s own object-population loop reads a byte at record `+4` for one purpose
  (feeds a `D0=5` resource lookup, Open item 3), while `$0000de5e`'s bounding-box test reads `+4`
  for a completely different one (rectangle width). Don't assume a field offset found in one
  routine's context carries over to another without checking both reads independently.
- **`hits <n> <addr>...` is the fast way to check "is this routine crossing-specific or ambient"**
  before spending a `watch` run on it — run once from a steady-gameplay snapshot with no input and
  once across a crossing; 0-vs-nonzero is immediate and cheap.
- **A "first writer per differing byte" analysis beats reasoning about destination-address ranges
  or "last writer" alone.** Computing, in Python, the *first* write (per byte, from a `watch` log)
  that moves a value away from its baseline-snapshot value cut straight through 237 candidate PCs
  to the one family responsible for ~31% of the real content change. Pattern: load both snapshots
  with `gfxview.load_ram`, diff byte-for-byte, regex-parse the `watch` log's `WATCH: step=...
  pc=$... Write... $addr <- $val` lines, and track running per-byte state to find the first change
  per address.
- `gfxview.load_ram(path)` returns `(ram_bytes, base)` — **that order**, not `(base, ram)`.
- `dotnet exec ... resume <snap> repl`'s printed `help` text does not list `kbd`/`mouse`/`disk`
  even though they exist and work (`Program.fs` line ~1396) — check the `parts.[0] = "<cmd>"`
  match arms, not `help`'s one-line summary, before concluding a command is missing.
- The REPL's `watch <addr> <len>` parses `<len>` as plain **decimal**, not hex (`watch 20e00 7d00`
  throws; use `watch 20e00 32000`). Only `<addr>` is hex.

## Next session

Start with Open item 1: reconcile §38d's room-record `+4`/`+5` (proven this session as x/y
width/height for the spatial room-boundary test) against §32a's older claim that the same offsets
are a graphics-table index — check both against a room whose graphics-table index is independently
known. Item 6 (decode the full 72-room table into a world map) is the natural follow-up once that's
settled. Prompt: `/resume cadaver`.
