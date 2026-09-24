# Cadaver: handoff

Updated 2026-09-24 by the session that ended at commit `c64a463` (50th pass). Ran the causal test
§49c itself proposed and closed Open item 2 (the five doors' positive id words): `callcap` LOCK
against a real door id (155) flips the resolved object's own lock flag but leaves the door
descriptor's own executor-tested flag byte untouched — doubly negative with §49c's static caller
search. Dave pushed back on §48c/§48d's "single reachable level" reading (below); that pivot is now
reframed as an open item instead of a settled negative.

## Resume point

- Last commit of this workstream: `c64a463` "cadaver: causal callcap test confirms door id word 155
  does not touch the door-transition executor's flag byte (50th pass, §50)".
- Disk image: `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add`. Present on this Mac checkout. The
  two-disk original mentioned in earlier handoffs is **not** currently present in the working tree's
  `Cadaver/` directory (checked this pass, only the one-disk image is there) — do not assume it is
  available without checking again.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). No new anchor snapshots this
  pass — the causal test ran live against `room2_tunnel_entry.snap` (§50), `callcap` restores memory
  after reporting its diff so the snapshot itself is untouched.
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry) or `gameplay_empire.snap` (CAVERN start
  tile) depending on which room's mechanism you're testing next. **Do not use `$5a99` to detect
  "crossing done"** — use `(A5)+1166` (§38b) instead. **Always pass `--disk-a "Cadaver...st"` and use
  `resume <snap> repl`, never the bare alias `rrepl`** — see "Known traps" below.
- Uncommitted work left behind: none of this session's own. `M68000/sessions/README.md` and
  `M68000/sessions/powermonger.md` still show modified in `git status` — the concurrent "Training
  efficiency (2)" session's work (confirmed live via `ListAgents` again this pass), left alone per
  the shared-resources rule.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` §1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35-49 (movement collision/proximity mechanism, the
icon-panel write chain, the full 72-room world-map/adjacency graph, the door-connectivity walk with
zero teleport doors, the world-map-scope question as settled as static analysis gets, the LOCK/UNLOCK
mechanism structurally disjoint from the door-transition flag, all fully closed). **New this session,
`mechanics.md` §50**:

- **§50.** Causal (not just structural) proof that the five doors' positive id words do nothing on
  the door-transition path: `callcap` LOCK directly against id `155` (a real id a door descriptor
  genuinely points to, resolved by `door_id_words.py`, §49b) sets bit 2 of that object's own `+15`
  byte — matching §24c's id-144 precedent exactly — but door `0x20`'s own descriptor bytes at `$6d45a`
  (owner room 19), including the `+4` byte `$007280`'s `btst #0,4(A0)` tests, read identically before
  and after. Combined with §49c's exhaustive static caller search, Open item 1 (now closed) has no
  surviving mechanism, structural or causal, connecting the id word to anything.

## Open, in priority order

1. **Does the one-disk crack pack more than the 72-room map already found (a second level), reached
   some way §48c/§48d's static search didn't find?** §48c/§48d's own reading (three independent
   static techniques find zero callers of the level-reload code at `$00b1e0`) concluded the one-disk
   build most likely has only the 72-room map reachable, with a second level needing the two-disk
   original's disk-swap path. **Dave disagrees**: his expectation is that the one-disk crack has been
   repacked to fit all 5 levels on one disk, not trimmed to one. This is now a genuine open
   disagreement, not a settled negative — the static search proved "no *currently loaded* code calls
   `$00b1e0`", which doesn't rule out a level-select mechanism that swaps in code/data at runtime
   (self-modifying, or loaded from elsewhere on the disk) that this spike hasn't looked for.
   **Concrete next step**: inspect the one-disk `.st` image directly (sector/file listing, e.g. via
   `tools/`'s disk-image tools per `DEVELOPING.md`) for level-tagged assets or a second set of
   room/object data beyond what the 72-room world-map (§38a/§44) already accounts for, rather than
   relying only on a loaded-image caller search — a data-only check, no live stepping needed first.
2. **Low priority, not needed to close anything above**: which of the other 13 `$ff8201`-touching
   call sites actually fires (title/intro screen, a different room-pair's crossing, a resolution/mode
   change).

## Known traps

(Unchanged carried-over list — see git history for the full set: `ScreenBufferA/B` role-swap framing
is wrong, `movem` block-copy chunk reversal, `watch`'s step= counter is a lifetime counter not local,
one-shot breakpoint chase non-reproducibility across separate invocations, re-disassemble elided
`...` excerpts in full, `bpc` over `bp` for one-shot dumps, `bt depth>1` can crash the REPL, a `watch`
range can bracket multiple regions in one call, `gfxview.py`'s `st-interleaved` assumes 16px-wide
masked blits (not this game's 32px-wide family), movement is joystick port 1, player = sprite slot 0,
use `tools/find_ram_callers.py`/`find_field_writers.py`/`find_literal_ptr.py`/`find_jump_table_hit.py`
— all indexed in `DEVELOPING.md` and the `reverse-engineer-st-game` skill, §5.)

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
  resuming one (48th pass's §47c mistake, caught only on a later re-read; now in `CLAUDE.md`).
- **A "no caller found in the loaded image" static negative is not the same as "the mechanism is
  unreachable"** — it only rules out a plain `bsr`/`jsr`/literal-address/displacement-table caller
  already resident; a runtime-loaded or self-modifying path stays untested (50th pass, item 1 above,
  raised by Dave against §48c/§48d's stronger "single reachable level" phrasing).

## Next session

Item 1 (whether the one-disk crack contains more than one level's worth of data) has a concrete,
data-only next step: inspect the disk image's own sectors/files for a second level's assets rather
than relying on the loaded-code caller search alone. If that turns up nothing, item 2 (the low-value
`$ff8201` call-site sweep) is the only remaining open item in this spike. Prompt: `/resume cadaver`.
