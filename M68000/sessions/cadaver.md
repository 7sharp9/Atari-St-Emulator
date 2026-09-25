# Cadaver: handoff

Updated 2026-09-25 by the session that ended at commit `a700060` (62nd pass), which proved the
61st pass's corrected addresses drive a real room crossing in the two-disk build: CAVERN→TUNNEL via
the documented Right→Up zigzag, `164(A5)` flipping from `$6c00a` to `$6c072` (`world_map.py`'s own
TUNNEL slot address). A pixel diff of the arrival frame against the one-disk build's own
`room2_tunnel_entry.png` milestone shows the same room, same art (the 1,552/64,000-pixel difference
is explained by player position, not content) — so this crossing proves the drive technique works,
but adds a second independent confirmation (alongside §59b's already-identical room table) that
Disk 2 contributes nothing new to the two rooms reachable from this snapshot. The open question has
narrowed from "is there an undiscovered room" to "is Disk 2's content gated behind something not yet
exercised from here" — see Open item 1.

Prior pass's summary (61st, `57c8ad4`): closed the 59th/60th pass's open item 1 itself — the player
entity was never dead, `$038338` was stale by the same `$100` shift the 59th pass found in the
resource manager; the correctly-resolved `56(A5)` (`$038438` in this build) holds the live player
slot and moves under real input.

## Resume point

- Last commit of this workstream: `a700060` "cadaver: item 1 narrowed — TUNNEL room art confirmed
  unchanged from one-disk build (62nd pass, cont.)". No emulator source changed this pass either, so
  no rebuild or regression-net run is needed before building on it.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). This pass's additions:
  - `probe_regs_disk2.repl`/output: confirms `A5=$182b4` right after `resume`ing
    `past_wall_mounted_90M.snap` and mounting Disk 2 — same as the 61st pass's own snapshot state.
  - `probe_cavern_tunnel_disk2.repl`/`disk2_cavern_tunnel_probe1.snap`: a straight `kbd ff 02`
    (Down) hold from the start — moves the bbox 11 units then stalls on a repeat hold, room pointer
    unchanged (`$6c00a`, still CAVERN). Kept as a negative result: Down alone does not cross here.
  - `probe_zigzag_disk2.repl`/`disk2_zigzag_probe1.snap`/`disk2_tunnel_probe1.png`: the
    Right(1.2M)→Up(0.5M) zigzag that does cross — `164(A5)` `$6c00a`→`$6c072`, screenshot confirms
    `TUNNEL`/`DAY 1`.
  - Carried over unchanged from the 61st pass and earlier: `probe_sprite_d93c.*`,
    `probe_arrayptr_field.*`, `probe_realarray_038438.*`, `retest_movement_038438.*`,
    `realbase_038438_after_right.snap`, `probe_sprite_realbase.*`, `retest_movement_bpc.*`,
    `retest_movement_realbase.*`, `realbase_after_right.snap`, `probe_sprite.*`, the `drive_*`/
    `full_trace_fdc*` files.
- **Start from**: `scratchpad/cadaver/past_wall_mounted_90M.snap` (PC=`$00015254`, Disk 2 not yet
  mounted — `disk ../Cadaver/disk2_replicants/disk2.st` first) for a fresh CAVERN start, or
  `scratchpad/cadaver/disk2_zigzag_probe1.snap` (PC=`$00006cb2`) to resume already standing in
  TUNNEL. Re-derive `56(A5)` (player) and `164(A5)` (current room) fresh from whichever snapshot is
  used — both are `$182ec`/`$18358` off `A5=$182b4` for these two specific snapshots, not constants.
- Uncommitted work left behind: none of this session's own. `CLAUDE.md`, `sessions/README.md`,
  `sessions/powermonger.md` still show modified in `git status` — still the concurrent "Training
  efficiency (2)" session's, left alone. `.obsidian/` and `Cadaver/` are untracked and not this
  session's to manage.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md` (§61 covers this pass), `graphics.md`,
`ai.md`. Carried over: `mechanics.md` §1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35-60 (movement
collision/proximity mechanism, the icon-panel write chain, the full 72-room world-map/adjacency
graph, the door-connectivity walk, the swapped-disk side-count bug, the Replicants/ST Amigos crack's
Disk 2 swap, the two genuine emulator gaps behind the "crack dispatch bug", the FDC "no data"
workflow fix, the two-disk build's `$100`-shift bugs in both the resource manager and the sprite-
array pointer field).

