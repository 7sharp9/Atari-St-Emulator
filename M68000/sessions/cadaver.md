# Cadaver: handoff

Updated 2026-09-26 by the session that ends at this commit (71st pass, following the 70th's
`80aa679`/`262e17e`), which looked for a purely static way to identify a creature-bearing room
(Dave's own steer this pass) and found two previously-unused resource mechanisms doing exactly
that, short of the one remaining link. Full writeup: `reversing/cadaver/mechanics.md` §65.

## Resume point

- Last commit of this workstream: this session's own commit, "cadaver: two new static resource
  mechanisms while hunting a creature room -- per-room object-id lists (type 5) and a large
  previously-undecoded monster-name string table (71st pass)". Previous: `80aa679`/`262e17e` (70th
  pass). No emulator source changed this pass either (two new `py/` scripts + doc edits, reusing
  the already-committed `room2_tunnel_entry.snap`), so no rebuild or regression-net run is needed
  before building on it.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored) — unchanged this pass, nothing
  newly captured; `room2_tunnel_entry.snap` (pre-existing) was re-read, not re-captured.
- Start from: `gameplay_empire.snap` (CAVERN) / `room2_tunnel_entry.snap` (TUNNEL) for ordinary
  static/gameplay work, same as every recent pass. Both of this pass's own scripts ran against
  `room2_tunnel_entry.snap` alone — no live driving needed to reproduce §65's findings.
- Uncommitted work left behind: none of this session's own. `M68000/sessions/README.md` still carries
  the pre-existing line-wrap-only edit noted in several prior handoffs (not this session's, left alone
  per "one writer per file"). `Cadaver/` (game disk images) and `.obsidian/` (an Obsidian vault
  config) are untracked, predate this session, and aren't part of any workstream — left alone.

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Carried over:
`mechanics.md` §1-63 (movement collision/proximity, the icon-panel write chain, the full 72-room
world-map/adjacency graph, the door-connectivity walk, the swapped-disk side-count bug, two genuine
emulator gaps behind the "crack dispatch bug", a real CAVERN→TUNNEL crossing driven live, Disk 2's
one-time boot-time load with zero further FDC activity, CAVERN/TUNNEL having no live-reachable third
room), `graphics.md` §5a-5j (the shared 80-tile terrain catalog and its full draw pipeline, both known
rooms scored ~96% pixel-exact against their reference screenshots, the palette-formula question
closed as not-achievable/not-needed), and the object-verb bytecode interpreter's foundational finds
(§22-26, §49-50: the 59-entry dispatch table's shape, the shared type-6/9 id-resolver, LOCK=opcode 18
tied to the lever object (id 144) and causally proven live via `callcap`, an exhaustive multi-technique
negative on any *external* caller reaching the interpreter at all, and the same negative extended to a
second real id (door 155)), and §64's full 59-entry opcode-id scan (CREATE/STOPACTI/UNLOCK CHEST
pinned, the rest of the verb vocabulary's handler addresses located).

