# Cadaver: handoff

Updated 2026-09-27 by the session that ended at commit `6a823ee` (76th pass — item 1's live half:
a real driven CAVERN item-pickup walk plus an actual CAVERN→TUNNEL room transition never once reach
the shared object-verb resolver, 0/10 hits across all four legs). A skill-lesson commit, `f208db4`
(`.claude/skills/resume/SKILL.md`), sits on top and is not part of this workstream.

## Resume point

- Last commit of this workstream: `6a823ee`, "cadaver: 76th pass -- item 1's live half: a real
  driven CAVERN item-pickup walk and an actual CAVERN->TUNNEL room transition never once reach the
  shared object-verb resolver". This session also found and committed a previously-dropped 75th
  pass (`9118604`) that a prior session had written into `mechanics.md` but never committed or
  handed off — see the resume skill's new note on telling a dropped pass from another session's
  live WIP. No emulator source changed either pass (docs only), so no rebuild or regression-net run
  is needed before building on this.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). This pass added no new
  persistent files — the two verification snapshots/renders it made to confirm the live test
  (`resolver_zigzag_check.snap/.png`, a re-render of the already-known lever-boundary snapshot) were
  deleted again once cross-checked against the already-committed `room2_tunnel_entry.png`.
- Start from: `gameplay_empire.snap` (CAVERN), same as recent passes. This pass's own live test used
  the 11th/12th passes' own documented drive (`kbd ff 08` held, then the `Up/Right/Up` zigzag,
  README "12th pass") from that same base snapshot.
- Uncommitted work left behind: none of this session's own. `M68000/sessions/README.md` still
  carries the pre-existing line-wrap-only edit noted in several prior handoffs (not this session's,
  left alone per "one writer per file"). `Cadaver/` (game disk images) and `.obsidian/` (an Obsidian
  vault config) are untracked, predate this session, and aren't part of any workstream — left alone.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` §1-63 (movement collision/proximity, the icon-panel write chain, the full 72-room
world-map/adjacency graph, the door-connectivity walk, the swapped-disk side-count bug, two genuine
emulator gaps behind the "crack dispatch bug", a real CAVERN→TUNNEL crossing driven live, Disk 2's
one-time boot-time load with zero further FDC activity, CAVERN/TUNNEL having no live-reachable third
room), `graphics.md` §5a-5j (the shared 80-tile terrain catalog and its full draw pipeline, both known
rooms scored ~96% pixel-exact against their reference screenshots), the object-verb bytecode
interpreter's core mechanism (§22-26, §49-50, §64: the 59-entry dispatch table's shape, the shared
type-6/9 id-resolver, an exhaustive multi-technique negative on any *external* caller ever reaching
the interpreter, the full opcode-id scan locating every verb's real handler address), §65-67 (the
compressed dialogue/monster-name string table, every room's static object-id list, the live
display-name-index formula, and slot 27's unique GIANT RAT object tied to the game's own "SPINE
CREATURE" hint text — 7/59 dispatch ids pinned by exact address match), and §68 (KILL/WAKE/SLEEP/
UNINV all succeed live against GIANT RAT's own id 194 via the resolver's type-6 branch; type 9 stays
provably empty even in slot 27).

**75th pass** (`mechanics.md` §69): a real, previously-unmapped script-driven "teleport to room N at
(x,y)" verb found at `$010974`-`$010a7a` inside the object-verb block, matching none of the 59 known
dispatch targets. Four independent techniques (a fresh `find_ram_callers.py` sweep, re-checking the
one nearby dispatch-table slot already rejected in §64d, two `find_jump_table_hit.py`/
`find_literal_ptr.py` false positives ruled out, and a live 60,000,000-step idle `bpc`) agree nothing
reaches it in this playthrough's loaded state. Side finding: `$0069ba` is a second real caller of the
room-load routine `$00e854` (the CAVERN/TUNNEL door resolver, §67, was the only one previously known),
tied to `2516(A5)` — a plausible day-cycle room-state refresh, not yet live-tested (see item 10).

**76th pass** (`mechanics.md` §70): drove a real gameplay sequence — `kbd ff 08` held 1.2M steps
(picks up a SILVER COIN along the way, per the 10th/11th passes) then the 12th pass's own zigzag
crossing the actual CAVERN→TUNNEL room transition — with `bpc 10738 10 <legsteps>` armed on the
shared id-resolver instead of a plain `s`. **0/10 hits on every one of the four legs.** Re-ran the
identical sequence without the breakpoint and confirmed via render that the transition genuinely
completed (status bar reads "TUNNEL", matching the committed `room2_tunnel_entry.png`). This extends
§24b's static whole-image "no external caller" sweep to real dynamic play, covering the two ordinary
actions available from this snapshot (movement/pickup, room transition) — it does not close item 1.

## Open, in priority order

