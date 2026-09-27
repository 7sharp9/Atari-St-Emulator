# Impossamole: handoff

Updated 2026-09-27 by the session that ended at commit (this handoff's own commit, 81st pass).

## Resume point

- Last commit of this workstream before this pass: `d47e62d` (80th pass: real-Hatari cross-check
  found this emulator's confirm→load path buggy for Amazon).
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image plus the
  full snapshot chain. New this pass: `at_icon2_settled.snap` (Amazon/icon-2 highlighted and settled
  at world-select — see `ANCHORS.md`). Real Hatari v2.6.1 still at `~/Downloads/hatari-snapshot/
  Hatari.app`, source at `~/GitHub/hatari/`. TOS ROM at `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/after_select3.snap` (Klondike Mine highlighted+settled at
  world-select) or the new `at_icon2_settled.snap` (Amazon highlighted+settled) to redrive either
  world's confirm sequence. **Must be resumed with `--disk-a "scratchpad/impossamole/impossamole cr
  replicants - emotion cr replicants.st"`** (path relative to `M68000/` — the disk image lives in
  `scratchpad/impossamole/`, not the repo root; a session this pass briefly pointed `--disk-a` at a
  nonexistent repo-root path before finding it there).
- Uncommitted work left behind: none from this pass. The pre-existing `M68000/sessions/README.md`
  whitespace-rewrap diff (predates this workstream, flagged unowned by several prior handoffs) is
  still there and still not this workstream's to fix. `.obsidian/` and `Cadaver/` at the repo root are
  also not this workstream's.

## Proven so far

See `reversing/impossamole/README.md`'s "Confirming a world", "Gameplay input" and "Known traps"
sections for full detail. This pass's changes to the prior understanding:

- **The "Amazon-specific confirm→load bug" framing from the 80th pass is too narrow.** The identical
  empty-`$42e00` hero-sprite-bank condition reproduces in Klondike Mine too: the same live breakpoint
  the 80th pass used (`bpc 1b4f8`) resolves to the exact same `A2=$00042e00`, and a full 384-byte dump
  (not a leading sample) is 0/384 nonzero in *both* worlds. This is not a per-world bug; it's either a
  general regression (no world's hero sprite draws in this emulator) or the two worlds were never
  expected to source hero graphics the same way (unverified against real hardware for Klondike).
- **Ruled out via a full hardware-register comparison: not a stubbed/unimplemented peripheral.**
  Watched the entire `$FF8000`-`$FFFC10` I/O space across the whole confirm-to-gameplay run for both
  worlds — identical touched-register sets (video/palette, FDC, DMA, YM2149, MFP). Neither world
  touches the Blitter range (`$FF8A00`+, confirmed genuinely unmapped here — real `BusError`, matching
  real STF-without-blitter hardware, not a silent stub — but moot since it's unused either way).
- **Item 5 from the 80th pass ("$b328's missing first call") is resolved: it was a trace-window
  artifact, not a bug.** A full FDC/GEMDOS trace from the actual confirm keypress (not from a
  downstream snapshot already past the depacker) shows all three of `$b328`'s calls firing, in order,
  for both worlds: `$53000`/`$c800`, `$40600`/`$2800`, `$4c400`/`$6c00` — each a real Fopen/Fread/Fclose
  triple with genuine FDC activity and real (non-garbage) resulting data. `$b328` itself (the per-world
  loader, keyed by `$bb76`) is fully read and understood this pass: table at `$b3ea`, 12-byte stride,
  3 pointers per world; its single caller (`$b0ee`, reached unconditionally from the world-select fire
  handler) fires for every world confirm, not just some.
- **A grey humanoid figure this pass initially reported as "Klondike's hero rendering" is retracted.**
  It does not sit at the hero object's own declared coordinates (a precise crop at `$40`,`$90` doesn't
  contain it — it's ~20-30px further right). Unidentified; likely background/tile art. General lesson
  now in `CLAUDE.md`: don't attribute a visible sprite to an object by screen-region proximity, check
  its exact declared position or breakpoint its own draw call.
- The `$b288`-`$b326` block (loads `CHARS11.DAT`/`SPRTS22.DAT`/`SPRTS33.DAT` to
  `$24000`/`$3b600`/`$42e00`) has no caller found by a static whole-RAM scan (`find_ram_callers.py`)
  in either world's post-confirm snapshot — consistent with either "never called at all" or "called
  once, earlier than either snapshot, from code since overwritten" (crack menu / title sequence).
  Not yet distinguished — see Open item 1.
- Everything the 79th/80th passes proved about movement mapping, the object-render dispatch, and
  `$be96`'s tile classification is unchanged and still stands.

## Open, in priority order

1. **Find whether `$b288` (the common `CHARS11`/`SPRTS22`/`SPRTS33` loader) ever runs in this
   emulator, in any world.** Two ways to settle it: (a) `hits`/`watch` on `$b288`/`$24000` from a
   **cold boot** (not a downstream world-select snapshot) to see if it fires even once during the
   crack-menu/title sequence; (b) extend the real-Hatari cross-check to Klondike Mine specifically —
   check the hero object's actual sprite-table address on real hardware to learn whether Klondike's
   hero is *also* sourced from `$42e00`/`$3b600` (shared) or something per-world. This replaces the
   80th pass's "diff confirm→load traces instruction-by-instruction" plan — the per-world loader
   (`$b328`) is now proven identical in shape between worlds, so that diff would find nothing; the gap
   is specifically the never-found-caller common-resource block.
2. Map the `$25000` tile-classification table's 256 entries (raw tile ID → walkable/ladder/hazard).
3. Live-test ladder climbing and the jump/attack state (`$c812`/`$227f3:=4`, `$c742`/`$227f3:=2`) —
   both still read statically only.
4. The `type=3` special case at `$bafc` (slot `$1a5de` drawing through the hero's own body when its
   type reads 3) — still never observed live.
5. Explore the Amazon level with movement working, past this one screen, once item 1 is resolved (or
   independently) — and check real Hatari for a genuine enemy/AI sighting.
6. Whether Orient/Ice Land/Bermuda Triangle load correctly in this emulator, once item 1 is in hand.
7. Classify the main game binary via the LINK-frame-count heuristic (§0 of the reversing skill) — not
   yet done.

## Known traps

- `resume <snap> repl` needs `--disk-a` re-passed every time (path relative to `M68000/`); the disk
  image itself lives in `scratchpad/impossamole/`, not the repo root.
- A `kbd`/`mouse` status byte is a raw level, not an edge-latched event, and a per-object busy flag
  can suppress a frame's input read on top of that (now in CLAUDE.md/README, no longer workstream-only).
- A busy-poll "wait for next interrupt" utility reads as stuck if you only sample at rest; prove with
  `hits`/`watch` (now in CLAUDE.md, no longer workstream-only).
- The screen base (`$1a2e4`) alternates `$70000`/`$78000` — check which one a write landed in.
- **A sprite spotted "in roughly the right screen area" is not proof it belongs to the object you
  think drew it — check its exact declared coordinates or breakpoint its own draw call** (now in
  CLAUDE.md).
- **Checking only a small prefix of a memory region, or only the first byte of a multi-byte field,
  is not the same as checking the whole thing** — an object's type field is a 16-bit word (not the
  first byte alone), and a loaded file's first 64 bytes can be a legitimate zero-padded header while
  the rest of the buffer is real data (now in CLAUDE.md).
- **A trace/watch window that starts at a downstream snapshot (already past the event you're
  checking for) will read as "never happens"** even when it did happen, just earlier. This cost both
  the 80th pass (the "$b328 missing call" false alarm) and this pass (an initial "Amazon never loads
  its second file" false alarm, corrected once a full trace from the actual confirm keypress was run).
  Always trace from the actual triggering input, not from a snapshot already past it, before
  concluding something never fires.
- The Blitter register range (`$FF8A00`-`$FF8A3F`) is genuinely unmapped in this emulator's MMU
  (`WriteByte`/`ReadByte`'s catch-all falls through to a real `BusError`) — this matches real STF
  hardware with no blitter fitted, not a bug, but worth knowing if a future game's routine does use it.

## Next session

Start with Open item 1: find whether `$b288` (common sprite/font loader) ever runs in this emulator.
Cold-boot a `hits`/`watch` census on it first (cheapest test); if it never fires from cold boot either,
this is a general regression affecting every world, not an Amazon-specific one, and the next question
becomes why `$b288` itself is never called (find its own caller, likely in the crack-menu/title code
that runs before any world-select snapshot). If it does fire from cold boot, the bug is downstream of
that (a decompression or copy step that clears/never-writes `$42e00`) — re-run the same live-breakpoint
technique (`bpc 1b4f8`) from cold boot instead of from a snapshot to see fresh, not-yet-overwritten
state. Item 2-4 are independent and can be picked up in the meantime.
