# Cadaver: handoff

Updated 2026-09-24 by the session that ended at commit `f818490` (56th pass, §56). Dave chose item
2 from the 55th-pass handoff (static graphics/level mining on `disk2_replicants.st`'s raw bytes,
independent of the crack dispatch bug) over item 1. Result: a real negative — the candidate-span
entropy scan and exhaustive width/layout rendering that decoded the one-disk crack's sprite sheet
found nothing coherent anywhere in Disk 2's own bytes, and the one static path left unexplored (a
depacker hiding in Disk 2's own boot sector) is ruled out too. This flips the priority: item 1 (the
crack dispatch bug, still open) is now the more promising route to further Disk 2 content, since
static guessing is exhausted short of a live read or a code-grounded struct definition.

## Resume point

- Last commit of this workstream: `f818490` "cadaver: static graphics scan on disk2_replicants.st
  comes back negative (56th pass)" (mechanics.md §56 only; no emulator/code changes this pass, no
  build needed).
- Disk images: unchanged from the 55th-pass handoff, still untracked under `Cadaver/`.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored), unchanged from the 55th-pass
  handoff — see that pass's entries for `agent_disk2_wall/before_jsr.snap` (the resume point for
  item 1) and `replicants_esc_30M.snap` (Disk 1 mounted, levels-disk prompt reached).
  - **New this pass**: `scratchpad/cadaver/disk2_gfx/` — `contact.png`/`disk2.html` (gfxview.py's
    auto palette/span scan against the raw `disk2_replicants.st` file), `try_widths.py` (the ad hoc
    render-every-width script, not promoted to `tools/`), `renders/` (~50 PNGs, all noise, kept for
    reference — safe to delete if space is needed, nothing in them was useful beyond what §56
    already describes).
- Uncommitted work left behind: none of this session's own. `M68000/sessions/README.md` and
  `M68000/sessions/powermonger.md` still show modified in `git status` — the concurrent "Training
  efficiency (2)" session's work (confirmed live via `ListAgents` at the top of this pass, busy
  throughout), left alone per the shared-resources rule. `.obsidian/` and `Cadaver/` are untracked
  and not this session's to manage.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` §1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35-55 (movement collision/proximity mechanism,
the icon-panel write chain, the full 72-room world-map/adjacency graph, the door-connectivity walk,
LOCK/UNLOCK structurally disjoint from door-transition, the five doors' id words causally inert,
the one-disk crack's disk contents ruled out for a second level, the two-disk original's Disk 2
independently confirmed as a real, distinct levels disk, the Replicants/ST Amigos crack reaching
the live "place levels disk" prompt and Disk 2 swap, the swapped-disk side-count bug found and
fixed in `MMU.fs`, and the crack's own protection-dispatch bug diagnosed but not fixed — all fully
closed except the dispatch bug itself, still open as item 1 below). **New this session,
`mechanics.md` §56**:

- **§56.** `disk2_replicants.st` is 98.3% byte-identical to the two-disk Empire `[t]` crack's own
  Disk 2 (§52's already-analysed image) — same game payload, different loader/protection sectors —
  so §52's block boundaries and entropy figures (block A `$e00`-`$52800`, 334KB, 7.72 b/B; block B
  `$58c00`-`$bb600`, 404KB, 7.62 b/B) apply directly to the file this spike can now actually load.
  `gfxview.py`'s own palette/span auto-detection against the raw file finds 5 lower-entropy
  candidate spans (4.69-5.02 b/B, `$13000`/`$36800`/`$5d000`/`$82000`/`$a8000`) with 1-4 STF
  palettes embedded *inside* each one — structurally different from every other decoded asset in
  this game, whose palette sits *before* its data. **Negative result**: none of those 5 spans, nor
  blocks A/B, decode to any coherent tile/sprite/room structure across 7 widths (16-320px,
  st-interleaved 4bpp) or 2 widths of raw chunky8 — 49 renders total, all noise, unlike the
  one-disk sprite sheet which snapped into a recognisable image at the first struct-grounded width
  tried. Also checked Disk 2's own boot sector for a hidden depacker (`disk2_findings.md`'s
  proposed next step): it's inert, all-zero after the BPB, consistent with this disk never being
  booted (§55) — there's no code there to find, so any depacker would have to be in the
  already-fully-disassembled resident code, which is confirmed not to contain one (§28c/§51c).

## Open, in priority order

1. **The crack's dispatch bug** (§55, second half — now the higher-priority item per §56's
   negative result): trace `$00b39c`/`$00b420`'s header-parse sequence from
   `agent_disk2_wall/before_jsr.snap` (PC=`$00011602`, one instruction before the fatal `jsr`) and
   compare against the equivalent code in the Empire one-disk release to determine whether the
   neutralized `$00b418` check is patchable back to something that skips the bad chunk instead of
   crashing, and what should have populated stream 0's `$21004` blob with genuinely Disk-2-aware
   content before this dispatch runs. This is what's currently blocking the live boot from reading
   past ~track 7 of Disk 2 — and, per §56, now the only concrete path to seeing Disk 2's real
   content interpreted by the game's own code, since static guessing is exhausted.
2. Which of the 13 (of 14) `$ff8201`-touching call sites other than the room-crossing path actually
   fires. Not needed to close anything above.
