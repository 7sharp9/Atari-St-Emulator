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
joystick fire tap/hold/combined-with-direction, Space) opened the door behind it, because none confirmed an icon in the object panel the fire opens: **superseded by §71, icon 7 of that panel operates the lever and opens the door**; fire does drive
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

*Superseded (§71): the conclusion below that nothing reaches the lever is retired. Operating the lever from its icon panel writes `0` over `$ffff` in entry 1's descriptor word `+2` (live, `lever_operate.py`), which is the rewrite this section guessed at.*

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
checking the descriptors' own 8-byte content directly.** Zero bytes differ, in any of the 18+
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

> **Corrected (77th pass, `secrets.md` "Object scripts: who runs the verb interpreter").** The verb table is at `$00ffba` and has 94 entries (first word `$bc` = its size; it ends where `$010076` begins); the consumer `$00fe54` indexes it there. The 59 entries read from `$010000` here and in §24 and §64 are only its last 59 with every target off by `$46`, and their ids are the true ids minus 35: hence §64d's mid-instruction landings, and "UNLOCK is not in the table" is false (LOCK is verb 54, UNLOCK 55, KILL/UNINV/WAKE/SLEEP 50/89/74/75). The interpreter's caller is the ring-304 consumer `$00fdbc`, which runs an object's script blocks on a matching queued event (open item 1 closed; proofs in `secrets.md`).

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
- Door descriptor (`entry.+10`'s target, an 8-byte type-4 resource record — §10c/§14/§47, corrected
  from an earlier "20 bytes" guess): `+0`/`+1` = a candidate world-space entry coordinate `(x,y)`;
  `+2` word = a secondary id, with two sentinels seen on TUNNEL/CAVERN's own two known doors —
  `$0000` ("hardcoded" — this is the initial CAVERN↔TUNNEL link, wired at boot outside the generic
  resource system per §14, not a same-room self-loop) and `$ffff` ("no room, sound/event cue only",
  pushes a ring-304 opcode, no geometry/room-load call at all). A positive id runs the generic
  `jsr $11256` lookup (*superseded, §72*: it scans the type-8 list, which is the rucksack, so the id is an item id and the door a lock; it "always missed" because the rucksack was empty in every snapshot taken). **The actual destination room is not
  read off this id word at all** — every case, positive id included, falls through to `$de5e`
  (§38d/§47: a linear point-in-rectangle scan of every type-3 room against the descriptor's own
  `+0`/`+1` candidate coordinate) → `$e854`/`$e84a` (ring-304 push + `2271(A5)` block-flag, both the
  same routine — `$e84a` just presets the flag to `$ff` first) → conditionally `$defa` (a ring-304
  opcode-`$8` push, itself *not* the loader — the real disk-read consumer for that opcode is still
  unlocated). §47's full walk of all 71 door ids in this build shows every one's candidate coordinate
  resolves spatially to the door's own owning room or its immediate rectangle neighbour — the id
  word's positive values (e.g. CAVERN's east door, `73`) look like a separate "is the target room's
  data resident/registered yet" gate, not a room selector.
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
it draws real moving entities every frame. **Correction (`graphics.md` §5): this object-array
repopulation is only the *prop* layer, not "the room's background."** The claim that walls/furniture/
terrain are all just entries in this same 70-byte object array doesn't survive contact with the
actual object catalog (`graphics.md` §3): none of CAVERN's 22 exported objects are wall-scale, and
22 objects can't cover a 10×10-tile room's walls and floor one at a time. The real terrain source is
a separate, shared, boot-time-loaded 80-tile catalog indexed per room by its own small compressed
tile-ID grid (`graphics.md` §5) — a genuinely different system from this section's object array,
not an instance of it. Why §33b/34b's exhaustive screen-buffer `watch` never caught a tile-catalog
writer is now clear too: it wasn't missing, it was out of scope — every capture window in §33-37
started from an already-resident room and watched a *crossing*, but `graphics.md` §5d's tile catalog
loads once at boot, and §5b's per-room tile-ID grid decode is gated on room-record data already
resident in the type-1/type-3 tables by the time any of those snapshots exist. The `$0150b4`
burst (~4,066 calls) is real and is the prop layer's own paint burst (§37b/c stand as proof of
that, just not of "the room's background").

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
$00e7de: subq.b #1,D2 ; subq.b #1,D3   ; (width-1), (height-1): outer/inner dbf trip counts
$00e7e2: move.l #$508,D5          ; column step, bytes
$00e7e8: move.l #$4f8,D6          ; row step, bytes
$00e7ee: lea 2634(A5),A4          ; table cursor
$00e7f2: movea.l (A5),A0          ; A0 = screen-buffer base
$00e7f4: movea.l A6,A1            ; A1 = this row's start (A6, updated each outer pass)
$00e7f6: move.w D2,D1             ; D1 = inner (column) dbf counter, reloaded every row
$00e7f8: move.l A1,D0 ; sub.l A0,D0   ; D0 = A1 - screen-buffer base
$00e7fc: move.w D0,(A4)+          ; table[row*width+col] := D0
$00e7fe: adda.l D5,A1             ; A1 += $508 (next column)
$00e800: dbf D1,#-10 == $e7f8     ; repeat "width" times
$00e804: adda.l D6,A6             ; A6 += $4f8 (next row's start)
$00e806: dbf D3,#-20 == $e7f4     ; repeat "height" times
$00e80a: rts
```

Full transcription (41st pass, replacing the 40th pass's elided summary above) resolves the loop's own
iso-projection arithmetic byte-exact, live-cross-checked against both room-record instances:
`screen_offset(row, col) = base_offset + row*$4f8 + col*$508`, `row` in `[0,height)`, `col` in
`[0,width)`, stored row-major (stride = width) at `(A5)+2634`, where `base_offset` is exactly the
`$5a10`-table value this section already committed to `(A5)+148`. Verified against every cell of both
rooms' live tables (TUNNEL 15/15, CAVERN 100/100 — `graphics.md` §5h has the full check and the
render-pipeline consumer this table feeds). `$508`=1288 bytes decomposes as 8 scanlines (screen
stride 160 bytes/line) + 8 bytes (16px) right; `$4f8`=1272 as 8 scanlines − 8 bytes (16px) left — a
diagonal isometric column/row step, not an axis-aligned grid step, consistent with the "carved,
overlapping cave-wall" look the tile catalog (§5d) renders.

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

## 41. Open item 1 (cadaver.md): `$014a90`/`$014b28` do not fire for the LEVER-proximity icon-panel
    change — it's a genuinely separate mechanism from the room-crossing redraw (41st pass)

`room2_lever_boundary.snap` was missing from this Mac checkout's scratchpad (only present on the
machine that made it — the known gpubox/per-machine scratchpad split), so rebuilt it fresh from
`room2_tunnel_entry.snap` using the 13th pass's own recipe: hold Left (`kbd ff 04`) from the tunnel
entry. Before injecting the hold, set `bpc 014a90 20 1500000` (stop after up to 20 hits or 1.5M
steps, whichever first) so the breakpoint's step budget covers the whole approach, not just the
final settled position — §32b/§33 had only ever caught this address during an actual *room*
transition, never during a pure proximity change within one room.

**Result: zero hits.** `bpc` gave up after the full 1,500,000-step budget having seen 0/20 hits of
`$00014a90`, i.e. that address is never reached at all while walking from the room-entry position
into the LEVER hotspot. `snap_render.py` on the resulting snapshot (`room2_lever_boundary_new.snap`)
confirms the approach genuinely reached the boundary — status bar reads "LEVER"/"TUNNEL" (matching
`room2_lever_boundary.png`'s known appearance) and the icon panel's left-hand box row shows the
same two lit icons the 13th pass documented, both absent from the idle `room2_tunnel_entry.snap`
render. A pixel diff of the bottom UI strip between the two renders confirms real, visible change in
both the icon-box region and the status-text region.

**This settles the open question `$014a90`'s own §33b left standing**: whatever paints the
LEVER-specific icon pair when the player enters proximity, it is not `$014a90`/`$014b28` — that
address is confirmed (now by a second, independent live test) to be a room-crossing-only redraw,
never invoked by a same-room proximity change. The icon-panel content update for object proximity
is a still-unidentified, separate write path — a new, narrower open item than the original (which
asked only whether `$014a90` was involved; it settles that as no, cleanly, rather than leaving it
untested).

## 42. The real LEVER-proximity icon-panel writer traced end to end: a generic nearby-object hint
    scan feeds a diff-based icon-panel redraw, sharing its trigger with the status-bar name field
    (42nd pass)

Picked up §41's open item directly. A raw pixel diff of `room2_tunnel_entry.snap` (idle) against
`room2_lever_boundary_new.snap` (`tools/snap_render.py`'s own base/rez/palette decode, done by hand
rather than via the PNGs) narrows the change to `x[10,49] y[155,181]` — the icon-box row, not the
whole screen (a first pass at this diff over the *whole* frame returned a 280x125 bbox, because the
player sprite itself also moved between the two states; restricting to the bottom-left UI region
before diffing was necessary).

**Finding the writer.** Armed `watch` over both possible screen-buffer bases (`$019100`/`$020f00` —
this game flips which is live, §10) restricted to that pixel bbox's byte range, then replayed the
13th pass's Left-hold approach fresh from `room2_tunnel_entry.snap`. After excluding the
already-known, continuously-running full-buffer copy family (`$014696`-`$0148ee`, the same
chunk-reversing block-copy documented in §33b/§35-36 and already ruled out as a content-authoring
site), one PC group stood out by being rare instead of continuous: `$015176`/`$01517e`/`$01518c`/
`$015192`, 56 hits each over the whole approach, writing exactly at row 155 col 0 and row 155-158
col 16 — i.e. a 32px-wide, ~14-row glyph blit landing precisely inside the diff bbox.

Disassembly around `$0150e2`-`$015198` is the **same shared masked/rotated-blit primitive already
documented at `$014ee4`** (rotate-by-`D1`, AND/OR/NOT composite, `$5870.l`-indexed shift-mask
table) — not a new blit routine, just a different call site reached via the dispatcher at
`$014d64`/`$014d7a` (`cmpi.b #$1,D6` / `beq $150e2` or `$15124`, the same `D6`-selected-variant
pattern as `$014a90`'s own `D6==2` path). `bpc 150e2 1 1600000` (first hit only) landed at step
192,518 with `D6=1 D7=$e(14) A0=$00000a7e` and a return address of `$0000bcca`, i.e. called from
inside `$00bca0`.

**`$00bca0` is a generic "draw icon glyph in panel slot" routine**: `A0 = 332(A5) + iconIndex*112`
(a 112-byte = 32×14px glyph per icon, `D0` selects which), `A1 = $5fbe + slot*8` (a fixed
screen-position table indexed by panel-slot number, `D1`), then falls into the shared blit
(`jsr $14d7a` with `D6=1,D7=14`). Its two static callers, `$00bc3e` and `$00bc72`, live inside a
larger function at `$00bbcc`/`$00bbd4` that is a **diff-based icon-panel redraw**: it walks
`2303(A5)` (an icon count, 0-6/7 per the `SEVEN OR OVER ICONS` cap, §7) over a table pointed to by
`456(A5)` (statically always `$5ff6`, `$00946a`), comparing each byte against a cached copy at a
second fixed table (`$6000`) and calling `$00bca0` only for the slots whose value actually changed
— exactly the shape that would make `$014a90`'s always-redraw-on-crossing behaviour a poor model
for this: this path only touches the screen when the *content* changes, matching §41's negative on
`bpc 014a90`.

**Who calls the redraw, and when.** A `hits` census of the redraw's few call sites during the same
approach (`$00bbcc`, `$00bbd4`, and every `bsr $bbd4`/`bsr $bbcc` site found by grepping the
whole-image listing) showed only `$00958e` firing, 3 times, first at step 192,475 — 43 steps before
the glyph blit, i.e. this is the caller. `$00958e` sits inside an input/event dispatcher block
(`$009542`-`$0095ea`) gated on `btst #1,2499(A5)`: whenever that bit is clear, the dispatcher
refreshes the icon panel. This runs off input-processing, not off a room-transition hook, which is
why `$014a90` (a room-crossing-only repaint) never fires for it.

**What actually changes.** Reading `2303(A5)` and the table at `$5ff6` directly out of both `.snap`
files (no emulator run needed — a live snapshot's static memory answers this, per the discipline
note below) settles the content question outright:

| Field | `room2_tunnel_entry.snap` (idle) | `room2_lever_boundary_new.snap` (LEVER proximity) |
|---|---|---|
| `2303(A5)` (icon count) | `1` | `3` |
| `$5ff6[0..2]` (icon indices) | `ff ff ff` (empty/sentinel) | `07 0b 06` |

Two new icon glyphs (indices `$07` and `$0b`) appear, plus the always-present trailing `$06` — a
real, in-RAM content change, not just a coincidental redraw of unchanged data.

**Tracing to the actual proximity check.** `2303(A5)`/`$5ff6` are built by a function at `$009440`:
it walks a caller-supplied list of nearby-object indices at `(A0)`, resolves each to an object
record `A4` (via `56(A5)` → `+8(A6)` → `+6(A4)`, the same object-table indirection used elsewhere in
this game, §7/§14), and skips any object whose record has bit 6 of byte `12(A4)` set. For the first
eligible object it falls into `$00946a`: sets `456(A5) := $5ff6`, compares the object's name-id
`10(A4)` against the currently-displayed name `1222(A5)` (**this is the same field that drives the
"LEVER"/"TUNNEL" status-bar text**, confirming §7's paired behaviour — name text and icon panel —
really is one write path, not two independent ones), then (`$0094be`-`$00953e`) appends a sequence
of fixed icon-index bytes into the table, each conditioned on a different bit/field of the object
record (`12`, `15`/`22`/`23`/`29(A4)`, one indirected through a verb→icon lookup table at `$5c1c`
keyed by `23(A4)`), always finishing with icon `$06`, and stores the resulting count into
`2303(A5)`.

**This closes the open item as originally scoped** (what paints the LEVER-specific icon pair) with
a full call chain, not just a negative: `$009440`'s nearby-object scan → `$00946a`'s icon-set
builder (`2303(A5)`/`$5ff6`) → the input-driven diff redraw (`$00958e` → `$00bbd4`/`$00bca0`) → the
shared masked-blit primitive (`$014d7a` → `$0150e2`, the same primitive `$014a90` also uses for its
own, unrelated room-crossing repaint).

**Narrower item still open**: what builds the object-index list fed to `$009440`'s `(A0)` — the
actual room-proximity/distance test that decides LEVER is "nearby" in the first place. Likely near
the collision/obstacle-check code at `$008870` (§7/§14), not traced this pass.

## 43. Open item 1 (§42) closed: `$008870` is both the movement collision test and the builder of
    `$009440`'s nearby-object list, via a per-room bounding-box overlap scan (43rd pass)

A `bpc 009440 1 250000` armed fresh from `room2_tunnel_entry.snap` (after the same `kbd ff 04`
Left-hold input) hit at step 189,923 with `A0=$00038036`; its one-deep backtrace (return address
`$00007376`) lands inside the per-frame input/movement handler at `$007368`-`$0073da`. Reading that
block in full: `bsr $77fe` computes a facing-based (dx,dy) into D0/D1 (via the direction table at
`$5bea`, indexed by the facing byte `2273(A5)`, negated when `2340(A5)` is set), then
`jsr $008870.l` is called with D0,D1 = the *candidate* new position and D2 carried from the
direction-table's second byte (an elevation/layer value). Its return status branches three ways:
`bmi` (blocked) and `beq` (a second, narrower case) both skip past the icon-panel path entirely;
only the fallthrough (candidate move accepted) does `movea.l 92(A5),A0 ; jsr $009440.l` — confirming
`92(A5)` is the fixed global holding the object-index-list pointer that both routines share, exactly
the pointer read at the live `bpc` hit.

**`$008870` builds that list itself, in the same call.** Full disassembly (`$008870`-`$008ac0`)
shows: `A4 := 92(A5)` (the list header), an initial `move.w D6,(A3)+` with `D6=0` zeroing the
header, then a series of room-boundary bounds checks against the candidate position (D0,D1) and a
per-quadrant obstruction-rectangle table (fields `2222`-`2237(A5)`, the same 4-corner-box fields
documented at line 1790) via a `jmp (A0)` computed jump keyed off a per-room table at `140(A5)`. If
any of these reject the candidate, the routine takes the "blocked" exit (`$88d8`/`$8ac2`) and
overwrites the list header with a status/blocker encoding instead of a count — this path is exactly
what the caller's `bmi`/`beq` branches catch, so it never reaches `$009440`.

Once the candidate position clears the boundary and obstruction checks, the routine falls into a
loop (`$89b2`-`$8ab6`, `dbf D7` over `D7 = 1152(A5)` — the room's live object count) over the room's
own object-placement table at `A6 = 56(A5)` (stride `$46` = 70 bytes, the same table/stride used
elsewhere for object iteration, §7/§14). For each entry it tests the candidate position's margin box
(`D3,D4,D5`, built from D0-D2 against the *room record*'s own offset fields `16/18/20(A0)`) against
that object's bounding rectangle (`0-3(A6)`) and a layer/elevation field (`4(A6)` vs D2); a match
appends the object-placement pointer `10(A6)` into the list (`move.l A2,(A3)+` with `A2 := 10(A6)`)
and increments the header's count byte (`addq.b #1,(A4)`), also flagging the nearest match (`bset
#7,-4(A3)` when the running distance byte `D5` beats the previous entries' spacing). This is the
"caller-supplied list" `$009440` walks: `move.b (A0),D7` reads that same header count, then
`movea.l (A0)+,A6` reads each `10(A6)`-sourced placement pointer in turn and resolves it to the
final object record via `56(A5) → +8(A6) → +6`, matching §42's description exactly.

**This closes the item as scoped.** The "room-proximity/distance test" is a bounding-box overlap
test between the player's candidate movement position (with a small margin) and each room object's
own rectangle, run once per frame as a side effect of the ordinary movement-collision check at
`$008870` — there is no separate distance/proximity routine to find; proximity here *is* the same
rectangle test the game already uses to decide whether a step is blocked. Proof: live `bpc`/`bt`
capture confirming the call site and the `92(A5)` pointer identity (above), plus full disassembly of
both routines showing the header/count/pointer layout agree byte-for-byte across the write side
(`$008870`) and the read side (`$009440`).

## 44. Open item 4 closed: all 72 populated rooms decoded into a full world map, confirming §38d's
    spatial resolver is generic, not a two-room coincidence

**44th pass.** §38a's type-3 index table (100 slots, base `$4ac36`, `[+0 size][+2 offset]` per
entry) and §38d's per-room rectangle fields (`x0=+1, y0=+3, w=+4, h=+5` off the record at
`$6bf0a + offset`) are both static game data, so every populated slot's rectangle can be read
directly from one snapshot with no emulator run. `py/world_map.py` walks all 100 slots, skips the
28 zero-size ones, and decodes the rest: **72/100 populated**, matching §38a's count exactly.

Checking every pair of the 72 rectangles for overlap found **zero** — confirming §38d's "rooms are
laid out as non-overlapping rectangles on one shared world grid" generically, not just for the one
TUNNEL/CAVERN pair originally checked. 99 pairs share a boundary edge (candidate doors/crossings)
and 18 touch only at a single corner; TUNNEL (slot 1) and CAVERN (slot 0) are among the edge pairs,
reproducing §38d's original by-hand result (`[19,12]-[22,17]` / `[12,18]-[22,28]`, touching at
`y=17/18`) as one case of the general script. Rendered map: `world_map.png` (rectangles labelled by
slot number, `TUNNEL`/`CAVERN` named).

This settles Open item 4 as originally scoped (decode every room's rectangle from the resource
manager) without needing to walk the door-descriptor bytes read at `$007250` (§38c) — the
rectangle adjacency graph is the room-connectivity map; a door descriptor's `(D0,D1)` bytes select
*where* on the shared grid the transition lands, but which rooms can neighbour each other is fully
determined by the rectangles alone, proven here for all 72 slots rather than inferred from two.

