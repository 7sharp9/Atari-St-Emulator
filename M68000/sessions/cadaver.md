# Cadaver: handoff

Updated 2026-09-24 by the session that ended at commit `ce15fe7` (54th pass, §54). Triaged the
53rd pass's Disk 2 CPU runaway (Open item 1): replayed a single keypress from
`replicants_disk2_retry_30M.snap` four different ways (space, Return, Escape, zero-delay space).
All four are deterministic across repeated invocations and land in sane state — the game re-reads
Disk 2 and cycles back to the same "ERROR ON THIS DISK" prompt, no crash. The runaway does not
reproduce from typical input; it looks like a one-off from the 53rd pass's own (uncaptured) REPL
sequence rather than a reliable protection mechanism or emulator gap.

## Resume point

- Last commit of this workstream: `ce15fe7` "cadaver: 53rd pass runaway does not reproduce from a
  clean keypress replay (54th pass)".
- Disk images: unchanged from the prior handoff, still untracked under `Cadaver/`:
  - `Cadaver/disk1_replicants/disk1.st`, `Cadaver/disk2_replicants/disk2.st` (819,200B raw `.st`
    each; the spaced original filenames are also present but unusable — the REPL's `disk`/other
    commands split on raw whitespace with no quoting).
  - The `[!]` verified-dump pair is `.stx` (Pasti flux-dump, not raw sectors) and was deleted last
    session — this emulator's loader can't read it; don't re-extract without a `.stx`→`.st`
    converter (doesn't exist in `tools/`).
  - Untried Replicants/ST Amigos `[a]`/`[a2]`/`[b]` disk-1/2 variants: see [[mac-st-sources]] and
    `reversing/cadaver/README.md`'s "Disk images".
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). Resume point for the "place
  levels disk" sequence, in order (all from the Replicants/ST Amigos Disk 1 cold boot, carried over
  from the 53rd pass):
  - `replicants_esc_30M.snap` → "PLACE LEVELS DISK IN DRIVE ONE AND PRESS A KEY", Disk 1 still
    mounted.
  - `replicants_disk2_swap_30M.snap` → after swapping to Disk 2 and a keypress: "THERE SEEMS TO BE
    AN ERROR ON THIS DISK. PRESS ANY KEY TO RETRY".
  - `replicants_disk2_retry_30M.snap` → after retrying: back at "PLACE LEVELS DISK...", Disk 2
    still mounted. **This session's replay point** — any single keypress from here deterministically
    re-triggers the same disk error (`replicants_retry_replay_space.snap`/`.png`, this session), not
    a crash.
  - PNG renders for every snapshot are alongside them (`snap_render.py`).
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
analysis, and §53 — the Replicants/ST Amigos crack reaches the live "place levels disk" prompt and
a Disk 2 swap gets a real in-game disk-error response — all fully closed). **New this session,
`mechanics.md` §54**:

