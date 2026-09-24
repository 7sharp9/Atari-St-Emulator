# Cadaver: handoff

Updated 2026-09-24 by the session that ended at this commit (48th pass). Fixed a doc error made
earlier this same session (`mechanics.md` §47c briefly revived a "type-8 room-registration" reading
that §31/§38 had already retired sixteen-plus passes earlier — caught on a re-read, corrected in
place), then narrowed Open item 1 (is the 72-room map one level of several): `$00b1e0`, the routine
that reloads room data from a stream and the only plausible "load the next level" candidate in this
image, is unreferenced by every static technique this spike has — direct call, raw data pointer, and
(new this pass) a displacement-style jump table. Promoted two new tools
(`find_literal_ptr.py`/`find_jump_table_hit.py`) and documented the escalation, plus the doc-writing
lesson, in the `reverse-engineer-st-game` skill and `CLAUDE.md`.

## Resume point

- Last commit of this workstream: `3539ba1` "cadaver: rule out a displacement-style jump table
  reaching $00b1e0 too (48th pass, §48c)". Two related shared-resource commits landed this same
  session but are not workstream-specific: `e5034c6` (first half of the doc fix + `find_literal_ptr.py`,
  bundled with the workstream commit before the split was worth making) and `33314a4` (skills:
  document the three static caller-search tools and the doc-writing lesson).
- Disk image: `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add`. Present on this Mac checkout. The
  working tree also now holds the two-disk original (§30b) in the same `Cadaver/` directory,
  untracked — a fresh subject, not yet booted.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). No new anchor snapshots this
  pass — every check was a static read of `room2_tunnel_entry.snap`'s RAM image, no live stepping.
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry) or `gameplay_empire.snap` (CAVERN start
  tile) depending on which room's mechanism you're testing next. **Do not use `$5a99` to detect
  "crossing done"** — use `(A5)+1166` (§38b) instead. **Always pass `--disk-a "Cadaver...st"` and use
  `resume <snap> repl`, never the bare alias `rrepl`** — see "Known traps" below.
- Uncommitted work left behind: `M68000/sessions/README.md` and `M68000/sessions/powermonger.md`
  still show as modified in `git status` — a concurrent session's workstream ("Training efficiency
  (2)", confirmed live via `ListAgents`), left alone per the shared-resources rule.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` §1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35-47 (movement collision/proximity mechanism, the
icon-panel write chain, the full 72-room world-map/adjacency graph, the door-connectivity walk with
zero teleport doors, all fully closed). **New this session, `mechanics.md` §48**:

