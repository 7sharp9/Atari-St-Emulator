# Cadaver: handoff

Updated 2026-09-24 by the session that ended at commit `ddf6344` (52nd pass, §52). Extracted the
two-disk Image Works Empire `[t]` (trained crack) release from Dropbox and tried to live-boot Disk 1
to the "place levels disk" prompt for a real Disk 2 swap test (Open item 1 from the prior handoff).
The live boot stalled — abandoned after ~1.6 billion emulated steps stuck in a looping cracktro, not
gated by any short keypress (confirmed by a controlled A/B/C/D test). Fell back to a static
byte-level comparison of the two disk images instead, and got independent confirmation from Dave: a
real commercial expansion for Cadaver shipped as a straight replacement for Disk 2. Both signals
agree Disk 2 is a real, distinct levels disk — reframing, not contradicting, §51's one-disk-specific
negative.

## Resume point

- Last commit of this workstream: `ddf6344` "cadaver: two-disk Empire release's Disk 2 confirmed a
  real, distinct levels disk (52nd pass, §52)". A related repo-wide methodology fix from this same
  session is in a separate commit, `3df3999` (`.claude/skills/reverse-engineer-st-game/SKILL.md`).
- Disk images: the one-disk image is unchanged (`Cadaver/Cadaver (1990)(Image Works)[cr Empire][one
  disk].st`, sha256 in `reversing/cadaver/README.md`). New this session, extracted from Dropbox
  (`~/Library/CloudStorage/Dropbox/Daves/ST games/Cadaver/`) into the working tree — untracked, do
  not `git add`:
  - `Cadaver/disk1_empire/Cadaver (1990)(Image Works)(M3)(Disk 1 of 2)[cr Empire][t].st` (819,200B,
    sha256 `5dd6a36f...e510c2a`)
  - `Cadaver/disk2_empire/Cadaver (1990)(Image Works)(M3)(Disk 2 of 2)(Level)[cr Empire][t].st`
    (819,200B, sha256 `9909ae87...29a26279`)
  Other crack groups (Replicants/ST Amigos) and the `[!]` verified-dump pair are still in Dropbox
  only, not extracted. See [[mac-st-sources]].
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). This session's boot-attempt
  snapshots (`disk2test_boot*.snap`, `ctrl_*.snap`) are throwaway — don't resume from them, they're
  all still sitting inside the trained crack's looping intro, nowhere near gameplay. The static
  analysis this session's findings rest on needs no snapshot: `reversing/cadaver/py/analyze_disk2.py`
  reads the `.st` files directly (paths hardcoded to this Mac checkout).
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry) or `gameplay_empire.snap` (CAVERN start
  tile) for any further one-disk-image work, unchanged from prior handoffs. **Do not use `$5a99` to
  detect "crossing done"** — use `(A5)+1166` (§38b) instead. **Always pass `--disk-a "Cadaver...st"`
  and use `resume <snap> repl`, never the bare alias `rrepl`** — see "Known traps" below. **Positional
  argv, not a `--snapshot` flag**: the raw binary's snapshot subcommand is `<N> snapshot <path>
  --disk-a <path>`, not `<N> --snapshot <path> ...` — the latter silently falls through to no-op
  argv matching with zero output (cost a wasted run this session; see Program.fs's `match argv with`
  block for the actual patterns before assuming a flag exists).
- Uncommitted work left behind: none of this session's own. `M68000/sessions/README.md` and
  `M68000/sessions/powermonger.md` still show modified in `git status` — the concurrent "Training
  efficiency (2)" session's work (confirmed live via `ListAgents` again this pass), left alone per
  the shared-resources rule.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` §1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35-51 (movement collision/proximity mechanism, the
icon-panel write chain, the full 72-room world-map/adjacency graph, the door-connectivity walk with
zero teleport doors, the LOCK/UNLOCK mechanism structurally disjoint from the door-transition flag,
the five doors' positive id words causally inert on the transition path, the one-disk crack's
physical disk contents ruled out as holding a second level, all fully closed). **New this session,
`mechanics.md` §52**:

