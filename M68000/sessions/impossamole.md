# Impossamole: handoff

Updated 2026-09-27 by the session that ended at commit `38985e4` (82nd pass, continued).

## Resume point

- Last commit of this workstream: `38985e4` "Amazon gameplay past the first screen (item 6,
  started)". Before it in the same pass: `c61ac29` ($b288 keypress-timing bisection).
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image,
  `coldboot_census/` (the known-good from-cold-boot scripts and `at_gameplay_final.snap`/
  `klondike_plus_30M.snap`), and new this pass `gameplay_explore/` (movement-input trials from
  `at_gameplay_final.snap`). See `scratchpad/ANCHORS.md` for the full indexed list. Real Hatari
  v2.6.1 at `~/Downloads/hatari-snapshot/Hatari.app`, source at `~/GitHub/hatari/`. TOS ROM at
  `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/gameplay_explore/ru_step8M.snap` — the furthest live Amazon
  state this workstream has: hero alive (`type=2` at `$1a572`), standing on a ledge past a water
  pool and totem-pole decorations, reached by resuming `at_gameplay_final.snap` and holding
  right+up (`kbd ff`/`kbd 09`) for 8,000,000 steps. **Must be run with `--disk-a "scratchpad/
  impossamole/impossamole cr replicants - emotion cr replicants.st"`** (path relative to `M68000/`)
  even though this stretch does no further disk I/O — the known trap below still applies to any
  `resume ... repl`.
- Uncommitted work left behind: none from this pass. The pre-existing `M68000/sessions/README.md`
  whitespace-rewrap diff (predates this workstream, flagged unowned by several prior handoffs) is
  still there and still not this workstream's to fix. `.obsidian/` and `Cadaver/` at the repo root
  are also not this workstream's.

## Proven so far

See `reversing/impossamole/README.md`'s "Why `$b288` sometimes never runs" and "Past the first
screen" sections for full detail and match counts:

- **`$b288` keypress-timing bisection is resolved, not a race.** It needs F1 then any second
  recognized key (Space, Return, and T — the "enter trainer" path — all verified interchangeable),
  in that order; firing is insensitive to hold duration (0-500,000 steps) and gap length
  (100-500,000 steps) once both keys are present, and never fires without both (tested to 35M
  steps of F1-only with zero hits). The old `after_select3.snap` lineage's exact failure is not
  reproduced by any combination tried and is now suspected to predate today's cold-boot path
  entirely — not worth further bisection time absent a new instance of the symptom.
- **Amazon gameplay driven past the single starting screen for the first time this workstream.**
  Held-right-only reproducibly (byte-identical PC across two independent re-runs, 8 checkpoints)
  walks the hero to `2(A0)=$00c0`, freezes there, gains a nonzero `+6` struct field, then the whole
  object array zeroes and the game performs a full resource reload through the same unpacker
  region the initial boot load uses. Held right+up (jump) instead avoids the reload and reaches
  genuinely new terrain — a ladder/tree structure, ground spikes, tribal totem-poles, and a water
  pool — with the hero still alive 8,000,000 steps in. The green `type=1` object previously called
  a fixed-rate parallax prop is shown to have its own autonomous motion (a 16M-step no-input
  control still drifts it `+8,+16`), narrowing that earlier characterization. The hazard/collision
  mechanism itself is **inferred from timing+visual correlation only, not yet `callcap`-proven** —
  see Open item 1.
- Everything the earlier part of the 82nd pass proved (hero sprite renders, Klondike loads a real
  mine-cavern level, both from a fresh cold boot) is unchanged and still stands.

## Open, in priority order

1. **`callcap`-prove the hazard/collision mechanism** found this pass. Find the actual
   collision-check routine (likely reached from `$c2fa`'s per-frame dispatch, alongside the sensor
   reads at `$be96`/`$c0d4`), disassemble it, and `callcap` it against known hero/creature-proximity
   states rather than relying on the timing/screenshot correlation this pass used. This replaces
   guessing "what killed the hero" with a proven mechanism.
