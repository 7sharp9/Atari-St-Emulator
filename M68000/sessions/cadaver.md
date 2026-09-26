# Cadaver: handoff

Updated 2026-09-26 by the session that ended at commit `262e17e` (70th pass, following the 69th's
`e6e9ad3`/`dbf5838`), which generalized the object-verb interpreter's one-off LOCK opcode-id match
(mechanics.md §23a) into a repeatable scan across all 59 dispatch-table entries and the full
debug-string vocabulary. Full writeup: `reversing/cadaver/mechanics.md` §64, `ai.md` §6c-2/§6e.

## Resume point

- Last commit of this workstream: `80aa679` "cadaver: generalize LOCK's opcode-id match across the
  whole 59-entry verb dispatch table -- 3 more ids confirmed, UNLOCK CHEST proven causally live (70th
  pass)". `262e17e` "reverse-engineer-st-game skill: bound jump-table/dispatch verb-attribution walks"
  is this same session's skill-lesson commit (own small commit per the shared-resource rule). No
  emulator source changed this pass (Python tooling + doc edits only, reusing existing snapshots), so
  no rebuild or regression-net run is needed before building on it.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored) — unchanged this pass, nothing
  newly captured; `gameplay_empire.snap` and `room2_tunnel_entry.snap` (both pre-existing) were
  re-read, not re-captured.
- Start from: `gameplay_empire.snap` (CAVERN) / `room2_tunnel_entry.snap` (TUNNEL) for ordinary
  static/gameplay work, same as every recent pass.
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
second real id (door 155)).

**This pass (`mechanics.md` §64, `ai.md` §6c-2/§6e)**: generalized the single LOCK address-match into
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

## Open, in priority order

1. **Pin the rest of the 59 dispatch ids to their verbs.** §64b's table gives real addresses for
   ~11 more verbs but not their numeric opcode ids; a further per-entry manual pass (disassemble each
   remaining target, check it against §64b's known addresses) could close more of this, but risks the
   same false-attribution failure mode the bounded walk was built to avoid — verify by hand, don't
   trust an automated match alone (see the skill's new note on this). id 12/25 are already known
   structurally real (§23a) but reach no debug string within reach of this pass's search depth.
2. **The KILL/UNINV/WAKE/SLEEP cluster's "always errors, no resolve" shape** (§64c) — read as likely
   explained by the creature resource table (type 9) being empty in every snapshot this spike has ever
   captured, but not proven live. If picked up: single-step one of these four handlers from a
   `callcap` call and confirm there really is no earlier resolve step being skipped, rather than
   inferring it from the type-9-empty pattern alone.
3. **STOPACTI's raw target word (`$f8ba`, an F-line opcode) decoding as garbage while the code two
   bytes later is clean** (§64a) — not explained. Worth a `bp`/single-step check to see whether this
   address is ever really executed as-is (an emulator gap or intentional probe, per the skill's own
   "deliberately looks like garbage" trap) versus the table's own arithmetic being subtly off for this
   one entry despite matching cleanly everywhere else tested.
4. **The goblet's (graphics.md §3 slot 16, state 4) actual art source** — still not identified; low
   priority, a one-off curiosity.
5. **Stack direction** (does per-column tile-stack index 0 sit at the floor or the ceiling, graphics.md
   §5e) — still not proven either way.
6. **The CAVERN mosaic's own ~3.4% overlap-edge residual** (graphics.md §5i-2) — small, visually
   negligible, cause not identified.
7. **Does Disk 2 add reachable content beyond CAVERN/TUNNEL?** (mechanics.md §63): still recommended
   closed for practical purposes.
8. `2516(A5)`'s role still unconfirmed. Only worth resolving if another item needs a real day/progress
   counter.
9. `disk_layout.py`'s blank/data classifier only catches single-byte fills, not short-period repeats.
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

## Next session

Item 1 (pinning the rest of the 59 dispatch ids) is the natural continuation of this pass's own
method and the highest-leverage next step for the interpreter thread — `py/verb_opcode_map.py` is
already the right starting tool, it just needs a slower, per-entry manual pass rather than another
automated sweep. Items 2/3 are smaller, standalone loose ends from this pass. Otherwise the older
open items (4-9) are all independent and small; pick whichever interests Dave. Prompt:
`/resume cadaver`.
