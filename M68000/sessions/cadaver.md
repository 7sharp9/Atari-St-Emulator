# Cadaver: handoff

Updated 2026-09-24 by the session that ended at commit `6419188` (51st pass). Ran the data-only
disk-layout check §50's own Open item 1 called for: the one-disk Empire crack's raw `.st` image has
no FAT12 file table and only 45.6% real data, concentrated in one ~270KB block plus crack-signature
fragments — no second level's data sits anywhere on this physical disk, closing item 1 alongside
§48c/§48d/§49/§50's structural and causal negatives.

## Resume point

- Last commit of this workstream: `6419188` "cadaver: raw disk-layout inspection finds no
  second-level data on the one-disk Empire crack (51st pass, §51)".
- Disk image: `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add`. Present on this Mac checkout. The
  two-disk original and the other crack groups (Replicants/ST Amigos, the `[!]` verified dump)
  mentioned in `reversing/cadaver/README.md`'s "Disk images" are **not** currently present in the
  working tree's `Cadaver/` directory, and **not in Dropbox either** (confirmed by Dave
  2026-09-24) — the only copy is on `gpubox` at
  `C:/Users/Dave/Documents/GitHub/Atari-St-Emulator/Cadaver/`, pull with the tar-over-ssh recipe
  in `CLAUDE.md` if a future pass wants to test the two-disk original directly rather than relying
  on §51's physical-inspection negative for the one-disk crack.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). No new snapshots this pass —
  §51's disk-layout check reads the `.st` file directly (`py/disk_layout.py`), no emulator run
  needed.
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry) or `gameplay_empire.snap` (CAVERN start
  tile) depending on which room's mechanism you're testing next. **Do not use `$5a99` to detect
  "crossing done"** — use `(A5)+1166` (§38b) instead. **Always pass `--disk-a "Cadaver...st"` and use
  `resume <snap> repl`, never the bare alias `rrepl`** — see "Known traps" below.