2. **Keep driving past the totems/water** from `ru_step8M.snap` (held right+up, or whatever the
   terrain now demands) — this is the first real look at Amazon level content beyond the starting
   screen, and mapping it is the actual reverse-engineering goal.
3. Confirm whether the plain-right hazard reload is a genuine "death → return to world-select"
   (check whether it eventually reaches `$1c3d8`, the same transition routine Klondike's unattended
   death used) or a per-level retry that stays in-world.
4. The Klondike cold-boot run past ~9M steps with no input goes black and PC moves to `$1c3d8` —
   still not confirmed or rendered (may be the wrong screen buffer, see "Known traps" in the
   README). Driving Klondike with real movement input (the same technique this pass used for
   Amazon) instead of leaving it idle is probably the fastest way to resolve this too, and opens up
   actual Klondike mechanics, which have not been examined at all yet.
5. Map the `$25000` tile-classification table's 256 entries (raw tile ID → walkable/ladder/hazard).
6. Live-test the ladder-climb (`$c812`/`$227f3:=4`) and jump/attack (`$c742`/`$227f3:=2`) state
   transitions at the code level — this pass's jump input exercises the jump/attack path in
   practice but hasn't been read or proven at the disassembly level.
7. The `type=3` special case at `$bafc` — still never observed live.
8. Whether Orient/Ice Land/Bermuda Triangle load correctly in this emulator, from a fresh cold boot.
9. Classify the main game binary via the LINK-frame-count heuristic (§0 of the reversing skill) —
   not yet done.

## Known traps

- **The single biggest trap this workstream carried for a long time: `after_select3.snap` and its
  whole descendant lineage never executed the crack's one-time common-resource loader (`$b288`)**
  — resolved this pass (see "Proven so far" above), but any future finding that looks like "this
  emulator can't do X" should still be re-checked from a fresh cold boot before being written up as
  a bug, on general principle.
- `resume <snap> repl` needs `--disk-a` re-passed every time (path relative to `M68000/`); the disk
  image itself lives in `scratchpad/impossamole/`, not the repo root.
- **A REPL `snap <path>` command writes relative to the directory the `dotnet exec` process was
  launched from (`M68000/`), not relative to the snapshot being resumed or any other script
  context.** A bare filename like `snap step1M.snap` inside a script fed to a run launched from
  `M68000/` lands at `M68000/step1M.snap`, not under `scratchpad/...` — cost this pass a `mv` cleanup
  step after forgetting to write the full `scratchpad/impossamole/...` path in a `snap` command.
  Always write the full path from `M68000/` in every `snap` line of a REPL script.
- A `kbd`/`mouse` status byte is a raw level in RAM, not an edge-latched event; a per-object busy
  flag can suppress a frame's input read on top of that (in CLAUDE.md/README, no longer
  workstream-only).
- The screen base (`$1a2e4`) alternates `$70000`/`$78000` — check which one a write/render landed
  in; a black `snap_render.py` output can mean "wrong buffer", not "blank screen".
- A sprite spotted "in roughly the right screen area" is not proof it belongs to the object you
  think drew it — check its exact declared coordinates or breakpoint its own draw call (in
  CLAUDE.md).
- Checking only a small prefix of a memory region, or only the first byte of a multi-byte field, is
  not the same as checking the whole thing (in CLAUDE.md).
- The Blitter register range (`$FF8A00`-`$FF8A3F`) is genuinely unmapped in this emulator's MMU —
  this matches real STF hardware with no blitter fitted, not a bug.

## Next session

Start with Open item 1: find and `callcap`-prove the hazard/collision routine that killed the hero
on plain held-right this pass, using `ru_step8M.snap` (survived, alive) and a fresh `at_gameplay_final.snap`
resume with plain held-right (reproduces the death deterministically, see `gameplay_explore/
right_hold_fine.txt`) as the two states to diff. Once that mechanism is proven rather than inferred,
item 2 (driving further into the newly-revealed terrain past the totems/water from `ru_step8M.snap`)
is the highest-value next step for actually mapping Amazon's level content, which this workstream has
never seen before this pass.
