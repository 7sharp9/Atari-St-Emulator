# Impossamole: handoff

Updated 2026-09-27 by the session that ended at commit `ea5cf48`.

## Resume point

- Last commit of this workstream: `ea5cf48` (a live real-Hatari cross-check retracted two "broken
  crack" readings from the last several passes as bugs in this repo's own F# emulator instead).
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image plus the
  full snapshot chain, unchanged this session. `after_confirm_amazon.snap` (PC=`$3b4`, right where
  the Amazon confirm's depacker loop starts) is a good starting point for load-path tracing. Real
  Hatari v2.6.1 is now available for cross-checks: `~/Downloads/hatari-snapshot/Hatari.app` (prebuilt)
  and full source cloned at `~/GitHub/hatari/` (needed to read `src/control.c`/`src/joy.c` for the
  remote-control protocol — see "Known traps"). The TOS ROM this repo uses is already at
  `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/after_amazon_load2.snap` to continue exploring the Amazon
  level, or `test_dirbit3_B.snap` (hero mid-walk-cycle, position `$1a574 = $00c0`) to continue from
  after a confirmed move. **Must be resumed with `--disk-a "impossamole cr replicants - emotion cr
  replicants.st"`** for any run that needs floppy reads (a bare memory/register check does not) —
  path relative to `M68000/`.
- Uncommitted work left behind: `M68000/sessions/README.md` still has the pre-existing whitespace-
  only rewrap edit noted by the last several handoffs (predates this workstream, no live session
  claims it). Also `.obsidian/` and `Cadaver/`, untracked at the repo root, not this workstream's.
  A real Hatari process may still be running in the background from this session's live cross-check
  (PID was in `/tmp/hatari.pid`, log in `/tmp/hatari_log.txt`, cmd fifo `/tmp/hatari_cmd.fifo`,
  screenshots in `/tmp/hatari_shots/`) — Dave was actively playing it at handoff time; check before
  killing it.

## Proven so far

See `reversing/impossamole/README.md`'s "Confirming a world" and "Gameplay input" sections for full
detail and addresses. Structural/mechanism findings from the prior pass all still stand:

- Movement mapping, busy-flag gating, and the object-render dispatch (`$00bada` running both
  `$1b25a`/`type==1` and `$1b3ec`/`type==2` per slot per frame through a shared masked-blit body,
  drawing directly at each object's own `(2(A0),4(A0))` screen coordinate) are unchanged.
- `$be96`'s tile classification is fully proven: a scroll-adjusted lookup (`$be2c`) into a raw
  1680x24 tile map at `$31800`, categorized through a 256-entry table at `$25000`.

**New and load-bearing: a live cross-check against real Hatari (v2.6.1, run 2026-09-27) proved two
of the last several passes' conclusions wrong.** Driven by hand through the same crack-menu →
title-fire → world-select → confirm sequence this workstream already uses (F1/Space via Hatari's
`--cmd-fifo` remote command channel for the keyboard-only crack menu, real OS-level keystrokes into
Hatari's actual window for the joystick-only title-fire/world-select-confirm steps, screenshots via
`hatari-shortcut screenshot`):

- **Confirming Klondike Mine reaches genuine gameplay on real hardware** — a real mine-cavern level,
  HUD (score/lives/ammo), a clearly visible hero sprite, ending in an actual "GAME OVER" death screen
  (`reversing/impossamole/hatari_crosscheck/hatari_klondike_gameover.png`). This emulator's own
  behavior (bounces to a blank "IMPOSSAMOLE" logo screen, zero disk reads) is real and reproducible,
  but the conclusion drawn from it three passes ago — "Klondike Mine's data is broken in this crack"
  — was wrong. It's this emulator's confirm→load path that fails, not the crack's data.
- **The Amazon gameplay screen shows a clearly visible hero sprite on real hardware** — a small
  mole-themed character (grey head, red scarf, blue suit, matching the title screen's mascot),
  standing in the exact scene this emulator has only ever rendered without one
  (`hatari_crosscheck/hatari_amazon_gameplay.png`, zoomed in `hatari_amazon_hero_zoom.png`). The
  hero's object struct in real Hatari (`$1a572`) matches this workstream's reverse-engineered layout
  exactly (`type=2`, `2(A0)`/`4(A0)` position, `6(A0)` frame index) — so the addressing/struct work
  from the last two passes stands. What's wrong is specifically that this emulator's confirm→load
  path never executes whatever real hardware executes to populate the hero's sprite bank (`$42e00`
  in this emulator, proven via `watch`/`hits` to be genuinely unreached — see the README) — not that
  the crack never loads it.

Conclusion: **this repo's F# core has a real confirm→load-path bug** (most likely FDC/disk-read
timing, or a subtly mishandled instruction somewhere between the confirm keypress and gameplay),
affecting at least Klondike Mine's level data and Amazon's hero sprite graphics. This is now the top
open item — see below.

## Open, in priority order

1. **Find where this emulator's confirm→load path diverges from real hardware.** Compare this
   emulator's trace (`ATARI_TRACE_FDC=1 ATARI_TRACE_GEMDOS=1` from `after_confirm_amazon.snap` or an
   equivalent Klondike-confirm snapshot) against real Hatari's own trace of the identical sequence
   (`tools/hatari_trace.py`, or repeat this session's live cross-check technique with Hatari's
   `hatari-debug` breakpoints) instruction by instruction from the confirm keypress onward, looking
   for the first point they disagree — a missed/failed sector read, a different branch taken, or an
   instruction this emulator handles differently. This blocks trusting *any* future "world X's data
   is broken/missing" claim in this game, and may also explain the still-unexplained missing first
   call of the `$b328` block (item 5 below) and generalizes to other games' reversing work if it's a
   shared FDC/timing bug rather than something impossamole-specific.
2. **Map the `$25000` tile-classification table's 256 entries** (which raw tile IDs from `$31800`
   read as walkable/ladder/hazard/etc) — a static dump plus cross-checking a few entries against
   `$31800`'s actual content near a known-walkable vs known-blocked spot would do it; this unlocks
   reading level layout directly instead of inferring it from sensor behaviour.
