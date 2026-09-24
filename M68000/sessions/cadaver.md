# Cadaver: handoff

Updated 2026-09-25 by the session that ended at commit `cc2c5a6` (57th pass). Resumed from the
56th-pass handoff's item 1 (the crack's "dispatch bug"), traced it live instead of statically, and
found the 55th pass had misdiagnosed it: it wasn't a crack-patched-out version check or stale
framebuffer data misread as code, it was two real emulator gaps. Fixed both, each behind its own
full regression-net pass (`verify` PASS, 30M-step diskless boot snapshot byte-identical, full
680x0 selftest 1,000,051 pass / 0 fail / 9 skip unchanged). Past both fixes, execution reaches
genuinely new, FDC-driven code and hits a further, still-open wall - real progress, not the same
wall in a new shape.

## Resume point

- Last commit of this workstream: `cc2c5a6` "cadaver: correct the 55th-pass dispatch-bug
  misdiagnosis, document the fix (57th pass)". Emulator fixes are `1cb269b` (reserved-MOVEQ ->
  vector 4) and `1f41114` (trace exception / vector 9), both on `master`, both already covered by
  their own regression-net run - no rebuild or reverification needed before building on them.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored), unchanged from the 55th/56th
  pass's entries except for this pass's additions below.
  - **Start from**: `scratchpad/cadaver/disk2_past_dispatch_30M.snap` - `before_jsr.snap`
    (55th-pass snapshot, PC=$00011602, one instruction before the `jsr (A2)` that used to crash)
    run forward 30M further steps with this session's two fixes in place. Lands at PC=$00011b0e,
    mid-loop in the new wall described below.
  - `scratchpad/cadaver/agent_disk2_wall/before_jsr.snap`: the original 55th-pass snapshot, still
    the right starting point if a shorter/different step budget than 30M is wanted.
  - `scratchpad/cadaver/regress_before.snap` / `regress_after.snap` / `regress_after2.snap`: this
    pass's own before/after diskless-boot regression snapshots (30M steps from cold boot, no disk)
    used to prove both fixes have zero effect outside the reserved encoding / trace bit. No longer
    needed - safe to delete.
- Uncommitted work left behind: none of this session's own. `M68000/sessions/README.md` and
  `M68000/sessions/powermonger.md` still show modified in `git status` - the concurrent "Training
  efficiency (2)" session's work (confirmed live via `ListAgents` at the top of this pass), left
  alone per the shared-resources rule. `.obsidian/` and `Cadaver/` are untracked and not this
  session's to manage.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md` (§57 is this pass), `graphics.md`, `ai.md`.
Carried over: `mechanics.md` §1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35-56 (movement collision/proximity
mechanism, the icon-panel write chain, the full 72-room world-map/adjacency graph, the
door-connectivity walk, LOCK/UNLOCK structurally disjoint from door-transition, the five doors' id
words causally inert, the one-disk crack's disk contents ruled out for a second level, the two-disk
original's Disk 2 independently confirmed as a real, distinct levels disk, the Replicants/ST Amigos
crack reaching the live "place levels disk" prompt and Disk 2 swap, the swapped-disk side-count bug
found and fixed, and the 56th pass's exhaustive negative static graphics scan of Disk 2's raw
bytes). **New this session, `mechanics.md` §57**:

- The 55th pass's `jsr (A2)` -> `$00021da0` wall is real Rob Northen protection code, not stale
  framebuffer data: a two-stage CPU-detection probe (MOVEC, already handled; a reserved bit-8
  MOVEQ encoding, not handled - the actual crash) followed by a trace-mode (vector 9)
  single-step decrypt loop.
- Fixed both emulator gaps: `ReservedMoveq` traps `$712x`-shaped reserved opcodes to vector 4
  (`Instructions.fs`/`68k.fs`, commit `1cb269b`); `Step()` now implements the trace exception
  itself, which was computed (`TraceMode`) but never consumed anywhere (`68k.fs`, commit
  `1f41114`) - `EnterVector`/`EnterGroup0Vector` also now clear T1 on entry, matching
  `EnterInterrupt`/`FetchTargetOrFault`'s existing behaviour.
- Past both fixes, `before_jsr.snap` run 30M steps reaches genuinely new code: `A4=$ffff8604`
  (the FDC/DMA register), confirmed via `ATARI_TRACE_FDC=1` issuing real `READ-SECTOR drive=0
  track=0 side=0 sector=8` commands that repeatedly come back "no data", with a `type I $03`
  (Restore) retry between attempts - PC only crawls from `$11b00` to `$11b0e` across those 30M
  steps. This is the new wall (item 1 below).

## Open, in priority order

1. **The new `READ-SECTOR track=0 side=0 sector=8` -> "no data" wall** at `$11b00`-`$11b0e`, from
   `scratchpad/cadaver/disk2_past_dispatch_30M.snap`. Not yet diagnosed: whether track 0/sector 8
   is genuinely absent from whichever disk is mounted in drive A at this point (a disk-swap step
   missed somewhere upstream of this snapshot), an FDC-modelling gap for this exact command
   sequence, or something else. Start with `ATARI_TRACE_FDC=1` over a wider window to see the
   full retry pattern, then check what disk is actually mounted at this point in the drive/`disk`
   REPL-command history vs. what the crack expects (compare against the equivalent point in a
   disk image known to boot clean, if one exists).
2. Which of the 13 (of 14) `$ff8201`-touching call sites other than the room-crossing path
   actually fires. Not needed to close anything above.