**This pass (62nd, `mechanics.md` §61)**: with the player and current-room fields both correctly
re-derived, drove a real CAVERN→TUNNEL crossing in the two-disk build using the same Right→Up
zigzag §32 proved on the one-disk build. `164(A5)` genuinely flips from CAVERN's rec address
(`$6c00a`) to TUNNEL's (`$6c072`, `world_map.py`'s own slot-1 address). A pixel diff of the arrival
frame against the one-disk build's own `room2_tunnel_entry.png` shows the same room (1,552/64,000
differing pixels, explained by player position) — so this crossing proves the *technique*, and adds
a second independent confirmation, alongside §59b's already-identical room table, that Disk 2
contributes nothing to the two rooms reachable from this snapshot. `2516(A5)` (§32a's unconfirmed
"day-count/variant selector" candidate) reads `100` here, inconsistent with it being a literal small
day index — flagged, not resolved. A plain Down hold from the start moves the player but stalls on
an in-room obstacle without crossing — recorded as a negative result so it isn't retried.

## Open, in priority order

1. **Does Disk 2 add reachable content beyond the known 72-room map?** Narrowed, not closed: two
   independent checks (the room table itself, §59b; this pass's rendered-art pixel diff) now agree
   Disk 2 adds nothing to what's spatially reachable from `past_wall_mounted_90M.snap`. The question
   is shifting toward *whether Disk 2's content is reachable from here at all*. Two concrete next
   tests, either would move this forward:
   - Drive to a room from `door_walk.py`'s graph that is *not* already screenshotted/documented in
     the one-disk crack's own milestones (check `reversing/cadaver/README.md`'s files table and
     `graphics.md`), and pixel-diff or read its status-bar text the same way this pass did for
     TUNNEL. No bbox-to-world-grid calibration exists (Open item 2), so treat each crossing as
     directional trial-and-error (Right/Up/Down/Left holds, checking `164(A5)` after each) rather
     than a computed path.
   - Find where the boot-time Disk1→Disk2 swap that built this snapshot actually reads Disk 2's
     data (an FDC trace, `ATARI_TRACE_FDC=1`, around the "expanding data"/"loading data" boot phase
     the README already documents), and check whether it's a one-time asset load (already reflected
     in the current snapshot, meaning Disk 2's difference is purely graphical/data assets already
     baked into what's on screen, not new rooms — plausible given a "levels disk" framing predating
     any structural room-table difference) versus something gated behind further game progress (a
     day counter, a specific puzzle) that hasn't fired yet.
2. No calibration exists between `world_map.py`'s world-grid room rectangles (coarse, e.g. CAVERN
   `[12,18]-[22,28]`) and the player bbox's own coordinate scale (e.g. `[25,23,19,17]`, up to
   `[69,23,63,17]` after one full rightward leg) — door candidate coordinates from `door_walk.py`
   can't yet be turned into "hold direction X for N steps" without trial and error. Worth deriving
   once item 1 needs more than a handful of crossings; not needed for item 1 itself if trial-and-
   error crossings suffice.
3. `2516(A5)`'s role is still unconfirmed — reads `100` in this snapshot, not a small "Day 1"-style
   index, so §32a's "day-count/variant selector" guess is unproven either way. Only worth resolving
   if item 1's boot-time-load hypothesis needs a real day/progress counter identified.
4. Which of the 13 (of 14) `$ff8201`-touching call sites other than the room-crossing path actually
   fires. Not needed to close anything above.
