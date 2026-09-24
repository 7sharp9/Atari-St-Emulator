# Cadaver — mechanics (14th pass)

Grounded in a full linear disassembly of `$008870`–`$008b98` (`MovementStep_ObstacleCheck`) and its
callers/callees against `room2_lever_boundary.snap` (Empire release, TUNNEL room). Confirms the
question the 13th pass's README left open: rooms are one hand-painted background each (7th pass),
so what does collision actually test against? Answer: **no pixel probe and no separate collision
mask — it's a live bounding-box test against two in-RAM object tables, refined by an optional
per-room "corner cutout" selector.** Static disassembly only this pass (no new `callcap`/`watch`
runs); register/offset roles below are read directly off the code, not guessed.

## 1. Call site and inputs

Called from several places (`$006e78`/`$006e94`, the joystick-driven walk loop; `$006d72`, an
unrelated text/script-advance path that reuses the same routine — see §4) as:

```
D0, D1   = candidate X, Y (bytes, from the mover's position fields)
D2       = candidate Z/height + 1 (byte)
A0       = mover's own object descriptor (52(A5) for the joystick-walk caller)
A1       = the position source / touch-identity object (160(A5) for the walk caller;
           offset +4 on this struct is later used as a per-object "id/sort" word)
(A5)+92  = pointer to a small shared "movement result" record, written by this routine
           and read back by the caller
```

`$006e50`'s loop (`MovementPathFollow_Field2243Bit7Gate`) recomputes D0/D1 by
`sub.w D6,D0` / `sub.w D7,D1` (D6/D7 = the per-direction velocity from
`DirectionVectorTable_16Entries_DxDyPairs`, 11th pass) and calls `$8870` again each step,
`bra $6e78` — i.e. **the obstacle check runs once per simulated sub-step of the walk, not once at
the destination**, so a diagonal or long move is checked incrementally.

## 2. The mover's footprint

```
D3 = D0 - A0.16 + 1     ; trailing-edge X  (A0.16 = mover half-width)
D4 = D1 - A0.18 + 1     ; trailing-edge Y  (A0.18 = mover half-depth)
D5 = D2 + A0.20 - 1     ; leading-edge Z   (A0.20 = mover half-height)
```

So the candidate footprint is the axis-aligned box `[D3..D0] x [D4..D1]` in the XY (floor) plane,
plus a `[D2..D5]` Z-range — sized from the mover's *own* struct, not a fixed constant. This is why
different-sized objects (props are `+50`/`+51` width/height fields too, per `graphics.md`) can share
one collision routine.

## 3. Room-extent test, with an optional non-rectangular refinement

```
if D0 >= RoomMaxX(2238) or D1 >= RoomMaxY(2239)
   or (D4 > RoomMinY(2218) and D3 <= RoomMinX(2217))
   or D3 < FloorClampX(2204) or D4 < FloorClampY(2203):
      goto EdgeOrPortalCheck   ; §5
```

If the footprint is inside these bounds, and a per-room selector pointer at **`(A5)+140`** is
non-null, control jumps (`jmp (A0)`, `A0` loaded from that pointer) into one of four near-identical
inline quadrant tests (globals `2234/2236/2235/2237`, `2230/2232/2231/2233`, `2226/2228/2227/2229`,
`2222/2224/2223/2225` — each a 4-field byte rectangle). Any one of the four quadrant tests failing
also routes to `EdgeOrPortalCheck`. **Reading**: this is how an irregular, hand-painted room shape
(no tile grid, confirmed 7th pass) gets an approximate collision boundary — an outer bounding
rectangle plus up to four optional corner-cutout rectangles, selected per room via `(A5)+140`,
rather than one plain box. If `(A5)+140` is null the room is just the outer rectangle. Which of the
four quadrants corresponds to which physical corner, and what selects the pointer per room, is not
traced this pass (static read of the dispatch shape only).

## 4. Live object-array collision (interior of the room)

Walks the **sprite-object array itself** — `SpriteObjectArrayPtr_A5Plus56` /
`SpriteObjectArrayCount_A5Plus1152` (the exact table `graphics.md` §3 catalogued for CAVERN, 22
entries; TUNNEL has 2), stride `$46` = 70 bytes, matching the struct stride already confirmed for
sprite dimensions. Per entry:

```
obj.bbox = [byte 0, byte 1, byte 2, byte 3]   ; x_min, y_min, x_max, y_max
obj.zbox = [byte 4, byte 5]                    ; z_min, z_max (also doubles as an id/kind pair)
if mover.footprint overlaps obj.bbox (cascaded cmp.b/bge chain, standard AABB test)
   and mover.zrange overlaps obj.zbox:
      record a one-shot "touch" event for (self, obj) via the dedup cache (§4a)
      if obj.byte24 < 0 (top bit set) and a flag on a linked struct (obj.+10 -> +15 bit 2) is set:
          shared_result.byte[1] = $FD    ; "touched an interactive/pickup object"
      else:
          shared_result.byte[1] unset    ; plain scenery block
```

`(A6)` walks the array with `adda.l #$46,A6` / `dbf D7,...`; no match after the full walk falls
through to the "clear" exit, `D0 = -1`.

### 4a. Touch-event dedup cache and queue (`$00e614`)

