# Cadaver: handoff

Updated 2026-09-24 by the session that ended at commit `4cb9dd7`.

## Resume point

- Last commit of this workstream: `4cb9dd7` "cadaver: $014b28 blit source is fixed, not per-room
  art — closes the $014a90 lead".
- Disk image: `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add`. Pulled from `gpubox` last session;
  still present on this Mac checkout this session (the rebuild recipe below still works if it isn't).
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). **Unlike the prior two
  sessions' experience, every `.snap` from the last session was still present this session** —
  `room2_tunnel_entry.snap`, `gameplay_empire.snap`, `tunnel_return_cross.snap`,
  `tunnel_return_settled.snap` all resumed cleanly with no rebuild. Don't assume they're gone;
  check before replaying the cold-boot recipe. If they are gone, the recipe (cold boot → CAVERN,
  zigzag to TUNNEL, cross back) is in the previous handoff's git history (`git show 6b07c6b:...`)
  or `reversing/cadaver/mechanics.md` §32.
  - New this session: `hit_014b28.snap`, a live snapshot with `PC=$014b28` (right before the
    `bsr $014d7a` masked-blit call), `A5=$18152`, saved mid-reverse-crossing from
    `room2_tunnel_entry.snap`. Untracked, useful starting point for reading `$55b6`'s contents
    without re-driving the crossing.
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry) or `gameplay_empire.snap` (CAVERN, day
  1) — both proven this session to still resume and both used to reproduce the crossing in either
  direction. `hit_014b28.snap` for the specific PC above.
- Uncommitted work left behind: none. `Cadaver/` (disk image) and `M68000/scratchpad/cadaver/*`
  (working data, including the new `hit_014b28.snap`) are untracked as designed, not left behind by
  mistake.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`.

- Collision, graphics compositing and the entity/object-verb bytecode interpreter are disassembled
  and documented (`mechanics.md` 1-6, 27).
- Type 3 (not type 8) is the real, populated room table, 72/100 slots (`mechanics.md` §31a).
- The reverse TUNNEL→CAVERN crossing is real and reproducible: `$0144b8` `ScreenFlip_ScanlineCopy`
  fires ~64,000 word-writes on a genuine portal crossing, zero on blocked movement (§31e).
- `$00014a90` fully disassembled (§32a): a room-record masking/prep routine, ANDs
  `room_record+$c0` into the live screen buffer, then calls the generic masked blitter at
  `$014b28`→`$14d7a`→`$14ee4` with fixed screen coords `(272,143)`.
- **New this session (§32b): `$014b28`'s blit source is a fixed address, not per-room art —
  settled, not just suspected.** Live register dump via `bpc 014b28 1 <maxSteps>` (reliable, unlike
  the prior pass's `bp`) at the exact moment of the call, both directions:
  - TUNNEL→CAVERN (`room2_tunnel_entry.snap`, `kbd ff 02`): `A0=$55b6 D0=$110(272) D1=$8f(143)
    D6=2 D7=6`, hit after 868,379 steps.
  - CAVERN→TUNNEL (`gameplay_empire.snap`, the zigzag recipe): **identical** `A0=$55b6`
    (`D0/D1/D6/D7` also identical), hit ~2.999M total steps in.
  - Same source address in both rooms closes `$014a90`/`$014b28` as "the room background painter"
    — it's a fixed status/icon-panel redraw on room entry (matches §7's independently-known "icon
    panel switches on proximity" behaviour), not room-specific art. The real room-background
    painter is still unfound; look elsewhere in the transition path (before `$0144b8`'s
    destination-side-only flip, §31e), not around `$014a90` again.

## Open, in priority order

1. **Where the room's own background art actually gets selected and blitted** — `$014a90` is now a
   closed, negative lead (§32b above), so the search moves to whatever runs before `$0144b8`'s
   flip in the same transition. Approach: `watch` the live screen buffer (`(A5)+$59e8` region, the
   same one `$014a90` ANDs into) across a full crossing and find every writer besides `$014a90`
   itself and the flip; or trace backward from `$69da` (the "already resident, re-enter main loop"
   branch, §28c) for whatever runs once per transition before the flip.
2. What `$55b6` actually contains — likely the fixed icon-panel glyph/sprite (§32b's working
   hypothesis, not yet confirmed). `gfxview.py` needs `numpy` on this Mac checkout
   (`ModuleNotFoundError` this session, not yet installed — `python3 -m pip install numpy`) to
   render it against the known palette; `hit_014b28.snap` above is the ready-made input. Compare
   the rendered shape against a real "default icon panel" vs "LEVER icon panel" screenshot pair to
   confirm the status/icon-panel hypothesis rather than leaving it inferred.
3. Room-record bytes `+0..+3` (still unknown; `+4`/`+5` are the graphics-table index, `+$c0` is the
   mask table per §32a).
4. How the ~72 real rooms connect in ordinary play (`$007104` is not it: both branches `bra $69da`,
   §31b).
5. The two-disk original (§30b): lower priority, would be a fresh subject.

## Known traps

- **The Cadaver disk image is not in the usual Dropbox ST-games folder** — it's only on `gpubox`.
  Pull it with the tar-over-ssh recipe (CLAUDE.md) before assuming the workstream is blocked.
- The prior handoff's claim that "every `.snap` resume point is gone between sessions, every time"
  did **not** hold this session — treat it as "check first, don't assume," not a hard rule.
- **Prefer `bpc <addr> 1 <maxSteps>` over `bp <addr> <maxSteps>` for a one-shot reliable register
  dump.** The previous pass's `bp` runs at this same address gave inconsistent results across two
  supposedly-identical replays (one crossed cleanly, one sat idle for the full budget); this
  session's `bpc` calls reproduced cleanly every time, from three separate fresh `resume ... repl`
  processes. Not root-caused (still open whether it's a real `bp`-path issue or was a script
  mistake last pass), but `bpc 1` is now the better default for "stop on first hit, print
  registers" until/unless it also flakes.
- `numpy` is not installed in this Mac checkout's `python3`; `gfxview.py` needs it for palette
  detection (`--contact`/`--html`) and fails with a bare `ModuleNotFoundError` otherwise.
- Movement is joystick port 1 (`kbd ff 01/02/04/08` = up/down/left/right). One packet is a
  self-terminating multi-substep move needing 60k-100k steps.
- Player = sprite-array slot 0 (`$038338`, +42 = 0); `A5 = $18152`.
- Use `tools/find_ram_callers.py` and `tools/find_field_writers.py` for "who calls / writes X".

## Next session

Install `numpy` (`python3 -m pip install numpy`) and run `gfxview.py` against
`scratchpad/cadaver/hit_014b28.snap` to read what `$55b6` actually is, confirming or refuting the
icon-panel hypothesis from §32b. Then move to the reframed open item 1: find the real room-art
paint step by watching the live screen buffer across a full crossing for writers other than
`$014a90` and the `$0144b8` flip. Prompt: `/resume cadaver`.
