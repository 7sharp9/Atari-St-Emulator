# Cadaver: handoff

Updated 2026-09-25 by the session that ended at commit `35bd269` (58th pass). Resumed from the
57th-pass handoff's item 1 (the "no data" FDC wall past the crack dispatch fix) and found it was
this workstream's own REPL-driving gap, not a game or emulator bug: `resume`ing a `.snap` never
remounts drive A's disk, and the 57th pass stepped forward without doing so. Remounting Disk 2 and
re-running the identical step count gets cleanly past the old wall into real gameplay.

## Resume point

- Last commit of this workstream: `35bd269` "cadaver: the 57th-pass FDC wall was a REPL workflow
  gap, not a game/emulator bug (58th pass)". No emulator source changed this pass, so no rebuild or
  regression-net run is needed before building on it.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). This pass's additions:
  - `full_trace_fdc.log` / `full_trace_mounted_fdc.log`: same `s 30000000` from `agent_disk2_wall/
    before_jsr.snap`, first with no disk mounted (reproduces the 57th pass's "no data" wall
    verbatim) then with `disk ../Cadaver/disk2_replicants/disk2.st` issued first (121 reads, all
    `-> OK`). The A/B pair that proves the diagnosis.
  - `past_wall_mounted_30M.snap` / `_60M.snap` / `_90M.snap`: `before_jsr.snap` with Disk 2 mounted,
    run forward 30M/60M/90M steps. `_90M` lands at PC=`$00015254`, rendered in
    `past_wall_mounted_90M.png` - the already-known "DAY 1 / BOAT / CAVERN" room (matches
    `reversing/cadaver/boat_hotspot.png` pixel-for-pixel), i.e. real gameplay past the old wall, not
    yet proof of anything Disk-2-exclusive.
  - `wall_widen.repl` / `wall_widen.log` (+ `wall_widen_fdc.log`, empty), `wall_retry_kbd.repl` /
    `.log` (+ `_fdc.log`, empty): this pass's own dead ends, stepping forward from the *already
    landed* `disk2_past_dispatch_30M.snap` (post-wall) with no disk mounted and/or a scripted
    keypress - all register dumps bit-identical except PC/CCR, confirming a real idle loop at
    `$11ac6` (matches §54's already-documented "no input" idle PC) rather than new information. Kept
    for reference but superseded by the `before_jsr.snap`-based A/B above; safe to delete.
  - `push_past_wall.repl` / `.log`: the driving script and register-dump log for the three
    `past_wall_mounted_*.snap` saves above.
- **Start from**: `scratchpad/cadaver/past_wall_mounted_90M.snap` (PC=`$00015254`, Disk 2 mounted,
  past the old wall, sitting in the Day 1/Boat/Cavern room) - or re-derive further from
  `agent_disk2_wall/before_jsr.snap` with `disk ../Cadaver/disk2_replicants/disk2.st` issued first.
- Uncommitted work left behind: none of this session's own. `CLAUDE.md` shows modified in `git
  status` - a line-unwrapping/reflow edit (content unchanged) from the concurrent "Training
  efficiency (2)" session (confirmed live via `ListAgents`, messaged about it), left alone per the
  shared-resources rule. `sessions/README.md`/`sessions/powermonger.md` likewise belong to that
  session. `.obsidian/` and `Cadaver/` are untracked and not this session's to manage.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md` (§58 is this pass), `graphics.md`, `ai.md`.
Carried over: `mechanics.md` §1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35-57 (movement collision/proximity
mechanism, the icon-panel write chain, the full 72-room world-map/adjacency graph, the
door-connectivity walk, the swapped-disk side-count bug, the Replicants/ST Amigos crack's Disk 2
swap, the two genuine emulator gaps behind the "crack dispatch bug" - reserved-MOVEQ trapping to
vector 4, trace-mode single-step to vector 9 - both fixed and regression-proven). **New this
session, `mechanics.md` §58**:

- §57's "new FDC wall" (`READ-SECTOR track=0 side=0 sector=8 -> no data` on repeat) was this
  workstream's own REPL-driving gap: `resume`ing a `.snap` starts with no disk mounted in drive A
  (deliberately excluded from `MmuSnapshot` - `MMU.LoadDiskA`'s own doc comment), and the 57th pass
  stepped forward without re-issuing `disk <path>` first.
- Reproduced the exact failing sequence byte-for-byte with the disk unmounted
  (`full_trace_fdc.log`), then reproduced the identical command sequence reading clean with Disk 2
  mounted first (`full_trace_mounted_fdc.log`, 121/121 reads OK) - a controlled A/B, not a guess.
- Past the fix, execution runs well beyond the old wall: track 13 side 1 by 30M steps, PC=`$15254`
  by 90M steps, rendering to the already-known Day 1/Boat/Cavern room. Real further progress, but
  not yet evidence Disk 2 supplies anything the one-disk crack didn't already have resident - that's
  the new, narrower open question (item 1 below).

## Open, in priority order

1. **Does Disk 2 supply any content beyond what's already known from the one-disk crack?** Past the
   old wall, 90M steps of forward-running with no player input lands back in the already-documented
   Day 1/Boat/Cavern room (`past_wall_mounted_90M.png` vs `boat_hotspot.png`, pixel-identical
   framing) - real gameplay, not proof of new content. Next step: drive it with actual player input
   (movement/interaction, per the `reverse-engineer-st-game` skill and this workstream's existing
   `kbd`/joystick notes) from `past_wall_mounted_90M.snap` far enough to reach a room or day beyond
   what `mechanics.md`'s existing 72-room world-map graph covers, or to exhaust the disk's own
   descriptor table at `(A5)+2538` (§55) and confirm it holds no further entries.
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

- **A `.snap` does not remember which disk is mounted in drive A** (`MMU.LoadDiskA`'s own doc
  comment: deliberately excluded, "external, physical-world state"). `resume`ing any snapshot
  starts with `diskA = None` until the REPL's own `disk <path>` re-mounts one (or `--disk-a`/
  `ATARI_DISK_A` was passed at process start) - stepping forward without it makes every FDC sector
  read fail "no data", indistinguishable from a genuinely absent sector or a real FDC gap unless you
  think to check (58th pass: this is exactly what made §57's "new FDC wall" look unresolved for a
  whole pass). Always issue `disk <path>` right after `resume`ing a snapshot that was taken with a
  real disk swapped in, before stepping forward. Flagged to the concurrent "Training efficiency (2)"
  session as worth folding into `CLAUDE.md`'s Rules section too, since it applies to any workstream
  that swaps disks, not just this one - not yet done because `CLAUDE.md` had that session's own
  uncommitted edit in the working tree this pass.
- **A blind linear/static disassembly at a `jsr` target that lands in what looks like a data
  region is not reliable evidence that the target really is stale data misread as code** - Rob
  Northen (and similar) protection code deliberately looks like garbage under a byte-for-byte scan.
  When a `jsr`/`jmp` target's static disassembly looks like noise, step through it live before
  concluding it's misread data rather than an emulator gap or a genuine probe (57th pass).
- **`run.ps1`'s subcommand names are aliases, not raw argv** (`CLAUDE.md`'s Rules section has the
  mapping) - `snap <N> <path>` is NOT valid raw argv; the raw form is `<N> snapshot <path>`.
  Passing the alias name directly to `dotnet exec` silently falls through to a disk-less cold boot -
  always `cmp`/`ls` a snapshot file after writing it if the exact argv hasn't been double-checked.
