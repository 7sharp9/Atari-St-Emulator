# Cadaver: handoff

Updated 2026-09-24 by the session that ended at commit `f831474`.

## Resume point

- Last commit of this workstream: `f831474` "cadaver: 120(A5) is a cache, not the source - $0144b8
  runs backwards to refresh it on crossings".
- Disk image: `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add`. Present on this Mac checkout this
  session with no rebuild needed. If it's gone, pull it from `gpubox` (tar-over-ssh recipe,
  `CLAUDE.md`).
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). All snapshots from the prior
  handoff were still present this session (`room2_tunnel_entry.snap`, `gameplay_empire.snap`,
  `tunnel_return_cross.snap`, `tunnel_return_settled.snap`, `hit_014b28.snap`) — no rebuild needed.
  New this session: `fresh_cavern_cross.snap` (live snapshot right after a real TUNNEL→CAVERN
  crossing, `mechanics.md` §36b). One-off Python scripts under `scratchpad/cadaver/decode_2de08/`
  and ad-hoc REPL scripts under `/tmp` (not scratchpad, not committed) — the reusable decode tool is
  promoted at `reversing/cadaver/py/decode_backbuffer.py`.
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry, `(A5)=$18152`, `120(A5)=$2de08`,
  `$5a99=0` in this snapshot — re-read all three live, they are not guaranteed stable across
  snapshots per README's own note). `kbd ff 02` reproduces the TUNNEL→CAVERN crossing.
  `gameplay_empire.snap` (CAVERN, day 1) for the reverse direction via the zigzag recipe.
  `hit_014b28.snap` for the specific PC `$014b28`. `fresh_cavern_cross.snap` for the post-crossing
  state used in §36's register capture.
- Uncommitted work left behind: none.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`.

- Collision, graphics compositing and the entity/object-verb bytecode interpreter are disassembled
  and documented (`mechanics.md` 1-6, 27).
- Type 3 (not type 8) is the real, populated room table, 72/100 slots (`mechanics.md` §31a).
- `$00014a90` fully disassembled (§32a) and its blit source pinned down live (§32b): `$014b28`'s
  source is a fixed, room-independent address (`$55b6`) — `$014a90` repaints a fixed status/icon-
  panel element at screen `(272,143)`, not room art.
- The entity/sprite-list renderer is live-traced (§33b, §34b): entry `$007f60`/`$0150b4`-family,
  called from a null-terminated pointer-list walk at `$00d900`-ish. Confirmed not the room-art
  source — it draws sprites at their own screen positions, not a room-sized background. `$00bf72`
  writes a small ~700-byte sprite-bitmap-cache region (`$2ca84`-`$2cd42`), also not room art.
- `$0144b8` (`ScreenFlip_ScanlineCopy`) fully disassembled (§34a): `(A5)+0` and `(A5)+$7d00` are
  the two halves of *one* 64000-byte double-buffer feeding the shifter; `120(A5)` is a **separate,
  third resident buffer** that the flip reads from.
- **§35, 36th pass: `120(A5)`'s buffer fully decoded, byte-exact.** Pulling the *full* linear
  disassembly of `$0144b8` (not the prior pass's elided excerpt) gave the real structure: 571
  chunks of 56 bytes (`movem.l (A0)+,#$fcff` / `movem.l #$ff3f,-(A1)`, 14 registers `D0-D7,A2-A7`)
  plus one `$5a99`-gated 24-byte remainder chunk (leading if `$5a99≠0`, trailing if `$5a99=0`),
  forward-read from `120(A5)`, written backward into the destination. Predecrement `movem`'s fixed
  reverse transfer order cancels the read-order reversal *within* each chunk, so only **chunk
  order** is reversed end-to-end across the whole 32000-byte transfer. Reconstructing that exactly
  and decoding as plain `320×200×4bpp st-interleaved` reproduces `(A5)+0`'s live bytes with
  **0/32000 diffs** against `room2_tunnel_entry.snap`. Script:
  `reversing/cadaver/py/decode_backbuffer.py <snap> [--out out.png]`.