## 45. Open item 1 closed: §43's proximity mechanism confirmed generic against a second object
    (CAVERN's BOAT, 45th pass)

§43 proved the `$008870`/`$009440` proximity mechanism was code-path-generic (a per-room
bounding-box scan, not a per-object special case) by reading the routine, but had only ever been
triggered live by one object, TUNNEL's LEVER. Reproducing the same test against CAVERN's BOAT
name-hotspot (11th pass) closes that gap: from `gameplay_empire.snap`, holding Down
(`kbd ff 02`) and arming `bpc 9440 1 1000000` hits at step 306,325 with **the same call site**
(`bt 1` return address `$00007376`, identical to §43's TUNNEL hit) and **the same fixed list
pointer** (`92(A5)` resolves to `$00038036` in both rooms — a global, not per-room, address).
`m 38036 32` at the hit shows the header count byte `01` (one match) followed by one entry
`$0007061e`, matching the live `A6` register exactly. Stepping 30,000 further and rendering the
resulting snapshot (`boat_hotspot.snap` → `boat_hotspot.png`) shows the icon panel and status bar
reading **"BOAT" / "CAVERN"**, confirming the resolved object is genuinely the BOAT hotspot, not a
coincidental neighbour in the room's object-placement table.

**Closes Open item 1 as scoped.** The mechanism found in §43 is confirmed generic across rooms and
objects from a second live trigger, not just from reading the code once: same caller, same list
global, same header/entry layout, a different room and a different resolved object record
(`$0007061e` here vs TUNNEL's LEVER-adjacent record in §43), both correctly reflected in the UI.
Proof: `bt 1`/`r` register capture at the hit (call site and list-pointer identity), `m 38036 32`
(header+entry layout), `boat_hotspot.png` (UI confirmation) — committed alongside this doc.

**Trap found reproducing this**: the raw `dotnet exec bin/Debug/net8.0/M68000.dll rrepl <snap>`
form used in earlier scratchpad drive scripts is not a real subcommand — `rrepl`/`snap`/`resume`
are `run.ps1` aliases, and the raw binary only recognises `resume <snap> repl [--disk-a <path>]`
(two tokens, not one). Passing `rrepl <snap>` verbatim to the raw binary matches no argv pattern
and silently falls through to a disk-less cold boot, which then sits forever in an early ROM loop
(`$00fc01a0`-`$00fc01d4`, stable across repeated `s` calls) waiting on hardware state a diskless
boot never reaches — this looked exactly like a stuck/crashed snapshot (blank `snap_render.py`
output, `bpc` never hitting even after millions of steps) until reproducing §43's exact recipe
(`resume <snap> repl --disk-a "..."`) on the *known-good* `room2_tunnel_entry.snap` reproduced its
documented step count exactly and exposed the argv mistake.

## 46. Open item 1 (shifter-base-flip conflict, cadaver.md) resolved: `watch` does catch `movep`
    writes, the hardware register genuinely never changes during the standard TUNNEL↔CAVERN crossing,
    and the two "conflicting" older snapshots are mid-transition captures of the same invariant, not
    contradictions (46th pass)

**46a. The write instruction, found.** `find_field_writers.py room2_tunnel_entry.snap "8201"` lists
every code site that computes `A0 = $ff8201` (the shifter screen-base-high register): **14 distinct
call sites** across the image, one of them at `$015272`:

```
$015272: move.b #$0,$8260.w      ; clear sync-mode byte
$015278: move.l (A5),D0          ; D0 = (A5)+0 — the current INACTIVE display-half pointer
$01527a: move.l D0,188(A5)
$01527e: lsr.l #8,D0
$015280: lea $8201.w,A0
$015284: movep.w D0,0(A0)        ; programs the hardware shifter base from (A5)+0
$015288: clr.b 2241(A5)
$01528c: rts
```

This is a genuine bank-swap routine: it reprograms the CRTC/shifter's screen-base register straight
from the RAM field §34a already identified as the inactive display half. `MOVEP`'s implementation
(`68k.fs` line 1504) calls the same `x.MMU.WriteByte` every other store instruction uses, and
`WriteByte` calls `checkWatch` unconditionally (`MMU.fs` line 1048) — **`watch` has no blind spot for
`movep`**, ruling out the instruction-coverage hypothesis this pass started with.

**46b. Confirmed by direct census: `$015272` never runs during the standard crossing, or at all
during 8.2M idle steps.** `hits 8200000 15272` from `idle_no_crossing.snap` (no input) and from
`room2_tunnel_entry.snap` after `kbd ff 02` (the same TUNNEL→CAVERN recipe §37/39th pass used) both
give **0 hits**, reproducing §37/39th pass's `watch ffff8200 8` "zero writes" finding exactly, now
via a second, independent method (PC census instead of a memory watch) that also identifies which
routine would have to fire. The 14 call sites mean the register genuinely is reprogrammable — just
not by anything this crossing recipe, or ordinary idle play, ever reaches.

**46c. `(A5)+0` and the live hardware shifter base are exact opposites in every snapshot checked,
including the two "conflicting" ones — a consistent invariant, not a contradiction.** Parsed all
seven `.snap` files with `py/snapinfo.py` (new this pass, reuses `tools/gfxview.py`'s existing
header/video-register parsing rather than re-deriving the `.snap` format):

| snapshot | room (`164(A5)`) | `(A5)+0` | live shifter base |
|---|---|---|---|
| `room2_tunnel_entry.snap` | TUNNEL (`$6bf84`) | `$19100` | `$20f00` |
| `idle_no_crossing.snap` | TUNNEL | `$19100` | `$20f00` |
| `gameplay_empire.snap` | CAVERN (`$6bf0a`) | `$19100` | `$20f00` |
| `watch_cache_crossing.snap` | CAVERN | `$19100` | `$20f00` |
| `watch_wide_crossing.snap` | CAVERN | `$19100` | `$20f00` |
| `watch_crossing_end.snap` | CAVERN | `$20f00` | `$19100` |
| `mid_bank_copy.snap` | CAVERN | `$20f00` | `$19100` |

Five agree (`(A5)+0`=`$19100`, shifter=`$20f00`); the two flagged snapshots agree with each other but
sit at the opposite parity, on **the same room** as three of the five agreeing ones. Given their
names — `watch_crossing_end` and `mid_bank_copy` are exactly the two snapshots §35/§36c's own
mid-transition captures produced ("reversed bank-copy" register capture, `$0144b8` caught mid-call)
— the far simpler explanation than a second hardware writer is that they were taken one genuine
buffer-role swap apart from the other five, mid-flip, by the RAM-side mechanism §34a/§35/§36
already fully decoded (`(A5)+0`/`(A5)+$7d00` swapping which half is "inactive" without ever touching
`$ff8200`). No new writer needed: the two "conflicting" reads are internally consistent with the
same invariant as the other five, just caught at a different point in that same already-understood
cycle.

**Closes Open item 1 as scoped.** The `watch ffff8200 8` "zero writes" result was correct, not a
tooling gap; `$015272` (and, more generally, at least one of its 13 siblings) is the confirmed
hardware writer when it does run, but the standard `kbd ff 02` TUNNEL↔CAVERN crossing this project's
gates use never calls it. The two older snapshots that looked like a conflict are mid-transition
captures of the same steady-state invariant `(A5)+0` = inactive half / shifter = active half, not
evidence of an undetected write. **Not yet done, low priority**: identify which of the 14 call
sites *does* fire (title/intro screen, a different room-pair's crossing, or a resolution/mode change)
— not needed to close this item, since the conflict is resolved without it.

## 47. Open item 1 (cadaver.md, door connectivity) closed: every door in the loaded image resolves
    spatially to its owning room or an edge-adjacent neighbour, no teleport doors exist in this build
    (47th pass)

**Reused, didn't re-derive**: §38a's type-3/type-4 resource-table format, §38d's `$de5e`
point-in-rectangle scan, and `world_map.py`'s own room-rectangle reader and `adjacency()`
classifier.

### 47a. Door descriptors are 8-byte type-4 records, not 20 bytes — corrected static-read error

§14/§10c's "20 bytes" characterization of the door-descriptor struct was never derived from the
resource-manager format, just guessed from the struct's rough shape. Resolving the three previously
known descriptor addresses through the type-4 resource row (index-table `$4adc6`, data-area
`$6d35a`, per §38a) instead of assuming a fixed stride: door id `$32` → index-table entry `size=8,
offset=$190` → `$6d35a+$190=$6d4ea`; id `$33` → `offset=$198` → `$6d4f2`; id `$3b` →
`offset=$1d8` → `$6d532` — all three exact matches against the already-known live addresses, and all
three (like every other resolved id below) read `size=8`. **Door descriptors are ordinary 8-byte
type-4 resource records**, laid out `[+0 cx][+1 cy][+2..+3 id word][+4..+7 unread, not needed to
close this item]`.

### 47b. The full walk: every room's door-link slots, resolved through type-4, then through `$de5e`'s
    own algorithm

Script: `reversing/cadaver/py/door_walk.py` (promoted from scratchpad this pass), run against
`room2_tunnel_entry.snap` (a static read — the resource tables are game data, not per-frame state,
so any snapshot with them initialised works, per `world_map.py`'s own doc comment). For each of the
72 populated type-3 rooms, reads its own 7 door-link slots (record `+6..+19`, §14, `$ffff`=unused),
resolves each referenced id to its type-4 descriptor (§47a), reads the descriptor's candidate
coordinate, and re-implements `$de5e`'s own resolution exactly as §38d fully disassembled it: a
linear scan over all type-3 rooms in slot order, first rectangle containing the candidate `(x,y)`
wins.

**Result: 71 distinct door ids referenced across all 72 rooms. Every single one resolves to either
the door's own owning room (the "self" side of a shared edge) or a room `world_map.py`'s
`adjacency()` classifies as `edge`-adjacent to it — zero non-adjacent ("teleport") resolutions, zero
unresolved ids.** This holds regardless of the descriptor's own id word (§47c; except that a `$ffff` word commits no room change at all until a script rewrites it, §71) — the five ids with a
genuine positive value (`53`, `73`, `155`, `167`, `244`) resolve exactly the same spatial way as the
ordinary `$0`/`$ffff`-sentinel doors, landing on an adjacent room just like every other door. Full
per-door table in the script's own output (door id, candidate coordinate, id-word tag, resolved
owner/destination pair and adjacency class); not reproduced here in full since it is exactly what
the script prints and would need to be re-run to trust anyway, not transcribed by hand.

**Closes Open item 1 as scoped**: there is no "teleport" door anywhere in this loaded image's door
data — the spatial-resolution mechanism (§38d) structurally can only ever land a crossing in whatever
room's rectangle physically contains the stored candidate coordinate, and every stored candidate in
this build sits on or adjacent to the door's own room boundary, consistent with a hand-authored map
where doors are placed at room edges. Two honest caveats: this is a static read of the *currently
loaded* door data, not a live re-test of every individual crossing (only the CAVERN↔TUNNEL pair has
been driven live end to end, §38c); and it says nothing about whether a later game event (the lever,
§26) could ever rewrite a candidate coordinate to something non-adjacent — no such write has been
found anywhere in this image (§14's own descriptor-content sweep found zero writes across an 18+
condition test).

### 47c. The id word's meaning is still open — the first-draft "type-8 registration gate" reading
    doesn't survive checking against §31/§38's own, already-corrected model, and is retracted here

*Superseded (§72): the id word is an item id, a lock the rucksack opens (`$011256` scans the type-8 list, which is the rucksack, not a room-registration table); this section's reading of the destination (spatial only) stands, its "encodes nothing known" and the "registration table" language do not.*

First-draft reading, written before double-checking and retracted in this same edit: `$de5e`'s
spatial-only algorithm (§38d) was paired with §14's type-8 framing to guess the positive id word
gates on "target room registered." That doesn't hold up. §31 (31st pass, sixteen passes before this
one) already established type 8 was never the room table — type 3 is, all 72 rooms are already
resident, and this image contains no disk-I/O-capable code at all (§30a/§31a) — and §38d's own
disassembly of `$de5e`, reused directly for this pass's `door_walk.py`, shows the resolver never
reads the id word at all, only the descriptor's coordinate (the caller `$00716e`-`$007182` does read it, before `$de5e` is reached: 0 continues to the resolver, `$ffff` takes the sound-cue path `$00731e`, §71). There is no live "unregistered room"
state left for the id word to gate: CAVERN's east door resolving to the "already resident" branch
(§13, id `73`) is fully explained by ordinary spatial adjacency under the corrected model, not by a
registration check that (per §31) was never real in the first place.

What the five positive id words (`53`, `73`, `155`, `167`, `244` — none a valid type-3 slot number,
§47b) actually encode is genuinely unknown, not a lead pointing at "why room 3's own init script
never runs" — that question (§26) is itself moot under the corrected model: with all 72 rooms already
resident and no disk I/O anywhere in the image (§30a), there is no unloaded room left to register.
If picked up again, treat the id word as an unexplained field on an otherwise fully spatially-resolved
struct, not evidence for a registration mechanism.

## 48. Doc correction, then Open item 1 (world-map scope) revisited: `$00b1e0` (the level-asset
    reloader that touches type 3, the real room table) has no reference anywhere in the loaded
    image, by any static technique tried so far — direct call or raw data pointer (48th pass)

**48a. Correction to §47c, made in place rather than left standing.** On rereading this session's
own §47c against the doc's earlier sections, its "positive door id word = type-8 room-registration
gate" reading turned out to revive a framing §31/§38 had already retired sixteen-plus passes
earlier — retracted and corrected directly in §47c (see that section; not re-narrated here).
`cadaver.md`'s Open item 2 restated the same stale framing and is corrected there too.

**48b. `find_literal_ptr.py`, promoted to `tools/` (game-agnostic, alongside `find_ram_callers.py`/
`find_field_writers.py` — also newly added to `DEVELOPING.md`'s tools table, since none of the
three were listed there despite being real, reusable tools this spike already leaned on).** §15c's
"`$00b1e0` has zero real callers anywhere in the loaded image" used only `find_ram_callers.py` — a
scan for instructions whose *own decoded text* names the target literally, which by construction
can never see an indirect call reached through a jump table (target address sitting as plain data,
loaded into a register, then `jsr (An)`). §17a already knew a gap existed in the adjacent case
(`find_ram_callers.py`'s original regex missed abs-long `jsr $xxxx.l` text, worked around with an
ad hoc "literal-pointer scan" for `$b5a8`/`$67ea`, never promoted to a real tool) — `find_literal_ptr.py`
generalizes that fix: scan the whole RAM image's raw bytes for the target address as a plain 4-byte
(or 2-byte) value, independent of whether `decode_one` recognizes an instruction there at all.
Validated against `$b5a8` first (3 hits, at `$0068fa`/`$00691a`/`$006924` — the exact three
`jsr $b5a8.l` sites §17a already found by hand) before trusting it on a new target.

**Result for `$00b1e0`: zero hits, 4-byte and 2-byte, at every alignment, in `room2_tunnel_entry.snap`'s
full ~1MB RAM image.** This is a stronger negative than §15c's — it rules out not just a direct
`bsr`/`jsr $b1e0` but also a plain absolute-address jump-table entry pointing at it. It does not, on
its own, rule out a PC/table-relative-displacement jump table (the same shape as this game's own
59-entry verb dispatch table, §23a) — that would encode a *displacement*, not the address `$b1e0`
itself.

**48c. Closing that remaining gap: `tools/find_jump_table_hit.py`, also promoted this pass — zero
hits against every displacement-style table this image can construct, up to 300 entries deep.**
Rather than guess candidate table bases by hand, this collects every literal absolute address any
instruction in the whole image names (`lea`, `jsr`, `move #imm`, ...) — since §23a's own dispatch
idiom always sets up a table base by loading a plain immediate address into a register, this covers
every table the currently-loaded code can actually construct — then checks each one's first 300
word- and long-sized entries for a value equal to `target - base`. Validated first against the
already-known `$010000` table (correctly re-finds entry 18 → `$01049a`, LOCK, exactly matching §23a)
before trusting it on `$00b1e0`: **303 candidate table bases found in the whole image, zero of them
have any entry, of either size, resolving to `$00b1e0`.**

**Reading, now as settled as a static check can make it**: three independent techniques —
`find_ram_callers.py` (§15c, direct call text), `find_literal_ptr.py` (§48b, raw address literal),
`find_jump_table_hit.py` (§48c, displacement-table entry) — all return zero references to `$00b1e0`
anywhere in this loaded image. Combined with §30a (no disk-I/O-capable code anywhere in the image)
and §30b (the working tree's two-disk original has its disk 2 explicitly labelled "(Level)"), the
weight of evidence is that the one-disk crack's 72-room map *is* the whole reachable game for this
specific build — `$00b1e0`'s level-asset-reload logic reads as code shared with a multi-level
original but structurally unreachable here, not a live in-game mechanism gated behind an unfound
trigger. This still doesn't *prove* a negative (a table entry beyond 300 slots, or a table base
computed at runtime rather than a plain immediate literal, would both be invisible to this method),
but every technique this spike has for finding a caller statically has now been tried and come back
empty. If a second level exists at all for this build, it most likely requires the two-disk
original's physical disk-swap path (§30b) — a fresh investigation, not a continuation of this one.

## 49. Open item 2 (cadaver.md, the five doors' positive id words): they're real, populated type-6
    object ids, but structurally disjoint from LOCK/UNLOCK's own record type — rules out the
    "LOCK/UNLOCK flips a door's own flag" reading, doesn't yet explain what the id word is for
    (49th pass)

**49a. LOCK/UNLOCK's target and the door-transition executor's own flag test are two different
resource types, at two different record offsets, in two different tables — they cannot be the same
mechanism.** §38c's `$007280: btst #0,4(A0)` tests bit 0 of byte **+4** of a door descriptor — an
8-byte **type-4** record (§47a: index `$4adc6`, data `$6d35a`). §22c's LOCK/UNLOCK instead operate
on bit 2 of byte **+15** of an object record resolved through `$010738`→`$00c542`/`$00c56e` against
**types 6/9** (§22d: type 6 index `$4b596`, data `$6eb92`) — a structurally unrelated table, at a
different base address, with a different record layout and a different flag bit entirely. Item 2's
open question ("does LOCK/UNLOCK simply flip a door's own open/closed flag on an already-resident
door") is answered **no**, at least for the LOCK/UNLOCK mechanism as currently found: it has no
access to a type-4 door record at all, only type-6/9 object records.

**49b. The five positive id words are real, populated type-6 object ids, not garbage or dead data**
(`py/door_id_words.py`, this pass, reused `py/door_walk.py`'s own descriptor resolver). Read as a
type-6 id (§38a/§23c's `TYPE6_INDEX=$4b596`/`TYPE6_DATA=$6eb92`), all five (`53`, `73`, `155`,
`167`, `244`) resolve to a real, nonzero-size record (16 or 22 bytes, matching the sizes §23c's own
1000/1000-populated sweep would produce) — not one falls outside the table or hits an empty slot.
Each record's own bytes `+4..+5` echo the same id back (e.g. id `155`'s record reads
`...009b...` at that offset, `$009b`=155) — a self-id field the generic type-6 layout carries on
every record, not something door-specific. All five currently read `+15` bit 2 **clear**
(unlocked) in `room2_tunnel_entry.snap`.

**49c. Reading, and what's still open.** The id word is a valid handle into the same object-id
space LOCK/UNLOCK operate on (types 6/9), so "the door is gated by some object's lock state" is not
ruled out the way "LOCK/UNLOCK writes the door's own flag directly" now is — but nothing found this
pass shows *anything* reads the id word as a type-6/9 id: `$de5e` (§38d, the resolver actually
driving room transitions) only reads the descriptor's coordinate bytes, never touches `+2..+3`, and
no caller of `$010738`'s id-resolve path was found reaching from a door descriptor's own address
(only from the verb-interpreter's script stream, §22d). The bit-2-clear state on all five is
consistent with either "these are real lock objects, just not currently locked in this save state"
or "the id word means something else entirely and the type-6 resolution is coincidental" — five
valid ids out of a fully-populated 1000-slot table isn't strong evidence either way on its own.
**Concrete next step if picked up again**: `callcap` LOCK (opcode 18, §23a) against one of these
five ids (e.g. `155`) from a snapshot near that door, then re-run the door-transition trace (§38c)
across it and check whether `$007280`'s own `btst #0,4(A0)` result, or anything else in the
executor's flow, changes — the first causal (not just structural) test of whether the id word does
anything at all.

## 50. The causal test from §49c's own plan: `callcap` LOCK against door id `155` does not touch the
    door-transition executor's own flag byte — the id word is causally inert on this path (50th pass)

**50a.** From `room2_tunnel_entry.snap`, live via the REPL, following §24c's own recipe (`A1` → a
scratch big-endian id operand, `callcap` LOCK's entry address directly):

```
m 6d45a 8                         ; before: door 0x20's descriptor, bytes 44 23 00 9b 01 00 00 02
m 6faf5 1                         ; before: object id 155's own +15 byte = $00 (bit2 clear)
w 18140 009b0000                  ; scratch-poke $00 $9b (=155, big-endian) at $18140
callcap 1049a 5000 - A1=18140     ; call LOCK directly with A1 -> the scratch id buffer
m 6d45a 8                         ; after
m 6faf5 1                         ; after
```

Result: `regdelta ... A0 $00052e0c->$0006fae6 D1 $00000003->$0000009b`, confirming the call resolved
id 155 to exactly the record address `door_id_words.py` computed (§49b); `mem $06faf5 $00->$04` —
LOCK causally set bit 2, matching §24c's own result on id 144 byte-for-byte. **The door descriptor's
own 8 bytes at `$6d45a` (owner room 19's door 0x20) read identically before and after**: `44 23 00
9b 01 00 00 02`, so byte `+4` (the exact byte §38c's executor tests: `$007280: btst #0,4(A0)`) stays
`$01` throughout. The only other memory `callcap` reports touched is the call's own temporary stack
frame (`$0180e9`-`$0180f9`, below the live `A7`) — internal to the call, not persistent game state.

**50b. Reading.** This is the causal counterpart to §49a's structural argument, run against the
concrete next step §49c itself proposed: LOCK on a real, populated id that a door descriptor genuinely
points to (155, not an arbitrary test id like §24c's 144) provably flips that object's own lock flag
and provably leaves the door descriptor's executor-tested byte untouched. Combined with §49c's static
result (no caller anywhere in the image resolves a door descriptor's id word through the type-6/9
id-resolve path), Open item 1 is now doubly negative — structural and causal — on every mechanism
this spike has found: **nothing currently known reads or acts on the five doors' positive id words** (*superseded, §72*: `$00716e`-`$0071bc` reads them, `jsr $011256` against the rucksack; §49-§50 searched for a caller of the type-6 resolver and the reader uses the type-8 scan).
This doesn't prove the id word is meaningless (an unfound reader is still possible, same caveat as
every other "no caller found" result in this doc), but it removes the last untested "maybe LOCK's
target and the door executor still interact some other way we haven't poked" gap — the two mechanisms
are now shown disjoint both on paper and in a live call, matching exactly the kind of proof §24c
already set the precedent for.

## 51. Raw disk-layout inspection of the one-disk Empire crack: no second level's worth of data
    anywhere on the physical disk, independent of §48c/§48d's loaded-image caller search (51st pass)

> **Superseded (77th pass, `secrets.md` "Loading, the expander and the level directory").** The game has its own LZHUF expander (`$0118ec`) and nearly every level resource is packed, so the raw entropy/layout reading below (§51-§56, including §28c's and §56's "no depacker found") is wrong: the one-disk image holds **two** levels (directory at sector 400), the second loads and renders, and the Empire `[t]` Disk 2's levels 3 and 5 are damaged.

Dave's pushback on §48c/§48d (cadaver.md handoff, Open item 1) was that "no caller of `$00b1e0`
found in the loaded image" only rules out a *currently loaded* level-reload path, not a
runtime-loaded or self-modifying one reading a second level straight off disk. That's a real gap in
a caller search alone, so this pass inspected the `.st` image itself (`py/disk_layout.py`), a
data-only check with no emulator stepping, to see whether the disk even has a second level's data to
find.

**51a. Not a FAT12 volume with listable files.** The boot sector's BPB fields parse as a plausible
Atari-ST FAT12 superblock (512 bytes/sector, 2 sectors/cluster, 2 FATs, 5 sectors/FAT, 10
sectors/track, 2 sides, 1600 total sectors = 819200 bytes, matching the file size exactly). But the
root directory (`@ 0x1600`, 7 entries × 32 bytes per the BPB's own `root_entries` field) is 224 bytes
of `0xE5` ("deleted entry") with no live entries at all — there is no file table to hold a
separately-named level pack. This is the same shape as the Medway Boys compilation's Disk B
(README "Disk images"): a non-filesystem, self-booting disk whose own loader code reads fixed
absolute sectors, not files by name. Whatever content exists on this disk has to be found by where
it physically sits, not by directory listing.

**51b. Sector-by-sector data/blank scan.** Classifying each of the 1600 512-byte sectors as "blank"
(all bytes identical — the disk's erase/format filler) or "data" gives one dominant contiguous real
block plus a handful of small ones, not content spread densely across the disk:

- sector 0 (boot sector, 512B)
- sectors 20-28 (9 sectors, 4.6KB)
- sectors 30-171 (142 sectors, 71KB)
- sectors 190-216 (27 sectors, 13.5KB)
- **sectors 400-936 (537 sectors, 268.5KB) — the one large block, almost certainly the bulk of the
  game's graphics/room/object data already decoded (world map, sprites, resource tables §15b/§23c)**
- six scattered single/few-sector fragments between sectors 1395 and 1586 (512B-3.5KB each, total
  ~9KB) — too small individually to be a second level's assets; more likely loader/signature
  remnants from the crack itself (title-screen text, a cracktro/menu fragment, or the load-table
  the boot code reads to know where the big block starts)

Total real data: 373248 of 819200 bytes (45.6%). The remaining 54.4% (871 whole sectors) is uniform
filler, and — critically — it isn't scattered in with the real data as slack between two payloads;
it's one contiguous ~230KB gap (sectors 937-1394) right after the one big data block, then more
gaps around the small tail fragments. That's the shape of "one level's data, followed by unused
disk", not "two levels' data, one of them still unaccounted for".

**51c. Reading.** No depacker/decompressor has been found anywhere in this spike's disassembly
(§28c ruled it out of the room-3 "already resident" path specifically; no other pass has found one
either), so there's no live LZ-style mechanism that could be inflating a small on-disk blob into
several levels' worth of RAM content — what's on disk is what the game has to work with, roughly at
its own size. A single ~270KB contiguous block of real data, with the rest of an 800KB disk sitting
at the format's erase pattern, is consistent with this one-disk crack holding exactly the 72-room
map already fully decoded (§44) and nothing further, not a second level trimmed for space or
packed in elsewhere. This is not as strong as a positive proof — it doesn't rule out, for instance,
non-uniform "blank-looking" filler that happens to still decode to something (unlikely for a genuine
format-erase pattern, but not checked byte-for-byte against a known ST format-fill value), and it
doesn't identify what the six small tail fragments are. But combined with §48c/§48d's static
caller-search negative, this closes the physical half of Dave's own concrete next step: there is no
second level's worth of data sitting on this disk for any loader, however invoked, to find.

**52. §51's negative was specific to the one-disk crack; the two-disk original's own Disk 2 is a
real, distinct "levels" disk — reframes rather than contradicts §51.** §51 closed the question only
for the specific one-disk Empire image analysed there. The two-disk Image Works original (both crack
groups and a `[!]` verified dump) became available this pass (Dropbox, see the README's "Disk
images"), and two independent signals now point the same way for it:

- **Ground truth from Dave**: a commercial expansion for Cadaver existed that shipped as a straight
  replacement for Disk 2 — i.e. Disk 2 really is "the levels disk" as its own filename label
  ("(Level)") already implied, not inferred from this spike's own analysis.
- **Static disk-layout comparison** (two-disk Empire `[t]` trained crack, `py/disk_layout.py` plus an
  ad hoc follow-up script, `scratchpad/cadaver/agent_disk2_analysis/`, not yet promoted into
  `reversing/cadaver/py/`): Disk 2 is ~91.9% real (non-blank) data after correcting
  `disk_layout.py`'s classifier for a 3-byte repeating filler pattern it missed in the tail
  (`disk_layout.py` itself still reports the uncorrected 98.4% until it's extended to detect
  short-period fills, not just single-byte fills) — against Disk 1's 46.4% (§51b) and the one-disk
  image's 45.6% (§51). Disk 2 is confirmed not a duplicate of either (0.1-0.3% byte-identical at
  matching offsets, vs. Disk 1/one-disk's expected ~41% from sharing the same crack group's
  boot/intro code). Its real data sits in two large contiguous blocks (334KB/404KB, entropy
  7.6-7.97 b/B) that are markedly *flatter* in byte distribution than Disk 1's own already-proven
  272KB resource-table block (fewer duplicate 512B sectors: 0.8-1.4% vs. 27.4%; lower max
  single-byte frequency: 7-9% vs. 22.7%) — denser/more uniform than the disk's own confirmed-real
  content, the opposite of what "mostly padding" would look like.

**Open tension, not yet resolved**: no depacker exists anywhere in this spike's disassembly
(§28c/§51c), so if Disk 2's flatter distribution means it's genuinely compressed, nothing currently
known in the loaded image could unpack it — a decompressor would have to live in Disk 2's own
boot/loader sectors (0-7, before its payload starts at sector 7), never analysed because this spike
has never booted from Disk 2. Also unresolved: no readable strings and no fixed-record stride were
found in either of Disk 2's blocks (unlike Disk 1's plaintext story text at `0x4a1a`), so nothing
here positively identifies the content as *levels* specifically rather than some other bulk data —
that identification rests on Dave's external ground truth about the expansion pack, not on anything
internal to this pass's analysis.

**Live confirmation attempted, not reached**: tried booting the two-disk Empire `[t]` (trained)
release's Disk 1 to reach the "place levels disk" prompt and swap in Disk 2 live via the REPL's
`disk` command, matching §48d/§50/§51's own suggested next step. Abandoned after ~1.6 billion
emulated steps: this release's crack intro is a long scrolling multi-crew greet-list followed by an
"ok let us schlupz now..." loading-bar screen that **loops** (a 600M-step snapshot and a
1600M-step snapshot from the same run show the same screen, only the loading-bar pixels differ) —
roughly 100x the ~15M steps the plain one-disk release needs to reach gameplay. A controlled A/B/C/D
test (same snapshot, same 5M-step budget, with no key / space / return / '1' injected) produced
pixel-identical screens in all four cases, ruling out "needs a keypress to skip" as the explanation for
this specific 5M-step window — whatever gates the loop, it isn't a short keypress landing anywhere
in that window. Not pursued further this pass; the `[!]` (verified-dump, likely uncracked) two-disk
pair in the same Dropbox folder is the next thing to try if a live swap is still wanted, since an
uncracked original should have no cracktro at all.

**53. Live Disk 2 swap reached the "place levels disk" prompt for the first time, via the
Replicants/ST Amigos crack rather than Empire `[t]`; the game read Disk 2 and reported a disk
error, then a retry keypress produced a CPU runaway (53rd pass).** §52's next-step list named the
`[!]` verified-dump pair as cheapest to try first; that pair turned out to be `.stx` (Pasti
flux-dump format, 1.85MB, not a multiple of 512 bytes) rather than a raw `.st` sector image — this
emulator's loader has no format check and would silently misread it as garbage sectors rather than
erroring (`DEVELOPING.md`'s new disk-image note), so it was not booted. Extracted the untried
Replicants/ST Amigos crack-group pair instead (`Cadaver/disk1_replicants/`,
`Cadaver/disk2_replicants/`, both 819,200B raw `.st`, sha256 in the README).

Cold-booting Disk 1 (20M steps) lands in a *static* trainer "presents" screen ("HIT MADLY ON * KEY
FOR UNLIMITED LIVES") — confirmed genuinely parked (PC moved 10 bytes over a further 5M-step
no-input control) rather than looping like Empire `[t]`'s cracktro. Driving it with correctly
separated make/break `kbd` calls (see the `reverse-engineer-st-game` skill's new note — the first
attempt sent make+break in one call and was silently dropped, exactly the failure mode that note
now documents) reached, in order: the game's own title screen (parchment + candles, distinct from
the trainer screen, `replicants_ctrl_space.png`), a language-select screen ("1 ENGLISH / 2 FRANCAIS
/ 3 DEUTSCH", `replicants_space2_20M.png`), a "restore game, place a disk and press 0-9, or ESC to
start fresh" prompt (`replicants_english_v2.png`), and finally **"PLACE LEVELS DISK IN DRIVE ONE
AND PRESS A KEY"** (`replicants_esc_30M.png`) — the exact prompt §51/§52 wanted a live test against,
reached in under 100M total emulated steps versus Empire `[t]`'s 1.6-billion-step stall.

Swapping to `disk2_replicants` via the REPL's `disk` command (paths with spaces don't parse — the
REPL splits on raw whitespace with no quoting, copy to an unspaced filename first) and pressing a
key: the game read Disk 2 and put up **"THERE SEEMS TO BE AN ERROR ON THIS DISK. PRESS ANY KEY TO
RETRY"** (`replicants_disk2_swap_30M.png`) — a real, game-authored disk-format complaint, not a
hang or a silent stall. Retrying (re-swap + keypress) returned to the "place levels disk" prompt
rather than repeating the same error text (`replicants_disk2_retry_30M.png`), and pressing a key
again from there caused the emulated CPU to run away — `PC` reached `$230f8020` (impossible on a
24-bit-bus 68000; nowhere close to `disk2_replicants`'s $019200-based screen RAM or any code region
seen this pass) and the process hit the decoder's deliberate "MOVE.B with An operand is illegal"
guard (`68k.fs:1562`) and crashed with an unhandled exception, not a normal breakpoint stop.

Left open at the end of this pass whether the runaway was a genuine Disk-2 protection mechanism or
an artifact of this pass's own REPL sequence — §54 (next pass) found it does not reproduce.

**54. The 53rd pass's CPU runaway does not reproduce from a clean replay — four independent
keypress variants from `replicants_disk2_retry_30M.snap` all land in sane state (54th pass).**
Starting fresh from the "PLACE LEVELS DISK..." prompt snapshot (Disk 2 already mounted) and
sending a single keypress with no other REPL activity: space (`kbd 39`/`kbd b9`, 100000 steps
between make and break), Return (`kbd 1c`/`kbd 9c`, same spacing), Escape (`kbd 01`/`kbd 81`, same
spacing), and space again with zero steps between make and break — all four, run over 30M steps
each, land at a sane PC (`$00011b04`, `$00011b0e` for the zero-delay case) with no exception, and
all four reproduce **the same deterministic result across repeated invocations of the identical
command sequence**: the game re-reads Disk 2 and puts up "THERE SEEMS TO BE AN ERROR ON THIS DISK.
PRESS ANY KEY TO RETRY" again (`replicants_retry_replay_space.png`), i.e. it cycles the same disk
error rather than crashing — and a control run with no key input at all leaves `PC` parked at
`$00011ac6`, confirming the wait loop is genuinely idle until a key arrives, not itself racing
toward the runaway. Which specific key/timing the 53rd pass used was never captured (its REPL
script lived only in that session's log, not saved to a file), so this isn't a byte-for-byte replay
of that pass — but four different plausible choices all converging on the same safe, deterministic
disk-error cycle makes a real, reliably-triggerable copy-protection crash unlikely; the 53rd pass's
runaway looks like a one-off artifact of that session's exact (uncaptured) sequence rather than a
reproducible mechanism, emulator-general or protection-specific. Downgrades Open item 1 from "found
a game/emulator interaction to triage" to "seen once, not reproducible with typical input, not
worth further live-boot investigation without a specific new lead."

**55. §53's "ERROR ON THIS DISK" was this emulator's own bug, not a real crack/protection
failure — `MMU.LoadDiskA` trusted the swapped-in disk's boot-sector BPB for side count, and Disk
2's own BPB lies (55th pass).** Disk 2 is never booted through TOS — it's swapped in after the
game is already running and read only via its own raw FDC sector commands — so nothing ever
validates its BPB the way a real boot would. The Replicants/ST Amigos crack's `disk2.st` BPB
declares `heads=1` (a 409,600-byte single-sided disk) while the file itself is a real
819,200-byte double-sided dump (80 tracks × 2 sides × 10 sectors × 512 bytes, confirmed by direct
byte inspection of offsets 11-27). `MMU.fs`'s old `diskASides` derivation took that header at face
value, so every side-1 FDC read returned "no data" (`MMU.fs`'s `fdcSide >= diskASides` guard), and
the game's own protection code correctly — from its own point of view — reported that as a disk
read error and looped back to the retry prompt, exactly the behaviour §53/§54 characterised as
"a real, game-authored disk-format complaint." It wasn't wrong that the complaint was
game-authored; it was wrong about *why* the game was seeing bad data. Fixed in `MMU.fs`'s
`LoadDiskA`: prefer 2 sides when the file is big enough for a standard double-sided disk at the
declared sectors-per-track but the header claims only 1 (commit `5547ae9`). Proof:
`ATARI_TRACE_FDC=1` over the same swap-and-retry sequence that used to fail now shows a clean
sequential read of both sides of every track it reaches (track 0 side 0 through track 7 side 1
confirmed by this pass, ~149 reads, no "no data" results) into a buffer starting around `$05e000`
— genuinely new data successfully loaded from Disk 2 for the first time this workstream, side-1
included. The read is only ~10% into the disk (track 7 of 80) when the separate dispatch bug below
fires and derails execution, so this is not yet proof the *entire* disk reads clean end to end,
only that the sides fix is correct and side-1 reads that used to fail now succeed.

Past the successful load, the 53rd/54th passes' framing of "the disk 2 swap is unresolved" no
longer applies, but a new, separate wall appeared: `jsr (A2)` at `$00011602` (called from
`$00b7f0`/`$00b420`'s embedded-resource-stream dispatcher, generic mechanism at `$011598` reading
`{base,length,pos}` triples from a descriptor table at `(A5)+2538`, `A1=0` meaning "execute this
chunk in place rather than copy it") jumps to `$00021da0`. The `illegal`/`(line-A)`/`???mode7reg5`
noise this pass read there and attributed to stale framebuffer pixel data decoded as code
(`$20f00`-`$28cff`, §33b/§37a) was wrong on both counts, corrected by §57: it is real, intentional
Rob Northen protection code (a CPU-detection/self-decrypt chain), and it needed two genuine
emulator fixes, not a crack-patched-out check to trace further. The `$00b418` version-style check
(`cmp.w $41c.l,D0` falling through a neutered `nop` either way) is still a real, separately-true
observation about this crack's own patched-out gate; it just isn't what was stopping progress here.

## 56. Static graphics/level mining on `disk2_replicants.st`'s raw bytes: negative result across
    every width/layout tried, and two structural findings that narrow the next step (56th pass)

Following on from §52/§55's static disk-layout work (which used the two-disk Empire `[t]` crack's
Disk 2), this pass ran the same entropy/candidate-span method directly against the file now proven
to load correctly live, `disk2_replicants.st` — independent of item 1 (the crack dispatch bug),
per the README's own "not started this session, worth deciding priority on" framing.

**56a. `disk2_replicants.st` and Empire `[t]`'s Disk 2 are the same underlying payload.** A 4-byte-
aligned identical-byte sample across the full 819,200-byte images gives 98.3% identical (vs. 0.1-
0.3% for any of the already-established "genuinely different disk" pairs in §52) — confirming the
two crack groups' Disk 2s differ only in their own boot/loader sectors, not in the game content
itself, so §52's entropy/block findings (block A `$e00`-`$52800`, 334KB, entropy 7.72; block B
`$58c00`-`$bb600`, 404KB, entropy 7.62) apply unchanged to the file this spike can now actually
load.

**56b. `gfxview.py`'s automatic palette/span scan on the raw file finds 5 mid-entropy candidate
spans, each with 1-4 STF palettes embedded *inside* it rather than immediately before it** — a
different structural pattern from every previously-decoded asset in this game (the one-disk
crack's player sprite sheet and Disk 1's room-art candidates both had their palette pair sitting
just *before* the data, per graphics.md §2). The five spans (`tools/gfxview.py --raw
disk2_replicants.st`, offsets confirmed against `disk2.html`'s own auto-detected data-span list):

| span | size | entropy | palette(s) inside |
|---|---|---|---|
| `$13000`-`$19800` | 26 KB | 4.75 | none found inside; nearest is `$39430` (outside) |
| `$36800`-`$40000` | 38 KB | 5.02 | `$39430`, `$39470` (9 colours each) |
| `$5d000`-`$67000` | 40 KB | 4.99 | `$5fc02` (9), `$611b0` (6) |
| `$82000`-`$8a800` | 34 KB | 5.00 | `$84a68`,`$84afc`,`$84b3c`,`$84b78` (9-10), `$88034`,`$8806a`,`$880a0` (9) |
| `$a8000`-`$ae800` | 26 KB | 4.69 | `$adb28` (7) |

These five spans are markedly lower-entropy (4.69-5.02) than blocks A/B (7.6-7.7), i.e. they read
as the better a-priori graphics candidates by the same entropy heuristic that found the one-disk
crack's real sprite sheet (which topped out at 5.25, graphics.md §2's original 7-span scan).

**56c. Negative result: none of the 5 candidate spans, nor blocks A/B, decode to any coherent
tile/sprite/room structure.** Rendered every one of the 5 spans at 7 widths each (16/32/48/64/
96/160/320 px, st-interleaved 4bpp, each span's own nearest/embedded palette) plus 2 widths each
as raw chunky8 (1 byte/pixel, palette-independent) — 49 renders total
(`scratchpad/cadaver/disk2_gfx/try_widths.py`, ad hoc, not promoted to `tools/`) — every single one
is visually indistinguishable from noise at any width tried; no repeating tile-column structure,
no silhouette, nothing resembling the one-disk sprite sheet's immediate "streaky noise, then
coherent art" transition (graphics.md §2). Also rendered blocks A/B the same way (chunky8, 160/320
px): same result, uniform noise throughout. This is a genuine negative, not an absence of trying —
unlike the confirmed player sprite sheet, which only needed the *right* width/height (struct
fields `+50`/`+51`, graphics.md §2) to snap into a recognisable image at the *first* width tried
once those fields were read; nothing here snapped into anything recognisable across the full grid
searched.

**56d. Disk 2's own boot sector carries no real code, closing off `disk2_findings.md`'s proposed
next step.** That file (52nd pass, not yet promoted into this doc) recommended checking sectors
0-7 for loader code the one-disk release's boot path doesn't have, in case a depacker for blocks
A/B lives there. A linear disassembly of sector 0 (`disassemble.py --rom disk2_replicants.st
--base 0 --linear 0 512`) shows only the boot-sector signature bytes and BPB fields, then 470+
bytes of `ori.b #$0,D0` (all-zero) with no branch, jump or subroutine anywhere in the sector — i.e.
there is no boot-code payload here to disassemble, consistent with §55's own finding that this
disk is *never booted* (it's swapped in mid-game, so TOS never executes its boot sector at all).
Any depacker for blocks A/B, if one exists, is not hiding in Disk 2's own unexecuted boot sector;
it would have to be part of the resident Disk-1-loaded code already fully disassembled and
confirmed to contain no such routine (§28c/§51c).

**Net effect on the open-item split.** Static guessing (candidate-span entropy scan → try every
plausible pixel width/layout) is the method that worked for the one-disk crack's real graphics and
has now been run exhaustively against Disk 2's own bytes without result. The two things that
would move this forward — the real record/pixel format grounded in the code that actually
interprets this data (the way `+50`/`+51` grounded the sprite sheet, graphics.md §2), or a live
view of what the game itself does with these bytes once loaded — both require the game to actually
read and process this data, which at the time of this pass was still blocked past track 7 (§57
gets past that wall, onto a new one). This pass's negative result narrows, rather than closes, the
open-item choice: item 2's static half is now exhausted short of guessing further widths blind, and
a live read is the more promising path to *any* further progress on Disk 2's content until a
code-grounded struct definition becomes available.

## 57. The "crack dispatch bug" was two real emulator gaps, not a data or dispatch problem;
    fixing both gets past `$00b418` onto a new, separate FDC wall (57th pass)

§55's `jsr (A2)` -> `$00021da0` wall was misdiagnosed as stale framebuffer data misread as code
(corrected above). Stepping past it (`ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll
resume scratchpad/cadaver/agent_disk2_wall/before_jsr.snap repl`, then `s <n>`/`r` from the REPL)
shows `$00021da0` is real Rob Northen protection code: it installs its own illegal-instruction
handler (vector 4, at `$10`) pointing into itself, then deliberately executes a reserved opcode to
trigger that trap — a CPU-detection probe (a genuine 68000 traps an unassigned opcode to vector 4;
a 68010+ emulator that mis-implements the probed opcode as valid would not). Two such probes back
to back, both landing on a genuine gap in this emulator rather than the crack:

- **`$4E7A`/`$4E7B` (MOVEC)**: already covered by the `Illegal` pattern (`Instructions.fs`'s own
  comment already names this exact crack as the reason it was added).
- **`$712c`, a bit-8-set MOVEQ encoding** (line-0111 has no other valid 68000 instruction; bit 8
  must be 0 for MOVEQ, so this is equally reserved and equally traps to vector 4 on real hardware):
  not covered — `DecodeBucket7`'s wildcard threw an unhandled .NET exception instead, crashing the
  whole process. This *was* "the crack dispatch bug": the emulator crashing here, not a
  neutered version check or a data-driven dispatch problem. Fixed by adding a `ReservedMoveq`
  pattern (`Instructions.fs`) and wiring it into `DecodeBucket7` to enter vector 4 like `Illegal`
  does (`68k.fs`, commit `1cb269b`).

Past both probes, the crack arms a third stage: it sets CCR's T1 (trace) bit and lets execution
free-run, using the trace exception (vector 9) as a single-step decrypt loop (trap after every
instruction, decrypt the next one, resume) — the same technique as the two probes, one level up.
This emulator's `Step()` computed a `TraceMode` property from CCR but never consumed it anywhere;
trace-mode single-stepping was entirely unimplemented, so the crack's loop just span forever
(confirmed via `watch 24 4` and two `r` dumps 2M steps apart showing byte-identical state — a real
infinite loop, not slow progress) instead of ever trapping. Fixed by sampling `TraceMode` before
each instruction and entering vector 9 afterward when the instruction completed via the plain
decode path (`68k.fs`, commit `1f41114`) — `EnterVector`/`EnterGroup0Vector` now also clear T1 on
entry like `EnterInterrupt`/`FetchTargetOrFault` already did, so a traced exception handler doesn't
immediately re-trace itself. Both fixes carry their own regression-net proof in their commit
messages (`verify` PASS, 30M-step diskless boot snapshot byte-identical before/after, full 680x0
selftest 1,000,051 pass / 0 fail / 9 skip unchanged — no SingleStepTests vector seeds T1, so the
trace fix is unexercised by that corpus but doesn't regress it).

With both fixes in, `before_jsr.snap` run forward (30M steps) reaches genuinely new code —
`A4=$ffff8604` (the FDC/DMA register), confirmed via `ATARI_TRACE_FDC=1` to be issuing real
`READ-SECTOR drive=0 track=0 side=0 sector=8` commands — but stalls at a new wall: the read
repeatedly comes back "no data", the crack retries with a `type I $03` (Restore-to-track-0) between
attempts, and PC only crawls from `$11b00` to `$11b0e` across those 30M steps (`scratchpad/cadaver/
disk2_past_dispatch_30M.snap`). Not yet diagnosed: whether track 0/sector 8 is genuinely absent
from whichever disk is mounted in drive A at this point in the sequence (a disk-swap step missed
somewhere upstream), an FDC modeling gap for whatever exact command sequence this is, or something
else — this is real, further progress, not the same wall in a new shape, and is next session's
starting point.

## 58. §57's "no data" FDC wall was neither a missing sector nor an FDC gap — the driving REPL
    session simply never remounted Disk 2 after loading the bare `.snap` (58th pass)

`MMU.LoadDiskA`'s own doc comment already says disk-A's mounted image is deliberately excluded
from `MmuSnapshot` ("which disk is in a drive is external, physical-world state, not something a
state save should capture or a state load should disturb") — `resume`ing any `.snap` therefore
starts with no disk in drive A (`diskA = None`) until the REPL's `disk <path>` command (or
`--disk-a`/`ATARI_DISK_A`) re-mounts one. §57's own driving session stepped straight from
`before_jsr.snap` with no `disk` command first, so `tryReadSector`'s `None -> false` case fired for
every single FDC request — a track/sector-independent "no data" that looks identical, byte for
byte, to a genuinely absent sector. Reproduced exactly: re-running the identical `s 30000000` from
`before_jsr.snap` with no disk mounted reproduces §57's whole observed sequence line for line (the
`$e0`/`$d0` probe pair three times, `type I $03` restore to track 0, then `READ-SECTOR track=0
side=0 sector=8 -> no data` on repeat, `scratchpad/cadaver/full_trace_fdc.log`). Re-running the same
`before_jsr.snap` and the same step count with `disk ../Cadaver/disk2_replicants/disk2.st` issued
first instead: the exact same command sequence now reads `-> OK` (`scratchpad/cadaver/
full_trace_mounted_fdc.log`), and execution sails on past the old wall — 121 reads, 0 "no data",
reaching track 13 side 1 by 30M steps (PC=`$0000da54`) and PC=`$00015254` by 90M steps
(`scratchpad/cadaver/past_wall_mounted_{30,60,90}M.snap`). At 90M steps the screen renders as the
already-known "DAY 1 / BOAT / CAVERN" room (`scratchpad/cadaver/past_wall_mounted_90M.png`, pixel-
identical framing to the existing `boat_hotspot.png`) — real gameplay, not a crash or a stall, but
not yet proof of Disk-2-exclusive content either: reaching the same Day-1 room this pass's dispatcher
was already known to render doesn't by itself show Disk 2 supplies anything the one-disk crack
didn't already have resident. Downgrades item 1 from "an unresolved wall, cause unknown" to "the
REPL workflow's own gap, now fixed by remounting the disk after every snapshot load" — no emulator
change needed, and the new open question is a different, narrower one (below).

## 59. Open item 1 (does Disk 2 add content beyond the known 72-room map): the room table itself is
    unchanged, and past the wall the game is not in normal interactive gameplay at all — the
    sprite/entity array is empty and joystick input has zero effect (59th pass)

**59a. `world_map.py`'s hardcoded resource-manager addresses were stale for the two-disk build,
producing a false "100/100 populated, massive overlap" reading.** The type-3 index-table/data-area
addresses (§38a) are not fixed constants — they're read out of `(A5)+96`'s resource manager at
runtime, and the two-disk Replicants build's whole resource manager sits **exactly `$100` bytes**
past the one-disk build's (`room2_tunnel_entry.snap`: A5=`$18152`, resmgr=`$4a466`, type-3
idx=`$4ac36`/data=`$6bf0a`; `past_wall_mounted_90M.snap`: A5=`$182b4`, resmgr=`$4a566`, type-3
idx=`$4ad36`/data=`$6c00a` — every one of the first 9 resource types shifted by the same `$100`,
confirmed table by table). `world_map.py` hardcoded the old build's addresses, so running it
against a Disk 2 snapshot walked 100 garbage "slots" all pointing at the same stray `$75894`
record and reported nonsensical universal overlap. Fixed: `world_map.py` now resolves type 3's
index-table/data-area pointers fresh from each snapshot's own `(A5)+96` (`resource_type()`, a
small reusable helper), matching the manual resource-manager decode above exactly. Re-run against
the Disk 2 snapshot: **72/100 populated, 117 adjacent pairs (99 edge, 18 corner, 0 overlap)** —
byte-identical rectangles, slot for slot, to the one-disk build's own map. `door_walk.py` has the
same staleness bug (`TYPE4_INDEX`/`TYPE4_DATA` hardcoded, plus a now-broken import of the constants
`world_map.py` no longer exports) and needs the same fix; not done this pass, flagged as a
background task instead of taking time from the live question below.

**59b. The type-3 room table itself supplies nothing new**: same 72 rooms, same rectangles, same
adjacency graph as the one-disk crack already fully mapped (§44). Whatever Disk 2 contributes, it
is not additional entries in this table, at least not by the time execution reaches
`past_wall_mounted_90M.snap`.

**59c. Driving real joystick input from `past_wall_mounted_90M.snap` appeared to produce no visible
effect** — the player sprite never seemed to move, the room never changed, and the rendered frame
was pixel-identical before and after. Five separate `kbd ff 08` (joystick-1 right, make) /
`s 3000000` / `kbd ff 00` (release) / `s 500000` cycles (15M steps total), and a variant trying a
space keypress first in case a "you found the Silver Coin" pickup notice was blocking movement
input, both left `164(A5)`'s current-room field at `$6c00a` (CAVERN/slot 0, unchanged) and the
rendered screen pixel-identical to the starting frame. The main loop was genuinely alive and running
frames (the shifter base keeps alternating `$19200`/`$21000` each cycle, and `bpc 80cc` — the
sprite/HUD blit routine — hits within 562k steps of a fresh joystick press), so this wasn't a hung
emulator. **§60 shows the reading was wrong: input was reaching a genuinely-live player entity the
whole time, at an address one `(A5)+56` re-derivation away from the one this pass happened to check
— see §60 for the corrected picture.**

**59d. The suspected cause, at the time: the player/entity sprite array reads empty.** §19a/§32c's
own already-documented sprite-object array base, `$038338` (player at slot 0), read all-zero in
every snapshot checked this pass. **Superseded by §60**: `$038338` is stale for this build, exactly
like §59a's resource-manager addresses — the real array sits `$100` bytes higher, and the entity
there is not empty at all.

## 60. Item 1 closed: the player entity is genuinely live — `$038338` was simply stale for the
    two-disk build, the same `$100`-shift bug §59a already found in the resource manager (61st pass)

**60a. `A6` at the real call site (`$00d93c`'s `bsr $7dd6`, per §32c/§33b) reads `$0003896a` in this
build, not `$038338`.** Two `bpc d93c 1` samples 8.7M steps apart (one before any input, one after a
full `kbd ff 08`/`kbd ff 00` right-hold cycle) both gave identical `A6=$0003896a`, `A3=$0003896a` —
stable, not a per-iteration transient. That address holds real, structured, non-zero bytes (`44 42
3d 3b ...`), unlike `$038338`, which is a plausible-looking bbox (`[68,66,61,59]`) per §19a's
documented `[x_lead,y_lead,x_trail,y_trail]` layout but did **not** move under a follow-up right-hold
test read back from that same fixed address without re-synchronizing on the breakpoint — a red flag
that `$0003896a` is a live *loop-iteration* pointer (this build processes multiple entries per frame
a few dozen steps apart, confirmed by three further `bpc d93c` hits landing after only 19–27 steps
each), not the array's own stable base, so a raw un-synchronized re-read of it after millions of
steps is reading whatever entry happens to occupy that address by then, not necessarily the same
one. Useful as a first proof-of-life signal, but not the address to build on.

**60b. The reliable derivation matches §59a's fix shape exactly: resolve `56(A5)` fresh from the live
snapshot, don't hardcode `$038338`.** `SpriteObjectArrayPtr_A5Plus56` (§21a) is, like the type-3
resource-manager pointer, a per-build runtime value read out of a fixed `A5`-relative field, not a
link-time constant. In `past_wall_mounted_90M.snap` (`A5=$182b4`), `56(A5)` = `$182ec` reads `00 03
84 38` = **`$038438`** — exactly `$038338 + $100`, the identical shift §59a found in the resource
manager, now confirmed in a second, unrelated `A5`-relative field. `$038438`'s first 4 bytes read
`19 17 13 11` = `[25,23,19,17]` — **byte-for-byte the exact canonical starting bbox** §19a documents
for a fresh route from this same starting position. Not a coincidence: this is genuinely the live
player slot.

**60c. Movement is real once read from the corrected address.** From `past_wall_mounted_90M.snap`,
`kbd ff 08` (right, make) / `s 3000000` / `kbd ff 00` (release) / `s 500000`, then `m 38438 4`:
`[25,23,19,17]` → `[69,23,63,17]` — x moved 44 units right, y unchanged, exactly the shape of a real
rightward walk leg. A second identical hold cycle produced no further movement (`[69,23,63,17]`
unchanged) — consistent with hitting a boundary, not a dead entity. Reproduced in
`scratchpad/cadaver/retest_movement_038438.log`.

**Net effect on item 1**: closed as a reframe, not a real gameplay dead-end. The 59th pass's
"genuinely unresponsive to input" finding (§59c) and its two open hypotheses (§59d) are both
superseded — hypothesis (a) was right, but the specific evidence for it (the `bpc 80cc` sample's
`A6=$88`) was a red herring; the actual fix is the same `+$100` resource-manager-style shift already
proven in §59a, applied to `56(A5)` instead of `(A5)+96`. `$00e80c`'s boot-time activation call needs
no further investigation — the entity it spawns is present and correctly positioned. The dynamic
question this reopens is the one §59b/§59 originally set out to answer: does Disk 2 add reachable
content beyond the 72-room map, now that the player can actually be driven through it. Not yet
explored this pass — see Open item 1 below.

## 61. A real room crossing (CAVERN→TUNNEL) driven live in the two-disk build from the corrected
    `56(A5)`/`164(A5)` addresses — the drive technique generalizes, but this crossing itself is
    known content, not new (62nd pass)

**Current-room field re-derived the same way as the player-slot fix.** `164(A5)` (`$18358` in
`past_wall_mounted_90M.snap`) reads `00 06 c0 0a` = `$6c00a`, exactly `world_map.py`'s own
`data_area` base for this snapshot's type-3 resource manager — i.e. slot 0 (CAVERN)'s own record
address, offset 0 into the data area. Confirms the field the 61st pass's handoff pointed to without
yet reading it live.

**`door_walk.py`'s door `0x32`** (candidate `(20,17)`, `0→1 (edge)`) is CAVERN's real door into
TUNNEL, consistent with every prior pass's CAVERN↔TUNNEL work on the one-disk build. A straight
`kbd ff 02` (Down) hold from `past_wall_mounted_90M.snap` moved the bbox 11 units
(`[25,23,19,17]`→`[25,34,19,28]`) then stalled on a second hold (room pointer unchanged at
`$6c00a`) — an in-room obstacle, not the crossing. The documented **Right→Up** zigzag (§32, one-disk
build) reproduces on this two-disk snapshot instead: `kbd ff 08` (Right, 1.2M steps) moved the bbox
to `[69,23,63,17]` (same stall point §60c already found), then `kbd ff 01` (Up, 500k steps) crossed
outright — `164(A5)` flipped from `$6c00a` to `$6c072`, exactly `world_map.py`'s slot 1 (TUNNEL) rec
address (`data_area + 104`, CAVERN's own `size`). `snap_render.py` on the post-crossing snapshot
(`scratchpad/cadaver/disk2_zigzag_probe1.snap`) shows the status bar reading `TUNNEL`/`DAY 1`, the
same room the one-disk crack's own milestones already document — not committed as a new asset,
since it isn't one.

**A pixel diff against the one-disk build's own `room2_tunnel_entry.png` milestone confirms TUNNEL's
room art itself is unchanged.** `disk2_tunnel_probe1.png` vs `room2_tunnel_entry.png`: 1,552 of
64,000 pixels differ (bbox `(96,61)-(312,191)`, the room-graphic/icon-panel area), but a visual
compare shows the same isometric TUNNEL scene, same inventory panel population — the difference is
consistent with the player sprite standing at a slightly different position/facing after two
different approach routes, not a content change. Confirms §59b's room-table finding (byte-identical
72-room map) extends to at least this one room's rendered art, not just its geometry.

**(Retired, `secrets.md`: `2516(A5)` is maximum health; the day is `2166(A5)`.) The `2516(A5)` "day-count/variant selector" candidate §32a flagged but never confirmed reads
`100` in `past_wall_mounted_90M.snap`**, not a small day index — inconsistent with it being a
literal "Day 1" counter (the status bar's "DAY 1" text is evidently a separate field). Not pursued
further this pass; still unconfirmed either way, see Open item 3 below.

**Net effect on item 1**: the drive mechanism (corrected `56(A5)` for the player, `164(A5)` for the
current room, `door_walk.py`'s graph for where each door leads) is now proven live end to end in the
two-disk build, not just in principle, and this first crossing plus its pixel-level check both land
on already-known, unchanged content (TUNNEL). Two independent checks now agree Disk 2 does not add
anything to the spatial room table or its rendered geometry, at least for the two rooms reachable
from this snapshot — the open question is narrowing toward *whether Disk 2's content is reachable
from here at all*, versus being gated behind a mechanism not yet exercised (a day-progression event,
or a mid-game "insert levels disk" prompt distinct from the one-time boot-time swap already used to
build this snapshot). See the open items below for the next concrete tests.

## 62. Disk 2's whole contribution is a one-time boot-time load, already complete by step 30M — zero
    further FDC activity through step 90M or across a real room crossing (63rd pass)

Open item 1's second concrete test from the 62nd pass's handoff: does the boot-time Disk1→Disk2 swap
that built `past_wall_mounted_90M.snap` read Disk 2 only once at boot, or is more of it gated behind
further game progress? §58 already traced the first 30M steps (`before_jsr.snap`, since lost between
sessions) and found 121 sector reads, all `-> OK`, ending at track 13 side 1 — but that trace never
covered the remaining 60M steps to `past_wall_mounted_90M.snap`, so whether reads continue past 30M
was unknown.

**62a. Resuming `past_wall_mounted_30M.snap`, remounting Disk 2, and stepping the remaining 60M steps
under `ATARI_TRACE_FDC=1` produces an empty FDC trace — zero register writes, zero commands, zero
reads.** `dotnet exec` raw argv `resume scratchpad/cadaver/past_wall_mounted_30M.snap repl` with
`disk ../Cadaver/disk2_replicants/disk2.st` / `s 60000000` on stdin
(`scratchpad/cadaver/probe_fdc_30to90M.repl`) lands at `PC=$00015254`, exactly the address the 58th
pass's from-scratch 90M-step run reached — reproducible, so the empty trace isn't a broken harness,
it's a genuine negative. Combined with §58's own 30M-step trace, the full boot-to-`past_wall_mounted_
90M.snap` picture is now: 121 reads in the first 30M steps, then nothing for the next 60M.

**62b. Re-running §61's own CAVERN→TUNNEL zigzag crossing under the same `ATARI_TRACE_FDC=1`
confirms the crossing itself touches the FDC zero times too.** Same recipe as `probe_zigzag_disk2.
repl`, same result (`164(A5)` `$6c00a`→`$6c072`, final `PC=$00006cb2` matching `disk2_zigzag_
probe1.snap` exactly) — the FDC trace file is empty end to end.

**Net effect on item 1**: the one-time-load hypothesis is now the better-supported reading, not just
the "plausible given a levels-disk framing" guess the 62nd pass's handoff left it as. Whatever Disk 2
contributes was fully read into RAM in the first 30M boot steps and never touched again — not on a
60M-step idle run, and not across a real room crossing that's the closest thing this spike has driven
to "game progress" from this snapshot. This doesn't rule out a trigger deeper in the game than
anything reached so far (a day-progression event, an explicit "insert levels disk" prompt distinct
from this one-time boot swap), but it does rule out the crossing/idle-time mechanisms as sources of
further disk activity, narrowing what "further game progress" could even mean here.

## 63. TUNNEL has no untested door left to try — its only two doors besides the CAVERN link are
    structurally incapable of loading a third room, not just unexplored (64th pass)

The 62nd pass's handoff proposed driving from `disk2_zigzag_probe1.snap` (standing in TUNNEL) to a
room not already documented, with `ATARI_TRACE_FDC=1` armed, as the one remaining live test for item
1. Running `py/door_walk.py` fresh against that exact two-disk-build snapshot first, to pick a real
target, shows there isn't one:

```
door 0x32 candidate=(20,17) [id=0 hardcoded-link]                          0->1 (edge), 1->self
door 0x33 candidate=(20,11) [id=-1 sound-cue-only, no room commit]         1->2 (edge), 2->self
door 0x3b candidate=(22,20) [id=73 generic-lookup, always-miss per §27c]   0->self, 8->0 (edge)
```

These are the only three door ids referencing CAVERN (slot 0) or TUNNEL (slot 1) anywhere in the
71-door table. `0x32` is the CAVERN↔TUNNEL link already driven live in §61. The other two are not
untested leads, they're already-closed by mechanism (§27c) or by an earlier live test (*both conclusions retired in §72: `$33` is the lever's door, §71, and `$3b` opens into room 8 for the iron key 73*):

- **`0x3b` is CAVERN's own east door from §13 (17th pass)** — id 73 decimal is exactly `$49`, the
  target id §13 already named, live-triggered, and found resolving to "already resident" (no new
  room). `door_walk.py`'s geometric read confirms *why*, independent of any id lookup or game-state
  gate: candidate `(22,20)` sits inside CAVERN's own rectangle (`[12,18]-[22,28]`), so `$de5e`'s
  point-in-rect scan can only ever return CAVERN itself. Per §27c, the id word never selects the
  destination at all (even a populated type-8 table wouldn't change this), so this is a permanent
  self-loop, not a state-dependent one.
- **`0x33` is TUNNEL's own second entry from §10b** — sentinel target `$ffff` (id -1). §27c's read of
  the portal-match code says this sentinel takes a distinct branch that pushes a ring-304 sound/event
  opcode and **never reaches `$de5e` or any room-load call at all** — structurally inert, not merely
  unresolved. A live check confirms the point is moot anyway: holding Up from `disk2_zigzag_probe1.
  snap` for 3M then 6M further steps (`probe_room2_up.repl`/`probe_room2_up2.repl`) produced zero
  movement in the player's own bbox (`$038438`, unchanged `[23,12,17,6]`) and zero FDC activity;
  sliding left first (`probe_room2_leftup.repl`, bbox `[23,12,17,6]`→`[14,12,8,6]` under a real
  9-unit Left move, confirming input still works) then holding Up again was also fully blocked at
  the same y, and again zero FDC activity. TUNNEL's north wall is solid at every x tried; §10b/§10c
  already showed this table has no live-triggerable third entry in the one-disk build, and this pass
  confirms the two-disk build's own portal table matches that shape.

**Net effect on item 1**: this closes off the 62nd pass's proposed next test as inapplicable, not
just unproductive — CAVERN and TUNNEL, the only two rooms this spike has ever driven the player
through, have no door capable of committing a third room, by the game's own proven door-descriptor
mechanism (§27c), independent of Disk 2 or any other game state. Combined with §47's whole-map static
result (all 71 doors resolve to their owner or an immediate rectangle neighbour, zero teleports —
proven against the one-disk build, but the type-3 room table and now this door table both read
byte-identical from the live two-disk snapshot) and §62's full-trace FDC negative, three independent
subsystems (room table, door/portal mechanism, FDC) now agree from three different angles that
nothing reachable from this snapshot ever surfaces a fourth room. The remaining gap named in the
62nd/63rd pass handoffs — a deeper in-game trigger (day-progression, an explicit disk-swap prompt)
this spike has never reached — is unchanged by this pass; it just confirms that reaching it, if it
exists, needs progress this spike doesn't yet know how to make, not a different door out of CAVERN or
TUNNEL.

## 64. The object-verb interpreter's 59-entry dispatch table mapped against the full debug-string
    vocabulary, not just LOCK — three more opcode ids confirmed, one causally proven live, and the
    rest of the verb vocabulary's handlers located even where the exact id isn't pinned (70th pass)

> **Corrected (77th pass, `secrets.md` "Object scripts: who runs the verb interpreter").** The verb table is at `$00ffba` and has 94 entries (first word `$bc` = its size; it ends where `$010076` begins); the consumer `$00fe54` indexes it there. The 59 entries read from `$010000` here and in §24 and §64 are only its last 59 with every target off by `$46`, and their ids are the true ids minus 35: hence §64d's mid-instruction landings, and "UNLOCK is not in the table" is false (LOCK is verb 54, UNLOCK 55, KILL/UNINV/WAKE/SLEEP 50/89/74/75). The interpreter's caller is the ring-304 consumer `$00fdbc`, which runs an object's script blocks on a matching queued event (open item 1 closed; proofs in `secrets.md`).

§23a validated the dispatch table's shape by resolving 6 of its 59 entries to plausible handler
prologues, but only ever matched a debug string to one of them (LOCK = id 18). This pass generalizes
that one-off address match into a repeatable scan (`py/verb_opcode_map.py`): read the debug-string
table's own addresses directly out of RAM instead of quoting them from §22b's prose, decode all 59
dispatch entries, and for each one follow its straight-line code (treating an unconditional
`bra`/`jmp` as a same-routine continuation, one level of conditional-branch following beyond that)
looking for a `lea <string>.l,A0` matching one of the real string addresses. This is deliberately
shallow — an earlier, unbounded version of the walk wandered into unrelated neighbouring routines and
reported strings that belong to a different handler entirely (caught by hand before trusting it, not
by an automated check) — so a "no verb found" result below means "not found by this bounded walk", not
"proven absent".

### 64a. Three more opcode ids confirmed by exact address match, one now causally proven live

- **id 1 (`$010914`) is a CREATE-style allocator.** Clean prologue (`moveq #0,D1; move.b (A1)+,D1;
  lsl.w #8,D1; move.b (A1)+,D1` — a 16-bit operand read, then a sign check against `348(A5)`, the
  same "current actor" global §49/§50 already named), reaching `"CREATE SIZE ZERO"` when a
  size-or-count check via `bsr $c5d2` comes back non-positive. **Has real internal callers** — unlike
  every other opcode found so far, `find_ram_callers.py` shows `bsr $10914` from `$010844`, inside a
  *different* handler (the one whose own error path prints `"EXCEEDED ADD LIST SPACE"`, `$01083e`,
  which itself starts with the shared `bsr $10738` object-id resolve) — i.e. **one verb handler calls
  another directly as a subroutine**, not only through the byte-dispatch table. The caller is still
  inside the interpreter's own `$010000`-`$011256` span, so this doesn't change §24b's external-
  reachability negative, but it's the first confirmed case of handler-to-handler composition in this
  system.
- **id 15 (`$01039a`) is UNINV, found the 73rd pass** and, like STOPACTI below, lands mid-instruction:
  `$01039a` sits 4 bytes into the preceding `bclr #0,6(A0,D0.w)` (UNINV's own success-path instruction,
  reached normally from its real resolver at `$01038a`), on the instruction's own EA-extension word.
  Executed as an opcode in its own right, those 2 bytes decode as a harmless `ori.b #$75,D6` — `D6` is
  never read again before the next real branch, so the effect is provably side-effect-free — landing
  cleanly on the real `rts` at `$01039c`, then `bra $103a2` into the "UNINV A NON-EXISTANT CRE" print
  block. Same shape as STOPACTI's own anomaly below, one instruction-family over. §64b's table below
  already had this address as UNINV's "handler entry" (found independently by the 70th pass's
  debug-string scan); this pass ties it to the numeric table slot and confirms *why* the address looked
  slightly unusual — it isn't a clean entry point, it's a deliberately-reused tail landing.
- **id 31 (`$010e7e`) is STOPACTI**, with a caveat: the raw word at the table target is `$f8ba`, an
  F-line opcode this disassembler doesn't decode (and which would fault on real 68000 hardware if
  actually executed) — not one of the "rare instruction family" gaps this repo's disassembler is
  already known to have (movep etc.), and not explained this pass. Two bytes later (`$010e80`) the
  code is clean and unambiguous: `beq $10e84 / bra $10e94`, the `beq` target prints `"STOP ACTI
  NON-X OBJECT"` and the fallthrough does `bset #6,15(A0)` — bit 6 of the same `+15` byte LOCK/UNLOCK
  use for bit 2 (§22c), confirming `+15` is a general per-object flag byte, not lock-specific. Its
  paired opcode, GOACTI, sits immediately before it at `$010e5c` (same shape, `bclr #6,15(A0)` on
  success) but isn't one of the 59 resolved table targets — the same "verb has no table slot" gap
  §23b already found for UNLOCK.
- **id 32 (`$010ea2`) is MOVE, an action-only bypass of the normal resolve gate, found the 73rd pass.**
  `$010ea2` is a fully-aligned, clean instruction: `bra $10eb4`, sitting immediately after MOVE's real
  resolve-gated entry (`$010e9c: bsr $10738; beq $10ea4` fail → `"MOVE A NON-X OBJECT"`, `$0178d6`;
  `bra $10eb4` success). `$10eb4` is MOVE's write action: `move.b 13(A0),D0; adda.w D0,A0; move.b
  (A1)+,3/4/5(A0); rts` — writes 3 script-stream bytes into the object's own position fields (`+3/+4/
  +5`). Unlike every other pinned id, this table slot skips the resolve/existence check entirely and
  always performs the write using whatever `A0` already holds when reached this way.
- **id 34 (`$010ee2`) is UNLOCK CHEST, now proven causally, not just structurally.** Static: `bsr
  $10738` (resolve) → on success, `moveq #0,D0; move.b 12(A0),D0; clr.w 2(A0,D0.w)` — clears a 16-bit
  field at `object+2` indexed by the object's own `+12` byte, i.e. a per-object array of chest-slot
  words starting at `+2`, a different field and a different addressing shape from LOCK/UNLOCK's fixed
  `+15` bit. Live, from `room2_tunnel_entry.snap`, reusing §24c/§50a's own `callcap`-on-the-handler-
  directly recipe against the already-known lever object (144, `$06fa0e`, `+12` byte reads `$22`):
  ```
  m 6fa32 2                          ; before: object+2+0x22 word = 00 01
  w 18140 00900000                   ; scratch-poke id 144 (big-endian) at $18140
  callcap 10ee2 5000 - A1=18140      ; call UNLOCK CHEST directly
  m 6fa32 2                          ; after
  ```
  Result: `regdelta ... A0 ...->$0006fa0e D1 ...->$00000090`, `mem $06fa33 $01->$00` — the low byte of
  the indexed word flips exactly as `clr.w` predicts (the high byte was already `$00`, so `callcap`'s
  diff shows only the one changed byte). This is the second genuinely causal proof of the whole verb
  interpreter (after LOCK, §24c), on a structurally different opcode with a different addressing
  shape — real evidence the mechanism generalizes across the vocabulary, not just LOCK/UNLOCK's one
  bit.
- **id 35 (`$010f0e`) is UNTRAP CHEST's always-erroring variant, found the 73rd pass.** `$010f0e` is a
  clean instruction boundary — the print-only tail of UNTRAP CHEST's real handler (`$010f06: bsr
  $10738; beq $10f0e; bra $10f1e`) — but it **falls through unconditionally into the success action**
  after printing: `move.l A0,-(A7); lea $17904.l,A0 ("UNTRAP CHEST NON-X OBJECT"); jsr $11788;
  movea.l (A7)+,A0`, then straight into `$010f1e`'s `clr.b 5(A0,D0.w)` with no intervening `rts` or
  branch. A genuinely new behavioural fact, not just a pin: reaching id 35 always prints the error
  *and* still performs the untrap write afterward.

### 64b. The rest of the verb vocabulary, located and disassembled — real addresses, not yet each
    pinned to a specific numeric id (three more pinned in §64a above as of the 73rd pass; this
    table's KILL/UNINV/WAKE/SLEEP row is corrected below, §64c)

Everything below was found the same way (the debug-string scan, then reading the code around each
`lea <string>.l,A0`), but landed on a dispatch-table entry that this pass's bounded walk couldn't
cleanly attribute (either the table target itself decodes as an out-of-place instruction, the same
class of risk as §64a's STOPACTI anomaly, or the routine is reached only via an internal `bsr`/`bra`
rather than sitting exactly at one of the 59 targets). Real code, real addresses, genuinely new
(`ai.md` §6e previously listed the whole vocabulary as "none individually mapped"); just not each one
proven-by-exact-table-slot the way §64a's four are.

| Verb | Handler entry | Resolver used | What it does on success |
|---|---|---|---|
| MOVEING (position set) | `$010520` | `bsr $c5a8` (type **4**, not the usual `$010738`) | writes a new 16-bit coordinate into `object+2` if it differs from the current value |
| GOANI | `$0104e2` | `bsr $c5a8` (type 4) | same shape as MOVEING, `clr.w 2(A0)` |
| GOMOVE | `$010554` | `bsr $10738` (type 6/9) | tests bit 0 of `+12`; errors `"GOMOVE A NONMOVE OBJECT"` if clear |
| STOPMOVE / STOP MOVE | `$0105b4` | `bsr $10738` | same bit-0-of-`+12` gate, then `move.b #1,0(A0,D0.w)` (an indexed array, same shape as UNLOCK CHEST's) |
| FLAG OP | `$0106bc` | `bsr $10738` | toggles bit 0 of `+3` and mirrors the result into `2270(A5)` — **this is the writer §23b's "aside" flagged but didn't chase**: the small nested-IF/comparison-operator bytecode table at `$0000ffba` gates on exactly this same `2270(A5)` byte, so FLAG OP is confirmed as that sub-interpreter's own condition-setting opcode, not an unrelated mechanism |
| GOACTI | `$010e5c` | `bsr $10738` | `bclr #6,15(A0)` (paired with STOPACTI/id 31's `bset`, §64a) |
| UNTRAP CHEST | `$010f06` | `bsr $10738` | `clr.b 5(A0,D0.w)`, `D0` from `+12` — same indexed-array shape again |
| CLEAR CHEST | `$010f9e` | none — reads `348(A5)` (current actor) directly, compares its `+6` word against an inline operand byte | `clr.w 0(A0,D0.w)` on match; **this one never calls the generic id-resolver at all**, it operates on whichever object is already "current", not an arbitrary id from the script stream |
| DIRTY POTION | `$010fd4` | `bsr $10738` | `bset #2,3(A0,D0.w)` |
| KILL / UNINV / WAKE / SLEEP | `$010374`/`$01039a`/`$0103b4`/`$0103ca` | see §64c: each print-only stub *does* have a real resolver, one call-frame away | each is a 4-8 byte stub that unconditionally prints its own "non-existant creature" string — see §64c |

### 64c. The KILL/UNINV/WAKE/SLEEP cluster always errors, and why that's not necessarily a bug in this
    build

Every other verb handler in this table follows the same shape: resolve, branch on failure, do the
real work on success. The four table targets themselves don't — each is just "print the not-found
string, `rts`" (or, for UNINV, a mid-instruction landing ahead of that print, §64a's id 15) — but
**the resolve step isn't missing, it's one call-frame away, found by the 73rd pass**
(`find_ram_callers.py` against each print stub): a real resolver sits immediately before each stub in
memory and branches to it only on failure — `$010354` (KILL, `beq $10374`; success pushes a 6-byte
record into a queue at `304(A5)`, increments `1154(A5)`), `$01038a` (UNINV, `beq $1039e`; success
`bclr #0,6(A0,D0.w)`), `$0103e0` (WAKE, `beq $103b4`; success `bclr #7,5(A0,D0.w); bsr $e13e`), `$0103f8`
(SLEEP, `beq $103ca`; success `bset #7,5(A0,D0.w); bsr $e172`). None of these four resolver entries are
themselves among the 59 table targets — like GOACTI/UNLOCK, they're reached only by internal call, not
a table slot — so the earlier "no resolve-and-branch gate at all" framing was true of the print stub in
isolation but wrong about the verb as a whole. **Type 9 (creatures) has been fully empty in every
snapshot this whole spike has ever captured** (§23c), so every one of these four real, resolve-gated
verbs fails deterministically whenever the shared resolver (§22d/`$c542`) takes its *negative-sentinel*
branch into type 9. **This is narrower than it first looks, and is corrected by §68: the same resolver
takes a *positive-id* branch into type 6 (fully populated, §23c) instead, and all four verbs succeed
live when called with a positive type-6 id — including GIANT RAT's own id 194.** "These verbs always
fail whenever invoked" was an overgeneralization from the type-9 case alone; the accurate statement is
"these verbs fail via the type-9 path (still true, still empty even in GIANT RAT's own room, §68) but
succeed via the type-6 path against any resolvable object, GIANT RAT included."

### 64d. What this leaves open

- **7 of the 59 dispatch entries are now pinned to a specific verb by address** (1, 15, 18, 31, 32, 34,
  35 — §64a; ids 15/32/35 added the 73rd pass). The other ~13 verbs in §22b/§6b's vocabulary have real
  handler addresses (§64b's table) but not a proven numeric opcode id — the same bounded-walk technique
  could be pushed further per-entry with more manual disassembly, but risks exactly the
  false-attribution failure mode the bounded walk was built to avoid (see the next bullet for a
  concrete case of that risk caught and rejected).
- **73rd pass, investigated and explicitly rejected as false attributions** (do not reuse without
  redoing the check): the bounded walk's raw output matched ids 2, 6, 9, 38, 53 and 54 to debug
  strings, but hand-verification found each one lands mid-instruction inside a *neighbouring* routine
  with a skipped push or pop, not a real entry — id 54 (claimed SLEEP, `$0103d0`) skips SLEEP's own
  `move.l A0,-(A7)` and would pop a value nothing pushed; id 6 (`$010af0`, `movem.l (A7)+,...`) pops
  registers nothing on this path pushed; id 38 (`$010ac2`) lands inside the *matching* push's own
  register-mask extension word (id 6/38 are two ends of one real, corrupted call, not two verbs); id 53
  (`$0107d6`) lands 2 bytes into an unrelated `lea`, leaving `A0` unset, then wanders ~30 instructions
  before coincidentally reaching a real string; ids 2 and 9 both start with an invalid decode (`ori.b`
  targeting an address register; `bchg` with an implausible bit number) resolving to real code only
  well past a single bounded hop. **General test going forward**: a table target whose first
  instruction looks implausible (`ori.b` to an address register, a `movem.l (A7)+` with nothing
  pushed on this path) is only a real entry if that instruction is provably side-effect-free (a
  register never read again before the next branch, as with id 15's `ori.b #$75,D6`) and no push/pop
  is skipped — ids 15/31/32/35 pass both tests, ids 2/6/9/38/53/54 fail one or both.
- **id 12 (`$010d5c`), refined but still not tied to a verb string.** Full disassembly through
  `$010dce`: resolves an object, checks its type byte, runs the already-documented three-field
  bounds/coordinate comparison, then a tile-offset collision check — every failure path converges on
  `$010dc8: addq.w #6,A1; clr.b 2270(A5); rts`, with no `lea`/string anywhere in the block. `2270(A5)`
  is the exact byte FLAG OP's own success path mirrors (§64b) — id 12 is now more likely a **boolean
  condition-test opcode feeding the same mini-IF interpreter at `$0000ffba`** that FLAG OP feeds, not a
  MOVE-family precondition with its own error message as previously guessed (inferred, not proven
  live).
- **id 25 (`$010e38`) unchanged** (resolve + 6-byte queue append at `308(A5)`, counter `1264(A5)`), but
  **id 30's target (`$010e52`) is a newly-found tail-alias landing inside id 25's own block**, on
  `move.l A2,308(A5); addq.w #1,1264(A5); rts` — id 30 is not GOACTI despite sitting near it, and isn't
  a new verb; it's a second, degenerate entry point into id 25's queue-append tail using whatever's in
  `A2` at call time.
- **External reachability is unchanged**: every new caller found this pass (`$010844`→`$010914`,
  the internal `beq`/`bra` webs within each handler) is internal to the `$010000`-`$011256` block,
  the same category §24b's 18-site external sweep already covers. This pass doesn't reopen or narrow
  the still-open "does anything outside this block ever invoke it" question from §24d/§26 — it only
  maps far more of the block's own internals than existed before. Script: `py/verb_opcode_map.py`
  (also dumps the debug-string table's real addresses, reusable independent of the table-mapping
  question).

## 65. Two new resource mechanisms found while looking for a creature room: the game's own
    compressed dialogue/monster-name string table, and every room's static object-id list — real
    monster names confirmed resident, but not yet tied to a specific room (71st pass)

Dave's own steer this pass was to aim toward finding a room with a creature to map more of the
KILL/UNINV/WAKE/SLEEP cluster (§64c). Re-reading §13/§28d/§63 first: reaching room 3 by driving the
player through CAVERN/TUNNEL is closed three independent ways already (the room table's own door
slots, the door/portal resolver's disassembly, and the FDC trace), and the lever's LOCK(144)
mechanism itself was already retracted as probably the wrong trigger (§28d). Rather than re-run
either closed thread, this pass looked for a purely static way to identify a creature-bearing room
directly from data already resident in RAM (per §13's own "9 palettes/104KB already loaded"
finding) — and found two previously-unused mechanisms doing that.

### 65a. The room loader's own object list is resource type 5, indexed by room slot — not type 6,
    and not per-room memory, a genuinely new resource type this spike had never resolved

Disassembling `$00cd50` in full (§37d had already named this as "the room loader" but not read past
its type-6 instantiation loop): before that loop starts, `move.w 1166(A5),D1; moveq #5,D0; bsr
$c5a8` resolves **type 5**, indexed by `(A5)+1166` — confirmed live to equal the room's own
world-grid slot number, byte for byte matching `world_map.py`'s own numbering (`1166(A5)` reads `0`
in `gameplay_empire.snap`/CAVERN and `1` in `room2_tunnel_entry.snap`/TUNNEL). The resolved type-5
record is a flat stream of `(room_record+29)+1` big-endian 16-bit words — each one a **type 6**
object id, read in the loop the rest of §37d already documented. This is the room's own static
object-population list, sitting in RAM for all 72 populated rooms simultaneously (the type-3 table
was already known to be fully resident; this is the first time its sibling per-room content list
was resolved too). Script `py/room_object_census.py` walks all 72 slots and prints each one's id
list; cross-checked against the two rooms already fully proven — slot 0 decodes to exactly
CAVERN's already-exported 22-object catalog (`graphics.md` §3), slot 1 decodes to `[0, 144]`, and
144 is the triple-confirmed lever id (§23d) — 2/2 real, not a guess.

### 65b. A previously-undocumented, much larger packed dialogue/item/spell/monster-name string
    table, decoded and enumerated for the first time — real creature names confirmed resident

§18b already read `$00fd2c`/`$00fd4e`/`$00fda2` (the packed-string decoder feeding the name-banner)
but only as much of the call tree as explained the *mechanism*; nobody had enumerated the table
itself. `find_ram_callers.py` against `$00fd2c` (23 hits, several inside the verb-interpreter block
itself, `$011004`/`$011156`/`$0111fe`/etc.) confirmed it's a general-purpose string fetch used
throughout the game, not one dedicated to error messages. The format, read straight off the three
routines: `(A5)+168` is a word-indexed offset table, `(A5)+172` a base the offset is added to
(giving the start of a packed byte stream), and the stream itself is a standard 6-bit/4-chars-per-
3-bytes packing (`b0>>2`, `(b0&3)<<4|b1>>4`, `(b1&0xf)<<2|b2>>6`, `b2&0x3f`) through a 256-byte
character map at the fixed address `$5ac0`, terminated by a map entry of `$ff`. Script
`py/name_strings.py` implements this and decodes indices 0-599 cleanly (real, readable text
throughout, not garbage past some cutoff). Validated three ways: index 200 decodes to `LEVER`
(object 144's own known live status-bar name), 188 to `BOAT`, 197 to `PICKAXE...` — all three
already-proven live names, decoded correctly with zero live/`kbd` input needed. Past the UI
vocabulary, the table holds the game's spell list, item flavour text, NPC lore (`WRATH HELLAND ...
DWARF LORD, ARCHITECT OF THE CAVES`, `GORBAG ... TAMER OF CREATURES`), the in-game diary text
Dave's own walkthrough reference matches (`DAY TWO, DESTROYED THE WORM...DAY THREE...CANNOT PASS
THE JUMPING CREATURES`) — and real monster names: index 224/225 `DEAD RAT`/`SCONCE`, 226 `GIANT
RAT`, 233 `SKELETON`, plus the live WAKE/SLEEP verb's own message pair at 159/160 (`THE CREATURE IS
SLEEPING`/`THE CREATURE AWAKES AND IS VERY VERY ANGRY`) — direct confirmation those two opcodes
(§64b) really are creature-facing verbs with real, written UI text waiting for a live creature to
attach to, not dead code.

### 65c. Not yet closed: an object's own display-name index is a separate numbering space from its
    type-6 id, so §65a's per-room id lists don't yet identify which room has the rat

The lever is the one object with both numbers already proven: id **144**, name-string index **200**
— different numbers, so there is no known arithmetic relationship (offset, shared table, etc.)
between the two spaces yet. This means a room's object-id list containing the same *number* as one
of §65b's monster-name indices (e.g. slot 27's list includes `226`, the same number as `GIANT RAT`)
is very likely coincidence given how dense both id ranges are (~700 object-slot references across
71 rooms against ~600 decodable string indices), not a real cross-reference — asserting it as one
without further proof would repeat exactly the kind of address-numerology mistake this doc has
retracted before (§13/§28d). Traced one candidate source of the real link this pass
(`$010ffa`-`$011064`, an EXAMINE/READ-style verb that composes descriptive text from the *current
actor* global `348(A5)` via a secondary `bsr $c576` sub-lookup) but it reads as **template-driven
composite text** (a base string plus conditionally-appended fragments, matching the "spell has ___
charges" style strings in §65b's own output), not a simple "object id → name index" field — the
real field, if a single one exists, is still unfound. This is the same open item mechanics.md has
already flagged once (the proximity-icon-panel writer, "still a distinct, unidentified open item"),
now with a second, independent way to attack it: find what supplies `D0` at one of $65b's other
9-odd internal `$fd2c` call sites reached from *outside* the EXAMINE verb (a proximity/touch path
rather than a script-read path) and read what field of the touched object it comes from.

### 65d. What this leaves open

- **The concrete next step for "find a room with a creature"**: locate the type-6 record field
  that supplies an object's own name-string index (§65c), most promisingly by reading one of
  `$00fd2c`'s other callers reached from the collision/touch path (§4/§27b) rather than a script
  opcode, the same way §18b traced `$defa`'s. Once found, decode it for every object id in every
  room from §65a's census and grep for a match against §65b's monster-name indices (224/225/226/
  233, and any others in the fuller 600-entry table not yet grepped for) — this would name the
  creature's room directly, with proof, no live movement puzzle needed.
- §65b's table almost certainly extends past index 599 (the last index this pass tried); a wider
  sweep (`py/name_strings.py --hi 1000` or higher) is cheap and untried.
- Neither `py/room_object_census.py` nor `py/name_strings.py` needed any `kbd`/`mouse` input or new
  snapshot — both ran against the already-committed `room2_tunnel_entry.snap`, reusable by any
  future pass without re-driving anything live.

## 66. §65's missing link found: an object's live display-name index sits in a per-room "live
    instance" record, not the type-6 template — proven 3/3, and it corrects graphics.md's "goblet"
    (72nd pass)

Dave's own steer continuing from the 71st pass: find the field. Live `bpc 946a 1 250000` (armed
after `kbd ff 04` from `room2_tunnel_entry.snap`, the same Left-hold approach as §41-43) catches
the exact comparison §42 described in full: `$009478: move.w 10(A4),D0` / `$00947c: cmp.w
1222(A5),D0` — register capture at the hit gives `A4=$00059910`, and `1222(A5)` reads `200` live,
matching the lever's already-proven name index exactly.

**The field is not in the type-6 template** (§65c already searched the lever's 44-byte record
byte-for-byte for `200` and found nothing — confirmed again here) **because `A4` isn't the
template.** Reading `A4`'s own resolution chain (`$00944e`-`$009456`) and reproducing it as a pure
static formula, verified byte-exact against memory (no emulator step needed once the chain is
known):

```
template   = resolve(type=6, id)              # §65a/door_id_words.py's read_type6
slot_off   = u16(template + 8)                # this object's own currently-assigned room-array
                                               # slot byte offset — written by the room loader
                                               # ($00cd50, §37d) at `$00ce5c`-`$00ce60`, only valid
                                               # while the object is instantiated in the CURRENTLY
                                               # LOADED room
slot_addr  = u32((A5)+56) + slot_off          # SpriteObjectArrayPtr_A5Plus56 (§21a/43) + slot_off
live_rec   = u32(slot_addr + 6)               # $00ce78's `move.l A0,6(A1)` (§37d) — corrected §67:
                                               # this IS the final writer when the room is reached
                                               # through its real trigger ($00e854); it only looked
                                               # "transient/superseded" in this section's own
                                               # already-loaded snapshots because those snapshots
                                               # were never observed at the moment of that write
name_index = u16(live_rec + 10)               # matches name_strings.py's table exactly
```

`py/room_object_names.py` implements this and walks the current snapshot's own room-object census
(reusing `room_object_census.py`'s resolvers). **Validated 3/3 against every name already proven
live**: TUNNEL's LEVER (id 144) → index 200 ("LEVER"), and — new this pass, from CAVERN's own
22-object catalog, no live driving needed since `gameplay_empire.snap` already has that room
loaded — id 257 → index 188 ("BOAT") and id 168 → index 197 ("PICKAXE"), both exact matches to
§65b's already-proven indices. Not a coincidence: three different objects, three different
templates, three different live records, all landing on the correct pre-known string.

**This also corrects graphics.md §3/§5a-2's "goblet" (sprite-array slot 16, state-4 outlier,
object id 413, `slot_off=$0460` = `16 * $46`).** Its live name index is **224**, whose primary
decoded string is **`SCONCE`** (not `DEAD RAT` — index 224's raw decode runs on into index 225's
own text with no length field, `SCONCE\0\0DEAD RAT\0A`; `py/name_strings.py --lo 224 --hi 225`
alone confirms 224 = `SCONCE` cleanly). The pixel art is still genuinely goblet/chalice-shaped
(graphics.md §5a-2's `32×23@$5fbaa` decode stands, unchanged) and its art-source question (not
sourced from type 2's 255-slot catalog like the other 20 static props) is still open — but the
game's own name for this prop is a wall sconce, not a goblet, plausibly the same object rendered at
low resolution (a cup-shaped candle-holder reads as a chalice at 32×23px). graphics.md's three
"goblet" mentions (§3, §5a-2, and the Open items list) should read "sconce (visually goblet-shaped,
name-index 224, mechanics.md §66)" going forward.

**Negative result for cadaver.md's open item 1 (name the creature's room): neither CAVERN's 22 nor
TUNNEL's 2 known objects carry a monster name index.** `py/name_strings.py --lo 224 --hi 234`
confirms the full monster/skeleton cluster's indices (224 SCONCE, 225 DEAD RAT, 226 GIANT RAT, 227
LID, 228 CHAIN, 229 FLAME, 230 PLANK, 231 CONOPTIC URN, 232 SKULL, 233 SKELETON) — running
`room_object_names.py` against both `gameplay_empire.snap` and `room2_tunnel_entry.snap` finds only
224 (SCONCE, the corrected goblet) among either room's objects; 225/226/233 (DEAD RAT/GIANT
RAT/SKELETON) appear in none of CAVERN's 22 or TUNNEL's 2 live records. The creature is not hiding
among either already-explored room's own dressing under this field.

**What this leaves open**: **`template+8` is *not* resident/valid for objects outside the
currently-loaded room — checked directly, and it fails silently rather than obviously.** Reading
LEVER's (id 144, a TUNNEL-only object) own `template+8` from `gameplay_empire.snap` (CAVERN loaded,
TUNNEL not) gives `$0000`, not an out-of-range or sentinel value — it silently **aliases onto object
id 0's own real slot** (CAVERN's slot 0 is a genuine, valid entry), rather than failing in any
detectable way. This rules out a naive one-snapshot 72-room census outright: a query for an object
belonging to any not-currently-loaded room would silently return some *other*, wrong object's live
record instead of erroring. §67 closes item 1 for real via a `callcap`-driven invocation of the
*real* room-transition trigger (not `$00cd50` in isolation — that alone touches none of the array,
see §67) per room, and also identifies who writes `slot_addr+6` and when (this section's own open
question above).

## 67. Item 1 closed: slot 27 holds a unique GIANT RAT object, tied directly to the game's own
    "SPINE CREATURE" hint text — the real room-transition trigger found, and §66's "unidentified
    writer" retracted (73rd pass)

**Validation first**: reproduced all 22 of CAVERN's real objects plus TUNNEL's LEVER — 23/23 exact
match on id, `live_rec` and `name_idx` — against §66's own single-room formula, with TUNNEL driven
*from CAVERN's loaded state* (the actual cross-room case item 1 needed). Independently re-verified by
this session directly against the live REPL, not just taken on the reporting agent's word: a fresh
`w 185e0 1b2888; watch 385b4 4; callcap e854 2000000 -` run reproduces the exact byte-for-byte
`live_rec=$0005d62a` write at `pc=$00ce78` for slot 27/id 194 below, and `u16($5d62a+10)` read
straight from the static, unmodified `gameplay_empire.snap` gives `226` — the chain holds with no
live driving needed for that second half, exactly as claimed.

**§66's own "unidentified writer" framing was wrong, and the real entry point is `$00e854`, not
`$00cd50` alone.** A raw `callcap cd50` against an already-loaded room touches *zero* bytes of the
sprite-object array — `$00cd50` depends on setup its real caller does first, so calling it in
isolation was never going to reproduce steady-state behaviour. The actual room-transition trigger is
`$00e854` (mechanics.md §38c's own already-disassembled routine, called from `$0072ac` right after the
door resolver commits `(A5)+1166`). Calling `$00e854` with only `(A5)+1166` written to the target
room's slot number is sufficient — it resolves `(A5)+164` (the room-record pointer) itself internally
(confirmed: a `callcap` diff shows `(A5)+164` flip from CAVERN's `$6bf0a` to TUNNEL's `$6bf84` with no
explicit write). Watching `slot_addr+6` across this call shows **`$00ce78`'s `move.l A0,6(A1)`
(§37d/§66) writes the correct, final `live_rec` in one shot** — no second write, no supersession —
for both an already-visited room and a never-before-loaded one (slot 2, this pass). §66's "transient,
later superseded by an unidentified writer" conclusion was an artifact of reading `$00cd50` out of its
real calling context, not a real second writer; retracted. (One residual gap: a genuine cold-boot,
first-ever room load was not reached live this pass — input injection into the boot menu didn't
respond to `kbd` scancodes for reasons not chased down — so this is proven for the `$00e854` re-entry
path specifically, not for the very first load of the game's life. No evidence points at a difference,
but it's untested.)

**The per-room recipe, validated and cheap** (`reversing/cadaver/py/full_room_name_census.py`,
consuming the transcript `parse_rooms.py` produces from a plain REPL driver script — see
`scratchpad/ANCHORS.md`'s `cadaver/agents/room_census` entry for the corpus): from one base snapshot
(`gameplay_empire.snap`), for each room slot 0-71, `w 185e0 <(slot<<16)|0x2888>` (preserving
`(A5)+1166`'s own low word — `w` only writes a longword and this is a 2-byte field), `watch 38338
2200`, `callcap e854 2000000 -`, `unwatch`. Each `callcap` snapshot-restores, so all 72 rooms run from
the same base with no cross-room contamination, in one REPL session (~6s wall clock total). `slot_off`
is simply `70 * (object's rank in its room's own type-5 id list)` — a shared, per-room-reused scratch
slot, not a persistent or growing one. `live_rec` addresses themselves are persistent, pre-existing
data (not freshly allocated per visit): rooms share decoration records exactly the way CAVERN's own
id409/id410 already shared one (§65a) — e.g. SCONCE's record at `$5f864` is reused by 10 different
rooms' objects.

**Coverage**: 56 of 72 rooms fully verified (instantiated-object count matches the static type-5
census 1:1, in order). 14 rooms (35 objects total) hit fewer `$00ce78` writes than their census
count — every one of those objects still has a valid type-6 template, so this is a real second code
path through the room loader not yet chased down (§37d already named candidate special-case branches
at `$00cdc2`/`$00cde6`/`$00cdf0`), not missing data. Slot 69 produced 102 `$00ce78` hits against only
28 census ids (moot for the search: every one of its objects reads `name_idx=$ffff`, none). Slot 71's
own static census list doesn't end in the usual 0 terminator — malformed, not chased down. All three
are open items below, not blockers for the finding.

**The finding**: every monster-cluster index (224 SCONCE, 225 DEAD RAT, 227 LID, 228 CHAIN, 229 FLAME,
230 PLANK, 231 CONOPTIC URN, 232 SKULL, 233 SKELETON) that shows up across the 56 clean rooms is a
shared decorative record reused 2-11 times each (SCONCE alone: 10 rooms) — ordinary dressing, not a
creature. **226 GIANT RAT is the one exception: it appears exactly once, in slot 27, object id 194,
`live_rec=$0005d62a`.** Full address trail, independently re-verified: `resolve(type=6, 194) →
template`, `template+8 → slot_off` (rank 9 of slot 27's 21-object roster), `array_base($38338) +
slot_off + 6 → $00ce78` writes `live_rec=$0005d62a` live, `u16($5d62a+10)=226`, `name_strings.py`
decodes `226 = "GIANT RAT"`. Slot 27 (`world_map.py`: 10×10 rectangle, same footprint as CAVERN, a
166-byte room record — CAVERN's own is 122 bytes, so slot 27 is if anything the larger of the two)
reads like a monster's den on its full roster: 6× STONE, 5× BONE, a SKULL (id 215, the shared
`$5f23c` record), the unique GIANT RAT, plus PARCHMENT/KEY/CHEST/3× FUNGHI.

**Direct textual confirmation of Dave's external walkthrough hint, verbatim, in the game's own
data**: `name_strings.py`'s widened sweep (see below) turned up index 272 —
`"MOST SKULLS WILL HELP YOU COMBAT THE SPINE CREATURE\0THE ESCAPE NUMBER STARTS WITH 1\0I HEAR A KEY
IS HIDDEN ON A BODY"` — three back-to-back hint strings, none carried by any placed object
(hint/narrative text, not an object name), directly naming the "SPINE CREATURE" and tying SKULLs to
fighting it. SKULL-bearing rooms across the clean 56: **26 (×2), 27, 29, 49, 50, 55, 58, 68** — slot
27 already stands out for GIANT RAT too.

**§65d's "the string table almost certainly extends past index 599" is now closed, negative**:
swept 0-999, everything from ~599 on decodes to a repeating `DOOR` garbage pattern then zero
padding — no further monster names or hints exist past what §65b/this section already found.

**Reading**: GIANT RAT being a *placed, named object* (not the empty type-9 creature table itself
being populated) was, at the time this section was written, not yet proof that the KILL/WAKE/SLEEP
cluster (§64c) resolves successfully against it. **§68 closes this live**: KILL/WAKE/SLEEP/UNINV all
succeed against GIANT RAT's own id (194) directly, via type 6, not type 9 — type 9 itself stays empty
even in slot 27 (also proven live, §68). Item 1 is fully proven, not just the strongest lead.

**What this leaves open**:
- The 14-room/35-object minority branch that skips `$00ce78`, slot 69's 3.6× overcount, and slot 71's
  malformed census list — none chased down, all in `scratchpad/cadaver/agents/room_census/`'s logs.
- A genuine cold-boot first room load, to confirm `$00ce78` is the writer there too, not just via
  `$00e854` re-entry — blocked this pass by the boot menu not responding to injected `kbd` scancodes
  at the point tried; not chased further since it wasn't needed for item 1 itself.

## 68. Item 1 fully closed: KILL/WAKE/SLEEP/UNINV all succeed live against GIANT RAT's own id — via
    type 6, not type 9, which stays empty even in slot 27 (74th pass)

§67's own "what this leaves open" named the concrete next step: drive to slot 27 and check whether
KILL/WAKE/SLEEP (§64c's four resolve-gated verbs) actually succeed there. Two independent live checks,
both from `gameplay_empire.snap`, no player movement needed (same style as §67's own `callcap`-driven
checks):

**Check 1 (negative): entering GIANT RAT's own room does not populate type 9.** `w 185e0 1b2888`
(load slot 27 the same way §67 validated), `watch 4c636 40` (type 9's own 10-slot index table, §23c's
`idx_ptr=$4c636`) and `watch 1899a 2` (`2120(A5)`, the global creature-id §22d's resolver reads for the
type-9 path) each armed across their own `callcap e854 2000000 -`: **zero `WATCH:` hits in either
range**, and the full ~1500-byte `callcap` memory delta (independently grepped, not just the watch)
contains no write anywhere in type 9's index table, its data base (`$7560a`), or the global creature-id
slot either. Slot 27 — the one room in the whole 72-room map with a uniquely-named monster object —
populates type 6 exactly like every other room (§67) and touches type 9 not at all. §64c's "type 9 has
been fully empty in every snapshot this spike has captured" now holds for GIANT RAT's own den
specifically, not just for CAVERN/TUNNEL — room-load is conclusively not how a creature would ever get
registered into type 9.

**Check 2 (positive, the actual headline result): the resolver's *other* branch succeeds against
GIANT RAT directly.** §22d's shared resolver (`$c542`) doesn't only serve type 9 — a **positive**
16-bit id read from the verb's own script-stream cursor (`A1`) takes it into type 6 instead (already
known 1000/1000 populated, §23c). GIANT RAT's id, 194, is positive. Calling each of the four resolvers
directly (no room load needed — type 6 is a global resource, not per-room) with `A1` pointed at a
2-byte scratch buffer holding `$00c2` (194 big-endian) — `w f0000 00c20000` then
`callcap 10354 20000 - A1=f0000` (KILL), `callcap 1038a 20000 - A1=f0000` (UNINV), `callcap 103e0 20000
- A1=f0000` (WAKE), `callcap 103f8 20000 - A1=f0000` (SLEEP) — **all four take their success path, not
the "non-existant creature" print stub**:

- KILL (`$010354`) and UNINV (`$01038a`) and WAKE (`$0103e0`) all `returned` cleanly, each with
  `A0=$00070034` in the register delta — independently cross-checked static: `resolve(type=6, 194)` via
  `py/room_object_census.py`'s own `resolve()` against `gameplay_empire.snap` gives the identical
  `$70034`, byte-for-byte. KILL's delta shows the documented 6-byte queue push into `304(A5)` and the
  `1154(A5)` counter incrementing 0→1, exactly its success-path disassembly (§64b); WAKE's delta is
  consistent with its own `bclr #7,5(A0,D0.w)` before `bsr $e13e`.
- SLEEP (`$0103f8`) takes the identical resolve branch — confirmed directly: an 8-step-capped `callcap`
  stops at `PC=$00c56c` (`moveq #6,D0`), the exact type-6-positive-branch instruction, with `D1=$c2`
  already loaded — but its own success action (`bsr $e172`) runs long and hits a 20000-step cap without
  returning (`exitSP` far below entry, many registers disturbed). This is very likely the same
  interrupts-masked-under-`callcap` hazard CLAUDE.md's cadaver rules already document for sound-effect
  code (`capture_hits.py`'s PowerMonger note): `$e172` (paired with the already-known "THE CREATURE IS
  SLEEPING" message, §64a) plausibly plays a cue and then busy-waits on a flag only a real interrupt
  clears. The resolve itself is proven; SLEEP's own downstream action past that point is inferred, not
  traced further this pass.

**This corrects §64c's framing, not just extends it**: "type 9 is always empty, so KILL/WAKE/SLEEP/
UNINV always fail whenever invoked" was true only of the type-9 (negative-sentinel) branch. The exact
same resolver's type-6 (positive-id) branch is fully live for these four verbs, and GIANT RAT — the one
object this whole spike has spent 70+ passes looking for — is concretely, provenly KILL-able,
WAKE-able, SLEEP-able and UNINV-able by its own numeric id, mechanically, right now. **What remains
open, not conflated with this result**: no caller anywhere in the game's own code has yet been found
that actually invokes these four ops with any operand during ordinary play (§23d/§24's "fourth,
still-unlocated dispatch site" stands unchanged) — this section proves the mechanism succeeds against
GIANT RAT when driven directly, not that the shipped game ever exercises it that way. Cadaver.md's
long-standing "find a room with a creature" thread is now closed on both halves: the room (slot 27,
§67) and the mechanism resolving against it (this section) are both live-proven, not inferred.

## 69. A genuine "teleport to room X at (x,y), both read from script data" verb found inside the
    object-verb block, at `$010974`-`$010a7a` — but four independent techniques, including a live
    60M-step idle run, agree nothing calls it in this playthrough's loaded state (75th pass)

Dave's own steer this pass was external ground truth again: the published walkthrough (pasted in
full this session) confirms room-to-room progression in this exact game is driven by levers scattered
throughout all 69 walkthrough rooms ("pull the lever to teleport to room 44", "...to Level 2", etc.),
not just TUNNEL's one lever. That reframed the standing question from "why won't LOCK(144) fire"
(closed negative since §28d) to "does the object-verb interpreter (§64) contain a teleport-style verb
at all, and if so, does anything reach it."

**Walkthrough room numbering is now pinned, cheaply, with no live driving**: walkthrough room *N* =
internal slot *N*-1. Four independent matches against the existing static census
(`scratchpad/cadaver/agents/room_census/full_census_names.txt`, §67's own corpus): room 1/slot 0
(CAVERN, already known), room 2/slot 1 (TUNNEL, the lever, already known), room 3/slot 2 (a `STONE
BAG` object, id 23 — the walkthrough's "collect the bag of stones"), room 4/slot 3 (`FULL BARREL`×3
plus a `SCONCE` — the walkthrough's barrel-to-wall-lantern trick), room 19/slot 18 (a `KEYHOLE`
object — the walkthrough's lock-and-key room). This also explains, rather than contradicts, §67's own
census: every creature the walkthrough names ("a maggot will appear [when the gem is collected]",
"entering and returning to room 19 causes a spiky floater to appear") is explicitly event-triggered,
not room-load placed, and slots 3/18/38 (the walkthrough's own "spiky floater"/"sleeping jumper"
rooms) all come back clean of any creature object in the static census, the same shape as every other
room — consistent with `ai.md`'s entity/action-script system doing the spawning, not the type-5/6
array §67/§68 already proved for GIANT RAT.

### 69a. `find_ram_callers.py` against `$00e854` itself — never run before — finds a second real call
    site and a genuine, previously unmapped verb

Mechanics.md had only ever named one caller of the room-transition trigger (`$0072ac`, the CAVERN/
TUNNEL door resolver, §67). A fresh scan finds **6** raw hits, two of them real `jsr $e854.l`
instructions the doc never covered: `$0069ba` and `$0072ac` (the known one). `$0069ba` sits in a
routine that reads `2516(A5)` (cadaver.md's still-open item 10, "a real day/progress counter"),
reduces it mod 3 (`divu #3`) into `1174(A5)`, then calls `$00e854` — a plausible day-cycle room-state
refresh, not chased further this pass; flagged as a fresh lead for item 10, not closed.

The other two hits, `bsr $e854` at `$0109ca` and `$010a58`, sit inside one routine, `$010974`-
`$010a7a`, fully disassembled this pass:

```
$010974: movea.l 160(A5),A0 ; clr 3 bytes of a struct
$010984: move.b (A1)+,D1    ; read one byte from a script/data stream (A1)
$010988: move.w D1,1166(A5) ; write it as the target-room field (§67's own "current room" field)
$010990: moveq #3,D0 ; bsr $c5a8   ; resolve it via type 3 (the room table)
$01099c-$0109b8: three more script bytes -> 2134/2136/2138(A5)   ; target x/y/facing, inferred
$0109ca: bsr $e854          ; the room load itself
$0109ce: beq $10a70          ; branches on success
```

This is a real, working "load room *N* at (x,y), both read from the calling script" verb — exactly
the shape the walkthrough's game-wide lever/teleport pattern needs — sitting inside the already-known
`$010000`-`$011256` object-verb block, but matching none of the 59 dispatch-table targets or ~20
named verbs §64 already mapped. Genuinely new territory in that block.

### 69b. Four independent techniques agree: nothing reaches it in this playthrough's loaded state

> **Corrected (77th pass, `secrets.md` "The level code overlay", `py/secrets/export_service8.py`).** The raw bytes `$00010974` at `$0060a2` are not a coincidence: the table starts at `$006082` (2 mod 4, installed by `move.l #$6082,392(A5)` at `$00b5ec`) and `$0060a2` is its entry 8. The overlay's trampoline `$04caaa` reaches the teleport verb as service 8 (`D6 = 32`); calling it with a crafted 4-byte stream loads TUNNEL from CAVERN. Only the loaded level-1 overlay never calls service 8.

- **`find_ram_callers.py 10974`**: 0 hits — no `bsr`/`jsr`/`bcc` anywhere in the whole image targets
  the routine's real entry point.
- **The one table slot that lands nearby, id 2 (`$0109ba`) of the 59-entry dispatch table, was
  already investigated and explicitly rejected** by the 73rd pass (§64d): its first instruction
  decodes as `bchg` with an implausible bit number (a corrupting effect, not side-effect-free) and the
  bounded walk that matched it to `"NO SPACE IN THIS ROOM"` wandered well past one hop — it fails both
  of §64d's own acceptance tests, and this pass's own re-check agrees: entering at `$0109ba` skips
  `$010974`-`$0109b8`'s own room-id/coordinate setup entirely, which no legitimate call would do.
- **Two `find_jump_table_hit.py` "hits" (`$00fe84` entry 196, `$00ffba` entry 37) are false
  positives, not new leads**: `$00fe84` is already proven a 29-entry table, ids 0-28 only (§25a), and
  entry 196 is far past that bound; `$00ffba` is already documented as a small nested-IF
  sub-interpreter feeding `2270(A5)` (§23b), not a 37-plus-entry call table. Neither candidate
  survives a check against the table's own already-published bound — the same false-attribution
  pattern §64d already warns about, just from a different tool.
- **A `find_literal_ptr.py` hit at `$0060a2` looked promising at first** (the raw bytes `$00010974`
  do appear there) **but is a byte-alignment coincidence, not real table data**: the surrounding
  region is a 4-byte-aligned array of `(value:word, flag:word)` pairs starting at `$006080`
  (`$0974`/`$0001` is one such pair, holding a plain 16-bit value, not part of a 32-bit pointer); the
  literal scan's 1-byte-alignment match at `$0060a2` just splices the flag word of one pair (`$0001`)
  to the value word of the next (`$0974`). Confirmed by dumping the region 4-byte-aligned from its
  real start and finding no 32-bit value in it equal to `$00010974` at all.
- **Live check: armed `bpc 10974 1 60000000` from `gameplay_empire.snap` (CAVERN, no input) — 0/1
  hits across 60,000,000 steps.** Rules out a periodic/background (e.g. day-cycle) trigger, not just
  a missing static caller.

**This doesn't contradict §64d's already-established "no external caller reaches the object-verb
block" finding — it extends the same result to one more specific, newly-identified verb inside that
block**, with one additional independent technique (the live idle-run breakpoint) added to the
methodology. Combined with §21c/§20b's already-proven "the lever's own AABB overlap is unreachable by
ordinary movement in this snapshot," the honest state of play is unchanged from §25c/§30's own
standing hypothesis: the code and script data that would drive room-to-room progression may simply
not be resident/reachable in this exact playthrough state, not that the mechanism doesn't exist —
`$010974` is now concrete proof the mechanism (a script-driven room teleport) really does exist in
this loaded image, just still not shown reachable from here.

### 69c. What this leaves open

- **Item 10 (`2516(A5)`'s role) now has a concrete lead** (§69a's `$0069ba` routine) instead of being
  purely speculative — not yet live-tested.
- **`$010974`'s own script-data format** (the bytes `(A1)` reads: room id, then apparently x/y/facing)
  is inferred from the write targets, not proven against a real script blob — no such blob has been
  located yet. Finding one (a per-object or per-room "script pointer" field feeding `A1` here) would
  both prove the format and, if any object anywhere in the 72-room world references it, hand item 1
  its still-missing caller.
- **The `$006080`-region `(value, flag)` table** encountered chasing the false-positive literal-ptr
  hit (§69b) is undecoded and unrelated to this thread — noted for whoever next has reason to read
  that area, not chased further this pass.

## 70. Item 1's live half done: a real, driven CAVERN pickup walk plus an actual CAVERN→TUNNEL room
    transition never once reach the shared object-verb resolver (76th pass)

§64d/§24b's static "no external caller" result already covered every `bsr`/`jsr`/branch in the whole
loaded image; the one half of item 1 still untested was whether *ordinary play* — not a synthetic
`callcap` — ever reaches the shared id-resolver (`$010738`, the single choke point every one of the
59 verbs funnels through, §64c/§68) live. Ran the 11th/12th passes' own documented, reproducible
drive from `gameplay_empire.snap` — `kbd ff 08` (Right) held 1.2M steps (the segment the 10th/11th
passes already showed picks up a SILVER COIN along the way), then the 12th pass's own zigzag
(`Up 0.5M → Right 1.2M → Up 1.2M`, `kbd ff 01`/`kbd ff 08` between legs) that crosses the real
CAVERN→TUNNEL room transition — with `bpc 10738 10 <legsteps>` armed for each leg instead of a plain
`s`.

**Result: 0/10 hits on every one of the four legs** (item pickup included, and the room transition
itself, which is known to call `$00e854` and, per §69a, at least one other routine). Re-ran the
identical command sequence without the breakpoint and rendered the final snapshot: status bar reads
**"TUNNEL"**, matching the already-committed `room2_tunnel_entry.png` (12th pass) exactly, confirming
this run really did complete the transition rather than stalling before it. This is a genuine dynamic
negative, not a repeat of the static one — it extends
§24b's whole-image sweep (which only proves no *static* caller exists) to actual gameplay input,
covering the two ordinary-play actions available from this snapshot (movement/pickup, room
transition). It does not close item 1: creature encounters, inventory-menu actions, and any
mechanism reachable only from rooms/state this one snapshot doesn't cover are still untested live.

## 71. The TUNNEL lever works: its operate icon, confirmed from the object panel, clears the door's `$ffff` sentinel (82nd pass)

**This retires §7, §10d, §20-§29's conclusion that no input reaches the lever.** The passes of §7-§29 held fire at the lever's boundary tile and watched the player descriptor, the portal table and the object array; none of them opened the object panel and confirmed an icon, because the panel was only understood in the 80th pass (secrets.md, "The player's action panel": the icon loop `$009c82` first waits for fire to be released, a second press confirms the highlighted icon, and the loop returns the icon id that `$00a0ac` dispatches).

**Live** (`py/secrets/overlay/action/lever_operate.py`, natural joystick input from `room2_tunnel_entry.snap`, nothing injected or poked):
- Left holds the hero to the stall at bbox (14,12,8,6), one step short of the lever's box (7,15,5,12). The fire probe there returns object 144 with the icon list 7, 11, 6 (operate, a second icon, cancel): the "bracket icon and key icon" of the 13th pass.
- Fire opens the panel (`$009c82` 1), icon 7 is already highlighted and fire confirms it: `$00a448` -> `$00a486` (event 5) 1 each, the consumer `$00fe24` 1, `$00fe30` 1. The lever's record byte 3 goes 0 to 1 (state bit 0, `32` in its ELSE branch).
- The lever's event-5 block (`scripts_level0.txt`, object 144) is `30 COND state bit 0 set; 14 IF ...: 27 SET FLAG 33 = $ffff, sound, 31 state bit 0 = 0; 15 ELSE: 10 CLEAR FLAG 33, sound $2a, 32 state bit 0 = 1`. A RAM diff before and after the confirm shows the door descriptor of type-4 record `$33` (`$6d4f2`, TUNNEL's north door, the "entry 1" of §10b) go from `14 0b ff ff 01 01 00 00` to `14 0b 00 00 01 01 00 00`: **the id word at +2 is the door's open/closed latch, `$ffff` closed (the sound-cue-only reading of §10c) and 0 open.** §10d's guess that pulling the lever "most plausibly rewrites entry 1's descriptor word +2 from `$ffff` to a real room id" was right about the word and wrong that it needs a room id: 0 is enough, the destination is the point-in-rectangle result of §38d as before.
- The reader of the word is the door branch of the movement code, `$00716e`-`$007182`: `movea.l 2(A0),A0; move.b 5(A0),2275(A5); move.w 2(A0),D3; beq $0071ca` (0: the transition proceeds to the resolver of §38d), `cmpi.w #$ffff,D3; beq $00731e` (the sound cue, no room change), anything else the `$011256` lookup of §14 (*read*; the 0 and `$ffff` outcomes are the live ones).
- After the confirm, Up from the stall leaves TUNNEL for room 2 (bbox (52,12,46,6) in the clean run) and Left then reaches room 3. The control run (same walks, no panel) leaves Up at (14,12,8,6), room 1, unchanged.

**What this corrects.**
- §47's "the descriptor's id word plays no role in the destination" is wrong for the `$ffff` value: a descriptor with `$ffff` does not commit a room change (a sound cue), one with 0 does. `door_walk.py` marks 13 level-0 doors `id=-1 sound-cue-only` (`$09 $12 $18 $1c $22 $23 $24 $25 $26 $29 $33 $3f $40`; the first count of 11 missed `$3f $40`); every one has an opener (§72). With only the other doors open, CAVERN's reachable set is {CAVERN, TUNNEL}, so every route out of CAVERN goes through one of these or through the keyed east door `$3b` (§72).
- The clearing verb 10 (`CLEAR FLAG n`) occurs in 17 level-0 blocks once the census is corrected (§72; the first count of 9 came from a decoder that dropped 49 objects), and its operand names the door: `$33` object 144 (event 5, the lever), `$18` object 81 (event 18, an item applied), `$23 $24 $25 $26` object 239 (event 18, four doors at once), `$09` object 391 (event 18), `$29` object 486 (event 5, the crown gate of §secrets "Id 486"), and `$14` object 458 (event 18; that door's word is already 0 in the static image). plus the sites the corrected census added in §72 (`$22` object 472 in room 8, `$1c` object 474, `$12` objects 211 and 212, `$3f $40` object 454, `$2a` object 179). *Read* here; the lever 144 is driven in this section and `$22`'s lever 472 in §72.
- The earlier ground truth ("the lever opens a door in front of it") holds. §22-§29's descriptions of LOCK/UNLOCK, the portal table and the touch events as candidate mechanisms are not the lever's mechanism.

**Jumping** (found while looking at why the circlet of the regalia walk was unreachable, secrets.md "The regalia walk"): fire held with nothing in front is a jump, and the collision scan `$008870` compares the hero's z base `D2` with each object's z top: a mover whose `D2` equals an object's top z reaches the branch at `$008a02` and queues event 9 for it (`$008a26`, `$008a5a`) every frame it stands on it. Landing on the TUNNEL lever (right 24,000 steps, then fire+left, so that the hero is at base z 34 when its x trail reaches 7; `lever_operate.py jump`: 11 passes through `$008a02` and `$008a26` in 600,000 steps, lever byte 3 stays 0) queues those touch events; the lever has no event-9 block and is not operated that way, so this is the real reading of the 22nd pass's "touch unreachable" (it was reachable only from above) and not the lever's mechanism.

**Next.** The door `$33` is open from here, so the route beyond TUNNEL (rooms 2, 3, 6, 7, 9, 70) is walkable; the next gate, `$22` (room 7 to 12), is opened by a lever in room 8 behind CAVERN's keyed east door (§72), and the one after, `$18` (room 15 to 16, object 81's event 18), by item 104: see cadaver.md.

## 72. A positive door id word is an item id: the key doors, door `$22`'s lever, and the walk from CAVERN to room 12 (83rd pass)

**What reads the word** (`$00716e`-`$0071bc`, the same door branch as §71; *read*, with the key crossing driven live below). For a descriptor `A0` whose id word `D3` is neither 0 nor `$ffff`, `move.l D3,D2; jsr $011256` runs a linear scan of the **type-8 list**, the rucksack (`moveq #8,D0`; `$00c628` yields each 4-byte record `[id][template idx]`, `cmp.w 0(A0,D3.w),D2`; `D0` = 1 found, 0 not). Found: byte `+7` of the descriptor decides what the crossing costs, **bit 1** calls `$00c3d4` and `$0e4fa` (the key leaves the rucksack) and then clears the word (`bra $0071b8`, `clr.w 2(A0)`), **bit 2 alone** clears the word and keeps the key, neither bit leaves the word as it is (the item must be carried at every crossing); sound `$12`, then the resolver `$0071ca` and the point-in-rectangle result of §38d as for any open door. Not found (`beq $00734a`): the crossing is dropped, no sound and no room change. So the id word has three states: `0` open, `$ffff` closed to everything but a script (a sound cue, bit 6 of `+7` queues op 8), and an item id, a lock that the item opens. §14's, §47c's and §49-§50's "type-8 registration table, never populated" is the rucksack, empty in every snapshot before a pick-up; that is why `$011256` always missed, and the five positive id words of §49b (`53 73 155 167 244`, real type-6 ids) are the keys:

| door | rooms | id word | item | flag `+7` | item placed in |
|---|---|---|---|---|---|
| `$3b` | 0 (CAVERN east) to 8 | 73 | "A SIMPLE IRON KEY" | 2 (consumed) | room 11 |
| `$20` | 19 to 20 | 155 | "A BRONZE DOOR KEY" | 2 | room 66 |
| `$31` | 27 to 28 | 167 | "A SMALL LEAD KEY" | 2 | room 69 |
| `$3c` | 4 to 22 | 244 | not yet read | 2 | room 4 |
| `$2a` | 13 to 36 | 53 | "THE ROYAL CROWN" | 0 (carried, never consumed) | room 37 (the treasury) |

**Live** (`py/secrets/overlay/action/route_to_room12.py`, below): the iron key taken by TAKE gives the rucksack record `(73, 57)`; CAVERN's east door at x lead 79, y 13..19 stalls without it (the word stays `0049`, `$00719a` not reached) and with it crosses into room 8, the word `0049` -> `0000`, the rucksack 1 -> 0. §13's "id 73 resolves to an already-resident room", §59's "`$3b` is a permanent self-loop" and §47c's "the id word encodes nothing" are all wrong: the destination still comes from the rectangle scan, the id word is the lock.

**The census hid the opener of `$22`** (and 48 other objects). `verb_decode.collect()` required `$17` at `len-1` of every block of an object, but a block whose script has odd length is followed by one pad byte that is `$17` only by luck (LEVER 472's is `$32`), and one such block dropped the whole object. With the pad accepted (`$17` at `len-1` or `len-2`) level 0 decodes 315 blocks in 224 objects (was 212 in 174), all exactly to their lengths; level 1 442 in 328 (was 264 in 220). The `scripts_level*.txt` dumps and the verb-use counts of secrets.md are regenerated. The corrected door table (verb 10 `CLEAR FLAG` and verb 27 sites, operands are hex door numbers):

| door | rooms | object, event | what the player does |
|---|---|---|---|
| `$33` | 1 to 2 | 144 LEVER, 5 | operate it from its panel (§71) |
| `$22` | 7 to 12 | **472 LEVER in room 8, 5** (`05 05 \| 0a 22 \| 17`: XP += 26, CLEAR FLAG `$22`) | operate it from its panel; room 8 is the closet behind CAVERN's keyed east door |
| `$18` | 15 to 16 | 81, 18 (gate `00 68`) | apply item 104 (shown in room 23 by EXAMINE of object 325, §73): done by natural input, §73 |
| `$1c` | 17 to 18 | 474 KEYHOLE in room 18, 18 (gate `00 68`) | apply item 104 too; its block sets its own state bit and deletes item 104 once object 81's bit is also set (*read*) |
| `$12` | 38 to 48 | FLAMEs 211 and 212 in room 38, 9 (gate `ffff`) | two touches in either order (*read*; the toucher is not driven) |
| `$23-$26` | 62 to 63, 64, 65, 66 | 239, 18 (gate `00 f0`) | apply item 240 (room 68): done by natural input, §73 |
| `$09` | 40 to 41 | 391, 18 (gate `00 6e`) | apply item 110 (room 40) |
| `$14` | 52 to 53 | 458, 18 (gate `01 cb`) | apply item 459 (room 53); the word is already 0 |
| `$3f`, `$40` | 23 to 26, 25 | 454, 18 (gate item 455) | apply item 455 (KEY, room 24); also creates three #447 objects |
| `$2a` | 13 to 36 | BUTTON 179 in room 14, 5, or the crown (53) carried | either one: the word is 53 and the descriptor never consumes it, so the crown alone opens the crossing; the fourth press of the chain 183, 181, 180, 179 clears the word, after which no crown is needed (§75, both driven) |
| `$29` | 36 to 60 | 486, 5 (type-8 id `$35` = the crown) | carry the crown into room 36 and operate 486 |

So the door words are not "11 sentinel doors": 13 level-0 doors start `$ffff` (`$09 $12 $18 $1c $22 $23 $24 $25 $26 $29 $33 $3f $40`), 5 are keyed, and every one of the 13 has an opener in the corrected census. §71's "no clearing script found for `$12 $1c $22`" is retired; verb 10 and verb 27 are the only writers of a descriptor's id word besides `$0071b8` (a whole-image read of the main image and the overlay by the subagent, no write to `$6d35a + 8n + 2` elsewhere; the overlay's UNLOCK/LOCK DOOR spells act on type-6 object records, §49-§50).

**The walk** (`route_to_room12.py`, natural joystick input only, from `lever_after.snap`; two runs give byte-identical logs and final snapshots): TUNNEL, 2, 6, 7 (door `$44`), 10 (`$39`, at the east wall with y lead 19), 11 (`$1a`); the iron key is the small object 73 (z 3), the stall at (44,35,38,29) probes `(73, icons 2 10 11 6)`, TAKE; back to CAVERN (the other doors stay open), Down to y lead 18 and Right at the east wall into room 8 (key consumed); room 8 has LEVER 472 at rect (6,17,4,14) z 16..33, the stall one step short of it (Up from the arrival, bbox (10,24,4,18)) probes `(472, icons 7 11 6)`, fire opens the panel, icon 7 confirms: `$00a448`, `$00a486`, `$00fe24` once each, XP 40 -> 66, door `$22`'s descriptor `25 16 ff ff 01 01 00 00` -> `25 16 00 00 01 01 00 00`. Back through CAVERN, TUNNEL, 2, 6 to room 7; door `$22` is on the south wall at local x about 64 (world (37,22) against room 7's rectangle [29,12]-[39,22], 8 px per grid cell): Down along the south wall at x lead 66 enters room 12 (arrival bbox (20,13,14,7)). Without the lever the same walk holds the hero at y 79 (a subagent's control: `$00716e` 11 times, the `$ffff` cue `$00731e` 11 times, room stays 7). Opening `$22` with the keyed doors still closed adds ten rooms (`door_reach.py --open 33 22 --keys 73`: 21 reachable, the new ones 12, 13, 14, 15, 18, 19, 61, 62, 67, 68); the keyed doors `$20 $2a $31 $3c` and the item doors beyond stay shut until their keys are found: item 240 (room 68) for object 239 (room 62, doors `$23-$26`) leads to key 155 (room 66) for `$20`, and item 104 sits in room 23, beyond it. Room 7's own contents (`probe`): 62-65 are scenery (no script), 253 sits at z 64..74, 271 is a takeable class-12 object ("VERY STRONG, ABOUT 11 FOOT LONG"; its event-4 block places it elsewhere), a random creature (279, 411 or 278) arrives by the room's event-14 timer at (46,32); the south half of CAVERN and the west of room 7 cost health (CAVERN's south walks fall from 67 to 1).

**Method.** A natural BFS over holds (`trek.py`: U/D/L/R to a stall or a room change, each node a snapshot, goal a room id or a probe) found rooms 2-7 in 33 nodes; walking to a door that sits mid-edge needs a finer hold (`goto`, 5,000-step chunks, one grid cell per ~10,000 steps after a ~40,000-step start lag), because a stall detector of fewer than six 20,000-step chunks ends the hold before the hero has begun to move.

## 73. From room 12 to room 16: the pickaxe wall, key 240 on object 239, bronze key 155, skeleton key 104 and object 81 (83rd pass)

**Event 18 works by natural input** (`overlay/action/route_to_room16.py`, a subagent's drive, re-run in this checkout: log identical to its two runs, 15 checkpoint snapshots byte-identical across runs, no poke). The rucksack panel (Space: `$009682`, `$009724`, `$009f02`) offers icon `$c` first when the object in front has class byte `$b` (objects 239, 81 and 474 do); `$009f02` stores the front object in `2128(A5)` and its class in `2476(A5)`, fire confirms `$c` (`$00a682` -> `$00a6f4`, event 18) and the object's block runs under the consumer with the held item's id compared against its gate (`00 f0` = 240, `00 68` = 104). The held item stays in the rucksack unless the block deletes it (239's block deletes 240; 81's leaves 104 in because 474's bit is not yet set).

**The route** (rooms by `1166(A5)`, every leg a joystick hold; `route_to_room16.py all` takes about 5 minutes, stages `a`-`e` resume from `scratchpad/cadaver/secrets_out/action/r16/ck_*.snap`):
- **Room 12 is a wall to demolish.** A hold stalls at (20,50,14,44) with no probe result: objects 170-177 are class-10 blocks (x 8..23, y 51..55, two per z level up to 63) whose scripts gate event 9 on a mover's template id `00 a8` / `00 a9` (pickaxe 168 / axe 169). The pickaxe is taken at the start (stage a begins at `sv_held_lever.snap`: pickaxe in the rucksack, lever 144 in front, then the §72 route). Space opens the rucksack panel (icons 11 13 1 6), `R` moves to icon `$d` (select: `1262(A5) = $00a8`), a 35,000-step tap Down turns the hero, and fire held 60,000 steps with nothing in front reaches `$00a19e`, a throw: the pickaxe flies (z 30 to 62 and back) and is blocked a few px short of the wall; throw 1 deletes the z 32-47 pair (174, 175), the top pair falls, the pickaxe lies in front, Down to the stall (20,45,14,39) probes `(168, icons 2 10 11 6)`, TAKE, back up, throw 2 deletes every remaining piece (rects 255), Down, Down, Left, Down reaches room 13 (fire with an object in front opens a panel instead of throwing, so the throw needs a few px of distance).
- Room 13 to 14 (Right) to 19 (Right, Right), Right, Left, Right, Up to 61, Up to y min 40, Left into 68. Key 240 ("A LARGE STEEL KEY") at the stall (29,30,23,24): TAKE `(240, 57)`.
- Room 62: Up, Right, Up, Up, Up, Left to the stall (11,16,5,10) of object 239 (class `$b`); Space, icon `$c`: `$00a682`, `$00a6f4` once, `$00fe5a` 5, `$0104e2` and `$010514` 4 each, the key deleted (`$00c30e`, `$00c3d4`), doors `$23 $24 $25 $26` all `ffff` -> `0000`, rucksack 1 -> 0.
- Room 66 (reached through 62's opened doors): TAKE the bronze key `(155, 36)`, back to 19, Right: door `$20` word `009b` -> `0000`, rucksack 0, room 20.
- **Item 104 is not placed anywhere at room 23's arrival.** Room 23 holds two tombs (z 0..17), 188 and 325 on the first, 191 on the second ("HOW DARE YOU DISTURB THE DEAD", event 7); 325's event-16 block runs `SHOW object #104`, so the skeleton key appears (x 34..36, y 65..67, z 26..29, class 13) only after 325 is EXAMINEd, and 325 can be examined only from beside it. The route jumps (back off 60,000 steps, fire+right) onto 325 (z base 26), creeps east until it drops onto 188 (base 20), taps Left 50,000 steps (probe `(325, icons 10 11 6)`), EXAMINE (icon 11: `$00a418`, `$00fe5a` once), then jumps again: the hero's walk east on top of 325 pushes the key ahead (x 42..44) and the probe facing right returns `(104, icons 2 10 11 6)`, TAKE `(104, 57)`. A fire probe sees only what is directly ahead: stop beside an item that is no obstacle.
- Back through 22, 20, 19, 14, 13 to room 15 (the detour through room 18 is harmless), settle 100,000 steps, Down, Left to the stall (13,75,7,69) of object 81 (class `$b`), Space, icon `$c`: `$00a682` 1, `$00a6f4` 1, `$00fe24` 3, `$0104e2` 1, `$010514` 1, door `$18` `2530ffff...` -> `2530 0000...`, rucksack `(104, 57)` kept; Down leaves room 15 for room 16 (arrival (20,13,14,7); entries 196 and the wall pieces 367-370).
- Door `$1c` (object 474, KEYHOLE in room 18) takes the same icon `$c` with 104: door `$1c` went `ffff` -> `0000` with the same hits (a separate exploration run, not in the script); apply it after 81, since 81's script deletes 104 only once 474's bit is also set.

**Hazards.** Health falls along the route: 63 to 53 in room 68's west end, 48 and 38 beside object 81 and 474, because objects 902 and 904 (class 3, instances of template 443 created on room entry, x 14..21) cost about 5 health per 150,000 steps; the run ends room 16 at health 33, and a hold from 474's stall reached health 0. Health, not routing, limits further detours. A hold's outcome also depends on a one-step phase (`Repl.__init__` runs `s 1`): the script snapshots, closes and reopens the REPL at the points where the explorations did, a continuous run without those reloads diverged in room 19; after a room arrival wait about 100,000 steps before Space or a hold.

**Where it leads.** Room 16's doors are `$19` (to 17, hardcoded) and `$1d` (to 30); `door_reach.py` puts 16, 30, 31, 32, 33 on the road to the regalia room; §74 walks it.

## 74. From room 16 to the treasury by natural input: health, the holy water of room 30, room 15's gem, the jar (85th pass)

**The road is open and costs nothing if the hazards are avoided** (`overlay/action/route_to_room33.py` from `r16/ck_e_room16.snap`, then `regalia_walk.py full` with `RW_START` set to the arrival snapshot `ck_h_room33.snap`: nothing injected, nothing poked; the route twice, 7 checkpoint snapshots and the log identical, the regalia walk twice, 99 snapshots and the log identical). Legs, every one a joystick hold or the object panel:
- Room 16 (health 33): `L` crosses door `$1d` into room 30 at (55,20,49,14); `L` again stalls at (29,20,23,14) against the holy water 213 (probe `(213, [2, 9, 10, 11, 6])`). The panel's icon 9 (`$00a5c0`, event 5) runs 213's block (message "THE WATER TASTES GOOD", verb 45 +2, verb 2 delete): health 33 -> 35.
- `D` to the south wall, then Right along it to x lead 37, then `D`: room 31 at (68,13,62,7). The gap is door `$2b` (portal 1 of room 30, bytes (51,53,28,48,47,0)); the stall-to-stall search's `D` holds at x 49..55 (after `L D`) and at 23..29 stalled against the wall instead, while stops at x lead 37 and 43 (`goto` with an x condition) both crossed, so the gap lies between x 31 and 43 at least.
- Room 31: `L` (door `$2c`) enters room 32 at (39,20,33,14), `D` to (39,31,33,25), `L` to (12,31,6,25), `U` through door `$2d` into room 33 at (20,47,14,41), health 35.
- Room 33 -> the treasury: `U` to y lead 28, `R` to the stall against 31, back off 60,000 steps, fire+right (the jump of secrets.md's regalia paragraph) lands on 31's west edge (x lead 46) because this start is south-west of where the injected entry was, `R` on top to x lead 51, then the search finds the circlet 32 as `RDUD` (stall (55,44,49,38), probe `(32, [2, 10, 11, 6])`); 28 by `UL`, 16 by `UR`, 26 by `RUL`, the BUTTON by `LDLUR`: room 33 -> 34 -> 37, XP 106 -> 132, health 35, rucksack `(104, 57)` plus the four regalia consumed by the BUTTON's verb 34 tests. This retires the injected entry (`regalia_walk.py` without `RW_START` still uses it, for the older proof).

**Health, in full.** The writers of `1174(A5)` in the level-0 image (`find_field_writers.py` on `gameplay_empire.snap`, main code and overlay: 7 references) are `$00695e` (level start, two thirds of the maximum), `$00e60e` (the save restore) and `$010cc8` (verb 45's adder; `$010c8c` is its entry after the operand read, and the container handler below calls it too). Nothing in that image regenerates health. Restoratives in level 0 are the two waters in room 30 (+2 each), the flask 135 in room 45 (+2), the flask 392 in room 46 (+10) and the potions (STAMINA 86 sits in the treasury, room 37, which the static census lists at room 37, unverified); so 35 health reaches the regalia room and the BUTTON, with nothing to spare for a hazard. **Hazard ledger, measured on the way** (a breadth-first search over holds with `trek.py`'s node semantics, pruned on any health loss): room 15's roaming object 902 (instance of template 443, class 3, event 9: -5 per touch; its rectangle was (20,48,13,41) in one snapshot and (20,34,13,27) in the next) cost 30 for one Up crossing of x 13..20 (33 -> 3) when taken soon after the arrival; §75 times it (the crossing is free if the hero waits 2,300,000 steps first); room 31's floor cost 15 for `D L R` and 30 for `D R L R` (35 -> 20, 35 -> 5); every stall the search reached in room 30 cost nothing, and creature 237 of room 30 did not touch the hero in these runs.

**Room 15's ten-visit reveal, driven** (`overlay/action/room15_gem.py`). The entry block's counter, variable 8, rises by one on each entry (the block runs a moment after the arrival: read after `s 150000`) and is 2 at room 16 on this route: eight Up entries from room 16 give 10, health unchanged (33). At 1 the block creates the hazard 443 and shows 414, at 2 to 9 the stones 424-431, at 10 the gem 131 at (8,49,6,46), z 0..2, and marks itself spent. The stones (x 6..12, y 14..68) wall off the west; the lane to the gem is Up to y lead 56 or 55 (a hold's final y depends on where `goto` stops: rows 50..56 hit object 428 at y 56..58 and Left stalls at (19,56,13,50) with probe 428, rows 49..55 clear it) and then Left to (14,55,8,49): probe `(131, [2, 10, 11, 6])`. TAKE (icon 2) runs 131's event-0 block, `5 XP += 26`, `6 GOLD += 100, XP += 100/4`, `2 DELETE`: gold 0 -> 100, XP 106 -> 157 (+26 +25), the rucksack count stays 1 (the record `(131, 34)` remains beyond the count). It is a treasure, not the CURE potion: the alchemist's letter (object 388, "YOUR CURE POTION I HAVE HIDDEN IN THE COMMON CRYPT, THE STONES BEING THE KEY") is the riddle of a different place.

**Icon 3 is OPEN on a class-8 container, with a trap** (handler read, `$00a494`-`$00a5b4`; its health effect driven on the jar 72 in room 30). The probe at the stall (12,37,6,31) after `L D L U` gives `(72, [2, 3, 10, 11, 6])`, class 8, subclass 5. The handler: for class 8, when bit 0 of `4(A6)` is clear, `neg.w` of the byte `5(A6)` goes through verb 45's adder (`bsr $010c8c`), then the lock word `2(A6)` is checked with the rucksack scan `$011256` (a key id), the contents word `(A6)` is placed with verb 41's `$010aaa`, and bit 0 of `4(A6)` toggles. Live: `$00a494` once, health 33 -> 28 (a control with the cancel icon over the same steps: 33 -> 33), no event-5 push at `$00a59c` and no consumer run (`$00fe24` 0 hits); the jar's own event-5 block ("IM AFRAID THE JAR IS TOTALLY EMPTY") was therefore not run by icon 3, so what answers it is still open. The chests 83 and 224 (class 8) and the contents path are the other half.

**Where it leads.** The treasury holds the royal crown (object 53, one `R` east of the arrival: probe `(53, [2, 10, 11, 6])`, TAKE writes `(53, 26)`, rucksack count 2 with the skeleton key; `regalia_walk.py crown`), and the crown is a pass of door `$2a` (room 13 to 36, the word 53 is never consumed; §75 finds that the BUTTON chain of room 14 opens it too) and, with object 486 in room 36, the way to door `$29` into room 60, where object 84 ("YOUR MEANS OF TRANSPORT TO THE CASTLE") runs verb 51 (START LEVEL, `scripts_level0.txt`): the natural exit of level 0. §75 drives the road to it and finds the dragon that stands in the way. `door_reach.py --open 33 22 23 24 25 26 20 18 1c --keys 73 155 104 240` reaches 46 rooms and not 60 or 36; the doors still closed are `$09`, `$12`, `$29`, `$2a`, `$31`, `$3c`, `$3f` and `$40`. Health 35 and the heal list above set the budget of any further walk: the flask 392 in room 46 is the one worth routing to.

## 75. Out of the treasury to room 36: the BUTTON chain, a patrol that is not a hazard, the dragon, the level change, and the teleport graph (86th pass)

Eight exploration agents each took one track from the open list; the two road scripts below were then promoted and re-run here. Labels: **driven natural** (joystick and keyboard only, nothing poked or injected), **driven injected** (state poked or a teleport/item injected, named), **read**, **inferred**. Findings without a promoted script say so.

**The road from the treasury to room 13's door `$2a` costs no health and gains 2** (driven natural; `overlay/action/route_treasury_to_room16.py`, 2 runs here, log and 12 of 12 checkpoints identical to each other and to the agent's two runs; then `route_room16_to_door2a.py`, 2 runs here, log and 11 of 11 checkpoints identical to the agent's; chained from the first script's end snapshot: all 14 health readings 37). From `rwn2/taken53.snap` (room 37, crown 53 and key 104 carried, health 35): `L` puts LEVER 86 in front (probe `(86, [7, 11, 6])`), icon 7 runs its block (`37 22 2 2 0`) and lands in room 34 at (16,16,10,10) with no health or XP change; `R` room 32, `U` room 33, `D` room 32, `R` room 31, `R` to the stall (73,20,67,14), `U` room 30 at (44,47,38,41), goto Left to x lead 34, `U` to the stall (33,15,27,9): water 214 is a non-obstacle in front (`(214, [2, 9, 10, 11, 6])`), icon 9 drinks it (35 -> 37), `R` through door `$1d` into room 16 (13,20,7,14), health 37. Room 34 also holds object 2, the BUTTON of the regalia gate (probe `(2, [4, 11, 6])`), and the unidentified object 94; its other exits are `D` to room 35 and `R` to 32. The legs came from a breadth-first search over holds pruned on any health loss: room 31's floor (`DDRL`, `DLRR`, `DRLR`) and room 15 (`URUU`) cost 30 elsewhere, the culprits are not named (`A0` not read).

**Room 15's roaming object 902 is a patrol with a safe window** (driven natural, 11 timed trials and a 40-sample trace in `scratchpad/cadaver/s86/a2/`). In the lane x 13..20 it walks y 31..79: north to y 31..38 by about 1,200,000 steps after the arrival, south to y 45..52 at 2,000,000, paused there until about 2,400,000, then south to the hero (a hero left standing in room 15 loses 33 -> 23 -> 3 by 3,400,000). Health after the climb to room 13, by steps waited before `U`: 0: 3; 300,000: 23; 600,000 to 2,000,000: 3 (seven trials); 2,300,000: 33; 2,500,000: 33. So §74's "30 per crossing" was an impatience cost: `route_room16_to_door2a.py` waits 2,300,000 steps, climbs (`U`, about 2,000,000 steps) to room 13 at (20,23,14,17) and loses nothing. Overlap of 902's rectangle with the hero in x, y and z cost nothing in the 2,300,000 run (hero y 58..64 against 902's 57..64 at about 380,000), so a bare overlap is not the damage condition; the condition is not found (open). Room 17 (door `$19` from 16) holds only 297-299 and does not lead to 14: door `$1c` is `ffff` and keyhole 474 is on room 18's side, reached from room 14 by door `$1e`.

**The four BUTTONs of room 14 are a chain, and the fourth opens door `$2a` for good** (driven natural, the same script). Room 14 (arrival (10,20,4,14)) holds 183, 179, 180 and 181 in a row on the north wall (x 8..11, 20..23, 33..36, 44..47), each probing `(id, [4, 11, 6])`. Their blocks read as a ladder: 183 sets its state bit, 181 needs 183's and clears it, 180 needs 181's, 179 needs 180's, runs CLEAR FLAG `$2a` and SHOWs object 184 ("THE KEY SEEMS BADLY DAMAGED"; 184 is never placed in room 14). Pressed in the order 183, 181, 180, 179 (icon 4 each: `$00a43c`, `$00a486`, `$00fe24` once; only the 179 press hits `$0104e2`) door `$2a`'s descriptor goes `2a21 0035` -> `2a21 0000`. Pressed 183, 181, 179 (skipping 180) the 179 block's ELSE clears all four bits and the word stays 53; 180 first changes nothing. The press stands are y lead 10..11, x lead 10 (183), >= 48 (181), <= 38 (180), <= 25 (179). Then `D`, `L` into room 13's east arrival (79,20,73,14), `U`, `L` to the stall (50,12,44,6) under the door. Control: before the chain `U` there does not move (word 53, no crown carried); after the chain `U` crosses with no crown in the rucksack (room 36 at (20,71,14,65), health 33). So the chain replaces the crown at this door; the crown is tested only at object 486 (below, read), and a hero that carries it needs no chain (driven injected, below).

**Room 36 holds a dragon that must die before object 486 exists** (the last leg driven with three injected steps; `scratchpad/cadaver/s86/a3/`, `a9/`). From `taken53.snap` with health poked to 100, a verb-37 entry into room 13 at (64,20,58,14) and the crown carried: `U` crosses door `$2a` into room 36 at (20,71,14,65) (XP +26, event 28; the control with the crown but no chain also opens it, word 53). Room 36 at entry: the wall 451 (41,25,28,8) z 2..23 (touch -25; one `U` hold stalled against it went 100 -> 25 -> death), the dragon 483 at (33,43,26,34) z 39..53 (the hero's z 0..29 passes under it), 484 (56,9,49,4), 487, 74 and 489; **486 is not placed**. The only clear lane to door `$29` (portal 0, x 28..51, y 0..2) is the 7-cell gap between 451 and 484: hero x lead exactly 48 (`goto(RIGHT, lead >= 47)` with 5,000-step chunks; `>= 48` overshoots to 49 and stalls on 484). Fire 905-907 (class 3, spawned by 483's timer block; 485's contact block is -20, or "THE FIRE CAUSED YOU NO HARM" with shield bit 1 of `2436(A5)`, then verb 50 kills the fireball itself) creeps toward the hero 3 to 8 cells per 100,000 steps from about 100,000 steps after the arrival; the dragon never moves, its own contact block is -50. The dragon's event-23 block (`scripts_level0.txt`): UNREGISTER, delete itself and 451 and 484, XP += 26, SHOW 486, PLACE 500 (the carcass, whose examine reveals the booty 501-508) and set its bit 0. **Event 23 queued for 483** (driven injected, `kill483.py`: one `$00fe24` hit) deleted 451 and 484, placed 486 at (68,3,65,3) z 26..39, 500 at (60,50,43,18) and a corpse 908, and paid +526 XP (the block's own verb 5 is +26: the other +500 is not found). Then `R` stalls three times against fireball contact before reaching (64,9,58,3) against 486: probe `(486, [4, 11, 6])`, icon 4 (`$00a43c`, `$00a486`, verb 10 once at `$0104e2`/`$010514`): door `$29` `2d17 ffff` -> `2d17 0000`; `goto(LEFT, lead <= 50)` to (49,9,43,3) and `U` enter room 60 at (20,31,14,25) (event 6, XP +26). Health ledger of that leg 100 -> 80 -> 60 (two fireballs). **Who can kill it is answered in §76.** Every verb 50 in the level-0 dumps kills its "actor" (the toucher or the object running the block); no script targets 483 and 483 never moves. Its HP is the byte at instance +80 = 250 (`$fa`), maximum +84 = 250, flag byte +86 = 4 (bit 0 clear: vulnerable; record byte 12 = 80 locates the block; read live). The projectile-hit scan (`$00f9c4`-`$00fa2c`, read) routes a mover on its class byte (+22): `$81` and `$84` go to `$00facc`, which for a class-3 victim subtracts byte 1 of the projectile's own block from the victim's HP byte and queues `op $17` (event 23) when it does not stay positive; `$80` goes to `$00fa8e` (damage to the hero). **A thrown pickaxe cannot do it**: its class byte is `$1a` (the axe's `$37`); 6 of 6 injected throws ran the throw handler `$00a19e`, the pickaxe landed about 12 cells ahead still airborne at z 29..33, 0 hits on `$00facc`/`$00faf4`, HP stayed 250. The MAGIC MISSILE and MASSACRE scrolls this paragraph's first version named were census errors: 463 and 450 are stones and a potion (§76), the hand-poked casts never ran the real apply path, and the one thing that kills the dragon is MASSACRE 324, found in §76 with the chain that delivers it.

**The pickaxe can be carried to room 36, but it is no weapon** (driven natural, `a10/route_room13_pickaxe.py`, 2 runs with 11 identical snapshots; not promoted because A9 shows it does not matter). From the door `$2a` stall: `D`, `L` (west wall), `U` into room 12 (20,79,14,73): the pickaxe 168 lies at (20,69,13,65) z 0..3 (a creature 901 roams the room), `U` runs to (20,33,14,27) with `(168, [2, 10, 11, 6])` in front (it is pushed ahead like key 104, inferred), TAKE: count 2 -> 3, `[(104,57), (168,32), (53,26)]`; back `D` into room 13 (20,13,14,7), never hold `D` there (the south door to 15 costs 5), goto Down to y lead 19, goto Right to x lead >= 50, `U` into room 36. Health 37 on every leg. The most recently taken item is the held one (Space, icon `$d`: `1262(A5)` = `$00a8` for the pickaxe, `$0035` for the crown without it). The axe 169 lies only in room 3 (26,17,19,13) behind blocks 197, 235, 236 and a creature 900 (not reached).

**Room 60 and the level change** (driven natural after the injected kill, A3): room 60 holds 84 at (5,17,3,14) z 16..33 and 490 (the dead man, "SOME POOR MAN WHO DIDNT QUITE MAKE IT"); `L` to (11,31,5,25), `U` to (11,24,5,18): probe `(84, [7, 11, 6])`, icon 7 (`$00a448`, `$00a486`, `$00fe24` once) is verb 51. Straight after it `2524(A5)` reads `0101`, room 0, health 0, XP 0, then the game waits at a "PLACE LEVELS DISK ... PRESS A KEY" screen that 7,000,000 idle steps do not change; Space (`kbd 39`, 60,000 steps, `kbd b9`) and about 20,000,000 steps load level 1 (`$0118ec` 4 hits, `$00ba2e` 5, `$00695e` 1): `2524(A5)` = `0100` (a level word that reads `0100` in level 1), room 0, the hero at (42,46,36,40), **health 60 carried over (not reset) and the maximum raised from 100 to 200, XP 710 carried, the rucksack empty** (key 104 and crown gone). The level-start health rule at `$00695e` is not read: the carried value may be what the "two thirds of the maximum" reads as when the old value is higher, or it is not touched at all (open).

**The heal road and the other loose rooms.** Each below was driven natural once by an exploration script (not promoted; no chained script and no identical re-run yet) unless marked.
- *Flask 392 costs nothing to reach and gives +10* (driven natural, `a4/s*.py`): from `r16/ck_e_room16.snap` 10 holds: `R` (room 17 (13,20,7,14)); goto Right to x lead >= 40, `D` (room 38 (44,13,38,7)); `D`, goto Left to x lead <= 22, `D` (room 39 at (20,13,14,7), the left gap of 38 at x 10..22, door `$03`); goto Right to x lead >= 46, `D`, `D` (room 40 at (44,13,38,7)); after settling `D L R D` (room 42 at (68,13,62,7)); `D R L D` (room 46 at (20,13,14,7)); `D` to (20,33,14,27), goto Left to (12,33,6,27), tap `D`; the scented oil 182 blocks the way (icon 2 takes it, drinking it is -1); `D` to (12,36,6,30): probe `(392, [2, 9, 10, 11, 6])`, icon 9: health 33 -> 43 (`$00a5c0`, `$00a5d2`, `$00fe24` once), the flask stays as an empty flask. Health 33 at every stop. Rooms 38 and 39 spawn roaming #444 creatures (-2 per frame; the right and centre gaps of 38 cost 8 to 32) and room 40 three #449 creatures (kill on contact, none touched in 60 holds); room 45 drains health (`D` from its arrival -18, `L` then `D` -32; flask 135 never found by a probe), cause unnamed (its event-15 blocks, read). Object 108 in room 43 SHOWs item 110 from an event-4 block (gate item 45), so item 110 comes through room 43, not room 40 (read). The flames 211/212 of room 38 (door `$12`) were not touched.
- *Room 24's item 455 opens doors `$3f` and `$40`* (driven natural from `r16/ck_d_key104.snap`, health 53, `a5/*.py`): from room 23 `R R U L`, goto Right to x trail >= 8, `U` into room 24 (20,63,14,57); `U`, `R` stalls at (60,29,54,23) with item 455 (start (36,27,34,25), z 0..3, pushed ahead like key 104) in front, TAKE: rucksack `[455, 104]`; `L` to (12,29,6,23): probe `(454, [11, 6])`, Space, icon `$c` (`$00a682`, `$00a6f4`, `$00fe24` once, `$00fe5a` 6): doors `$3f` and `$40` `ffff` -> 0000, 455 consumed, health unchanged. Three spiders (#447, class 3) appear at (24,61,21,58), (32,57,29,54), (28,44,25,41) and chase the hero (-2 per touch, then they die, +5 XP; a corpse blocks the lane until deleted). Door `$3f` (23 to 26) is crossed only in the x 6..12 lane (goto Left to x lead <= 15, `D`, `L`, `D`): room 26 (20,13,14,7), 19 entries, takeable 341, 342, 347 and gold objects 346-349 (+3 gold each), no health loss. Door `$40` (23 to 25): goto Up to y lead <= 59, `R`: room 25 (13,28,7,22), the flask room (48 is harmful, -5; 282 "FLASK COVERED IN FROGSKIN" icon 9; the bowl 379 "ADDING HOLY WATER TO A BLESSED BOWL"; 87 and 461 takeable). Room 24 also holds the tombs 90 and 111 ("APPEASE THE SOUL OF THE DEAD WITH GOLDEN PIECES") and BALMIC FLUIDS 142 (icon 9, effect untested).
- *Rooms 27-29 are reached only by teleports* (graph *read* from both dumps; teleports driven injected, `a6/`). {27, 28, 29} is a closed door component (27-28 door `$31`, key 167; 28-29 door `$37`, open). Door-only reachability with every `$ffff` door opened and every key held is 65 of 72 rooms (not 27, 28, 29, 37, 47, 69, 71); adding every verb-37 edge gives 70 of 72 (not 69, 71); the natural road's keys (73, 155, 53, 104) reach 48 rooms, and the drop of room 21 adds exactly 27-29. Teleports: room 21's hole (region (39,22)-(43,26), z 8..10, with object 207's bit 0 set, which object 207 in room 20 places by its event 5) to room 27 (8,4,`$50`): driven injected, the fall cost 10 health (the rope 271 from room 7 changes the block, read); room 4's pit (region (8,8)-(19,19), z 8..10) to room 28 (8,3,`$50`): driven injected, hero at (64,24,58,18); room 28's chain region (x 44..52, y 12..20, z 75..110, the CHAIN 382 at z 82..107) back to room 4 (3,3,0): driven injected; room 27's event 17 to room 49 (2,2,0) once variable 4 exceeds 5, which needs six objects of template low byte `$29` or `$42` pushed into room 27's pit region: read; room 48's entry to room 22 (6,1,0) with variable 4 above 4: driven injected with the variable poked; 37 -> 34 (LEVER 86, driven natural above), 34 -> 37 (BUTTON 2), 38 -> 37 (object 56 with the same four regalia) and 45 -> 47 (bowl 162 bit 0), 47 -> 46 (object 129): read. Contents (driven injected survey, health 100): room 4 has the PIT 238 and key 244 at (14,33,13,31); room 22 is a transit room (doors `$21`, `$3c` with key 244, `$3d`); room 27 holds 22 entries (stones, bones, the GIANT RAT 194 at (72,74,60,63), PARCHMENT 226, KEY 184 at (40,78,38,76), CHEST 224 at (30,76,21,71)) and drains health 1 per about 25,000 to 32,000 steps in its pit region (cause unknown); room 28 the CHAIN 382 and three #449 objects on first entry; room 29 four gems 186, 187, 189, 190, a book 225 and bones; room 69 is a reservoir of 28 placed entries (KEY 167 at (67,30,65,28), flasks, scrolls 482, charms 491 and 163, a -2 creature 127, create templates) that object blocks move out with verb 73 (167 from the rat 194). Injecting the rat's event 5 put key 167 at (76,70,74,68) beside it.
- *Level 1's first leg and its graph* (driven natural, 2 identical runs, `a7/route_level1.py`; the rest read): from `level1_loaded.snap` (room 0 (42,46,36,40), health 67, the CAVERN value carried across the injected level load) `U L U` to room 34 (52,63,46,57), `U` (a no-op that still changes the reload phase), `L`, `U` to room 29 (20,79,14,73), `U R U R` to room 31 (10,20,4,14); health 67 throughout. Room 29's lane `R` then `U` costs 60 (67 -> 7), room 34's `UU` 10 (inferred from `HEALTH += $fff6` in objects 429/200). Level 1 has 129 doors over 97 rooms (`door_walk.py`); from room 0 the open doors reach 35 of 90 rooms with doors; the openers of its 39 closed doors are in `a7/opener_rooms.txt`. Door `$74` (room 17 to 87) is opened by room 17's region (event 15) when the rucksack holds item 730 (room 68) or 731 (room 90); room 87 deletes weapons and magic items on entry and answers six teleporter objects; room 88's region runs START LEVEL (level 2) when object 735's bit 0 is set by its event-20 countdown. Room 31's altar puzzle (altar 131, drape 130, skull 198 at z 56..62 whose event-9 block GOMOVEs 130 and 131) is not solved; an injected GOMOVE did nothing and a hold after `H.real()` moved nothing (reload after every injection).
- *Containers, event 26 and icons* are in secrets.md ("The container block and the icons not driven before").

## 76. The dragon's killers, the class-byte correction, and the rest of the south-east cluster (87th pass)

Eight agents on tracks from the open list, then six follow-ups on the dragon (`scratchpad/cadaver/s87/FINDINGS.md` has every report). Labels as in §75. One script set was promoted and re-run here; everything else is exploration (single runs unless a count says otherwise).

**The census had the class byte from the wrong table; three "weapon" findings of §75 were wrong.** The description routine `$011066` takes an object's class from byte 22 of the type-2 class template named by the type-6 record's word at +6, and its block from the type-6 record at byte 12 (`item_census.py` read byte 22 of the type-6 record, which for a record with body offset 22 is body byte 0; fixed, and the output of the fixed script agrees with the agents' re-keyed table `s87/b6/cls_table.txt`). So **object 450 is a potion** (class 2, potion id 1 SUPER FAST, "THE BOTTLE ... N.I.K.E."), not a MASSACRE scroll; **463, 469 and 121 are class `$81` THROWING STONES** (damage 3, 150, 200 and 20 stones), the ammunition templates of three bags (class 4: 462 in room 8, 470 in room 58, 23 in room 2), not MAGIC MISSILE scrolls in a starting kit; and the real scrolls (class 1) are 27 MAGIC MISSILE (power 15, 20 charges, room 47), 324 **MASSACRE** (power 200, 1 charge, room 39), 87 FREEZE (room 25), 461 LEARN POTION (room 25), 132 READ LANGUAGE (room 41), 161 MIND BLAST (room 47), 259 MAP (room 44), 304 BLESS WEAPON (room 55), 371 READ MAGIC (room 40), 82 TURN MONSTER (room 70) and 482 DISPELL TRAP (room 69). Potions placed: STAMINA 62 and 140, SUPER FAST 450, GIANT JUMP 282 (room 25), ALCOHOL 255, POISON 139/142, SHOT SHIELD 141 (room 24), WATER, FIRE SHIELD 12 (room 69 only), CURE 116, MAGIC SHIELD 256 (room 47), CURE POISON 460.

**Only one thing kills the dragon in the game's own rules: a MASSACRE cast** (driven, items given by verb 35, injected). Event 23 reaches a victim from four code sites: the hit scan's damage path `$00facc` (HP -= byte 1 of the projectile's block), verb 50 (13 of 13 scripted uses act on the actor, none names 483), the overlay's own-creature handler `$04c88e`, and the spells MAGIC MISSILE `$4cd94`, MASSACRE `$4cde0` and MIND BLAST `$4ce54`. The extra +500 XP of the injected kill is paid by the event-23 gate `$00ff4e` (`add.l D0,1192(A5)` at `$00ff6a`, D0 = block byte 4 = 250 doubled by block byte 6 bit 2): every victim with an event-23 block pays it, so a natural kill pays 26 + 500 = 526 XP. **MASSACRE 324** walks the list at `396(A5)`, which holds `[483]` about 100,000 steps after the arrival; one cast with fire held and the scroll selected (Space, icon `$d`) kills the dragon with no aim and no range (event 23 queued at `$4ce24`, 451 and 484 deleted, 486 at (68,3,65,3), XP 158 -> 684, the scroll consumed). It must be learned first: 324's body byte 3 bit 7 is set and `$f02e` refuses with message `$25` ("YOU DONT HAVE THE WISDOM TO USE THIS SPELL YET", 11 hits in 300,000 steps). **READ MAGIC 371** (class 1, body byte 7 = 2) is offered icon `$10` (`$a0ce`; the table at `$a0ac`) only with an object in front of the hero: with 324 lying in front it clears the bit and is consumed (1 of 1).

**Nothing else reaches the dragon from a place the hero can stand.** All five of these were driven in room 36 (items injected, health poked to 100):
- *Thrown stone object* (icon `$d`, handler `$a19e`): one hit of 3 (250 -> 247) from hero y 54..65, then the whole object is deleted (a thrown object takes its count with it); 84 hits would need 84 objects.
- *The bag's own fire* (icon 13 SELECT, mode 4, handler `$f150`): one stone per shot, ~100,000 steps per shot, the shared ammunition byte (template block byte 2) 150 -> 149; 36 shots, 0 hits. The stone is a ballistic arc anchored to the spawn (spawn z = hero bottom + ~21, apex top z 29 at about 12 cells, z 1..4 at y 33); the dragon is z 39..53 at y 34..43, so a floor shot never touches it, and the hero needs bottom z >= ~14. Stones that meet the dragon's class-3 fireballs hit those instead (`$facc`, 15 of 16 shots in one run).
- *Scroll 27's missile* (real cast: `$f02e`, `$f0f6`, `$1083e`; ammunition template 476, class `$82`, whose body byte 0 gets spell id | `$80` and byte 1 the scroll power; a strike on anything runs `$fa34`, queues event 1 and calls `$4cd94`): spawns at z top 22 and sinks one z per ~20,000 steps, so from the ground it flies at z 22..18 under the dragon and is deleted at y 32..27 by an unidentified target (wall 451, inferred); it would need hero bottom z >= 20.
- *Height*: the hero cannot shoot or cast in the air (the joystick/fire read at `$006e10` runs only when the jump pointer `312(A5)` is 0; Space in the air opens the panel and pauses; a fire held across a flight acts at landing), and the only raised floor in room 36 is wall 451's top (z 23): the hero can land on it (1 of 1, from (43,42,37,36) with UP + fire) and is hit for 25 four times in about 120,000 steps (2 runs). A thrown pickaxe is class `$1a` and misses the damage path (6 of 6).
So a fatal weapon exists only as the MASSACRE scroll, unless a source of height appears (GIANT JUMP 282 does not help while fire is ground-only).

**FIRE SHIELD 12 stops the fireballs** (driven injected): a drink sets bit 1 of `2436(A5)` (power 100 into `2437`) and arms timer 3 at 40 ticks of ~410,000 steps (~16.4M steps); object 485's event-9 block then prints "THE FIRE CAUSED YOU NO HARM" instead of -20 (health 100 for 25 x 100,000 steps against 100 -> 40 in 2.5M unshielded), and verb 50 kills the fireball either way. The dragon's own contact (-50) and wall 451 (-25) do not test the bit. Potion 12 is in room 69's pool; the chain that delivers it is chest 109 (room 67, icon 3) to coin 113, carried to room 57 and thrown onto tomb 103 (driven natural from an injected entry: the throw lands, `$a19e`, `$8a34`, `$8a68`, `$f368`, `$100b0`), then soul 107 rises and its event-12 block MOVEs the potion to the tomb top, where the hero cannot reach it from the floor.

**The MASSACRE chain is the game's own design, and it is long.** Reading the blocks: 324 is hidden in room 39 until object 165, "THIS URN HOLDS THE SOUL OF CAROLUS" (event 0 on take: -5, "TO DISTURB THE SOULS OF THE DEAD IS TABOO"), lands on **altar 99, "THE ALTAR OF LORD CAROLUS"** (room 39, rect (33,48,7,33) z 18..21 on platform 97; event 4 gate 99: SHOW 324, XP +26, delete 165, "THE LORD CAROLUS CAN NOW REST IN PEACE"). 165 is hidden in **chest 157** (room 56; lock key 166 in room 51; trap byte 5), whose icon 3 damages and returns before the lock test (§ "container block"), so the trap must be cleared by the DISPELL TRAP scroll 482 (cast with icon `$10` at the chest: trap 5 -> 0, then icon 3 consumes 166 and shows 124, 165, 398 "ONLY THE CROWN OF THE KING ALLOWS ONE TO PROGRESS"). 482 sits in room 69's pool; urn 453 in room 53 moves it out when the urn smashes (event 11: pushed off its platform, §77). Carrying 165 to the altar: a thrown urn follows one fixed arc (8 cells ahead at z 30..37, apex z 59..66 after ~21 cells, z 16..23 at 34..35 cells); thrown west from (49,40,43,34) after a 20,000-step LEFT tap it lands on the altar top and runs the block (1 of 1; from x lead 48 it lands half off the altar and fires nothing), and 324 then rests on top of the altar (z 22..25), which the hero reaches with one jump and takes from the altar's top (§77). READ MAGIC 371 is SHOWn together with key 110 by the HIGH ALTAR 45 (room 40) when flask 108 is thrown onto it; 108 is SHOWn by urn 143 thrown onto statue 156 (room 43; event 4 gate `$9c`, XP +26; drinking 108 is -20; a drop fires no event 4, §77); urn 143 is the content of chest 224 in room 27 (lock key 184), so the chain goes through room 27. Key 110 with object 391 (room 40, icon `$c`) then clears door `$09` (rooms 40-41), and urn 389 of room 41 on statue 46 makes three spiders; statue 51 of room 44 reads "HE WHO RETURNS MY SOUL TO ITS RESTING PLACE SHALL PASS TO THE CASTLE".

**Room 27 and the road to 371** (driven natural except one step). The natural road to room 27 from room 23 costs 10 health, all of it the fall: `R D L U`, goto Down to y trail 38 at x 6..12, `L` (door `$3d`) room 22, `L` room 20; object 207 (probe `(207,[4,11,6])`, icon 4 from (40,10,34,4)) places 203 and 204; door `$41` by goto Down y lead >= 22, goto Right x lead >= 70, a `U` held ~600,000 steps; room 21 (68,55,62,49), goto Left x lead <= 45, `U` walks into the hole and lands in room 27 at (64,32,58,26). Room 27's drain is its pit region 1 (x 0..40, y 0..56, event 15, -1 per cell; the "unexplained" drain was the hero's trail overlapping it): never hold `U` at x <= 40. Walking pushes the loose objects: `L` along the south wall carries key 184 to the west wall; icon 2 takes it; chest 224's icon 3 consumes it and places urn 143; the rat 194's icon 3 runs its event 5 (key 167 appears); door `$31` then opens into room 28 (13,20,7,14) (30 tokens, two runs, 30 of 30 checkpoints identical, health 43 unchanged). **Room 28's only way on is the chain region (x 44..52, y 12..20, z 75..110), which no jump reaches** (floor peak top 64; from pillar 301 the apex x is at most 39): one verb-37 step `28 6 3 $50` puts the hero in it, event 15 sends it to room 4 at (32,16,26,10), key 244 is taken and door `$3c` crosses to room 22 with the urn carried. The other exit of rooms 27-29 is the **six-gem teleport**: variable 4's feeders are the gems 186, 187, 189, 190 (room 29), 164 (room 9) and 290 (room 20) (template low byte `$29` or `$42`); each gem in the pit region counts one, the sixth fires event 17 to room 49 in the south-east cluster (driven injected for five of six PLACEs; a gem thrown by the hero from outside the region was counted, 1 of 1). A hero who falls without 164 and 290 has no natural exit unless the chain is climbed.

**The south-east cluster and the FLAMEs** (driven natural unless marked). Room 17's entry block (event 6) **deletes the skeleton key 104** (2 runs); both the heal road and the cluster road pass through room 17, and 104 opens only door `$1c`. Room 16 to room 53 costs 4 at health 33: touching a FLAME is a jump (fire with nothing ahead, direction held; apex bottom z 35, ~520,000 steps) that passes within a cell of it: 211 (x 54..55, y 36..37, z 18..26, on tower 54) from x lead 54..61, 212 (x 28..29, y 37..38, on tower 56) from x lead 28..35; the second touch clears door `$12` (`393dffff` -> `393d0000`), which is the south-east corner of room 38 (`D` along x = 79, then `R` into room 48); room 38's two #444 creatures (-2 per contact frame) are the real cost (use the east lane first; `goto L` along y 13 went 33 -> 1). Room 48 is an empty corridor to door `$13` and room 52 (three spiders, -2 each), where `$14` leads to room 53; room 53's entry (event 6) closes `$14` behind the hero (`ffff`), and item 459 appears on slab 49 of platform 39 at ~4.5M steps after the arrival (a jump onto the slab from lane y 55..61 reaches it); icon 2 takes it and icon `$c` on 458 (west wall) reopens `$14` (XP +26). Room 53 reaches room 59 by `D`, `R`, `D` at zero cost; **room 59's altar 101 ("SHRINE OF GLUTTONS") answers an item that lands on it with an event 9 gated on the item's id**: 118 (the cured meat of chest 35, room 35) SHOWs potion 450 and pays 26 XP, 153 and the others are refused (driven for 118, injected; thrown from x lead 22..29, which lands on the slab, not on pillar 303). **Teleport 27 -> 49 bypasses the FLAMEs:** from room 49 the doors reach 48, 50, 51, 52, 55, 56, 57 without `$12`, and 56 is one `U` from the arrival. The 38-47 cluster: room 45's drain is two floor strips (x 3..23, y 33..40 and x 3..46, y 60..71, z 0..1, event 15 `45 ffff`, -1 per step; a jump over them is inferred); flask 135 and bowl 162 are non-obstacles, and flask 135 dropped beside the bowl runs event 4 (135 replaced by 136, the bowl's bit 0 set) so that icon 9 on the bowl teleports to room 47 (driven natural, health unchanged); room 47's lever 129 SHOWs 256 on press 1 (MAGIC SHIELD, on top of shelf 138, z 11..18), sends the hero to room 46 on press 2, shows scroll 27 on press 3 and 161 on press 5 (read).

**Chained scripts** (driven natural, promoted to `overlay/action/`, `py/secrets/README.md`): `route_room16_to_flask392.py` (room 16 to flask 392 at 33 -> 43 and back to room 16, 30 and 45 checkpoints, two runs identical), `route_room23_to_item455.py` (19 checkpoints, two runs), and `route_heal_chain.py` (treasury to the door `$2a` stall through water 214, flask 392 and the BUTTON chain: 71 checkpoints, two runs by the agent and one here, snapshots and logs identical; health 35 -> 37 -> 47). A hero that leaves the treasury this way reaches room 36 at health 47 carrying the crown and the oil 182 (the key is gone).

**Where the workstream stands.** Level 0's exit needs a MASSACRE cast, and §77 chains the whole road to it by natural input. The two links this section left open (the way out of room 27 and the reach onto altar 99's top) are solved there, and no other weapon reaches the dragon.

## 77. The whole level-0 road by natural input: treasury to room 60 (88th pass)

Five agents solved the two open links of §76 and two rounds joined every segment on one lineage; the parent then ran the chain from the treasury twice (`overlay/action/exit_level0/route_level0_exit.py`, 427 snapshots `cmp`-identical between the runs, each run about 4 minutes). Labels as in §75. **The whole chain is driven natural: joystick and keyboard only, nothing given, poked or injected.** It starts at `rwn2/taken53.snap` (room 37, crown 53 and key 104 carried, health 35) and ends in room 60 at (20,31,14,25), health 20, XP 980, level word 0, rucksack [53, 92, 182, 228, 482] (crown 53, oil 182, scroll 482; 92 and 228 are not named). The dragon dies to the MASSACRE cast (XP 402 -> 954), 486 opens door `$29`, the hero walks into room 60; the level change itself (object 84, verb 51) was driven from a sibling lineage (below).

**The segments and their health** (each starts from the previous segment's last snapshot; every leg not named costs 0):

| segment | from -> to | health |
|---|---|---|
| `route_heal_chain.py` (§76) | treasury -> door `$2a` stall in room 13, flask 392 drunk | 35 -> 47 |
| `d1/route_gems_to_room27.py` | room 13 -> rooms 12, 6, 2, 3, 9 (gem 164), 7, 13, 14, 19, 20 (gem 290, object 207 operated), 21, the hole -> room 27 | -2, -2 (room 7), -1 (room 9 maggot), -2 (room 7), fall -10: 47 -> 30 |
| `e1/route_room27_to_room22_natural.py` | room 27: key 184, chest 224 (urn 143), rat 194 (key 167), door `$31`, room 28, door `$37`, room 29's four gems, six throws, room 49, door `$0c`, room 48 -> room 22 | 30 -> 30 |
| `g1/route_room22_to_altar99.py` | room 22 -> 20, 19, 14, 13, 15 (2.3M wait), 16, 17, 38 (F1 crossing), 39, 40: urn 143 onto statue 156, flask 108 onto altar 45, 371 and 110 taken; 39, 38 (FLAMEs), 48, 52, 53 (459, 458, urn 453 smashed, 482), 51 (key 166), 56 (chest 157), urn 165, 49, 48, 38, 39: 165 thrown onto altar 99, the jump, 324 in front | -2 (room 52 spiders), -1 (creature 909), -2 (room 52 again), -5 (urn 165 take): 30 -> 20 |
| `g2/route_altar_to_room36_real.py` | READ MAGIC cast at 324, take 324, room 38 (F1), 17, 16, 15 (2.3M wait), 13, 14, door `$2a` stall, room 36: MASSACRE, 486, door `$29`, room 60 | 20 -> 20 |

The cast came about 100,000 steps after the room 36 arrival and before any fireball (fireballs cost -20 from about 100,000 steps), so the 20 health at the end of the road is enough; a poke to 19 and to 5 at the start of G2's segment (TEST ONLY) cost nothing on any leg of that segment.

**The way out of room 27 is the gem teleport, driven.** Variable 4 is the byte at `2286(A5)`. A gem (template low byte `$29` or `$42`) lying in pit region 1 after a throw adds 1 within 100,000 steps and is deleted; the sixth flips the room to 49 at (16,16,10,10) (+26 XP from room 49's event 28 about 300,000 steps later; the variable stays 6). The hero throws from outside the region: from the lane y 25..31 at x lead 69 (trail >= 63), Space, icon `$d` (select), then FIRE held 200,000 steps with nothing in front (handler `$a19e`); the gem rests at x 24..27, y 29..31, z 16..28. Room 49 is walkable: door `$0c` joins it to room 48 (and `$1b` to 56), so the south-east cluster is one door component behind the FLAME door. **Room 48's entry (event 6: `COND VAR 4 > 4`, TELEPORT room 22 at (6,1,0), VAR 4 = 0, block spent) lands the hero in room 22 at (44,12,38,6)** with the variable reset and nothing lost but the key 167 that door `$31` consumed. The six gems are the four of room 29 (taken by walking into each until the hero stalls in front of it, icon 2: 189, 186, 187, 190), 164 (room 9 at (17,11,15,9): facing it fires event 7, +26 XP and a maggot 912 whose contact is -1) and 290 (room 20 on platform 286, reached by one floor jump from (26,51,20,45) with RIGHT+FIRE; it lands past the gem and `L` stalls against it). Object 207 must be operated (icon 4 from (42,10,36,4)) before the fall: without it 203 covers room 21's hole and `U` stays at z 5. The fall costs 10 and drops nothing (the rucksack holds 32 and the chain never carries more than 12).

**Room 27 has a guard and a fireball.** Room 27's event-14 block creates a creature 127 at (10,10,0) (class 3, z 0..15) that fires a 3x3 fireball (class 128, z 10..13) south down x 14..16 at about 3 cells per 25,000 steps (-10 on contact). It appears after the hero has stood on the south strip (y 73..79), 175,000 to 1,050,000 steps later, was gone about 175,000 steps after its shot in one lineage and did not respawn in 3M idle steps. The stands in its column (the walk to x 14 and the chest stand, x trail <= 16) cost 10 if the fireball is in flight; E1's `WQ` token parks the hero at (25,65,19,59) until the guard has been seen and is gone. The 87th pass's "pit region drains while walking the south wall" was the hero's trail overlapping x <= 40 or this fireball; the throw lane never enters the region.

**The jump is +35, and it reaches both altar tops.** A RIGHT+FIRE or LEFT+FIRE hold from the ground lifts the hero at about 80,000 steps, to bottom z 22 by 192,000, to the apex bottom z 35 at about 320,000 and back to z 22 at 448,000: one jump lands on a top at z 22 (the altars' items rest at z 22..25) and the hero then walks on it. Altar 99 (x 7..33, y 33..48, z 18..21; platform 97 lies entirely inside it): from the throw position (49,40,43,34) one LEFT+FIRE jump lands at (29,40,23,34) (8 of 8 variants of the hold lengths), `goto Left` to x lead 21 puts 324 in front (probe `(324,[2,10,11,6])`), icon 2 takes it (a stop at x 17 pushes 324 three cells west, still takeable). Altar 45 (room 40) takes the same jump from x lead 21 with RIGHT+FIRE released at the first landing (holding fire past it starts a second jump). Walking off an altar top is free (z 22 -> 0 over about 330,000 steps), unlike room 21's hole. Landing and walking on the altars triggers nothing (altar 99's only block is event 7, a message).

**A drop fires no event 4; a throw does.** Space, icon 1 (`$a1e0`) places the item two cells ahead at z 0..7 as a plain object. The event-4 push (`$00f31a` to `$00f328`) lives in the mover-collision loop, so only a thrown mover reaches a target's event 4: urn 143 onto statue 156 (room 43) from (14,45,8,39) facing right (the urn flies at z 32..39, apex 61..68 at x 40..44, lands on the statue top z 11..18 after about 33 cells, flask 108 appears, XP +26; the hero cannot stand west of x lead 14 in room 43), flask 108 onto HIGH ALTAR 45 from (14,39,8,33) (lands at x 50..52, z 22..29; 110 and 371 appear on the altar top), urn 165 onto altar 99 from (49,40,43,34) after a 20,000-step LEFT tap (324 appears at (9..14,32..36) z 22..25, XP +26; from x lead 48 the urn lands half off and fires nothing). Room 43 lies east of room 40 (door `$0a`, room 40's east edge); room 40's south gap is the sealed door `$09`. Flask 108 and the other loose items are pushed ahead when walked into; to take one, stand where only it is in front.

**The scroll half.** Urn 453 stands on platform 37 (room 53, x 52..63, y 16..39, z 0..17) at z 18..33; a RIGHT+FIRE jump from (24,41) lands on it at (58,41,52,35), and pushing the urns (UP, then RIGHT at y lead 28) off the platform smashes them (event 11): 453 gives scroll 482 on the floor east of the platform (65..72, y 14..20), 452 gives gold 202. The 87th pass's read of a smash about 3.96M steps after the entry is not what the chain uses. A different urn, 198, wanders x 34..44, y 20..21 and falls at about 4.2M steps (one 5M-step watch run); that fall is the event 11 that SHOWs 459, which appears about 4.4M to 4.8M steps after the room 53 entry, so the chain waits 4.8M. The 482 is taken by approaching from the north (a probe at x lead 62..63 sees the platform, not the scroll). Key 166 lies at (10..12,28..30) in room 51 (a non-obstacle, stand at (19,31,13,25) facing left). Chest 157 in room 56: Return, select 482, icon `$10` clears the trap byte (5 -> 0), then icon 3 consumes 166 and shows 124, 165 and 398; urn 165's take is -5. READ MAGIC cast at 324 lying in front (Return, select 371, icon `$10`, the first icon) clears its body byte 3 from `$81` to `$00` (bit 0 clears too: unexamined) and consumes 371; 324 is then taken (icon 2) and selected (Return, icon `$d`, the pre-selection persists into room 36), and one fire hold with nothing in front kills the dragon (hits `$f02e`, `$4cde0`, `$fe24`, `$fdbc` once each; XP +552, 483 gone, 486 at (68,3,65,3)); the hero operates 486 (icon 4, door `$29` `2d17ffff` -> `2d170000`, needs the crown) and walks to room 60.

**The Return grid is unreliable with many items.** The cursor `2122(A5)` is a grid cell number, not a slot, and does not start at slot 0; with six or more items carried the grid shows four cells, the cursor sticks at cell 3 and the opened item is not the one it names (3 RIGHT pulses opened 371, 5 opened 110, 4, 8 and 12 opened 165). The scripts therefore search the RIGHT-pulse count on forks of the leg's own checkpoint and accept only an item word `1236(A5)` equal to the wanted id (`find_n` in `g1/` and `g2/`); the icon that follows is picked by its box layout (`drv.pick_icon_id` blindly walks past a short panel row: on a flask's `[9,11,13,1,6]` the blind path lands on the cancel box and DOWN from there selects the next rucksack item, which threw key 167 in a trial).

**Rooms 38 and 39 are phase lotteries, and F1 crosses 38.** The roaming creatures of rooms 38 and 39 (ids >= 900: 905 shuttles y 40..47 between x 22..29 and x 72..79, 906 walks the east and south walls, 907 loops x 6..53, y 13..31 in room 38 and patrols y 48..55 in room 39) move at the hero's own speed (about 25,000 steps per cell) and **their motion is a function of the steps the hero has spent inside the room**: leaving freezes them (left after 300,000, 1,000,000 steps in room 17, re-entered: they continued from the same cells). A fixed wait outside the room changes nothing, and a fixed wait inside it is a lottery (south arrival at a fixed start: a wait of 1.0M costs 0, 1.3M -22, 1.6M -12, 2.0M 0, 2.3M -14; E2's walk down room 38 cost 0 in its own lineage and 24 in the real one). `f1/route_cross38.py <start> <OUTDIR> <down|up>` reads the creature table every 5,000 steps for 4.5M steps on a fork, plans the smallest wait that keeps the hero's measured walk profile at least 3 cells from every rectangle with z bottom below 41, and executes it (waits in the real chain: down 1,045,000, up 140,000; over all start phases of one recording `down` solved 192 of 192 with a mean wait of 420,000, `up` 169 of 214, the other 45 being the phases where 906 walks west along the south wall toward the arrival). Room 39's north lane has no lookahead yet: G1's `W39` search found that a pre-wait of 1,125,000 steps is free in this lineage (0 -> -10, 250,000 to 500,000 -> -28, 1.0M -> -14).

**The level change** (driven natural from room 60 in a sibling lineage at health 23 and XP 777, `g2/level_change.py`): `L` to (11,31,5,25), `U` to (11,24,5,18), probe `(84,[7,11,6])`, icon 7 (verb 51); the level word reads `0101`, the screen waits at "PLACE LEVELS DISK", Space (`kbd 39`, 60,000 steps, `kbd b9`), and level 1 loads about 21,000,000 steps later at (42,46,36,40) with the **health carried over (23), the maximum 200, XP carried, the rucksack empty (type-8 count 1, record (680,93))**: the real chain would arrive with 20 of 200 (inferred from the carry-over, not driven).

**Open.** Level 1 (the first fight starts at 20 of 200 health; §75 holds its first leg and graph). Room 39's lookahead and the 45 unsolved `up` phases of room 38 (a different entry phase, or a sidestep, is untested). The room 52 spiders cost 2 each way (not dodged). Key 110 with object 391 (door `$09`, rooms 40-41), rooms 41, 44, 54, 58, potion 450's effect, and the extra bit READ MAGIC clears in 324 are unread or undriven. Why the guard of room 27 never fired in D2's lineage is not isolated. Whether a cast spends a charge of 482 is not measured.

## Files

| File | What |
|---|---|
| `mechanics.md` | this file |
| `py/full_room_name_census.py` | 73rd pass: combines the static per-room type-5 census with the live `$00ce78` back-pointer writes captured by driving `$00e854` (the real room-transition trigger) for all 72 room slots from one base snapshot, resolving every placed object's name index game-wide — proof for §67 (23/23 cross-room validation; the slot-27/GIANT RAT finding) |
| `py/parse_rooms.py` | 73rd pass: parses the 72-room `$00e854` REPL transcript (`scratchpad/ANCHORS.md`'s `cadaver/agents/room_census` corpus) into per-room `(rank, live_rec)` lists for `full_room_name_census.py` |
| `py/name_strings.py` | 71st pass: decodes the packed dialogue/item/spell/monster-name string table at `(A5)+168`/`172` through the `$5ac0` character map — proof for §65b (real monster names DEAD RAT/GIANT RAT/SKELETON, validated against LEVER/BOAT/PICKAXE's already-known live names) |
| `py/room_object_census.py` | 71st pass: walks all 72 populated rooms' own static object-id lists via the newly-found type-5 resource (indexed by room slot) — proof for §65a (2/2 cross-check against CAVERN's 22-object catalog and TUNNEL's known `[0,144]`) |
| `py/room_object_names.py` | 72nd pass: for the currently-loaded room, resolves every object's own live display-name index (template → room-array slot → live instance record → `+10`) and decodes it via `name_strings.py` — proof for §66 (3/3: LEVER/BOAT/PICKAXE, plus the goblet→SCONCE correction and the CAVERN/TUNNEL creature-name negative). Only resolves objects belonging to the room the given snapshot has loaded, not all 72 at once — superseded for the all-72-rooms case by `py/full_room_name_census.py` (§67) |
| `py/verb_opcode_map.py` | 70th pass: reads the embedded debug-string table's real addresses out of RAM, decodes the 59-entry verb-interpreter dispatch table, and for each entry does a bounded walk (straight-line body + one level of conditional-branch following) looking for a matching error string — proof for §64 (**superseded**: the table is the 94-entry one at `$00ffba`, secrets.md "The script language") |
| `py/disk_layout.py` | 51st pass: parses the one-disk Empire `.st` image's boot-sector BPB, checks the root directory for real FAT12 entries, and classifies every 512-byte sector as data vs. blank/erase filler — proof for §51. Its blank/data classifier only catches single-byte-repeat fills, not short-period repeating patterns (52nd pass found a 3-byte cycle on Disk 2's tail it missed) — not yet extended to handle that |
| `py/analyze_disk2.py` | 52nd pass: per-run entropy, byte-distribution (stddev/mean, max frequency, duplicate-sector rate), fixed-stride periodicity scan and ASCII-string scan over `disk_layout.py`'s data runs, plus cross-image byte-identity sampling — proof for §52's Disk-1-vs-Disk-2-vs-one-disk comparison (paths hardcoded to this Mac checkout, not parameterised) |
| `scratchpad/cadaver/disk2_gfx/try_widths.py` | 56th pass: renders `disk2_replicants.st`'s 5 candidate spans (and blocks A/B) as st-interleaved 4bpp at 7 widths and raw chunky8 at 2 widths using `gfxview.py`'s own palette/span detection — proof for §56c's negative result (ad hoc, scratchpad only, ~50 renders in `scratchpad/cadaver/disk2_gfx/renders/`, untracked) |
| `py/door_id_words.py` | 49th pass: for the 5 doors with a genuine positive id word, dumps the descriptor's own `+4..+7` bytes and resolves the id word as a type-6 object id, checking its `+15` lock flag — proof for §49 |
| `py/snapinfo.py` | 46th pass: one-line-per-snapshot room/display-buffer-parity/shifter-base report, reusing `tools/gfxview.py`'s header parsing — proof for §46 |
| `boat_hotspot.png` | 45th pass: live snapshot rendered at CAVERN's BOAT proximity hotspot, status bar/icon panel reading "BOAT"/"CAVERN" — proof for §45 that the §43 mechanism resolves a second object correctly, not just TUNNEL's LEVER |
| `py/world_map.py` | 44th pass: walks the type-3 resource-manager table and decodes every populated room's world-grid rectangle (§38a/§38d), reports the adjacency graph, renders `world_map.png`; 59th pass: resolves the type-3 index-table/data-area pointers fresh from each snapshot's own `(A5)+96` instead of hardcoding them, after the hardcoded addresses were found stale against the two-disk build (§59a) |
| `world_map.png` | 44th pass: rendered map of all 72 populated room rectangles, labelled by slot (TUNNEL/CAVERN named) — proof for §44 |
| `room2_lever_boundary_new.snap` | 41st pass: live snapshot rebuilt from `room2_tunnel_entry.snap` (13th pass's Left-hold recipe) after `room2_lever_boundary.snap` was found missing from this Mac's scratchpad — status bar "LEVER"/"TUNNEL", icon panel showing the lever's icon pair, matching the original 13th-pass screenshot; resume point for further proximity-icon-panel work; untracked like the other `.snap` resume points |
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
