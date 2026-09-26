# Cadaver: handoff

Updated 2026-09-26 by the session that ends at this commit (72nd pass, following the 71st's
`989ec3e`), which closed §65's own missing link — the field that turns an object's type-6 id into
its live display-name index — proved it 3/3 against every name already known live, and used it to
correct a graphics.md misidentification (the "goblet" is actually named "SCONCE"). Full writeup:
`reversing/cadaver/mechanics.md` §66.

## Resume point

- Last commit of this workstream: this session's own commit, "cadaver: found the object-id ->
  live-name-index link, corrected graphics.md's goblet to SCONCE, ruled out CAVERN/TUNNEL as the
  creature room via this field (72nd pass)". Previous: `989ec3e` (71st pass). No emulator source
  changed this pass either (one new `py/` script + doc edits), so no rebuild or regression-net run
  is needed before building on it.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored) — unchanged this pass, nothing
  newly captured; `room2_tunnel_entry.snap` and `gameplay_empire.snap` (both pre-existing) were
  re-read (one fresh live `bpc 946a`/register-capture run against `room2_tunnel_entry.snap`, no new
  snapshot saved), not re-captured.
- Start from: `gameplay_empire.snap` (CAVERN) / `room2_tunnel_entry.snap` (TUNNEL) for ordinary
  static/gameplay work, same as every recent pass. `py/room_object_names.py` (this pass's own
  script) ran against both with no new snapshot needed.
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
not dead code. **Not yet closed as of the 71st pass**: an object's own display-name index is a
different numbering space from its type-6 id (proven by the lever: id 144, name index 200), so
§65a's per-room id lists couldn't yet be grepped against §65b's monster-name indices.