- **§54.** The 53rd pass's Disk 2 CPU runaway does not reproduce. Four keypress variants replayed
  from `replicants_disk2_retry_30M.snap` (space, Return, Escape, zero-delay space), each run 30M
  steps and each deterministic across repeated invocations of the identical command sequence, all
  land in sane state: the game re-reads Disk 2 and cycles back to the same disk-error prompt. A
  no-key control run confirms the wait loop is genuinely idle (`PC` parked) until a key arrives.
  The exact key/timing the 53rd pass used was never captured to a file (its REPL script lived only
  in that session's log), so this isn't a byte-for-byte replay of that pass, but four plausible
  choices all converging on the same safe outcome makes a reliable, reproducible crash unlikely.

## Open, in priority order

1. **Low priority, downgraded this session**: the 53rd pass's Disk 2 runaway is not reproducible
   with typical single-keypress input (§54) — not worth further live-boot chasing without a
   specific new lead (e.g. a captured drive.txt from a session that hits it again). If it recurs,
   save the exact REPL sequence to a file immediately (`reversing/cadaver/drive.txt` convention,
   `reverse-engineer-st-game` skill) so it can be replayed byte-for-byte, which this session could
   not do.
2. Which of the 13 (of 14) `$ff8201`-touching call sites other than the room-crossing path actually
   fires. Not needed to close anything above.
3. `disk_layout.py`'s blank/data classifier only catches single-byte fills; extend it to detect
   short-period repeats (§52's 3-byte cycle) so its headline percentage doesn't need a manual
   correction next time.
4. No `.stx`→`.st` converter exists in `tools/`. Only worth writing if a future session
   specifically wants to boot a `.stx`-only release (the deleted `[!]` pair, or another game's
   protected original) — Pasti's format is flux-level and non-trivial, not a quick script.
5. **Unchanged, lower priority than the above**: try the Disk-1/Disk-2 `[a]`/`[a2]`/`[b]` variant
   files in the same Replicants/ST Amigos Dropbox folder, if a future session wants to keep
   pursuing live Disk 2 gameplay for its own sake — not blocking anything, since §54 downgraded the
   runaway that motivated this.

## Known traps

(Unchanged carried-over list — see git history for the full set: `ScreenBufferA/B` role-swap framing
is wrong, `movem` block-copy chunk reversal, `watch`'s step= counter is a lifetime counter not local,
one-shot breakpoint chase non-reproducibility across separate invocations, re-disassemble elided
`...` excerpts in full, `bpc` over `bp` for one-shot dumps, `bt depth>1` can crash the REPL, a `watch`
range can bracket multiple regions in one call, `gfxview.py`'s `st-interleaved` assumes 16px-wide
masked blits (not this game's 32px-wide family), movement is joystick port 1, player = sprite slot 0,
use `tools/find_ram_callers.py`/`find_field_writers.py`/`find_literal_ptr.py`/`find_jump_table_hit.py`
— all indexed in `DEVELOPING.md` and the `reverse-engineer-st-game` skill, §5.)

- **A significant one-off REPL result (a crash, a rare event) that isn't captured to a `drive.txt`
  or script file can't be replayed byte-for-byte by a later session**, even when the game state
  that led to it is deterministic — only the *sequence of REPL commands* was lost, not the engine's
  determinism. This session tried four plausible replays of the 53rd pass's runaway and all came up
  safe; that's evidence the runaway is unlikely to be a reliable mechanism, but it's not a
  disproof, because the actual sequence used was never saved (54th pass).
- **The REPL's line parser splits on raw whitespace with no quoting** (`Program.fs`'s `runRepl`,
  `input.Split(' ')`) — `disk "path with spaces.st"` never matches the `disk <path>` pattern and
  silently falls through with no error. Copy the image to an unspaced filename first.
- **Send a key's make and break codes in two separate `kbd` calls, with a real `s <n>` step count
  between them, not one `kbd <make> <break>` call** — now in the shared `reverse-engineer-st-game`
  skill (§2) since it applies to any game with an interrupt-driven IKBD ISR, not just this one.
  Sending both in one call lets the ISR drain them before the main loop's poll ever sees the
  key-down state, so the input is silently dropped and a wait screen looks input-inert when it
  isn't. This session found the "PLACE LEVELS DISK..." wait loop does **not** care which key is
  sent (space/Return/Escape all produce identical results) — it's a generic "any key" poll.
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

No urgent open thread: item 1 (the Disk 2 runaway) is downgraded and not worth chasing without a
new lead, and items 2-5 are all low priority and non-blocking. If Dave wants to keep pursuing live
Disk 2 gameplay, item 5 (the `[a]`/`[a2]`/`[b]` disk variants) is the next thing to try, starting
from `M68000/scratchpad/cadaver/replicants_esc_30M.snap` (Disk 1 still mounted, at the swap prompt)
so a variant Disk 2 can be tried without re-driving the whole boot. Otherwise this spike has no
open thread that clearly justifies more time — worth checking with Dave on priority before the next
session picks it back up. Prompt: `/resume cadaver`.
