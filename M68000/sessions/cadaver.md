# Cadaver: handoff

Updated 2026-09-24 by the session that ended at this commit (40th pass). **Closed Open item 1**:
reconciled §38d's proven room-record width/height fields (`+4`/`+5`) against §32a/§31c's older
"quadrant/graphics-table index" claim — they're the same two bytes, read two ways, not a conflict.

## Resume point

- Last commit of this workstream: `245ff07` "cadaver: reconcile §38d width/height against §32a's
  graphics-table-index claim (40th pass)".
- Disk image: `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add`. Present on this Mac checkout, no
  rebuild needed.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored) — unchanged this pass, all
  prior-handoff snapshots still present. No new snapshots this pass; the reconciliation only needed
  static reads off the two already-present snapshots (`room2_tunnel_entry.snap`,
  `burst_end.snap`) plus a disassembly, no live emulator run.
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry), same `kbd ff 02` crossing recipe.
  **Do not use `$5a99` to detect "crossing done"** — use `(A5)+1166` (§38b) instead.
- Uncommitted work left behind: none (this handoff and `mechanics.md` §39 are both committed).

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` 1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35, 36, 37, 38. **New this session, `mechanics.md`
§39**:

- **§39 — Open item 1 closed.** `$0000e7b0` disassembled in full (`(A5)+164`'s current room record,
  bytes `+4`/`+5` read as `D0`/`D1`): the routine computes `index = (width-3)*2 + (height-3)*16`
  from those same two bytes §38d proved are the room's bounding-box width/height, uses it to index a
  lookup table at `$5a10.l`, and writes the result to `(A5)+148` (the field §31c saw written and
  inferred was an independent "quadrant/graphics-table index"). Verified with a static memory read
  off both `room2_tunnel_entry.snap` (TUNNEL: `+4=3,+5=5` → index `$20` → table word `$2d50`) and
  `burst_end.snap` (CAVERN: `+4=10,+5=10` → index `$7e` → table word `$1268`) — both snapshots'
  actual `(A5)+148` values match the computed lookups exactly. There is no second `+4`/`+5`-like
  field; §32a/§31c's reading was directionally right (the value does drive room-shape-dependent
  screen layout, per `$e7b0`'s own trailing loop building a per-tile screen-offset table at
  `2634(A5)+`) but wrong to treat it as independent from §38d's bounding box.

## Open, in priority order

1. Identify room-record byte `+4` read into D6 *before* the object-population loop at `$cd62` (a
   separate `bsr $c5a8` call with `D0=5`, §31d/§37d) — is this the same `+4` byte §38d/§39 decoded as
   "width", reused for a third purpose (a type-5 resource key), or a genuinely different field at a
   different offset in a different record variant? Not yet checked; static read + live `callcap` on
   `$cd62` would settle it.
2. What `$55b6` contains for a *different* transition (e.g. an actual LEVER-proximity icon-panel
   change, §7) — still zero-checked, only the plain crossing has been tried.
3. Reconcile the shifter-base-flip conflict: 4 independent checks (39th pass) never saw the base
   flip in one `kbd ff 02` crossing (`watch ffff8200 8` logged zero writes), but two older scratch
   snapshots (`watch_crossing_end.snap`, `mid_bank_copy.snap`) read shifter base `$19100` via the
   same `gfxview.py` helper. Not reconciled: either those came from a longer/different recipe, or a
   different crossing entirely.
4. The two-disk original (§30b): lower priority, would be a fresh subject.
5. Walk the full type-3 room table (72 populated slots) and decode every room's bounding-box
   rectangle (§38d) to build the complete world map / room-adjacency graph implied by the now-proven
   spatial resolver — would settle "how do all ~72 rooms connect" beyond the one TUNNEL/CAVERN pair
   checked so far. `$e7b0`'s own `$5a10` table (§39) could be walked the same way to check every
   populated room's `(width,height)` pair maps to a sane, in-range table entry — a cheap sanity
   check on §39's reconciliation before trusting it for rooms other than TUNNEL/CAVERN.

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
- **Struct field offsets get reused for different meanings at different call sites in the same
  routine, and even across different routines reading the same record** — `+4`/`+5` alone now has
  two confirmed distinct uses (§38d's bounding-box width/height, §39's `$5a10`-table index derived
  from that same width/height) plus a third, unreconciled candidate (Open item 1 above, `$cd62`'s
  `D0=5` resource-key read). Don't assume a field offset found in one routine's context carries over
  to another without checking both reads independently — but also check whether two readings that
  looked like a conflict are actually the same bytes used two ways, as §39 turned out to be.
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

Start with Open item 1: is `$cd62`'s `D0=5` read of room-record byte `+4` (a type-5 resource-key
lookup, §31d/§37d) the same byte §38d/§39 decoded as "width", or a different offset in a different
record variant? A static read of the CAVERN/TUNNEL records at that exact byte, cross-checked against
`$cd62`'s own disassembly and a live `callcap $cd62` dump, would settle it the same way §39 settled
the `+4`/`+5` question. Item 5 (decode the full 72-room table, and sanity-check §39's `$5a10` table
against every populated room) is the natural follow-up once that's clean. Prompt: `/resume cadaver`.