3. **Live-test ladder climbing and the jump/attack state** (`$c812`/`$227f3:=4`, `$c742`/`$227f3:=2`)
   — both still read statically only. Needs a snapshot near an actual ladder tile (findable now via
   item 2's table) or a forced sensor byte.
4. **Investigate the `type=3` special case at `$bafc`**: a routine fixed to slot `$1a5de` (a
   background-prop slot) checks `cmpi.w #$3,0(A0)` and, if true, calls `$1b3f8` — the *hero's own*
   draw body — on that slot. Slot `$1a5de` read `type=1` in every snapshot examined so far, so this
   branch has never been seen to fire; worth checking what would set that slot's type to 3 (an item
   pickup, a switch, or — possibly — this game's closest thing to an enemy/AI-driven object).
5. **Find the missing first call of the `$b328` per-world decompression block** (target `$53000`/
   `$c800` — its two siblings, targeting `$40600` and `$4c400`, fired during the Amazon load, but this
   one didn't show up in the same `hits`/`bt` census). May turn out to be the same root cause as
   item 1 rather than a separate bug.
6. **Explore the Amazon level with movement working, past this one screen** — in this emulator, once
   item 1 is resolved (or independently, to see how far this emulator's other mechanics hold up).
   Also worth checking on real Hatari for a genuine enemy/AI sighting, since this game clearly has
   real hazards (Klondike Mine killed Dave's played character on real hardware).
7. Whether Orient/Ice Land/Bermuda Triangle load correctly in this emulator, once item 1's fix (or
   diagnosis) is in hand — testing them before that is likely to just reproduce the same bug.
8. Classify the main game binary via the LINK-frame-count heuristic (§0 of the reversing skill) —
   not yet done; would confirm hand-written-asm vs compiled-C and whether the decompile route (§3b)
   is worth taking for the remaining engine code.

## Known traps

- `resume <snap> repl` does not reattach a disk image — `--disk-a` must be passed again on every
  resume for a disk-booted game, or floppy reads silently fail (see README's "Known traps").
- A busy-poll "wait for next interrupt and consume it" utility reads as stuck if you only sample the
  field it polls at rest. Also in the README.
- A `kbd`/`mouse` status byte is a raw level in RAM, not an edge-latched event, and a per-object busy
  flag can suppress a whole frame's input read on top of that — both now in CLAUDE.md and the
  README's "Known traps"/"Gameplay input" sections; no longer workstream-only.
- Diffing a held-input frame against the *pre-input* frame (rather than a same-length *no-input
  control*) reads ordinary per-frame animation as input-driven movement and doesn't identify which
  sprite actually moved — generalized into the reverse-engineer-st-game skill's cracktro A/B lesson;
  no longer workstream-only.
- The draw loop's screen base (`$1a2e4`) alternates between `$70000`/`$78000` (a real double buffer)
  — check which one a write landed in before trusting a render of "the currently displayed" buffer.
- **A "broken/missing data" conclusion drawn only from this emulator's own behavior is not safe
  without a real-hardware cross-check.** Two such conclusions in this workstream's own history
  (Klondike Mine's data, the hero's sprite bank) turned out to be this emulator's bugs, not crack
  defects — proven wrong only by actually running the same disk in real Hatari. Any future "world/
  resource X doesn't load in this crack" claim should get the same cross-check before being written
  up as settled, not just a static/zero-disk-reads argument from this emulator alone.
- **Hatari's remote-control channel (`--control-socket`/`--cmd-fifo`) cannot inject joystick input**,
  only real ST-keyboard scancodes (`hatari-event keydown/keyup <ST scancode>`, straight into
  `IKBD_PressSTKey` — confirmed by reading `src/control.c`, not guessed). Hatari's keyboard-as-
  joystick emulation (`Joy_KeyDown`/`Joy_KeyUp` in `src/joy.c`, cursor keys + Right Ctrl when a port
  is set to `--joystick 1`/`--joy1 keys`) is driven from genuine SDL key events reaching Hatari's own
  window and is not reachable through the remote command channel at all. So: crack-menu keyboard
  input (F1, Space, etc.) can be scripted headlessly via the fifo; anything the game reads as raw
  joystick-1 (`$1c4c1` in this game, per the README) needs a real window and real keystrokes.
  `osascript`/System Events synthetic keystrokes are also gated by macOS Accessibility permission
  (denied by default) — this session worked around it by asking Dave to press the actual keys
  himself while watching the real window, which also doubled as a legitimate live playthrough.
- Hatari's `hatari-debug` commands need a `$` prefix for hex addresses (`m $42e00 24`, not
  `m 42e00 24`  — the bare form is parsed as decimal and errors). A plain PC address breakpoint
  (`hatari-debug a $addr`) does not actually pause emulation when hit through the remote command
  channel (no interactive terminal attached) — it only logs a running hit count and lets emulation
  continue, and re-issuing the same command adds a *second* independent breakpoint rather than
  replacing or removing the first. Getting a genuine paused-and-query breakpoint this way would need
  a real interactive debugger session (a pty), not the fifo/socket alone — not attempted this session
  to avoid disrupting Dave's live, actively-played game.

## Next session

Start with open item 1: find where this emulator's confirm→load path diverges from real hardware.
This is the highest-value item in the whole backlog right now — it's directly responsible for at
least two wrong conclusions already written up and retracted, may explain the still-open `$b328`
missing-call question (item 5) for free, and could be silently affecting other games' reversing work
in this repo if it's a shared FDC/disk-timing bug rather than something specific to this game. Items
2-4 are independent and can be picked up in the meantime if item 1 needs a break. Item 6 (deeper
Amazon exploration, and checking real Hatari for a genuine enemy sighting) is worth doing once item 1
is either fixed or well enough understood that further exploration in this emulator won't be wasted
effort.