5. `disk_layout.py`'s blank/data classifier only catches single-byte fills, not short-period
   repeats (§52's 3-byte cycle) - not yet extended.
6. No `.stx`->`.st` converter exists in `tools/`. Only worth writing for a `.stx`-only release.
7. The five crack variants extracted in the 55th pass and the untried single-sided
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
  once on a different build.** Proven for the type-3/4 resource tables (`(A5)+96`, 59th pass), the
  sprite-array pointer (`56(A5)`, 61st pass), and now the current-room field (`164(A5)`, this pass) -
  three unrelated fields, same root cause. Before trusting any address this workstream has ever
  hardcoded, re-check it against the current snapshot's own `A5` first.
- **`world_map.py`'s room rectangles and the player bbox use different coordinate scales with no
  known conversion yet** - a room's world-grid rect (e.g. CAVERN `[12,18]-[22,28]`, 10 units wide) is
  roughly 4-6x coarser than the bbox's own units (a full rightward leg moves the bbox 44 units). A
  door candidate's `(cx,cy)` from `door_walk.py` cannot yet be turned directly into a movement plan;
  crossings so far were found by replaying/adapting known recipes (§32's zigzag) and checking
  `164(A5)`, not by computing a path from the coordinates.
- **A live register sampled at a breakpoint can be a per-iteration loop pointer, not a stable base
  address — confirm stability with two widely-spaced samples before building on it, and never trust
  a raw memory re-read at that address after millions of unsynced steps.** (61st pass, `A6=$0003896a`
  at `$00d93c` looked stable across one 8.7M-step gap but was a live loop-iteration pointer.)
- **A resource-manager-derived address (anything reached via a fixed `A5`-relative field) is not a
  fixed constant across builds** - always resolve it fresh from the live snapshot's own `A5` rather
  than hardcoding a value read once from one build.
- **A `.snap` does not remember which disk is mounted in drive A** - always issue `disk <path>`
  right after `resume`ing a snapshot that was taken with a real disk swapped in, before stepping
  forward.
- **A blind linear/static disassembly at a `jsr` target that lands in what looks like a data
  region is not reliable evidence that the target really is stale data misread as code** - step
  through it live before concluding it's misread data rather than an emulator gap or a genuine
  probe (57th pass).
- **`run.ps1`'s subcommand names are aliases, not raw argv** (`CLAUDE.md`'s Rules section has the
  mapping) - `snap <N> <path>` is NOT valid raw argv; the raw form is `<N> snapshot <path>`.
- Stepping past a reserved/undefined-opcode CPU-detection probe or a trace-mode decrypt loop can
  legitimately take tens of millions of steps before the interesting part starts - check `r` twice
  a few hundred thousand steps apart first before assuming a hang.
- **A rendered frame that "looks like" a known gameplay screenshot, or a main loop that runs and
  draws every frame, is not proof the game state is actually live and interactive** - check the
  entity data itself (from a correctly-derived address) before concluding input has no effect.
- `bp <hexaddr> [maxSteps]` takes at most 2 arguments - `bpc <addr> <n> [maxSteps]` if an Nth-hit
  count is needed.
- The REPL's `disk <path>` command mounts a *relative* path from the process's own working
  directory (typically `M68000/`), not relative to wherever the snapshot or driving script lives.
- `$5a99` is not a room-transition signal; use `164(A5)` (this pass) or `(A5)+1166` (§38b, an older
  build's offset for the same kind of field) instead - re-derive per snapshot, don't assume either
  numeric offset is a constant across builds.
- A live snapshot's static memory alone can settle a "what does routine X compute" question without
  running the emulator forward; it canNOT settle "is this address really data, or an emulator gap
  disguised as data", or "is this FDC failure real, or is the disk just not mounted" - both need a
  live step.
- `gfxview.load_ram(path)` returns `(ram_bytes, base)`. `gfxview.detect_palettes(ram, base)` returns
  a list of dicts, not tuples.
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

Item 1 is still the priority and has narrowed: two independent checks this pass and last (room
table geometry, TUNNEL's rendered art) found Disk 2 identical to the one-disk build for everything
reachable from `past_wall_mounted_90M.snap`. Two productive directions, pick whichever fits the
session's time budget: (a) drive to a room not already documented by the one-disk crack's own
milestones and check it the same way (trial-and-error directional holds, no bbox/world-grid
calibration exists — see Open item 2), or (b) trace the boot-time Disk1→Disk2 swap itself
(`ATARI_TRACE_FDC=1` around the documented "expanding data" boot phase) to see whether Disk 2's
whole contribution is a one-time asset load already baked into this snapshot, which would settle
item 1 as "no additional reachable content" rather than "not yet found". No emulator rebuild or
reverification needed first - nothing in `*.fs` changed this pass or last. Prompt: `/resume cadaver`.
