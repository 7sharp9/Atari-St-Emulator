# Impossamole: handoff

Updated 2026-09-26 by the session that ended at commit (this session's doc/screenshot commit).

## Resume point

- Last commit of this workstream: this session's commit (Klondike Mine's confirm proven to loop
  back to world-select; The Amazon proven to load for real and reach a first gameplay frame).
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image plus the
  full snapshot chain. New this session: `after_refire.snap`/`after_refire2.snap` (Klondike Mine's
  confirm screen after a held fire, settled back on world-select), `after_move_orient.snap`/
  `after_move_orient_settled.snap` (cursor moved to icon index 2, The Amazon), `after_confirm_amazon
  .snap` (PC inside the byte-copy depacker at `$3b4` right after confirming Amazon),
  `after_amazon_load1.snap`/`after_amazon_load2.snap` (post-load, PC settled at `$1ab96` driven by
  template copy `$b1b6`; `after_amazon_load2.snap` is the first real gameplay frame), and
  `after_amazon_moveright.snap` (one joystick-1 "right" packet tried on the gameplay frame — no
  visible change).
- Start from: `scratchpad/impossamole/after_amazon_load2.snap` to pick up the open item below.
  **Must be resumed with `--disk-a "impossamole cr replicants - emotion cr replicants.st"`** (see
  README's "Known traps") — path relative to `M68000/`.
- Uncommitted work left behind: `M68000/sessions/README.md` still has the pre-existing whitespace-
  only edit noted by the prior handoff (predates this session, no live session claims it —
  `ListAgents` showed only an unrelated "GPU training optimization research" session). Also
  `.obsidian/` and `Cadaver/`, untracked at the repo root, not this workstream's.

## Proven so far

See `reversing/impossamole/README.md` for the full writeup and screenshots.

- Disk boot → crack menu → trainer skip → title screen → joystick-1 fire → world-select screen →
  held-fire confirm on a settled, unlocked icon: unchanged from the previous handoff, still holds.
- **Klondike Mine's post-confirm "IMPOSSAMOLE" logo screen (`after_confirm_screen.png`) loops back to
  world-select on fire; it does not advance into a level.** The prior handoff's read of `$17ac0`'s
  fire path stopped right after `jsr $bb7e` (an irrelevant cheat-word lookup) and concluded fire did
  nothing here. The very next instruction, `$017b58: jmp $17c9c` (unconditional), routes into the
  world-select screen's own re-entry setup (reinitializes the cursor object at `$1a2ea` from the
  `$17fa2` table, repoints the live screen buffer at `$53000`) and falls into `$17dd0`'s selection
  loop. Proven live: a full-frame held fire from `after_confirm_screen.snap` drives PC to `$1c3d8`
  (the same title→select transition code used the first time), and `hits 400000 b1bc 17ad4 17df4
  1813c 1847e` afterwards lands all 4 hits on `$17df4` (the world-select copy); the rendered frame
  (`after_refire2.snap`) is pixel-identical to `world_select.png`. Now in CLAUDE.md as a general rule
  (read a routine to its next control-flow instruction, not just to the first self-contained-looking
  call, before concluding an input does nothing).
- **A different world loads for real, proving Klondike Mine's data is what's broken, not the
  engine's confirm path.** Moved the select cursor to icon index 2 (The Amazon) via joystick-1
  bit 3 (increment, wraps against the `$bb79` locked mask) and confirmed with a held fire. PC lands
  at `$3b4`, a byte-copy depacker (`move.b -(A2),-(A1); dbf D1,#-4`) running out of the low,
  otherwise-idle vector-table RAM. `ATARI_TRACE_FDC=1` over the same window shows 30+ real
  `FDC read` lines across tracks 0/7/8 both sides — Klondike Mine's identical window showed zero.
  A few million steps later PC settles at `$1ab96`, the shared VBL-wait body, but driven by a
  **fourth template copy, `$b1b6`** (not `$17ac0`/`$17dd0`; `hits 300000 b1bc 17ad4 17df4 1813c
  1847e`: 12 hits, all on `$b1bc`) — previously uncharacterized. The live frame (`amazon_gameplay
  .png`) is a real level screen: hero sprite on a terraced, vegetation-covered hillside next to a
  ruined stone pillar, cloudy sky — visually nothing like the select/logo templates' blue field.
- **The game's opening "isometric platformer" label was an unverified guess and looks wrong.**
  `amazon_gameplay.png` is a plain side-view platform scene, no isometric projection. README's
  opening line now flags this instead of repeating the guess; genre is unlabelled pending a room
  that actually shows a diamond/2.5D grid.

## Open, in priority order

1. **Find the gameplay input mapping.** One joystick-1 "right" packet (bit 3, held a full VBL frame)
   on `after_amazon_load2.snap` produced no visible change — direction bits may differ from the
   select screen's mapping, gameplay may read raw keyboard instead of the joystick-1 IKBD byte used
   so far, or another input (fire, a different joystick header) may be needed first before movement
   registers. Read template copy `$b1b6`'s own body (only identified as the driver so far, not yet
   read) the same way `$17dd0` was read for world-select, to find what it actually polls each frame,
   rather than guessing more packets.
2. Why Klondike Mine specifically fails (zero disk reads where Amazon has 30+): check whether its
   `.DAT` pair (`MINES22.DAT`/`MINES33.DAT`) is truncated/corrupt in this crack, or whether the
   engine silently swallows a disk-read error for it; also worth confirming Orient/Ice Land/Bermuda
   Triangle load correctly (Amazon alone doesn't prove all four).
3. Once movement is found: explore the Amazon level, map its tile/sprite formats, and classify the
   main game binary via the LINK-frame-count heuristic (§0 of the reversing skill).

## Known traps

- `resume <snap> repl` does not reattach a disk image — `--disk-a` must be passed again on every
  resume for a disk-booted game, or floppy reads silently fail (see README's "Known traps").
- A busy-poll "wait for next interrupt and consume it" utility reads as stuck if you only sample the
  field it polls at rest. Also in the README.
- A `kbd`/`mouse` status byte is a raw level, not edge-latched — a same-packet-timing press/release
  pulse can miss every per-frame poll. In CLAUDE.md and the README's "Known traps"/"Confirming a
  world" sections.
- Reading a routine's fire/input handler only as far as the first call that looks like a complete
  explanation (a cheat-word lookup, a sound call) can miss an unconditional jump immediately after
  it that is the actual mechanism. Now a general CLAUDE.md rule; see "Proven so far" above.

## Next session

Start at `scratchpad/impossamole/after_amazon_load2.snap` (`--disk-a` attached). Read template copy
`$b1b6`'s body in full first (per-frame VBL-wait/render/input, the same shape as the other 4 copies)
to find what it actually polls for movement, rather than guessing more joystick packets — the same
read-before-guess approach that found the Klondike-Mine loop-back and the Amazon load path this
session. Once movement is confirmed, explore the Amazon level and start on tile/sprite formats.
Screenshot before and after any input change.