**72nd pass (`mechanics.md` §66)**: found the missing link directly — live `bpc 946a`/register
capture against `room2_tunnel_entry.snap` (Left-hold approach, same as §41-43) caught §42's own
`move.w 10(A4),D0`/`cmp.w 1222(A5),D0` comparison live, giving `A4=$59910` where `1222(A5)=200`
(the lever's own name index). Reproducing `A4`'s resolution chain as a pure static formula —
`template=resolve(type=6,id)` → `slot_off=u16(template+8)` (the room loader's own per-load slot-
offset cache, §37d) → `slot_addr=u32((A5)+56)+slot_off` → `live_rec=u32(slot_addr+6)` →
`name_index=u16(live_rec+10)` — and implementing it in `py/room_object_names.py` gives **3/3**
against every name already proven live: LEVER (id 144→200), and, new this pass with zero live
driving needed (both rooms' snapshots already had their objects resident), CAVERN's BOAT (id
257→188) and PICKAXE (id 168→197). Bonus finding: CAVERN's slot-16 "goblet" (object id 413,
graphics.md §3/§5a-2's `state=4` outlier) resolves to name index 224 = **"SCONCE"**, not a goblet —
graphics.md corrected. Checked every one of CAVERN's 22 and TUNNEL's 2 objects against the full
224-233 monster-name-index cluster: **no match** — neither already-explored room's own dressing is
hiding the creature under this field. Checked whether the formula generalizes to a one-snapshot,
all-72-room census: **it doesn't, and fails silently.** Reading LEVER's (TUNNEL-only) own
`template+8` from `gameplay_empire.snap` (CAVERN loaded, TUNNEL not) gives `$0000`, not an
out-of-range/sentinel value — it silently aliases onto CAVERN's own real slot 0 object instead of
erroring. Still open: who overwrites the room-array slot's own `+6` field after the room loader's
confirmed initial write there (a room-record pointer, not the value actually found).

## Open, in priority order

1. **Extend the name-index census (mechanics.md §66) to all 72 rooms to name the creature's room.**
   The field and the 3/3-proven formula (`py/room_object_names.py`) are done, but a one-snapshot
   census across all 72 rooms is confirmed unsafe (72nd pass): `template+8` silently aliases onto
   another real object's slot for anything outside the currently-loaded room rather than erroring,
   so don't re-check that path again. A `callcap`-driven, no-real-movement invocation of the room
   loader (`$00cd50`) per room is the likely next tool — feasible since §37d's routine takes only
   the room record pointer as real input — or actually visiting the remaining rooms. Once censused,
   grep every room's objects' name indices against 224-233 (or whatever monster indices a wider
   `name_strings.py --hi` sweep turns up) — this names the creature's room directly.
   **New lead (Dave, 72nd pass, from an external fan walkthrough at oldgames.sk — unverified against
   the emulator, treat as a hint not a fact):** the walkthrough names a **"SPINE CREATURE"** — fed to
   a prisoner in its own gaol-area rooms 19-23, one message reads (paraphrased, not quoted verbatim
   per this doc's own copyright discipline) that skulls are the weapon against it. That description
   lines up with §65b's own decoded `THE CREATURE IS SLEEPING`/`...AWAKES AND IS VERY VERY ANGRY`
   strings and the KILL/UNINV/WAKE/SLEEP cluster far better than a generic rat/spider/worm/beetle/
   jumper does. The walkthrough's own room numbering is a fan/player scheme, not confirmed to equal
   our type-3 slot indices, but its room 1 ("old mine workings": coin/diary/pick) and room 2 (pull a
   lever, opens its door "2/3") plainly match CAVERN (slot 0) and TUNNEL/LEVER (slot 1) — so slot
   0↔room 1, slot 1↔room 2 is a reasonable starting anchor, not proven further out. Worth prioritizing
   the census (or a live walk) toward the walkthrough's own gaol/prison stretch (its rooms ~13-38,
   reached via its door 8/12 from room 1) over a blind 72-room sweep.
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
5. **The sconce's (visually goblet-shaped, graphics.md §3 slot 16, state 4, live name index 224,
   mechanics.md §66) actual art source** — still not identified; low priority, a one-off curiosity.
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
- **A documented "N(A1) := room-record/template back-pointer" write from disassembling a loader
  routine can be true and still not be the field a later live read finds there.** §37d's own
  disassembly of `$00cd50`'s room-loader loop shows `$00ce78`'s `move.l A0,6(A1)` really does write
  the room-record pointer into the new object slot's `+6` field — re-confirmed this pass by checking
  the branch condition (`22(A0)`, the room record's own byte) actually takes the normal path, not the
  `$c30e`/`$c7e8` special case. But by the time ANY steady-state snapshot exists — including a
  freshly loaded, never-stepped one, no live driving needed to see it — that same field already holds
  a completely different pointer (mechanics.md §66's `live_rec`). The loader's own write is real but
  transient/superseded very early, before anything downstream ever reads it; don't assume a loader's
  documented initial write is a structure's final, steady-state value without checking a snapshot.

## Next session

Item 1 (extend the name-index census to all 72 rooms, then name the creature's room) is the direct
continuation of this pass's own new lead — `py/room_object_names.py` is already the right tool,
proven 3/3 against known ground truth, and only reaching rooms other than CAVERN/TUNNEL is missing.
The one-snapshot shortcut is already ruled out (72nd pass): go straight to a `callcap`-driven
`$00cd50` invocation per room, or an actual visit. Item 1's own new sub-lead (the external
"SPINE CREATURE" walkthrough hint, unverified) points at the gaol/prison stretch beyond CAVERN/
TUNNEL as the priority target over a blind sweep — worth trying to establish a walkthrough-room ↔
type-3-slot mapping first (starting from the slot-0/room-1, slot-1/room-2 anchor) so the census can
jump straight there. Item 2 (the KILL/UNINV/WAKE/SLEEP cluster) follows directly once item 1 gives
it a live target. Items 3/4 are the standing interpreter loose ends from the 70th pass. Otherwise
the older open items (5-10) are all independent and small; pick whichever interests Dave. Prompt:
`/resume cadaver`.
