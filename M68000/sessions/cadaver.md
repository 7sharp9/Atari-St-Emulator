# Cadaver: handoff

Updated 2026-09-24 by the session that ended at this commit (49th pass). Checked LOCK/UNLOCK's own
target against the door-transition executor's flag test and found them structurally disjoint (two
different resource types, two different record offsets) — this rules out one reading of Open item 2
("LOCK/UNLOCK flips a door's own open/closed flag") and gives it a concrete next causal test instead.

## Resume point

- Last commit of this workstream: `7a91477` "cadaver: LOCK/UNLOCK is structurally disjoint from the
  door-transition flag; the 5 door id words are real type-6 object ids (49th pass, §49)".
- Disk image: `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add`. Present on this Mac checkout. The
  working tree also holds the two-disk original (§30b) in the same `Cadaver/` directory, untracked —
  a fresh subject, not yet booted.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). No new anchor snapshots this
  pass — every check was a static read of `room2_tunnel_entry.snap`'s RAM image via
  `py/door_id_words.py`, no live stepping.
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry) or `gameplay_empire.snap` (CAVERN start
  tile) depending on which room's mechanism you're testing next. **Do not use `$5a99` to detect
  "crossing done"** — use `(A5)+1166` (§38b) instead. **Always pass `--disk-a "Cadaver...st"` and use
  `resume <snap> repl`, never the bare alias `rrepl`** — see "Known traps" below.
- Uncommitted work left behind: `M68000/sessions/README.md` and `M68000/sessions/powermonger.md`
  still show as modified in `git status` — a concurrent session's workstream ("Training efficiency
  (2)", confirmed live via `ListAgents`), left alone per the shared-resources rule.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` §1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35-48 (movement collision/proximity mechanism, the
icon-panel write chain, the full 72-room world-map/adjacency graph, the door-connectivity walk with
zero teleport doors, the world-map-scope question as settled as static analysis gets, all fully
closed). **New this session, `mechanics.md` §49**:

- **§49a.** LOCK/UNLOCK (§22c: `bset/bclr #2,15(A0)`) operates on a type-6/9 object record; the
  door-transition executor's own flag test (§38c: `btst #0,4(A0)`) operates on a type-4 door-
  descriptor record — different resource type, different table, different base address, different
  offset. **They cannot be the same mechanism.** Answers half of Open item 2 as scoped in the 48th
  pass's handoff: LOCK/UNLOCK does not flip a door's own open/closed flag, structurally.
- **§49b.** The five doors' genuine positive id words (`53`, `73`, `155`, `167`, `244`, §47b/§47c)
  all resolve to real, populated type-6 object records (`py/door_id_words.py`, new this pass) — not
  garbage, not out-of-range. All five currently read lock-flag (`+15` bit 2) **clear** in
  `room2_tunnel_entry.snap`.

## Open, in priority order

1. **What the five doors' positive id words actually encode** (was Open item 2; item 1, world-map
   scope, is closed as settled per §48 and dropped from this list). They're valid type-6 object ids
   (§49b), the same id space LOCK/UNLOCK (opcode 18, §23a) operates on, but nothing found so far
   shows anything actually *reads* the id word that way — `$de5e` (§38d, the routine that actually
   resolves room transitions) never touches it, only the descriptor's coordinate bytes. **Concrete
   next step**: `callcap` LOCK against one of the five ids (e.g. `155`) from a snapshot near that
   door, then re-run the door-transition trace (§38c) across it and check whether `$007280`'s
   `btst #0,4(A0)` result, or anything else in the executor's flow, changes — the first causal test
   of whether the id word does anything at all, not just a structural read.
2. **Low priority, not needed to close anything above**: which of the other 13 `$ff8201`-touching
   call sites actually fires (title/intro screen, a different room-pair's crossing, a resolution/mode
   change).
3. **The two-disk original** (§30b, present in the working tree at `Cadaver/`) — a fresh subject: its
   own boot trace/wall-fixing pass (reversing skill §1-2) would be needed before any of this spike's
   snapshots, addresses or struct layouts can be assumed to carry over. Still the natural pivot if
   item 1 above is treated as a dead end rather than chased with the `callcap` test.

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

## Next session

Item 1 (the door id words) has a scoped, cheap causal test ready to run: `callcap` LOCK against id
`155` (or any of the other four) from a snapshot near that door, then re-check the door-transition
trace. If that comes back negative too, the id word likely means something this spike hasn't
guessed yet, and the two-disk pivot (item 3) becomes the better use of a session. Prompt:
`/resume cadaver`.
