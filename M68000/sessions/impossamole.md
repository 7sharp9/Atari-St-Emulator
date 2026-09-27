# Impossamole: handoff

Updated 2026-09-27 by the session that ended at commit `8f47549`.

## Resume point

- Last commit of this workstream: `8f47549` (object-render dispatch and tile-collision system
  proven; the prior handoff's "world-scroll vs screen position" question resolved; proven live that
  the hero's sprite-bank unpacker never runs anywhere on this crack's path into Amazon gameplay).
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image plus the
  full snapshot chain, unchanged this session. `after_confirm_amazon.snap` (existing, PC=`$3b4`, right
  where the Amazon confirm's depacker loop starts) was this session's main starting point. Several
  scratch snapshots taken mid-blit/mid-walk to confirm the hero's draw address and sprite-table entry
  live (`/tmp/mid_draw.snap`, `/tmp/livewalk.snap`, `/tmp/livewalk2.snap`) were **not** saved into
  scratchpad — recreate with the recipes in "Proven so far" below if needed again, all cheap (well
  under 100,000 steps from `after_amazon_load2.snap` or `after_confirm_amazon.snap`).
- Start from: `scratchpad/impossamole/after_amazon_load2.snap` to continue exploring the Amazon
  level, or `test_dirbit3_B.snap` (hero mid-walk-cycle, position `$1a574 = $00c0`) to continue from
  after a confirmed move. **Must be resumed with `--disk-a "impossamole cr replicants - emotion cr
  replicants.st"`** for any run that needs floppy reads (a bare memory/register check does not) —
  path relative to `M68000/`.
- Uncommitted work left behind: `M68000/sessions/README.md` still has the pre-existing whitespace-
  only rewrap edit noted by the last three handoffs (predates this workstream, no live session claims
  it — `ListAgents` this session showed "GPU training optimization research" and "ownhammerlabs-1c",
  neither on impossamole). Also `.obsidian/` and `Cadaver/`, untracked at the repo root, not this
  workstream's.

## Proven so far

See `reversing/impossamole/README.md`'s "Gameplay input" section for full detail and addresses.

- Movement mapping and busy-flag gating (bit 7 fire, bits 0-3 direction, `$1a5d7` busy flag,
  `$227f3` state machine): unchanged from the prior handoff, still holds.
- **The hero object (`$1a572`, `type=2`) draws through the same shared, type-gated blitter as
  background props (`type=1`), at its own literal screen `(2(A0),4(A0))`** — not a world/camera-
  scroll value as the prior handoff guessed. Proven live: `bpc 1b47a` on a fresh `after_amazon_load2`
  resume shows the draw body computing `Y*160+X/2` from the hero's own stored X/Y and adding it to
  the screen base, matching by hand. The render dispatcher is `$00bada` (called from the `$b1b6`
  gameplay template), which runs both `$1b25a` (`type==1`) and `$1b3ec` (`type==2`) per slot per
  frame; each falls into its own copy of the same masked-blit body first proven at `$1ac34`.
- **Diffing all 20 object-array slots (`$1a2ea`, 108-byte stride) between a no-input and a held-
  right-input snapshot** (same step count) shows the hero's slot is the *only* one moving with input
  (`+64,+8`); every other active slot moves the opposite way (`-44,0`) — background/parallax, not the
  hero. The green creature visible in both comparison screenshots (`amazon_noinput_2M.png`/
  `amazon_walk_right.png`) is one of these `type=1` props, not the hero.
- **The hero's entire sprite bank is unpopulated throughout this playthrough — not a per-frame
  "idle selects a blank pose" as first guessed.** The type-2 body reads its own table, separate from
  type-1's `$3b600`: `A2 = $3b600+$7800+6(A0)*384` (`$42e00`, 384 bytes/entry). Live-drove the hero
  into an actual walk (`kbd ff`/`kbd 08` + ~70,000 steps, short of a full ~200,000-step cycle) and
  caught `$227f3=1` with real non-zero frame indices (`7`, `9` across two drives) — then checked the
  *exact* live `A2` the code was about to read (`bpc 1b4f8`) against that address: every entry
  checked (`0`, `7`, `9`) is all-zero, and a 4000-byte scan from `$42e00` found no non-zero byte at
  all.
- **Proven live that the unpacker call for `$42e00` never runs at all, anywhere on the path into
  Amazon gameplay.** `watch 42e00 9600` held from `after_confirm_amazon.snap` (PC=`$3b4`) across
  5,000,000 steps (past confirmed entry into real gameplay) caught zero writes; the same watch over
  the same run caught 100/100 sanity-check writes to `$53000`, ruling out a tooling gap. A `hits`
  census on the block believed to call the `$42e00` unpacker (`$b288`, its call site `$b2ca`, plus
  `$b328` and the gameplay loop entry `$b1bc` as sanity checks) landed **zero** hits on all four
  across the same window. The unpacker routine (`$1c6de`) did fire twice, but both returns (`bt 1`)
  trace to the *other* per-world decompression block at `$b328`-`$b3a8` (keyed by `$bb76`, the
  selected-world index), targeting `$40600`/`$4c400` — not `$42e00` — and even there only 2 of that
  block's 3 straight-line calls fired (the first, targeting `$53000`, must be reached some other way,
  now its own small open item). Conclusion: this crack's boot-to-gameplay path never populates the
  hero's graphic bank at all — not a per-frame gating question, a load-path one.
