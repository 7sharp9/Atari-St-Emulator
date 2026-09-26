# Impossamole: handoff

Updated 2026-09-26 by the session that ended at commit `faa63fa`.

## Resume point

- Last commit of this workstream: `faa63fa` (identifies the world-select confirm input: hold fire,
  not a pulse).
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image, an
  `extracted/` directory, and the snapshot chain through `after_select3.snap` (world-select screen,
  Klondike Mine highlighted) → `after_confirm_fire.snap` (mid-transition, PC inside TOS ROM at
  `$00fc1bea` right after a held fire on Klondike Mine) → `after_confirm_screen.snap` (settled on a
  new, not-yet-identified plain "IMPOSSAMOLE" logo screen — screenshot committed as
  `reversing/impossamole/after_confirm_screen.png`). A handful of `test_*.snap`/`.png` files from
  this session's input experiments (return/space/joystick-0/direction/double-tap probes, all
  negative results) are also left in the directory; only the `after_*` ones matter going forward.
- Start from: `scratchpad/impossamole/after_confirm_screen.snap` to pick up the open item below.
  **Must be resumed with `--disk-a "impossamole cr replicants - emotion cr replicants.st"`** (see
  README's "Known traps") — the path is relative to `M68000/`, i.e.
  `scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st`.
- Uncommitted work left behind: `M68000/sessions/README.md` has a pre-existing uncommitted
  whitespace-only edit (two paragraphs unwrapped to single lines) that predates this session and
  isn't claimed by any live session (`ListAgents` showed none on this repo) — left alone per "one
  writer per file"; flag it to Dave if it's still sitting there. Also two untracked, unrelated paths
  at the repo root (`.obsidian/`, `Cadaver/`) — not touched, not this workstream's.

## Proven so far

See `reversing/impossamole/README.md` for the full writeup and screenshots.

- Disk boot → crack menu → trainer skip → title screen → joystick-1 fire → world-select screen:
  unchanged from the previous handoff, still holds.
- **The world-select confirm input is a held joystick-1 fire, not a pulse.** The select screen runs
  through one of 5 copies of a shared per-frame template (`find_ram_callers.py <snap> 1ab8a 1abb2
  1ac34`; `hits <n> <5 JSR sites>` identifies which copy is live — `$17dd0` for this screen). Its
  cursor object (`$1a2ea`) exposes the highlighted icon index (byte 78), a "settled" flag (`$227f3`),
  and a locked-icon bitmask (`$bb79`, live value `$10` = only Bermuda Triangle locked); only on a
  frame where settled and unlocked does `$017e9e` test `btst #7,$1c4c1.l`. `$1c4c1` is a raw level,
  not edge-latched: a press/release pulse timed by the gap *inside* one IKBD packet (`kbd ff`/`s
  30`/`kbd 80`) is far shorter than one VBL frame and can miss the one frame that polls it — this is
  exactly why the prior handoff's fire attempts looked like "nothing happens". Holding fire for
  60000+ steps before releasing reliably drives PC into TOS ROM (`$00fc1bea`, a GEMDOS call) — proven
  live, reproducible from `after_select3.snap`. Now also a general CLAUDE.md rule (kbd/mouse status
  bytes need a full-frame hold to test reliably).
- **Past the confirm, PC lands on a new, unidentified logo screen** (`after_confirm_screen.png`):
  plain "IMPOSSAMOLE" text on a blue field, visually distinct from the earlier `title_logo.png`.
  Running through the *other* template copy (`$17ac0`, confirmed via backtrace). `ATARI_TRACE_FDC=1`
  over 500k steps here shows zero disk reads, so it is not a background load-progress wait; it is an
  idle loop with its own `$22806` frame counter. A fire here routes through `$17ac0`'s local fire
  handler (`jsr $bb7e`), which turned out to be an unrelated hidden password/cheat-word listener
  (`$1837e`'s table decodes as ASCII words including `COMMANDO`, `JUGGLERS`) keyed off `$bb7d`
  (stays 0 on this screen, so nothing fires) — not the mechanism that will advance this screen.

## Open, in priority order

1. **Identify what the post-confirm logo screen (`after_confirm_screen.snap`) is, and what advances
   past it.** Candidates: a per-world loading/briefing page waiting on a different input; a
   fallback because Klondike Mine's own assets are incomplete/missing in this crack (worth trying a
   *different* world, e.g. The Orient, to see if it reaches the same screen or genuinely loads); or a
   screen that auto-advances once something else (not disk I/O) completes. Read the `$17ac0` template
   copy's own body in full (only its up/down-toggle and fire-cheat-dispatch parts have been read so
   far) for a state variable this screen itself sets/reads that differs from the plain attract loop,
   and check its callers the same way `$17dd0` was pinned down (`hits` against `$17ac0`'s own JSR
   sites while sitting on this screen, to rule out it just being a literal return to attract mode).
2. Once a world genuinely loads: reach actual isometric gameplay for one of the 5 worlds.
3. Classify the main game binary once reached via GEMDOS `Pexec` (watch for the trace line) — likely
   hand-written 68000 asm given the crack/trainer wrapper, but confirm via the LINK-frame-count
   heuristic (§0 of the reversing skill) rather than assuming.

## Known traps

- `resume <snap> repl` does not reattach a disk image — `--disk-a` must be passed again on every
  resume for a disk-booted game, or floppy reads silently fail (see README's "Known traps").
- A busy-poll "wait for next interrupt and consume it" utility reads as stuck if you only sample the
  field it polls at rest. Also in the README.
- A `kbd`/`mouse` status byte is a raw level, not edge-latched — a same-packet-timing press/release
  pulse can miss every per-frame poll. Now in CLAUDE.md and the README's "Known traps" (general rule)
  and "Confirming a world" section (this workstream's concrete instance).

## Next session

Start at `scratchpad/impossamole/after_confirm_screen.snap` (`--disk-a` attached). Read the `$17ac0`
template copy's full body first (it's only partially read) to find what's actually gating this
screen, rather than guessing inputs — the same reading-before-guessing approach that found the
confirm mechanism this session, after several rounds of guessing packets got nowhere. If reading
doesn't turn up an obvious gate, try firing with a full-frame hold (per the new CLAUDE.md rule) before
concluding the screen needs something else; also worth trying a different world (not Klondike Mine)
from `after_select3.snap` in case this is Klondike-specific breakage in the crack. Screenshot before
going further once anything changes.
