# Cadaver: handoff

Updated 2026-09-25 by the session that ended at this commit (64th pass), which ran the 63rd pass's
own proposed next step — drive to an undocumented room from `disk2_zigzag_probe1.snap` with
`ATARI_TRACE_FDC=1` armed — and found there is no undocumented room reachable to drive to. Running
`py/door_walk.py` fresh against that exact two-disk snapshot shows the only three door ids touching
CAVERN or TUNNEL are: `0x32` (the CAVERN↔TUNNEL link already driven live in §61), `0x3b` (CAVERN's
own east door, already live-tested in §13/17th-pass and shown to resolve to "already resident" — this
pass's fresh geometric read confirms why: candidate `(22,20)` sits inside CAVERN's own rectangle, so
it is a permanent self-loop by construction, not a state-dependent miss), and `0x33` (TUNNEL's second
entry, sentinel target `$ffff` — per §27c this branch never reaches the room-load path at all,
structurally inert). A live check on `0x33` anyway (hold Up 3M then 6M more steps from
`disk2_zigzag_probe1.snap`, then Left 1.5M to rule out a stuck-input false negative, then Up again)
found the player's own bbox (`$038438`) never moved past `[23,12,17,6]`→`[14,12,8,6]`(Left only) and
FDC activity stayed at zero throughout. Net: TUNNEL's north wall has no live-triggerable exit at any
x tried, matching §10b/§10c's own one-disk-build finding that this table has no third live entry —
this pass confirms the two-disk build's portal table matches that shape. See `mechanics.md` §63 and
Open item 1.

Prior pass's summary (63rd, `37ff4b8`): traced the FDC across the 62nd pass's own remaining open
window — resumed `past_wall_mounted_30M.snap`, remounted Disk 2, stepped the remaining 60M steps
under `ATARI_TRACE_FDC=1` (empty trace, `PC=$00015254` matching the from-scratch 90M-step run), then
re-ran §61's own CAVERN→TUNNEL zigzag under the same flag (also empty). Net: Disk 2's whole
contribution is a one-time load, complete by step 30M of boot, never touched again by idle time or by
a real room crossing.

## Resume point

- Last commit of this workstream: this session's own handoff commit, on top of `37ff4b8` "cadaver:
  item 1 further narrowed — Disk 2's whole contribution is a one-time boot load (63rd pass)". No
  emulator source changed this pass either, so no rebuild or regression-net run is needed before
  building on it.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). This pass's additions:
  - `probe_check_addrs.repl`: no-step read of `182ec`/`18358` off `disk2_zigzag_probe1.snap`'s
    `A5=$182b4`, confirming the player-array pointer (`$038438`) and current-room field (`$6c072`,
    TUNNEL) are unchanged from the 62nd/63rd pass's own derivation for this snapshot.
  - `probe_room2_up.repl`/`.log`/`_fdc.log`/`.snap`: 3M steps holding Up from `disk2_zigzag_probe1.
    snap` — room field unchanged (`$6c072`), FDC log empty (0 lines).
  - `probe_room2_up2.repl`/`.log`/`_fdc.log`/`.snap`: same, 6M steps, with a bbox read (`$038438`)
    before/after — `[23,12,17,6]` unchanged both times, FDC log empty.
  - `probe_room2_leftup.repl`/`.log`/`_fdc.log`/`.snap`: 1.5M Left then 3M Up — Left moves the bbox
    9 units (`[23,12,17,6]`→`[14,12,8,6]`, confirming input still works), but Up from the new x is
    still fully blocked (bbox unchanged) and FDC stays silent.
  - Carried over unchanged from the 63rd pass and earlier: `probe_fdc_30to90M.*`,
    `probe_zigzag_fdc_check.*`, `probe_regs_disk2.*`, `probe_cavern_tunnel_disk2.*`/
    `disk2_cavern_tunnel_probe1.snap`, `probe_zigzag_disk2.repl`/`disk2_zigzag_probe1.snap`/
    `disk2_tunnel_probe1.png`, `probe_sprite_d93c.*`, `probe_arrayptr_field.*`,
    `probe_realarray_038438.*`, `retest_movement_038438.*`, `realbase_038438_after_right.snap`,
    `probe_sprite_realbase.*`, `retest_movement_bpc.*`, `retest_movement_realbase.*`,
    `realbase_after_right.snap`, `probe_sprite.*`, the `drive_*`/`full_trace_fdc*`/
    `full_trace_mounted*` files, `past_wall_mounted_{30,60,90}M.snap`.
- **Start from**: `scratchpad/cadaver/past_wall_mounted_90M.snap` (PC=`$00015254`, Disk 2 not yet
  mounted — `disk ../Cadaver/disk2_replicants/disk2.st` first) for a fresh CAVERN start, or
  `scratchpad/cadaver/disk2_zigzag_probe1.snap` (PC=`$00006cb2`) to resume already standing in
  TUNNEL. Re-derive `56(A5)` (player) and `164(A5)` (current room) fresh from whichever snapshot is
  used — both are `$182ec`/`$18358` off `A5=$182b4` for these two specific snapshots, not constants.
  Neither snapshot has a further real door to drive through — see Open item 1 — so the next session's
  first move should be deciding whether to keep pushing item 1 (needs a new live state beyond these
  two rooms, not another crossing from them) or moving to a different open item.