- **§52.** Reframes §51 (which only spoke to the one-disk crack) for the two-disk original: Dave
  confirmed a real commercial expansion shipped as a straight replacement for Disk 2, matching its
  own filename label "(Level)". Independently, a static comparison of the two-disk Empire `[t]`
  crack's images (`py/analyze_disk2.py`) found Disk 2 is ~91.9% real (non-blank) data — corrected
  from `disk_layout.py`'s coarse 98.4% after finding a 3-byte repeating filler pattern its classifier
  missed — against Disk 1's 46.4%; confirmed not a duplicate of either Disk 1 or the one-disk image
  (0.1-0.3% byte-identical at matching offsets, vs. ~41% for same-crack-group images); and its two
  large data blocks (334KB/404KB) are markedly flatter/less-repetitive in byte distribution than Disk
  1's own already-proven 272KB resource-table block (0.8-1.4% duplicate sectors vs. 27.4%; 7-9% max
  byte frequency vs. 22.7%) — denser than the disk's own confirmed-real content, not less. Two open
  tensions: no depacker exists anywhere in this spike's disassembly, so if that density means Disk 2
  is compressed, nothing known could unpack it (a decompressor would have to live in Disk 2's own
  unanalysed boot/loader sectors 0-7); and no readable strings or fixed-record stride were found in
  Disk 2's blocks, so nothing *internal* to this analysis positively identifies the content as levels
  specifically — that rests on Dave's external ground truth, not on the byte analysis alone. A live
  boot-and-swap attempt (Disk 1 to the "place levels disk" prompt, then `disk`-swap in Disk 2) was
  tried and abandoned — see Open item 1.

## Open, in priority order

1. **Live gameplay confirmation, not yet reached.** The two-disk Empire `[t]` (trained) crack's own
   intro is a scrolling multi-crew greet-list followed by a loading-bar screen that **loops**
   (confirmed: a 600M-step snapshot and a 1600M-step snapshot from the same run show the same screen,
   diffing only in the loading-bar pixels) — roughly 100x the ~15M steps the one-disk release needs
   to reach gameplay, and not converging within a ~1.6 billion step budget. A controlled A/B/C/D test
   (same snapshot, same 5M-step budget, no key / space / return / '1') produced pixel-identical
   screens in all four cases, ruling out a short keypress as what's gating this specific window — the
   loop's real trigger (a timed protection check? genuine slow disk depacking? something else) is
   unidentified. **Next thing to try**: the `[!]` (verified-dump, likely uncracked original) two-disk
   pair in the same Dropbox folder — an uncracked original should have no cracktro to grind through
   at all, unlike every crack-group image tried so far. If that also fails to reach the prompt
   quickly, this item should probably be downgraded: §52's static + external-ground-truth evidence is
   already fairly strong without it.
2. **Low priority, unchanged from the prior handoff**: which of the 13 (of 14) `$ff8201`-touching
   call sites other than the room-crossing path actually fires (title/intro screen, a different
   room-pair's crossing, a resolution/mode change). Not needed to close anything above.
3. **New, low priority, not blocking anything**: `disk_layout.py`'s blank/data classifier only
   catches single-byte-repeat fills; extend it to detect short-period repeating patterns (the 3-byte
   `6D B6 DB` cycle §52 found on Disk 2's tail) so its headline percentage doesn't need a manual
   correction next time it's used.

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
  `resume <snap> repl [--disk-a <path>]` (two tokens), not `rrepl <snap>`.** Also applies to
  `snapshot`: it's positional (`<N> snapshot <path>`), there is no `--snapshot` flag — see Resume
  point above. Calling the raw `dotnet exec` binary with an unmatched argv pattern silently falls
  through to a disk-less cold boot (or, for the snapshot case, prints nothing and exits 0 having done
  nothing), which looks exactly like a stuck/corrupted snapshot until you reproduce a *known-good*
  prior result with the correct argv. Also in `CLAUDE.md`'s Rules section.
- **`$5a99` is not a room-transition signal.** Use `(A5)+1166` (§38b) instead.
- **Struct field offsets get reused for different meanings at different call sites — but check
  whether an apparent second meaning is actually dead code before concluding it's a real conflict.**
  See §40's `$cd62` case for the worked example.
- **A live snapshot's static memory alone can settle a "what does routine X compute" question**,
  without running the emulator forward, when the routine's inputs are just RAM values already
  sitting in the snapshot. This extends to the disk image itself: a "does the disk hold more content"
  question can be mostly settled by parsing the raw `.st` file's own bytes (BPB, directory, sector
  entropy/uniformity/byte-distribution) with no emulator run at all (§51/§52) — though it can't
  positively identify *what kind* of content it is the way a live boot or a readable string can.
- **When a screen isn't advancing the way you expect (a cracktro, a loading screen), don't infer
  "does this keypress matter" from trials that also vary the step count** — run a same-snapshot,
  same-step-budget A/B instead. §52's initial "keypress causes a rewind" read was wrong, from an
  uncontrolled comparison; the real cause was the intro looping on its own. Now also in the
  `reverse-engineer-st-game` skill, section 2.
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

Open item 1 (live gameplay confirmation of the Disk 2 swap) is the only thing still worth chasing on
this thread, and only if the `[!]` verified-dump pair turns out to boot cleanly without a long
cracktro — try that first before sinking more step-budget into any crack-group image. If it also
stalls, §52's static + Dave's external confirmation is strong enough evidence to just call the
"is Disk 2 a real levels disk" question settled and move on to the low-priority items (2, 3) or a
new thread. Prompt: `/resume cadaver`.