`$00e614` is **not** a geometry test (despite being fed a packed pair-of-object-ids longword) — it's
a 64-entry ring-buffer *seen-pairs* cache at `(A5)+512`, count at `(A5)+2146`. Given a longword key
(`swap`-packed from the two objects' `+4` id words), it scans the cache; if the pair was already
recorded this returns "seen" (Z set) and the caller skips the push. Otherwise it appends the key,
and once the cache fills (64 entries) flushes it via `$11788`. On a genuinely new pair, the caller
pushes a 3-word command (`opcode $9`, the touching object pointer, its `+4` id word) into the
same VBL-serviced ring queue at `(A5)+304` / count `(A5)+1154` that `TimerQueueService` (`$9006`)
already drains every frame (2nd-pass finding) — **this is almost certainly how one-shot pickup/
interaction scripts get triggered** (e.g. the "SILVER COIN"/"BOAT" inventory adds noted in the
10th/11th passes), by queuing opcode `$9` once per never-before-seen (mover, object) touch. Not yet
confirmed which queue consumer handles opcode `$9` specifically (`TimerQueueService`'s own opcode
table, `2534(A5)`, was named but not decoded — candidate for a future pass).

## 5. Edge/portal check (`$008ac8`, reached when the room-extent test in §3 fails)

Guarded first by a per-mover "kind" check: `D7 = A1.byte(12)`; if the byte read from a small table
at `5(A1, D7.w)` is **not `7`**, the whole portal check is skipped and the routine returns the plain
"no block" result (`D0=-1`) — reading this as "only a mover of kind 7 (almost certainly the player)
can trigger a room transition; anything else that reaches the room edge (a thrown object, say) is
just left alone by this routine," though nothing this pass confirms what a non-player mover
actually does on hitting the edge elsewhere.

For a kind-7 mover, walks a **second**, separate object table — `(A5)+88` base, `(A5)+1162` count,
same 70-byte stride — this is the portal/exit table, distinct from the sprite-object array. Each
entry's bbox (bytes 0-3, same layout as §4) is tested the same way, with one addition: a
direction-dependent diagonal-corner allowance (`btst #0/#1,2243(A5)`, the joystick-latch byte from
the 11th pass) that swaps which two edges are checked depending on the current movement direction —
this is what lets the player graze past a doorpost corner diagonally instead of being blocked square
by the portal's bounding box.

Outcomes:
- **Match**: `D0 = -2`, `D1 = entry.+10` (a pointer — likely the target room's load descriptor),
  and `entry.+26` (a word) is written to `(A5)+1184` (a "pending room target" global, not
  previously named). This is the concrete mechanism the 12th pass's CAVERN→TUNNEL zigzag went
  through — a portal-table entry, not a plain wall tile, at the room-edge notch.
- **No match**: `D0 = $FF`, written to the shared result record's status byte — a hard wall/room
  boundary with no exit here.

The shared result record at `(A5)+92` (byte 0 = `D0`/status, bytes 2-5 = `D1`, bytes 6-9 cleared on
a normal in-array block) is what callers like `$006e78`'s `bmi`/`beq` pair and the `cmpi.b #$fd,1(A4)`
check (item-pickup branch) actually read — the routine's own `D0`/flags return doubles as a
same-frame convenience, the record is the durable result.

## 6. Not chased this pass

- Which of the four §3 quadrant tables maps to which physical room corner, and what selects
  `(A5)+140` per room (a room-init table, presumably — not located).
- `TimerQueueService`'s opcode table (`2534(A5)`) — needed to confirm opcode `$9` is really the
  pickup/interaction trigger and not something else (a sound cue, most likely candidate given the
  queue's other known use).
- Whether the "kind `7`" mover check is really "is the player," or a broader category (e.g. anything
  with a script-driven walk) — would need a `callcap`/`watch` check against a non-player mover, and
  no such mover has been found in either room yet (per the standing "no creature found" item in the
  README).
- `$006d72`'s reuse of `$8870` (a text/dialogue-script-advance context, `D2` accumulated from script
  bytes rather than a Z-height) — the same obstacle-check routine is called there too, meaning it's
  a genuinely general-purpose "does this box fit/touch something" utility, not movement-specific;
  not traced further, flagged only so a future pass doesn't assume `$8870` is walk-only.

## 7. The TUNNEL lever hotspot (13th pass, moved here from the README as the other confirmed
   mechanics finding)

The lever is **not** a discrete entity in either obstacle table above — TUNNEL's sprite-object array
stays at count 2 (player + the ladder/tool prop) the entire time the player stands at the lever, and
no additional portal-table entry was found either. Standing at a specific spot (reached only via a
held-Left approach from the room-entry snapshot) sets the status-bar name field to "LEVER" and
switches the icon panel to a lever-specific icon pair — this is a **separate, coordinate-only
proximity hotspot** (a name/icon lookup keyed on the player's screen position, evaluated regardless
of the object-table collision system above), the same class of mechanism as CAVERN's "BOAT" name
hotspot at the boat prop (11th pass). No input tried against it (13th pass: keyboard interact,
joystick fire tap/hold/combined-with-direction, Space) opens the door behind it; fire does drive
real writes to the player descriptor through unnamed code `$00afb2`→`$00db4a`→`$00db54`→`$00db58`→
`$00db5e`→`$00db68`, confirmed by `watch` but not yet disassembled — the concrete next step for this
half of the spike, not chased further this pass (see the README's own scope note for the 14th pass).

## 8. Bounded look at the lever's fire-driven write chain (timeboxed, not fully traced)

Per the 14th pass's own scope note, one bounded look at `$00afb2`→`$00db4a`→`$00db54`→`$00db58`→
`$00db5e`→`$00db68` (the 13th pass's fire-tap `watch` hits on the player descriptor), not chased to
a conclusion:

- **`$00afb2`** is inside a loop with a **70-byte (`$46`) stride** — the same stride as the
  sprite-object array and the action-slot control blocks — clearing each entry's `field+14` and
  writing `D0` to `field+38`, then calling an undisassembled `$00b1a2` per entry, `dbf`-looping over
  `D7+1` entries. Reads as a per-object reset/rescan triggered once when fire is pressed, most
  plausibly "find the nearest interactable object" (matching the observed highlight-flash), not a
  door-specific action.
- **`$00db4a`-`$00db78`** packages four values (`D1/D2/D3/D5/D6` in, matching a "screen position +
  type" shape) into an entity's own `field+18/20/21/23/46`. A separate routine at `$00db8a` reads
  those same fields back out **only when `field+42 == 5`** (the confirmed "static prop" state byte
  from `graphics.md` §3) and pushes the entity pointer onto a queue at `(A5)+344`, then calls an
  undisassembled `$00ddb6`.
- **Net reading, unconfirmed**: fire press → rescan nearby objects (`$afb2`'s loop) → for a static
  prop in reach, package its position/type (`$db4a`) → if still a static prop (`$db8a`'s gate), queue
  it for further processing (`$ddb6`). This looks like a generic "select the nearby interactable
  object" pipeline, not a lever-specific or door-specific one — consistent with the 13th pass's
  observation that fire's visible effect (an icon highlight) reproduces at the boat and other props
  too, not just the lever. **Not settled**: what `$b1a2`/`$ddb6` actually do, and therefore whether
  this pipeline is capable of opening a door at all or is purely cosmetic (the highlight/selection
  UI). Left here rather than continued, per this pass's own scope boundary — a full trace of
  `$b1a2`/`$ddb6` is the concrete next step if the lever is picked up again, in preference to more
  `kbd`/`mouse` input guessing.

## 9. The real room-transition executor, found via embedded debug strings (`$7104`-`$7364`)

A late addition this pass, found efficiently rather than by more disassembly: the game binary has an
embedded **debug string table right after the opcode-`$89` secondary table** (`$1729d`+42 ≈
`$1729d`+`$2a`, i.e. `$172c7` onward) — developer error messages, presumably compiled in and never
shown to the player normally: `"EVENT STACK NOT CLEARED A"`, `"DOOR ERROR"`, `"BOTH ROOMS BLOCKED"`,
`"EVENT STACK NOT CLEARED B"`, `"SHOULDNT OF PUT IN RUCK"`, `"UNKNOWN ANI OBJECT"`, `"ANI PIC HAS
GONE ODD"`, `"LOAD LEVEL ERR"`, `"CANT SAVE GAME"`, `"SEVEN OR OVER ICONS"` (an inventory-icon-count
limit of 7, matching `$1616c`'s dispatch-table icon-panel context), `"LIMB CODE NOT WRITTEN"`
(twice), `"TRYING TO ADD AN OBJECT THAT DOSNT EXIST"`, `"ROOM DELETE AN OBJECT THAT DOSNT EXIST"`,
`"NO OBJECTS IN ROOM ERR"`, `"DEL_OBJ_IN_ROOM ... REDUCE ENTRY SIZE ERR"`, more cut off at the end
of this pass's read. A raw-byte scan of RAM for the absolute addresses of `"DOOR ERROR"` (`$172e2`)
and `"BOTH ROOMS BLOCKED"` (`$172ee`) as 4-byte operands finds exactly one code reference each —
**`$007264`** and **`$0072f6`** — landing squarely inside a previously untouched routine,
`$007104`-`$007364`, which is **the actual room-transition executor** triggered by a portal-table
match (§5's `D0=-2` return from `$008870`/`$8ac8`):

```
A0 = the door/portal descriptor (the §5 portal table entry's own +10 pointer)
D3 = word at A0+2                      ; target room id
if D3 == 0: skip to $71ca (no transition, just an in-room door flag toggle)
if D3 == -1: goto $731e (a different, "same-room secondary exit" path, not traced further)
else:
    jsr $11256                          ; resolve the target room's own record from D3 (room id -> descriptor)
    if that lookup fails (beq): goto $734a (abort, no message - this isn't the "DOOR ERROR" case)
    ... compute the player's new position in the destination room from the door descriptor's own
        fields (byte 0/1 = entry x/y, byte 2 = flags, byte 5 = entry-facing, copied to 2275(A5)) ...
    D0,D1 = candidate entry position; jsr $de5e (undisassembled - "can the player actually enter
             the target room's entry point" check, by its position in the flow)
    if D7 < 0 (jsr $de5e's result): print "DOOR ERROR" ($172e2) via $11788 (the same debug-string
             printer $e614's touch-event flush and the sound-register-table flush both use)
    ... else continue: jsr $e84a (undisassembled - a second gate, using the target room id in D4)
    if that result is negative: print "BOTH ROOMS BLOCKED" ($172ee), same printer
    ... else: if a derived flag byte is still non-negative, the room switch is treated as already
        resident and the routine just updates state and returns to the main loop ($69da) - this is
        almost certainly the path the 12th pass's CAVERN->TUNNEL transition took, since both rooms'
        data were already loaded from the one-disk image at boot
    else: sets 2142(A5) = 2 and calls bsr $defa (undisassembled - the actual "load a new room" call,
        by elimination the one path not yet exercised by anything seen so far in this spike)
```

**Why this matters for the lever**: the "no tested input opens the door" finding (13th pass) and the
"fire only drives a generic prop-selection pipeline, not a door-specific one" finding (§8 above) are
both about the *approach* to the door. This routine is the actual *execution* of a door once its
portal-table entry is matched by `$008870`/`$8ac8` — meaning the concrete open question is no longer
"what input opens the door" but **"does the lever's door even have a matching portal-table entry at
all, and if so, does `$de5e`/`$e84a` accept it"**. Three concrete, disassembly-only next steps, none
requiring more input-guessing:
1. Dump the TUNNEL room's own portal table (`(A5)+88`/`(A5)+1162`, §5) and check whether an entry
   exists near the lever's screen position at all — if not, the lever's door genuinely isn't a
   `$008870`-reachable portal yet (it may need the lever to be "pulled" first, flipping a flag this
   routine or `$de5e` checks, rather than being walkable-through already).
2. Disassemble `$de5e` and `$e84a` — likely short, gate-only routines given their position in the
   flow (a "can enter" check and a "not blocked from the other side" check respectively).
3. Disassemble `$defa` (the actual room-load path) to see what it needs (sector numbers? a resident
   level-data check?) - if the lever's target room's data simply isn't loaded from this one-disk
   image the way CAVERN/TUNNEL's shared data was, that alone would explain a silent no-op with no
   input ever "working."

## 10. TUNNEL's live portal table, decoded (15th pass) — the lever's door has no live entry at all

Full linear disassembly of `$008ac8`-`$008b98` (the portal-check body §5 only summarized) plus
`$007104`-`$00734e` (the room-transition executor §9 left partly as pseudocode) against
`room2_lever_boundary.snap`. Static only, cross-checked by dereferencing every pointer directly out
of the snapshot's own RAM (`tools/disassemble.py --snap ... --linear`, no live stepping needed).

### 10a. §5's bbox description was an oversimplification — it's a threshold/edge test, not AABB containment

`$8ac8`'s actual comparison chain (`$8afa`-`$8b78`) does **not** test `x_min <= x <= x_max` the way
§4's sprite-collision AABB does, despite reading the same four bytes. It's a two-branch
threshold test: `(D0 >= byte0) OR (D0 >= byte2)` selects between two different downstream edge
checks (`$8b08` vs `$8b0e`), and a whole second block (`$8b3a`-`$8b7c`) — the direction-dependent
"diagonal corner allowance" already named in §5 — swaps which pair of edges gets checked based on
`btst #0/#1,2243(A5)` (the joystick-latch bits). Net effect: byte0/byte2 (and byte1/byte3) are a
**pair of independent threshold lines** the mover's footprint must straddle in the right direction,
not a min/max pair — so `byte0 > byte2` (seen live below) is not a sign of a broken/degenerate entry,
it's normal for this test shape.

### 10b. TUNNEL's portal table has exactly 2 entries, both dumped in full

`(A5)+88` = `$00037e48`, `(A5)+1162` = `2`, stride `$46` (confirmed matching §4/§5's stride):

```
entry 0 @ $037e48: bbox=[1b 2d 04 28] z/id=[2f 00] +10ptr=$06d4ea +26word=$0032
entry 1 @ $037e8e: bbox=[1b 05 04 00] z/id=[2f 00] +10ptr=$06d4f2 +26word=$0033
```

Both pass the leading `tst.l (A6); bmi ...` liveness check (neither is a deleted/negative-flagged
entry) — both are real, active portal entries. Room-extent globals in this same snapshot:
`RoomMaxX=$18(24) RoomMinX=$02(2) RoomMaxY=$28(40) RoomMinY=$0a(10)`. Entry 0's Y-threshold pair
(`$2d`=45, `$28`=40) sits right at `RoomMaxY`; entry 1's Y-threshold pair (`$05`=5, `$00`=0) sits
below `RoomMinY` — i.e. **the two entries sit at opposite (north/south) edges of the room**, not
stacked on top of each other.

### 10c. Dereferencing both entries' door descriptors settles it: neither is an unopened door to a new room

Each entry's `+10` pointer is itself a door-descriptor struct (README §9's `A0`); its word at offset
`+2` is the target-room id `$007104` branches on:

```
$06d4ea (entry 0's descriptor): word@+2 = $0000   -> D3==0  -> falls into $71ca
$06d4f2 (entry 1's descriptor): word@+2 = $ffff   -> D3==-1 -> goto  $731e
```

Both hit the two special-cased branches at `$7178`-`$7182` that **skip the room-resolve/`$de5e`/
`$e84a`/`$defa` chain entirely** — neither descriptor carries a real positive room id, so the
"else" branch (`jsr $11256` room lookup, README §9's full chain) is dead code for both of TUNNEL's
current portals. Traced each special case to the end:

- **`$731e` (entry 1, D3=-1)**: `btst #6,7(A0)`-gated push of a 3-word command
  (`opcode $30`, payload `$8`) onto the same VBL-serviced ring queue at `(A5)+304` that
  `TouchPairDedupCache_AndEnqueueTouch` (§4a) and `TimerQueueService` already use — then
  `addq.b #8,2494(A5)` and, if that doesn't overflow a counter, one more queued opcode (`$3c`) via
  `$158f8`. **No geometry/room-load call anywhere in this path** — it's a self-contained sound/event
  cue (matches the queue's other known use, §4a), unrelated to doors or rooms.
- **`$71ca` (entry 0, D3=0)**: **does** run the full chain — computes a candidate entry position
  from the door descriptor's own bytes 0/1 (matching README §9's read), then `jsr $de5e`
  (`FindNearestFreeEntryTile_DoorErrorGate`, disassembled: not a boolean test but a scan loop that
  walks outward from the candidate tile against a 4-rectangle bound in `A0`'s own struct,
  incrementing `D1` each miss — "find the nearest free tile to enter at," printing `"DOOR ERROR"`
  only if it never finds one, `D7 < 0`), then `jsr $e854` (`QueueEntityIntoRing304_AndSetField2271_
  Direct` — pushes another ring-304 command, opcode `$401c`, and sets `2271(A5)`), then
  conditionally `jsr $e84a` (**not a separate gate** — it's a 2-instruction wrapper,
  `move.b #$ff,2271(A5); bra $e854`, i.e. the "BOTH ROOMS BLOCKED" call is the *same* routine as the
  first call, just entered with `2271(A5)` forced to `$ff` first), and only then, gated on a byte
  arithmetic check (`addi.b #$2,D4; bpl $69da`), `bsr $defa`.
- **`$defa` itself is not the sector-level loader** — it's another 12-instruction ring-304 queue
  push (opcode `$8`, payload `2142(A5)`). The real "read this room's data off disk" work, if any, is
  deferred to whatever consumes queue opcode `$8` (the same not-yet-decoded `TimerQueueService`
  opcode table at `2534(A5)` flagged as open in §4a) — **not found or confirmed this pass**. A
  separate, unreached-from-`$defa` routine at `$00df46`-`$00df9c` builds a padded `".  "`-style
  8.3 filename and calls into `$e038`/`$1160e`/`$11742` — a plausible disk-filename-lookup routine,
  but nothing in this pass's trace connects it to the opcode-`$8` dispatch, so it's flagged, not
  claimed.

### 10d. Conclusion for the lever

TUNNEL's portal table, as populated in this snapshot, has **exactly one entry capable of a real
transition outcome at all** (entry 0 — its geometry at the room's south/`RoomMaxY` edge matches the
already-proven-working CAVERN exit from the 12th pass), and **one entry that is not a door at all**
(entry 1 — a sound/event cue with no room-transition semantics, sitting at the room's north edge).
**Neither entry represents an unopened door to a new room** — this settles the open question from
§9/the README's next-step 10 with a real negative, not an inconclusive one: the lever's door is not
`$008870`-reachable in this game state, full stop, because there is no third portal-table entry and
no room id anywhere in the two that exist. This is not evidence the target room's data is missing
from the one-disk image (nothing here tests disk residency) — it's evidence the **portal table
itself hasn't been populated with that door yet**, consistent with the pass's own standing
hypothesis that pulling the lever must flip a flag (most plausibly rewriting entry 1's descriptor
word`+2` from `$ffff` to a real room id, or appending a 3rd entry to the table / bumping
`(A5)+1162`) before this mechanism can ever fire. Driving the lever via a `$007104` callcap (as
previously proposed) would not help — there's still no portal entry to match regardless of how
`$007104` itself is invoked. The concrete next lead is the *other* still-untraced half of this spike:
`$00b1a2`/`$00ddb6` (the fire-chain tail from §8) — the standing candidate for whatever *writes* a
new portal-table entry or door-descriptor field, not the transition executor itself.

## 11. `$00b1a2`/`$00ddb6` disassembled (15th pass, cont.) — the fire chain is a dead end too, confirmed both statically and live

- **`$00b1a2`** is a generic 10-instruction helper: `btst #0,D0` (an even-alignment check on
  whatever's passed in `D0` — an animation-frame pointer, per §8's read of its caller's loop) and,
  if odd, prints the debug string at `$17348`, **`"ANI PIC HAS GONE ODD"`** — a sanity assert on a
  sprite-frame offset's alignment, called once per rescanned object from `$00afb2`'s loop. Nothing
  room/door/portal related.
- **`$00ddb6`** walks a linked list of candidate structs (terminated by a negative long at `+10`),
  testing each one's stored rectangle (`+0/+1/+4/+6`) against the incoming `D0-D3` position args and
  appending any overlap hit to an output list at `A2` (tagging the high bit of the stored pointer as
  a "matched" flag). This is a generic spatial-overlap/selection-list builder for whatever candidate
  set the caller (`$00db8a`'s queue at `(A5)+344`) feeds it — the same "select nearby interactable
  objects" shape §8 already inferred, now confirmed structurally. **No write anywhere in either
  routine touches the portal table, a door descriptor, or any of the room-extent/transition globals**
  (`(A5)+88`, `(A5)+1162`, `(A5)+1184`, or any `$037exx` address).
- **Confirmed live, not just by absence of code**: from `room2_lever_boundary.snap`, `watch`ed
  `(A5)+88` (4 bytes), `(A5)+1162` (2 bytes), and the full portal table `$037e48`-`$037ed3` (140
  bytes) across fire-tap, fire-release, the known interact gesture (`kbd 50`/`kbd d0`), fire+Left
  combined (`kbd ff 84`), and another release — zero watch hits fired, and a `m 37e48 140` dump
  before and after the whole sequence (~1.5M steps) is byte-for-byte identical. **The fire pipeline
  genuinely never touches the portal table under any input combination tried across the 13th and
  15th passes.**
- **New lead worth flagging, not chased this pass**: the 13th pass's own screenshot description of
  the lever's icon panel — "a bracket/hook icon + a **key** icon" — was read at the time as generic
  per-object UI (matching CAVERN's boat), but in hindsight a key icon is a plausible hint this needs
  an **inventory item used on the object** (a mouse-driven icon-click action) rather than a
  keyboard/joystick "pull" gesture at all. That whole input class is effectively untested: the 8th
  pass showed the game's IKBD ISR misinterprets raw mouse-motion packets as spurious keystrokes
  rather than parsing them properly, and no pass has tried clicking a specific inventory/UI icon
  slot (as opposed to clicking in the room). Concrete next step if the lever is picked up again.

## 12. The icon-panel and mouse leads, closed (16th pass) — no UI-driven icon selection exists, and buttons-as-keys is never enabled anywhere in this playthrough

Following up the 15th pass's own two leads (§11): traced `$00bf72`'s actual caller graph and the data
feeding its icon-index argument, and separately settled whether mouse buttons can ever report as
keys during this playthrough. Both come up empty, disassembly- and trace-grounded, not more
input-guessing.

### 12a. `$00bef0`/`$00bf72` has exactly two callers in the whole loaded image, neither driven by player input

`disassemble.py --callers` only scans the TOS ROM (a standing tool gap - it can't see JSR/JMP
abs.long targets inside the loaded game image), so callers were found instead by brute-force
scanning `room2_lever_boundary.snap`'s RAM for every BSR opcode (`$61xx`/`$6100`) whose displacement
resolves to `$bef0` - the only reachable form, since a whole-RAM scan for both abs-long JSR/JMP
references and raw 4-byte pointer literals to `$bef0`/`$bf72`/`$bfb0` came back with zero hits.
Exactly two BSR sites exist:

- **`$00af6a`** (`FireRescanLoop_OverSpriteObjectArray_CallsB1a2AndPanelIcon`), inside the per-object
  rescan loop from §8 (walking `SpriteObjectArrayPtr_A5Plus56`/`SpriteObjectArrayCount_A5Plus1152`,
  the same loop `$00afb2`/`AssertAnimFramePtrEven...` lives in). Gated on the candidate object's
  linked-struct byte `+12` bit 5 being set, then further gated on that same struct's byte `+22 == $6`
  - **if bit 5 is set but the type byte isn't `6`, the routine takes the "else" branch and prints the
  debug string `"UNKNOWN ANI OBJECT"`** (`$17334`, via the same `$11788` printer as "DOOR ERROR"),
  confirming type `6` is the one valid "has a panel icon" kind. Only in the type-`6` case does it call
  `$00bef0`, with `D0` = the byte at **`(A5)+2455`**.
- **`$00cea8`**, inside an unrelated per-object *construction* loop (`$00cd82`-`$00cee0`, a distinct
  70-byte-stride table walk, not traced beyond this). Same bit-5 gate on struct byte `+12`, but here
  `D0` is **hardcoded to `0`** (`moveq #0,D0`) - no per-object index at all.

Neither call site reads a keyboard scancode, a mouse packet, or any UI-selection index. The only
variable input across both sites is `(A5)+2455`.

### 12b. `(A5)+2455` is written exactly once, by the movement-animation script interpreter, not by any input handler

A full-image scan for every instruction touching displacement `2455(A5)` (`Disassembler.decode_one`
swept across every even address of the snapshot's RAM, filtered on operand text) finds exactly two
hits: the `$00af66` read above, and a single writer at **`$0007590`**
(`MovementAnimByteStream_ReadLiteralOrEscape_Writes2455`: literal bytes `<$80` pass straight through
to `D0`; `$ff` and `$fc` are two-byte escape opcodes for a "rewind" and a "queue a sound via
`$158f8`" case respectively, ending `$0075d8: move.b D0,2455(A5)`), reading from a script pointer at
`(A5)+376`. That pointer is set a few instructions earlier, at **`$007480`-`$007536`**
(`MovementAnimScript_SelectPtrByDirState_Writes376`), by a dispatcher keyed on the player's current
move/turn state (`2266(A5)`) and direction fields (`2268/2273/2274/2280(A5)`, the same field family as
`DirectionVectorTable_Lookup_ByField2273`) - it selects one of six small tables (`$5c46`, `$5c79`,
`$5cac`, `$5cc3`, `$5ce6`, `$5d09`, all sitting just after `DirectionVectorTable_16Entries_DxDyPairs`
at `$5bea`) as the byte-stream source. **Reading**: `(A5)+2455` is the player's own current
movement/turn animation-frame byte, refreshed by this per-direction script interpreter every time the
player's move state changes - `$00bf72`'s icon-panel draw at `$00af6a` is reusing that same byte as
its icon index, not reading any UI-selection state. There is no keyboard cycle-icon mechanism
anywhere in this call graph.

### 12c. Mouse buttons-as-keys: confirmed still off at the lever, and never turned on anywhere in the boot-to-gameplay path

Two independent checks, both negative:

- **Live, at the exact resume point**: `resume room2_lever_boundary.snap repl` + `mouse down l`
  reports `buttons-as-keys=false` - the same false the 8th pass found in `gameplay_empire.snap`, now
  confirmed at the lever itself, in a snapshot reached by real prior-pass play (not a synthetic
  state).
- **Static, the whole boot path**: a fresh cold boot (`dotnet exec ... 15000000 --disk-a
  "...[cr Empire][one disk].st"` with `ATARI_TRACE_IKBD=1`) logs **exactly three IKBD commands for
  the entire boot-to-gameplay window**: `$80 $01` (reset), `$12` (mouse disabled), `$1A` (joystick
  auto-report disabled) - `$07` (the command that sets the buttons-as-keys bit) is never sent. The
  game explicitly disables the IKBD mouse subsystem at boot and never re-enables buttons-as-keys mode
  before gameplay starts; combined with the live check above, it also never turns it on anywhere in
  the play session that reached the lever. Mouse clicks are conclusively dead for the lever's door in
  this game state, not just untested.

### 12d. Conclusion: the icon-panel lead is closed, both proposed leads are exhausted

Both of the 15th pass's own leads (bracket/key icon = a UI-selection mechanism; mouse click = an
untested input class) are now dead ends grounded in disassembly and a live trace, not another round
of input-guessing. Combined with §§7-11's earlier findings (portal table has no entry, fire chain
never writes the portal table, keyboard/joystick/interact are exhausted), **every
currently-identifiable input path to the lever's door is closed**. This is where the README's own
next-steps hand off to item 7 (find a creature/monster in either room) rather than continuing to
chase the door.

## 13. CAVERN's own portal table, dumped for the first time (17th pass) — a second real door found and live-triggered, but resolves to "already resident" with no visible room change

Following the README's own next-steps item 7 (find a creature), this pass checked its two open
resume points and found both already closed by extension of existing findings, then found and
tested a genuinely new door while mapping a route around them.

- **TUNNEL's edges**: no new live testing needed. §10b's static dump already enumerated TUNNEL's
  *entire* live portal table (exactly 2 entries, both accounted for), and §11 already confirmed live
  that nothing in the fire/interact pipeline ever writes to that table. There is no third TUNNEL edge
  to find — this was already a closed question, not an open resume point.
- **The boat boundary**: also already exhausted. Down (11th pass), fire alone and fire+Left (13th
  pass, explicitly "reproduces at the boat and other props too, not just the lever"), and the whole
  icon-panel/mouse-buttons-as-keys system (16th pass, §12, which closed those mechanisms *in general*,
  not per-object) all cover the boat as much as the lever. Nothing new to try there without a genuinely
  new verb, which this pass didn't find.

**CAVERN's own portal table, however, had never actually been dumped** (only inferred by walking) —
done this pass the same way §10b did for TUNNEL, from `movement_at_boat_boundary.snap` (A5=$18152
confirmed live via `r`, fixed for the whole session): `PortalTablePtr_A5Plus88` ($181aa) = `$00037e48`
— the *same* buffer address TUNNEL's table lives at (portal-table entries get reloaded into one
reused buffer per room-load, not duplicated in separate per-room memory) — and
`PortalTableCount_A5Plus1162` ($185dc) = `2`. Entry 0's door descriptor is `$0006d4ea`, the exact same
address as TUNNEL's own entry 0 — confirmation this is one shared descriptor for the single physical
CAVERN↔TUNNEL door, referenced from both rooms' tables rather than copied. **Entry 1's descriptor,
`$0006d532`, is new** — distinct from either of TUNNEL's two known descriptors. Its word at `+2` is
`$0049` (73 decimal): a real, positive, non-special target room id, unlike every descriptor seen
before (`0` = "the current room", `-1` = "no room, a sound/event cue"). Its bbox threshold pair
(`byte0`/`byte2` = `0x55`/`0x50`) puts this door's X-line right at CAVERN's own `RoomMaxX` — dumped
fresh this pass (`RoomMaxX_A5Plus2238`=$18a10=`80`, alongside `RoomMinX`/`RoomMinY`/`FloorClampX`/
`FloorClampY`) — i.e. **CAVERN has a second, real, previously-undiscovered door on its east wall.**

Reached it live: a one-off Python parse of `m 38338 1540` (all 22 sprite-object-array bboxes) showed
the 11th pass's "held Right to its boundary" had stopped at the chest (`slot20`, x 50-54) — well short
of the real wall at x=80 — and found a clear lane around y≈12-18 threading between the mat prop
(y 6-10) and the flower/torch cluster (y 17-23 and up). Walked it from `gameplay_empire.snap` with
`kbd ff 01/02/08` nudges (up, then small corrections around two more prop blocks the same way): 
`PendingRoomTargetWord_A5Plus1184` ($185f2) flipped from its idle sentinel `$ffff` to `$003b` —
exactly entry 1's own `+26` word. **This is the first time in the whole spike a portal match has
fired for anything other than TUNNEL's two already-known special cases.**

The transition stalled there, though. Register/flag evidence (not a full disassembly of the load
path) points at why: `RoomLoadQueuedFlag_A5Plus2142` ($189b0 — README §9's "sets 2142(A5)=2" marker
for the one real "go load a new room" call) stayed `$00` through 6.5M further steps, and
`DoorFacingOrBlockedFlag_A5Plus2271` ($18a31) read `$01` — neither the real-load marker nor the `$ff`
"BOTH ROOMS BLOCKED" sentinel. That combination matches exactly one branch of §9/§10c's own
flowchart: `$de5e`'s entry-tile search succeeded (no "DOOR ERROR"), `$e854` ran and set its own value
into `2271(A5)`, and the `addi.b #$2,D4; bpl $69da` check took the **"already resident" branch** —
the same one the CAVERN↔TUNNEL door takes on every ordinary crossing — which just updates state and
returns to the main loop without ever calling `$defa` (the actual new-room loader). Player bbox,
`PortalTablePtr_A5Plus88`'s value, and `RoomMaxX`/`RoomMinX` all stayed byte-identical across the
whole 6.5M-step window past the match — the behavioral signature of "already resident," not a stalled
or blocked load.

A brief look at `$011256` (`RoomIdLookup_ByD2_LinearScan`, the `jsr`'d room-id resolver — 20-odd
instructions, not the full room-load path, and not chased into its own `bsr $c628`/`$c52c` helpers)
shows a linear scan that returns `D0=0` on a miss or a resolved pointer on a hit, keyed on `D2` (not
`D3`, correcting §9's shorthand — the caller must load the target id into `D2` for this routine even
though `D3` is what the caller-level pseudocode names it). A miss reads as the more likely candidate
for a genuine "DOOR ERROR"-style abort, which didn't happen here — consistent with, but not proof of,
**id `$49` resolving straight back to CAVERN's own already-loaded descriptor**, i.e. this second door
being a same-room wraparound/decorative edge rather than a link to an unexplored room.

**17th-pass conclusion, RETRACTED same pass — this was wrong, and wrong in an instructive way.**
The line originally here claimed the connectivity graph was fully known and the search for a
creature was closed. External ground truth (the game's own published walkthrough, plus the user's
own prior playthrough of this *exact* one-disk Empire file) directly contradicts that: pulling
TUNNEL's lever really does open a door to a room 3, which has a "spiky floater" enemy (killed with
a thrown bag of stones), and later rooms have maggots and worse. Two things were wrong with the
reasoning above, not just the conclusion:

1. **The scope was too narrow.** "Both rooms' portal tables are fully enumerated" only proves there's
   no *third room reachable through the two portal tables in their current, pre-lever state* — it
   says nothing about whether the lever *changes* TUNNEL's table (the `$10d`-flagged hypothesis this
   pass never actually tested, having gotten distracted by CAVERN's own second door instead) or about
   whether room 3's data is sitting in RAM already, reachable some other way than these two tables.
2. **A fresh `gfxview.py --contact` scan of `room2_lever_boundary.snap`** (prompted by a direct
   question about whether tile/sprite data for other rooms is even resident) turned up **9 distinct
   palette tables** (`$5a94`, `$12180`, `$12278`, `$122c4`, `$4d21c`, `$4d23c`, `$5751e`, `$5f884`,
   `$61a90` — up from the 2 this spike had accounted for) and confirmed the **104KB span
   `$51000`-`$6b000`** this pass's own CAVERN-prop lookups only ever sampled 2-3 pointers out of.
   CAVERN's ~20 static props don't need 9 palettes or 104KB. That is real, concrete evidence more
   rooms' assets are already loaded in this exact snapshot — consistent with the README's own
   "self-contained one-disk crack, no swap needed" framing (Milestones section) — not evidence of a
   closed 2-room map.

**Corrected next step, round 1**: find the master room/resource table that `$011256`
(`RoomIdLookup_ByD2_LinearScan`) and its `$c628`/`$c52c` helpers walk. Chased further this same pass
— see §14, which both confirms the mechanism and rules it out as currently populated.

## 14. Chasing the master resource table and the lever's real trigger — both dead-ended, cleanly, same
    pass as the retraction above. Concrete new ground truth either way; still no lever solution.

**The resource-table mechanism, fully traced, confirmed empty.** `(A5)+96` (`$181b2`) is a pointer to
a master resource-type-descriptor array: 18-byte rows, indexed by a small integer (`$011256` uses
type `8` for rooms), each row `{+0: index-table ptr, +4: data-base ptr, +8..+15: unknown (8 bytes),
+16: count (word)}` (`$c52c`'s own body — `mulu #$12,D0` confirms the 18-byte stride). Type 8's row:
index-table `$4c536`, data-base `$7550a`, **count `64`**. `$c628` does a linear scan of the index
table starting at the caller's index, testing each 4-byte slot's first word for non-zero (0 = empty,
skip forward) — a sparse, appendable slot table, not a direct array. **Dumped all 256 bytes of the
index table: every slot is `$0000`.** `callcap 11256` with `D2` set to the target id `$49`, to
CAVERN's own record's leading word (`$660c`), and to `0` **all three return `D0=0` (miss)** — the
type-8 table has never had anything registered into it in this whole playthrough, not even the
currently-resident rooms. Reading: CAVERN and TUNNEL were linked directly at boot (hardcoded, not
through this generic resource system), and whatever *would* populate a new slot here — presumably a
"register this room" call made when a room is freshly loaded from disk — has never run. This is
strong, if indirect, support for "room `$49`'s data plus its registration genuinely hasn't happened
yet" over "already resident, self-loop" from earlier this section; either way, `$011256` failing
silently (landing at `$734a`, which — verified this pass — is a **quiet abort with no distinguishing
signal from a genuine miss**, since `$734a` and a real hit both fall through the same cleanup path)
means the CAVERN-east-door investigation cannot be pushed further without first finding what actually
registers a room, which nothing in the traced boot/play path does yet.

**The room-record format, fully decoded from two known-good examples.** `(A5)+164` (`$181f6`) points
to the *current* room's own record — confirmed by finding it holds `$0006bf0a` in CAVERN
(`gameplay_empire.snap`) and `$0006bf84` in TUNNEL (`room2_lever_boundary.snap`), 122 bytes apart, both
inside the low-entropy `$6b800`-`$6d800` span `gfxview` flagged. Format (bytes, 0-indexed from record
start), cross-checked against live globals: `+0..+5` unknown per-room fields (differ per room, not yet
interpreted); `+6..+19`: **7 door-link slots, 2 bytes each** (`$ffff` = unused) — CAVERN's are
`[$0032, $003b, ×5 unused]`, TUNNEL's are `[$0032, $0033, ×5 unused]` — `$0032` is the *same* value in
both, confirming it's the shared CAVERN↔TUNNEL door, and each room's own values match its live portal
table's `+26` word exactly (this is the source data the live table gets initialized from at room-load,
via the `$cb00`-ish loop in the room-init routine, 8 iterations reading 2-byte slots from a stream);
`+20`/`+21`: `FloorClampY`/`FloorClampX` — `06`/`06` for both rooms here, matching the live globals
exactly in both cases. The small door-link values (`$32`,`$33`,`$3b`, and more seen scattered through
other rooms' records in a wider dump — `$34`,`$35`,`$36`,`$3a`,`$3c`…) read as a **global, sequential
door-id namespace** across every room in the game, separate from the door-descriptor pool
(`$6d4ea`/`$6d4f2`/`$6d532`, ...) that a live table's `+10` pointer resolves to.

**The "descriptor gets rewritten in place" hypothesis (`mechanics.md` §10d's own standing guess) —
directly tested and refuted.** Dumped TUNNEL's own two door descriptors (`$6d4ea`, `$6d4f2` — note
`$6d4f2`'s target word is still `$ffff`, the "sound cue" sentinel) before and after: the known interact
gesture (Down/Return), joystick fire alone, and — this pass, going further than any before — **the
full 12-action-id + all-direction + fire-combo sweep already run against the live table, rerun instead
checking the descriptors' own 20-byte content directly.** Zero bytes differ, in any of the 18+
conditions tested. This closes the specific "lever pulls rewrite $6d4f2's target word" idea cleanly —
not just "the live table copy doesn't reflect it" (which was the actual gap in the 17th pass's
original sweep — the live table only holds a *pointer* to the descriptor, so a rewrite-in-place would
never have shown up there; this round checked the real target and still found nothing).

**One genuinely new, unexplained data point**: the player's bbox at `room2_lever_boundary.snap` is
`[8-14, 6-12]` (x, y); TUNNEL's one non-player sprite-array entry (`state=5`, previously guessed a
"ladder/tool prop") sits at `[5-7, 12-15]` — off by exactly 1 unit in x, touching at the y=12 boundary.
This is far closer than coincidental and is almost certainly the lever's own physical hitbox (or
immediately adjacent to it). **Holding Left for 100k more steps from here produces zero position
change** — the object's collision blocks any closer approach, meaning a true AABB overlap (the
precondition for `mechanics.md` §4's "touched an interactive/pickup object" `$FD` outcome) can never
be reached through ordinary movement, and may already have fired once, on whatever approach originally
reached this snapshot (13th pass) — the touch-dedup cache (§4a) would suppress a repeat regardless.

**`TimerQueueService` (`$9006`), disassembled in full this pass — a dead end for finding the trigger,
not a lead.** It's the *producer* onto the `(A5)+304` ring queue (pushes opcodes `$400e`/`$4014`
itself) and drives a small internal countdown-timer/callback table (`2534(A5)`, up to 16 slots) — not
a consumer of arbitrary game-logic opcodes. This means the `mechanics.md` §4a speculation ("opcode `$9`
… is almost certainly how one-shot pickup/interaction scripts get triggered") was very likely wrong:
the weight of evidence (this routine's own producer role, plus §10c's independent, later read of
opcodes `$30`/`$3c` on the *same* queue as a plain sound cue) points to the whole `(A5)+304` ring being
the **sound/music command buffer**, not a script-trigger mechanism. Retracting that speculation here
rather than leaving it standing.

**Where this leaves the lever**: every keyboard/joystick/fire/mouse input this spike can generate has
now been tried against both the live portal table *and* the underlying descriptors, with no effect.
The resource-table "room registration" system is real but unpopulated, and finding what populates it
(not yet located) is the most promising remaining thread — it would explain both the lever and the
CAVERN east-door in one mechanism. Concrete next steps, in priority order:
1. Find what **writes into the type-8 index table** (`$4c536` onward) — a static scan for
   `move.w`/`move.l` instructions targeting that address range (the same technique that cracked
   `$568e` and `88(A5)` this pass) would show the actual "register a room" call, if one exists in the
   currently-loaded code at all.
2. Failing that, reconsider whether "pulling the lever" is gated on an **inventory precondition**
   (the walkthrough's room-1 text lists coin/diary/pick collected *before* the lever, though it never
   explicitly ties the pick to it) — check live whether the axe/pick prop (`graphics.md`'s CAVERN
   slot 4) has actually been picked up in any existing snapshot, and if not, get it and retry the full
   action sweep at the lever with it "held."
3. Re-examine whether `room2_lever_boundary.snap`'s exact position is even the *narrowest* trigger
   tile, not just close enough for the naming hotspot — a finer (sub-approach-direction) position
   sweep hasn't been tried, only the one position reached via the 13th pass's original held-Left
   approach.

## 15. The type-8 index table's only writer, found (18th pass) — it's the save-game restore
    deserializer, not a live "register a newly discovered room" call, and it has never run in
    this spike's boot path

Following up §14's own priority-1 next step ("find what writes into the empty resource table"),
per explicit user redirection away from more input-guessing and toward the same whole-image
`Disassembler.decode_one` sweep technique that cracked `$568e`/`88(A5)`/etc. Static disassembly
only — no new `callcap`/`watch` runs.

### 15a. The literal-address sweep itself is a methodological dead end here, and that's informative

A full sweep of every even address in `room2_lever_boundary.snap`'s whole ~1MB RAM (script:
`scratchpad/cadaver18/scan_writers.py`, same shape as the earlier `$568e` scan) for any decoded
instruction whose operand text names a literal address inside the index table's own byte range
(`$4c536`-`$4c636`, 256 bytes = 64 × 4-byte slots) found **zero hits, anywhere in the image**. This
is a real negative, not a missed target: unlike `$568e`/`88(A5)`/`1162(A5)` (each reached directly,
either as an absolute literal or a fixed `(A5)+N` displacement), the index table is only ever
reached through **one extra level of indirection** — code loads a *pointer* to it out of the
resource-type-descriptor row (itself found via `(A5)+96` → row `type*18`), so no instruction
anywhere ever encodes `$4c536` as a literal operand. The writer-scan technique that worked for
§14's targets fundamentally cannot find this one; a caller-graph approach was needed instead.

### 15b. The table's three consumer primitives and its one initializer, fully disassembled

- **`$00c52c`** (`ResourceRow_Resolve_ByTypeD0`): `A0 = (A5)+96 → row[D0]` (18-byte stride,
  confirmed), returns `A1 = row+0` (index-table ptr), `A2 = row+4` (data-base ptr). Every other
  routine below starts with `bsr $c52c`.
- **`$00c628`** (`ResourceIndexTable_ScanForward_FromD1`): from row+16 (slot count, `64` for
  rooms), scans slots `D1..count-1` for the first slot whose leading word is non-zero (`tst.w
  (A1); bne` = hit). On a hit, `D1` = the found slot index, `A0` = `row+4-base + slot's own +2
  word` (a computed record pointer), matching §14's already-decoded room-record format. On a
  miss, `D1 = -1`. **This is a "find the next populated entry", not a keyed lookup** — the
  README/§14's own `$011256` (`RoomIdLookup_ByD2_LinearScan`) wraps this exact primitive in its
  own ID-compare loop (confirmed: one of `$c628`'s 13 real callers, at `$010f4a`-`$010f76`, does
  precisely that — `bsr $c628` then `cmp.w 2(A0),D2` against the target id, re-looping from the
  next index on a mismatch).
- **`$00c660`**: the same scan, backward from `D1` down to `0` instead of forward — one real
  caller found (`$00ad06`, part of a "recover after a miss" retry inside the same routine that
  also calls `$c628`, `$00acf0`-`$00ad60`).
- **`$00c696`** (`ResourceTypeTable_InitAllRows`): walks a fixed **10-entry** table at `$57c8`
  (one row per resource type, 0-9 — type `8` is rooms), for each entry carving that type's
  index-table region **sequentially out of a shared pool at `(A5)+100`** and its data-base region
  sequentially out of `(A5)+44`, writing the row's `+0`/`+4`/`+12`/`+16` fields, then `bsr $c6d0`
  to **clear** the newly-carved index-table region to all-zero and clear row+8. This is the
  routine that produces the "all 64 slots empty" state §14 found live — it only *allocates and
  clears* space for every type, it never writes a real entry into any of them.

### 15c. Whole-image caller scan (BSR/JSR, not just the TOS-ROM-only `--callers` mode) of all four

`scratchpad/cadaver18/find_callers_ram.py` (new — sweeps every even address the same way, keeping
`bsr`/`jsr`/`jmp` lines whose resolved target matches a given list) found every real call site of
`$c628`/`$c660`/`$c696`/`$c9c2`/`$c9ee` (the last two are §15d's find) in the whole loaded image:
14 call sites for the scan primitives (disassembled the context of every one — `$009700`,
`$009820`, `$009bfe`, `$00ab7a`, `$00abae`, `$00ad06`, `$00ad2c`, `$00ad38`, `$00b208`(`$c696`,
not `$c628`), `$00b738`, `$00c3ea`, `$00de74`, `$00e544`, `$00e826`, `$010f52`, `$011262`), plus 5
each for `$c9c2`/`$c9ee` below. **Every one of the 14 scan-primitive callers is read-only usage**
(enumerate, ID-match-and-retry, or iterate-and-consume) — none write a non-zero word into any
slot. This rules out a live "register on lookup miss" pattern existing anywhere reachable.

`$00b208`'s call to `$c696` (a **second**, non-boot re-init of the whole 10-type table) sits
inside `$00b1e0`-`$00b52a`, a large routine that opens a memory-resident data stream (`jsr
$1127c.l`/`jsr $112fc.l`, a generic "read N bytes from an already-open in-memory block" pair, not
disk I/O) and bulk-reloads resource types **2, 3, 4, 5, 6** (via `$00b534`, a per-type "read
row+8's byte count, then read `16(A0)*4` bytes straight into the row's index table" bulk loader)
plus **2, 3, 5, 6, 7** (a plain `move.l #imm,12(A0)` write) from that stream — this is the level's
*graphics/sound asset* loader, confirmed by what it reads (the `$5a9c` palette, 800-byte screen
regions, etc.). **Type 8 (rooms) never appears anywhere in this routine, for either mechanism** —
rooms are structurally excluded from the generic level-asset bulk loader, not merely
under-observed; this sharpens §14's "CAVERN/TUNNEL were linked directly at boot, not through this
generic resource system" into a proven code-level exclusion rather than an inference from one
empty snapshot. (`$00b1e0` itself has **zero real callers anywhere in the loaded image** either,
by the same whole-RAM scan — it's dead code in this exact playthrough, a separate, weaker echo of
the same pattern found for the actual type-8 writer below.)

### 15d. The actual writer: `$00c9ee`, the save-game restore deserializer — gated behind a save
    file this spike's boot path has never loaded

A sibling pair of routines, found while reading `$00b1e0`'s neighbourhood for other `bsr
$c52c`-based callers: **`$00c9c2`** (serialize: `A3 = save-buffer cursor`; writes row+8's byte
count then that many raw bytes, then the *whole* index table, `16(A0)*4` bytes, into the buffer)
and **`$00c9ee`** (its exact mirror: deserialize the same two blocks *from* the buffer *into* the
row's data-base region and index table). Their call sites:

```
$00b758: move.l #$44414320,D0   ; "CAD " (ASCII), a save-file magic header
$00b764-$00b77e: moveq #{3,4,5,8,6},D0 / bsr $c9c2   ; SAVE: serialize types 3,4,5,8,6 in turn
```
```
$00b8fc: move.l (A0),D0 ; read the loaded buffer's own header word
$00b906: cmpi.l #$44414320,D0 / beq  ; must match "CAD " or bail (-> $b9a6, a different path)
$00b94e-$00b968: moveq #{3,4,5,8,6},D0 / bsr $c9ee   ; RESTORE: deserialize the same 5 types
```

**Type 8 (rooms) is explicitly included on both sides** — `$00b962: moveq #8,D0 / bsr $c9ee` is a
real, concrete write of a fresh index table (and its associated data bytes) into the live type-8
row, sourced from whatever a `"CAD "`-headed save buffer contains. This is the **only** writer of
the type-8 index table found anywhere in the whole loaded image, after an exhaustive caller sweep
of every routine that ever dereferences `(A5)+96`.

The restore call sits inside the boot-time menu handler already named in the README (milestone 6,
"restore-game prompt... place a disk... or ESC to start at the beginning") — `$00b822` onward
reads scancodes and branches on function-key-style codes (`$3c`/`$3d`/`$3e`), and `$00b8fc`'s
"CAD " check is the gate on whichever branch corresponds to "load an existing save" rather than
"ESC: start fresh". **Every boot in this whole spike, from the very first milestone pass onward,
has taken the ESC/start-fresh path** (README's "How it was run" section, `gameplay_empire.snap`'s
own provenance) — the restore branch, and therefore `$00c9ee`'s type-8 write, has **never executed
once** in any snapshot or trace this spike has produced.

### 15e. What this does and doesn't settle

**Settled**: the type-8 table isn't dead/vestigial code with no writer at all (§14 left that
genuinely open) — a real writer exists, is fully disassembled, and its non-execution in every
snapshot this spike has is now explained by a concrete, checkable precondition (which boot menu
branch got taken), not a mystery.

**Not settled, and worth stating plainly rather than overclaiming**: `$00c9ee` only *restores*
whatever a save file already contains — it cannot be the mechanism that puts a room's entry into
the table for the **first** time within a single playthrough (pulling the lever, if it does
anything to this table at all, cannot itself be "run the restore deserializer", since that needs a
pre-existing save buffer already containing room 3's registration). Two live readings follow,
genuinely open:
1. The resource-table system is **orthogonal to the lever entirely** — a save/continue
   bookkeeping structure, unrelated to how new rooms actually get discovered during live play
   (which would have to happen through the still-undecoded `$defa` "actual load a new room" call
   from README §9/§10c, or some other mechanism this spike hasn't located at all). This reading is
   consistent with §14's finding that the descriptor-rewrite hypothesis was directly refuted and
   with this pass's own finding that no "insert on miss" code pattern exists anywhere.
2. A **first booted-fresh playthrough never populates type 8 live at all** — CAVERN/TUNNEL's link
   is hardcoded (§14), and room 3 (if reachable this session) might load through a per-room
   mechanism that also bypasses this table, with the table only ever mattering for a genuine
   save/continue flow (e.g. resuming a game where the player already has rooms 1-3 unlocked from
   an earlier session written to disk).

**Concrete, not-yet-tried next step**: cold-boot the game, actually trigger the in-game **SAVE**
path (`$00c9c2`'s own caller, the `"CAD "`-header writer at `$00b744`-`$00b782` — not yet traced
back to *its* own caller/trigger key this pass) from a state where the player has reached as far as
possible, then reboot and choose **"place a disk" / restore** instead of ESC, and check live
whether the type-8 table (still just `$4c536`, 256 bytes) picks up any non-zero slot — this would
directly test reading 1 above (orthogonal) vs. 2 (the table only ever holds what was saved). If
still empty even after doing this, that's strong evidence the table has nothing to do with the
lever regardless of save state, and the real per-room discovery mechanism (if any) lives entirely
inside `$defa`'s undecoded body.

## 16. Secondary thread checked this pass: the axe/pick has never been picked up in any existing
    snapshot

Per the standing lower-priority lead (the walkthrough lists a pick collected before the lever,
though not explicitly *for* it). CAVERN's sprite-object-array slot 4 is confirmed (via
`sprites/manifest.csv`) to be the axe/pick prop, base `$38338 + 4*$46 = $38450`. Dumped slot 4's
bbox/state across every CAVERN-loaded snapshot this spike has produced (`gameplay_empire.snap`,
`movement_at_boat_boundary.snap` — after the 11th pass's boat-boundary walk already added a `BOAT`
item to the array, count 22→23 — and `cavern_east_door_matched.snap`): **state stays `5` (static
prop) with a stable bbox in all three** — it has never been removed or flagged as held in any
snapshot this whole spike has captured. Untried, not ruled out: actually walking to it and running
the interact sweep there, mirroring what the 13th/17th passes already did at the lever and boat.

## 17. The SAVE-serializer's real caller chain, found (19th pass) — it is not a player-triggered
    hotkey at all; it fires automatically, once, at the very start of every boot, always on an
    empty type-8 table. The axe/pick navigation attempt was also tried this pass and not completed.

Following §15e's own next step ("trigger the real SAVE... reboot fresh... choose restore"), traced
`$00c9c2`'s caller (the `"CAD "`-header writer block, `$00b744`-`$00b782` in the 18th pass's
reading, confirmed here as `$00b758`-`$00b782`) all the way up to its real trigger, using the same
whole-RAM BSR/JSR scan technique as the 18th pass (now promoted to `tools/find_ram_callers.py` -
the 18th pass's own script was scratchpad-only and didn't survive between sessions) plus a new
companion, `tools/find_field_writers.py` (whole-RAM scan for every instruction naming a given
`(A5)+N` operand - the same method §12b used by hand for `2455(A5)`).

### 17a. The caller chain: `$00b6e0` (SAVE-serialize, containing `$00c9c2`) ← `$00b5a8` ← 3 sites
    inside one boot-time menu-init routine, gated on a tri-state flag that is always `0` on first
    entry

`find_ram_callers.py` on `$b6e0` finds exactly one caller in the whole loaded image: `$00b66c: bsr
$b6e0`, itself inside a larger routine entered at `$00b5a8` (confirmed as a real entry point - the
preceding instruction, `$00b5a6`, is `rts`). `$00b5a8`'s own callers: exactly 3, all `jsr
$b5a8.l` (abs-long, found via a raw literal-pointer scan since `find_ram_callers.py`'s original
regex missed abs-long JSR text due to a trailing `.l`/`.w` suffix - fixed in the promoted version),
at `$0068f8`/`$006918`/`$006922`, a 3-way dispatch on the byte at **`2518(A5)`**:

```
$0068de: tst.b 2518(A5)
$0068e2: beq  $6920        ; Z (0)          -> jsr $b5a8 D0=1                       (no c6d0 clear)
$0068e4: bmi  $6900        ; N (negative)   -> clr 2518(A5); c6d0 type8; c6d0 type9; jsr $b5a8 D0=1
$0068e6: ...               ; else (positive)-> c6d0 type8; c6d0 type9; jsr $b5a8 D0=1
```

All three branches call `$b5a8` (which internally calls `$b6e0`, the SAVE-serialize routine)
unconditionally - they differ only in whether resource types 8/9 (§15b's `$c6d0`, the
index-table-clear primitive) get cleared first. `find_field_writers.py` on `2518(A5)` finds every
writer: `clr.b 2518(A5)` at `$00681a` (inside the *same enclosing routine*, well before the `tst.b`
at `$0068de`, with no other writer anywhere between them), plus later writers at `$006900`
(explicit `#0`, inside the `bmi` branch itself), `$006962` (`#1`, well *after* the whole dispatch
block, at the end of this same routine), and two `#$ff` writers elsewhere (`$00b926`, `$01041e`,
not chased - later error/reset paths). **On the first pass through this code, nothing writes
`2518(A5)` between the `clr.b` and the `tst.b` - it is deterministically `0`, so the `beq $6920`
branch is the one that always fires on a cold boot**, calling `jsr $b5a8` directly with no
resource-table clear. The enclosing routine itself (`$0067ea` onward, right after an embedded
developer-string block at `$006790`-`$0067e8` that this pass also stumbled into: readable
fragments like `"...E N...T E...S E...C O...M E..."` sit as raw bytes there, not further
identified) has **zero internal callers anywhere in the loaded image** (`find_ram_callers.py` on
`$67ea`: 0 hits; a literal-pointer scan: also 0 hits) - consistent with this being the program's
own top-level boot-menu entry, invoked once from outside any 68k code this scan can see (i.e. from
`Pexec`'s own program-start handoff), not from an in-game hotkey.

### 17b. Live confirmation, cheap and free of new step-budget burn: every existing gameplay
    snapshot already shows the dispatch completed

Rather than a fresh multi-tens-of-millions-of-step boot run (tried once, see §17c - far more
expensive than expected and inconclusive on its own), the existing committed snapshots already
settle this: `gameplay_empire.snap`, `movement_at_boat_boundary.snap`, and
`room2_lever_boundary.snap` **all read `2518(A5) = $01`** - exactly the value `$006962` writes at
the very end of this same boot-menu routine, after the dispatch-and-`jsr $b5a8` block has already
run. Since all three snapshots were reached via ordinary boot + play (no special save-key ever
pressed in this whole spike), this confirms live that **`$00b6e0`/`$00c9c2` (SAVE-serialize) really
does execute automatically, every single boot, before the language-select/restore-game prompt is
even shown** - it is not a player-triggered "press a key to save" action at all.

### 17c. What this settles, and what it retires from the pass's own plan

This retires the originally-planned step 2 ("trigger the real SAVE, reboot, choose restore, watch
the type-8 table") as no longer meaningful in the form proposed: the serialize call is not gated
behind any discoverable player action, so there is nothing to "trigger" beyond what already happens
on every boot - and because it fires at the very start of boot, before any room has ever been
loaded or any resource registered, **the buffer it writes is always built from an empty type-8
table** (§14/§15's own finding: the live index table has never had a real entry in this whole
spike). Serializing empty data into a RAM buffer, even if repeated via a genuine restore-menu
choice, does not create or reveal a populated table - the open question was never really "does a
save/restore round trip populate type 8," it's "does anything ever populate type 8 in the first
place," which §15/this section together now answer: not automatically, not from any code path this
spike's whole-image scans have found. Whether the in-memory `"CAD "` buffer this routine builds
ever gets written to a real disk sector at all (a precondition for a genuine save file to exist to
restore from) is a separate, still-untraced question - not chased this pass, since it wouldn't
change the answer above even if confirmed.

**One live boot attempt, also worth recording**: a `u b6e0 60000000` (run-to-address) from a fresh
cold boot, no scripted key input, never reached `$b6e0` in 60,000,000 steps (still deep in TOS ROM,
`PC=$00fc2f24`, `A5=0` - the game's own program hadn't even taken over yet). This is not evidence
against the finding above (§17b's snapshot-based confirmation is direct and doesn't depend on it) -
it's a data point that a real cold boot's TOS-side disk/GEMDOS init alone costs well over 60M steps
before the game's own code starts running at all, useful context for budgeting any future
from-scratch boot attempt in this spike.

### 17d. Secondary thread: the axe/pick prop, navigation attempted, not reached this pass

Per the pass's own fallback plan, tried walking to CAVERN's axe/pick prop (sprite-object-array slot
4, bbox `[73,23,66,19]` in `gameplay_empire.snap`, i.e. roughly `x66-73,y19-23`) from the player's
start position (`[25,23,19,17]`, i.e. `x19-25,y17-23` - almost the same y-band, well short in x)
using the confirmed joystick-port-1 protocol (`kbd ff 01/02/04/08` = up/down/left/right, `kbd ff
00` releases - not the keyboard scancodes tried in the very first navigation attempt this pass,
which used the wrong, UI-only input class and produced a small, misleading diagonal drift before
this was caught). Multiple threading attempts (up-then-right, up-then-right-then-down, a longer
up-clearance, a combined diagonal up+right packet) each made partial progress (typically 6-12 units
per successful leg) before stalling completely against what reads as a real, wide obstacle spanning
roughly `x43-57` across every y-band tried between `y6` and `y31` - consistent with the room's own
chest prop (slot 19 here, bbox `[57,21,53,17]`) plus neighbouring props (slot 20 `[54,29,50,24]`,
slot 21 `[43,10,38,6]`) leaving no gap in any of the lanes tried, unlike the 17th pass's own
successful "`y≈12-18`" thread past the same chest to the room's *east* wall (`x=80`) - that route
was walked from a different resume point/object-array state and headed to a different destination
(the east door, not the axe), so it isn't a direct contradiction, but it wasn't successfully
replicated toward the axe this pass either. **Not reached** - the interact/fire sweep was never run
against the axe. Concrete next step if this thread is picked up again: either replicate the 17th
pass's exact route (same snapshot, same step counts) and then turn south into the axe's y-band only
once clearly past the chest in x, or decode the room's own quadrant-cutout collision data (§3's
`(A5)+140` selector, still unlocated) to compute a real clear path instead of trial-and-error
stepping.

## 18. The ring-304 queue's consumer, found (20th pass) — opcode `$8` is a name-banner display
    trigger, not a room loader; the "room loading" thread README §9/§10c/mechanics §14/§17 kept
    circling is now closed with a concrete negative

Following the standing open item from §10c/§14/§17 ("what consumes opcode `$8`, and does `$defa`'s
push lead to real disk I/O"). Found via `tools/find_field_writers.py` on `304(A5)`/`1154(A5)`
against `cavern_east_door_matched.snap` (116 and 93 hits respectively — almost all of them are
*producer*-side push sequences, the same `addq.w #1,1154(A5)` / `cmpi.w #$c8,1154(A5)` shape
`TimerQueueService` and half a dozen other subsystems already share), then picking out the one
genuinely different shape in the list: a lone `subq.w #1,1154(A5)` at `$00fe74` — a decrement,
not an increment, i.e. the one and only *consumer*.

### 18a. `$00fdbc` (`Ring304QueueConsumer_DispatchByOpcodeByte`) is the real drain loop

Full linear disassembly, `$00fdbc`-`$00fe82`: pops a 3-word entry (opcode word, payload longword,
a third word stored to `1156(A5)`), with an optional 4th longword read if the opcode's bit 15 is
set (a variable-length entry, not documented before this pass). `cmpi.b #$8,D6 / beq $ffa4` is a
**dedicated jump for opcode `$8` alone** — every other opcode (the `$9`/`$30`/`$3c`/`$400e`/`$4014`
family already characterized in §4a/§10c/§14 as sound/event cues) falls through into a shared,
generic "call an entity's linked action-script" path (`$fe0c`-`$fe70`, a `jsr`-through-table
dispatcher keyed on a per-entity byte at struct offset `+11`/`+31`). Opcode `$8` bypassing that
generic path entirely, straight to its own handler, is what singles it out as the one opcode worth
tracing — exactly the queue-consumer README §9/§14/§17 had never actually found.

### 18b. `$00ffa4` (`Opcode8Handler_ResolveNameIndex_DrawBanner`) and its full call tree, all static,
    zero trap/FDC instructions anywhere

```
$00ffa4: jsr $11338      ; DoubleBufferPtr_SelectInactive_A5Plus0_156 (see 18c)
$00ffaa: moveq #10,D7
$00ffac: bsr  $a836      ; NameBanner_DecodeStringAndUpdateSlotCache_ByD0Index, payload in D0
$00ffb0: jsr  $11338     ; same buffer-select call again, bracketing the work
$00ffb6: bra  $fe74      ; back into the queue-drain loop's decrement-and-continue step
```

`$00a836` (`move.l A0,D0` first — the payload from the queue entry becomes the string/name index):
1. `bsr $fd2c` → `$fd4e` → `$fda2`: decodes a **6-bit-packed character stream** (tables at
   `168(A5)`/`172(A5)`, indexed by `D0`) through a 256-byte character map at `$5ac0`
   (`PackedNameString_CharacterMapTable`, new this pass), writing plain ASCII bytes into a small
   buffer at `3234(A5)` until the table returns its `$ff` terminator sentinel. This is a **generic
   string decoder**, unrelated to the already-known `$00df46`-`$00df9c` 8.3-filename builder
   README §10c flagged and never connected to anything — a second, independent decode path.
2. `$a846` onward walks a **4-slot LRU cache at the fixed address `$6000`** (10 bytes/slot,
   `$c8`-style capped iteration, `moveq #3,D6`), checking whether `D0`'s index is already cached;
   on a hit it just updates `2132(A5)` (a "currently-displayed name index" global) and returns; on a
   miss it evicts the least-recently-used slot (a byte counter at `2106(A5)` tracks LRU distance)
   and writes a fresh slot header (`$4b` marker word + several other `211x(A5)`/`2108(A5)` globals).
3. Either way it calls `bsr $e030` (`StatusBannerText_WordWrapLayout_CallsBcd0`), which **word-wraps
   the decoded string** (`bsr $116dc` for per-character pixel width, matching the games' own font
   metrics call used elsewhere) against a target width/position (`1256(A5)`/`1258(A5)`, itself
   derived from `2108(A5)`/`2110(A5)`/`2112(A5)` — the cache-slot header's own on-screen position
   fields) and calls `bsr $bcd0` (`MessageBoxBorder_Draw...`) per wrapped line.
4. `$00bcd0` draws a **bordered box from a fixed graphic template at `$5c00`** (`lea $5c00.l,A1`,
   `bsr $bd6e`/`bd92`/`bd98` — corner/edge/fill blit helpers) with the wrapped text inset inside it.

**No `trap`, no `$ffff86xx` FDC register access, no `Rwabs`-style call anywhere in this whole tree**
(`$ffa4`→`$a836`→`$fd2c`/`$fd4e`/`$fda2`→`$e030`→`$bcd0`/`$bd6e`/`$bd92`/`$bd98` — verified by
grepping every instruction disassembled across the whole call graph). This directly answers the
question this thread has been chasing since §9: **opcode `$8` is a message-box/name-banner display
trigger, not a room loader, and `$defa` never gets anywhere near real disk I/O.**

### 18c. `2142(A5)` is a shared "which name to show" register, written by dozens of unrelated call
    sites across the whole game — confirming this is a generic display mechanism, not a room-load
    flag with one special value

`find_field_writers.py` on `2142(A5)` (the same field README §9 read as "sets 2142(A5)=2" for the
room-transition case) finds it written with a couple of dozen *different* literal values across the
image — `$2` (the CAVERN/TUNNEL-door call site, `$007310`), `$3`, `$e`, `$f`, `$1b`, `$1c`, `$1e`,
`$23`, `$25`, `$28`, `$29`, `$2b`, `$2c`, `$31`, `$32`, `$35`, from over a dozen unrelated routines
scattered from `$009016` to `$04cd00` — not one flag with one "go" value, but the generic
**message-index register** the whole game's UI writes before triggering a name-banner display.
`$00df08` (inside `$defa` itself) reads it right back out, confirming `$defa`'s payload really is
just "whatever index was last written here," matching the decode-by-index pipeline in §18b exactly.

### 18d. Live check on `cavern_east_door_matched.snap`: no pending queue entry at all — this specific
    door never reaches `$defa` in the first place, correcting an assumption carried since §13

Resumed the snapshot (`ATARI_NOTRACE=1`, A5 confirmed live at `$18152`) and read
`RoomLoadQueuedFlag_A5Plus2142` (`$189b0`), the queue count (`1154(A5)` = `$18596`, **`0`** both
immediately and after 3,000 further steps), and `PendingRoomTargetWord`/`DoorFacingOrBlockedFlag`
(unchanged at `$003b`/`$01`, matching §13's own values). **The queue is empty** — there is no opcode
`$8` entry sitting here waiting to drain, contradicting the framing this pass inherited ("right
after a portal match fired but before the queue got drained"). This is consistent with, and now
directly confirms, §13's own finding that this specific door (CAVERN's east wall) resolves through
the **"already resident" branch**, which never calls `$defa` at all — so this snapshot was never
going to show opcode `$8` firing regardless of the consumer question. The consumer/handler trace in
§18a-§18b stands on its own (pure static disassembly, no live dependency), but the live check here
is a real, useful correction to the resume point's own documented framing, not a confirmation of it.

### 18e. Where this leaves the room-loading question

Every one of README §9/§10c's speculative branches through `$007104`'s room-transition executor has
now been chased to a concrete end: the "already resident" branch (every crossing seen live so far)
just updates state and loops; the one branch that calls `$defa` pushes a **display** request, not a
load request. **No code path found anywhere in this whole spike ever performs raw sector/FDC-level
disk I/O for a room** — the "self-contained one-disk crack, no swap needed" framing (README's
Milestones section) plus the 104KB/9-palette resident-asset finding (§13) both point the same way:
whatever room 3 needs is either already sitting in RAM from the one-disk boot load (matching the
"CAVERN/TUNNEL linked directly at boot, hardcoded" reading from §14) or requires a mechanism this
spike's whole-image static sweeps still haven't found. This retires the queue-consumer thread
entirely — it is not the lever's missing link, and it is not a currently-live room loader either.

## 19. The axe/pickaxe, reached and picked up live (20th pass, cont.) — closes §16's standing open
    item with a real, screenshot-confirmed pickup, and opens a new, concrete lever lead

Per the pass's own fallback plan (triggered by §18's queue-consumer thread dead-ending): replicated
the shape of the 17th pass's successful chest-clearing route from `gameplay_empire.snap`, this time
turning toward the axe's own y-band instead of continuing to the east door, using exact live bbox
reads at every leg rather than replaying blind step counts.

### 19a. The route, exact bboxes at each leg (player slot 0, `$038338`, bytes 0-3 = `[x_lead,y_lead,
    x_trail,y_trail]`)

1. **Right** (`kbd ff 08`) from the start (`[25,23,19,17]`) to the chest boundary: stalls at
   `[52,23,46,17]` after ~1.2M steps — matches the 11th pass's own chest-boundary finding exactly.
   Checkpointed as `axe_touch.snap`'s ancestor (not committed — see Files).
2. **Up** (`kbd ff 01`) from there: stalls quickly at `[52,12,46,6]`, blocked by `slot16`'s own bbox
   (`[55,7,49,4]`, the state-`4` outlier object) — not the open lane hoped for by continuing further
   up, but `y=12` is already inside the 17th pass's own confirmed `y≈12-18` clear band.
3. **Right** again from `y=12`: runs cleanly to `[79,12,73,6]` (chest/`slot19`/`slot20` no longer in
   the way at this height) — the same lane the 17th pass rode to the east door, confirmed
   reproducible from a different launch point.
4. **Down** (`kbd ff 02`) from an intermediate checkpoint at `[76,12,70,6]`: descends cleanly to
   `[77,24,71,18]` and stalls — this **overlaps the axe's own bbox** (`[73,23,66,19]` in the
   pristine snapshot: x-overlap `71-73`, y-overlap `19-23`, a real AABB hit per §4's own test shape).

### 19b. Live-confirmed, not just bbox math: the status bar reads "PICKAXE", and it's a real pickup,
    not just a name-hotspot touch

`tools/snap_render.py` on the resulting snapshot (`axe_touch.snap`, committed as `axe_touch.png`)
shows the status bar reading **"PICKAXE" / "CAVERN"** — the same proximity name-hotspot mechanism
already characterized for "LEVER" (§7) and "BOAT" (11th pass README entry). More than a hotspot,
though: `SpriteObjectArrayCount_A5Plus1152` (`$185d2`) reads **`23`**, up from the pristine
snapshot's `22`, with the new slot 22 entry holding a **`$ffffffff` sentinel bbox** — off the walkable
map, the same signature the 11th pass's "BOAT" pickup produced (README: "picks up a 'BOAT' item...
inventory boxes fill in"). A direct pixel crop-and-diff of the inventory icon panel against a fresh
render of the pristine `gameplay_empire.snap` (not the old milestone screenshot, to rule out a
palette/pipeline difference) confirms it visually: the panel gains **two** filled icon boxes where
the pristine start has none — a pickaxe-handle icon (this pickup) and a separate "?" icon (almost
certainly the "SILVER COIN" picked up incidentally during the initial Right-to-chest-boundary leg,
per the 10th pass's own note that walking right "picks up a coin and other items along the way").
This closes mechanics §16's open item outright: **the axe/pick has now been picked up, live, in this
exact one-disk Empire playthrough.**

### 19c. The pickaxe-precondition lead, retracted (user ground truth, same pass) — the lever needs
    no item, only "the action"

§14's own priority-2 next step read the walkthrough's room-1 item list (coin/diary/pick collected
before the lever) as a possible inventory precondition, and §19b's pickup was aimed at unblocking a
"retest with it held" plan on that basis. **User-supplied ground truth, from direct knowledge of
this exact game, retracts that reading**: the lever can be operated with just the interact action,
no item needed. This means the 13th pass's own "no tested input opens the door" finding (every
keyboard/joystick/fire input tried inert, `room2_lever_boundary.snap`) has the wrong explanation —
not a missing item, and (per §14/§18) not a portal-table/resource-table gate either. The most
likely remaining explanation, not yet tested: **imprecise positioning** — every prior attempt used
the one position reached via the 13th pass's original held-Left approach, and §14's own priority-3
next step ("re-examine whether that position is even the narrowest trigger tile... a finer
sub-approach-direction sweep hasn't been tried") was never chased. `axe_touch.snap` (pickaxe held)
is no longer a needed precondition for the next attempt, though it doesn't hurt to use it as the
travel starting point since the pickaxe is already there. **Concrete next step**: a finer position
sweep right at TUNNEL's lever hotspot (small nudges in every direction from the known
`room2_lever_boundary.snap` position, re-triggering the "LEVER" name-hotspot after each nudge to
confirm still-in-zone) with the basic interact action (`kbd 50`/`kbd d0`, action 101) retried at
each candidate tile, watching TUNNEL's live portal table (`$037e48`, count at `(A5)+1162`, §10b) and
the room-name banner (§18) for any change — the door-opening signal doesn't have to be guessed at,
it's a portal-table entry appearing where §10b found none.

## 20. The finer-position-sweep lead, closed (21st pass) — the LEVER hotspot is essentially one
    tile, the player is hard-blocked with zero clearance on the two sides that face the object, and
    interact is inert everywhere reachable inside the zone

Following §19c's own next step and direct user redirection (ground truth: the lever needs no item,
only "the action" — retracting the pickaxe-precondition reading). Drove `room2_lever_boundary.snap`
live via the REPL (`kbd ff 01/02/04/08` directional packets, `kbd 50`/`kbd d0` for the interact
action, `m 38338 4` for the player's own bbox, `m 37e48 140`/`m 185dc 2` for TUNNEL's live portal
table and its count) rather than more disassembly.

### 20a. A real methodology trap, worth recording for any future pass: "hundreds to low thousands of
    steps" undershoots this game's movement latency, and a released direction keeps drifting for a
    while afterward

The very first attempts (300, then up to ~300,000 steps split across several `s` calls with reads in
between) showed **zero** bbox change in any direction — looking exactly like "blocked everywhere,"
which would have wrongly closed the sweep before it started. The actual cause: this game's walk
appears to be a **bounded, self-terminating multi-substep move triggered once per joystick packet**
(matching mechanics.md §1's "checked once per simulated sub-step," now seen from the outside) rather
than a continuous velocity while held. A single `kbd ff 02` (down) packet, given enough steps to run
to completion (empirically **~60,000–100,000 steps**, after which `PC` returns to the same idle
main-loop address, `$00006b76`, seen at rest before the packet too), reliably produces a clean,
reproducible **3-unit** move and then stops on its own — confirmed by re-running the identical
command sequence from the identical snapshot twice and getting the identical resulting `PC`
(`$00015190`) and bbox both times. Shorter budgets (hundreds to tens of thousands of steps) catch
the move mid-flight or before it starts, and — the trap — if a *different* command sequence happens
to spend more wall-clock-irrelevant-but-step-relevant time in between (e.g. an interact attempt's own
settle wait), the same nominally-inert nudge can appear to have silently continued for another unit
during that unrelated wait. Every reading below uses the settled, self-terminating-move methodology
(one packet, ≥60,000 steps, then read), not the original short-nudge one.

### 20b. Directional results at the baseline tile: hard-blocked toward the object, wide open away
    from it

From `room2_lever_boundary.snap`'s own bbox (`[x 8-14, y 6-12]`, matching mechanics.md §14 exactly):

- **Up** (`kbd ff 01`) and **Left** (`kbd ff 04`): **zero bbox change over 300,000+ held steps**,
  each tested independently. This is a real, hard block with no measurable clearance at all — not a
  slow-pace artefact (300,000 steps is 3-5x what a full 3-unit Down/Right move needs). Left heading
  toward smaller x matches §14's own "holding Left for 100k more steps produces zero position
  change" finding, now reproduced with a much larger budget and confirmed for Up too.
- **Down** (`kbd ff 02`) and **Right** (`kbd ff 08`): both move cleanly, ~3 units per settled packet
  (`[8-14,6-12]` → `[8-14,9-15]` for Down; → `[11-17,6-12]` for Right), reproducibly.

Net picture: the player's baseline position is wedged into a corner with **zero give** on the two
sides nearest the interactive object (the object sits at `[5-7,12-15]`, diagonally below-left, per
§14), while the two sides facing away from it are wide open. A follow-up check — move Down first to
enter the object's own y-band (`y 9-15`), then try Left from there, hoping the wall that blocks Left
at `y 6-12` doesn't extend into `y 9-15` — also hard-blocked immediately (`x` stayed at trailing edge
`8` the whole time, one unit short of the object's own leading edge `7`, matching §14's "off by
exactly 1 unit in x" finding exactly). **Genuine AABB overlap with the object is not reachable from
this approach direction by any combination of cardinal moves tried this pass** — §14's suspicion
confirmed, not just repeated.

### 20c. The "LEVER" name-hotspot itself is gone by 3 units in either free direction — screenshot-
    confirmed, not inferred

Rendered (`tools/snap_render.py`) three settled positions: the baseline tile (status bar: **"LEVER" /
"TUNNEL"**, confirming this really is the 13th pass's own hotspot tile), a clean 3-unit-down move
(status bar: **"TUNNEL" only** — no "LEVER", icon panel's special box empty — `lever_hotspot_gone_
3units_down.png`), and a clean 3-unit-right move (same: "TUNNEL" only, hotspot gone). Combined with
§20b's finding that the only two directions with any room to move (Down, Right) both drop the hotspot
well before any new tile could plausibly offer a different interact outcome, and that the two
directions actually pointing at the object (Up, Left) are hard-blocked at zero clearance: **there is
no reachable second tile, in any direction this pass could drive to, that is both inside the "LEVER"
hotspot and different from the position the 13th pass already tested.** The hotspot is, for every
practical purpose reachable by ordinary movement from this approach, the single tile already tried.

### 20d. Interact retested at baseline and at every reachable position along the way, portal table
    watched directly each time — zero effect, every time

`kbd 50`/`kbd d0` (action 101, this spike's only confirmed interact verb) retried at the baseline
tile and at several points along the Down/Right drift (a mix of clean and momentum-tailing
positions, spanning baseline out to 3 settled units in each free direction), each followed by a
direct dump of TUNNEL's live portal table (`$037e48`, 140 bytes, §10b) and its live count
(`(A5)+1162` = `$000185dc` here, confirmed via `A5=$18152` matching every other snapshot in this
spike) rather than a screenshot guess. **Byte-for-byte identical before and after, every single
time** — no new entry, no count change, matching §10c/§11/§14's own exhaustive descriptor-level
checks and extending them to cover this pass's newly-reached positions too.

### 20e. Conclusion: the position-sweep hypothesis is closed, not just untested

§14's own priority-3 next step ("re-examine whether the known position is the narrowest trigger
tile") is now answered directly: it effectively *is* the only trigger tile reachable this way — the
hotspot has no meaningful footprint beyond it in any direction ordinary movement can explore from
this approach, and the object behind it is walled off with zero clearance on both sides that matter.
Between this and mechanics.md §§10-18's own closed leads (portal table, resource table, fire chain,
icon panel, mouse-buttons-as-keys, ring-304 queue consumer), **every input class and every reachable
position this spike has been able to generate has now been tried against the lever's door with no
effect.** This leaves the user's own framing from this pass's own briefing as the honest state of
play: either a genuinely different, not-yet-characterized verb exists (a second action-id family
this spike's 9th-pass sweep didn't cover, or an approach from a completely different direction this
one-disk-image playthrough's known room layout doesn't offer a path to), or the mechanism lives
somewhere this spike's whole-image static sweeps (§15c/§17a's own techniques) haven't pointed a
caller-graph search at yet. Not chased further this pass, per its own scope.

## 21. The lever's own object-array entry, read in full and run through §4's own interactive-
    classification test (22nd pass) — it fails: the object is PLAIN SCENERY, not interactive/pickup

Following §20's own handoff (whether the lever's object is even flagged "interactive" by §4's
classification, before spending more time on §18a's never-traced generic action-script dispatcher).
A handful of targeted `m` reads against `room2_lever_boundary.snap` (A5=`$18152` confirmed live, as
in every snapshot this spike has produced), no live stepping.

### 21a. TUNNEL's sprite-object array base is `$038338`, same address CAVERN's happens to use — now
    confirmed live for TUNNEL specifically, not carried over by assumption

`SpriteObjectArrayPtr_A5Plus56` (`$1818a`) reads `00 03 83 38` = `$038338`; the count at
`SpriteObjectArrayCount_A5Plus1152` (`$185d2`) reads `2`, matching §4/§10b's stride-`$46`, 2-entry
picture for TUNNEL exactly. The one non-player entry (slot 1, base + `$46` = `$03837e`) dumped in
full, all 70 bytes:

```
07 0f 05 0c 21 10 00 05 99 10 00 06 fa 0e 00 00 22 08 00 9a 36 0a 00 4e ff 01 00 10 00 00 00 00
00 00 00 00 00 00 00 05 99 52 05 00 ff 00 00 aa 00 04 01 18 00 05 99 56 00 90 80 00 e0 00 a0 00
60 00 03 81 0f ff
```

`bbox` (bytes 0-3) = `[7,15,5,12]` — an exact match for §14/§20's own "the object sits at
`[5-7,12-15]`, diagonally below-left" description, confirming this live entry really is the same
lever/tool-prop object the whole spike has been circling, not a different slot.

### 21b. Both halves of §4's interactive/pickup test, checked directly against real bytes for the
    first time this spike

Per §4's own pseudocode: `byte24 < 0` (top bit set) **and** a flag on the entry's own `+10`-linked
struct (`+15` bit 2) set → `$FD`/"interactive, pickup" outcome; otherwise plain scenery.

- **`byte24`** = `0xff` — top bit set, first condition **true**.
- **`+10` pointer** (bytes 10-13: `00 06 fa 0e`) = `$0006fa0e`. Dereferenced (32 bytes dumped,
  `m 6fa0e 32`): `07 0f 10 00 00 90 00 23 00 46 01 01 22 22 22 01 12 85 1e 0e 07 1b 33 ff ff 1f 16
  0f 05 0a 33 20`. Byte at offset `+15` (0-indexed into this dump) = `0x01`; `0x01 & 0x04 = 0` —
  **bit 2 is clear**, second condition **false**.

The `AND` of the two conditions is **false**. Per §4's own branch, this object is classified plain
scenery, not "touched an interactive/pickup object" — `shared_result.byte[1]` never gets set to `$FD`
for it, and the `cmpi.b #$fd,1(A4)` item-pickup branch (§5) would never fire on this object no matter
how it's touched.

### 21c. Why this closes the touch/opcode-`$9` thread for the lever specifically, on top of (not
    instead of) §20's own position finding

§4a's dedup-cache/opcode-`$9` push is worded as unconditional on the AABB overlap itself (it records
the touch, then separately branches on the `$FD` classification) — so in principle a plain-scenery
object could still be touched and still queue opcode `$9` into the ring-304 queue, reaching §18a's
generic per-entity action-script dispatch (`$fe0c`-`$fe70`) independently of the `$FD`/pickup outcome.
But §4's own routine *is* the object-array collision/obstacle check (§4's own header), and §20b
already established, live, that genuine AABB overlap with this exact object is **not reachable by any
combination of cardinal moves** from the approach this spike has driven — the player is hard-blocked
with zero clearance on the two sides that face it. A block-before-overlap collision test never
actually produces the intersection §4's `if` guards, meaning the touch/dedup/opcode-`$9` push never
executes for this object via ordinary movement in the first place, regardless of classification.

Put together: (1) the object was never classified "interactive" to begin with, so even a genuine
touch would not have set the pickup flag §5's downstream check reads, and (2) §20 already showed the
touch that would trigger *any* of §4a's machinery (interactive or not) is itself unreachable by
ordinary movement. This is a double, not a single, negative — closes the touch/opcode-`$9` pathway
for the lever specifically without needing to trace §18a's dispatcher against this entity at all
(there is nothing here for it to ever be handed).

### 21d. Recommendation for the next pass: the whole-image caller-graph scan, not a new input verb

Of the two leads §20/the memory resume point left open — a genuinely different, uncharacterized verb
outside the 9th pass's action-id sweep, or a whole-image caller-graph scan for whatever actually gates
the door — the caller-graph scan is the cheaper and more likely to pay off. Every productive finding
in this spike from §9 onward (the debug-string scan, §10's static portal-table disassembly, §18's
`find_field_writers.py`-driven queue-consumer discovery) came from static/whole-image techniques, not
live input-guessing; every live input-guessing round (§8, §13, the original interact sweep, §20 itself)
came back inert. With the portal table (§10, no entry) and the touch/interactive pathway (this
section) both now closed as real negatives, whatever opens this specific door is neither of the two
mechanisms this spike already knows how to search for — the honest next move is `find_ram_callers.py`/
`find_field_writers.py` against a candidate the game itself would need regardless of mechanism (a
per-door "open/locked" state byte, or whatever code path the debug string `"DOOR ERROR"`'s *sibling*
success case writes to, since §9/§10c only followed the failure prints) rather than guessing at a
third input verb with no evidence one exists.

## 22. Action 101's own script decoded byte-by-byte (23rd pass) — confirms it, does nothing
    door-related, and a bigger find from finishing the debug-string scan: a whole
    previously-undocumented "object verb" bytecode interpreter (LOCK/UNLOCK/MOVE/creature
    kill-wake-sleep/rucksack/chest ops), whose LOCK/UNLOCK opcodes write the *exact* bit §21b
    found clear on the lever's own linked struct

Per the standing README next-step (§21d's caller-graph recommendation, plus a cheap side-check on
action 101's own script). Two independent threads this pass, both static/data-scan only — no new
`kbd`/`mouse` input.

### 22a. Action 101's script (`$16f07`), decoded against `ai.md`'s 17-opcode table — animation-only,
    confirmed rather than assumed

Raw bytes (`m 16f07 64` off `room2_lever_boundary.snap`):

```
85 bc 81 09 80 06 83 01 87 34 8a 02 3b 8b 85 bc 81 09 80 05 83 0a 87 35 8a 02 88 9c 0e 8b 81 09
80 05 83 03 87 35 8a 02 88 9c 2d 8b 83 06 81 09 80 07 ...
```

Walking it opcode-by-opcode against `ai.md`'s table: `$85 bc` (set tick-scale from operand `$bc`),
`$81 09` (set slot flag-lane bit), `$80 06` (frame-group byte), `$83 01` (duration), `$87 34`
(load preset `$34` from the shared table), `$8a 02` (set flag bits), then a **literal frame byte**
(`$3b`, `<$80` — ends the tick per `ai.md` §3's own yield rule), then `$8b` (force-idle — re-installs
the null action, per `ai.md`'s own reading, once the countdown from `$83`'s duration expires). The
stream repeats this same shape twice more (`$85 bc … $87 35 … $88 9c` — `$88`'s peeked byte `$9c` has
its top bit set, so per `ai.md`'s own reading it "ends the entity's turn" without also taking the
literal-frame path — then a literal frame byte on the *next* tick, then `$8b` force-idle again).
**Every opcode present is one of the 8 confirmed animation/timing/flag opcodes (`$80/$81/$83/$85/
$87/$88/$8a/$8b`) plus literal frame bytes — no `$8c`/`$8d` (the only chain-to-another-script pair)
appears anywhere in the 64 bytes dumped.** This closes the side-check exactly as expected going in:
action 101's own script is a short, self-terminating "set a preset, show a pose, hold it, go idle"
sequence — three back-to-back instances of that shape, matching the 4th pass's "crouch, arm/implement
raised, relax" visual read — with nothing that touches collision, the portal table, or any
door/room-state field. (The `$8b` force-idle recurring mid-dump, before the full 64 bytes are
consumed, is a hint that bytes past the first `$8b` belong to a *different* action id's script packed
contiguously in the same region, not more of action 101's own stream — consistent with `ai.md`'s own
note that scripts are just byte offsets into one shared pool, not separately allocated. Not chased
further; irrelevant to the door question either way.)

### 22b. The embedded debug-string table, finished (picking up where §9 stopped at `$172c7`) — it
    runs to `$17951` and names a whole engine-level "object verb" vocabulary, not just room-transition
    errors

Full dump, `$172c7`-`$17951` (2200 bytes covers it with room to spare — the table is followed by
null padding). §9 had only reached as far as `"DEL_OBJ_IN_ROOM ... REDUCE ENTRY SIZE ERR"`; the rest
of the table, previously unread:

```
OBJECT NOT IN RUCKSACK, CANT ADD TO HEAP, EXCEEDED MAXIMUM HEAP SIZE, DELETE ERROR,
CANT FIND A SPACE CSORT, CANT ADD SAME UOBJ TO SLIST, NO ROOM IN SORT LIST,
TOO MANY CREATURES IN ROOM, NOT FOUND CREATURE TO DELETE, EXCEEDED ADD LIST SPACE,
NO CREATE SPACE IN ROOM, EXCEEDED SPACE FOR MULTIDEL, NO SPACE IN RUCK,
EXCEEDED COLLISION CHECK LIST, CANT BE NEG OBJ PUSHED, CANT BE ZERO OBJ PUSHED,
SHOWING AN NON-EXISTANT OBJECT, CANT FIND A SPACE, GOANI A NONANI OBJECT,
GOANI A NON-EXISTANT OBJECT, STOPANI A NON-EXISTANT OBJECT, STOPANI A NONANI OBJECT,
KILLING A NON-EXISTANT CRE, UNINV A NON-EXISTANT CRE, WAKING A NON-EXISTANT CRE,
SLEEPING A NON-EXISTANT CRE, SET ACTION NOT WRITTEN, REVEAL NAME OF NON-X OBJECT,
LOCKING NON-EXISTANT OBJECT, UNLOCKING NON-EXISTANT OBJECT, MOVEING A NON-X OBJECT,
GOMOVE A NONMOVE OBJECT, STOP MOVE A NON-X OBJECT, STOPMOVE A NONMOVE OBJECT,
FLAG OP ON NON-X OBJECT, ELSE SHOULDNT BE CALLED,
PUT IN RUCK AN OBJECT THAT DOSNT EXIST, PUT IN RUCK RTN. RUCK FULL,
EXCEEDED ADD LIST SPACE, CREATE SIZE ZERO, NO SPACE IN THIS ROOM, INIT ROOM ERROR,
CANT PUT CREATURE IN ROOM, CANT FIND A SPACE PUT IN ROOM, GOACTI NON-X OBJECT,
STOP ACTI NON-X OBJECT, MOVE A NON-X OBJECT, UNLOCK CHEST NON-X OBJECT,
UNTRAP CHEST NON-X OBJECT, CLEAR CHEST NON-X OBJECT, DIRTY POTION NON-X OBJECT
```

This reads unmistakably as the error-message set of a **generic room/level "object verb" scripting
language** — LOCK/UNLOCK, MOVE/GOMOVE/STOPMOVE, GOANI/STOPANI, creature KILL/WAKE/SLEEP/UNINVENT,
rucksack (inventory) add, FLAG ops, chest-specific UNLOCK/UNTRAP/CLEAR, and a potion op — not more
room-transition diagnostics like `"DOOR ERROR"`. This is a different, previously-undocumented
system from both `mechanics.md`'s collision/portal machinery and `ai.md`'s animation-only 17-opcode
interpreter, and it's exactly the kind of thing that could plausibly implement "pulling a lever
unlocks a door."

### 22c. Found the LOCK/UNLOCK object opcode handlers directly, via the same address-reference
    technique that cracked `"DOOR ERROR"` in §9 — and one of them writes the exact bit §21b found
    clear on the lever's own linked struct

Scanned the whole snapshot for the absolute addresses of `"LOCKING NON-EXISTANT OBJECT"` (`$17710`)
and `"UNLOCKING NON-EXISTANT OBJECT"` (`$1772c`) as 4-byte operands — **exactly one code reference
each**, `$0104bc`/`$0104d2`, both `lea $xxxxx.l,A0` immediately before `jsr $11788.l` (the same
debug-string printer `"DOOR ERROR"` uses). Disassembling the surrounding block (`$010460`-`$0104e0`):

```
$01049a: bsr  $10738        ; resolve an object by 16-bit id (operand read from the script stream)
$01049e: beq  $104b6        ; not found -> print "LOCKING NON-EXISTANT OBJECT", $0104ba
$0104a0: bset #2,15(A0)     ; found -> LOCK: set bit 2 of the resolved object's own +15 byte
$0104a6: rts

$0104a8: bsr  $10738        ; same resolve
$0104ac: beq  $104cc        ; not found -> print "UNLOCKING NON-EXISTANT OBJECT", $0104d0
$0104ae: bclr #2,15(A0)     ; found -> UNLOCK: clear bit 2 of the same +15 byte
$0104b4: rts
```

**`+15` bit 2 is the exact flag `mechanics.md` §21b read on the lever object's `+10`-linked struct**
(`$0006fa0e`, byte at dump-offset `+15` = `$01`, `$01 & $04 = 0` — bit 2 clear) — the second,
currently-false half of §4's own interactive/pickup `AND` test (`byte24<0` **and** `+10→+15 bit 2`).
This is a real, dedicated engine mechanism for that exact bit, not an incidental flag: a LOCK opcode
sets it, an UNLOCK opcode clears it, on an object resolved by numeric id, matching the struct shape
(a small object-attribute record, not the sprite-object-array entry itself) §21b already dumped 32
bytes of. A neighbouring block at `$010478` (`move.w #$28,2142(A5); bsr $defa`) — reached when a bit-1
test at `$010462`/`$010468` on a *different* struct byte (`+3`, not `+15`) is set — pushes the same
`(A5)+2142`/`$defa` name-banner display §18b already decoded, i.e. a third, related op that shows a
message (plausibly "it's locked") instead of toggling a flag.

### 22d. The id-resolver (`$010738`→`$00c542`/`$00c56e`) uses the *same* `(A5)+96`
    resource-type-descriptor system as the always-empty rooms table (§14/§15) — but against
    **types 6 and 9**, which are live, not the empty type-8 rooms table

`$010738` reads a big-endian 16-bit id from the script stream (`(A1)+` twice), then `bsr $c542`:
`tst.w D1; bpl $c56c` (positive id -> type **6**, `moveq #6,D0`) / `cmpi.w #$ffff,D1` (`$ffff` ->
`A0 = 348(A5)` directly, a "self/current actor" sentinel, also used directly by several sibling
opcodes at `$010756`-`$010790`) / else (a different negative sentinel) -> type **9**, id replaced by
global `2120(A5)`. Both real-type paths fall into `$00c56e`→`$00c576`'s shared body: `mulu #$12,D0`
(18-byte row stride, `A0 = (A5)+96 → row[type]`, matching `$00c52c`'s own layout from §15b exactly),
`A1 = row+0` (index table), `A2 = row+4` (data-base), `A1 += id*4` (the same 4-byte sparse-slot
index format as the rooms table), `D0 = *A1 & $1ffff` (offset), `A0 = row+4-base + D0` — i.e. **this
is a second caller of the exact same generic id→record resolver the whole `(A5)+96` resource system
uses**, just for types 6/9 (object/creature records) rather than type 8 (rooms). Types 6/9 were never
checked live in §14/§15 (only type 8 was dumped and found empty) — since the LOCK/UNLOCK opcodes
clearly operate on real objects during ordinary play (chests, the rucksack, creatures per §22b's
string list), types 6/9's index tables are very likely populated, unlike type 8's. Not dumped this
pass (no live snapshot access needed for the disassembly-only finding above); a concrete, cheap next
check if this thread is picked up again.

### 22e. Traced this interpreter's other entry point — the ring-304 queue's own "generic opcode"
    path (`mechanics.md` §18a's `$fe0c`-`$fe70`, previously flagged but not disassembled) — confirmed
    as a per-entity tagged-record dispatcher, a genuinely new mechanism, not yet tied back to the lever

`$00fdbc`'s drain loop (§18a) branches to its own opcode-`$8` handler (`$ffa4`, the name-banner) but
falls through to `$00fe0c` for every *other* opcode. Disassembled in full this pass:
`A4 = the touched/queued entity's own struct + $10 or +$20` (chosen by struct byte `+11`/`+31`,
whichever is nonzero), then `$00fe14`-`$00fe6e` walks a small table of **tagged records** at `A4`
(`[tag_byte][length_byte][payload...]`, bounded by a count at `1168(A5)`), comparing each record's
tag (`D3`, top bit stripped) against the queue's own opcode byte (`D6`) — on a match, `bsr $11728`
with `A2 = $00fe84` (`add.w D0,D0; adda.w 0(A2,D0.w),A2; jmp (A2)`, a second-level, word-relative
jump table, contents not decoded this pass); on a miss, skip forward by the record's own length byte
and try the next one. **Reading**: an entity can carry its own small table of "if you receive queue
opcode X, run handler Y" bindings — this is plausibly how a scripted room event (not necessarily tied
to player touch/collision at all) gets attached to a specific object. **Not yet connected to the
LOCK/UNLOCK opcodes from §22c** — `$011728`'s own jump table (`$00fe84`) wasn't decoded, so whether
matching a tagged record can lead into the `$010000`-region object-verb interpreter, or is a wholly
separate (e.g. sound-cue) mechanism, is still open. Concrete next step if this is picked back up.

### 22f. Ruled out, not reopened: the fire chain still doesn't reach any of this

Per §21d's own caller-graph recommendation, checked whether `$00db4a`-`$00dc9a` (the fire-driven
"select nearest interactable" pipeline, `mechanics.md` §8/§11) reaches `$010738` or anything in the
`$010000`-`$011256` verb-interpreter range. It doesn't — `$00db8a` onward (disassembled further this
pass than §11 went) is a self-contained highlight/selection-box renderer (reads struct fields
`+18/+20/+23/+46/+50/+51`, calls `$8668`, not disassembled but consistent with the visible
orange-highlight flash from §13) with no `bsr`/`jsr` anywhere near `$010738` or the verb block. §11's
"cosmetic only" conclusion for the fire chain stands — this pass extends rather than contradicts it.

### 22g. Where this leaves the lever

Two real, disassembly-grounded new facts: (1) the exact flag bit §21b found clear on the lever's own
linked struct has a dedicated, discoverable LOCK/UNLOCK mechanism elsewhere in the image, operating on
objects by numeric id against a resource-type table (6/9) that (unlike rooms' type 8) is plausibly
populated; (2) the ring-304 queue's generic dispatch path is a real, previously-undecoded per-entity
event-binding mechanism, distinct from both the collision system and the animation interpreter. Neither
is yet connected to TUNNEL's lever specifically — no code path found this pass writes to the lever's
own `$6fa0e` struct, and the LOCK/UNLOCK handlers themselves have zero direct `bsr`/`jsr` callers
(found only by unique debug-string cross-reference), meaning whatever calls them does so through a
computed jump table this pass didn't locate. **Concrete next steps, in priority order**: (1) locate
the object-verb interpreter's own top-level dispatch table (the word-relative-offset table indexing
into `$010460`/`$0104a8`/etc., analogous to `ai.md`'s `$15cae` or this pass's own `$00fe84`) — finding
it would give the LOCK/UNLOCK opcodes' real numeric ids, and from there a caller-graph or literal-id
scan could find what invokes LOCK specifically; (2) dump types 6/9 of the `(A5)+96` resource table
live (§22d) to see whether they're populated, and if so what object ids exist and what their `+15`
bytes currently read; (3) decode `$00fe84`'s jump table (§22e) to see whether any tagged-record match
leads into the verb interpreter, which would tie the ring-304 queue (already known to carry an
opcode-`$9` "touch" event, §4a) to LOCK/UNLOCK after all — through some *other* entity than the
lever's own inert scenery object.

## 23. LOCK's own opcode id found (18, exact address match); UNLOCK's isn't in the same table — but
    the headline result is bigger: **the lever is object id 144**, and that's now triple-confirmed
    live, closing most of what §22g left open (24th pass)

Per §22g's own priority order: static/data work only, no `kbd`/`mouse` input, all against
`gameplay_empire.snap` (global) and `room2_lever_boundary.snap` (TUNNEL-local, used only to cross-check).

### 23a. The interpreter's top-level dispatch table, found by raw byte-scan at `$010000`-`$010075`
    (59 entries) — LOCK is entry 18, an exact, non-coincidental address match

Per §22g item 1's own reasoning (LOCK/UNLOCK have zero `bsr`/`jsr` callers anywhere in the image —
reconfirmed this pass with `find_ram_callers.py` against `$0104a0`/`$01049a`/`$0104a8` and every
neighbouring handler address named in §22c: still 0 hits each, only the block's own internal `bne`
survives), they must be reached through a computed jump table. Rather than guess a location,
dumped the raw bytes at the block's own stated start (`$010000`, "roughly $010000ish" per §22c) and
found a clean run of 59 plausible word-relative offsets (`$0810 $0914 $09ba $0c28 ... $101a`)
immediately followed, at exactly `$010076`, by real code (`moveq #0,D3; move.b (A1)+,D3; ...` — a
recognisable operand-read prologue) — i.e. the table is bounded cleanly on both ends, not an
eyeballed guess. Resolving each entry as `$010000 + entry` (the exact idiom `$00fe84`/`$011728`
already established elsewhere in this image, see §22e — `add.w D0,D0; adda.w 0(A2,D0.w),A2; jmp
(A2)`, table base in A2, entries are offsets added to that same base) and disassembling the target:

**entry 18 (`$010024` = `$049a`) resolves to exactly `$01049a`** — the first instruction of LOCK's
own handler (`bsr $10738`, §22c's own disassembly, byte-for-byte). This isn't a loose "lands
somewhere in the block" hit, it's an exact match on the address of a specific two-word instruction,
among ~3,400 possible byte values the entry could have held — not a coincidence. **LOCK's real
numeric opcode id is 18.** A handful of other entries corroborate the table is genuine and not a
lucky single hit: id 1 (`$010914`), id 12 (`$010d5c`), id 25 (`$010e38`), id 34 (`$010ee2`), and id
50 (`$010306`) all resolve to the same "read a big-endian word operand from `(A1)+`" or "`bsr
$10738`" prologue shape real opcode handlers use elsewhere in this block (§22c/d). Script:
`scratchpad/cadaver24/dump_table.py` (this session, not committed — reused for §23c below).

### 23b. UNLOCK's own address is not one of the 59 entries — genuinely open, not just unfound

Checked directly: none of the 59 resolved targets equals `$0104a8` (UNLOCK's own first instruction).
The nearest neighbours are entry 17 (`$010490`, the tail of an unrelated error-print stub) and entry
19 (`$0104e0`, which is *also* not UNLOCK's entry — it's the bare `rts` at the very end of UNLOCK's
own error-print path, landed on because `$4e75` is common everywhere in code, not because it's a
deliberate target; unlike entry 18's hit, this one is exactly the low-specificity kind of match that
could be coincidence). So the simple "LOCK=18, UNLOCK=19" adjacency guess (motivated by the two
verbs sitting next to each other both in code and in §22b's debug-string table) is directly refuted
by this data, not just unconfirmed. UNLOCK is reached some other way — a second table, a shared
opcode with an operand-driven branch (ruled out already, §22c's disassembly of `$0104a8` is
unconditional), or it's simply unreachable in this build. Not chased further this pass; a genuine
open item, not a dropped one.

**Aside, not chased further:** the same `add.w D0,D0; adda.w 0(An,D0.w),An; jmp (An)` idiom exists
as a small family of *generic, reusable* dispatch stubs at `$011700`-`$01172e` (six variants,
differing only in which address register carries the table base — `$011728` is the exact one §22e
already named), confirmed via `find_ram_callers.py` to have real callers: `$00fe30`/`$00fe5a`
(§22e's ring-304 tagged-record dispatcher, as expected) and, new this pass, `$010646`/`$010686`
*inside* the verb-interpreter block itself, both `lea $ffba.l,A2` before the `bsr` — a **third,
much smaller table** (base `$0000ffba`, low memory) driving what reads as a nested IF/comparison-
operator bytecode (`$010632`-`$010690`, gated on a scratch byte at `2270(A5)`) embedded inside the
same verb-script stream. Unrelated to LOCK/UNLOCK specifically; noted for whoever next reads this
region, not decoded further.

### 23c. Priority-2 done live, ahead of its own scoping — types 6/8/9 of the `(A5)+96` resource
    table dumped directly from `gameplay_empire.snap` (no `kbd`/`mouse`, no REPL — the snapshot's
    RAM alone is enough once `A5=$18152` is known, confirmed live in every snapshot this spike has
    produced)

`(A5)+96` (`$181b2`) reads `$0004a466`. Row `= ptr + type*18` per §15b's own layout, reconfirmed
exactly against type 8's already-known values (`idx_ptr=$4c536`, `count=64` — matches §15/§17
verbatim, a clean cross-check that this pass's read technique is correct):

| type | idx_ptr | data_base | count | populated |
|---|---|---|---|---|
| 6 (objects) | `$0004b596` | `$0006eb92` | 1000 | **1000 / 1000** |
| 8 (rooms) | `$0004c536` | `$0007550a` | 64 | 0 (matches §15/§17) |
| 9 (creatures) | `$0004c636` | `$0007560a` | 10 | 0 (no live creature exists in this snapshot) |

Type 6 is **fully populated** — every one of the 1000 possible object ids resolves to a real record,
confirming §22d's prediction outright (types 6/9 live, unlike rooms' always-empty type 8). Scanning
all 1000 records' own `+15` byte, **16 currently have bit 2 set** (`$0c/$44/$04/$24` etc. — genuinely
locked objects right now, in ordinary mid-game state), which is itself worth noting: it means LOCK
*does* fire somewhere during normal play on other objects, this mechanism isn't dormant everywhere,
just for the lever. Type 9 being fully empty is consistent with every prior pass's "no live creature
found anywhere" conclusion (7th/9th passes) — creatures are a real, provisioned resource type, just
never instantiated in any state this spike has reached.

### 23d. The headline result: **the lever is object id 144** — cross-confirmed on two independent
    live snapshots, closing the "is the lever even resolvable by this system" question outright

Object id 144's type-6 record: `index_table[144] = $002c0e7c`, masked offset `$0e7c`, `data_base
($06eb92) + $0e7c` resolves to **`$0006fa0e`** — **exactly** §21b's own "lever's linked struct" address,
the one LOCK/UNLOCK's `bset #2,15(A0)` / `bclr #2,15(A0)` operate on. Confirmed three independent
ways, not assumed from the address match alone:

1. **The id resolves to the right address.** `type-6 index_table[144]` in `gameplay_empire.snap`
   → record `$06fa0e`.
2. **The lever's own sprite-array entry links there directly.** Re-derived from
   `room2_lever_boundary.snap` (TUNNEL, where the lever's slot-1 sprite entry actually lives, per
   §21c's own array-walk): `SpriteObjectArrayPtr_A5Plus56` (`$1818a`) → base `$038338`; slot 1
   (`base+$46`) = `$03837e`; that entry's own `+10` field reads **`$0006fa0e`**, byte-for-byte the
   same address — the "`+10`-linked struct" language every earlier section (§4, §21b, §22c) has
   been using turns out to be literally this type-6 record, not a separately-discovered structure.
3. **The classification bytes read exactly as §21b originally found.** In `room2_lever_boundary.snap`,
   record `$06fa0e`'s own `+15` = `$01` (bit 2 clear — §21b's exact original reading, byte-for-byte)
   and `+24` = `$ff` (top bit set — §21's own classification-test reading). (In `gameplay_empire.snap`,
   a different room/session, the same record currently reads `+15=$00` — still bit-2-clear, no
   contradiction, just a different point in that save's history; not chased further.)

This is the strongest single fact this spike has produced connecting the LOCK/UNLOCK mechanism to
the lever specifically: **object id 144 is not a hypothetical or a nearby-address coincidence, it is
mechanically the lever**, reachable by the exact id-resolve path (`$010738`→type-6 row→index-table
entry 144) that LOCK (opcode 18) and UNLOCK both use. A byte-scan of the loaded image for a literal
`[opcode][$00 $90]` (144 big-endian) operand pattern was tried as a cheap next check (`grep`-style
scan for raw bytes `$00 $90` preceded by a plausible opcode byte, `scratchpad/cadaver24/find_id144.py`)
but is inconclusive: the handful of hits with opcode-18 (`$12`) as the preceding byte all sit inside
one dense, evenly-strided region (`$0376ac`-`$037cfc`, stride ~176-192 bytes, incrementing leading
bytes) that reads far more like a coordinate/portal data table than object-verb script bytecode —
not pursued further, a real script invocation (if one exists in this build at all) needs the
interpreter's actual top-level "read opcode byte from the room script, dispatch" entry point, which
this pass didn't locate (it lives outside the `$010000`-`$011256` block itself, most likely back
through `EntityScriptDispatch`/`$15c70` or a sibling "run this entity's init script" caller — not
one of the reusable stubs at `$011700`-`$01172e`: `find_ram_callers.py` against all three `bsr`-able
entry points there, `$011718`/`$011720`/`$011728`, finds only 6 callers total — `$00a09e`, `$00affc`,
the two ring-304 sites already known from §22e, and the two `$ffba`-table sites from §23b — none in
or near `$15c70`, so whatever calls into the verb interpreter's own `$010000` table does it through
neither this family of generic stubs nor a direct `bsr`, meaning it's a fourth, still-unlocated
dispatch site).

### 23e. Where this leaves the lever now

The dormant-flag mechanism from §22c is no longer just "a real mechanism that writes the right bit
somewhere" — it operates on the lever's own object by a confirmed, specific numeric id (144), through
a confirmed, specific opcode (LOCK = 18). What's still missing is purely "who calls it": no script
byte sequence invoking opcode 18 with operand 144 has been found yet, and the top-level entry point
that would read such a sequence from a room's init script wasn't located this pass. **Concrete next
steps, in priority order**: (1) find `EntityScriptDispatch`'s (`$15c70`) or a sibling routine's own
call into this verb interpreter — grep `cadaver.sym`-adjacent code for whatever sets up `A1` (the
script-stream cursor every handler in this block reads via `(A1)+`) before landing in the
`$010000`-table's target range, since that caller is necessarily the thing that owns "which room's
init script" and would settle whether TUNNEL's own room-load ever queues opcode 18/id 144 at all;
(2) if found, `callcap` that opcode-18/id-144 path directly (`callcap <entry> D0=... A1=<script ptr>`
or equivalent) and diff the lever's own `+15` byte before/after — the fastest possible confirmation,
cheaper than any further static search; (3) decode `$00fe84`'s jump table (§22e, still not done) as
the fallback path if (1)/(2) don't pan out, since the ring-304 queue's generic dispatch remains the
other still-open mechanism from §22g.

## 24. The dispatch caller is not findable by any static technique tried (25th pass) — so the
    lever's LOCK path was confirmed causally instead, by calling it directly

Per §23e's own priority order: item (1), find whatever sets up the byte-opcode dispatch into the
`$010000` table, then item (2), `callcap` the opcode-18/id-144 path and diff the lever's `+15` byte.
Four independent static techniques were tried for (1), all against `gameplay_empire.snap`; all came
back empty or irrelevant. (2) was then done anyway, directly on LOCK's own address rather than
through the (still unfound) dispatcher — which turns out to still answer the question that mattered.

### 24a. Four static searches for "what loads the table's `$010000` base", all negative

1. **Absolute literal scan.** Every occurrence of the 32-bit value `$00010000` anywhere in RAM
   (564 raw hits — almost all noise inside sprite/bitmap mask data, the same false-positive shape
   flagged since §15a), filtered down to only those immediately preceded by a real
   "load this absolute address into an address register" opcode (`lea`/`pea` abs.l, `movea.l #imm`,
   `move.l #imm,Dn` — all eight register-encoded opcode words each): **zero matches.** The table
   base is never materialised via an absolute-long literal anywhere in this image.
2. **PC-relative `lea` scan.** A full whole-RAM instruction decode (same technique as
   `find_ram_callers.py`) for any `lea disp(PC),An` whose resolved target (disassemble.py's ea_str
   already prints the resolved absolute address for this mode) equals `$010000`: **zero matches.**
3. **Opcode-byte-read-and-double pattern scan.** The classic "read one script byte, double it,
   index a word table" prologue (`moveq #0,Dn` / `move.b (A1)+,Dn` / `add.w Dn,Dn`, any single
   register) scanned for as a 3-instruction shape across the whole image: **zero matches.** (Several
   *handlers reached by* the table do read further operand bytes this way — e.g. ids 1/46 — but
   nothing reads the *dispatch* opcode byte this way before indexing `$010000`.)
4. **`(A5)+N` pre-stored base check.** Scanned every `(A5)+N` field (N = 0..4000) for the literal
   longword `$00010000`, on the chance the base lives as data rather than an immediate — 5
   candidates (offsets 1144/1228/2118/2303/2499). `find_field_writers.py` against each shows they're
   all small byte/word counters or 3-bit flag fields (`2499(A5)` in particular is bit-tested/toggled
   with `btst`/`bchg #0/#1/#2` at 32 different sites) — the `$00010000` reading was a coincidental
   4-byte window spanning unrelated neighbouring fields, the same false-positive class as (1)'s
   bitmap-data hits. None of these is a real 32-bit pointer field.

**Aside — `$010076` (the code immediately after the table, previously read in §23a as merely
"confirms the table's own bounds") is a real, distinct routine, but not the dispatcher and not
reachable at all.** Full disassembly shows it reads a 16-bit id via `(A1)+` into `D3`, then
`bsr $10740` — an **internal alternate entry point** into the shared id-resolver at `$010738`
(LOCK's own callee), landed on 8 bytes past the resolver's normal start, i.e. `$010076` supplies its
own already-read id in `D3`/`D1` and skips the resolver's own byte-read prologue. `find_ram_callers.py`
against `$10076` (bsr/jsr/bra/Bcc, whole image): **zero real callers**, and it isn't one of the
59 table targets either (checked against the full id→address list). Whatever calls this exists
outside every static-branch mechanism this tool can see, or it's dead code — not chased further.

### 24b. Whole-block external-caller sweep: the block has 18 real external entry points, none of
    them the opcode dispatcher

Rather than keep guessing how the table's base gets loaded, swept for every real `bsr`/`jsr`/branch
in the whole image whose target lands anywhere in `$010000`-`$011256` (the full verb-interpreter
span §22c/§23a/§14 have mapped), split by whether the *caller* is itself inside or outside that
span. 291 internal calls (handlers calling the shared id-resolver, id-resolve helpers calling each
other, etc. — all already-known shapes, no surprises). **18 external calls**, from `$009b7e`,
`$00a060/66/42e/466/4b4/4ea/508/54e/572/654/6c8/7e8`, `$00f17a/26a/298/ac4`, and one apparent
write-site, `$03c31e: bset D7,$10006.l` (a bit-set landing inside the table's own storage) —
**checked and ruled out**: disassembling the surrounding bytes (`$03c300`-`$03c344`) shows pure
garbage (`ori?`, unresolved line-F opcodes, back-to-back nonsense), the same misaligned-data
false-positive class flagged since §15a/id-26's table entry — `$03c31e` is inside a data region
being decoded as if it were code, not a real instruction, and not a lead.

Disassembled all nine distinct external targets (`$1007e`, `$101d8`, `$10c8c`, `$10aaa`, `$11066`,
`$111e2`, `$1120e`, `$11250`, `$1083e`): every one is a **named, single-purpose utility** already
partly known from earlier passes or newly identified here — `$1007e` (the id-resolver's own
alt-entry, see 24a), `$11250`/`$011256` (the already-documented `RoomIdLookup_ByD2_LinearScan`,
which turns out to itself have a second alt-entry at `$011250` that presets `D3=2` before falling
into the shared body), and several others reading as sound-cue/state-flag helpers. **None of the 18
external callers targets the opcode-byte dispatcher, and none targets any of the 59 known table
entries.** Combined with 24a's four negative searches, this is now a broad, multi-angle negative,
not a narrow miss: whatever normally invokes LOCK/UNLOCK by script opcode has no findable static
call site anywhere in this exact loaded image.

### 24c. Priority-2 done anyway, directly on LOCK's own address — causal proof, independent of the
    unfound dispatcher

Since LOCK's own entry address (`$01049a`) and calling convention (`A1` → 2-byte big-endian id
operand, consumed via `(A1)+` inside the shared resolver at `$010738`) are already fully known from
disassembly (§22c/§23a), the dispatcher didn't need to be found to run this test — only to *invoke
LOCK*, not to prove what invokes it during ordinary play. From `room2_lever_boundary.snap`, live via
the REPL:

```
m 6fa0e 20                        ; before: +15 byte (offset 15) = $01, bit 2 clear
w 18140 00900000                  ; scratch-poke $00 $90 (= 144, big-endian) at $18140,
                                   ;   8 bytes below the live SP ($18152) - safe, unused stack space
callcap 1049a 5000 - A1=18140     ; call LOCK directly with A1 -> the scratch id buffer
```

Result: `--- callcap $01049a: returned ... 14 byte(s) changed ... mem $06fa1d $01->$05 ---` — the
lever's own `+15` byte flips from `$01` to `$05`, i.e. **exactly bit 2 sets**, matching LOCK's own
`bset #2,15(A0)` byte-for-byte (`callcap` restores all memory after reporting the diff, so the live
REPL session itself is untouched by this test — the "before"/"after" `m` dumps read identically
around it by design, the diff line is the actual result). This is the first genuinely **causal**
(not structural/address-match) proof in this whole spike that the LOCK verb, given operand 144,
does flip the exact flag §4/§21b/§22c/§23d have been tracking since the object-classification test
was first written. It proves the mechanism works exactly as read from static disassembly; it does
**not** prove anything in the live game currently calls it that way — §24a/§24b's negative results
stand as a separate, real finding: this path has no static caller in the loaded image.

### 24d. Where this leaves the lever

The two questions from §23e are now: (a) does the LOCK/UNLOCK-on-id-144 mechanism work — **yes,
causally confirmed**; (b) does anything in this game state actually invoke it — **still unknown**,
but now backed by a much broader negative (four independent static techniques plus an 18-site
external-caller sweep, not just "no direct bsr found" as in §22g). This raises, rather than closes,
the possibility that the mechanism is genuinely dormant in this build — vestigial code from an
earlier design (the same class of finding as UNLOCK's own unreachable table slot, §23b) — though
that's not proven either — a data-driven or self-modifying reach hasn't been ruled out, but the one
concrete candidate for that this pass found (`$03c31e`'s apparent table write) turned out to be
misaligned-data noise, not real code (§24b). **Concrete next step**: decode `$00fe84`'s jump table
(§22e, still not done) — the original §22g/§23e fallback, and the one still-open mechanism this pass
didn't need to touch since the direct-`callcap` route answered the causal-proof question on its own.

## 25. `$00fe84` fully decoded (26th pass) — it does NOT connect the ring-304 queue to LOCK/UNLOCK;
    a clean negative, settling the §22e/§22g/§24d fallback

Per §24d's own next step. Static disassembly only, against `gameplay_empire.snap`.

### 25a. Table bounds: 29 entries, same "table then code, boundary = smallest offset" shape as `$010000`

Dumped raw words from `$00fe84` outward, resolving each as `$00fe84 + entry` (the same idiom
`$011728` itself implements — confirmed already in §22e). The first 29 entries (ids 0-28) all
resolve to small, sane, tightly-clustered targets in `$00febe`-`$00ffa2`, every one decoding as
real, coherent code; from id 29 onward the "entries" blow up into wild, implausible offsets
(`$122d`, `$b200`, `$6700`, ...) landing on garbage (`ori?`, unresolved line-F opcodes) — the same
signature as reading past a table's real end into code bytes, not data. The smallest offset among
the 29 real entries is exactly `$003a` (58 decimal = 29 × 2 bytes) → `$00febe`, which is where real
handler code demonstrably resumes (confirmed by disassembling straight through from there with no
decode errors) — an exact structural match for how the `$010000` table's own boundary was confirmed
in §23a. **The table is `$00fe84`-`$00febd`, 29 word-relative entries, ids 0-28.**

### 25b. All 29 handlers are precondition gates (return `D0=0` pass / `D0=-1` fail) against a handful
    of small state fields — not verb-interpreter dispatch targets

Full linear disassembly of `$00febe`-`$00ffa2` (the complete handler-code region all 29 entries land
in). None of it is a jump/call into anything resembling the `$010000`-`$011256` object-verb block;
every handler either returns a constant or compares an operand against one of three small global
fields — `1156(A5)` (word), `1157(A5)` (byte), `1167(A5)` (byte) — or against a byte field pulled
out of a record resolved via the shared id-resolver (`$00c542`, the same routine LOCK/§22d's id
lookup family uses, confirming it's a genuinely shared primitive, not verb-specific):

- ids `0,3,5,6,7,11,14,21,22,25,27,28` (12 of 29) → `$00ff4a`, an unconditional **pass** (`D0=0`).
- id `2` → `$00fee6`, an unconditional **fail** (`D0=-1`); id `8`'s own entry (`$00ffa0`) is the same
  constant-fail code reached as a fallthrough tail from ids 12/13/19/20's own comparison failure, not
  a distinct handler.
- ids `4,26` / `18` / `9` → compare a 16-bit operand against `1156(A5)`, pass on equality (id 9's
  own version additionally passes on the `$ffff` sentinel, `bmi`, before the equality check).
- ids `12,13,19,20` → compare a byte operand directly against `1157(A5)`, pass on equality.
- ids `15,17` → same byte-vs-`1157(A5)` compare, but on a **pass** also does a real mutation:
  `move.l 384(A5),348(A5)` — copies a saved pointer into `348(A5)`, the "self/current actor" slot
  already named in §22d. This is the one handler in the set that changes state rather than just
  gating, but the state it changes is "which entity subsequent opcodes act as," not anything on the
  lever.
- id `10` → a compound two-field gate: operand byte 1 vs `1167(A5)`, operand byte 2 vs `1157(A5)`,
  both must match to pass.
- id `1` → resolves `1156(A5)` via `$c542`, then compares an operand byte against a field of the
  *resolved record itself* (offset computed from the record's own byte `+12`) — the most
  "id-aware" gate in the set, but still a comparison, not a call.
- id `16` → `btst #7,D4; bne skip; bclr #5,3(A0)` — clears bit 5 of whatever object `A0` currently is
  (caller-supplied, not resolved here) unless a flag bit is set; always returns pass. A real
  mutation, but on a bit unrelated to the lever's own `+15` field.
- id `23` → the one handler that does substantive work: resolves an entity via `A0` (already set by
  the caller), reads a per-entity value, conditionally doubles it, accumulates it into a running
  total at `1192(A5)` (a plausible score/inventory-count field), and conditionally queues a sound
  effect (`D0=$21` via `jsr $158f8`, the same sound-cue call site pattern as every other queued sound
  in this image) — reads as a generic "count this and play a chime" event, not object-specific.

**No handler among the 29 references `$06fa0e` (the lever's own record), object id 144, or any
address inside `$010000`-`$011256` anywhere.** This closes the standing §22e/§22g/§24d question
outright: **the ring-304 tagged-record dispatcher (`$fe0c`-`$fe70`) cannot reach LOCK/UNLOCK through
`$00fe84`, under any tag value 0-28** — it's a self-contained precondition/scoring sub-system, not a
bridge into the object-verb interpreter. Opcode/tag `9` (the already-known "touch" event id from
§4a) does have a real handler here (id 9, above) for the first time this spike has traced it past
"gets pushed onto a queue" — but it terminates in a plain pass/fail comparison, not a call anywhere,
so it doesn't reopen §14's already-retracted "opcode 9 triggers pickup scripts" hypothesis, just adds
one concrete data point to it.

### 25c. Where this leaves the lever, with both §24d fallback items now exhausted

Both concrete next steps standing after §24 are now closed: the dispatch-table caller search (§24a/
§24b) and the `$00fe84` decode (§25b above) are both clean negatives, not unfound leads. Combined
with §24c's causal proof that the mechanism itself works correctly when invoked directly, the most
coherent reading left is: **the code that calls LOCK with id 144 is not currently loaded into RAM at
all**, rather than being loaded-but-unreachable. This fits every fact gathered across the whole
spike, not just this pass's own: the type-8 room-registration table has been confirmed empty in
every snapshot since §14/§15/§23c (room 3 was never registered); the 17th pass's
`gfxview.py --contact` scan found 9 palette tables and a 104KB span of resident *graphics* data this
spike has barely sampled, consistent with room *assets* being preloaded from the one-disk image while
room 3's *script/init code* — the thing that would contain a `LOCK 144`-equivalent bytecode sequence
— has not been. If true, no further static search of the currently-loaded image can find this
caller, because it doesn't exist yet; it would only appear once room 3's own data (not just its
graphics) loads, which every portal/transition trace this spike has done (§9/§10/§13) shows has never
actually happened in any snapshot taken so far. **Concrete next step, if this spike is picked up
again**: rather than more caller-graph or literal-scan work in the current snapshot, look for *how*
room 3's own script/code would get loaded at all — i.e. resume the still-open thread from §14's
priority-1 ("what writes into the empty type-8 index table" was answered, §15, as "the save-restore
deserializer, never taken this playthrough") from the opposite direction: what *would* register a
freshly-loaded room during ordinary play (not restore), and why has it never fired even at CAVERN's
own newly-found second door (§13)? That's a broader question than the lever specifically, but it's
the one structural gap left that every dead end in §9-§25 keeps pointing back to.

## 26. Closing the lever-caller thread — a documented negative, not reopened (27th pass)

Thirteen passes (14th-26th) chased "what calls LOCK with object id 144" through four independent
static techniques — absolute-literal scan, PC-relative `lea` scan, opcode-read-pattern scan, and an
18-site whole-block external-caller sweep (§24a/§24b) — plus a full decode of the one remaining
candidate dispatch table, `$00fe84` (§25), all coming back negative, and one causal proof that the
mechanism itself works when called directly (`callcap $01049a`, §24c). The lever's own object (id
144, §23d) is real, its LOCK/UNLOCK flag (`+15` bit 2) is real, and LOCK's opcode id (18) is real —
nothing in the currently-loaded image calls it. The most coherent reading, given every fact gathered
across this whole thread (the type-8 room-registration table is confirmed empty in every snapshot,
§14/§15/§23c; the 17th pass's palette-table find shows room *assets* preloading from the one-disk
image while room 3's own *script/init code* has never been shown to load, §13/§25c), is that **the
calling code is simply not resident in RAM in any snapshot this spike has taken** — not a decode
failure, a missed dispatch site, or a dormant/vestigial mechanism. Closed here as a documented
negative, not reopened by this pass's consolidation work. The one remaining structural question —
what would register a freshly-loaded room during ordinary play, and why it never fires even at
CAVERN's own second door (§13) — stays queued as the README's own next concrete step, not chased in
this doc-only pass.

## 27. Consolidated room/level-encoding reference (27th pass)

Pulls together the room/object/portal/resource-table facts already found and cited across §3, §4,
§10b/§10c, §13, §15b, and §23c/§23d into one schema-style reference, instead of leaving them spread
across separate changelog entries. This is consolidation, not new reversing — every fact below cites
back to the section it was originally derived in.

### 27a. Room extent (collision boundary)

- Outer bounding rectangle: `RoomMaxX`/`RoomMaxY`/`FloorClampX`/`FloorClampY` (globals `2238`/`2239`/
  `2204`/`2203`) and `RoomMinX`/`RoomMinY` (`2217`/`2218`) — §3.
- Optional per-room refinement: `(A5)+140`, if non-null, points at 4 quadrant-cutout rectangles
  (globals `2222`-`2237`, 4 fields each) selected via `jmp (A0)` — an outer box with up to 4 corner
  cutouts, for irregular hand-painted rooms with no tile grid (§3, `graphics.md` §2). Null pointer =
  plain rectangle. Which quadrant maps to which physical corner, and what selects the pointer per
  room, is still open (§6).
- A footprint failing the extent test falls through to the edge/portal check (27c).

### 27b. Live object array (in-room collision + interactive classification)

- `SpriteObjectArrayPtr_A5Plus56` / `SpriteObjectArrayCount_A5Plus1152`, stride `$46` (70 bytes) —
  §4, `graphics.md` §3.
- Per-entry fields relevant here: bytes 0-3 = bbox (x_min,y_min,x_max,y_max), bytes 4-5 = z_min/z_max
  (doubles as an id/kind pair), byte 24's top bit = classification candidate, `+10` = pointer to the
  object's own type-6 resource record (27d), whose `+15` bit 2 is the LOCK/UNLOCK state.
- Classification rule (§4): AABB+Z overlap **and** `byte24<0` **and** the linked record's `+15` bit 2
  set → `$FD` ("touched an interactive/pickup object"); otherwise a plain scenery block. (TUNNEL's
  lever fails this today only on the `+15` half, per §21/§22c — see §26.)
- Touch dedup: a 64-entry ring cache at `(A5)+512`/count `(A5)+2146` (§4a), keyed on a packed id-pair;
  a genuinely new touch queues opcode `$9` onto the shared `(A5)+304` sound/event ring (the same ring
  the object-verb interpreter's own event pushes use, `ai.md` §6).

### 27c. Portal/edge table (room transitions)

- A second, separate object table: `(A5)+88` (`PortalTablePtr_A5Plus88`) / `(A5)+1162`
  (`PortalTableCount`), same 70-byte stride as 27b, but a threshold/edge test rather than AABB
  containment (§10a) — `byte0`/`byte2` and `byte1`/`byte3` are independent threshold lines the
  mover's footprint must straddle in the movement direction, with a diagonal-corner allowance
  swapping which pair is checked (`btst #0/#1,2243(A5)`).
- Match: `D0=-2`, `entry.+10` = door-descriptor pointer, `entry.+26` word → `(A5)+1184` ("pending room
  target"). No match: `D0=$FF` (hard wall, no exit).
- Door descriptor (`entry.+10`'s target, 20 bytes — §10c/§14): `+2` word = target room id, with two
  special sentinels — `$0000` = "current room" (self-loop path, skips the real room-resolve chain)
  and `$ffff` = "no room, sound/event cue only" (pushes a ring-304 opcode, no geometry/room-load call
  at all). A real positive id runs the full chain: `$de5e` (nearest-free-entry-tile search) →
  `$e854`/`$e84a` (ring-304 push + `2271(A5)` block-flag, both the same routine — `$e84a` just
  presets the flag to `$ff` first) → conditionally `$defa` (a ring-304 opcode-`$8` push, itself *not*
  the loader — the real disk-read consumer for that opcode is still unlocated).
- Per-room source data: the current room's own record (pointed to by `(A5)+164`) holds 7 door-link
  slots at `+6..+19` (2 bytes each, `$ffff`=unused) drawn from a **global, sequential door-id
  namespace** shared across every room — this seeds the live portal table's `+26` words at room-load
  (§14).
- Two confirmed live examples: TUNNEL's 2-entry table (§10b — one real CAVERN-linked door, one
  sound-cue-only entry with target `$ffff`); CAVERN's 2-entry table (§13 — the same shared
  CAVERN↔TUNNEL descriptor as entry 0, plus a second, previously-undiscovered east-wall door to
  target room id `$49` whose live transition resolves to the "already resident" branch, not a new
  load).

### 27d. Master resource-table system (types 6/8/9 — objects/rooms/creatures)

- `(A5)+96` → a 10-row array (one row per resource type 0-9), 18 bytes/row: `{+0: index-table ptr,
  +4: data-base ptr, +8..+15: unknown, +16: count}` (§14/§15b). Rows are initialized once at boot by
  `$00c696` from a fixed 10-entry table at `$57c8`.
- Index table: sparse, 4-byte slots, a `$0000` leading word = empty. `$00c628`/`$00c660` scan
  forward/backward for the next populated slot from a given index — a "find next," not a keyed
  lookup; id-keyed callers (e.g. `$011256`) wrap this in their own compare-and-reloop. A populated
  slot's own `+2` word, added to the row's data-base, gives the record address.
- Confirmed live population, `gameplay_empire.snap` (§23c):

  | type | role | index ptr | data base | count | populated |
  |---|---|---|---|---|---|
  | 6 | objects | `$0004b596` | `$0006eb92` | 1000 | 1000/1000 |
  | 8 | rooms | `$0004c536` | `$0007550a` | 64 | 0 (never registered in any snapshot) |
  | 9 | creatures | `$0004c636` | `$0007560a` | 10 | 0 (no live creature found yet) |

- Type 8's index table has no known writer anywhere in the currently-loaded image other than the
  save-restore deserializer (`$00c9ee`, gated behind a boot-menu branch this spike has never taken,
  §15) — this is the mechanical reason every room transition in this spike resolves to a hardcoded or
  already-linked room rather than a freshly-registered one.
- Type 6 records are what the object-verb interpreter (`ai.md` §6) resolves LOCK/UNLOCK/etc. operands
  against, by 16-bit id — confirmed live for the lever specifically: id 144 → record `$0006fa0e`, the
  exact same address the live object array's own `+10` field points to (§23d), whose `+15` byte is
  the classification flag from 27b.

## 28. The flag-poll hypothesis tested live and closed; both fallback leads from §25c also closed —
    reframes the whole LOCK(144) thread as the wrong mechanism, not an unreached one (28th pass)

Tests §25c/§26's own two remaining fallbacks, per the resume point's own priority order, plus a
direct live test of a gap those passes themselves identified: every prior test of the LOCK
mechanism used `callcap`, which **reverts memory after reporting its diff** — nothing in this whole
spike had ever left the `+15` flag set and kept driving the game to see if anything reacts to it.

### 28a. Priority 1 — held the flag set for real, live, and nothing reacted (closes the "something
    polls it" hypothesis)

From `room2_lever_boundary.snap`, poked `$06fa1d` (object 144's own `+15` byte) from `$01` to `$05`
with a real `w`-write, not `callcap` — `w 6fa1c 22051285` (a longword-aligned write at `$06fa1c`,
preserving the three neighbouring bytes `$22`/`$12`/`$85` and changing only the target byte, since
`$06fa1d` is odd and the REPL's `w` command writes a longword via `MMU.WriteWord`, which raises an
address error on an odd address — `MMU.fs:996` — so a direct `w 6fa1d ...` is not possible). Ran
5,000,000 steps forward from there with no other input (the player was already positioned at the
lever boundary from the snapshot itself). Re-checked all three markers the resume point named,
before and after:

- **Object 144's own flag**: still `$05` after 5M steps (`22 05 12 85` at `$06fa1c`) — the poke
  held, not reverted by anything.
- **`RoomLoadQueuedFlag_A5Plus2142`** (`$189b0`): unchanged (`00 00 00 32` both times); also live
  `watch`ed for the whole run — zero writes landed there at all.
- **`DoorFacingOrBlockedFlag_A5Plus2271`** (`$18a31`): unchanged (`$01`, same byte, both times).
- **TUNNEL's live portal table** (`$037e48`, both 70-byte entries, 140 bytes total): byte-for-byte
  identical before and after.

**Completely inert.** This isn't a new finding in isolation — it's consistent with, and closes the
gap in, §21c's already-established static finding that genuine AABB overlap with this object is
unreachable by ordinary movement (§20b: hard-blocked, zero clearance, on both sides facing it), so
the classification/touch code that would ever read this flag never executes for this object at all.
What this pass adds is the missing live half: holding the flag set for real, for millions of steps,
also rules out any mechanism *outside* that collision path polling it in the background. Between
the two, "does anything react to this specific flag, ever, under any condition this spike can drive
to" is now a closed negative, not an inferred one.

### 28b. Priority 2a/2b — both already closed by the 18th pass; re-run confirms it, finds nothing new

`find_field_writers.py room2_lever_boundary.snap "2142(A5)"` (28 hits, all instructions in the
whole loaded image referencing that field) filtered to the literal value `2` specifically finds
exactly one site: `$007310: move.w #$2,2142(A5)`. This is not a new discovery — §18c already named
this exact address as "the CAVERN/TUNNEL-door call site" while establishing that `2142(A5)` is a
shared "which name to show" message-index register written by over a dozen unrelated routines with
a couple of dozen different literal values, not a single-purpose room-load flag. Re-running the
filtered search this pass confirms there is exactly one literal-`2` writer in the whole image, and
it's the one already accounted for — no new lead. §18b/§18e's own finding (`$defa` is a
name-banner/message-box display trigger, never gets near disk I/O, and no code path anywhere in
this whole spike performs raw sector/FDC-level disk I/O for a room) stands, re-confirmed rather than
re-derived.

### 28c. Priority 2c — disassembled the "already resident" branch in full for the first time; it's
    the game's own main loop, not a room-transition routine, and hides no copy/decompress step

Every prior pass characterized `$69da` ("the already resident branch... just updates state and
returns to the main loop") from register/flag behavior around a portal match, never from reading it
directly. Disassembled it this pass (`disassemble.py --snap room2_lever_boundary.snap --linear
69da 90`): it opens with `jsr $11898` (a VBL-wait/frame-sync call) followed by a long run of
per-frame housekeeping — clearing/incrementing dozens of `(A5)+N` byte fields (animation counters,
debounce timers, `2202(A5)`, `2480(A5)`, `2519(A5)`, etc.) and `jsr`ing out to half a dozen other
small routines (`$e1fa`, `$af10`, `$dde8`, `$d78a`, `$14a90`, `$ebaa`). **`$69da` is the game's own
main-loop re-entry point, not a room-transition-specific routine** — confirmed directly, not
inferred: `room2_lever_boundary.snap`'s own resume PC (`$6b76`) sits inside this exact instruction
range. There is no decompression or table-copy step hiding in "already resident" handling — it
falls straight through to ordinary per-frame housekeeping, exactly as §13 originally read it from
register behavior, now confirmed from the actual instructions. This specific hypothesis (a
decompress/unpack step disguised as generic state update) is closed as a negative; the broader
question — where room 3's own init/unpack code would actually live, if not here — is still open.

### 28d. The reframe: LOCK(144) is very likely the wrong mechanism entirely, not a real-but-unreached
    one — and that changes what the next pass should try

§13's own retraction (17th pass) already carries user-supplied external ground truth: pulling
TUNNEL's lever really does open a door to room 3 in the real game, on this exact one-disk Empire
file. Fourteen passes (14th-27th) exhaustively searched for what calls LOCK on object 144 and found
nothing; this pass held the flag set live for 5M steps and found nothing reacts to it either. Taken
together with §21c's double negative (the object was never classified interactive to begin with,
*and* genuine touch is unreachable by ordinary movement), the weight of evidence now points past
"the caller isn't resident" (§25c/§26's reading) toward a stronger conclusion: **LOCK(144)/the
`+15` bit-2 flag is probably not the door's real trigger mechanism at all** — a wrong hypothesis
this spike has been chasing since the 23rd pass's own opcode-ID match made it look like the obvious
candidate, not a dormant-but-real one. The concrete puzzle this leaves for whoever picks the spike
up next: the real game's lever-pull genuinely works, but every tested approach to the object's own
bbox is hard-blocked before reaching genuine overlap (§20b) — either the collision/interaction model
this spike has mapped (§4/§27b, AABB-overlap-gated) isn't actually what governs a "pull" verb at
all, or the reachable position tested (Left, walked flush from `room2_tunnel_entry.snap`) isn't the
real trigger tile, or there's a still-uncharacterized input verb distinct from the generic interact
gesture already exhausted (§13, §20d). Not chased further this pass — flagged here as the priority
reframe for the 29th pass, ahead of any further LOCK-specific work.

## 29. Priority 1 re-examined live from a genuinely different approach route — still a real wall, not
    a Left-only artefact; priorities 2/3 closed too (29th pass)

Per `next_session.md`'s own priority order, following the 28th pass's reframe (§28d): stop chasing
LOCK(144)'s caller and instead re-examine whether "hard-blocked, zero clearance" (§20b) is a real
wall or an artefact of the one approach route (walking Left from `room2_tunnel_entry.snap`) this
spike has always used.

### 29a. Priority 1 — a genuinely new route (Down×3 then Left×3 from the room entry, not from the
    boundary tile) reaches a different boundary tile on the object's *south* side; still exactly
    1 unit short, still a hard wall, still inert to interact

From `room2_tunnel_entry.snap`'s own start position (`x14-20,y6-12` — confirmed live, six units
right of `room2_lever_boundary.snap`'s `x8-14,y6-12`, i.e. exactly the 13th pass's own Left-walk
distance), drove **Down first** (three settled `kbd ff 02` packets, ≥90,000 steps each, §20a's own
methodology) before ever pressing Left, reaching `y17-23` — well past the object's own `y12-15`
band, the opposite side from every prior approach. Then **Left** from there: two settled packets
move cleanly (`x20→x13→x7`), a third produces **zero movement** at `x6-12,y17-23` — a new hard
block, one unit right of the object's own `x_min=5`, not the same tile any prior pass has stood on.
**Up** from this new tile moves one unit (`y17-23→y16-22`) then also hard-blocks (zero movement on
a second Up packet) — the player is now wedged at `x6-12,y16-22`, one unit *below* the object's own
`y_max=15`, with its `x_min=6` already inside the object's own `x5-7` span. This is the mirror
image of §20b's finding (there: y-adjacent/touching, x off by 1; here: x-overlapping, y off by 1) —
**the same "exactly one unit of clearance, never true overlap" behaviour reproduces from a route
that never uses the original Left-approach corridor at all**, closing the "is the wall an artefact
of one route" question as no, confirmed from a second, independent direction.

Interact (`kbd 50`/`kbd d0`) retried from this new south tile, watching the lever's own `+15` byte
(`$06fa1d`) and TUNNEL's live portal table/count directly: **byte-for-byte identical before and
after** — inert here too, matching every prior tile tested. Snapshot committed:
`room2_lever_south_boundary.snap`.

### 29b. Priority 1, cont. — true diagonal packets (not sequential axis moves) tested at both
    corners; both fully blocked, no diagonal-squeeze past the 1-unit gap

Tried a genuine simultaneous diagonal joystick packet (both direction bits in one `kbd` byte, not
two sequential single-axis moves) at both boundary tiles, since a corner gap that blocks each axis
individually sometimes still admits a diagonal move in engines that only collision-test one axis at
a time:

- From the new south tile (`x6-12,y16-22`), toward the object (up-left, `kbd ff 05`): **zero
  movement**, twice.
- From the original NE tile (`room2_lever_boundary.snap`, `x8-14,y6-12`), toward the object
  (down-left, `kbd ff 06`): **zero movement**, twice.

No diagonal squeeze either way. Combined with §29a, three independent approach vectors (NE
straight-line, S straight-line, and true diagonals from both corners) all produce the identical
"one unit short, hard wall" result. **Priority 1's own question is answered: this is a real
collision wall around the object, not a single-route artefact** — the object's own live bbox
(`x5-7,y12-15`) is genuinely unreachable by ordinary movement from any direction or combination
this spike can generate, not just the one the 13th pass happened to use first.

### 29c. Priority 2 — not live-tested; §17c already answers it analytically, and re-running it would
    cost ~60M+ steps to reconfirm a already-derived certainty, not test a new hypothesis

`next_session.md` asked for the save→reboot→restore test as untried; re-checking the 19th pass's
own findings first (§17/§17c) shows it was already retired, for a stronger reason than "not yet
tried": `$00b6e0` (SAVE-serialize)'s **only** caller in the whole loaded image is a boot-menu
dispatch block with **zero external callers of its own** (§17a — confirmed by `find_ram_callers.py`
on both `$b6e0` and its own caller `$b5a8`) — there is no player-reachable hotkey that invokes it at
all, only an automatic run once at the very start of every boot, before any room has ever loaded,
always against an empty type-8 table (§17b, confirmed live in three existing snapshots). Choosing
"restore" instead of "ESC" at the boot menu would deserialize whatever a `"CAD "`-headed save buffer
holds — but the only code that ever *writes* that buffer runs before type 8 has anything in it, so
the buffer's own type-8 payload is empty by construction regardless of which menu branch runs after
it. Re-running this live would only reconfirm §17c's own conclusion at the cost of a fresh cold
boot (§17c's own data point: a `u b6e0 60000000` run-to-address from cold boot didn't even leave TOS
ROM in 60,000,000 steps) — not worth spending this pass's step budget on a result already derived
from two independent whole-image caller sweeps. **Genuinely still open, not closed by this
reasoning**: whether the in-memory `"CAD "` buffer ever reaches a real disk sector at all (§17c's
own flagged loose end) — but even a real on-disk save from an *earlier* session would need that
earlier session to have registered a room into type 8 while playing, which nothing in the currently
understood code does either. Not chased further this pass.

### 29d. Priority 3 — the 6 alias action ids, each driven through the real IKBD pipeline for the
    first time (not the hand-write shortcut); completely inert, closing this as a live negative

The 9th pass's own callcap/hand-write sweep (README "9th pass, cont.") proved that installing an
action id's script pointer by hand is **not** equivalent to a real keypress for at least one
known-good case (Down/101) — the real IKBD dispatch path does something beyond the `$15bf4` install
that a memory write doesn't reproduce. That gap meant the 6 *alias* ids (`127/129/158/159/188/198`,
`ai.md`-adjacent `KeyDispatchTable` values `$7f/$81/$9e/$9f/$bc/$c6`) had only ever been
"tested" by table-structure inspection (all pointing at the same `$16fe4` no-op script) or by the
hand-write method the 9th pass itself flagged as unreliable — never by a real bound key through the
real pipeline, and never at the lever specifically. Re-dumped the live 61-entry `KeyDispatchTable`
(`m 1616d 305`) from `room2_lever_boundary.snap` to find one real scancode per alias id (`$15`→127,
`$3a`→129, `$23`→158, `$42`→159, `$3c`→188, `$24`→198 — matches the 9th/12th-pass id lists exactly,
confirming the table is unchanged), then drove each through `kbd <make>`/`kbd <break>` (500k-step
settle before, 1M-step hold after, mirroring the 9th pass's own per-id discipline) from the lever
boundary tile, checking the player's own bbox, the lever's `+15` byte, and TUNNEL's portal table
after each. **All 6 are completely inert** — zero bbox change, zero flag change, zero portal-table
change, every time. Combined with the already-exhausted 12 real ids (9th pass) and the basic
interact/fire/space sweep (13th pass), **every action id this game's dispatch table can produce, for
every scancode that reaches one, has now been driven through the real input pipeline at the lever
specifically, with no effect** — this thread is now exhausted, not just structurally implied.

**Not attempted this pass**: priority 3's other half (retest with the pickaxe held at the lever
boundary) — the navigation cost from `axe_touch.snap` (CAVERN) through to TUNNEL's lever is
unexplored and the 21st pass already carries direct user ground truth that the lever needs no item,
only the interact action, making a null result the likely outcome. Flagged for whoever picks this
up next rather than spent on this pass's own budget.

### 29e. Where this leaves the spike

Every concrete lead `next_session.md` listed for this pass is now closed: priority 1 (route
artefact) — no, confirmed from three independent vectors; priority 2 (save/restore) — already
analytically closed by the 19th pass, re-confirmed rather than re-run; priority 3 (alias ids) —
closed live. The one item genuinely left untried is the pickaxe-at-the-lever retest (§29d), already
flagged as low-value by the spike's own user-supplied ground truth. With the LOCK(144)-caller
thread also closed (§28) and every input class/position/action-id combination this spike can
generate now exhausted against the lever specifically, **the honest state of play is that this
spike's whole toolset (REPL-driven movement, the full interact/fire/keyboard action space, and
every reachable tile including corners and diagonals) has been exhausted against this specific
puzzle** — any further progress most likely needs either the still-undecoded `$defa`/room-3-load
path (§28c's own open half), or accepting that this door's real trigger lives in code this
playthrough's RAM image has never loaded at all (consistent with §27d's finding that room 3's own
init/script data, unlike CAVERN/TUNNEL's, has never been shown resident).

## 30. `$defa`/room-3-load path closed for good — this loaded image contains no disk-I/O-capable code
    at all, by any mechanism; and the working tree turns out to hold the two-disk original alongside
    the one-disk crack this whole spike has used (30th pass)

Per `next_session.md`'s own recommendation, following §28d/§29e: rather than another live-driving
pass, statically settle §28c's own open half — where would room 3's init/unpack code actually live,
if anywhere, in this loaded image.

### 30a. Whole-image sweep for raw FDC/DMA hardware I/O — zero hits, closing the question completely

§18 (20th pass) already fully disassembled opcode `$8`'s consumer chain and found "zero trap/FDC
instructions anywhere in the whole call tree" — but that was scoped to one call chain (the ring-304
opcode-`$8` consumer reached from `$defa`), not the whole loaded program. This pass extended the
same question to every instruction in the whole image: a real 68000 loader that bypasses TOS (as
the README's own GEMDOS trace already showed this game does — 2 GEMDOS calls total pre-restore-
prompt, no `Fread`) has no way to read a disk sector except by directly poking the ST's FDC/DMA
hardware registers. Addresses transcribed from `hatari/src/fdc.c` (not recalled): `$ff8604` (FDC
data/status, shared with DMA sector count), `$ff8606` (DMA mode control/status), `$ff8609`/
`$ff860b`/`$ff860d` (DMA base-address high/mid/low bytes, `FDC_WriteDMAAddress`), `$ff860a`/
`$ff860e` (density/side select region). `find_field_writers.py gameplay_empire.snap` against each
of the 7 addresses, scanning every decoded instruction in the whole live RAM image: **zero hits,
for every one of the 7**.

Combined with the already-established facts — no GEMDOS `Fread` (README §"raw disk sectors"
finding), and `$defa`/opcode-`$8`'s own consumer chain confirmed to be a name-banner display with no
trap/FDC instructions anywhere in it (§18b/§18e) — this closes the question at the whole-image
level, not just one call chain's: **no code anywhere in this loaded one-disk executable can perform
disk I/O by any mechanism** — not TOS file I/O, not XBIOS `Floprd`/`Flopwr`, not a raw FDC/DMA
register poke. `$defa` cannot ever load room 3's data, structurally, not because the right trigger
hasn't been found yet.

This finally answers §28c's own open question ("where would room 3's own init/unpack code actually
live, if not [in `$69da`'s main-loop housekeeping]") — **nowhere, in this specific loaded image**:
it contains no disk-I/O-capable code path at all, so room 3's script/init data cannot become
resident during ordinary play regardless of how exhaustively the caller-search or the live
input/route/action-id space (§20-§29) gets searched. The structural gap §27d/§28c/§28d kept pointing
at is now a proven property of this image, not an unlucky playthrough.

### 30b. New discovery, orthogonal to the disassembly sweep — the two-disk Image Works original sits
    in the working tree, untracked, alongside the one-disk Empire crack this whole spike has used

While locating the disk image for the sweep above, the working tree's `Cadaver/` directory (untracked
per `git status`) turned out to already hold both releases, not just the one-disk crack this spike
has used since the 13th pass:

- `Cadaver (1990)(Image Works)[cr Empire][one disk].st` — this spike's own image, 819,200 bytes.
- `Cadaver (1990)(Image Works)(M3)(Disk 1 of 2)[cr Empire][t].st` (inside its `.zip`) — 819,200 bytes.
- `Cadaver (1990)(Image Works)(M3)(Disk 2 of 2)(Level)[cr Empire][t].st` (inside its `.zip`) — 819,200
  bytes, explicitly labelled **"(Level)"**.

The one-disk release is exactly the same size as *each* disk of the two-disk set — it is not simply
"disk 1 with room 3's data stripped out," it's a distinct, independently-sized single-disk image.
Disk 2's own "(Level)" label strongly suggests the two-disk original keeps at least some room/level
data off the boot disk entirely, loaded via a real mid-game disk swap — exactly the kind of resident
data this pass's §30a sweep shows the one-disk crack's own code can never reach, because it has no
disk-I/O path at all. This may mean the one-disk crack is missing room 3 (and whatever else lived on
disk 2) entirely, rather than gating it behind an unfound trigger.

The emulator already has hot-swap support for exactly this (`disk <path>` REPL command →
`MMU.LoadDiskA`, "models a real physical floppy swap ... without needing a fresh cold boot" —
`Program.fs`), so booting the two-disk original and following it to wherever it prompts for disk 2
is mechanically possible with existing tooling. But it is a materially different undertaking from
this pass's static chase, not a continuation of it: a fresh boot-to-gameplay drive on a different
image, needing its own wall-fixing/boot-trace pass (reversing skill §1-2) before any of this spike's
TUNNEL-lever-specific snapshots, collision findings, or resource-table addresses can be assumed to
carry over — save states and live struct layouts are not guaranteed binary-identical between the two
releases. **Not attempted this pass** — flagged as a new scope decision for whoever picks this up
next, not decided here.

### 30c. Where this leaves the spike

With §30a's whole-image sweep closing the `$defa`/room-3-load question completely, **every concrete
lead this spike has ever queued for the one-disk Empire crack is now exhausted**: the input/route/
action-id space (§20-§29), the LOCK(144)-caller search (§14-§28), and now the disk-I/O question
(§30a) are all closed negatives. The only way forward on this puzzle specifically is the two-disk
pivot (§30b) — a new investigation, not another pass over the same image.

## 31. Correction, same session — type 8 was the wrong resource type all along; type 3 is the real,
    populated room table (72/100 slots), vindicating the user's own ground truth that this one-disk
    image has many visitable rooms; a live room-switch hack gets object/sprite state working but not
    yet the on-screen background (31st pass)

The user, on reading §30's "room 3 can never become resident" conclusion, gave direct ground truth
that contradicts its premise: **the one-disk version has many rooms, and they have personally
visited them** — no disk swap involved. That sent this pass back to find what §14-§30 got wrong,
rather than treating §30a's disk-I/O finding as the last word.

### 31a. Type 3, not type 8, is the real room table — dumped live, 72/100 slots populated

`(A5)+96` row 3 (`idx_ptr=$4ac36`, `data_base=$6bf0a`, `count=100`) — its `data_base` is **exactly**
CAVERN's own known room-record address (§14). Dumping the sparse index table directly: **72 of 100
slots are populated**, not 0. Slot 0 resolves to `$6bf0a` (CAVERN) and slot 1 to `$6bf84` (TUNNEL) —
both already-known addresses, confirmed exactly. A companion byte-level scan of the low-entropy
`$6b800`-`$6cc00` span for the room-record signature (7 door-link words, `FloorClampX/Y` bytes in
range) independently finds ~54 more real, distinct, resident room records in the same span, entirely
consistent with type 3's own count. **Type 8 (rooms, per §14/§15/§23c/§27d) was simply the wrong
resource type** — everything this spike built on "type 8 = rooms, always empty, therefore room 3
can never load" (§15, §17-§19, §23c, §25c, §26, §27d, §28d, §30a) used the wrong table. What type 8
actually is remains unknown and is no longer assumed to be rooms; it is not touched by anything in
this section.

This fully vindicates the user: the one-disk image genuinely has dozens of rooms, all already
resident (consistent with, not contradicting, §30a's "no disk I/O anywhere" finding — nothing needs
to be loaded because everything is already there from the initial `Pexec`).

### 31b. Re-reading `$007104` fresh confirms it still isn't how ordinary rooms connect — both its
    branches converge on the same `$69da` re-entry regardless of outcome

Disassembling `$007104` fresh past where §9/§10c's own summaries stopped (`$7104`-`$7360`, this pass,
not trusting the prior paraphrase): confirms `jsr $11256.l` really is the call at `$718e` (type 8,
not type 3 — §30a's own disassembly of `$011256` itself, hardcoding `moveq #8,D0`, stands). But
tracing to the end of the routine: **the "already resident" (`D3==0`) branch and the "real target
id, `$011256` succeeds" branch both end in `bra $69da`** (`$730c`/`$731a`) — the only difference
between them is whether `bsr $defa` (the name-banner push, §18) fires first. There is no branch
anywhere in `$007104` that does anything visually different for a "genuinely new room" versus
"already resident" beyond a banner message. This independently reinforces §28d/§30a's own
conclusion from a different angle: whatever mechanism actually switches the ~72 real rooms into and
out of view during ordinary play, it is not `$007104`/`$011256`/type 8 at all — that whole chain is
real code, but not the one connecting this game's real room graph.

### 31c. The real room-activation routine, found and partially exercised live — object/sprite state
    switches cleanly to a foreign room, but the on-screen background does not (yet)

`find_field_writers.py` against `164(A5)` (the current-room pointer) surfaces exactly two writers:
`$00e818` (inside `$00e80c`, hardcoded `D1=0` — the boot-time "activate type-3 slot 0" call) and
`$00e95c` (inside a shared tail reached from the same body, `$00e958`-`$00e9xx`). `$00e854` (already
named in §10c/§27c as "`QueueEntityIntoRing304_AndSetField2271_Direct`", based on an incomplete read)
turns out to be the entry into this same activation body used by `$007104`'s own `jsr $e854` — but
is its own subroutine with its own `rts`, not simply falling through into the `$e958`+ tail.

Live-tested via `callcap e854 A0=<foreign room record>` (the 72-room scan's slot 5, `$6c052`, chosen
arbitrarily as "a real room that isn't CAVERN/TUNNEL"): **493 bytes changed, no crash** — a real
rebuild of the sprite/object-array region (`$038338`+, hundreds of bytes cleared/reset) plus a large
scratch region at negative `A5` offsets (`$0180aa`-`$0189xx`, not previously documented — outside
every known-positive-offset global this spike has mapped). Replaying that exact diff onto a real
(non-reverted) copy of `gameplay_empire.snap`, forcing `164(A5)` to `$6c052` directly (the one field
`$e854` itself doesn't touch), and stepping the result forward 2,000,000 real steps: **stable, no
crash, `164(A5)` holds** — but `snap_render.py` on the result is **byte-identical to the unmodified
CAVERN reference**, and the status bar still reads "CAVERN". Object/sprite bookkeeping now points at
a different room; the screen does not.

Chasing the missing piece: `$00e7b0` (called from the same body, right after `$e95c`'s `164(A5)`
write, via `bsr $e7b0`/`bsr $ccd4`) reads the *current* room record's bytes `+4`/`+5`, indexes a table
at `$5a10.l` (`(byte4-3)*2 + (byte5-3)*16`), and writes the result into `(A5)+148` plus a longer
associated table at `$018b9c`+ — this looks like the real "select this room's background/quadrant
graphics" step §27a flagged as "not located" (`(A5)+140`'s own selector). `callcap e7b0` from the
already-164(A5)-hacked state: 62 bytes changed, register `A0` ends at `$019100` — the exact screen
base address `snap_render.py` reports for the ordinary CAVERN render. Replaying this diff too, on top
of the first hack, stepping forward again: **still no visible change** — the background bitmap and
room-name text are still CAVERN's. `$e7b0` writes graphics *offset/scaling metadata*, not the
background bitmap source itself; whatever actually triggers a redraw of the background bitmap from
a room's own asset data hasn't been found yet.

**Not chased further this pass** — the concrete next step for whoever picks this up: find what
writes the physical screen buffer's background layer (`graphics.md`'s own compositing pipeline, not
yet cross-referenced against this pass's findings) and what triggers it for a room switch — most
likely gated on `2271(A5)` (already known to distinguish "already resident" from "genuinely new" in
`$e854`'s own body, per the `tst.b 2271(A5)` branches at `$e8bc`/`$e970`/`$e990` this pass's read
passed through without fully tracing every arm) or reached only via `$e80c`'s own boot-time call
shape rather than a bare `$e854` call. Room-record bytes `+0..+3` (still "unknown per-room fields"
per §14) are a good next place to look — `+4`/`+5` are now known (quadrant/graphics-table index);
`+0..+3` may hold the actual background-asset id or pointer.

Scratch snapshots from this pass (`room_hack_test.snap`, `room_hack_test2.snap`, `*_stepped.snap`)
and renders (`room_hack_test.png`, `room_hack_stepped.png`, `room_hack_test2.png`,
`gameplay_empire_reference.png`) are untracked, kept for the next pass to resume from rather than
committed.

### 31d. `$00ccd4` found and exercised too — real per-room object repopulation (types 5/6), still not
    the background; and a structural reframe of what CAVERN→TUNNEL actually is

Continuing the same body: `$e968`'s third call, `bsr $ccd4`, disassembled and callcapped from the
already-hacked state. It re-clears the same sprite/object-array region `$e854` touches (`$00ccfe`:
zero a `68(A5)`-based buffer, then re-initialize `56(A5)`'s 70-byte-stride array with default/
sentinel fields — 95 entries), then (`$00cd50`) reads **the current room record's own bytes 4 and 29**
(byte 4 is the same field `$e7b0`'s quadrant-table lookup uses) and fetches a **type-5** resource
(`bsr $c5a8`, `D0=5` — a resource type never referenced anywhere else in this spike) keyed by
`1166(A5)`, then a second, **type-6** (objects) fetch, populating the live object array from both.
This is real, working, room-specific object repopulation — but `callcap ccd4` from the hacked state
still shows **zero writes inside the back-buffer address range** (`(A5)+120` = `$02de08`, confirmed
identical in both a fresh CAVERN snapshot and the real, live `room2_tunnel_entry.snap` — one shared
scratch buffer, not per-room). The background draw is in none of `$e854`, `$e7b0`, or `$ccd4`.

**A more useful finding came from re-examining what `$71ca` (the `D3==0` "current room" branch,
§9/§10c) actually does, now that its full body has been read fresh this session (§31b)**: it never
touches `164(A5)`, the back buffer, or the portal table — it only recomputes the player's *position*
from the door descriptor's own entry-offset bytes, using whatever `164(A5)` **already** points to.
Yet CAVERN→TUNNEL is a confirmed, real, visually-different transition (`room2_tunnel_entry.snap`,
12th pass) that goes through exactly this branch on **both rooms' own copies of the same shared door
descriptor** (§10b/§13: CAVERN's own portal entry for this door also resolves to `$6d4ea`, `+2`
word `$0000`). Since the "current room" sentinel demonstrably does not mean "stay in this room" (it
demonstrably doesn't, empirically) and does not fetch a new room record either, the more consistent
reading is that **CAVERN and TUNNEL are not two separate "rooms" being switched between at all** —
`$71ca` reads as a plain **screen-edge scroll/reposition within one continuous, larger playfield**
that happens to be hand-painted to look like two distinct scenes, not a room-load boundary. This
would mean type 3's 72 entries are not "the 72 walkable rooms this spike has been assuming" but a
coarser unit (levels/chapters, or something else) — and it would mean this pass's whole room-hack
methodology (forcing `164(A5)` to a different type-3 slot and replaying `$e854`/`$e7b0`/`$ccd4`'s
own effects) was testing the wrong kind of transition for "walking to a new screen," which might
explain why none of the three routines touch the background even though all three genuinely run.
**Not confirmed** — this is a structural reframe from re-reading known-good disassembly plus one
consistent absence-of-evidence (no back-buffer write in three separate real routines), not a new
positive test. The concrete way to settle it: `watch` the back-buffer range (`$02de08`, `$7d00`
bytes) live across an *actual* CAVERN→TUNNEL crossing (walk backward from `room2_tunnel_entry.snap`
toward the shared door) — if nothing writes it during a transition already known to change what's on
screen, background changes happen by some other confirmed-real means (e.g. per-scanline scroll of a
single wide bitmap) and this whole "load a background per room" framing needs revisiting; if
something *does* write it, that call site is the real redraw trigger `$e854`/`$e7b0`/`$ccd4` are
missing. Not run this pass — the natural next step, cheaper than more blind subroutine tracing.

### 31e. That watch, run for real: the reverse TUNNEL→CAVERN crossing genuinely redraws the screen —
    but it's `$0144b8` itself doing it, and it only fires on a real transition, not on movement alone

Ran the exact test §31d proposed, same session. From `room2_tunnel_entry.snap`, `watch 2de08 32000`
armed, then tried each direction: **Right** (blocked at a wall a few units out, zero watch hits, four
figure step budgets), **Up** (blocked immediately, zero hits), **Down** — a real, clean crossing:
player bbox jumps from `[20,12,14,6]` to `[76,13,70,7]` (a different part of the shared coordinate
space entirely) and the watch fires **~130 back-to-back `WriteWord`s**, all at `pc=$014966`/
`$01496e`/`$014976` — inside `$0144b8` itself (`ScreenFlip_ScanlineCopy`, graphics.md §4a), not a
new, undiscovered routine. Snapshotting mid-flight and rendering catches a genuinely different,
transitional frame (black borders, a half-composited third scene, "TUNNEL" label not yet updated —
`tunnel_return_cross.png`); stepping 500,000 more steps and re-rendering settles cleanly to CAVERN's
own known background and "CAVERN" label (`tunnel_return_settled.png`), matching the 12th pass's
original CAVERN→TUNNEL screenshot in reverse. **This is the pre-existing, already-known CAVERN↔TUNNEL
link, traversed backward for the first time this spike has driven it** — not a newly-unlocked room —
but it settles two things cleanly: (1) `$0144b8`'s screen-flip only fires on a genuine portal
crossing, not on ordinary blocked movement (Right/Up produced real player-adjacent activity but zero
watch hits) — a useful, previously-undocumented behavioral fact about when the "chunked, tear-free"
flip actually runs; (2) `$0144b8` is a **destination**-side consumer here, not the source — it flips
an **already-fully-composited** frame onto the visible screen, so the real "paint CAVERN's pixels"
step happened earlier in the same transition, before this flip, and is still unlocated. `$014a90`
(one of §28c's own six `$69da`-callees, never individually traced) sits immediately after this flip
routine in memory and reads a room-specific field at `(A5)+496` into a masked composite — a
plausible next lead, not yet followed.

**Net effect on the room-hack goal**: still open. The `164(A5)`-to-type-3-slot-5 hack (§31c/§31d)
remains unconfirmed either way — this pass's live test exercised the *known* CAVERN↔TUNNEL link, not
the hacked link, so it neither confirms nor refutes §31d's "CAVERN/TUNNEL might be one continuous
playfield, not two rooms" reframe. What it does rule out: `$0144b8` itself is not where a per-room
background gets selected (it's a generic flip, any two frames would trigger the same code path) —
whatever reads a *specific* room's *specific* art has to run before it, each transition, and hasn't
been caught in the act yet for either the real CAVERN↔TUNNEL link or the hacked type-3 slot.

## 32. Resume infrastructure rebuilt from scratch (32nd pass); `$014a90` disassembled in full for the
    first time — confirmed to mask directly onto the live screen buffer, but the actual room-art
    source it reads is still not pinned down live

Picked up cold: every `.snap`/scratch file this workstream's handoff pointed to (`room_hack_*`,
`tunnel_return_*`, `room2_tunnel_entry.snap`) was gone — untracked and never surviving between
sessions, as the README always said they would be — and the Cadaver disk image itself wasn't even
present on this checkout (it lives on `gpubox`, pulled over via the tar-over-ssh recipe in
`CLAUDE.md`). Re-derived the whole chain from a cold boot rather than treating any of it as still
available:

- Cold boot (ESC at the restore-game prompt, any key at "place levels disk", wait out "expanding
  data"/"loading data") reproduces `gameplay_empire.snap`'s CAVERN/DAY 1 state exactly.
- The documented zigzag (`Right 1.2M → Up 0.5M → Right 1.2M → Up 1.2M`, joystick port 1) reaches
  TUNNEL exactly as the 12th pass described — same screen layout, same "TUNNEL" status-bar label.
- Arming `watch 2de08 32000` and holding Down reproduces the 31st pass's reverse TUNNEL→CAVERN
  crossing exactly: ~64,000 watch hits, all at `pc=$014966`/`$01496e`/`$014976` (inside
  `$0144b8` `ScreenFlip_ScanlineCopy`), settling cleanly to a CAVERN render pixel-identical in
  character to the original `gameplay.png` milestone.

New snapshots (same names as the ones this handoff had lost, so the README's own file table stays
accurate): `room2_tunnel_entry.snap`, `tunnel_return_cross.snap`, `tunnel_return_settled.snap` (all
untracked, `M68000/scratchpad/cadaver/`) plus committed renders
(`room2_tunnel_entry.png`/`tunnel_return_cross.png`/`tunnel_return_settled.png`).

### 32a. `$00014a90` in full — a room-record masking/prep routine that writes into the live screen
    buffer directly, not a separate "background painter" waiting to be found

Full linear disassembly from `tunnel_return_cross.snap` (`$014a90`-`$014b74`):

```
$014a90: A0 = 496(A5)              ; current room record
$014a94: A0 += $c0                 ; room_record+$c0: a 12-word (6x2) mask table
$014a98: A1 = (A5)                 ; *(A5) is the live screen buffer pointer (ScreenBufferA/B
                                    ;   role-swap field, README's 2nd pass) - not a scratch copy
$014a9a: A1 += $59e8                ; a fixed offset into that live screen buffer
loop x6: D0 = (A0)+ ; and.w D0,(A1)+ x4 ; D0 = (A0)+ ; and.w D0,(A1)+ x4 ; A1 += $90
$014abc: bra $014ac0
$014ac0: A1 = 496(A5) ; A0 = A1+$60
loop x6: move.l (A1)+,(A0)+ x4      ; copies room_record[0..$60) -> room_record[$60..$c0)
                                    ;   in place, inside the room record itself (data prep for a
                                    ;   later call, not a screen write)
$014ae0: D0 = 2516(A5) ; D0 /= $16 (22, unsigned) ; D0 = $64 (100) ; D1 /= D0 (D1<<2)
$014af2: A1 = $60fc.l + D1          ; a 4-entries-per-slot table, index from 2516(A5) via two
                                    ;   divides - looks like a day-count/variant selector, not
                                    ;   confirmed
$014afa: D0,D1 = (A1)+,(A1)+        ; two mask words from the table
loop x6: and.w D0,(A0)+ x4 ; and.w D1,(A0)+ x4   ; masks the just-copied room_record[$60..$c0)
                                    ;   copy in place against the table's two words
$014b1c: D6=2, D7=6, D0=$110 (272), D1=$8f (143)
$014b28: bsr $014d7a                ; the generic sub-pixel masked blitter (README 7th pass names
                                    ;   its sibling at $00bf72; $14d7a is the same shape - checked
                                    ;   D6==2 branches straight to $14ee4, a full arbitrary-shift
                                    ;   and/or/not composite loop, same silhouette as $14f4a on)
$014b2c: rts
```

**Settled**: `$014a90` is not a still-missing routine that writes somewhere else and needs
tracing further downstream before it touches video RAM — the very first loop already ANDs a
room-specific mask (`room_record+$c0`) directly into the live screen buffer at a fixed offset
(`+$59e8`) from its base. This mask-then-blit shape (mask pass, then a positioned masked-blit call
with fixed screen coordinates `(272,143)`) is a strong match for "the actual per-room paint step"
the 31st pass was looking for — it runs on the room-record pointer (`496(A5)`) that changes per
room, not a fixed address.

**Still open, concretely**: what `$014ee4`'s source (`A0` at the `bsr $14d7a` call) actually points
to — the room-specific art itself, versus another fixed system asset (a HUD/inventory-panel
redraw, say) that merely happens to run once per room-entry. A live register dump was attempted
this pass (`bp 14a90 <n>`/`bp 14b28 <n>`) but came back inconsistent between two supposedly-
identical replays from `room2_tunnel_entry.snap` + the same `kbd ff 02` hold — one run crossed
cleanly in ~1.5M steps (matching the watch-based test above), the other sat at the idle main-loop
PC for the full 2M-step budget with no movement at all. Not yet root-caused: possibly a real
IKBD/interrupt-timing sensitivity in the `bp` polling path itself (untested against `watch`, which
did reproduce cleanly across this pass's two separate replays), or a mundane mistake in this
pass's own REPL script.
**Next step for whoever picks this up**: re-run the crossing under `watch` (proven deterministic
this pass) with a second watch region on `496(A5)` and `A0` at `$014b28` — or add a REPL command
that dumps registers on a `watch` hit rather than relying on `bp`'s separate, apparently-flakier
polling — then read whatever `A0` points to with `gfxview.py`/`disassemble.py --snap` to see
whether it's genuinely per-room art or a fixed shared asset.

### 32b. `$014b28`'s blit source is a fixed address, not per-room art — `$014a90` paints a status/icon
    panel, not the room background (33rd pass)

Root-caused the prior pass's `bp` flakiness first: it wasn't `bp` itself — `bpc 014b28 1 <maxSteps>`
(stop on the *first* hit rather than relying on `bp`'s own polling) reproduced cleanly, back to back,
every time this pass tried it, both from a single-session replay and from two independent fresh
`resume ... repl` processes. Whatever made the previous pass's two `bp` replays diverge (one crossed,
one sat idle for the full 2M-step budget) did not recur; most likely a REPL-session/script mistake in
that pass rather than a real emulator nondeterminism (`watch` was already known-clean, see §32a's own
note).

Live register dump at `$014b28`, both directions of the CAVERN↔TUNNEL link:

- **TUNNEL→CAVERN** (from `room2_tunnel_entry.snap`, `kbd ff 02` hold, hit after 868,379 steps):
  `A0=$000055b6 A1=$00006100 D0=$110(272) D1=$8f(143) D6=2 D7=6`.
- **CAVERN→TUNNEL** (from `gameplay_empire.snap`, the §-recipe zigzag, hit ~99,021 steps into the
  final `kbd ff 01` leg, roughly 2.999M total steps): **identical** `A0=$000055b6 A1=$00006100
  D0=$110(272) D1=$8f(143) D6=2 D7=6` — same source address, same screen position, same shape, in
  the opposite room-transition direction.

**This settles the open question**: the blit source at `$014b28` (`$14ee4`, the arbitrary-shift
and/or/not composite loop reached via `$14d7a`'s `D6==2` branch) is a **fixed, room-independent
address** (`$55b6`), not the current room's own art selected via `496(A5)` — if it were per-room art,
CAVERN and TUNNEL would read different source addresses, and they read the same one. `$014a90` is
therefore not "the room background painter"; it repaints a fixed on-screen element at a fixed screen
position `(272,143)` (right-hand portion of the 320x200 screen, a plausible status/icon-panel
location) every time a room transition completes, matching §7's independently-documented behaviour
("standing at the lever sets the status-bar name field to 'LEVER' and switches the icon panel to a
lever-specific icon pair") — a fixed icon/status panel that gets redrawn on room entry is exactly the
kind of asset this shape (fixed coords, fixed source, `room_record+$c0` used only as a *mask*, not a
source pointer) would produce. `m 55b6 128` shows mostly zero bytes with a sparse `f8 00 00 3f`/`f8
01 86 3f` pattern starting around offset 108 — not dense enough to be a full-screen or full-room
bitmap, consistent with a small icon/glyph asset rather than room art.

**Reframe for the still-open room-background question** (§31e/§32a's original goal): `$014a90` is
now a closed lead, not an open one. Whatever actually selects and blits a *room's own* background
art still hasn't been caught in the act; the search should look elsewhere in the transition path
(before `$0144b8`'s flip, which is confirmed destination-side-only per §31e) rather than continuing
to chase `$014a90`/`$014b28`.

**Not yet done**: confirming `$55b6`'s contents are the actual icon-panel glyph/sprite data (versus,
say, a palette or mask table reused for another purpose) — read it with `gfxview.py` against the
known screen palette and compare its rendered shape to a real "LEVER" vs default icon-panel
screenshot pair.

## 33. `$55b6`'s actual bytes decoded; a full-screen-buffer watch during a live crossing rules out the
    entity/sprite-draw path as the missing room-background painter (34th pass)

### 33a. `$55b6` is 96 bytes of solid zero, then a short repeating word pattern — confirms it is not
    room art, refines but does not overturn §32b

Reading the snapshot's own RAM directly (the `A68S` header format `gfxview.py` already parses:
magic, version byte, 19 little-endian int32 registers, int16 CCR, then a length-prefixed RAM block)
at `$55b6` in `hit_014b28.snap`: bytes `$55b6`-`$5615` (96 bytes = exactly the 4-longwords/row × 6-row
extent `$014b28`'s `D6=2,D7=6` call consumes, per §32b/§32a's loop trace) are **solid zero**. The
sparse `f8 00 00 3f` / `f8 01 86 3f` pattern §32b's `m 55b6 128` output noticed starts at `$5616`,
*outside* the consumed range — it's unrelated neighbouring data, not part of this blit's source.

So the actual source content for this specific live call is a blank/all-zero mask-source, not a
glyph. This still fits §32b's icon-panel conclusion (a masked blit that ANDs a room-mask onto the
screen then ORs in a fixed, room-independent source at `$55b6` reads as "clear this panel region to a
known state on room entry", which can legitimately be all-zero for the *default* panel state — the
"LEVER"-vs-default icon difference §7 documents would then come from a different, not-yet-traced
write, not from this call's source varying). Rendering the 96-byte blob confirms this visually
(`gfxview.py` with `base=55b6 width=32 rows=6 bpp=4 st-interleaved` shows a solid black/background
rectangle, zoom 8, no visible glyph) — not informative as an image, but the negative result is real,
not a rendering-layout mistake (raw hex was read directly, independent of `gfxview.py`'s decode).

**Still open**: this closes "is `$55b6` a glyph" (no) but does not identify what, if anything,
distinguishes a "LEVER" icon-panel redraw from a default one — that would need catching a
`$014b28`/`$014a90` call during an actual LEVER-proximity transition, not the plain room-crossing this
pass and §32b both used.

### 33b. Full-screen-buffer `watch` across a live TUNNEL→CAVERN crossing: every writer PC identified;
    none of them is a new candidate for "the room-art painter" — the entity/sprite-draw system is
    ruled out, not confirmed

Item 1's open question ("what paints a room's own background, since `$014a90`/`$0144b8` are both
closed leads") needed a census of every routine that writes the live screen buffer during a real
crossing, not just the two previously-known ones. Ran `watch <screen_buffer_base> 32000` (the full
320×200×4bpp buffer, base read live from `4(A5)`... no — `(A5)` itself, confirmed `$19100` this pass,
matching `gfxview.py`'s independently-detected live screen base) across the same `room2_tunnel_entry.snap`
+ `kbd ff 02` (Down) TUNNEL→CAVERN crossing §31e/§32 both used, then bucketed all ~668k `WATCH` lines
by PC (`grep -o 'pc=\$[0-9a-f]*' | sort | uniq -c`). Every hit PC falls into one of three known
buckets, no unexplained fourth:

1. `$0144ee`-`$014956` (~140 distinct PCs × 4480 hits each) plus `$014966`/`$01496e`/`$014976`
   (1120 each) plus a handful more up to `$0150d8` (166-488 each) — all inside or immediately after
   `$0144b8` `ScreenFlip_ScanlineCopy` (§31e), an unrolled scanline-copy body larger than the three
   individual PCs §31e originally named. Confirms §31e's "destination-side-only flip" finding, gives
   it a fuller PC range, nothing new.
2. `$0080cc`/`$0080d2` (6936 hits each) plus `$00807a`-`$008090`/`$008274`-`$008298` (22-488 each) —
   traced back live via `bpc 007f60 1 <maxSteps>` + `bt`: entry `$007f60` is another instance of the
   same masked sub-pixel blit shape as `$014d7a`/`$14ee4`/`$14f4a` (reads `(A5)` for the screen base,
   same `$90`-row-stride convention), called from `$00d93c`'s `bsr $7dd6` inside a loop at `$00d946`
   (`move.l (A2)+,D1 ; bmi $d9ce` — a null-terminated pointer-list walk) reading entity-record fields
   at offsets 14/20/21/50/51/52 off `A3`. `A6=$00038338` at the call — §21a's already-documented
   sprite-object array base (same one the player occupies at slot 0). **This is the entity/sprite
   list renderer** (mechanics.md §1-6's object-verb/composite system), not a new routine — it draws
   whatever entities (player, creatures, items) are visible during the crossing, at their normal
   screen positions. A real finding, but not the missing lead: it's the already-known sprite system,
   caught live for the first time, not an unidentified background painter.
3. Nothing else. No PC outside these two buckets touched the screen buffer during this crossing.

**Net effect on item 1**: the entity/sprite-draw system is now positively ruled out as the room-art
source (it draws sprites at their own positions, not a room-sized background), narrowing but not
closing the question. Since nothing else wrote the buffer during this capture window, the real
possibilities left are: (a) the background is drawn into the buffer well before this transition
window (e.g. when the room is first loaded/decoded into memory, not at the crossing moment) and this
window only ever needed to *flip* an already-painted back buffer — which would mean §31e's premise
("something paints room art each crossing") is itself wrong and needs re-examining; or (b) the
capture window (kbd-press to ~2.2M steps) didn't fully bracket the true paint moment. **Next step**:
before another live `watch` attempt, test (a) first — it's cheaper and, if true, closes the item as a
reframe rather than a new hunt: watch the *other* (non-visible) screen buffer role (`4(A5)`'s
counterpart per README's "ScreenBufferA/B role-swap field", §32a) starting from well before any
movement, across an idle period with no crossing at all, and see whether it already holds the
about-to-be-shown room's art before the flip ever runs.

## 34. `$0144b8` disassembled at last — its own source register reveals a *third* resident buffer at
    `120(A5)`, not a two-way role-swap between `(A5)` and a second pointer field (35th pass); that
    buffer inspected live but not yet decoded

### 34a. The "two role-swapping buffers" model was wrong: `(A5)`/`(A5)+120` are not two peers of the
    same kind

Tested §33b's item-1(a) reframe directly: read `(A5)` and `120(A5)` live from `room2_tunnel_entry.snap`
(idle, before any input) — `$19100` and `$2de08` respectively — then rendered *both* through
`gfxview.py` at `320×200×4bpp st-interleaved`. Both `$19100` and the live hardware-scanned screen
(`$20f00`, confirmed via `load_video_regs`'s shifter-register read, ground truth for "what's on screen
right now") show byte-identical TUNNEL art. That is exactly steady-state double buffering: nothing
here is holding pre-painted future-room content, and `$19100` is *not* a second peer buffer to `120(A5)`
the way §32a's comment ("ScreenBufferA/B role-swap field") assumed.

Disassembling `$0144b8` itself for the first time (never done in full across 31 prior passes, despite
being referenced constantly since §28c) settles the actual shape:

```
$0144b8: movem.l #$fffe,-(A7)
$0144bc: movea.l 120(A5),A0        ; SOURCE = a third, separate buffer field, not (A5) itself
$0144c0: movea.l (A5),A1
$0144c2: adda.l #$7d00,A1          ; DEST = (A5)+$7d00 (32000) - the *other half* of a 64000-byte
                                    ;   region based at (A5), not a different pointer field at all
$0144c8: move.l #$1498c,$90.w      ; installs a mid-copy yield vector (trap #4, §31e's "splits the
                                    ;   copy across several VBLs so it never tears")
...
$0144e2 on: movem.l (A0)+,#$003f / movem.l #$fc00,-(A1)   ; then a long chain of
            movem.l (A0)+,#$fcff / movem.l #$ff3f,-(A1)  ; forward-reading, backward-writing
                                                           ; 56-byte movem transfers
```

`A1` starts at `(A5)+$7d00` and every `-(A1)` write pre-decrements *before* addressing, so the writes
actually land counting **down** from `(A5)+$7d00` to `(A5)+0` — i.e. into the `[$19100,$20eff]` half,
confirmed exactly by this pass's `watch`: bucketing a dual-range watch (`watch 19100 117504`, spanning
both `$19100` and `$2de08`'s 32000-byte extents in one call) by destination address, the `$0144ee`-family
PCs land 100% inside `[$19100,$20eff]` (§33b's "bucket A"), never inside `[$20f00,$28cff]`. **The real
structure**: `(A5)+0` and `(A5)+$7d00` are the two halves of *one* 64000-byte double-buffer feeding the
shifter (confirmed: `$20f00` is exactly `$19100+$7d00`, and is what the live hardware scan showed);
`120(A5)` is a wholly separate, third resident buffer that the flip *reads from* — this is the actual
candidate for "where room art lives before the flip", not a peer of `(A5)` in a two-way swap.

### 34b. `120(A5)`'s buffer (`$2de08` this session) inspected live: not blank, not a clean decoded
    frame either — structured but currently undecoded

Rendered `$2de08` at the same `320×200×4bpp st-interleaved` settings that correctly show `$19100`/
`$20f00`'s real TUNNEL frame: the result is *not* random noise (it has consistent per-row banding, not
uniform static) and *not* a recognisable room image either — inconclusive with the straight screen
layout. Two live-traced writers into ranges near this buffer during the same crossing turned out to be
already-known systems, not a new painter:

- `$0080cc`/`$0080d2` and `$0150b4` family (§33b's "bucket B", `A3=$00038338` at the call in both
  cases — the entity/sprite-object array base, §21a) are the entity-list renderer (§33b), confirmed
  again this pass with a second live capture (`bpc 0150b4`, caller `$0000d8ee`, a few bytes into the
  same `$00d900` sprite-walk loop as §33b's `$0000d940` capture) — not new.
- `$00bf72` (README's own long-known "sibling" of the masked blitter, 28384 hits this pass) writes a
  small, separate ~700-byte region (`$2ca84`-`$2cd42`) *adjacent to but distinct from* `120(A5)`'s
  32000-byte buffer — its source register at a live capture (`bpc 0150b4`) pointed into this same small
  region (`A0=$0002ca8c`), meaning this ~700-byte area is a **sprite bitmap cache/staging buffer** the
  entity renderer reads from, not room art either (too small for a 320×200 background by two orders of
  magnitude).

**Net**: after two full passes of live captures, nothing caught in the act writes `120(A5)`'s buffer
with new content during a crossing — either the write happens outside every window captured so far
(neither the ~2.2M-step crossing window nor the pre-crossing idle instant), or `120(A5)`'s buffer isn't
a plain 320×200×4bpp raster at all and needs a different decode (packed/compressed source format,
different width, or a stale/uninitialized region this early in the game that only gets used starting
from a later room count). **Concretely still open**: decode `$2de08`'s actual layout — try alternate
widths/strides in `gfxview.py` against this exact snapshot (the buffer is real and non-empty, so some
combination should resolve the banding into a recognisable image), and/or capture the *previous*
frame(s) before this snapshot's idle point to see whether `120(A5)`'s content changes across frames
even without a room crossing (would mean it's actively maintained by something not yet triggered by
this particular replay).

## 35. `120(A5)`'s buffer fully decoded — it holds the pre-flip room frame, byte-order-reversed at
    56-byte `movem` granularity (36th pass)

**Proven, byte-exact.** §34a's own disassembly excerpt of `$0144b8` was too compressed to derive the
real byte layout from; pulling the *full* linear disassembly (`disassemble.py --linear 0144b8 700`)
instead of trusting the elided `...` gave the exact instruction count needed to reconstruct it:

- `move.b #$4,$5a98.w` primes an outer-loop counter to 4; the body from `$144ea` to `$014956`
  contains exactly **142** `movem.l (A0)+,#$fcff` / `movem.l #$ff3f,-(A1)` pairs (56 bytes each,
  14 registers: `D0-D7,A2-A7` — confirmed by decoding both masks: `#$fcff` in postincrement-mode
  register-bit order and `#$ff3f` in the *reversed* predecrement-mode bit order name the same 14
  registers). `subq.b #1,$5a98.w` / `bne $144ea` repeats that 142-pair body 4 times (568 pairs,
  reading straight through — `A0` keeps advancing across outer-loop iterations, so this is a
  code-size unroll trick, not four re-reads of the same data), followed by 3 more pairs outside the
  loop: **571 chunks of 56 bytes total** (31976 bytes).
- One extra **24-byte** chunk (`movem.l (A0)+,#$003f` / `movem.l #$fc00,-(A1)`, 6 registers
  `D0-D5`) makes up the remaining 24 bytes (571×56 + 24 = 32000, exactly one frame). It runs
  **either before all 571 56-byte chunks** (if `$5a99` is nonzero at entry — `tst.b $5a99.l / beq
  $144ea` skips it when zero) **or after all of them** (if `$5a99` is zero — a second `tst.b
  $5a99.l / bne $1498a` after the last pair skips it when nonzero): exactly one of the two runs,
  gated by the same flag byte read twice.
- **Byte order**: predecrement `movem` transfers registers in the fixed order A7→A0,D7→D0; this
  register set only has `D0-D7,A2-A7`, so transfer order is `A7,A6,A5,A4,A3,A2,D7,D6,...,D0`. That
  is the exact *reverse* of the postincrement read order (`D0,D1,...,D7,A2,...,A7`) for the same
  register set, and since predecrement also fills memory high-to-low, the two reversals cancel:
  **each chunk's own 56 (or 24) bytes land in the destination in the same relative order they were
  read** — only the order of chunks *across* the whole transfer is reversed (the first chunk read
  ends up at the highest destination address, the last chunk read at the lowest).

Reconstructing this exactly — chunks read in program order from `120(A5)`, written in reverse chunk
order (the odd 24-byte chunk placed at whichever end its flag value picks) — and decoding the result
as plain `320×200×4bpp st-interleaved` reproduces `(A5)+0`'s live bytes **exactly, 0/32000 diffs**,
in `room2_tunnel_entry.snap` (`$5a99=0` there, so the 24-byte chunk is trailing). Rendered, it's the
same TUNNEL room as `room2_tunnel_entry.png`, pixel for pixel. **This settles item 1 entirely**:
`120(A5)` is not compressed, not a different resolution, and not a different bit-plane packing — it
is the *exact same raster*, stored solely with this chunk-reversal so the flip's forward-read/
backward-write `movem` pattern (presumably chosen for code density or a specific 68000 timing
reason, not a data-format reason) produces the correct forward-order frame in the visible buffer.

Script: `reversing/cadaver/py/decode_backbuffer.py <snap> [--out out.png]` (reads `120(A5)` and
`$5a99` live, reproduces the algorithm above, verified against `room2_tunnel_entry.snap`). Sanity
check against `gameplay_empire.snap`/`hit_014b28.snap`/`tunnel_return_*.snap` shows large diffs
(16-28k/32000) as *expected*, not a refutation — those are settled gameplay states where sprites,
the player, and UI panels have already been composited onto `(A5)+0` by later draw passes (§33b) on
top of the raw room flip; only a snapshot taken immediately after a flip and before those later
passes run (like `room2_tunnel_entry.snap`) matches `120(A5)` byte-for-byte.

**Reframes item 1(b)** ("find the writer"): since `120(A5)` holds a complete, already-composited
320×200 room raster rather than a smaller tile/sprite source, it is very unlikely to be built by a
runtime compositor at all (consistent with two full passes, §33b/§34b, catching no live writer
during a crossing) — the far more likely source is the room-load disk read itself, storing each
room's pre-rendered background pixel-for-pixel in this reversed layout on disk. Next step: trace the
disk-sector read(s) that happen during a room crossing (the game reads raw sectors directly, not via
GEMDOS `Fread` per the 7th pass's finding) and check whether the bytes landing in `120(A5)` match
sectors read verbatim, rather than watching for a runtime writer that may not exist.

## 36. The disk-read hypothesis is wrong: no trap/FDC activity during a real crossing, and
    `$0144b8` itself runs *backwards* to refresh `120(A5)` — the real writer is upstream of it
    (37th pass)

**36a. No GEMDOS/BIOS/XBIOS trap and no FDC register activity during a real crossing.** Ran the
reverse TUNNEL→CAVERN crossing (`kbd ff 02` from `room2_tunnel_entry.snap`, the same recipe §31e
proved redraws the screen) twice, once under `ATARI_TRACE_OS=1` and once under `ATARI_TRACE_FDC=1`
(2.5M steps each, covering the whole crossing). **Zero trace lines from either** — not one `Rwabs`,
`Floprd`, or raw FDC command/sector-read log entry. §35's own reframe (room art is loaded, not
composited) is itself now wrong in its specific mechanism: nothing hits the disk during this
crossing at all, confirmed both ways, not just absence of GEMDOS calls (the pre-existing, weaker
evidence).

**36b. Yet `120(A5)`'s content genuinely changes.** Decoded `120(A5)` before (`room2_tunnel_entry.snap`)
and after (`fresh_cavern_cross.snap`, this pass, same crossing) with `decode_backbuffer.py`: TUNNEL
art before, unambiguous CAVERN art after (boat/barrel/chest props, status bar "CAVERN") — real
content change, zero disk I/O, `120(A5)`'s own pointer value unchanged (`$2de08` both times).

**36c. `watch`ing `120(A5)`'s own address range during the crossing shows `$0144b8` (the flip
routine, same PCs as §35) writing *into* it — with its **source and dest roles reversed** from
normal.** A full register capture at the crossing's actual `$0144b8` call (`u 144c8`/`r` chained
across the call site, landing on the correct invocation by matching register content rather than
step count — `watch`'s printed step numbers are the CPU's persistent lifetime counter carried in
the snapshot, tens of millions higher than any single command's own local step budget, which cost
real time to realise) gives, reproduced 3× within one continuous trace (the trap #4 mid-copy yield
re-enters the same call across several VBLs, per §34a):

```
A0=$00020f00  A1=$00035b08
```

`A1=$35b08` is exactly `120(A5)+$7d00` (`$2de08+$7d00`) — the *dest* is `120(A5)`'s own buffer, and
`A0=$20f00` is exactly `(A5)+0 ($19100) + $7d00` — the **other, currently-inactive half of the
ordinary display double-buffer** (§34a's `(A5)+0`/`(A5)+$7d00` pair). This is the *exact same copy
mechanism* as the ordinary per-frame flip (§35), run with source and dest swapped: instead of
refreshing a display-buffer half from `120(A5)` (the normal direction), this call **banks the
inactive display-buffer half's current content back into `120(A5)`**, chunk-reversing it in the
process (same algorithm, `decode_backbuffer.py` applies unchanged, just swap which side is "source").

**Reframe, again, sharper this time**: `120(A5)` is not the room's original source data at all — it
is a **cached/reversed copy of whatever was most recently composited into the display double-buffer's
inactive half**, kept around so the *ordinary* per-frame flip can cheaply refresh a buffer half
without re-drawing it from scratch every frame. On a room crossing, something else must first draw
the *new* room's raw art into that inactive half (`$20f00` in this snapshot) — RAM-to-RAM, matching
36a's no-disk-I/O finding — and *then* this reversed `$0144b8` call archives it into `120(A5)` as the
new per-frame-refresh master copy. **The real "room background painter" is whatever writes the
inactive display-buffer half before this reversed bank-copy runs — not a writer of `120(A5)` at
all**, which is why §33b/§34b's own `watch 2de08 32000` runs, and every runtime-compositor search to
date, correctly found nothing: they were watching a downstream cache, not the source.

**Not yet done, cheap next step**: `watch $20f00 32000` (or wherever `(A5)+0+$7d00` points in the
snapshot you resume from) across the same crossing to catch *that* buffer's writer directly, now
that the right address is known. Decoding `$20f00`'s content at the exact moment just before this
reversed bank-copy runs (plain `320×200×4bpp st-interleaved`, no chunk-reversal — it's the *display*
buffer, per §34a) would also directly confirm it already holds finished CAVERN art at that point,
which this pass inferred from 36b's end-state but did not capture mid-transition (repeated attempts
to land a clean snapshot at that exact instant hit REPL step-count nondeterminism between separate
invocations of the same nominal script — successfully captured the registers three times within one
continuous run, but a fresh short script re-targeting the same point did not reliably reproduce it;
chaining `s 1`/`u 144c8 30000`/`r` for the needed ~30 iterations within one *unbroken* run, as this
pass did, is the reliable form — don't split it across separate invocations).

## 37. The room background painter found: `$00cd50`-`$00cee0` populates the object array from the
current room record on room entry, and the already-documented masked-blit renderer draws it once

**39th pass.** §36's "not yet done, cheap next step" is done, and goes further: not only is the
inactive display half's writer identified, its *cause* — the current room's own object list — is
too, closing this workstream's longest-open question.

**37a. `watch 19100 64256` (spanning *both* display halves in one call, so the "which half is
inactive right now" ambiguity that stalled the 38th pass can't cause a miss) over a full 8.2M-step
`kbd ff 02` crossing logs every write into the pair — 5,635,133 events, only 237 distinct PCs, every
one already known (the `$0144b8` flip body, the panel writers, an ambient periodic layer). A
`watch 2de08 32000` on `120(A5)` over the same crossing shows it written by nothing but that same
`$0144b8` family. A full 1MB RAM diff between the pre- and post-crossing snapshots confirms no other
region of the image changes by more than ~7KB — the room's content really does live only in these
two already-charted buffers, closing off the "we're watching the wrong address" failure mode.

**37b. Computing, per byte, the *first* write (from the watch log) that moves it away from its
`room2_tunnel_entry.snap` value — not the *last* writer, which is dominated by routine re-copying —
finds a single family responsible for far more of the real change than anything else: `$0150b4`/
`$0150ba`/`$0150d2`/`$0150d8`, 11,585 of the 37,800 differing bytes across both halves (≈31%, more
than 3× the next-largest family). This is the masked-blit primitive already named in §33b/34b as
"the entity/sprite-list renderer... confirmed not the room-art source" — that conclusion holds for
its *steady-gameplay* calls (real entities, drawn at their own positions), but during a crossing the
same entry point behaves completely differently: `hits` census gives **0** calls over 8.2M steps of
ordinary `gameplay_empire.snap` play, vs **4,066** calls during one crossing, all in a tight
front-loaded burst (first hit step 49,322, **last hit step 1,058,685** — entirely within the first
13% of the crossing, then silent for the remaining ~7.1M steps).

**37c. Snapshotting right as that burst ends (`bpc 150b4 4066 2000000` from `room2_tunnel_entry.snap`
after `kbd ff 02`, `s 200`, `snap` → `burst_end.snap`) and diffing both display halves against the
pre-crossing start and against the established `gameplay_empire.snap` CAVERN reference:**

| | vs TUNNEL start | vs CAVERN reference |
|---|---|---|
| `$19100` half | 18,289/32,000 different | **656/32,000 different (≈98% match)** |
| `$20f00` half | 18,287/32,000 different | **636/32,000 different (≈98% match)** |

Under 13% of the way through the crossing, the room is already fully painted — the small remaining
diff is almost certainly the player sprite's own position/animation, not room content. **`$0150b4`'s
burst is confirmed as the room-tile painter.** (A control run of 8.2M idle steps with *no* input at
all leaves both halves within 0-368/32,000 bytes of their start — the ~18,300-byte change is real
crossing content, not ordinary per-frame animation churn.)

**37d. Walking `$0150b4`'s call chain up (its caller at the crossing-time hit: `$0000d8ee`, inside
the already-documented `$00d800`-`$00da06` visible-object walker of §33b/34b) leads to the actual
room loader: `$00cd50`-`$00cee0`.** This routine runs once per room entry and:

- reads `movea.l 164(A5),A0` — **`(A5)+164` is the current room record pointer.** Confirmed by
  direct read: `$0006bf84` in `room2_tunnel_entry.snap` (TUNNEL) vs `$0006bf0a` in `gameplay_empire`/
  `burst_end`/`watch_wide_crossing` (CAVERN) — a different, room-specific address, read fresh at
  room-load time rather than a fixed pointer.
- zeroes three counters at `1148(A5)`/`1150(A5)`/`1152(A5)` (object sub-totals and grand total —
  `1152(A5)` is the one that grows from 2 (TUNNEL) to 22 (CAVERN) over the crossing, confirmed live
  via `watch 185d2 2`: `$0000ce2e` increments it by exactly 1 per object, ~114-116 steps apart, 22
  times in a row, no other writer touches it),
- reads `move.b 29(A0),D7` from the room record — **this is the room's object count**, and it is
  byte-exact against the two rooms sampled: TUNNEL record byte `+29` = `$02` (2), CAVERN record byte
  `+29` = `$16` (22) — matching the independently-watched `1152(A5)` growth exactly, 2/2. (Room-record
  bytes `+0..+3`/`+4`/`+5`/`+$c0` from §32a remain as documented; `+29` is a new field this pass
  adds — offset `+4`, also read here as a byte into D6 before the object loop, is not yet identified,
  it feeds a separate `bsr $c5a8` lookup with a different selector and needs its own check.)
- for each of the `D7+1` object-list entries (walked via `A4`, seeded from a per-room list next to
  the record), looks up the object's shared template via `bsr $c5a8` (a `(type, index)` resource
  lookup — called here with a `#6` selector) and instantiates a new 70-byte slot in the
  already-documented `56(A5)` object array (`SpriteObjectArrayPtr_A5Plus56`, §21a) by copying
  position/bounding-box/type fields from the template (`6(A1):=A0` keeps a back-pointer to the room
  record itself; `10(A1):=A6` keeps one to the template).

**Put together**: a room crossing does not "paint a background bitmap" as a single operation at all
— it **re-populates the shared object array from the new room's own object list** (this routine),
and the *already-documented* per-frame visible-object walker (§33b/34b's `$00d800`) then draws every
newly-active object once via the ordinary masked-blit path (§37b/c's `$0150b4` burst), the same way
it draws real moving entities every frame — a room's "background" is just its full set of static
objects (walls, furniture, terrain pieces), rendered through the identical entity-rendering pipeline,
not a separate system. This also explains why every previous pass's search for a "background writer"
kept finding only entity/sprite-blit PCs and concluding they must be unrelated: they *are* the room
painter, just called ~4,066 times instead of the handful used for genuine on-screen entities.

**Not yet done**: read `bsr $c5a8`'s body (the `(type, index)` template lookup — used both for room
records at `164(A5)` and for entries in this loop) to find the actual room/object resource table and
confirm how many rooms/objects it covers; that table, once found, would settle Open item 4 (room
connectivity) alongside this section's room-record field. Also unreconciled: this session's shifter
video-base register never changed across four independent snapshots and a direct `watch ffff8200 8`
(zero writes) for this exact crossing recipe, while two older scratch snapshots
(`watch_crossing_end.snap`, `mid_bank_copy.snap`) read shifter base `$19100` via the same
`gfxview.py` helper — check before trusting "the shifter always flips on a crossing" as general.

**Also corrected this pass**: `$5a99` is not a "room reached" flag (as several prior handoffs
assumed when using "`$5a99`: 0→1" to detect crossing completion) — it is local scratch state for
`$0000bba8`, a small wrapper that runs `$0144b8` with `(A5)+0`/`120(A5)`'s roles temporarily swapped
so the same routine can bank a display half into `120(A5)` instead of refreshing a half from it (the
"reversed" call §36c found, now understood as this wrapper's designed behaviour, not an ad hoc
swap). `$0000bba8` is itself confirmed crossing-specific (0 hits/8.2M steady-state steps vs exactly
4 during one crossing, `A1` always `$0002de08` and `A0` alternating the two display halves at every
hit), but `$5a99` toggles 1→0 within ~1,200 steps on *every* call, not just the last — using it as a
sticky "crossing done" signal is unreliable; use the room record pointer at `(A5)+164` (§37d) or the
CAVERN-content match fraction (§37c's table) instead.

## 38. The resource-manager format decoded; `(A5)+1166` is the real, clean "current room" field;
the door/portal resolver found

**39th pass, continued.** §37d's `bsr $c5a8` (the `(type, index)` lookup used both for the current
room record and for object templates) is now fully read, and it explains everything by itself —
this section supersedes §31a's guess of "Type 3... the real, populated room table" with the actual
mechanism, and gives Open item 4 (room connectivity) its concrete next target.

**38a. The resource manager**: `(A5)+96` points to an array of 18-byte type records (indexed by
`D0`, the "type" argument every `bsr $c5a8`/`$c52c`-family call takes): `[+0 index-table ptr]`
`[+4 data-area ptr]` `... [+16 entry count, word]`. `$c5a8` computes, for `(type=D0, index=D1)`:
`entry = index_table[D1]` (4 bytes: `[+0 size]` `[+2 offset]`), returns `data_area + entry.offset`
in `A0` and `entry.size` in `D0`. Read directly off `room2_tunnel_entry.snap`, the first 12 types:

| type | index-table | data area | count |
|---|---|---|---|
| 0 | `$4a51a` | `$4d65e` | 100 |
| 1 | `$4a6aa` | `$4ea4a` | 100 |
| 2 | `$4a83a` | `$5115a` | 255 |
| **3** | `$4ac36` | **`$6bf0a`** | **100** |
| 4 | `$4adc6` | `$6d35a` | 400 |
| 5 | `$4b406` | `$6dfda` | 100 |
| **6** | `$4b596` | `$6eb92` | **1000** |
| 7 | `$4c536` | `$7550a` | 0 |
| 8 | `$4c536` | `$7550a` | 64 |
| 9 | `$4c636` | `$7560a` | 10 |
| 10 | `640000` (nonsense — likely past a real bound) | `f0064` | 25 |
| 11 | `be001e`/`d7001e` (nonsense) | | 375 |

Type 3's data area, `$6bf0a`, is **exactly** §37d's `(A5)+164` room-record pointer for CAVERN — the
whole room-record system §32a and §37d described is just this resource manager's type 3 (§31a's
"Type 3 (not type 8) is the real, populated room table, 72/100 slots" is the same table seen from a
different angle — the 72 populated count is confirmed again here by walking the index table: 72 of
100 entries have nonzero `size`). Type 6 (1000 entries, used by §37d's per-object template lookup)
is the object-template pool. Decoding the type-3 index table and matching offsets against known
addresses identifies room **slots**, byte-exact: **CAVERN is slot 0** (`offset=0`→`$6bf0a`, record
size 122) and **TUNNEL is slot 1** (`offset=$7a`→`$6bf84`, record size 32) — record size scales with
the room's object count (§37d: CAVERN has 22 objects, TUNNEL 2), consistent with a header plus a
per-object index-word tail.

**38b. `(A5)+1166` is the current room's slot index — a clean, single-write field, unlike `$5a99`.**
Confirmed by direct read: `1` in `room2_tunnel_entry.snap` (TUNNEL, slot 1), `0` in
`gameplay_empire.snap`/`burst_end.snap` (CAVERN, slot 0) — matching 38a's slot numbers exactly. A
`watch 185e0 2` (`(A5)+1166`'s absolute address) over the same 8.2M-step crossing logs **exactly
one write**, at absolute step 58,093,915, PC `$0000727c`, `1166(A5) := 0` — no toggling, and it
lands inside §37b/c's `$0150b4` burst window (burst runs ~57,449,323-58,458,686), about 58% of the
way through it. **Use this field, not `$5a99`, to detect "which room is the game in right now" or
"has this crossing committed yet".**

**38c. The writer, `$0000727c`, sits inside what is very likely the actual door/portal resolver —
Open item 4's target.** Immediate context (`disassemble.py --linear 0x7250 60`):
```
$007250: move.b (A0),D0        ; a door/portal descriptor's two bytes
$007252: move.b 1(A0),D1
$007256: jsr $de5e.l            ; resolve (D0,D1) -> target room slot, result in D7 (or D7<0: none)
$00725e: bmi $7262              ; D7<0: no door here (falls into a "name unset" lookup, $7262-7270)
$007272: cmp.w 1166(A5),D7      ; already in that room?
$007276: beq $727a              ; yes: skip
$007278: exg D6,D7               ; no: D6 becomes the target room index
$00727a: move.l D7,D4
$00727c: move.w D6,1166(A5)     ; COMMIT: current room := target room
$007280: btst #0,4(A0)          ; door-descriptor flag -> picks between two $158f8 calls (sound?)
                                  ; ...
$0072ac: jsr $e854.l             ; likely triggers the object-repopulation (§37d's $00cd50) indirectly
$0072bc: bset #3,7(A0)
$0072c2: bra $69da               ; shared post-transition continuation (already known, §31b)
```
This is the first routine found that both (a) reads a door/portal descriptor and (b) writes the
clean current-room field — a strong candidate for "the" room-transition trigger `mechanics.md`
has been looking for since §9/§31b (`$007104`/`bra $69da`). **38d. `$0000de5e` is not a portal/exit-graph lookup at all — it's a spatial point-in-rectangle
scan over every type-3 room record.** Full disassembly: takes a world coordinate `(D0,D1)` (aliased
`D6,D2`), then repeatedly calls the bounds-checked resource lookup `$c628` with `type=3`, index
starting at 0 and incrementing (`addq.w #1,D1; bra $de74`) until either a match or the type's own
`16(A0)`-bound (100, §38a) is hit. For each candidate room record `A0`, it tests the point against
a rectangle built from four record fields: `x0=1(A0)`, `y0=3(A0)`, `width=4(A0)`, `height=5(A0)`
(constructing `[x0,y0]`-`[x0+width,y0+height]` and checking `x0 <= D6 <= x0+width` /
`y0 <= D2 <= y0+height`), and returns the first matching room's slot index. **This means Cadaver's
"rooms" are laid out as non-overlapping rectangles on one shared coarse world-coordinate grid, and
a door/crossing target is found by testing where the crossing point lands, not by following an
explicit per-room exit table.** Reading the two known rooms' rectangles this way:

| room | `x0` (`+1`) | `y0` (`+3`) | `w` (`+4`) | `h` (`+5`) | rect |
|---|---|---|---|---|---|
| TUNNEL (slot 1) | 19 | 12 | 3 | 5 | `[19,12]`-`[22,17]` |
| CAVERN (slot 0) | 12 | 18 | 10 | 10 | `[12,18]`-`[22,28]` |

The two rectangles are adjacent and touch right at `(22,17)`-`(22,18)` — exactly where a direct
TUNNEL→CAVERN crossing would need them to, a good sanity check for two rooms already known to
connect. **This conflicts with §32a's existing claim that room-record "`+4`/`+5` are the
graphics-table index"** — not yet reconciled (§32a may describe a different record variant, or one
of the two readings is wrong; needs a check against a room whose graphics-table index is
independently known before trusting either). **Confirmed live, end to end.** `bpc de5e 1` during the same `kbd ff 02` crossing catches its first
call with `D0=$14` (20), `D1=$11` (17) — a world coordinate on the shared edge between the two
rectangles above (`x=20` inside both rects' x-range; `y=17` is TUNNEL's exact upper bound, one below
CAVERN's lower bound). A tighter follow-up, `bpc de5e 1` then `bpc dee8 1` (the `move.l D1,D6`
result-commit instruction inside the same loop), shows this *particular* call resolves to `D6=1`
(TUNNEL — `A0`/`A3` read `$0006bf84` at that point, TUNNEL's own record address) with the loop
having tested index 0 (CAVERN) and failed, index 1 (TUNNEL) and matched — i.e. this early call is
still validating "haven't left TUNNEL yet", consistent with `(20,17)` sitting on TUNNEL's inclusive
edge. **The decisive check**: `bpc 727c 1` (the actual `(A5)+1166`-commit instruction §38b's watch
found, at absolute step 58,093,915) shows `D6=0` — CAVERN's slot — right before it commits, with
`D0=$14`/`D1=$11` still the same `(20,17)` world coordinate. This closes the loop completely: the
spatial point-in-rectangle scan over every type-3 room genuinely resolves the crossing point to
CAVERN and the resolved slot is what gets written into the live current-room field.

## 39. Open item 1 closed: `+4`/`+5` are exactly one field, read two ways — §32a/§31c's "quadrant/
graphics-table index" is computed *from* §38d's width/height, not a conflicting reading of a
different field

**40th pass.** `$0000e7b0` (already named in §31c as the routine that writes `(A5)+148`, but not
disassembled there) is the reconciliation: full linear read (`disassemble.py --linear 0xe7b0 60`
off `room2_tunnel_entry.snap`):

```
$00e7b0: movea.l 164(A5),A6      ; current room record (§31a/§38a's type-3 record)
$00e7b8: move.b 4(A6),D0         ; byte +4 - §38d's rectangle "width"
$00e7bc: move.b 5(A6),D1         ; byte +5 - §38d's rectangle "height"
$00e7c0: move.l D0,D2 ; move.l D1,D3   ; keep originals (D2/D3) for the loop below
$00e7c4: subq.w #3,D0 ; subq.w #3,D1   ; (width-3), (height-3)
$00e7c8: lsl.w #4,D1              ; (height-3)*16
$00e7ca: add.w D0,D0              ; (width-3)*2
$00e7cc: add.l D1,D0              ; index = (width-3)*2 + (height-3)*16
$00e7ce: lea $5a10.l,A4 ; adda.l D0,A4
$00e7d6: movea.w (A4),A6          ; table[index], sign-extended
$00e7d8: move.l A6,148(A5)        ; COMMIT: (A5)+148 := table[index]
$00e7dc: adda.l (A5),A6           ; A6 += screen-buffer base
$00e7de: subq.b #1,D2 ; subq.b #1,D3   ; (width-1), (height-1): loop trip counts
  ; nested dbf loop, (height-1)x(width-1) iterations, writes (A1-A0) screen-buffer offsets
  ; into a table at 2634(A5)+, stepping A1 by $508/$4f8 per column/row
$00e80a: rts
```

Live cross-check (direct memory read off both room-record instances, no emulator run needed —
these are static per-snapshot reads): `room2_tunnel_entry.snap` (TUNNEL, record `$6bf84`) has
`+4=3, +5=5` → `index=$20` → `word[$5a30]=$2d50`; `burst_end.snap` (CAVERN, record `$6bf0a`) has
`+4=10, +5=10` → `index=$7e` → `word[$5a8e]=$1268`. Both snapshots' own `(A5)+148` (`$181e6`, since
`A5=$18152`) read **exactly** `$2d50` (TUNNEL) and `$1268` (CAVERN) — matching the computed table
lookups byte-for-byte in both rooms.

**Reconciled, not a conflict**: `+4`/`+5` are a single width/height pair (§38d, used directly as
the spatial-rectangle bounds `$de5e` tests). `$e7b0` reuses those same two bytes as a 2-D index
`(width-3, height-3)` into a `$5a10` lookup table that returns a screen-space row-stride/offset
value, which both seeds `(A5)+148` and drives a nested loop (trip counts `width-1`/`height-1`) that
builds a per-tile screen-buffer-offset table at `2634(A5)+` — the per-room "quadrant/graphics"
layout §31c inferred from the write to `(A5)+148` alone. §31c's characterization was directionally
right (it does select room-shape-dependent screen layout) but wrong to treat it as an independent
field: there is no second `+4`/`+5`-like pair elsewhere in the record, just this one reused as both
a bounding box and a table index derived from the box's own dimensions. Open item 1: **closed**.

## 40. Follow-up: `$cd62`'s own `+4` read is dead code, and two more live reads of the same byte
    confirm it's the width field, not a fourth meaning

**40th pass, continued.** §31d flagged `$00cd50`'s (inside `$00ccfe`'s body — not a separate
subroutine, a fallthrough label) `move.b 4(A0),D6` at `$00cd62` as a third context reading
room-record byte `+4`, alongside a `bsr $c5a8` call with `D0=5` (type-5 resource fetch) right after
it, raising the question of whether that fetch is keyed by byte `+4` too. Traced in full
(`disassemble.py --linear 0xccfe 700`, `room2_tunnel_entry.snap`): the type-5 fetch's key is
`D1=1166(A5)` (the current-room slot, §38b), **not** `D6`/byte `+4` — and `D6` itself is never read
again anywhere between `$cd62` and the routine's `rts` at `$cf80` (confirmed by grep over the full
linear disassembly of `$ccfe`-`$cf80`: no `D6` reference in that whole span until it's
unconditionally overwritten for an unrelated local at `$cf1c`, after the only `rts` that could
return it). **This particular read is dead**: a value computed and discarded, not a third meaning
for the byte.

The same function's *next* label (`$cfc4`, a second, separate `164(A5)`-rooted routine reached via
its own `rts` boundary at `$cfc2`) reads room-record byte `+4` **twice more**, and both reads are
live:

- `$00d09a: move.b 4(A1),D2` → `addq.w #1,D2` (width+1) → `mulu D2,D1` — byte `+4` used as a
  per-row stride multiplier indexing a table at `84(A5)`, exactly the "width" reading §38d/§39
  already established (a stride of `width+1` rows is the natural shape for a rectangular grid one
  wider than its interior).
- `$00d06a: move.b 4(A1),D6` feeds (`$d236`-`$d252`) into an address computation that does
  `suba.w D6,A2` against `A2 = 2634(A5) + word[2634(A5) + D1*2]` — **`A2` is seeded from the exact
  `2634(A5)+` table `$e7b0`'s trailing loop builds from the `$5a10` lookup (§39)**. This is that
  table's consumer: per-object screen-position placement during room population reads back the
  per-tile screen-offset `$e7b0` computed at room-entry time, then adjusts it using byte `+4` again
  directly (not just indirectly through the table).

**Open item 1 (`M68000/sessions/cadaver.md`), the version raised after §39, is closed too**: there
is no fourth/conflicting meaning for `+4` — every live read across `$e7b0`, `$00cfc4`'s two sites,
and `$de5e` (§38d) is consistent with "the room's width in tile units," and the one read that looked
like a candidate for something else (`$cd62`) turns out to compute nothing anyone uses.

## Files

| File | What |
|---|---|
| `mechanics.md` | this file |
| `burst_end.snap` | 39th pass: live snapshot at the end of `$0150b4`'s room-paint burst (step ≈1,058,885 of the `kbd ff 02` crossing from `room2_tunnel_entry.snap`) — both display halves already ≈98% match the CAVERN reference here (§37c); untracked like the other `.snap` resume points |
| `watch_wide_crossing.snap` | 39th pass: end state after the same crossing run to completion (8.2M steps), taken alongside a `watch 19100 64256` log spanning both display halves at once (§37a); untracked |
| `py/decode_backbuffer.py` | 36th pass: decodes `120(A5)`'s buffer into a normal raster by reversing `$0144b8`'s chunk order; verified byte-exact (0/32000 diff) against `room2_tunnel_entry.snap`. Same algorithm applies to the reversed bank-copy direction found in §36 (source/dest swapped) |
| `fresh_cavern_cross.snap` | 37th pass: live snapshot right after a real TUNNEL→CAVERN crossing from `room2_tunnel_entry.snap` (`kbd ff 02`, 2.5M steps) — `120(A5)` decodes to CAVERN art here, proving the buffer's content genuinely changed with zero disk/FDC activity (§36a/36b); untracked like the other `.snap` resume points |
| `room2_tunnel_entry.png`/`tunnel_return_cross.png`/`tunnel_return_settled.png` | 32nd pass: re-derived from a cold boot after every prior resume snapshot was lost between sessions (untracked, as expected) — same states the 12th/31st passes originally reached, `.snap` counterparts untracked in `M68000/scratchpad/cadaver/` |
| `lever_sweep_down_clean.snap` | 21st pass: live snapshot 3 settled units below the lever hotspot — status bar reads "TUNNEL" only (no "LEVER"), the resume point behind §20c/§20d's clean readings; untracked like the other `.snap` resume points |
| `lever_hotspot_gone_3units_down.png` | 21st pass: screenshot at the snapshot above, proving the "LEVER" name-hotspot is gone 3 units below the baseline tile |
| `axe_touch.snap` | 20th pass: live snapshot with the pickaxe just picked up (status bar "PICKAXE", inventory count 22→23) — resume point for §19c's next step (travel to TUNNEL's lever and retest with it held); untracked like the other `.snap` resume points |
| `room2_lever_south_boundary.snap` | 29th pass: live snapshot at the new south-approach hard-block tile (`x6-12,y16-22`, §29a) — reached via Down×3 then Left×3 from `room2_tunnel_entry.snap`, a genuinely different route from the original Left-only approach; untracked like the other `.snap` resume points |
| `axe_touch.png` | 20th pass: screenshot at the snapshot above, status bar reading "PICKAXE" / "CAVERN" |