- Uncommitted work left behind: none of this session's own. `CLAUDE.md`, `sessions/README.md`,
  `sessions/powermonger.md` still show modified in `git status` — still the concurrent "Training
  efficiency (2)" session's, left alone. `.obsidian/` and `Cadaver/` are untracked and not this
  session's to manage.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md` (§63 covers this pass), `graphics.md`,
`ai.md`. Carried over: `mechanics.md` §1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35-62 (movement
collision/proximity mechanism, the icon-panel write chain, the full 72-room world-map/adjacency
graph, the door-connectivity walk, the swapped-disk side-count bug, the Replicants/ST Amigos crack's
Disk 2 swap, the two genuine emulator gaps behind the "crack dispatch bug", the FDC "no data"
workflow fix, the two-disk build's `$100`-shift bugs in both the resource manager and the sprite-
array pointer field, a real CAVERN→TUNNEL crossing driven live with the corrected addresses, Disk 2's
one-time boot-time load with zero further FDC activity through a real crossing).

**This pass (64th, `mechanics.md` §63)**: ran the 63rd pass's own proposed test — drive to an
undocumented room with `ATARI_TRACE_FDC=1` armed — and found it inapplicable: `door_walk.py` run
fresh against `disk2_zigzag_probe1.snap` shows CAVERN and TUNNEL's only three door ids are the
already-used CAVERN↔TUNNEL link, CAVERN's own east door (already live-tested in §13, and now shown by
the game's own door-descriptor mechanism, §27c, to be a permanent geometric self-loop, not a
state-dependent miss), and TUNNEL's second entry (a `$ffff` sentinel that §27c's code read shows
never reaches a room-load call at all). A live check on the last one anyway — Up 3M then 6M more
steps, then Left 1.5M to rule out a stuck-input false negative, then Up again — found TUNNEL's north
wall solid at every x tried and FDC silent throughout. Three independent subsystems (room table §59b,
door/portal mechanism §27c/this pass, FDC §62/§63) now agree nothing reachable from either driveable
room ever surfaces a fourth.

## Open, in priority order

1. **Does Disk 2 add reachable content beyond the known 72-room map?** As close to closed as this
   spike can get without a new starting state: four independent checks (room table, §59b; rendered
   art, §61; full FDC trace, §62/63rd pass; the door/portal mechanism itself, §63/this pass) all agree
   nothing reachable from `past_wall_mounted_90M.snap` or `disk2_zigzag_probe1.snap` ever surfaces a
   fourth room, and between them they explain *why* from three unrelated angles (nothing left to
   load, nothing left to read, no door left to walk through) rather than just reporting a string of
   negatives. What's left is a **structural gap, not a testing gap**: CAVERN and TUNNEL are the only
   two rooms this spike has ever put a live player in, and both are provably dead-ended by the door
   mechanism itself (§27c) — no amount of further directional trial-and-error from either one can
   reach a third room. Making further progress on this item needs either (a) a live snapshot standing
   in some *other* room (there is no known route to one from here — TUNNEL's lever puzzle was already
   exhaustively dead-ended in the one-disk build across the 12th-41st passes), or (b) reversing
   whatever deeper in-game trigger (day-progression, an explicit disk-swap prompt) might populate the
   type-8 registration table this spike has only ever seen empty (§27d) — neither is a quick follow-up
   test, both are open-ended reversing work. Recommend treating this as closed for practical purposes
   (Disk 2 contributes a one-time boot-time asset load and nothing else, as far as this spike can
   drive) unless Dave wants the open-ended push into (a) or (b).
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

Item 1 has run out of cheap next tests: this pass found that CAVERN and TUNNEL — the only two rooms
this spike has ever put a live player in — have no door capable of reaching a third room at all, by
the game's own proven door-descriptor mechanism (§27c), not just none tried yet. Combined with the
room-table match (§59b), the rendered-art match (§61) and the full FDC silence (§62/§63rd pass), four
independent subsystems now agree nothing reachable from here ever surfaces a fourth room. Recommend
raising this with Dave as effectively closed (Disk 2 = one-time boot-time asset load, nothing more, as
far as this spike can drive) unless he wants to fund the open-ended work of either reaching a new room
via TUNNEL's already-exhaustively-dead-ended lever puzzle, or reversing the still-unpopulated type-8
registration table's real trigger — neither is a quick follow-up. If he'd rather keep pushing, start
by re-reading Open item 1's own "what's left" paragraph, which names both directions. No emulator
rebuild or reverification needed first - nothing in `*.fs` changed this pass or the last three.
Prompt: `/resume cadaver`.