- **`$be96`'s tile classification, fully proven**: `$c0d4` samples up to 11 points around the hero's
  position through `$be2c`, which converts `((2(A0)-$20)+$227b6)>>3` / `clamp((4(A0)-8)>>3,0,23)`
  into a lookup into a raw byte tile-map at `$31800` (1680 cols x 24 rows, row stride `$690`);
  `$be96` maps that raw byte through a 256-byte category table at `$25000` into the `$227e0`-`$227eb`
  sensor bytes `$c488`'s handlers read. `$227b6` (added inside `$be2c`) is the level's actual
  horizontal scroll counter — a separate variable from the hero's own position — and is the source of
  the background props' `-44` shift above.
- **Lesson applied to the README's "Known traps"**: `$1a2e4` (the draw loop's screen base) alternates
  between `$70000`/`$78000`, a real double buffer; `snap_render.py`'s own docstring already warns
  about exactly this class of mismatch (the Cadaver `ScreenBufferA/B` precedent) but it cost time
  here before being found and applied — confirm which buffer a write landed in before trusting a
  "no visible pixels" read against the currently-displayed one.

## Open, in priority order

1. **Map the `$25000` tile-classification table's 256 entries** (which raw tile IDs from `$31800`
   read as walkable/ladder/hazard/etc) — a static dump plus cross-checking a few entries against
   `$31800`'s actual content near a known-walkable vs known-blocked spot would do it; this unlocks
   reading level layout directly instead of inferring it from sensor behaviour.
2. **Live-test ladder climbing and the jump/attack state** (`$c812`/`$227f3:=4`, `$c742`/`$227f3:=2`)
   — both still read statically only. Needs a snapshot near an actual ladder tile (findable now via
   item 1's table) or a forced sensor byte.
3. **Investigate the `type=3` special case at `$bafc`**: a routine fixed to slot `$1a5de` (the
   background-prop slot that scrolled `-44` two sessions ago) checks `cmpi.w #$3,0(A0)` and, if true,
   calls `$1b3f8` — the *hero's own* draw body — on that slot. Slot `$1a5de` read `type=1` in both
   snapshots examined so far, so this branch has never been seen to fire; worth checking what would
   set that slot's type to 3 (an item pickup, a switch, or the game's only other moving object found
   so far — possibly the first lead toward something enemy/AI-like, since nothing hostile has been
   found yet at all on this one screen).
4. **Explore the Amazon level with movement working, past this one screen.** No enemy or AI-driven
   object has been encountered anywhere yet; every object seen is the hero, a static prop, or a
   dormant (`type=0`) slot. Walking further is the only way to find out whether this game has visible
   enemies at all, and separately, whether the hero's sprite bank (`$42e00`, confirmed never written
   from confirm through 5M steps of this one screen) ever gets populated further into the level — if
   it doesn't even there, that points at this crack being broken for the hero graphic entirely rather
   than a trigger further away.
5. **Find the missing first call of the `$b328` per-world decompression block** (target `$53000`/
   `$c800` — its two siblings, targeting `$40600` and `$4c400`, fired during the Amazon load, but this
   one didn't show up in the same `hits`/`bt` census). Small, likely a quick static read of what
   reaches `$b354` a different way, but worth closing since it's the same block the hero-sprite
   investigation just characterized.
6. Why Klondike Mine specifically fails (zero disk reads where Amazon has 30+): check whether its
   `.DAT` pair (`MINES22.DAT`/`MINES33.DAT`) is truncated/corrupt in this crack, or whether the
   engine silently swallows a disk-read error for it; also worth confirming Orient/Ice Land/Bermuda
   Triangle load correctly (Amazon alone doesn't prove all four) — and, given this pass found the hero
   sprite bank never loads either, whether Klondike Mine's brokenness and this are related symptoms of
   the same underlying crack defect.
7. Classify the main game binary via the LINK-frame-count heuristic (§0 of the reversing skill) —
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
- New this session, now in the README's "Known traps": the draw loop's screen base (`$1a2e4`)
  alternates between two physical addresses (a real double buffer) — check which one a write landed
  in before trusting a render of "the currently displayed" buffer to show it.

## Next session

Start at `scratchpad/impossamole/after_amazon_load2.snap` (`--disk-a` attached). Pick open item 1
first (map the `$25000` tile-classification table) — it's independent and unlocks item 2 (ladder/
jump-attack live tests) and reading level layout directly. Item 3 (`type=3` at `$1a5de`) is a small,
concrete lead toward whatever this game's closest thing to an enemy/AI-driven object is — worth a
quick look before committing to item 4's larger push further into the level, which now also carries
the hero-sprite-bank question (does it ever populate further into the level, or is this crack simply
missing the hero graphic outright).