**70th pass (`mechanics.md` §64, `ai.md` §6c-2/§6e)**: generalized the single LOCK address-match into
a reusable scan (`py/verb_opcode_map.py`) across the whole 59-entry table and the full ~40-string
debug vocabulary. Three more opcode ids confirmed by exact address match: **id 1 = CREATE**
(`$010914`, first confirmed case of one verb handler calling another directly rather than only
through the byte-dispatch table), **id 31 = STOPACTI** (`$010e7e`, pairs with GOACTI, both operate on
bit 6 of the same `+15` byte LOCK/UNLOCK use for bit 2), **id 34 = UNLOCK CHEST** (`$010ee2`) — and
UNLOCK CHEST is now the second opcode in the whole spike proven causally, not just structurally:
`callcap`'d directly against the lever object (144), it clears a real 16-bit field in the object's own
record. The rest of the verb vocabulary (MOVEING, GOANI, GOMOVE, STOPMOVE, FLAG OP, GOACTI, UNTRAP/
CLEAR CHEST, DIRTY POTION, creature KILL/UNINV/WAKE/SLEEP) now has real, disassembled handler
addresses (§64b's table) even where the exact numeric id isn't pinned. Two new architectural facts:
MOVEING/GOANI resolve through resource type 4 (`$00c5a8`) rather than the type-6/9 resolver every
other verb uses, and FLAG OP is confirmed as the condition-setter for the small nested-IF bytecode
table at `$0000ffba` that §23b's "aside" had flagged but never traced. External reachability of the
whole interpreter is unchanged from §24/§26's negative — every new caller found this pass is internal
to the interpreter's own `$010000`-`$011256` span.

**71st pass (`mechanics.md` §65)**: Dave's own steer — aim toward finding a room with a creature, to
give item 2 below a live target. Re-confirmed the direct-movement route is genuinely closed (§13/
§28d/§63's three independent negatives), so looked for a static route instead and found two new
resource mechanisms: **type 5 is every room's own static object-id list**, indexed by room slot
(`py/room_object_census.py`, 2/2 cross-checked against CAVERN's known 22-object catalog and TUNNEL's
known `[0,144]`), and a large, previously-undecoded **packed dialogue/item/spell/monster-name string
table** at `(A5)+168`/`172` through the `$5ac0` character map (`py/name_strings.py`, validated 3/3
against LEVER/BOAT/PICKAXE's already-known live names). The string table holds real monster names —
`DEAD RAT`/`GIANT RAT`/`SKELETON` — and the live WAKE/SLEEP verb's own message pair (`THE CREATURE IS
SLEEPING`/`...AWAKES AND IS VERY VERY ANGRY`), direct confirmation those opcodes are creature-facing,
not dead code. **Not yet closed**: an object's own display-name index is a different numbering space
from its type-6 id (proven by the lever: id 144, name index 200), so §65a's per-room id lists can't
yet be grepped against §65b's monster-name indices — the one missing link is which type-6 record
field supplies an object's own name index (§65c/§65d has the concrete next move).

## Open, in priority order

1. **Find the type-6 record's own name-index field, then name the creature's room.** (§65c/§65d)
   `py/name_strings.py`/`py/room_object_census.py` already give the two halves (monster-name indices
   224/225/226/233, and every room's own object-id list); only the field linking an object id to its
   own name-string index is missing. Most promising lead: trace `$00fd2c`'s other callers reached from
   the collision/touch path (§4/§27b) rather than a script opcode, the way §18b traced `$defa`'s —
   that's the proximity-name-banner writer this doc has flagged as unidentified since §41, and it's
   very likely the exact field this item needs. Once found: decode it for every id in every room from
   the census and grep against the monster-name indices (widen `name_strings.py --hi` past 599 too,
   the table almost certainly continues) — this names the creature's room with proof, no live
   movement puzzle required.
2. **The KILL/UNINV/WAKE/SLEEP cluster's "always errors, no resolve" shape** (§64c) — read as likely
   explained by the creature resource table (type 9) being empty in every snapshot this spike has ever
   captured, but not proven live. Once item 1 names a real creature room, `callcap` one of these four
   handlers from a snapshot actually standing in it rather than inferring from the type-9-empty
   pattern alone.
3. **Pin the rest of the 59 dispatch ids to their verbs.** §64b's table gives real addresses for
   ~11 more verbs but not their numeric opcode ids; a further per-entry manual pass (disassemble each
   remaining target, check it against §64b's known addresses) could close more of this, but risks the
   same false-attribution failure mode the bounded walk was built to avoid — verify by hand, don't
   trust an automated match alone (see the skill's new note on this). id 12/25 are already known
   structurally real (§23a) but reach no debug string within reach of this pass's search depth.
4. **STOPACTI's raw target word (`$f8ba`, an F-line opcode) decoding as garbage while the code two
   bytes later is clean** (§64a) — not explained. Worth a `bp`/single-step check to see whether this
   address is ever really executed as-is (an emulator gap or intentional probe, per the skill's own
   "deliberately looks like garbage" trap) versus the table's own arithmetic being subtly off for this
   one entry despite matching cleanly everywhere else tested.
5. **The goblet's (graphics.md §3 slot 16, state 4) actual art source** — still not identified; low
   priority, a one-off curiosity.
6. **Stack direction** (does per-column tile-stack index 0 sit at the floor or the ceiling, graphics.md
   §5e) — still not proven either way.
7. **The CAVERN mosaic's own ~3.4% overlap-edge residual** (graphics.md §5i-2) — small, visually
   negligible, cause not identified.
8. **Does Disk 2 add reachable content beyond CAVERN/TUNNEL?** (mechanics.md §63): still recommended
   closed for practical purposes.
9. `2516(A5)`'s role still unconfirmed. Only worth resolving if another item needs a real day/progress
   counter.
10. `disk_layout.py`'s blank/data classifier only catches single-byte fills, not short-period repeats.
    No `.stx`→`.st` converter exists in `tools/`.

## Known traps

(Carried over from earlier passes — see git history for the full set: `ScreenBufferA/B` role-swap
framing is wrong, `movem` block-copy chunk reversal, `watch`'s step= counter is a lifetime counter not
local, one-shot breakpoint chase non-reproducibility, re-disassemble elided `...` excerpts in full,
`bpc` over `bp` for one-shot dumps, `bt depth>1` can crash the REPL, a `watch` range can bracket
multiple regions in one call, `gfxview.py`'s `st-interleaved` assumes 16px-wide masked blits, movement
is joystick port 1, player = sprite slot 0, use
`tools/find_ram_callers.py`/`find_field_writers.py`/`find_literal_ptr.py`/`find_jump_table_hit.py`,
the `moveq #0,Dn`-then-`move.b` zero-extend/condition-code trap, a byte's top bits gating a whole
different code path, a whole-image `disassemble.py --all` dump + call-site census to rule out a dead
type/case, a struct field documented as "an array at `(A5)+N`" may actually be a pointer to it, mask
overlapping tile/sprite art rather than pasting it opaquely, a scratch/display-list buffer generally
can't be read from a steady-state snapshot, a `bpc <addr> 1 <budget>` armed per zigzag leg catches a
one-shot room-entry routine without knowing in advance which leg crosses the door, a clustered (not
uniform) pixel-diff mismatch points at missing content over a placement bug, two lookalike routines
sitting next to each other can be genuinely different primitives not the same routine reached two
ways, a low spatially-uneven pixel-diff score against an independent reference can be a cross-tool
palette-rounding mismatch not missing content, tracing only "the first half" of a routine that both
reads and writes through a shared pointer can misattribute a callee's own scratch fields to the
caller's real output struct, confirm your own reference assets actually came from an "authoritative"
source before chasing it to unify an internal formula mismatch.)

- **When resolving what a jump-table/dispatch entry does by matching it to an error string, bound the
  forward walk** — an unbounded transitive branch-follow wanders into unrelated shared code and
  mis-attributes a handler to the wrong string. Now in `.claude/skills/reverse-engineer-st-game/
  SKILL.md` §3 (70th pass, `mechanics.md` §64). The reliable shape: the entry's own straight-line body
  (following an unconditional `bra`/`jmp` as a same-routine continuation) plus exactly one level of
  conditional-branch following, no more.
- A dispatch-table target whose raw word arithmetic is provably correct can still decode as a garbage/
  unimplemented instruction while clean, coherent code resumes a couple of bytes later (70th pass,
  STOPACTI's `$f8ba`) — don't discard a target as misaligned without checking what comes right after
  it first.
- **An object's own numeric id and its display-name string index are different numbering spaces —
  a shared number between them is very likely coincidence, not a real cross-reference, until a real
  field ties them together.** Proven by the lever: id 144, name index 200 (71st pass, §65c). Don't
  grep a room's object-id list against the name-string table's own indices and report a match as
  "found it" without first finding the actual field that supplies an object's name index — a mistake
  this pass caught before writing it up, in the same family as the address-numerology retractions
  already in this doc (§13/§28d).

## Next session

Item 1 (find the type-6 record's own name-index field, then name the creature's room) is the direct
continuation of this pass's own new leads — `py/name_strings.py` and `py/room_object_census.py` are
already the right tools, both proven against known ground truth, and only the linking field is
missing. Item 2 (the KILL/UNINV/WAKE/SLEEP cluster) follows directly once item 1 gives it a live
target. Items 3/4 are the standing interpreter loose ends from the 70th pass. Otherwise the older
open items (5-10) are all independent and small; pick whichever interests Dave. Prompt:
`/resume cadaver`.