- **New this session (§36, 37th pass): the disk-load hypothesis from §35 is wrong — `120(A5)` is a
  downstream *cache*, not the room's source, and every prior "find the writer" search was watching
  the wrong buffer.** Traced a real TUNNEL→CAVERN crossing (`kbd ff 02` from `room2_tunnel_entry.snap`)
  under both `ATARI_TRACE_OS=1` and `ATARI_TRACE_FDC=1` — **zero** trap/FDC activity either way, yet
  `120(A5)`'s content genuinely changes to CAVERN art (`decode_backbuffer.py`, confirmed visually).
  Chasing the crossing's actual `$0144b8` call by register content (its printed `watch` step numbers
  are the CPU's persistent lifetime counter baked into the snapshot, not any command's own local
  step budget — cost real time to work out) caught it running with **source and dest swapped**:
  `A0=$20f00` (`(A5)+0+$7d00`, the display double-buffer's *inactive* half) → `A1=$35b08`
  (`120(A5)+$7d00`, `120(A5)`'s own buffer). Same copy mechanism as the ordinary per-frame flip, run
  backwards: it **banks the freshly-drawn inactive display-buffer half into `120(A5)`** as a cache
  for future per-frame refreshes, not the other way round. Reproduced 3× within one continuous
  trace. The real room-background painter writes the display buffer's inactive half directly
  (RAM-to-RAM, matching the no-disk-I/O finding) — not `120(A5)`, which is why §33b/§34b's watches
  on `120(A5)` correctly found nothing. See Open item 1 below for the narrowed next step.

## Open, in priority order

1. **Find what writes the display double-buffer's inactive half (`$20f00` in this snapshot,
   `(A5)+0+$7d00` generally) with the new room's raw art.** §36 traced the actual mechanism one
   level further back than any prior pass: `120(A5)` only ever *receives* a copy of that buffer half
   (via `$0144b8` run backwards) — the real painter writes the half directly, with no disk/FDC
   activity (confirmed under both `ATARI_TRACE_OS=1` and `ATARI_TRACE_FDC=1` across a full crossing),
   so it's a RAM-to-RAM writer somewhere else in the loaded image, not a room-load disk read (that
   hypothesis, from the prior handoff, is now closed as wrong — see §36a). Two concrete next steps,
   in order:
   - (a) `watch $20f00 32000` (re-read the live address fresh each snapshot — it's `(A5)+0+$7d00`,
     not a fixed constant) across the same `kbd ff 02` crossing from `room2_tunnel_entry.snap`. This
     is the first watch ever armed on the *right* buffer for this question — every prior pass
     (§33b/§34b, and this session's own first attempt) watched `120(A5)` instead, which §36 now
     explains is a dead end for finding the painter (real writes happen one hop upstream).
   - (b) If that watch is quiet too, decode `$20f00` itself (plain `320×200×4bpp st-interleaved`, no
     chunk-reversal — it's the display buffer, not `120(A5)`) at a snapshot taken *mid-crossing*,
     before the reversed `$0144b8` bank-copy runs, to directly confirm it already holds finished
     CAVERN art at that point (inferred from the end-state this session, not yet captured
     mid-transition — see Known traps for the exact chase recipe and its reproducibility gotcha).
2. What `$55b6` contains for a *different* transition (e.g. an actual LEVER-proximity icon-panel
   change, §7) — §33a only checked the plain crossing this and the prior pass both used, and found
   zero. Lower priority than item 1.
3. Room-record bytes `+0..+3` (still unknown; `+4`/`+5` are the graphics-table index, `+$c0` is the
   mask table per §32a).
4. How the ~72 real rooms connect in ordinary play (`$007104` is not it: both branches `bra $69da`,
   §31b).
5. The two-disk original (§30b): lower priority, would be a fresh subject.

## Known traps

- **The Cadaver disk image is not in the usual Dropbox ST-games folder** — it's only on `gpubox`.
  Pull it with the tar-over-ssh recipe (CLAUDE.md) before assuming the workstream is blocked.
- **The "`ScreenBufferA`/`B` role-swap" framing in older passes is wrong** — don't reuse it. There
  are three regions, not two: `(A5)+0` and `(A5)+$7d00` are static halves of one double-buffer
  (dest of `$0144b8`'s flip), and `120(A5)` is a separate resident buffer (`$0144b8`'s source,
  chunk-reversed per §35) holding the actual room art. All three addresses are per-snapshot, not
  fixed constants.
- **A `movem.l (A0)+,list` / `movem.l list,-(A1)` block copy is not a plain memcpy** — predecrement
  mode's fixed reverse register-transfer order cancels with the address decrementing, so each
  chunk's *internal* byte order survives, but chunk order across the whole transfer is reversed.
  Recognise this pattern (fast copy + `trap #4`/vector-based mid-copy yield is the tell — Cadaver
  uses it to spread a copy across several VBLs) before assuming a buffer that renders as noise at
  the "obvious" width needs a different bpp/stride; it may just need chunk-reversal. Full method and
  proof: `mechanics.md` §35, tool: `reversing/cadaver/py/decode_backbuffer.py`. General lesson
  logged in the `reverse-engineer-st-game` skill.
- **The same copy routine can run with source and dest swapped** — don't assume a routine's
  "normal" direction (learned from its most common call site) is its only one. `$0144b8` almost
  always flips `120(A5)` → the display buffer; on a crossing it runs the other way, banking the
  display buffer back into `120(A5)`. A `watch` on the routine's usual *source* address won't catch
  this; watch the actual call's registers (§36c) or the specific address you care about.
- **`watch`'s printed `step=` numbers are the CPU's persistent lifetime counter, restored from the
  snapshot on resume — not a fresh per-command counter.** `hits`/`u`/`bpc`/`bp` all count locally
  from 0 for their own call instead. The two are offset by a large, snapshot-specific constant (tens
  of millions for a snapshot with this much accumulated history); don't try to convert one to the
  other by arithmetic — find the event by register/memory content, not by matching step numbers
  across different commands.
- **To land a breakpoint on a *specific* dynamic occurrence of a PC that's hit many times** (e.g. a
  per-frame routine, only one call of which matters), chain `s 1` / `u <addr> <cap>` / `r` in a
  single unbroken REPL run and read off which iteration has the register values you want, then
  reuse that same script prefix unmodified. Splitting the chase across separate invocations (even
  with an apparently-identical script) was **not reliably reproducible** this session — two
  supposedly-identical short reruns of the same prefix both failed to reach the same PC within the
  same step budget that the original, longer, unbroken run reached repeatedly. Root cause not found;
  budget more steps than the observed minimum if re-deriving this, and prefer one long run that logs
  everything over several short targeted ones.
- **When a prior pass's doc excerpts disassembly with `...`, re-disassemble in full before trusting
  the excerpt's implied structure** — `disassemble.py --linear <addr> <n>` with a generous `<n>`.
  The elided part hid the exact loop count (`subq.b`/`bne`, 4×142+3 = 571 chunks) that made §35
  possible; guessing from the excerpt alone would have kept the chunk-reversal invisible.
- **Prefer `bpc <addr> 1 <maxSteps>` over `bp <addr> <maxSteps>` for a one-shot reliable register
  dump.**
- **`bt <depth>` with `depth` > 1 can throw an unhandled `Atari.AddressError` and kill the REPL
  process** if the return-address chain doesn't follow the A6 link-frame convention past the first
  frame. Use `bt 1` first; only widen once you've confirmed the caller actually uses linked A6
  frames.
- **A `watch` range can cover multiple regions of interest in one call** — `watch <lo> <len>` takes
  a single contiguous span, but nothing stops that span from being wide enough to bracket two or
  more buffers at once — then bucket the resulting hits by destination-address range in a script.
  Cheaper than multiple separate `watch` runs when you need to compare several regions' write
  traffic from the same replay.
- `gfxview.py`'s `st-interleaved` layout renders standard 16-pixel word-interleaved planes
  correctly, but this game's masked-blit routines (`$014ee4`/`$007f60`/`$14f4a`/`$0150b4` family)
  read source data as **4 consecutive longwords per row** (one plane per 32-bit longword, 32 pixels
  wide, no inter-plane stride) — different in-memory order than word-interleaved for any width other
  than exactly 16px. Read the raw bytes directly from the snapshot instead of the HTML viewer for
  these sources.
- Movement is joystick port 1 (`kbd ff 01/02/04/08` = up/down/left/right). One packet is a
  self-terminating multi-substep move needing 60k-100k steps.
- Player = sprite-array slot 0 (`$038338`, +42 = 0); `A5 = $18152`.
- Use `tools/find_ram_callers.py` and `tools/find_field_writers.py` for "who calls / writes X".

## Next session

Start with Open item 1(a): `watch $20f00 32000` (read `(A5)+0+$7d00` fresh from whatever snapshot
you resume from — don't hardcode the address) across the `kbd ff 02` TUNNEL→CAVERN crossing from
`room2_tunnel_entry.snap`. This is the first watch aimed at the actual painter rather than
`120(A5)`'s downstream cache (§36's reframe). `decode_backbuffer.py`'s plain-raster decode (no
chunk-reversal needed for this buffer, it's the display buffer) gives a fast way to check any
candidate mid-crossing snapshot for finished CAVERN art. Prompt: `/resume cadaver`.
