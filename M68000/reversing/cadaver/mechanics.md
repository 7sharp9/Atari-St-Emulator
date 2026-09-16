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

## Files

| File | What |
|---|---|
| `mechanics.md` | this file |
