# Cadaver: handoff

Updated 2026-09-24 by the session that ended at this commit (47th pass). Closed the door-connectivity
Open item 1: walked all 71 door ids referenced across every one of the 72 populated rooms and
resolved each spatially exactly as `$de5e` does — every door lands on its own room or an
edge-adjacent neighbour, zero teleports. Also found and corrected a stale doc claim (door
descriptors are 8 bytes, not 20) and reframed the standing Open item 3 (scripting/bytecode layer):
it isn't a fresh question, `mechanics.md` §22-26 already found and fully proved a real object-verb
bytecode interpreter, closing "does one exist" as yes; what's actually open is narrower (why room
3's own init/registration script never loads).

## Resume point

- Last commit of this workstream: `a312452` "cadaver: close door-connectivity Open item 1, no
  teleport doors exist (47th pass)". A related shared-resource commit, `de384c2` (resume skill:
  re-check a carried-over Open item against later doc sections), landed this same session but is
  not workstream-specific.
- Disk image: `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add`. Present on this Mac checkout.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). No new anchor snapshots this
  pass — `room2_tunnel_entry.snap` (already present) was the only snapshot needed, since §47's walk
  is a static read of game data, not a live test.
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry) or `gameplay_empire.snap` (CAVERN
  start tile) depending on which room's mechanism you're testing next. **Do not use `$5a99` to
  detect "crossing done"** — use `(A5)+1166` (§38b) instead. **Always pass
  `--disk-a "Cadaver...st"` and use `resume <snap> repl`, never the bare alias `rrepl`** — see
  "Known traps" below.
- Uncommitted work left behind: `M68000/sessions/README.md` and `M68000/sessions/powermonger.md`
  still show as modified in `git status` — a concurrent session's workstream, left alone per the
  shared-resources rule (carried over unchanged from prior handoffs).

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` 1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46
(movement collision/proximity mechanism, the icon-panel write chain, the full 72-room
world-map/adjacency graph, the §43 proximity mechanism confirmed generic against a second object,
the shifter-base-flip hardware writer, all fully closed). **New this session, `mechanics.md` §47**:

- **§47.** Closed the door-connectivity Open item 1: `door_walk.py` (promoted from scratchpad to
  `reversing/cadaver/py/` this pass) reads every one of the 72 populated rooms' door-link slots,
  resolves each of the 71 distinct door ids through the type-4 resource table (confirming the
  descriptor is an 8-byte record, correcting §14/§10c's earlier "20 bytes" guess) to a candidate
  world coordinate, then re-implements `$de5e`'s own point-in-rectangle scan (§38d) to find the
  resolved destination room. Result: every door resolves to its own owning room or a
  `world_map.py`-classified `edge`-adjacent neighbour — zero non-adjacent ("teleport") doors, zero
  unresolved ids. The descriptor's secondary id word (positive on 5 of the 71 doors) plays no role
  in the destination — reframed as more likely a "target room resident/registered" gate, consistent
  with §14's already-empty type-8 table and §13's CAVERN-east-door ("already resident") finding.

## Open, in priority order

1. **Whether `world_map.png`'s 72-room graph is one level of several, not the whole game** — Dave's
   observation, 45th pass: the game likely has more than one level, and completing one probably
   reveals another. Narrowed this session (`mechanics.md` §48): `$00b1e0`, the one routine in this
   image that bulk-reloads type 3 (rooms, per §31) from a stream — a plausible "load the next level"
   candidate, §15c — has zero references anywhere in the loaded image by either a direct-call scan
   (`find_ram_callers.py`, §15c) or a new raw-data-pointer scan (`tools/find_literal_ptr.py`, §48b,
   promoted this pass and validated against a known-good target first). Combined with §30a (no
   disk-I/O-capable code anywhere in this image) and §30b (the working tree's two-disk original has
   its disk 2 explicitly labelled "(Level)"), the growing reading is that this one-disk build's
   72-room map probably *is* the whole reachable game — a second level, if it exists for this build
   at all, most likely needs the two-disk original's physical disk-swap path (§30b), not a live
   in-game trigger. **Not settled**: `find_literal_ptr.py` can't see a PC/table-relative-displacement
   jump table (same shape as the verb dispatch table, §24) pointing at `$00b1e0` — that would need a
   different search (compute the displacement from a candidate table base) before this closes for
   good.
2. **Retracted, not just re-scoped: this item was restating a framing (`mechanics.md` §14's empty
   "type-8 room-registration table") that `mechanics.md` §31/§38 had already retired sixteen-plus
   passes before this handoff was written, and §47c (this pass, now corrected in place) briefly
   revived it by mistake before catching and fixing the error against the doc's own later sections.**
   Type 8 was never the room table (§31: type 3 is, 72/100 slots populated); all 72 rooms are already
   resident with no disk I/O anywhere in the image (§30a); and the real door/room-transition mechanism
   (`$de5e`'s spatial point-in-rectangle resolver, the clean current-room field `(A5)+1166`) is fully
   proven end to end (§38, reused directly by this pass's own §47 door walk). Under that model there is
   no unloaded "room 3" left to register, so "why does it never load" isn't a live question. The
   object-verb bytecode interpreter itself is still real and proven (`mechanics.md` §22-26: LOCK/UNLOCK
   confirmed causally on the lever's object id 144), and §26's negative ("nothing in the loaded image
   calls LOCK with id 144") still stands as a fact — but the *reason* attached to it (tied to type-8)
   is invalid. What's still genuinely open, not yet re-examined under the corrected model: whether
   LOCK/UNLOCK simply flips a door descriptor's own open/closed flag (§38c's `btst #0,4(A0)`) on an
   already-resident door rather than "registering" anything, and what the five doors' positive id
   words (`53`,`73`,`155`,`167`,`244` — §47b/§47c) actually encode, since it isn't a room selector and
   isn't a registration gate. No concrete next step scoped yet; lower priority than item 1.
