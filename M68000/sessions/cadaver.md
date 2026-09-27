# Cadaver: handoff

Updated 2026-09-27 by the session that ended at commit `c0aa482` (74th pass — item 1 fully closed
live: KILL/WAKE/SLEEP/UNINV all succeed against GIANT RAT's own id 194 via type 6, not type 9). The
skill-file lesson from this pass is in the separate, shared-resource commit `7beeb7e`
(`.claude/skills/reverse-engineer-st-game/SKILL.md`).

## Resume point

- Last commit of this workstream: `c0aa482`, "cadaver: 74th pass -- item 1 fully closed live:
  KILL/WAKE/SLEEP/UNINV all succeed against GIANT RAT's own id 194 via type 6, not type 9 (which
  stays empty even in slot 27)". No emulator source changed this pass (docs only), so no rebuild or
  regression-net run is needed before building on it.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored), unchanged this pass — no new
  files added. `gameplay_empire.snap` is the only snapshot this pass touched, and only via `callcap`
  (which snapshot-restores after every call), so it is byte-identical to before.
- Start from: `gameplay_empire.snap` (CAVERN), same as recent passes. All of this pass's checks ran
  as `callcap`/`watch` recipes from that one base snapshot — no live driving, no player movement.
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
rooms scored ~96% pixel-exact against their reference screenshots), the object-verb bytecode
interpreter's core mechanism (§22-26, §49-50, §64: the 59-entry dispatch table's shape, the shared
type-6/9 id-resolver, an exhaustive multi-technique negative on any *external* caller ever reaching
the interpreter, the full opcode-id scan locating every verb's real handler address), and §65-67 (the
compressed dialogue/monster-name string table, every room's static object-id list, the live
display-name-index formula, and slot 27's unique GIANT RAT object tied to the game's own "SPINE
CREATURE" hint text — 7/59 dispatch ids pinned by exact address match).

**74th pass, item 1 closed for real** (`mechanics.md` §68): two independent live checks, both from
`gameplay_empire.snap`, no player movement needed.

- **Negative**: loading GIANT RAT's own room (slot 27, via the same `$00e854` room-transition
  trigger §67 validated) writes nothing into type 9's 10-slot creature index table (`$4c636`) or the
  global creature-id slot (`2120(A5)`) — confirmed both by an armed `watch` producing zero hits across
  the full 2,000,000-step call and by grepping the call's own complete ~1500-byte memory delta for
  either address range. Type 9 stays provably empty even in the one room built around a named
  monster; room-load is conclusively not how a creature would ever reach it.
- **Positive, the headline result**: the shared id-resolver (`$c542`, §22d) has two branches, not
  one — a positive 16-bit id goes to type 6 (already known 1000/1000 populated, §23c), only a
  negative sentinel goes to type 9. GIANT RAT's id, 194, is positive. Calling each of KILL (`$010354`),
  UNINV (`$01038a`), WAKE (`$0103e0`) and SLEEP (`$0103f8`) directly via `callcap` with `A1` pointed at
  a 2-byte scratch buffer holding `$00c2` (194 big-endian) makes all four take their real success
  path, not the "non-existant creature" print stub: KILL/UNINV/WAKE all `returned` cleanly with
  `A0=$00070034` in the register delta, byte-for-byte the same address `resolve(type=6, 194)` gives
  statically (`py/room_object_census.py`'s own `resolve()`); KILL's delta shows its documented 6-byte
  queue push and `1154(A5)` counter increment exactly; SLEEP's resolve is independently confirmed via
  an 8-step-capped call landing exactly on the type-6-positive branch instruction, though its own
  success action (`bsr $e172`) runs into what looks like a sound/interrupt-dependent wait under
  `callcap`'s masked-interrupt regime (same category as the already-documented PowerMonger hazard) and
  wasn't traced further. §64c's "type 9 is always empty so these verbs always fail whenever invoked"
  is corrected, not just extended: true for the type-9 branch, false for the type-6 branch, and GIANT
  RAT is concretely KILL/WAKE/SLEEP/UNINV-able by its own id right now.

## Open, in priority order

1. **Find who actually invokes the object-verb interpreter during ordinary play, with what operand.**
   §68 proves the *mechanism* succeeds against GIANT RAT when driven directly; nothing yet shows the
   shipped game ever calls KILL/WAKE/SLEEP/UNINV (or any of the 59 verbs) with any specific id during
   real gameplay — the "fourth, still-unlocated dispatch site" from §23d/§24/§64d stands unchanged.
   This is now the direct continuation of this pass's own finding: the room (slot 27) and the
   mechanism (§68) are both proven, only "who calls it and when" is missing. Concrete next step:
   find `EntityScriptDispatch`'s (`$15c70`) or a sibling routine's own call into `$010000`-`$011256`,
   or `bp`/`hits` against `$010738` (the shared resolver every verb goes through) during a long
   ordinary-play run to see if it ever fires at all outside a synthetic `callcap`.
2. **Check whether GIANT RAT is also driven through `ai.md`'s separate `EntityScriptDispatch`/3-slot
   action-script system** — a different interpreter from the one §68 tested (mechanics.md §63 already
   distinguishes them explicitly). `ai.md`'s own "no live creature has been found" framing dates from
   its 14th pass, before GIANT RAT's discovery (mechanics.md §67/§68); it needs its own live check
   (does GIANT RAT's slot ever appear in `ActiveEntitySlotBitmask`?) before that text is corrected —
   not assumed from §68's unrelated result.
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
10. `2516(A5)`'s role still unconfirmed. Only worth resolving if another item needs a real
    day/progress counter.

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
only a real entry if provably side-effect-free with no skipped push/pop — all now in
`.claude/skills/reverse-engineer-st-game/SKILL.md` §3/§5, not repeated here.)

- **`callcap`'s own unconditional memory-delta printout (`mem $addr $old->$new`) is not the same
  output as an active `watch`'s lines (`WATCH: step=...`).** `callcap` always prints the whole call's
  changed-memory footprint regardless of any `watch`; a narrow `grep`/`tail` on the combined output can
  make it look like the watch fired when it didn't, or vice versa. Grep for `WATCH:` and `callcap \$`
  by name, and confirm a targeted-range negative both ways (this pass's own §68 type-9 check).
- **The shared type-6/9 id-resolver's branch is chosen by the sign of the id itself, not by which verb
  calls it.** KILL/WAKE/SLEEP/UNINV don't inherently target type 9 — a script encoding them with a
  positive id resolves via type 6 exactly like every other verb (§68). "This verb cluster only ever
  reaches the empty type-9 table" was an assumption from having only ever seen the print-stub failure
  case, not a property of the verbs themselves.

## Next session

Item 1 is the direct continuation of this pass: with both the room (slot 27) and the resolve mechanism
(§68) now proven, the only missing piece for "does this game ever actually run a KILL/WAKE/SLEEP on
GIANT RAT" is finding the real top-level caller of the object-verb interpreter — a question that's
been open since §23d/§24 and is now the clear next frontier. Item 2 is a cheap, independent sanity
check on `ai.md`'s older, now out-of-date-looking "no live creature" framing — worth doing before
touching that file's text. Items 3-10 are unrelated loose ends, any of which can run in parallel.
Prompt: `/resume cadaver`.
