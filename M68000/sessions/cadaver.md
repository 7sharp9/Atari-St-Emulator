# Cadaver: handoff

Updated 2026-09-27 by the session that ended at commit `70a40c9` (73rd pass — two parallel subagents,
their headline claims spot-verified by hand against the live REPL/disassembly before being folded
into `mechanics.md`). Skill-file lessons from this pass are in the separate, shared-resource commit
`ce91113` (`.claude/skills/reverse-engineer-st-game/SKILL.md`).

## Resume point

- Last commit of this workstream: `70a40c9`, "cadaver: 73rd pass -- two parallel subagents close item
  1 (slot 27's unique GIANT RAT, tied to the game's own SPINE CREATURE hint text) and pin 3 more
  dispatch ids (7/59)". No emulator source changed this pass (docs + two new `py/` scripts), so no
  rebuild or regression-net run is needed before building on it.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). New this pass:
  `agents/room_census/` (the 72-room `$00e854` census corpus — `all_rooms_e854.repl`/
  `all_rooms_combined.log`, indexed in `scratchpad/ANCHORS.md`'s `cadaver/agents/room_census` row;
  regenerate by re-running the REPL driver from `gameplay_empire.snap` if missing) and
  `agents/dispatch_ids/` (one-off verification dumps/scripts, not indexed — superseded by
  `mechanics.md` §64's own text).
- Start from: `gameplay_empire.snap` (CAVERN) / `room2_tunnel_entry.snap` (TUNNEL), same as every
  recent pass — both still the base for everything in `mechanics.md` §67. No live driving to slot 27
  has happened yet; that's the next session's own first step (see below).
- Uncommitted work left behind: none of this session's own. `M68000/sessions/README.md` still carries
  the pre-existing line-wrap-only edit noted in several prior handoffs (not this session's, left
  alone per "one writer per file"). `Cadaver/` (game disk images) and `.obsidian/` (an Obsidian vault
  config) are untracked, predate this session, and aren't part of any workstream — left alone.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` §1-63 (movement collision/proximity, the icon-panel write chain, the full 72-room
world-map/adjacency graph, the door-connectivity walk, the swapped-disk side-count bug, two genuine
emulator gaps behind the "crack dispatch bug", a real CAVERN→TUNNEL crossing driven live, Disk 2's
one-time boot-time load with zero further FDC activity, CAVERN/TUNNEL having no live-reachable third
room), `graphics.md` §5a-5j (the shared 80-tile terrain catalog and its full draw pipeline, both known
rooms scored ~96% pixel-exact against their reference screenshots), and the object-verb bytecode
interpreter's core mechanism (§22-26, §49-50, §64: the 59-entry dispatch table's shape, the shared
type-6/9 id-resolver, an exhaustive multi-technique negative on any *external* caller ever reaching
the interpreter, the full opcode-id scan locating every verb's real handler address).

**65th-66th pass**: found the game's own compressed dialogue/item/spell/monster-name string table
(`name_strings.py`) and every room's static object-id list (type 5, `room_object_census.py`), then the
missing link between an object's numeric id and its live display-name index (`room_object_names.py`,
proven 3/3) — but only for the *currently loaded* room, and with a wrong theory of who writes the
field it depends on.