3. `disk_layout.py`'s blank/data classifier only catches single-byte fills, not short-period
   repeats (§52's 3-byte cycle) — not yet extended.
4. No `.stx`→`.st` converter exists in `tools/`. Only worth writing for a `.stx`-only release.
5. The five crack variants extracted in the 55th pass and the untried single-sided
   `disk2_replicants[b].st` (55th-pass handoff, Resume point) — low priority, superseded by item 1
   as the more direct path to more Disk 2 content; only worth trying if item 1 stalls.

## Known traps

(Unchanged carried-over list — see git history for the full set: `ScreenBufferA/B` role-swap
framing is wrong, `movem` block-copy chunk reversal, `watch`'s step= counter is a lifetime counter
not local, one-shot breakpoint chase non-reproducibility, re-disassemble elided `...` excerpts in
full, `bpc` over `bp` for one-shot dumps, `bt depth>1` can crash the REPL, a `watch` range can
bracket multiple regions in one call, `gfxview.py`'s `st-interleaved` assumes 16px-wide masked
blits, movement is joystick port 1, player = sprite slot 0, use
`tools/find_ram_callers.py`/`find_field_writers.py`/`find_literal_ptr.py`/`find_jump_table_hit.py`.)

- **`ATARI_NOTRACE=1` applies to every `dotnet exec` invocation, including `resume <snap> repl`
  piped a script, not just a cold boot** — in `CLAUDE.md`.
- **A disk image swapped in mid-game and never booted through TOS can have a self-inconsistent
  boot-sector BPB** — `MMU.fs`'s `LoadDiskA` now cross-checks this for side count (§55).
- **A disk that's never booted (swapped in mid-game) has no reason for its boot sector to hold real
  code either** — Disk 2's sector 0 is all-zero filler after the BPB (§56d); don't expect a
  never-booted disk's boot sector to be a useful place to look for loader/depacker code.
- **A high entropy match alone doesn't distinguish "genuine bitmap/sprite data" from "genuine
  structured table data" from "compressed data with no known unpacker"** — Disk 1's already-proven
  room/resource table block reads at the same ~7.6 b/B entropy as Disk 2's still-uncharacterized
  blocks A/B; entropy narrows candidates but the actual content needs either a code-grounded struct
  definition or a live read to identify (§52, §56).
- `bp <hexaddr> [maxSteps]` takes at most 2 arguments — `bpc <addr> <n> [maxSteps]` if an Nth-hit
  count is needed.
- The REPL's `disk <path>` command mounts a *relative* path from the process's own working
  directory (typically `M68000/`), not relative to wherever the snapshot or driving script lives.
- `run.ps1`'s subcommand names are aliases, not raw argv (`CLAUDE.md`'s Rules section has the full
  mapping).
- `$5a99` is not a room-transition signal; use `(A5)+1166` (§38b) instead.
- A live snapshot's static memory alone can settle a "what does routine X compute" question without
  running the emulator forward, and extends to a disk image's own raw bytes for "does the disk hold
  more content" — though it can't identify *what kind* of content without a live boot or readable
  strings (§51/§52), and, per §56, exhaustive width-guessed rendering can rule out "it's a plain
  raster at any obvious stride" too, once tried thoroughly enough to trust the negative.
- When a screen isn't advancing the way expected, don't infer "does this keypress matter" from
  trials that also vary the step count — run a same-snapshot, same-step-budget A/B instead (§52).
- `gfxview.load_ram(path)` returns `(ram_bytes, base)`, that order. `gfxview.detect_palettes(ram,
  base)` returns a list of dicts (`addr`/`type`/`words`/`colors`/`distinct`), not tuples.
- The REPL's `watch <addr> <len>` parses `<len>` as decimal, not hex.
- `kbd`/other REPL input commands only enqueue IKBD bytes for delivery during a subsequent `s`/`bp`/
  `bpc` — issue them before the step/breakpoint that should consume them, and split make/break
  codes into two separate `kbd` calls with a real `s <n>` between them.
- `bt` with no depth argument defaults to depth 8 and reliably crashes the REPL — always pass `bt 1`.
- If hand-parsing a `.snap`'s header instead of using `gfxview.py`'s loaders: `cpu.CCR` is written
  as an int16, not a byte, so the RAM-length field sits 1 byte later than expected.
- A static-analysis session's own new interpretive claim can revive a framing a doc's later
  sections already retired — grep the doc for later sections before writing a new reading.
- A "no caller found in the loaded image" static negative only rules out a plain resident caller
  already loaded; a runtime-loaded or self-modifying path stays untested until checked another way.

## Next session

Item 1 (the crack's own protection-dispatch bug) is now the clear priority: §56 exhausted the
static-analysis path item 2 offered, and item 1 is the only remaining route to either seeing Disk
2's content live or grounding its format in code the way the one-disk sprite sheet's `+50`/`+51`
fields did. Start from `agent_disk2_wall/before_jsr.snap` (PC=`$00011602`) and trace backward
through `$00b39c`/`$00b420`'s header-parse sequence; compare against the equivalent code path in
the Empire one-disk release, which reaches gameplay cleanly and must therefore either not hit this
dispatch at all or hit it with an intact version-check branch. Prompt: `/resume cadaver`.
