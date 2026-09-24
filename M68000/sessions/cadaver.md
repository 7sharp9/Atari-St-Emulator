# Cadaver: handoff

Updated 2026-09-24 by the session that ended at commit `5f339a7` (55th pass, §55). Found and fixed
a real emulator bug that was misread by the 53rd/54th passes as a crack/protection failure: Disk
2's own boot-sector BPB lies about its side count (it's never booted, so nothing ever validated
it), and the emulator trusted it, so every side-1 sector read silently failed. Fixed, verified live
via FDC trace, and documented. Past the fix, hit a second, unrelated wall inside the crack's own
protection-dispatch code — diagnosed, not yet fixed, not an emulator gap.

## Resume point

- Last commit of this workstream: `5f339a7` "docs: ATARI_NOTRACE=1 applies to resume+repl runs
  too, not just cold boot" (preceded by `183f366` docs and `5547ae9` the actual emulator fix).
- Disk images: unchanged from the prior handoff, still untracked under `Cadaver/`. This pass also
  extracted five more crack-group variants into `M68000/scratchpad/cadaver/variants/` (untracked,
  gitignored) while chasing Open item 5 from the last handoff — `Cadaver (1990)(Image
  Works)(M3)(Disk 1 of 2)[cr Empire][t][a/b].st`, `[cr Replicants - ST Amigos][a/a2].st` — all four
  just needed the same keypress-past-cracktro handling as the base pairs and were not pushed
  further once the real bug (below) was found; a fifth, single-sided `disk2_replicants[b].st`
  (409,600B) and Empire `[t][a]`'s disk 2 (829,440B, non-standard size) are also there, untried.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored).
  - `replicants_esc_30M.snap` (carried over): "PLACE LEVELS DISK IN DRIVE ONE AND PRESS A KEY",
    Disk 1 (`disk1_replicants`) still mounted — the resume point for any further Disk 2 work.
  - `agent_disk2_wall/before_jsr.snap`: PC=`$00011602`, one instruction before the `jsr (A2)` that
    derails into the protection-dispatch bug (see Proven §55 below) — best starting point to
    continue tracing the header-parse sequence at `$00b39c`/`$00b420`.
  - `agent_disk2_wall/wall_712c.snap` / `wall_712c_v2.snap`: post-derail, PC=`$00021e1a`, inside
    the inactive framebuffer half — not useful for further static work, kept for reference.
  - `agent_disk2_wall/events.bin` (~117MB): full flow-event trace proving the derailment's call
    chain; fine to delete once no longer needed.
  - `agent_disk2_wall/fdc_trace.log`: confirms Disk 2's real FDC reads land around `$05e000`, not
    near the resident blob at `$21004` that gets (wrongly) executed.
- Uncommitted work left behind: none of this session's own. `M68000/sessions/README.md` and
  `M68000/sessions/powermonger.md` still show modified in `git status` — the concurrent "Training
  efficiency (2)" session's work (confirmed live via `ListAgents`, idle throughout this pass), left
  alone per the shared-resources rule. `.obsidian/` and `Cadaver/` are untracked and not this
  session's to manage.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` §1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35-54 (movement collision/proximity mechanism,
the icon-panel write chain, the full 72-room world-map/adjacency graph, the door-connectivity walk,
LOCK/UNLOCK structurally disjoint from door-transition, the five doors' id words causally inert,
the one-disk crack's disk contents ruled out for a second level, the two-disk original's Disk 2
independently confirmed as a real, distinct levels disk, the Replicants/ST Amigos crack reaching
the live "place levels disk" prompt and Disk 2 swap, and the 53rd pass's CPU runaway shown not to
reproduce — all fully closed). **New this session, `mechanics.md` §55**:

