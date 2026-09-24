# Cadaver: handoff

Updated 2026-09-24 by the session that ended at commit `1a6c586`.

## Resume point

- Last commit of this workstream: `1a6c586` "skills: reverse-engineer-st-game - note the movem
  forward-read/backward-write chunk-reversal idiom" (cadaver work itself at `05fb60d`).
- Disk image: `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add`. Present on this Mac checkout this
  session with no rebuild needed. If it's gone, pull it from `gpubox` (tar-over-ssh recipe,
  `CLAUDE.md`).
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). All snapshots from the prior
  handoff were still present this session (`room2_tunnel_entry.snap`, `gameplay_empire.snap`,
  `tunnel_return_cross.snap`, `tunnel_return_settled.snap`, `hit_014b28.snap`) — no rebuild needed.
  Nothing new saved to scratchpad this session (only reads via a one-off Python script under
  `scratchpad/cadaver/decode_2de08/`, not committed — the promoted, reusable version is
  `reversing/cadaver/py/decode_backbuffer.py`).
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry, `(A5)=$18152`, `120(A5)=$2de08`,
  `$5a99=0` in this snapshot — re-read all three live, they are not guaranteed stable across
  snapshots per README's own note). `kbd ff 02` reproduces the TUNNEL→CAVERN crossing.
  `gameplay_empire.snap` (CAVERN, day 1) for the reverse direction via the zigzag recipe.
  `hit_014b28.snap` for the specific PC `$014b28`.
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
- **New this session (§35, 36th pass): `120(A5)`'s buffer fully decoded, byte-exact.** Pulling the
  *full* linear disassembly of `$0144b8` (not the prior pass's elided excerpt) gave the real
  structure: 571 chunks of 56 bytes (`movem.l (A0)+,#$fcff` / `movem.l #$ff3f,-(A1)`, 14 registers
  `D0-D7,A2-A7`) plus one `$5a99`-gated 24-byte remainder chunk (leading if `$5a99≠0`, trailing if
  `$5a99=0`), forward-read from `120(A5)`, written backward into the destination. Predecrement
  `movem`'s fixed reverse transfer order cancels the read-order reversal *within* each chunk, so
  only **chunk order** is reversed end-to-end across the whole 32000-byte transfer. Reconstructing
  that exactly and decoding as plain `320×200×4bpp st-interleaved` reproduces `(A5)+0`'s live bytes
  with **0/32000 diffs** against `room2_tunnel_entry.snap`. `120(A5)` is not compressed, not a
  different resolution/bpp — it's the *same raster*, stored solely with this chunk-reversal.
  Script: `reversing/cadaver/py/decode_backbuffer.py <snap> [--out out.png]`. This settles the old
  "room background painter" question at the buffer level and reframes it: see Open item 1 below.

## Open, in priority order

1. **Find what loads `120(A5)`'s content on a room crossing.** §35 proved `120(A5)` holds a
   complete, already-composited 320×200 room raster (chunk-reversed), not a smaller tile/sprite
   source — that makes a *runtime compositor* unlikely (consistent with two full passes, §33b/§34b,
   catching no live writer during a crossing). The far more likely source is the room-load disk
   read itself, storing each room's pre-rendered background pixel-for-pixel in this reversed layout
   on disk. Next step: trace the disk-sector read(s) during a room crossing (the game reads raw
   sectors directly, not via GEMDOS `Fread`, per the 7th pass) and check whether the bytes landing
   in `120(A5)` match sectors read verbatim — a `watch 2de08 32000` across a *disk-read* window
   (not just a CPU-side compositor window) is the targeted version of the old item 1(b). If a disk
   read is confirmed, decoding `decode_backbuffer.py`'s output for other rooms (once their sector
   ranges are known) would let every room's background be extracted without booting to it.
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

Start with Open item 1: trace the disk-sector read(s) that happen during a room crossing (the game
reads raw sectors directly, not via GEMDOS `Fread`) and check whether the bytes landing in `120(A5)`
match sectors read verbatim — `decode_backbuffer.py` gives a byte-exact way to recognise when a
buffer holds a correctly-reconstructed room frame, so any candidate write/read window can be checked
by decoding and comparing rather than eyeballing. If disk-read tracing stalls, fall back to a wider
`watch 2de08 32000` window starting from a cold boot (before the first room ever loads) rather than
mid-game, since every capture so far has started from an already-populated buffer. Prompt: `/resume
cadaver`.
