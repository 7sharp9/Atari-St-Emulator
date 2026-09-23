# Cadaver: handoff

Updated 2026-09-24 by the session that ended at commit `6b07c6b`.

## Resume point

- Last commit of this workstream: `6b07c6b` "Cadaver: rebuild the resume infra from a cold boot,
  disassemble $14a90".
- Disk image: not on this Mac checkout by default — pulled from `gpubox` this session (see
  `mac-st-sources.md` memory / CLAUDE.md's tar-over-ssh recipe). Once pulled, it lives at
  `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add` it.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). Every `.snap` this or any
  prior pass produced is **gone between sessions** — that is expected (README calls them out as
  untracked resume points), not a bug. Rebuild recipe, proven working this session end to end:
  1. Cold boot `<steps> repl --disk-a "<the .st>"` (`ATARI_NOTRACE=1`, `repl` mode so it's
     interactive), send `kbd 01`/`kbd 81` (ESC) at the restore-game prompt, any key at "place
     levels disk", wait out "expanding data"/"loading data" (a few `s 8000000` steps) — lands in
     CAVERN/DAY 1, equivalent to the old `gameplay_empire.snap`.
  2. Zigzag to TUNNEL: `kbd ff 08` (Right make) `s 1200000` `kbd ff 00` `kbd ff 01` (Up make)
     `s 500000` `kbd ff 00` `kbd ff 08` `s 1200000` `kbd ff 00` `kbd ff 01` `s 1200000` `kbd ff 00`
     → `room2_tunnel_entry.snap` equivalent.
  3. Reverse crossing: `watch 2de08 32000`, `kbd ff 02` (Down make), `s 1500000` →
     `tunnel_return_cross.snap`; `kbd ff 00`, `s 500000` → `tunnel_return_settled.snap`. Expect
     ~64,000 watch hits, all at `pc=$014966`/`$01496e`/`$014976`.
- Start from: `scratchpad/cadaver/room2_tunnel_entry.snap` (fresh TUNNEL entry, rebuilt this
  session) or `tunnel_return_cross.snap` (mid-crossing, watch already fired). Both untracked;
  rebuild with the recipe above if missing again.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`.

- Collision, graphics compositing and the entity/object-verb bytecode interpreter are disassembled
  and documented (`mechanics.md` 1-6, 27).
- Type 3 (not type 8) is the real, populated room table, 72/100 slots (`mechanics.md` §31a).
- The reverse TUNNEL→CAVERN crossing is real and reproducible: `$0144b8` `ScreenFlip_ScanlineCopy`
  fires ~64,000 word-writes on a genuine portal crossing, zero on blocked movement (§31e, and this
  session's §32 reproduction, exact match).
- **`$00014a90` fully disassembled this session (§32a)** — a room-record masking/prep routine that
  ANDs `room_record+$c0` directly into the *live* screen buffer (`*(A5) + $59e8`, not a scratch
  copy), copies and re-masks `room_record[0..$60)` into `[$60..$c0)`, picks a 2-word variant from a
  small table at `$60fc` indexed off `2516(A5)`, then calls the generic sub-pixel masked blitter
  (`$14d7a`, `D6=2` branch → `$14ee4`) at fixed screen coords `(272,143)`. This is a strong
  candidate for the actual per-room background paint step the 31st pass was hunting — first routine
  found that provably writes into the live screen buffer keyed off the current room record.

## Open, in priority order

1. **What `$14ee4`'s blit source (`A0` at the `$014b28` call site) actually points to** — the room's
   own art, versus a fixed system asset (HUD/inventory panel) that happens to run once per room
   entry. This is the direct continuation of §32a and the single most direct path to closing the
   original "what paints a room's background" question. Proof: get a clean register dump at
   `$014b28` (this session's `bp` attempt gave inconsistent results across two identical replays —
   see trap below, root-cause or route around it), read what `A0` points to with
   `disassemble.py --snap`/`gfxview.py`, and check whether it varies with the current room record.
2. Room-record bytes `+0..+3` (still unknown; `+4`/`+5` are the graphics-table index, `+$c0` is now
   known to be a mask table per §32a).
3. How the ~72 real rooms connect in ordinary play (`$007104` is not it: both branches `bra $69da`,
   §31b).
4. The two-disk original (§30b): lower priority, would be a fresh subject.

## Known traps

- **The Cadaver disk image is not in the usual Dropbox ST-games folder** — it's only on `gpubox`.
  Pull it with the tar-over-ssh recipe before assuming the workstream is blocked.
- **Every `.snap` resume point is gone at the start of a fresh session, every time** — this isn't
  session-specific bad luck, it's the untracked-scratchpad convention working as designed. Budget
  time to replay the recipe above rather than searching for a snapshot that predictably won't be
  there.
- **`bp <addr> <maxSteps>` gave inconsistent results across two supposedly-identical replays** of
  the same crossing from the same snapshot with the same `kbd` input this session (one crossed
  cleanly, one sat idle for the full budget) — `watch` reproduced cleanly both times over the same
  span. Not root-caused. Prefer `watch` over `bp` for anything timing-sensitive around this
  crossing until this is understood; don't trust a single `bp` "gave up" result without a `watch`
  cross-check.
- Movement is joystick port 1 (`kbd ff 01/02/04/08` = up/down/left/right). One packet is a
  self-terminating multi-substep move needing 60k-100k steps.
- Player = sprite-array slot 0 (`$038338`, +42 = 0); `A5 = $18152`.
- Use `tools/find_ram_callers.py` and `tools/find_field_writers.py` for "who calls / writes X".

## Next session

Get a reliable register dump at `$014b28` (root-cause the `bp` flakiness first, or just add a
watch-triggered register dump instead of relying on `bp`) and read what `A0` points to. If it's
per-room art, drive the hacked type-3-slot render test (§31c/§31d) again with this now-known real
paint routine and check whether it can be made to draw a different room. Prompt: `/resume cadaver`.