- **§48a.** Corrected §47c in place: its "positive door-id word = type-8 room-registration gate"
  reading revived a framing (§14's empty type-8 table) that §31/§38 had already retired — type 8 was
  never the room table (type 3 is, all 72 rooms already resident, no disk I/O anywhere in the image).
  The id word's meaning stays genuinely open, just not explained by a registration mechanism that was
  never real.
- **§48b/§48c.** `$00b1e0` (the level-asset reloader that touches type 3, i.e. rooms) has zero
  references anywhere in `room2_tunnel_entry.snap`'s loaded image, by three independent static
  techniques: direct call (`find_ram_callers.py`, §15c, pre-existing), raw data pointer
  (`tools/find_literal_ptr.py`, new this pass, validated against `$b5a8`'s 3 known callers first),
  and displacement-style jump table (`tools/find_jump_table_hit.py`, new this pass, validated by
  re-finding the known `$010000` table's entry 18 → LOCK first). Both new tools promoted to `tools/`
  and indexed in `DEVELOPING.md`.

## Open, in priority order

1. **Whether `world_map.png`'s 72-room graph is one level of several, not the whole game** — Dave's
   own 45th-pass observation. As settled as static analysis can make it (§48b/§48c): every technique
   this spike has for finding a caller of the level-reload routine `$00b1e0` comes back empty, and
   combined with §30a (no disk-I/O-capable code anywhere in this image) and §30b (the two-disk
   original's disk 2 is explicitly labelled "(Level)"), the reading is that this one-disk build's
   72 rooms are the whole reachable game. **Not proven** — a table entry beyond 300 slots, or a table
   base computed at runtime rather than a literal, would be invisible to `find_jump_table_hit.py`.
   The only way to actually settle it is the two-disk pivot below (item 4), which is a different
   investigation, not a continuation of this one's static techniques.
2. **The object-verb bytecode interpreter's LOCK/UNLOCK caller, and the door descriptors' five
   positive id words** — the interpreter itself is real and proven (§22-26: LOCK/UNLOCK confirmed
   causally on the lever's object id 144), and §26's negative ("nothing in the loaded image calls
   LOCK with id 144") still stands as a fact, but its old *explanation* (tied to type-8) is retracted
   (§48a). Genuinely open, not yet re-examined under the corrected type-3 model: does LOCK/UNLOCK
   simply flip a door descriptor's own open/closed flag (§38c's `btst #0,4(A0)`) on an already-resident
   door, rather than "registering" anything? And what do the five doors' positive id words
   (`53`,`73`,`155`,`167`,`244` — §47b/§47c) actually encode, since they're neither a room selector
   (§38d: `$de5e` never reads them) nor a registration gate (§48a)? No concrete next step scoped yet.
3. **Low priority, not needed to close §46**: which of the other 13 `$ff8201`-touching call sites
   actually fires (title/intro screen, a different room-pair's crossing, a resolution/mode change).
4. **The two-disk original** (§30b, now present in the working tree at `Cadaver/`) — a fresh subject:
   its own boot trace/wall-fixing pass (reversing skill §1-2) would be needed before any of this
   spike's snapshots, addresses or struct layouts can be assumed to carry over. The natural next step
   if item 1 is treated as settled rather than chased further statically.

## Known traps

(Unchanged carried-over list — see git history for the full set: `ScreenBufferA/B` role-swap framing
is wrong, `movem` block-copy chunk reversal, `watch`'s step= counter is a lifetime counter not local,
one-shot breakpoint chase non-reproducibility across separate invocations, re-disassemble elided
`...` excerpts in full, `bpc` over `bp` for one-shot dumps, `bt depth>1` can crash the REPL, a `watch`
range can bracket multiple regions in one call, `gfxview.py`'s `st-interleaved` assumes 16px-wide
masked blits (not this game's 32px-wide family), movement is joystick port 1, player = sprite slot 0,
use `tools/find_ram_callers.py`/`find_field_writers.py`/`find_literal_ptr.py`/`find_jump_table_hit.py`
— now all indexed in `DEVELOPING.md` and the `reverse-engineer-st-game` skill, §5.)

- **`run.ps1`'s subcommand names are aliases, not raw argv — the raw binary only understands
  `resume <snap> repl [--disk-a <path>]` (two tokens), not `rrepl <snap>`.** Calling the raw
  `dotnet exec` binary with an alias name silently matches no argv pattern and falls through to a
  disk-less cold boot, which then sits forever in an early ROM wait loop (`$00fc01a0`-`$00fc01d4`,
  identical PC across repeated `s` calls regardless of which snapshot was named). This looks exactly
  like a stuck or corrupted snapshot — blank `snap_render.py` output, `bpc` never hitting even after
  millions of steps — until you reproduce a *known-good* prior result (e.g. §43's documented step
  count) with the correct argv and it works. Also in `CLAUDE.md`'s Rules section.
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
- **A static-analysis session's own new interpretive claim can revive a framing the doc's own later
  sections already retired** — not just a stale carried-over handoff item (that's the `/resume`
  skill's job to catch). Grep the doc for later sections before writing a new reading, not just when
  resuming one (this session's §47c mistake, caught only on a later re-read; now in `CLAUDE.md`).

## Next session

Item 1 is as settled as static analysis gets; the real choice is whether to keep chasing edge cases
in `find_jump_table_hit.py`'s blind spots (deeper tables, runtime-computed bases) or pivot to the
two-disk original (item 4) as a fresh investigation with its own boot/wall-fixing pass. Item 2 (LOCK/
UNLOCK's caller, the door id words) is the cheaper thread if a quicker win is wanted instead. Prompt:
`/resume cadaver`.
