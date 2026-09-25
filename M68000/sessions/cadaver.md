# Cadaver: handoff

Updated 2026-09-25 by the session that ended at commit `57c8ad4` (61st pass), which closed the
59th/60th pass's open item 1: the player entity was never dead on `past_wall_mounted_90M.snap` — the
documented sprite-array address (`$038338`) was simply stale for the two-disk build, exactly the
same `$100`-shift bug the 59th pass had already found and fixed in the resource manager. The
correctly-resolved address (`56(A5)` → `$038438` in this build) holds the exact canonical starting
bbox and moves under real joystick input.

Prior pass's summary (60th, `bd6bb93`): narrow follow-up to the 59th pass's queued item 2 —
`door_walk.py` had the same stale-resource-address bug `world_map.py` had; fixed to resolve
type-3/type-4 addresses dynamically via `world_map.resource_type()`. No new investigation that pass.

## Resume point

- Last commit of this workstream: `57c8ad4` "cadaver: item 1 closed — player entity is live,
  $038338 was stale by $100 (61st pass)". No emulator source changed this pass, so no rebuild or
  regression-net run is needed before building on it.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). This pass's additions:
  - `probe_sprite_d93c.repl`/`.log`: two `bpc d93c 1 20000000` samples 8.7M steps apart from
    `past_wall_mounted_90M.snap`, confirming `A6=$0003896a` is stable there — but see the trap below
    on why this address turned out to be a live loop-iteration pointer, not the array base to build on.
  - `probe_arrayptr_field.repl`/`.log`: reads `56(A5)` (`$182ec` → `$038438`) and `1152(A5)`
    (`$18734`, word count `$0014` = 20) fresh from the snapshot's own `A5=$182b4` — the fix.
  - `probe_realarray_038438.repl`/`.log`: dumps `$038438`, confirming `[25,23,19,17]`, the exact
    §19a canonical starting bbox.
  - `retest_movement_038438.repl`/`.log`, `realbase_038438_after_right.snap`: two `kbd ff 08`/
    `kbd ff 00` right-holds from `past_wall_mounted_90M.snap`, reading `$038438` back each time:
    `[25,23,19,17]` → `[69,23,63,17]` (real rightward movement) → unchanged (stalled at a boundary).
  - `probe_sprite_realbase.repl`/`.log`, `retest_movement_bpc.repl`/`.log`,
    `retest_movement_realbase.repl`/`.log`, `realbase_after_right.snap`: the dead-end path through
    `$0003896a` — kept for the record of why that address was rejected (see Known traps).
  - `probe_sprite.repl`/`.log` and the `drive_*`/`full_trace_fdc*` files: carried over from the
    59th/58th passes, unchanged this session.