- Uncommitted work left behind: none of this session's own. `M68000/sessions/README.md` and
  `M68000/sessions/powermonger.md` still show modified in `git status` — the concurrent "Training
  efficiency (2)" session's work (confirmed live via `ListAgents` again this pass), left alone per
  the shared-resources rule.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` §1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35-50 (movement collision/proximity mechanism, the
icon-panel write chain, the full 72-room world-map/adjacency graph, the door-connectivity walk with
zero teleport doors, the LOCK/UNLOCK mechanism structurally disjoint from the door-transition flag,
the five doors' positive id words causally inert on the transition path, all fully closed). **New
this session, `mechanics.md` §51**:

- **§51.** Raw disk-layout inspection of the one-disk Empire `.st` image (`py/disk_layout.py`): the
  root directory is 224 bytes of `0xE5` with no live FAT12 entries — a non-filesystem, self-booting
  disk like the Medway Boys compilation's Disk B, not one where a second level could sit as a
  separately-named file. Sector-by-sector classification finds only 45.6% of the 800KB image is real
  (non-uniform) data: one dominant ~270KB contiguous block (sectors 400-936, almost certainly the
  already-decoded 72-room map/graphics/resource tables) plus a few small early chunks and six tiny
  fragments near the disk's end that decode to crack-group signature text ("THE MARVELLOUS...",
  "THE FALLEN ANGELS", "NOKTURNAL", "PRESENT:"), not game data. With no depacker found anywhere in
  this spike's disassembly, there is no live content-expansion mechanism that could be hiding a
  second level in a smaller packed blob. Combined with §48c/§48d's static loaded-image caller-search
  negative (no code path reaches the level-reload routine `$00b1e0`) and §49/§50's structural and
  causal proof that the door descriptors' id words don't gate a level swap, **Open item 1 is now
  closed on every axis this spike can test**: static (loaded code), causal (id-word behaviour), and
  physical (disk contents). It remains not airtight — the erase-pattern classification wasn't
  byte-verified against a known ST format-fill value, and a byte-identical "blank" sector that still
  decodes to something is unlikely but unchecked — but there is no further concrete, data-only next
  step left to try against this specific question.

## Open, in priority order

1. **Low priority, the only item left in this spike**: which of the 13 (of 14) `$ff8201`-touching
   call sites other than the room-crossing path actually fires (title/intro screen, a
   different room-pair's crossing, a resolution/mode change). Not needed to close anything above;
   pick up only if there's appetite to keep extending this spike past the "is there a hidden second
   level" question, which is now closed as far as static/causal/physical checks can take it.

## Known traps

(Unchanged carried-over list — see git history for the full set: `ScreenBufferA/B` role-swap framing
is wrong, `movem` block-copy chunk reversal, `watch`'s step= counter is a lifetime counter not local,
one-shot breakpoint chase non-reproducibility across separate invocations, re-disassemble elided
`...` excerpts in full, `bpc` over `bp` for one-shot dumps, `bt depth>1` can crash the REPL, a `watch`
range can bracket multiple regions in one call, `gfxview.py`'s `st-interleaved` assumes 16px-wide
masked blits (not this game's 32px-wide family), movement is joystick port 1, player = sprite slot 0,
use `tools/find_ram_callers.py`/`find_field_writers.py`/`find_literal_ptr.py`/`find_jump_table_hit.py`
— all indexed in `DEVELOPING.md` and the `reverse-engineer-st-game` skill, §5.)

- **`run.ps1`'s subcommand names are aliases, not raw argv — the raw binary only understands
  `resume <snap> repl [--disk-a <path>]` (two tokens), not `rrepl <snap>`.** Calling the raw
  `dotnet exec` binary with an alias name silently matches no argv pattern and falls through to a
  disk-less cold boot, which then sits forever in an early ROM wait loop (`$00fc01a0`-`$00fc01d4`,
  identical PC across repeated `s` calls regardless of which snapshot was named). This looks exactly
  like a stuck or corrupted snapshot — blank `snap_render.py` output, `bpc` never hitting even after
  millions of steps — until you reproduce a *known-good* prior result (e.g. §43's documented step
  count) with the correct argv and it works. Also in `CLAUDE.md`'s Rules section.
- **`$5a99` is not a room-transition signal.** Use `(A5)+1166` (§38b) instead.
- **Struct field offsets get reused for different meanings at different call sites — but check
  whether an apparent second meaning is actually dead code before concluding it's a real conflict.**
  See §40's `$cd62` case for the worked example.
- **A live snapshot's static memory alone can settle a "what does routine X compute" question**,
  without running the emulator forward, when the routine's inputs are just RAM values already
  sitting in the snapshot. This extends to the disk image itself: a "does the disk hold more content"
  question can be settled by parsing the raw `.st` file's own bytes (BPB, directory, sector
  entropy/uniformity) with no emulator run at all (§51).
- **When checking adjacency between inclusive-coordinate rectangles read from game data, a real
  shared boundary is a gap of exactly 1, not an overlap** (§44's classification rule).
- **A `bpc` armed only at the settled boundary can miss a mechanism that fires during the approach**
  — arm it before injecting the movement input, not just at the end state (§41).
- **A one-deep `bt 1` from a `bpc` hit is enough to find a routine's caller and the gating condition
  around the call site** — read the caller's own disassembly rather than chasing a deeper backtrace.
- `gfxview.load_ram(path)` returns `(ram_bytes, base)` — **that order**, not `(base, ram)`.
- `dotnet exec ... resume <snap> repl`'s printed `help` text does not list `kbd`/`mouse`/`disk`
  even though they exist and work (`Program.fs` line ~1396).
- The REPL's `watch <addr> <len>` parses `<len>` as plain **decimal**, not hex.
- `kbd`/other REPL input commands only *enqueue* IKBD bytes for delivery during subsequent `s`/`bp`/
  `bpc` steps — issue them **before** the step/breakpoint command that should consume them.
- **`watch`'s log reports the exact address each write landed at** — filter a coarse watch range by
  exact address/PC afterward rather than trying to watch a tight, possibly non-contiguous, region.
- **A continuously-firing PC group in a `watch` log is very likely the known full-buffer copy/flip
  routine, not new content** — group hits by PC first and prioritise the rare groups.
- `bt` with no depth argument defaults to depth 8 and reliably crashes the REPL process — always
  pass `bt 1`.
- **If you ever need to hand-parse a `.snap`'s header instead of using `tools/gfxview.py`'s
  `load_ram`/`load_video_regs`/`snapshot_regs`: `cpu.CCR` is written as an int16, not a byte**
  (`Program.fs` `SaveState`'s `w.Write(cpu.CCR)` — `CCR` is F# `int16`), so the RAM-length field
  that follows sits 1 byte later than a naive "19 regs + 1-byte CCR" read expects; getting this
  wrong desyncs every field after it (46th pass, cost real time before `gfxview.py`'s own helpers
  were found and reused instead of re-deriving the format).
- **A static-analysis session's own new interpretive claim can revive a framing the doc's own later
  sections already retired** — not just a stale carried-over handoff item (that's the `/resume`
  skill's job to catch). Grep the doc for later sections before writing a new reading, not just when
  resuming one (48th pass's §47c mistake, caught only on a later re-read; now in `CLAUDE.md`).
- **A "no caller found in the loaded image" static negative is not the same as "the mechanism is
  unreachable"** — it only rules out a plain `bsr`/`jsr`/literal-address/displacement-table caller
  already resident; a runtime-loaded or self-modifying path stays untested until checked some other
  way (50th pass; §51 supplied that other way for the specific "second level" question by checking
  the disk's own physical contents directly).

## Next session

Open item 1 (the level-count question) is now closed on every axis this spike found practical to
test. The only remaining open item (the low-priority `$ff8201` call-site sweep) is not worth picking
up unless there's appetite to keep extending this spike further — otherwise this workstream is at a
natural stopping point. Prompt: `/resume cadaver`.
