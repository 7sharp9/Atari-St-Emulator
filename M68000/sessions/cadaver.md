# Cadaver: handoff

Updated 2026-09-24 by the session that ended at this commit (46th pass). Closed the carried-over
shifter-base-flip Open item 1: found the actual hardware writer ($015272, `movep.w` from `(A5)+0`),
confirmed `watch` has no blind spot for `movep`, and showed the two "conflicting" older snapshots
are mid-transition captures of the same `(A5)+0`/shifter-base invariant the doc already understood,
not evidence of an undetected write.

## Resume point

- Last commit of this workstream: `2f1df82` "cadaver: close shifter-base-flip conflict, Open item 1
  (46th pass)". Prior commit: `ed4d807` "cadaver: close open item 1 - confirm §43's
  proximity mechanism against BOAT (45th pass)". A related shared-resource commit, `14515d7`
  (`CLAUDE.md` note on `run.ps1` alias argv), landed the 45th-pass session but is not
  workstream-specific.
- Disk image: `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add`. Present on this Mac checkout.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). No new anchor snapshots this
  pass — `gameplay_empire.snap` (already present) was the resume point used.
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry) or `gameplay_empire.snap` (CAVERN
  start tile) depending on which room's mechanism you're testing next. **Do not use `$5a99` to
  detect "crossing done"** — use `(A5)+1166` (§38b) instead. **Always pass
  `--disk-a "Cadaver...st"` and use `resume <snap> repl`, never the bare alias `rrepl`** — see
  "Known traps" below.
- Uncommitted work left behind: none of this session's own. `M68000/sessions/README.md` and
  `M68000/sessions/powermonger.md` still show as modified in `git status` — a concurrent session's
  workstream, left alone per the shared-resources rule (carried over unchanged from prior handoffs).

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` 1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45
(movement collision/proximity mechanism, the icon-panel write chain, the full 72-room
world-map/adjacency graph, the §43 proximity mechanism confirmed generic against a second object,
all fully closed). **New this session, `mechanics.md` §46**:

- **§46.** Closed the carried-over shifter-base-flip Open item 1: `find_field_writers.py` located
  the hardware writer (`$015272`, `movep.w D0,0(A0)` with `A0=$ff8201`, `D0` from `(A5)+0`) among
  14 code sites that touch that register; confirmed `MOVEP` goes through the same `WriteByte`/
  `checkWatch` path as any other store (`68k.fs`/`MMU.fs`), so `watch` has no blind spot for it;
  `hits 8200000 15272` gives 0 both idle and across the standard `kbd ff 02` TUNNEL↔CAVERN crossing,
  reproducing §37/39th pass's "zero writes" by an independent method. The two "conflicting" older
  snapshots turn out to sit at the *opposite*, but still internally consistent, parity of the same
  `(A5)+0`-is-inactive-half / shifter-is-active-half invariant §34a already established (proof
  table: `py/snapinfo.py`, new this pass) — mid-transition captures, not an undetected write.

## Open, in priority order

1. **Whether every door connects only edge-adjacent rooms, or some "teleport" across the world
   grid** (scoped when §44 closed item 4): would need a walk of every room's door-descriptor list
   (only TUNNEL's two entries are known, §15th pass, format at `$007250`/§38c) cross-referenced
   against `world_map.png`'s adjacency graph.
2. **Whether `world_map.png`'s 72-room graph is one level of several, not the whole game** — Dave's
   observation, 45th pass: the game likely has more than one level, and completing one probably
   reveals another. Not yet checked: whether the type-3 resource-manager table at `$4ac36` (§38a,
   what `world_map.py` walks) is per-level and gets rebuilt/switched on a level-complete event, or
   is a single fixed table for the whole game. Would need finding the level-complete/level-advance
   trigger (search for a win-condition check or a routine that rewrites `$4ac36`'s slots) and
   diffing the table before/after it fires.
3. **Whether the game has a scripting/bytecode layer driving room or object behaviour** — Dave's
   second observation, 45th pass: worth checking for a dispatch-by-opcode pattern (a table of small
   routines indexed by a byte read from room/object data) rather than assuming every interaction is
   hand-written 68000. Not yet scoped as a concrete test: start from a room's object-placement table
   entries (`56(A5)` stride 70, §43) and check whether any field looks like an opcode/operand
   stream read by a small interpreter loop, rather than only static bounding-box/bitmap data.
4. **Low priority, not needed to close §46**: which of the other 13 `$ff8201`-touching call sites
   actually fires (title/intro screen, a different room-pair's crossing, a resolution/mode change) —
   §46 closed the conflict without needing this.
5. The two-disk original (§30b): lower priority, would be a fresh subject.

## Known traps

(Unchanged carried-over list — see git history for the full set: `ScreenBufferA/B` role-swap
framing is wrong, `movem` block-copy chunk reversal, `watch`'s step= counter is a lifetime counter
not local, one-shot breakpoint chase non-reproducibility across separate invocations, re-disassemble
elided `...` excerpts in full, `bpc` over `bp` for one-shot dumps, `bt depth>1` can crash the REPL,
a `watch` range can bracket multiple regions in one call, `gfxview.py`'s `st-interleaved` assumes
16px-wide masked blits (not this game's 32px-wide family), movement is joystick port 1, player =
sprite slot 0, use `tools/find_ram_callers.py`/`find_field_writers.py`.)

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

Items 2 and 3 (carried from the 45th pass as Dave's observations: whether the world map is only one
level of several, and whether a scripting/bytecode layer drives room/object behaviour) are not yet
scoped down to a first concrete probe — worth 15-20 minutes of code/data reading before committing
to a live-test plan for either. Item 1 (door-connectivity walk) is the cheaper, already-scoped
alternative if that reading doesn't land quickly. Prompt: `/resume cadaver`.
