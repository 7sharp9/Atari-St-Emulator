# Cadaver: handoff

Updated 2026-09-24 by the session that ended at commit `be5cbb5` (53rd pass, §53). Tried the `[!]`
verified-dump pair per the prior handoff's plan — it's `.stx` (Pasti), unbootable by this
emulator — then extracted and drove the untried Replicants/ST Amigos crack pair instead. Reached
the "place levels disk" prompt live for the first time (Open item 1, carried over three handoffs),
swapped in Disk 2, and got a real in-game disk error followed by a CPU runaway on retry.

## Resume point

- Last commit of this workstream: `be5cbb5` "cadaver: Replicants/ST Amigos crack reaches 'place
  levels disk' live; Disk 2 swap errors then a CPU runaway (53rd pass, §53)". Two unrelated
  repo-wide doc fixes from this same session are in their own commit, `f35aafd` (`DEVELOPING.md`,
  `.claude/skills/reverse-engineer-st-game/SKILL.md`).
- Disk images: unchanged one-disk and Empire two-disk images from the prior handoff, still
  untracked under `Cadaver/`. New this session, extracted from Dropbox, untracked, do not `git add`:
  - `Cadaver/disk1_replicants/Cadaver (1990)(Image Works)(M3)(Disk 1 of 2)[cr Replicants - ST
    Amigos].st` (819,200B) — plus a copy at `disk1_replicants/disk1.st` (**the REPL's `disk`/other
    commands split on raw whitespace with no quoting; a path with spaces never matches, use the
    unspaced copy**).
  - `Cadaver/disk2_replicants/Cadaver (1990)(Image Works)(M3)(Disk 2 of 2)(Level)[cr Replicants -
    ST Amigos].st` (819,200B) — copy at `disk2_replicants/disk2.st`.
  - `Cadaver/disk1_verified`/`disk2_verified` were tried and deleted this session — the `[!]` pair
    is `.stx` (Pasti flux-dump, 1,848,748B/1,850,494B, not a multiple of 512), which this
    emulator's raw-sector loader cannot read (silently misreads it as garbage, per the new
    `DEVELOPING.md` note) — don't re-extract these without a `.stx`→`.st` converter, which doesn't
    exist in `tools/` yet.
  - Replicants/ST Amigos crack-group Dropbox filenames and the untried `[a]`/`[a2]`/`[b]` disk-1/2
    variants: see [[mac-st-sources]] and `reversing/cadaver/README.md`'s "Disk images".
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). This session's key snapshots,
  in the order they were produced (all from the Replicants/ST Amigos Disk 1 cold boot):
  - `replicants_boot_20M.snap` → trainer "presents" screen (static, confirmed parked).
  - `replicants_ctrl_space.snap` → game's own title screen (parchment+candles), reached by sending
    `kbd 39` then `kbd b9` **as two separate REPL calls** with real step counts between them (see
    Known traps).
  - `replicants_space2_20M.snap` → language-select screen.
  - `replicants_english_v2.snap` → "restore game / press 0-9, or ESC to start fresh" prompt.
  - `replicants_esc_30M.snap` → **"PLACE LEVELS DISK IN DRIVE ONE AND PRESS A KEY"** — the target
    prompt Open item 1 has wanted since the Empire `[t]` crack's cracktro stalled it three handoffs
    ago. Resume from here to continue the Disk 2 investigation without re-driving the whole boot.
  - `replicants_disk2_swap_30M.snap` → after `disk disk2.st` + keypress: **"THERE SEEMS TO BE AN
    ERROR ON THIS DISK. PRESS ANY KEY TO RETRY"** — a real in-game message, not a hang.
  - `replicants_disk2_retry_30M.snap` → after retrying (re-swap + keypress): back at the "place
    levels disk" prompt, not a repeat of the same error text.
  - The very next keypress from `replicants_disk2_retry_30M.snap` (no new snapshot — it crashed
    the REPL process) sent `PC` to `$230f8020` (impossible on a 24-bit-bus 68000) and hit the
    CPU decoder's deliberate "MOVE.B with An operand is illegal" guard (`68k.fs:1562`), an
    unhandled exception, not a breakpoint stop. **Not yet triaged** — see Open item 1.
  - PNG renders for every snapshot above are alongside them (`snap_render.py`).
