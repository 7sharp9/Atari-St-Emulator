# Cadaver: handoff

Updated 2026-09-25 by the session that ended at commit `bd6bb93` (60th pass), a narrow follow-up
to the 59th pass's queued item 2: `door_walk.py` had the same stale-resource-address bug the 59th
pass fixed in `world_map.py` (a broken import of now-removed `INDEX_TABLE`/`DATA_AREA` constants,
plus its own hardcoded one-disk-build `TYPE4_INDEX`/`TYPE4_DATA` for type-4 door descriptors). Both
now resolve dynamically via `world_map.resource_type()`, matching mechanics.md §59a's fix shape.
No new investigation this pass - item 1 (player entity not live) is untouched and still the
priority.

Prior pass's summary (59th, `e82924e`): resumed from the 58th-pass handoff's item 1 ("does Disk 2
supply content beyond the one-disk crack's 72-room map") and drove real player input for the first
time from `past_wall_mounted_90M.snap`. Found the room table is unchanged (same 72 rooms as the
one-disk build) and, separately, that the game is not in normal interactive gameplay at that
snapshot at all - the player/entity sprite array is empty and joystick input has no effect. Also
fixed the `world_map.py` stale-address bug described above.

## Resume point

- Last commit of this workstream: `bd6bb93` "cadaver: fix door_walk.py's stale hardcoded type-3/4
  resource addresses (60th pass)". No emulator source changed this pass either, so no rebuild or
  regression-net run is needed before building on it.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). This pass's additions:
  - `drive_explore.repl` / `.log`, `drive_right{1..5}.snap` / `.png`: five `kbd ff 08` (joystick-1
    right, make) / `s 3000000` / `kbd ff 00` (release) / `s 500000` cycles from
    `past_wall_mounted_90M.snap` with Disk 2 mounted first. Current-room field (`164(A5)`) and the
    rendered frame are unchanged across all five - no movement, no room change.
  - `drive_dismiss.repl` / `.log`, `drive_dismiss{1,2}.snap` / `.png`: same test, but trying a
    space keypress first (in case a "found the Silver Coin" notice was blocking movement input)
    before the same right-hold. Same negative result.
  - `probe_sprite.repl` / `.log`: `bpc 80cc 1 20000000` (the sprite/HUD blit routine, §32c) from
    the same snapshot with a joystick-right held - hits within 562k steps, so the main loop is
    alive and drawing every frame; `A6=$88` at that particular hit, not `$038338`, but this
    specific call site wasn't confirmed to be §32c's outer sprite-list walker rather than one of
    the blit's other callers (open, see mechanics.md §59d).
  - `full_trace_fdc.log` / `full_trace_mounted_fdc.log`, `past_wall_mounted_{30,60,90}M.snap`,
    `push_past_wall.repl` / `.log`: carried over from the 58th pass, unchanged this session.
- **Start from**: `scratchpad/cadaver/past_wall_mounted_90M.snap` (PC=`$00015254`, Disk 2 mounted,
  sitting in the Day 1/Boat/Cavern room, sprite array empty) - or re-derive from
  `agent_disk2_wall/before_jsr.snap` with `disk ../Cadaver/disk2_replicants/disk2.st` issued first,
  per the 58th pass's recipe.
- Uncommitted work left behind: none of this session's own. `CLAUDE.md`, `sessions/README.md`,
  `sessions/powermonger.md` still show modified in `git status` - belong to the concurrent
  "Training efficiency (2)" session, left alone per the shared-resources rule. `.obsidian/` and
  `Cadaver/` are untracked and not this session's to manage.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md` (§59 covers both the 59th and this 60th