1. **Find who actually invokes the object-verb interpreter during ordinary play, with what
   operand.** Narrower than before this pass: movement, item pickup, and the CAVERN→TUNNEL room
   transition are now dynamically ruled out (§70), on top of the existing static 18-site whole-image
   sweep (§24b/§64d) and the direct proof the mechanism itself works when called (§68). Still
   untested live: creature encounters, inventory-menu actions, and any state only reachable from
   rooms/content this one snapshot doesn't cover. Two concrete next steps: (a) chase §69c's own open
   question — find a real per-object/per-room "script pointer" field feeding `$010974`'s `A1`
   operand (the newly-found teleport verb); if any object anywhere in the 72-room world references
   such a script, it hands this item its missing caller directly; (b) probe TUNNEL's other content
   (not the lever — its own AABB overlap is already proven unreachable, §20-21 — but anything else in
   that room) with the resolver armed the same way §70 did.
2. **Check whether GIANT RAT is also driven through `ai.md`'s separate `EntityScriptDispatch`/3-slot
   action-script system** — a different interpreter from the one §68/§70 tested (mechanics.md §63
   already distinguishes them explicitly). `ai.md`'s own "no live creature has been found" framing
   dates from its 14th pass, before GIANT RAT's discovery (mechanics.md §67/§68); it needs its own
   live check (does GIANT RAT's slot ever appear in `ActiveEntitySlotBitmask`?) before that text is
   corrected — not assumed from §68's unrelated result. Cheap, independent of item 1.
3. **Chase the three room-census loose ends from §67**, all in
   `scratchpad/cadaver/agents/room_census/`'s logs, independent of items 1/2: (a) the 14-room/35-object
   minority that hits fewer `$00ce78` writes than its static census count (§37d already named candidate
   special-case branches at `$00cdc2`/`$00cde6`/`$00cdf0`); (b) slot 69's 102 `$00ce78` hits against
   only 28 census ids; (c) slot 71's static object-id list not ending in the usual 0 terminator.
4. **A genuine cold-boot first room load**, to confirm `$00ce78` is the writer there too, not just via
   `$00e854` re-entry (§67 only proved the re-entry path). Blocked twice now: the boot menu didn't
   respond to injected `kbd` scancodes at the point tried, for reasons not chased down.
5. **Pin more of the 59 dispatch ids** (7/59 now, §64d). The bounded-walk technique could be pushed
   further per-entry, but risks the same false-attribution failure mode already caught and rejected
   for 6 candidates — verify by hand, don't trust an automated match alone.
6. STOPACTI's raw target word (`$f8ba`, an F-line opcode) decoding as garbage while the code two bytes
   later is clean (§64a) — not explained; a `bp`/single-step check would settle whether it's ever
   really executed as-is.
7. The sconce's (visually goblet-shaped, live name index 224, `mechanics.md` §66) actual art source —
   still not identified; low priority.
8. Stack direction (does per-column tile-stack index 0 sit at floor or ceiling, `graphics.md` §5e) —
   still not proven either way.
9. Does Disk 2 add reachable content beyond CAVERN/TUNNEL? (`mechanics.md` §63) — still recommended
   closed for practical purposes.
10. **`2516(A5)`'s role now has a concrete lead**, not just an open question: §69a's `$0069ba`
    routine reads it, reduces it mod 3 (`divu #3`) into `1174(A5)`, then calls `$00e854` — a
    plausible day-cycle room-state refresh. Not yet live-tested (does `2516(A5)` actually change over
    a long idle run, and does `$0069ba` actually fire when it does).

## Known traps

(Carried over — see git history for the full set: `ScreenBufferA/B` role-swap framing is wrong,
`movem` block-copy chunk reversal, `watch`'s step= counter is a lifetime counter not local, one-shot
breakpoint chase non-reproducibility, re-disassemble elided `...` excerpts in full, `bpc` over `bp`
for one-shot dumps, `bt depth>1` can crash the REPL, a `watch` range can bracket multiple regions in
one call, movement is joystick port 1, player = sprite slot 0, the `moveq #0,Dn`-then-`move.b`
zero-extend trap, a byte's top bits gating a whole different code path, an object's own numeric id and
its display-name index are different numbering spaces, a struct field documented as "an array at
`(A5)+N`" may actually be a pointer to it, a documented loader write can be true and still not the
field a later steady-state snapshot finds there, a `callcap` that touches nothing can mean the routine
depends on setup only its real caller does first, a dispatch-table target landing mid-instruction is
only a real entry if provably side-effect-free with no skipped push/pop, `callcap`'s own memory-delta
printout vs. an active `watch`'s output are not the same thing — all now in
`.claude/skills/reverse-engineer-st-game/SKILL.md` §3/§5, not repeated here.)

## Next session

Item 1 is the natural continuation: the movement/pickup/room-transition branch of ordinary play is
now closed as a live negative (§70), narrowing the search to creature encounters, inventory-menu
actions, and §69c's own script-data-format question (which could hand this item its answer directly
if a real script blob feeding `$010974` turns up). Item 2 is a cheap, independent sanity check on
`ai.md`'s older "no live creature" framing, worth doing before touching that file's text. Item 10 now
has a concrete lead (`$0069ba`) worth a quick live test alongside either. Items 3-9 are unrelated
loose ends, any of which can run in parallel.
Prompt: `/resume cadaver`.