3. **Low priority, not needed to close §46**: which of the other 13 `$ff8201`-touching call sites
   actually fires (title/intro screen, a different room-pair's crossing, a resolution/mode change) —
   §46 closed the conflict without needing this.
4. The two-disk original (§30b): lower priority, would be a fresh subject.

## Known traps

(Unchanged carried-over list — see git history for the full set: `ScreenBufferA/B` role-swap
framing is wrong, `movem` block-copy chunk reversal, `watch`'s step= counter is a lifetime counter
not local, one-shot breakpoint chase non-reproducibility across separate invocations, re-disassemble
elided `...` excerpts in full, `bpc` over `bp` for one-shot dumps, `bt depth>1` can crash the REPL,
a `watch` range can bracket multiple regions in one call, `gfxview.py`'s `st-interleaved` assumes
16px-wide masked blits (not this game's 32px-wide family), movement is joystick port 1, player =
sprite slot 0, use `tools/find_ram_callers.py`/`find_field_writers.py`/`find_literal_ptr.py`.)

- **`run.ps1`'s subcommand names are aliases, not raw argv — the raw binary only understands
  `resume <snap> repl [--disk-a <path>]` (two tokens), not `rrepl <snap>`.** Calling the raw
  `dotnet exec` binary with an alias name silently matches no argv pattern and falls through to a
  disk-less cold boot, which then sits forever in an early ROM wait loop (`$00fc01a0`-`$00fc01d4`,
  identical PC across repeated `s` calls regardless of which snapshot was named). This looks exactly
  like a stuck or corrupted snapshot — blank `snap_render.py` output, `bpc` never hitting even after
  millions of steps — until you reproduce a *known-good* prior result (e.g. §43's documented step
  count) with the correct argv and it works. Now also in `CLAUDE.md`'s Rules section; this entry can
  be deleted once a pass confirms nobody's hit it again.
- **`$5a99` is not a room-transition signal.** Use `(A5)+1166` (§38b) instead.
- **Struct field offsets get reused for different meanings at different call sites — but check
  whether an apparent second meaning is actually dead code before concluding it's a real conflict.**
  See §40's `$cd62` case for the worked example.
- **A live snapshot's static memory alone can settle a "what does routine X compute" question**,
  without running the emulator forward, when the routine's inputs are just RAM values already
  sitting in the snapshot.
- **When checking adjacency between inclusive-coordinate rectangles read from game data, a real
  shared boundary is a gap of exactly 1, not an overlap** (§44's classification rule).
- **A `bpc` armed only at the settled boundary can miss a mechanism that fires during the approach**
  — arm it before injecting the movement input, not just at the end state (§41).
- **A one-deep `bt 1` from a `bpc` hit is enough to find a routine's caller and the gating condition
  around the call site** — read the caller's own disassembly rather than chasing a deeper backtrace.
- `gfxview.load_ram(path)` returns `(ram_bytes, base)` — **that order**, not `(base, ram)`.
- `dotnet exec ... resume <snap> repl`'s printed `help` text does not list `kbd`/`mouse`/`disk`
  even though they exist and work (`Program.fs` line ~1396).
- The REPL's `watch <addr> <len>` parses `<len>` as plain **decimal**, not hex.
- `kbd`/other REPL input commands only *enqueue* IKBD bytes for delivery during subsequent `s`/`bp`/
  `bpc` steps — issue them **before** the step/breakpoint command that should consume them.
- **`watch`'s log reports the exact address each write landed at** — filter a coarse watch range by
  exact address/PC afterward rather than trying to watch a tight, possibly non-contiguous, region.
- **A continuously-firing PC group in a `watch` log is very likely the known full-buffer copy/flip
  routine, not new content** — group hits by PC first and prioritise the rare groups.
- `bt` with no depth argument defaults to depth 8 and reliably crashes the REPL process — always
  pass `bt 1`.
- **If you ever need to hand-parse a `.snap`'s header instead of using `tools/gfxview.py`'s
  `load_ram`/`load_video_regs`/`snapshot_regs`: `cpu.CCR` is written as an int16, not a byte**
  (`Program.fs` `SaveState`'s `w.Write(cpu.CCR)` — `CCR` is F# `int16`), so the RAM-length field
  that follows sits 1 byte later than a naive "19 regs + 1-byte CCR" read expects; getting this
  wrong desyncs every field after it (46th pass, cost real time before `gfxview.py`'s own helpers
  were found and reused instead of re-deriving the format).

## Next session

Item 1 (whether the world map is one level of several) is still the standing priority, now narrowed
by this session's `$00b1e0`/`find_literal_ptr.py` finding rather than closed — the open half is
whether a PC/table-relative jump table (not a plain literal) reaches `$00b1e0`, or whether to treat
the one-disk build as settled to its 72 rooms and pivot to the two-disk original (§30b) as a fresh
investigation. Item 2 no longer has a scoped next step (see its entry above — the "type-8
registration" framing it used to point at is retracted); if it's picked up again, start from
re-scoping it under the type-3/§38 model, not from `$4c536`. Prompt: `/resume cadaver`.