- Uncommitted work left behind: none of this session's own. `M68000/sessions/README.md` and
  `M68000/sessions/powermonger.md` still show modified in `git status` — the concurrent "Training
  efficiency (2)" session's work (confirmed live via `ListAgents`), left alone per the
  shared-resources rule.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` §1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35-52 (movement collision/proximity mechanism,
the icon-panel write chain, the full 72-room world-map/adjacency graph, the door-connectivity walk,
LOCK/UNLOCK structurally disjoint from door-transition, the five doors' id words causally inert,
the one-disk crack's disk contents ruled out for a second level, the two-disk original's Disk 2
independently confirmed as a real, distinct levels disk by Dave's ground truth + static byte
analysis — all fully closed). **New this session, `mechanics.md` §53**:

- **§53.** The `[!]` verified-dump pair is `.stx` (Pasti), unbootable here — ruled out, not
  attempted live. The untried Replicants/ST Amigos crack pair, driven with correct make/break
  keyboard discipline, reaches the game's own title/language/restore-game/place-levels-disk
  sequence live in well under 100M total steps (vs. Empire `[t]`'s 1.6-billion-step cracktro
  stall) — Open item 1 from the last three handoffs, reached for the first time. Swapping in Disk 2
  gets a real in-game "error on this disk" message (not a hang, not silent garbage), and retrying
  causes a CPU runaway into the 68000 decoder's illegal-instruction guard. Two explanations remain
  open and untriaged: a genuine sector/track-layout mismatch between this crack's Disk 2 image and
  what its Disk 1 loader expects (plausible copy-protection on the level disk specifically), or a
  gap in this session's own REPL sequence or the emulator's FDC error-handling path. Repo-wide
  side-findings from this pass, not cadaver-specific: `.stx` unsupported (`DEVELOPING.md`), and the
  kbd make/break discipline note promoted from this game's README into the shared
  `reverse-engineer-st-game` skill (commit `f35aafd`).

## Open, in priority order

1. **Triage the Disk 2 disk-error + runaway.** Three candidate explanations, cheapest first:
   (a) re-run the exact same REPL sequence from `replicants_disk2_retry_30M.snap` a second time —
   if the runaway reproduces byte-for-byte, it's deterministic and worth a `watch`/`bpc` trace of
   the FDC read that precedes it, not a fluke; (b) try the Disk-1/Disk-2 `[a]`/`[a2]`/`[b]` variant
   files in the same Replicants/ST Amigos Dropbox folder — if a different variant swap reads
   cleanly, it's this specific pairing's protection, not a general emulator gap; (c) if a `.stx`
   converter ever gets written, boot the `[!]` pair the same way as a ground-truth "does an
   unprotected original's Disk 2 read cleanly" check. If all three point to a real protection
   scheme on Disk 2 rather than an emulator bug, §53's static-evidence conclusion (Disk 2 is a
   real, distinct levels disk) stands as-is and this item downgrades to "known unplayable without
   a working `.stx` path" rather than something to keep chasing.
2. **Low priority, unchanged**: which of the 13 (of 14) `$ff8201`-touching call sites other than
   the room-crossing path actually fires. Not needed to close anything above.
3. **Low priority, unchanged**: `disk_layout.py`'s blank/data classifier only catches single-byte
   fills; extend it to detect short-period repeats (§52's 3-byte cycle) so its headline percentage
   doesn't need a manual correction next time.
4. **New, low priority, not blocking anything**: no `.stx`→`.st` converter exists in `tools/`. Only
   worth writing if a future session specifically wants to boot a `.stx`-only release (the `[!]`
   pair here, or another game's protected original) — Pasti's format is flux-level and non-trivial,
   not a quick script.

## Known traps

(Unchanged carried-over list — see git history for the full set: `ScreenBufferA/B` role-swap framing
is wrong, `movem` block-copy chunk reversal, `watch`'s step= counter is a lifetime counter not local,
one-shot breakpoint chase non-reproducibility across separate invocations, re-disassemble elided
`...` excerpts in full, `bpc` over `bp` for one-shot dumps, `bt depth>1` can crash the REPL, a `watch`
range can bracket multiple regions in one call, `gfxview.py`'s `st-interleaved` assumes 16px-wide
masked blits (not this game's 32px-wide family), movement is joystick port 1, player = sprite slot 0,
use `tools/find_ram_callers.py`/`find_field_writers.py`/`find_literal_ptr.py`/`find_jump_table_hit.py`
— all indexed in `DEVELOPING.md` and the `reverse-engineer-st-game` skill, §5.)

- **The REPL's line parser splits on raw whitespace with no quoting** (`Program.fs`'s `runRepl`,
  `input.Split(' ')`) — `disk "path with spaces.st"` never matches the `disk <path>` pattern and
  silently falls through with no error. Copy the image to an unspaced filename first.
- **Send a key's make and break codes in two separate `kbd` calls, with a real `s <n>` step count
  between them, not one `kbd <make> <break>` call** — now promoted to the shared
  `reverse-engineer-st-game` skill (§2) since it applies to any game with an interrupt-driven IKBD
  ISR, not just this one. Sending both in one call lets the ISR drain them before the main loop's
  poll ever sees the key-down state, so the input is silently dropped and a wait screen looks
  input-inert when it isn't.
- **`run.ps1`'s subcommand names are aliases, not raw argv — the raw binary only understands
  `resume <snap> repl [--disk-a <path>]` (two tokens), not `rrepl <snap>`.** Also applies to
  `snapshot`: it's positional (`<N> snapshot <path>`), there is no `--snapshot` flag. Calling the
  raw `dotnet exec` binary with an unmatched argv pattern silently falls through to a disk-less
  cold boot (or, for the snapshot case, prints nothing and exits 0 having done nothing), which
  looks exactly like a stuck/corrupted snapshot until you reproduce a *known-good* prior result
  with the correct argv. Also in `CLAUDE.md`'s Rules section.
- **`$5a99` is not a room-transition signal.** Use `(A5)+1166` (§38b) instead.
- **A live snapshot's static memory alone can settle a "what does routine X compute" question**,
  without running the emulator forward, when the routine's inputs are just RAM values already
  sitting in the snapshot. This extends to the disk image itself: a "does the disk hold more
  content" question can be mostly settled by parsing the raw `.st` file's own bytes with no
  emulator run at all (§51/§52) — though it can't positively identify *what kind* of content it is
  the way a live boot or a readable string can, and it can't say anything at all about a `.stx`
  image without first converting it.
- **When a screen isn't advancing the way you expect (a cracktro, a loading screen), don't infer
  "does this keypress matter" from trials that also vary the step count** — run a same-snapshot,
  same-step-budget A/B instead. §52's initial "keypress causes a rewind" read was wrong, from an
  uncontrolled comparison. Now also in the `reverse-engineer-st-game` skill, §2.
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
  (`Program.fs` `SaveState`'s `w.Write(cpu.CCR)`), so the RAM-length field that follows sits 1 byte
  later than a naive "19 regs + 1-byte CCR" read expects.
- **A static-analysis session's own new interpretive claim can revive a framing the doc's own later
  sections already retired** — grep the doc for later sections before writing a new reading (48th
  pass's §47c mistake; now in `CLAUDE.md`).
- **A "no caller found in the loaded image" static negative is not the same as "the mechanism is
  unreachable"** — it only rules out a plain `bsr`/`jsr`/literal-address/displacement-table caller
  already resident; a runtime-loaded or self-modifying path stays untested until checked some other
  way (50th pass; §51 supplied that other way by checking the disk's own physical contents).

## Next session

Item 1 (triage the Disk 2 disk-error + runaway) is the only open thread worth chasing. Start from
`M68000/scratchpad/cadaver/replicants_disk2_retry_30M.snap` and re-run the same key-press sequence
once to check determinism before trying the `[a]`/`[a2]`/`[b]` disk variants. If the runaway turns
out to be this specific crack's own copy protection on Disk 2 rather than an emulator gap, close
this item and treat §53's static-evidence conclusion (Disk 2 is a real, distinct levels disk) as
the spike's final word on the "second level" question — there's no cheap path to actual live
gameplay on it without either a clean crack or a `.stx` converter for the verified-dump pair.
Prompt: `/resume cadaver`.