- **§55.** The "ERROR ON THIS DISK" message §53/§54 treated as an open protection/emulator question
  was this emulator's own bug: `MMU.LoadDiskA` derived a swapped-in disk's side count purely from
  its own boot-sector BPB, but a disk that's swapped in mid-game and never booted (Cadaver's Disk
  2) has no reason for its BPB to be honest — the Replicants/ST Amigos crack's `disk2.st` declares
  1 side despite being a real double-sided 819,200-byte dump. Every side-1 FDC read failed with "no
  data", and the game correctly (from its own view) reported a disk error. Fixed in `MMU.fs`
  (`5547ae9`): prefer 2 sides when the file is big enough for a standard double-sided disk at the
  declared sectors-per-track but the header claims only 1. **Proof**: `ATARI_TRACE_FDC=1` over the
  same swap-and-retry sequence that used to fail now shows clean side-0 and side-1 reads (track 0
  through track 7 confirmed this pass, ~149 reads, zero "no data" results) — not yet proven for the
  whole 80-track disk, since a second, separate bug (below) derails execution before the read gets
  that far.
  - **The second bug, past the fix, is the crack's own, not ours.** A generic embedded-resource-
    stream dispatcher (`$011598`, reads `{base,length,pos}` triples from a table at `(A5)+2538`)
    gets called with its "execute this chunk in place" sentinel and `jsr (A2)`s into `$21da0` —
    which is inside the *inactive* half of the double-buffered screen (`$20f00`-`$28cff`,
    §33b/§37a), not real code, hence the `illegal`/`(line-A)` decode noise. That target's backing
    blob at `$21004` is confirmed byte-identical before and after the Disk 2 swap, so it's resident
    data from original Disk-1 boot, not anything Disk 2's own sectors populate (those land at
    `$05e000`, per the FDC trace) — this is not "Disk 2 payload misread as code." Immediately
    before the dispatch, at `$00b418`, a version-style check (`cmp.w $41c.l,D0`) is followed by a
    bare `nop` where a real conditional branch belongs, so both outcomes of the check fall through
    to the same "execute the chunk" path — a strong signature of a crack-patched-out protection
    gate, not a missing OS trap or FDC timing gap (the FDC/DMA side is now proven correct). Not yet
    confirmed which original check this replaces; would need the equivalent address range in the
    Empire one-disk release for comparison.

## Open, in priority order

1. **The crack's dispatch bug** (§55, second half): trace `$00b39c`/`$00b420`'s header-parse
   sequence from `agent_disk2_wall/before_jsr.snap` (PC=`$00011602`, one instruction before the
   fatal `jsr`) and compare against the equivalent code in the Empire one-disk release to determine
   whether the neutralized `$00b418` check is patchable back to something that skips the bad chunk
   instead of crashing, and what should have populated stream 0's `$21004` blob with genuinely
   Disk-2-aware content before this dispatch runs. This is what's currently blocking the live boot
   from reading past ~track 7 of Disk 2.
2. **Static graphics/level mining on the raw Disk 2 file, independent of item 1.** Since Disk 2's
   own sector payload is now proven to load correctly (side-1 included) and §52 already showed
   ~91.9% of the file is real, non-blank data in two large blocks, the same method `graphics.md`
   used to find the one-disk crack's packed sprite sheet (entropy/candidate-span scan via
   `gfxview.py`, then render at diagnostic widths/bpp to look for tile structure) could be tried
   directly against `disk2_replicants.st`'s own bytes, without needing item 1 solved first. Not
   started this session — a genuine fork in direction from item 1, worth deciding priority on
   rather than assuming.
3. Which of the 13 (of 14) `$ff8201`-touching call sites other than the room-crossing path actually
   fires. Not needed to close anything above.