pass), `graphics.md`, `ai.md`. Carried over: `mechanics.md` §1-6, 27, 31a, 32a/b, 33b/34b, 34a,
35-58 (movement collision/proximity mechanism, the icon-panel write chain, the full 72-room
world-map/adjacency graph, the door-connectivity walk, the swapped-disk side-count bug, the
Replicants/ST Amigos crack's Disk 2 swap, the two genuine emulator gaps behind the "crack dispatch
bug", and the 58th pass's own REPL-workflow fix for the FDC "no data" wall).

**This pass (60th)**: `door_walk.py` now resolves both type 3 (rooms) and type 4 (door
descriptors) via `world_map.resource_type()` instead of importing removed module constants /
hardcoding one-disk-build addresses. Re-run against `past_wall_mounted_90M.snap` (Disk 2 build):
71 distinct doors across 72 rooms, every resolved destination is `self` or edge-adjacent to its
owning room - no `NON-ADJACENT (teleport)` anomalies, consistent with a correctly-resolved static
door table.

**59th pass, `mechanics.md` §59**:

- `world_map.py`'s hardcoded type-3 index-table/data-area addresses (`$4ac36`/`$6bf0a`) were the
  one-disk build's; the two-disk Replicants build's whole resource manager sits `+$100` past them
  (confirmed across the first 9 resource types, table by table). Fixed to resolve type 3's
  pointers fresh from each snapshot's own `(A5)+96` (`resource_type()` helper) instead of
  hardcoding them.
- Re-run against the Disk 2 build: **same 72 rooms, same rectangles, same 117-pair adjacency graph
  as the one-disk build** - the room table itself supplies nothing new.
- Five real `kbd ff 08`/`kbd ff 00` right-holds (15M steps total) and a space-then-right variant
  from `past_wall_mounted_90M.snap` produced **zero movement, zero room change, pixel-identical
  rendered frames** - not a hang (the main loop is alive, frames keep flipping, the sprite/HUD blit
  routine fires within 562k steps of a fresh press), but genuinely unresponsive to input.
- The likely cause: `$038338` (§19a/§32c's documented player/entity sprite array base, player at
  slot 0) reads **all-zero** in `past_wall_mounted_90M.snap` and every snapshot driven from it -
  where every normal one-disk-build gameplay snapshot has real data there. Not yet settled whether
  the address itself is stale for this build (parallel to the `world_map.py` bug) or the address is
  still correct and this build's boot-time entity-activation call (`$00e80c`, §31) never ran on the
  step-forward-from-mid-protection-chain path that reached this snapshot.

## Open, in priority order

1. **Get the player entity genuinely live, then retest movement.** Two candidate next steps,
   either closes this: (a) re-derive the sprite array's *current* address the way §59a fixed the
   room table - breakpoint the sprite-list walker at `$00d93c`'s `bsr $7dd6` call site (§32c) and
   read its own `A6` directly, not the deeper generic blit at `$0080cc` (this pass's one `bpc 80cc`
   sample gave `A6=$88`, implausibly low, and wasn't confirmed to be the right call site); or (b)
   if `$038338` is confirmed still correct, trace why `$00e80c`'s activation call doesn't fire on
   `past_wall_mounted_90M.snap`'s lineage, and whether a genuine cold boot with Disk 2 pre-mounted
   (rather than a mid-flight disk swap replayed forward from `before_jsr.snap`) reaches a state
   where it does. This subsumes the old "drive input to explore beyond the 72-room map" framing -
   there's no point walking anywhere until the player entity exists.
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

- **A resource-manager-derived address (anything reached via `(A5)+96`'s type-record table, §38a)
  is not a fixed constant across builds - a different crack/relocation shifts the whole table.**
  Always resolve it fresh from the live snapshot's own `(A5)+96` rather than hardcoding a value
  read once from one build (59th pass: the two-disk Replicants build's resource manager sits
  `+$100` past the one-disk build's; `world_map.py` hardcoded the old value and silently misread
  garbage as a valid but nonsensical room table until fixed). This is a narrower, address-specific
  case of the more general rule below about heap/runtime addresses.
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
- **The main loop running and drawing frames every cycle does not mean the game is in normal
  interactive gameplay** - it can be alive, flipping buffers, and calling the sprite/HUD blit
  routine every frame while the player/entity array is completely empty and input has zero effect
  (59th pass, `past_wall_mounted_90M.snap`). A rendered frame that "looks like" a known gameplay
  screenshot is not proof the game state is actually live and interactive; check the entity array,
  not just the picture.
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

Item 1 is the priority: get the player/entity sprite array genuinely live from
`scratchpad/cadaver/past_wall_mounted_90M.snap` before attempting any more movement tests - either
re-derive the sprite array's current address via `$00d93c`'s own call site (not the deeper generic
blit), or confirm `$038338` is still correct and trace why the boot-time entity-activation call
(`$00e80c`) never fired on this snapshot's lineage. No emulator rebuild or reverification is needed
first - nothing in `*.fs` changed this pass. Prompt: `/resume cadaver`.