- **Start from**: `scratchpad/cadaver/past_wall_mounted_90M.snap` (PC=`$00015254`, Disk 2 mounted,
  sitting in the Day 1/Boat/Cavern room) — mount Disk 2 (`disk ../Cadaver/disk2_replicants/disk2.st`)
  after resuming, then read the player entity from `56(A5)` (re-derived per snapshot, not
  hardcoded — it was `$038438` for this specific snapshot's `A5=$182b4`), not from `$038338`.
- Uncommitted work left behind: none of this session's own. `CLAUDE.md`, `sessions/README.md`,
  `sessions/powermonger.md` still show modified in `git status` — belong to the concurrent
  "Training efficiency (2)" session, left alone per the shared-resources rule. `.obsidian/` and
  `Cadaver/` are untracked and not this session's to manage.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md` (§60 covers this pass), `graphics.md`,
`ai.md`. Carried over: `mechanics.md` §1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35-59 (movement
collision/proximity mechanism, the icon-panel write chain, the full 72-room world-map/adjacency
graph, the door-connectivity walk, the swapped-disk side-count bug, the Replicants/ST Amigos crack's
Disk 2 swap, the two genuine emulator gaps behind the "crack dispatch bug", the FDC "no data"
workflow fix, and the 59th pass's own resource-manager `$100`-shift fix for the room/door tables).

**This pass (61st, `mechanics.md` §60)**: the 59th pass's "player entity genuinely dead, joystick
input has zero effect" finding was wrong — it read the player slot from `$038338`, which is stale
for the two-disk build by the same `$100` shift §59a already found in the resource manager, just in
a different `A5`-relative field (`56(A5)` instead of `(A5)+96`). Re-derived fresh per snapshot:
`56(A5)` → `$038438` in `past_wall_mounted_90M.snap`. That address holds the exact canonical starting
bbox (`[25,23,19,17]`, matching §19a byte-for-byte) and moves a real 44 units right under a
`kbd ff 08` hold, then stalls on a second hold — genuine collision behaviour, not a dead entity.
`$00e80c`'s boot-time entity-activation call needs no further investigation; it worked.

## Open, in priority order

1. **Does Disk 2 add reachable content beyond the known 72-room map?** This is the question §59
   originally set out to answer and is now actually answerable, since the player can be driven for
   real. Resolve the current room via `164(A5)` (`$6c00a` in this snapshot) plus `door_walk.py`'s
   graph, drive the player through doors using `56(A5)`'s corrected address to confirm movement at
   each leg, and look for anything not already known from the one-disk crack's 72-room map (new
   items, NPCs, dialogue, rooms outside the 72). Proof: a `snap_render.py` screenshot or a status-bar
   read of something absent from the one-disk crack's own documented content.
2. Which of the 13 (of 14) `$ff8201`-touching call sites other than the room-crossing path actually
   fires. Not needed to close anything above.
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

- **Any `A5`-relative pointer field, not just the `(A5)+96` resource-manager table, is build-
  relocatable and must be re-derived fresh from the live snapshot, never hardcoded from a value read
  once on a different build.** The 59th pass proved this for the type-3/4 resource tables
  (`(A5)+96`); this pass found the identical `$100` shift in `SpriteObjectArrayPtr_A5Plus56`
  (`56(A5)`) — an unrelated field, same root cause. Before trusting any address this workstream has
  ever hardcoded (`$038338` and any other absolute address quoted as a fact rather than derived from
  a register in the current session), re-check it against the current snapshot's own `A5` first.
- **A live register sampled at a breakpoint can be a per-iteration loop pointer, not a stable base
  address — confirm stability with two widely-spaced samples before building on it, and never trust
  a raw memory re-read at that address after millions of unsynced steps.** This pass's first probe
  (`A6=$0003896a` at `$00d93c`'s call site) looked stable across one 8.7M-step gap, but the entry it
  pointed at is one of several processed a few dozen steps apart within the same frame; reading that
  fixed address again after a further 3M unsynchronized steps returned `$ffffffff` — not because the
  entity died, but because a *different* entry now occupied that same iteration slot. The reliable
  fix was the `A5`-relative field re-derivation (the trap above), not the sampled register.
- **A resource-manager-derived address (anything reached via a fixed `A5`-relative field, §38a/§60b)
  is not a fixed constant across builds - a different crack/relocation shifts the whole table or
  buffer.** Always resolve it fresh from the live snapshot's own `A5` rather than hardcoding a value
  read once from one build (59th pass: the resource manager itself shifted `$100`; 61st pass: the
  unrelated sprite-array pointer field shifted by the identical `$100`).
- **A `.snap` does not remember which disk is mounted in drive A** (`MMU.LoadDiskA`'s own doc
  comment: deliberately excluded, "external, physical-world state"). `resume`ing any snapshot
  starts with `diskA = None` until the REPL's own `disk <path>` re-mounts one (or `--disk-a`/
  `ATARI_DISK_A` was passed at process start) - stepping forward without it makes every FDC sector
  read fail "no data", indistinguishable from a genuinely absent sector or a real FDC gap unless you
  think to check (58th pass). Always issue `disk <path>` right after `resume`ing a snapshot that
  was taken with a real disk swapped in, before stepping forward.
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
  not slow progress - check what condition it's blocked on.
- **A rendered frame that "looks like" a known gameplay screenshot, or a main loop that runs and
  draws every frame, is not proof the game state is actually live and interactive** - check the
  entity data itself (and make sure you're reading it from a correctly-derived address, per the
  traps above) before concluding input has no effect (59th/61st pass).
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

Item 1 is the priority and is now genuinely tractable: with the player entity live via the corrected
`56(A5)` address, drive it through `door_walk.py`'s 72-room graph for real and look for anything Disk
2 adds beyond the one-disk crack's known content. Start from
`scratchpad/cadaver/past_wall_mounted_90M.snap`, re-mount Disk 2, and re-derive `56(A5)` fresh rather
than reusing `$038438` verbatim (it's this snapshot's value, not a constant). No emulator rebuild or
reverification is needed first - nothing in `*.fs` changed this pass. Prompt: `/resume cadaver`.