4. `disk_layout.py`'s blank/data classifier only catches single-byte fills, not short-period
   repeats (§52's 3-byte cycle) — not yet extended.
5. No `.stx`→`.st` converter exists in `tools/`. Only worth writing for a `.stx`-only release.
6. The five newly-extracted crack variants (Resume point above) and the untried single-sided
   `disk2_replicants[b].st` — low priority, superseded by item 1/2 as the more direct path to more
   Disk 2 content; only worth trying if items 1/2 stall.

## Known traps

(Unchanged carried-over list — see git history for the full set: `ScreenBufferA/B` role-swap
framing is wrong, `movem` block-copy chunk reversal, `watch`'s step= counter is a lifetime counter
not local, one-shot breakpoint chase non-reproducibility, re-disassemble elided `...` excerpts in
full, `bpc` over `bp` for one-shot dumps, `bt depth>1` can crash the REPL, a `watch` range can
bracket multiple regions in one call, `gfxview.py`'s `st-interleaved` assumes 16px-wide masked
blits, movement is joystick port 1, player = sprite slot 0, use
`tools/find_ram_callers.py`/`find_field_writers.py`/`find_literal_ptr.py`/`find_jump_table_hit.py`.)

- **`ATARI_NOTRACE=1` applies to every `dotnet exec` invocation, including `resume <snap> repl`
  piped a script, not just a cold boot** — now in `CLAUDE.md` (this pass lost real time to four
  parallel `resume ... repl` pushes that forgot it and each wrote a multi-GB trace log before being
  killed and rerun correctly).
- **A disk image swapped in mid-game and never booted through TOS can have a self-inconsistent
  boot-sector BPB** — nothing ever validates it, so a crack group's boilerplate header (side count,
  in this case) can simply be wrong. If a post-swap "disk error" message appears, check the image's
  real file size against its own BPB-implied size before assuming it's a genuine crack/protection
  failure (§55). `MMU.fs`'s `LoadDiskA` now cross-checks this for side count specifically; the same
  class of bug could in principle affect sectors-per-track too, though no case of that has been
  seen.
- **`bp <hexaddr> [maxSteps]` takes at most 2 arguments** — `bp <addr> <n> <maxSteps>` (3 args)
  matches no pattern and silently does nothing; use `bpc <addr> <n> [maxSteps]` if an Nth-hit count
  is needed.
- The REPL's `disk <path>` command mounts a *relative* path from the process's own working
  directory (typically `M68000/`), not relative to wherever the snapshot or driving script lives —
  `../Cadaver/...` from `M68000/`, not `Cadaver/...`.
- `run.ps1`'s subcommand names are aliases, not raw argv (`CLAUDE.md`'s Rules section has the full
  mapping) — `<N> snapshot <path>`, `<N> resume <path>`, `resume <path> repl`, `<N> verify`,
  `<N> checkpoint` are the real forms; passing an alias straight to the raw binary silently falls
  through to a disk-less cold boot or a no-op.
- `$5a99` is not a room-transition signal; use `(A5)+1166` (§38b) instead.
- A live snapshot's static memory alone can settle a "what does routine X compute" question without
  running the emulator forward, and extends to a disk image's own raw bytes for "does the disk hold
  more content" (§51/§52) — though it can't identify *what kind* of content without a live boot or
  readable strings.
- When a screen isn't advancing the way expected, don't infer "does this keypress matter" from
  trials that also vary the step count — run a same-snapshot, same-step-budget A/B instead (§52).
- `gfxview.load_ram(path)` returns `(ram_bytes, base)`, that order.
- The REPL's `watch <addr> <len>` parses `<len>` as decimal, not hex.
- `kbd`/other REPL input commands only enqueue IKBD bytes for delivery during a subsequent `s`/`bp`/
  `bpc` — issue them before the step/breakpoint that should consume them, and split make/break
  codes into two separate `kbd` calls with a real `s <n>` between them (the shared
  `reverse-engineer-st-game` skill, §2).
- `bt` with no depth argument defaults to depth 8 and reliably crashes the REPL — always pass `bt 1`.
- If hand-parsing a `.snap`'s header instead of using `gfxview.py`'s loaders: `cpu.CCR` is written
  as an int16, not a byte, so the RAM-length field sits 1 byte later than expected.
- A static-analysis session's own new interpretive claim can revive a framing a doc's later
  sections already retired — grep the doc for later sections before writing a new reading.
- A "no caller found in the loaded image" static negative only rules out a plain resident caller
  already loaded; a runtime-loaded or self-modifying path stays untested until checked another way.

## Next session

Item 1 (fix or bypass the crack's own protection-dispatch bug, to read further into Disk 2 live)
and item 2 (mine `disk2_replicants.st`'s raw bytes for graphics/level structure directly, no live
boot needed) are both live and independent — worth checking with Dave on which to prioritize rather
than assuming. Item 2 is likely the faster path to concrete graphics/sprite/level content specific
to what Dave asked this session to keep pushing toward; item 1 is the more classic reversing thread
(a crack-group bug, not this project's) and has no guaranteed payoff even if solved, since it only
unblocks *more* live reading, not necessarily new understanding on its own. Prompt: `/resume
cadaver`.