- Stepping past a reserved/undefined-opcode CPU-detection probe or a trace-mode decrypt loop can
  legitimately take tens of millions of steps before the interesting part starts - don't assume a
  large step count with little PC movement means a hang; check `r` twice a few hundred thousand
  steps apart first (identical registers = real loop; PC/registers differing but slowly = genuine
  multi-instruction work, keep stepping). But when *every* data/address register, not just PC, is
  bit-identical across samples tens of millions of steps apart, that's a real idle/busy-wait loop,
  not slow progress - check what condition it's blocked on (58th pass: `$11ac6` is exactly §54's
  documented "no keyboard input" idle address, reused generically, not a fresh wall).
- `bp <hexaddr> [maxSteps]` takes at most 2 arguments - `bpc <addr> <n> [maxSteps]` if an Nth-hit
  count is needed.
- The REPL's `disk <path>` command mounts a *relative* path from the process's own working
  directory (typically `M68000/`), not relative to wherever the snapshot or driving script lives.
- `$5a99` is not a room-transition signal; use `(A5)+1166` (§38b) instead.
- A live snapshot's static memory alone can settle a "what does routine X compute" question without
  running the emulator forward, and extends to a disk image's own raw bytes for "does the disk hold
  more content" - though it can't identify *what kind* of content without a live boot or readable
  strings. It canNOT settle "is this address really data, or an emulator gap disguised as data", or
  "is this FDC failure real, or is the disk just not mounted" - both need a live step, and the
  latter needs an A/B with the disk mounted vs not (58th pass).
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

Item 1 is the priority: from `scratchpad/cadaver/past_wall_mounted_90M.snap` (Disk 2 mounted, past
the old wall, sitting in the Day 1/Boat/Cavern room), drive real player input forward far enough to
either reach content beyond `mechanics.md`'s existing 72-room world-map graph, or exhaust Disk 2's
own descriptor table at `(A5)+2538` and confirm it holds nothing further. No emulator rebuild or
reverification is needed first - nothing in `*.fs` changed this pass. Prompt: `/resume cadaver`.