3. `disk_layout.py`'s blank/data classifier only catches single-byte fills, not short-period
   repeats (§52's 3-byte cycle) - not yet extended.
4. No `.stx`->`.st` converter exists in `tools/`. Only worth writing for a `.stx`-only release.
5. The five crack variants extracted in the 55th pass and the untried single-sided
   `disk2_replicants[b].st` (55th-pass handoff) - low priority, superseded by item 1 as the more
   direct path to more Disk 2 content.

## Known traps

(Carried over from earlier passes - see git history for the full set: `ScreenBufferA/B` role-swap
framing is wrong, `movem` block-copy chunk reversal, `watch`'s step= counter is a lifetime counter
not local, one-shot breakpoint chase non-reproducibility, re-disassemble elided `...` excerpts in
full, `bpc` over `bp` for one-shot dumps, `bt depth>1` can crash the REPL, a `watch` range can
bracket multiple regions in one call, `gfxview.py`'s `st-interleaved` assumes 16px-wide masked
blits, movement is joystick port 1, player = sprite slot 0, use
`tools/find_ram_callers.py`/`find_field_writers.py`/`find_literal_ptr.py`/`find_jump_table_hit.py`.)

- **A blind linear/static disassembly at a `jsr` target that lands in what looks like a data
  region (e.g. framebuffer/screen memory) is not reliable evidence that the target really is
  stale data misread as code.** Rob Northen (and similar) protection code deliberately looks like
  garbage under a byte-for-byte scan - self-installing exception-vector handlers, deliberately
  executed reserved/unimplemented opcodes as CPU-detection probes, trace-mode single-step decrypt
  loops. The 55th pass called this "stale framebuffer pixel data decoded as code" from a static
  read alone; actually single-stepping the live CPU past it (57th pass) showed it was real,
  intentional protection code the whole time, and the "crash" was two genuine emulator gaps. When
  a `jsr`/`jmp` target's static disassembly looks like noise, step through it live before
  concluding it's misread data rather than an emulator gap or a genuine probe.
- **`run.ps1`'s subcommand names are aliases, not raw argv** (`CLAUDE.md`'s Rules section has the
  mapping) - `snap <N> <path>` is NOT valid raw argv; the raw form is `<N> snapshot <path>`
  (`resume <N> <path>` is likewise `<N> resume <path>`). Passing the alias name directly to
  `dotnet exec` silently falls through to a disk-less cold boot and, worse, a `snapshot`/`snap`
  confusion can silently save nothing at all rather than erroring - always `cmp`/`ls` a snapshot
  file after writing it if the exact argv hasn't been double-checked against `run.ps1`'s own
  `switch` block.
- Stepping past a reserved/undefined-opcode CPU-detection probe or a trace-mode decrypt loop can
  legitimately take tens of millions of steps before the interesting part (the actual disk read)
  starts - don't assume a large step count with little PC movement means a hang; check `r` twice
  a few hundred thousand steps apart first (identical registers = real loop; still identical after
  a fix = still a real gap; PC or registers differing but slowly = genuine multi-instruction work,
  keep stepping).
- `bp <hexaddr> [maxSteps]` takes at most 2 arguments - `bpc <addr> <n> [maxSteps]` if an Nth-hit
  count is needed.
- The REPL's `disk <path>` command mounts a *relative* path from the process's own working
  directory (typically `M68000/`), not relative to wherever the snapshot or driving script lives.
- `$5a99` is not a room-transition signal; use `(A5)+1166` (§38b) instead.
- A live snapshot's static memory alone can settle a "what does routine X compute" question without
  running the emulator forward, and extends to a disk image's own raw bytes for "does the disk hold
  more content" - though it can't identify *what kind* of content without a live boot or readable
  strings, and exhaustive width-guessed rendering can rule out "it's a plain raster at any obvious
  stride" too, once tried thoroughly enough to trust the negative (§56). It canNOT, per this
  session's own finding, settle "is this address really data, or an emulator gap disguised as
  data" - that needs a live step.
- `gfxview.load_ram(path)` returns `(ram_bytes, base)`, that order. `gfxview.detect_palettes(ram,
  base)` returns a list of dicts (`addr`/`type`/`words`/`colors`/`distinct`), not tuples.
- The REPL's `watch <addr> <len>` parses `<len>` as decimal, not hex.
- `kbd`/other REPL input commands only enqueue IKBD bytes for delivery during a subsequent `s`/`bp`/
  `bpc` - issue them before the step/breakpoint that should consume them, and split make/break
  codes into two separate `kbd` calls with a real `s <n>` between them.
- `bt` with no depth argument defaults to depth 8 and reliably crashes the REPL - always pass `bt 1`.
- If hand-parsing a `.snap`'s header instead of using `gfxview.py`'s loaders: `cpu.CCR` is written
  as an int16, not a byte, so the RAM-length field sits 1 byte later than expected.
- A static-analysis session's own new interpretive claim can revive a framing a doc's later
  sections already retired - grep the doc for later sections before writing a new reading.
- A "no caller found in the loaded image" static negative only rules out a plain resident caller
  already loaded; a runtime-loaded or self-modifying path stays untested until checked another way.

## Next session

Item 1 is the clear priority: from `scratchpad/cadaver/disk2_past_dispatch_30M.snap` (PC=$11b0e),
widen the `ATARI_TRACE_FDC=1` window to see the full retry pattern around the `READ-SECTOR
track=0 side=0 sector=8` -> "no data" failures, and determine whether this is a missing disk-swap
step, a genuinely absent sector on the mounted image, or an FDC-modelling gap. Both of this
session's emulator fixes are committed and pass the full regression net already, so no
reverification is needed before building on them. Prompt: `/resume cadaver`.