**73rd pass, item 1 closed** (`mechanics.md` §67): the real room-transition trigger is `$00e854`
(not `$00cd50` called in isolation, which touches none of the sprite-object array — it depends on
setup only `$00e854` does first). Calling `$00e854` with just the target room's slot number written
extends the name-index census to all 72 rooms from one base snapshot (validated 23/23 against every
already-proven name), and retracts §66's "unidentified second writer" theory: `$00ce78` writes the
correct, final value in one shot when reached through the real trigger. **226 GIANT RAT is the only
monster-cluster name index that isn't a shared decorative record — it appears exactly once, in slot
27, object id 194, `live_rec=$0005d62a`** (full address trail re-verified independently against the
live REPL this session, not just taken on report). Slot 27 is a 10×10 monster's-den-shaped room (6×
STONE, 5× BONE, a SKULL, the unique GIANT RAT, PARCHMENT/KEY/CHEST/3× FUNGHI). The game's own string
table (widened sweep, 0-999, closing §65d's "extends past 599" as negative) holds the "SPINE CREATURE"
hint text verbatim at index 272, tying SKULLs to fighting it — direct corroboration of Dave's external
walkthrough lead. 56/72 rooms fully verified; 14 rooms/35 objects hit a second, uninvestigated code
path through the room loader; slot 69 and slot 71 have unexplained anomalies (see Open item 2 below).

**73rd pass, dispatch-id pinning** (`mechanics.md` §64a/§64d): **7 of 59 dispatch ids now pinned**
by exact address match (1, 15, 18, 31, 32, 34, 35 — three new this pass: 15 UNINV, 32 MOVE's
resolve-bypassing action-only entry, 35 UNTRAP CHEST's always-erroring-but-still-writes variant).
Corrected §64c: the KILL/UNINV/WAKE/SLEEP cluster's print stubs aren't gate-less — each has a real
resolver one call-frame before it (`$010354`/`$01038a`/`$0103e0`/`$0103f8`), so the "creature table is
always empty" conclusion is now better-grounded, not weaker. id 12 re-read in full and is now more
likely a boolean condition-test for the `$0000ffba` mini-IF interpreter than a MOVE precondition
(inferred). id 30 found to be a degenerate second entry into id 25's own queue-append tail, not a new
verb. Six bounded-walk candidates (ids 2/6/9/38/53/54) investigated and explicitly rejected as false
attributions — a concrete instance of the standing caution, now with a checkable side-effect-free/
no-skipped-push-or-pop test (folded into `.claude/skills/reverse-engineer-st-game/SKILL.md`).

## Open, in priority order

1. **Confirm slot 27 is the creature's room live, not just the strongest static lead.** Drive to slot
   27 for real (or `callcap`/`hits`/`watch` its state without moving the player, the way `$00e854` was
   driven this pass) and check whether KILL/WAKE/SLEEP (`mechanics.md` §64c, real resolvers at
   `$010354`/`$01038a`/`$0103e0`/`$0103f8`) actually succeed there instead of hitting the always-empty
   type-9 creature table. This is the concrete next step to go from "strongest lead" to "proven" —
   everything needed (the room, the resolver addresses, the census tool) already exists.
2. **Chase the three room-census loose ends from §67**, all in
   `scratchpad/cadaver/agents/room_census/`'s logs, none blocking item 1's own finding: (a) the
   14-room/35-object minority that hits fewer `$00ce78` writes than its static census count — a real
   second branch through the room loader, candidates already named in §37d (`$00cdc2`/`$00cde6`/
   `$00cdf0`); (b) slot 69's 102 `$00ce78` hits against only 28 census ids (moot for the creature
   search — none of its objects carry a monster name — but structurally unexplained); (c) slot 71's
   static object-id list not ending in the usual 0 terminator.
3. **A genuine cold-boot first room load**, to confirm `$00ce78` is the writer there too, not just via
   `$00e854` re-entry (§67 only proved the re-entry path). Blocked this pass: the boot menu didn't
   respond to injected `kbd` scancodes at the point tried, for reasons not chased down — solving that
   input-injection blocker is a prerequisite for this item, not the item itself.
4. **Pin more of the 59 dispatch ids** (7/59 now). §64d catalogs what's left: the bounded-walk
   technique could be pushed further per-entry, but risks the same false-attribution failure mode
   just caught and rejected for 6 candidates — verify by hand, don't trust an automated match alone.
5. STOPACTI's raw target word (`$f8ba`, an F-line opcode) decoding as garbage while the code two bytes
   later is clean (§64a) — not explained; a `bp`/single-step check would settle whether it's ever
   really executed as-is.
6. The sconce's (visually goblet-shaped, live name index 224, `mechanics.md` §66) actual art source —
   still not identified; low priority.
7. Stack direction (does per-column tile-stack index 0 sit at floor or ceiling, `graphics.md` §5e) —
   still not proven either way.
8. Does Disk 2 add reachable content beyond CAVERN/TUNNEL? (`mechanics.md` §63) — still recommended
   closed for practical purposes.
9. `2516(A5)`'s role still unconfirmed. Only worth resolving if another item needs a real
   day/progress counter.

## Known traps

(Carried over — see git history for the full set: `ScreenBufferA/B` role-swap framing is wrong,
`movem` block-copy chunk reversal, `watch`'s step= counter is a lifetime counter not local, one-shot
breakpoint chase non-reproducibility, re-disassemble elided `...` excerpts in full, `bpc` over `bp`
for one-shot dumps, `bt depth>1` can crash the REPL, a `watch` range can bracket multiple regions in
one call, movement is joystick port 1, player = sprite slot 0, the `moveq #0,Dn`-then-`move.b`
zero-extend trap, a byte's top bits gating a whole different code path, an object's own numeric id and
its display-name index are different numbering spaces (a shared number is coincidence until a real
field ties them together), a struct field documented as "an array at `(A5)+N`" may actually be a
pointer to it, a documented loader write can be true and still not the field a later steady-state
snapshot finds there — the two new traps this pass added are now in
`.claude/skills/reverse-engineer-st-game/SKILL.md` §3/§5, not repeated here:)

- A `callcap` that touches none of the memory you expected can mean the routine depends on setup only
  its real caller does first (§67's `$00cd50`-vs-`$00e854`), not that the routine does nothing —
  check one level up the call chain before trusting a zero-effect result as a negative.
- A dispatch-table target landing mid-instruction is only a real entry if its consumed bytes are
  provably side-effect-free and no push/pop is skipped — a checkable test now in the skill, used this
  pass to accept 3 new pins and reject 6 false-attribution candidates.

## Next session

Item 1 is the direct continuation of this pass's own finding: drive to slot 27 (or otherwise get its
state live without moving the player) and check whether KILL/WAKE/SLEEP actually resolve against a
real creature there, using the already-proven resolver addresses. If that closes clean, cadaver.md's
long-standing "find a room with a creature" thread is fully proven, not just strongly inferred, and
the AI/mechanics work on the creature itself (KILL/WAKE/SLEEP's actual effects) becomes the new
frontier. Items 2/3 are loose ends from the same census, independent of item 1's own answer. Item 4
(dispatch ids) is independent and can run in parallel with item 1 the same way this pass did. Prompt:
`/resume cadaver`.
