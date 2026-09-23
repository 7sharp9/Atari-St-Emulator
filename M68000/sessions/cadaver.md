# Cadaver: handoff

Updated 2026-09-23, migrated into the handoff regime from the root `next_session.md` and the memory
RESUME block (both written by the 31st pass). No session has worked Cadaver since.

## Resume point

- Last commit of this workstream: `416a0b1` (29th pass, 2026-09-17).
- **Uncommitted work left behind:** `M68000/reversing/cadaver/mechanics.md` holds sections 30 and 31
  (+243 lines, the 30th and 31st passes), never committed. Scratch snapshots and renders in
  `reversing/cadaver/` are untracked: `room_hack_test*.snap/png`, `room_hack_stepped.*`,
  `room_hack_after.snap`, `tunnel_return_cross.*`, `tunnel_return_settled.*`,
  `gameplay_empire_reference.png`, `movement_before/after_right.png`, `blocks.txt`, `cg.dot`,
  `cadaver_events.bin`. The first step of the next session is to review and commit `mechanics.md`
  (named files only), deciding which of the scratch files are milestones worth keeping.
- Disk: the Empire one-disk release only, `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st`
  (sha256 in `reversing/cadaver/README.md`). The Medway Boys/ZIPPY crack corrupts level data on the
  disk-2 swap (its own anti-debug patch); do not use it. `Cadaver/` also holds the two-disk Image
  Works original (disk 2 labelled "(Level)"), unused so far.
- Start from: `room_hack_test2_stepped.snap` (room-activation hack applied, runs stable) or
  `tunnel_return_cross.snap` / `tunnel_return_settled.snap` (a real TUNNEL -> CAVERN crossing
  mid-flight and settled). Resume with `resume <path> repl --disk-a "<the .st>"`.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`.

- Collision, graphics compositing and the entity/object-verb bytecode interpreter are disassembled
  and documented (`mechanics.md` 1-6, 27; `graphics.md`; `ai.md` 6).
- **Type 3, not type 8, is the room table** (`mechanics.md` 31a): `(A5)+96` row 3's data base is
  CAVERN's own address and its index table is 72/100 populated. Everything in sections 15-30 built on
  "type 8 = rooms, always empty, room 3 can never load" is superseded; the one-disk image has the
  room data.
- The room-activation routine `$00e854` / `$00e80c` / `$00e95c` (writer of `164(A5)`): forcing
  `164(A5)` to another resident room record plus `$e854`'s 493-byte effect runs stable for 2M steps,
  but the rendered screen stays CAVERN's (31c). `$00e7b0` reads room-record bytes +4/+5 through the
  `$5a10` table into graphics metadata at `(A5)+148` (no visible change). `$00ccd4` repopulates the
  room's objects from types 5/6 (31d).
- A real reverse TUNNEL -> CAVERN crossing (from `room2_tunnel_entry.snap`, Down) fires
  `$0144b8` `ScreenFlip_ScanlineCopy` (~130 writes, only on a real crossing), a destination-side flip
  of an already composited frame, not the step that paints the room (31e).
- Closed as clean negatives, do not reopen: the four static caller searches (24a/24b), the `$00fe84`
  decode (25), the LOCK(144) flag-poll question (28a), the position/route/action-id sweeps (20, 29),
  disk I/O from the loaded image (30a: no FDC/DMA register access anywhere in RAM).

## Open, in priority order

1. **What paints a room's background from its own asset data.** Lead: `$00014a90`, one of the six
   `$69da` callees of 28c (`$e1fa`, `$af10`, `$dde8`, `$d78a`, `$14a90`, `$ebaa`), never traced alone,
   right after `$0144b8` in memory, reading a room field at `(A5)+496` into a masked composite. Proof:
   `watch` the back buffer during a real crossing and name the PC that writes the room's pixels; then
   make the hacked type-3 room render (screen differs from CAVERN in `snap_render.py`).
2. Room-record bytes +0..+3 (still unknown; +4/+5 are the graphics-table index): the second candidate
   if `$14a90` is a dead end.
3. How the ~72 real rooms connect in ordinary play (`$007104` is not it: both branches `bra $69da`).
4. The two-disk original (`30b`): lower priority now that the one-disk image is known to hold the
   rooms; it would be a new subject (fresh boot and wall-fixing), not a continuation.

## Known traps

- Movement is joystick port 1 (`kbd ff 01/02/04/08` = up/down/left/right). One packet is a
  self-terminating multi-substep move needing 60k-100k steps; shorter budgets read as "blocked", and
  a released direction can leave a 1-unit momentum tail. One packet, >= 60k steps, then read.
- Player = sprite-array slot 0 (`$038338`, +42 = 0); `A5 = $18152`.
- Use `tools/find_ram_callers.py` and `tools/find_field_writers.py` for "who calls / writes X";
  do not rewrite them.

## Next session

Commit the stranded sections 30-31 of `mechanics.md` first. Then trace `$14a90` from
`tunnel_return_cross.snap` (a real crossing) and find the write that paints the room background;
if it names the per-room data it reads, drive the hacked type-3 room and diff the render against
CAVERN. Prompt: `/resume cadaver`.
