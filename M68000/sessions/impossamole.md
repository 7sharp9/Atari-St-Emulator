# Impossamole: handoff

Updated 2026-09-27 by the session that ended at commit (this handoff's own commit, 82nd pass).

## Resume point

- Last commit of this workstream before this pass: `83b2e7a` (81st pass: reframed the hero-sprite
  bug as world-general, not Amazon-specific — since retracted, see below).
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image, the old
  `after_select3.snap`/`at_icon2_settled.snap` lineage, and new this pass:
  `coldboot_census/script.txt` (Amazon) and `coldboot_census/klondike_script.txt` (Klondike), the
  from-cold-boot REPL scripts that reliably run the `$b288` common-resource loader — see
  `scratchpad/ANCHORS.md` for the full snapshot list. Real Hatari v2.6.1 still at
  `~/Downloads/hatari-snapshot/Hatari.app`, source at `~/GitHub/hatari/`. TOS ROM at
  `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/coldboot_census/script.txt` or `klondike_script.txt`, run as a
  **fresh cold boot** (`dotnet exec ... 724388 repl --disk-a ... < script.txt`), not by resuming
  `after_select3.snap`/`at_icon2_settled.snap` — that lineage's own original boot skipped the
  `$b288` load (see "Proven so far"). **Must be run with `--disk-a "scratchpad/impossamole/
  impossamole cr replicants - emotion cr replicants.st"`** (path relative to `M68000/`).
- Uncommitted work left behind: none from this pass. The pre-existing `M68000/sessions/README.md`
  whitespace-rewrap diff (predates this workstream, flagged unowned by several prior handoffs) is
  still there and still not this workstream's to fix. `.obsidian/` and `Cadaver/` at the repo root
  are also not this workstream's.

## Proven so far

See `reversing/impossamole/README.md`'s "Real-hardware cross-check", "Why no hero sprite is
visible", "Confirming a world" and "Gameplay input" sections for full detail. This pass's changes to
the prior understanding are large — it retracts the central finding of the 80th and 81st passes:

- **The "this emulator has a confirm→load bug" framing (80th/81st passes) is retracted. It was never
  a bug in this repo's F# core — it was one specific, long-lived, reused snapshot lineage
  (`after_select3.snap` and everything descended from it, which is most of this workstream's
  snapshots since very early on) whose own original cold boot happened to skip a one-time resource
  load.** A fresh cold boot this pass (own REPL script, not a reused snapshot) through the identical
  crack-menu → title-fire → world-select → confirm sequence reaches **full parity with real Hatari
  for both worlds**: Klondike Mine loads into a genuine mine-cavern level instead of bouncing to a
  blank logo screen, and Amazon's hero sprite renders correctly (grey head, red scarf, blue suit,
  pixel-for-pixel matching Hatari's own screenshot) instead of never appearing. Reproduced
  byte-for-byte across two independent cold boots (identical `hits` census output).
- **Root-caused to `$b288`, the common `CHARS11.DAT`/`SPRTS22.DAT`/`SPRTS33.DAT` loader**: it runs
  exactly once, very early — step 1,057,153, roughly 330k steps after the trainer-skip keypress and
  tens of millions of steps before the title screen — as part of the crack's own loading sequence,
  not as part of the confirm→load path at all. This is why the 79th-81st passes' static whole-RAM
  scan of post-confirm snapshots never found a caller: by confirm time the caller code is long since
  overwritten by later loads. Directly checked against the old lineage to localize the divergence:
  resuming `after_select3.snap` itself (already at world-select, before any world is chosen) and
  dumping `$42e00` shows it is **already** all-zero there — so whatever skipped `$b288` happened
  during that lineage's own original boot, before world-select was ever reached, not afterward.
- **The old lineage's exact original boot-menu keypress timing is lost** — no `.repl` script was ever
  saved from whichever early pass first produced `after_select3.snap`, so it can't be directly
  diffed against this pass's known-good timing. What's proven is that one specific, reproducible
  timing (`kbd 3b`/`s 100000`/`kbd bb`/`s 500000`/`kbd 39`/`s 500000`/`kbd b9` from the boot-menu
  wait point) reliably works; whether `$b288`'s execution is genuinely timing-sensitive (a race this
  emulator's FDC/DMA model resolves differently at different step counts) or the old lineage did
  something else entirely (different trainer-skip key, etc.) is the new top open item.
- Two new committed screenshots prove the parity claim: `coldboot_amazon_gameplay.png` /
  `coldboot_amazon_hero_zoom.png` (hero visible, matching `hatari_amazon_hero_zoom.png`) and
  `coldboot_klondike_gameplay.png` (genuine mine-cavern level, matching
  `hatari_klondike_gameover.png`'s layout). The old lineage's screenshots (`amazon_gameplay.png`,
  `after_confirm_screen.png`) are kept for reference with corrected captions, not deleted.
- Everything the 79th-81st passes proved about movement mapping, the object-render dispatch, the
  hero's screen-space draw formula, and `$be96`'s tile classification is unchanged and still stands —
  none of that was ever wrong, it just ran on top of an incompletely-loaded RAM image.

## Open, in priority order

1. **Characterize why `$b288`'s execution is sensitive to early-boot keypress timing.** Bisect the
   known-good script's gaps (`s 100000`/`s 500000`/`s 500000` around the F1 and trainer-skip keys),
   one variable at a time, re-running the cold-boot `hits` census on `b288` after each change, to find
   the boundary where it stops firing. That boundary is the actual mechanism. This replaces the old
   Open item 1 ("does `$b288` ever run") — it does; now the question is what gates it.
2. Confirm what screen the Klondike cold-boot run reaches after ~9-12M steps of no player input (goes
   black, PC moves to the shared `$1c3d8` transition routine — likely an unattended death, not yet
   rendered/confirmed; the screen may be on the buffer `snap_render.py` isn't currently displaying,
   see README "Known traps"). Better: drive Klondike with real movement input from the fresh-cold-boot
   lineage instead of leaving it running untouched, and examine mine-cavern gameplay mechanics, which
   haven't been looked at at all yet (only Amazon's have).
3. Map the `$25000` tile-classification table's 256 entries (raw tile ID → walkable/ladder/hazard).
4. Live-test ladder climbing and the jump/attack state (`$c812`/`$227f3:=4`, `$c742`/`$227f3:=2`) —
   both still read statically only.
5. The `type=3` special case at `$bafc` (slot `$1a5de` drawing through the hero's own body when its
   type reads 3) — still never observed live.
6. Explore the Amazon level with movement working, past this one screen — from the fresh-cold-boot
   lineage now that the hero sprite renders, this is finally worth doing.
7. Whether Orient/Ice Land/Bermuda Triangle load correctly in this emulator, from a fresh cold boot.
8. Classify the main game binary via the LINK-frame-count heuristic (§0 of the reversing skill) — not
   yet done.

## Known traps

- **The single biggest trap this workstream has been carrying since very early on: `after_select3.snap`
  and its whole descendant lineage (`at_icon2_settled.snap`, `after_confirm_amazon.snap`,
  `after_amazon_load*.snap`, etc.) never executed the crack's one-time common-resource loader
  (`$b288`), for reasons still not understood (see Open item 1).** Any future finding that looks like
  "this emulator can't do X" should be re-checked from a fresh cold boot (`coldboot_census/script.txt`
  or `klondike_script.txt`) before being written up as a bug — this pass found the entire
  "confirm→load path is buggy" conclusion from the 80th/81st passes was an artifact of reusing this
  one stale lineage across dozens of passes, not a real divergence from hardware.
- `resume <snap> repl` needs `--disk-a` re-passed every time (path relative to `M68000/`); the disk
  image itself lives in `scratchpad/impossamole/`, not the repo root.
- A `kbd`/`mouse` status byte is a raw level, not an edge-latched event, and a per-object busy flag
  can suppress a frame's input read on top of that (now in CLAUDE.md/README, no longer workstream-only).
- A busy-poll "wait for next interrupt" utility reads as stuck if you only sample at rest; prove with
  `hits`/`watch` (now in CLAUDE.md, no longer workstream-only).
- The screen base (`$1a2e4`) alternates `$70000`/`$78000` — check which one a write/render landed in;
  a black `snap_render.py` output can mean "wrong buffer", not "blank screen" (this pass hit this with
  the Klondike post-gameplay snapshots and left it as Open item 2 rather than resolving it, given time).
- **A sprite spotted "in roughly the right screen area" is not proof it belongs to the object you
  think drew it — check its exact declared coordinates or breakpoint its own draw call** (now in
  CLAUDE.md).
- **Checking only a small prefix of a memory region, or only the first byte of a multi-byte field,
  is not the same as checking the whole thing** (now in CLAUDE.md).
- **A trace/watch window that starts at a downstream snapshot (already past the event you're
  checking for) will read as "never happens"** even when it did happen, just earlier — this is
  exactly what made `$b288` look uncalled for three passes running (79th-81st all checked from
  post-confirm or post-select snapshots). Always trace from the actual triggering input (ideally a
  cold boot) before concluding something never fires.
- The Blitter register range (`$FF8A00`-`$FF8A3F`) is genuinely unmapped in this emulator's MMU — this
  matches real STF hardware with no blitter fitted, not a bug.

## Next session

Start with Open item 1: bisect the F1/trainer-skip keypress timing to find what actually gates
`$b288`'s execution. Vary one gap at a time from the known-good script
(`scratchpad/impossamole/coldboot_census/script.txt`) and re-run the cold-boot `hits` census after
each change — the step count where it stops firing is the mechanism. Item 2 (confirm the Klondike
death/end screen) is a quick, independent side quest if item 1 stalls. Once item 1 is understood (or
set aside), item 6 (driving Amazon past this one screen, now that the hero renders) is the highest-value
next step for actually reverse-engineering the game rather than the emulator's own boot quirks.
