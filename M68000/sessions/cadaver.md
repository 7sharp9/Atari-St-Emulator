# Cadaver: handoff

Updated 2026-09-25 by the session that ended at this commit (63rd pass), which ran the 62nd pass's
own second next-step: traced the FDC across the full remainder of the boot-to-`past_wall_mounted_
90M.snap` window and across a real room crossing, and found zero further disk activity in either.
§58 had already shown 121 sector reads in the first 30M boot steps; this pass resumed
`past_wall_mounted_30M.snap`, remounted Disk 2, and stepped the remaining 60M under
`ATARI_TRACE_FDC=1` — an empty trace, landing at the same `PC=$00015254` the from-scratch 90M-step
run reaches (reproducible, so the empty trace is a genuine negative, not a broken harness). Re-running
§61's own CAVERN→TUNNEL crossing under the same trace flag confirms the crossing itself touches the
FDC zero times too. Net: Disk 2's whole contribution is a one-time load, complete by step 30M of
boot, never touched again by idle time or by the one player-driven action tested — the one-time-load
reading for item 1 is now evidence-backed, not just plausible. See Open item 1.

Prior pass's summary (62nd, `a700060`): proved the 61st pass's corrected addresses drive a real room
crossing in the two-disk build — CAVERN→TUNNEL via the documented Right→Up zigzag, `164(A5)`
flipping from `$6c00a` to `$6c072` (`world_map.py`'s own TUNNEL slot address). A pixel diff of the
arrival frame against the one-disk build's own `room2_tunnel_entry.png` milestone showed the same
room, same art (the 1,552/64,000-pixel difference explained by player position, not content) — a
second independent confirmation, alongside §59b's already-identical room table, that Disk 2
contributes nothing new to the two rooms reachable from this snapshot.

## Resume point

- Last commit of this workstream: this session's own handoff commit, on top of `a700060` "cadaver:
  item 1 narrowed — TUNNEL room art confirmed unchanged from one-disk build (62nd pass, cont.)". No
  emulator source changed this pass either, so no rebuild or regression-net run is needed before
  building on it.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). This pass's additions:
  - `probe_fdc_30to90M.repl`/`probe_fdc_30to90M.log`/`probe_fdc_30to90M_fdc.log`: resumes
    `past_wall_mounted_30M.snap`, remounts Disk 2, steps 60M more under `ATARI_TRACE_FDC=1` — the
    FDC log is empty (0 lines), final `PC=$00015254` matches the from-scratch 90M-step run exactly.
  - `probe_zigzag_fdc_check.log`/`probe_zigzag_fdc_check_fdc.log`: re-runs §61's own zigzag crossing
    recipe under the same trace flag — also an empty FDC log, final `PC=$00006cb2` matches
    `disk2_zigzag_probe1.snap` exactly.
  - Carried over unchanged from the 62nd pass and earlier: `probe_regs_disk2.*`,
    `probe_cavern_tunnel_disk2.*`/`disk2_cavern_tunnel_probe1.snap`, `probe_zigzag_disk2.repl`/
    `disk2_zigzag_probe1.snap`/`disk2_tunnel_probe1.png`, `probe_sprite_d93c.*`,
    `probe_arrayptr_field.*`, `probe_realarray_038438.*`, `retest_movement_038438.*`,
    `realbase_038438_after_right.snap`, `probe_sprite_realbase.*`, `retest_movement_bpc.*`,
    `retest_movement_realbase.*`, `realbase_after_right.snap`, `probe_sprite.*`, the `drive_*`/
    `full_trace_fdc*`/`full_trace_mounted*` files, `past_wall_mounted_{30,60,90}M.snap`.
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

Detail in `reversing/cadaver/README.md`, `mechanics.md` (§62 covers this pass), `graphics.md`,
`ai.md`. Carried over: `mechanics.md` §1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35-61 (movement
collision/proximity mechanism, the icon-panel write chain, the full 72-room world-map/adjacency
graph, the door-connectivity walk, the swapped-disk side-count bug, the Replicants/ST Amigos crack's
Disk 2 swap, the two genuine emulator gaps behind the "crack dispatch bug", the FDC "no data"
workflow fix, the two-disk build's `$100`-shift bugs in both the resource manager and the sprite-
array pointer field, a real CAVERN→TUNNEL crossing driven live with the corrected addresses).

**This pass (63rd, `mechanics.md` §62)**: traced the FDC across the 62nd pass's own remaining open
window. §58 (58th pass) had shown 121 sector reads in the first 30M boot steps building toward
`past_wall_mounted_90M.snap`, but never traced the remaining 60M steps. Resuming
`past_wall_mounted_30M.snap`, remounting Disk 2, and stepping 60M more under `ATARI_TRACE_FDC=1`
produced an empty trace — zero further FDC activity — landing at the same `PC=$00015254` the
from-scratch 90M-step run reaches (reproducible, so not a broken harness). Re-running §61's own
CAVERN→TUNNEL zigzag under the same trace flag found the crossing itself touches the FDC zero times
too. Net: Disk 2's whole contribution is a one-time load, complete by step 30M of boot, untouched by
idle time or by the one player-driven action tested.

## Open, in priority order

1. **Does Disk 2 add reachable content beyond the known 72-room map?** Narrowed further this pass:
   three independent checks (the room table itself, §59b; the rendered-art pixel diff, §61; this
   pass's full FDC trace, §62) now agree Disk 2 adds nothing reachable from `past_wall_mounted_90M.
   snap`, and §62 additionally shows *why* — the whole Disk 2 payload loads once in the first 30M
   boot steps and is never read again, not on idle time and not across a real room crossing. The
   remaining gap is narrow: is there a trigger deeper in the game (a day-progression event, an
   explicit in-game "insert levels disk" prompt distinct from this one-time boot swap) that would
   cause a *second* FDC read episode, never yet exercised from this snapshot? One concrete next
   test:
   - Drive to a room from `door_walk.py`'s graph that is *not* already screenshotted/documented in
     the one-disk crack's own milestones (check `reversing/cadaver/README.md`'s files table and
     `graphics.md`), with `ATARI_TRACE_FDC=1` armed throughout, and check both the room's rendered
     content (pixel-diff/status-bar text, as §61 did for TUNNEL) and whether any FDC activity fires
     during the crossing. No bbox-to-world-grid calibration exists (Open item 2), so treat each
     crossing as directional trial-and-error (Right/Up/Down/Left holds, checking `164(A5)` after
     each) rather than a computed path. If several more crossings all stay FDC-silent and land on
     already-known content, that's grounds to close item 1 as "no additional reachable content" —
     the one-time-load reading — rather than keep treating it as open.
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

Item 1 is still the priority and has narrowed further: three independent checks now (room table
geometry, TUNNEL's rendered art, this pass's full FDC trace) agree Disk 2 contributes nothing
reachable from `past_wall_mounted_90M.snap`, and the FDC trace explains why — the whole Disk 2 load
is a one-time boot-time event, complete by step 30M, never touched again by idle time or by a real
room crossing. The one productive remaining direction: drive to a room not already documented by the
one-disk crack's own milestones, with `ATARI_TRACE_FDC=1` armed throughout, and check both its
content (trial-and-error directional holds, no bbox/world-grid calibration exists — see Open item 2)
and whether the crossing itself fires any FDC activity. If several such crossings all stay
FDC-silent and land on already-known content, that's enough to close item 1 outright as "no
additional reachable content", not just narrow it further. No emulator rebuild or reverification
needed first - nothing in `*.fs` changed this pass or last two. Prompt: `/resume cadaver`.
