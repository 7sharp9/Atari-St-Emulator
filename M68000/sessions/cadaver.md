# Cadaver: handoff

Updated 2026-09-24 by the session that ended at this commit (39th pass). Landed a real lead on
Open item 1 (the room-paint writer) and two corrections to prior "proven" claims — see below.

## Resume point

- Last commit of this workstream before this pass: `679c28d` "cadaver handoff after the (A5)+0
  live-flip correction and inactive-half watch (38th pass)".
- Disk image: `Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (sha256 in
  `reversing/cadaver/README.md`) — untracked, do not `git add`. Present on this Mac checkout,
  no rebuild needed.
- Working data: `M68000/scratchpad/cadaver/` (untracked, gitignored). All snapshots from prior
  handoffs still present. New this session (all reproducible from `room2_tunnel_entry.snap` with
  the recipes below, kept for convenience):
  - `watch_wide_crossing.snap` / `watch_wide.log`: full 8.2M-step `kbd ff 02` crossing with
    `watch 19100 64256` (covers **both** display halves in one call, so the "inactive half flips"
    problem the 38th pass hit can't cause a miss). 5,635,133 write events, 237 distinct writer PCs.
  - `watch_cache.log`: same crossing, `watch 2de08 32000` (the `120(A5)` cache buffer instead).
  - `watch_28c00.log`: same crossing, `watch 28c00 6869` (a third region the full-RAM diff below
    turned up).
  - `watch_5a99.log`: same crossing, `watch 5a99 1` — the exact steps `$5a99` toggles.
  - `watch_shifter.log`: same crossing, `watch ffff8200 8` (the shifter's own video-base
    register) — **zero** writes logged.
  - `idle_no_crossing.snap`: `room2_tunnel_entry.snap` + 8.2M steps with **no** input (control for
    "is the content diff just animation noise").
  - `bba8_regs.log`: registers at each of the 4 `$0000bba8` hits during the crossing.
  - `full_10000_40000.asm`, `full_8000_10000.asm`, `full_40000_90000.asm`: whole-range linear
    disassembly dumps used to find `$144b8`'s only two callers; regenerable, not load-bearing.
  - Drive scripts for all of the above: `drive_wide_watch.txt`, `drive_watch_cache.txt`,
    `drive_watch_28c00.txt`, `drive_watch_5a99.txt`, `drive_watch_shifter.txt`,
    `drive_idle_control.txt`, `drive_bba8_regs.txt`, `drive_hits_bba8.txt`,
    `drive_hits_014f7a.txt`, `drive_hits_0150b4.txt`, `drive_hits_crossing_0150b4.txt`,
    `drive_0150b4_first_regs.txt`.
- Start from: `room2_tunnel_entry.snap` (fresh TUNNEL entry), same `kbd ff 02` crossing recipe.
  **Do not use `$5a99` to detect "crossing done" — see the correction below, it means something
  different and is misleading for that purpose.**
- Uncommitted work left behind: none (only this handoff is under version control).

## Proven so far

Detail in `reversing/cadaver/README.md`, `mechanics.md`, `graphics.md`, `ai.md`. Unchanged this
session's additions are new leads, not yet folded into `mechanics.md` — see "Corrections" and
"New lead" below before trusting anything that contradicts them. Carried over: `mechanics.md`
1-6, 27, 31a, 32a/b, 33b/34b, 34a, 35, 36.

## Corrections from this session (supersede parts of the 36th-38th pass writeup; not yet folded into mechanics.md)

1. **`$5a99` is not a "room reached" flag — it's `$0000bba8`'s own local scratch/re-entrancy flag,
   unrelated to which room is displayed.** Fully disassembled `$0000bba8`:
   ```
   $bba8: move.b #$1,$5a99.l      ; set flag
   $bbb0: move.l (A5),-(A7)       ; save real (A5)+0
   $bbb2: move.l A1,(A5)          ; (A5)+0 := A1  (temporary)
   $bbb4: move.l A0,120(A5)       ; 120(A5)  := A0  (temporary)
   $bbb8: jsr $144b8.l            ; run the normal flip/copy body with swapped roles
   $bbbe: move.l A1,120(A5)       ; 120(A5)  := A1  (restore-ish, see below)
   $bbc2: move.l (A7)+,(A5)       ; restore real (A5)+0
   $bbc4: clr.b $5a99.l           ; clear flag
   $bbca: rts
   ```
   `watch 5a99 1` over the full 8.2M-step crossing shows it flip 1→0 **four separate times**, each
   pair only ~1174 steps apart (`$00bba8` sets it, `$00bbc4` clears it moments later) — at absolute
   steps 58272716/58273890, 58313692/58314866, 58479334/58480508, 58701957/58703131. It is not
   sticky. A prior pass's "confirmed by `$5a99`: 0→1" as a crossing-complete detector was reading
   this scratch flag mid-flip by coincidence, not a room-identity signal. **Don't use `$5a99` to
   decide whether a crossing has completed; use the room-index/mode field method in Open item 1
   below instead (not yet identified either — see there).**
2. **`$0000bba8` is a generic "run `$0144b8` with its two buffer roles swapped" wrapper, confirmed
   crossing-specific, not a per-frame routine.** `hits` census: **0** hits over 4M/8.2M steps of
   ordinary `gameplay_empire.snap` play, vs **exactly 4** hits during one `kbd ff 02` crossing.
   Register capture at all 4 hits: `A1` is `$0002de08` (`120(A5)`'s fixed cache address) every
   time; `A0` alternates `$00020f00`, `$00020f00`, `$00020f00`, `$00019100` — i.e. it always banks
   *display half → cache*, matching the 37th pass's "backwards" finding, just via a clean, named,
   generic entry point instead of an ad hoc register-swap read at one call site. This **replaces**
   the 37th pass's framing (it wasn't an odd one-off swap, it's this wrapper's designed behaviour)
   but does not change the conclusion: this routine still only *banks already-correct pixels into
   the cache*, it does not originate new content.
3. **The shifter's live video-base register never changed during this session's crossing** —
   `watch ffff8200 8` (spanning the base hi/mid/lo bytes) logged **zero** writes over the full
   8.2M-step run, and `gfxview.py`'s `live screen: base` read `$00020f00` in all four fresh
   snapshots taken this session (`room2_tunnel_entry`, `watch_wide_crossing`, `idle_no_crossing`,
   and the pre-existing `gameplay_empire`). **This conflicts with the 38th pass's claim** that
   `watch_crossing_end.snap` showed shifter base `$19100` — that file (still on disk) does read
   `$19100` via the same `load_video_regs` helper, as does `mid_bank_copy.snap`, so the flip is
   real *in some runs*, just not in this specific `kbd ff 02`-only recipe. **Not reconciled**:
   either those two older snapshots came from a longer/different sequence that does eventually
   flip, or from a different crossing than the one this session drove. Check before trusting "the
   shifter base flips every crossing" as general — it did not flip in 4 independent runs this
   session (main crossing + idle control, both checked twice: once via a direct write-watch, once
   via before/after snapshot reads).

## New lead on Open item 1 (find the room-paint writer) — not yet proven byte-exact, needs one more pass

**Exhaustively ruled out**: a `watch` spanning *both* display halves at once (`watch 19100 64256`,
so the "which half is inactive" ambiguity from the 38th pass can't cause a miss) over the full
8.2M-step crossing logged every write into that whole span — 5.6M events, only 237 distinct PCs,
all attributable to the known `$0144b8` flip body (`$0144ee`-`$014a60`), the known panel/icon
writers (`$00be46`-`$00be9e`, `$00d0aa`-`$00d350`), and a periodic small-copy layer
(`$014f7a`-`$014fe0`, `$0150d2`/`$0150d8`). A second `watch 2de08 32000` over the cache found it
written **only** by the same `$0144xx`-`$0149xx` family (146 distinct PCs, all within that one
routine) — nothing else touches the cache at all. A full 1MB RAM diff between the pre- and
post-crossing snapshots confirms these really are the only two regions that changed by more than
~7KB, so the "we might be watching the wrong address" failure mode from the 38th pass is closed.

**Control confirms the diff is real, not animation churn**: stepping 8.2M steps from
`room2_tunnel_entry.snap` with *no* input at all (`idle_no_crossing.snap`) leaves both display
halves within 0-368/32000 bytes of their start value, while still ~18300/32000 bytes different
from `gameplay_empire.snap`'s steady CAVERN content — so the real crossing genuinely repaints
~57% of each 32000-byte half; it isn't just per-frame animation noise from taking two arbitrary
snapshots 166 frames apart.

**The `$014f7a`-family periodic layer is *not* crossing-specific** — `hits` census shows it firing
23,103 times over 8.2M steps of ordinary idle `gameplay_empire.snap` play (*more* than the 8,473
times it fired during the crossing itself). It's an ambient effect (water? a shared animated
layer?) unrelated to room transitions; ruled out as the room-paint source.

**The actual lead — "last writer per differing byte" and "first writer that changes a byte away
from its start value", computed directly from `watch_wide.log` against a raw before/after byte
diff of both halves (37,800 differing bytes total):**
- The *last* writer touching each of the 18,859 differing bytes in the always-shown `$20f00` half
  is overwhelmingly the ordinary `$0144xx`-`$0149xx` flip-copy body (dozens of PCs, ~140-150 bytes
  apiece) plus the known `$0080cc`/`$0080d2` blit (513+450 bytes, the single biggest single-PC
  share) — no unidentified PC appears. This says the *final* value largely arrives via routine
  copying, as expected.
- The *first* writer to move each of the 37,800 differing bytes away from its `room2_tunnel_entry`
  value is dominated by **`$0150b4`/`$0150ba`/`$0150d2`/`$0150d8`** — 3,167 + 2,869 + 2,810 + 2,739
  = **11,585 of 37,800 bytes (≈31%)**, more than 3× any other single family (the next-largest,
  `$014474`-family, accounts for ~1,762). This is the disassembled masked-blit primitive
  (`and.l (A1),D5` / `or.l D3,D5` / `move.l D5,(A1)+`, standard AND-mask/OR-data sprite blit,
  4 words per call = one masked 32×N blit) already named in `mechanics.md` §33b/34b as "the
  entity/sprite-list renderer... confirmed not the room-art source — it draws sprites at their own
  screen positions, not a room-sized background". **That conclusion was drawn from watching it
  during steady gameplay, where it does behave like ordinary entity rendering. This session found
  it behaves completely differently during a crossing:**
  - `hits` census: **0** calls over 8.2M steps of steady `gameplay_empire.snap` play (same as
    `$0080cc`, also 0 there) — so like `$0080cc`/`$bba8`, it's crossing-specific.
  - During the crossing it's called **4,066 times**, but only in a tight front-loaded burst: first
    hit at step 49,322, **last hit at step 1,058,685** — i.e. it runs entirely within the first
    ~13% of the 8.2M-step crossing, then goes completely silent for the remaining ~7.1M steps.
    4,066 calls in ~1M steps, each blitting a small masked tile via the same primitive used for
    entities, is far more consistent with **tile-by-tile background painting** than with drawing
    the handful of on-screen entities.
  - `$0080cc` (the other known "panel" blit) is also 0/8.2M steady-state but runs almost the whole
    crossing (39,412 calls, step 890,273 to 8,193,144) — starting right as `$0150b4`'s burst tails
    off. Candidate: the visible wipe/dissolve transition effect, running *after* the new room's
    tiles are already painted into the (still hidden) target buffer.
  - Register capture at `$0150b4`'s very first hit (step 49,322): `A0=$0002ca8c` (matches the
    already-documented "sprite-bitmap-cache region `$2ca84`-`$2cd42`" from §33b/34b — i.e. reading
    from the same small resident tile/sprite cache used for ordinary entities) and
    `A1=$0001b8b8` (inside the `$19100` display half) — caller return address `$0000d8ee`.
    **`bt 4` crashed the REPL here** (known trap, `depth>1`), so the deeper call chain above
    `$0000d8ee` wasn't captured; use `disassemble.py --linear 0xd8c0 80` from `room2_tunnel_entry`
    or a fresh `bt 1` per stop instead of a multi-frame backtrace next time.

**Confirmed this session** (closes the "not yet proven" gap above): `bpc 150b4 4066 2000000` from
`room2_tunnel_entry.snap` after `kbd ff 02` stops right as the burst ends; `s 200; snap` there
(`burst_end.snap`) and a raw byte diff against both `room2_tunnel_entry.snap` (TUNNEL) and
`gameplay_empire.snap` (steady CAVERN reference) gives, for **both** display halves:
- vs TUNNEL start: ~18,287-18,289/32,000 bytes different (the room really has been repainted);
- vs the CAVERN reference: only **636-656/32,000 bytes different (≈98% match)**.

That's at step ≈1,058,885 of the 8,200,000-step crossing — **under 13% of the way through** — so
the room is essentially fully painted (the tiny remaining diff is almost certainly player-sprite
position/animation state, not room content) long before `$0080cc`'s 39,412-call activity even
gets going. **`$0150b4` is confirmed as the room-tile painter; `$0080cc`'s subsequent activity is
some other, separate crossing-specific effect (visible wipe/reveal transition or similar), not
part of painting the room.** This is a real proof (match-count based, reproducible from
`room2_tunnel_entry.snap` with the recipe above) and should be written up in `mechanics.md` next
session, superseding §33b/34b's "confirmed not the room-art source" for this specific
crossing-time call path (that finding still stands for `$0150b4`'s *steady-gameplay* entity-blit
calls — the same routine, different calling context).

**Next session should:**
1. Read `$0000d8ee` (the caller of the whole `$0150b4` burst) in full — it's very likely the
   "decode this room's tile table and blit every tile" loop the earlier passes were looking for;
   its source table would also answer Open item 3 (room-record bytes `+0..+3`) and possibly
   Open item 4 (room connectivity) if it walks a room-to-room graph to know what to paint.
2. Fold this session's `$0150b4`/`$5a99`/`$bba8` findings into `mechanics.md` as a new numbered
   section (37th pass's §36 is the last one landed; this would be the next).
3. Reconcile the shifter-base-flip conflict (correction 3 above) before relying on either claim.

## Open, in priority order

1. Read `$0000d8ee` (caller of the confirmed `$0150b4` room-paint burst) and fold this session's
   findings into `mechanics.md` — see "New lead" above.
2. What `$55b6` contains for a *different* transition (e.g. an actual LEVER-proximity icon-panel
   change, §7) — still zero-checked, only the plain crossing has been tried.
3. Room-record bytes `+0..+3` (still unknown; `+4`/`+5` are the graphics-table index, `+$c0` is the
   mask table per §32a) — may fall out of item 1's `$0000d8ee` read.
4. How the ~72 real rooms connect in ordinary play (`$007104` is not it: both branches `bra $69da`,
   §31b) — may also fall out of item 1's `$0000d8ee` read.
5. The two-disk original (§30b): lower priority, would be a fresh subject.

## Known traps

(Unchanged from the prior handoff except the new entries at the end — see that file's git history
for the full carried-over list: `ScreenBufferA/B` role-swap framing is wrong, `movem` block-copy
chunk reversal, `watch`'s step= counter is a lifetime counter not local, one-shot breakpoint chase
non-reproducibility across separate invocations, re-disassemble elided `...` excerpts in full,
`bpc` over `bp` for one-shot dumps, `bt depth>1` can crash the REPL, a `watch` range can bracket
multiple regions in one call, `gfxview.py`'s `st-interleaved` assumes 16px-wide masked blits (not
this game's 32px-wide family), movement is joystick port 1, player = sprite slot 0, use
`tools/find_ram_callers.py`/`find_field_writers.py`.)

- **`$5a99` is not a room-transition signal — see correction 1 above.** It's a local scratch flag
  for one specific wrapper routine (`$0000bba8`) and toggles on and off within ~1200 steps every
  time that wrapper runs; treating it as sticky ("0→1 means the new room is up") is wrong.
- **`hits <n> <addr>...` is the fast way to check "is this routine crossing-specific or ambient"**
  before spending a `watch` run on it — run once from a steady-gameplay snapshot with no input and
  once across a crossing; 0-vs-nonzero is immediate and cheap (this session used it on `$bba8`,
  `$014f7a`, `$0150b4` and `$0080cc` in seconds each, vs the multi-minute `watch` runs).
- **A `gfxview.py load_video_regs`/"last differing byte's writer" analysis directly against a
  `watch` log's text is more decisive than reasoning about destination-address ranges alone** —
  computing, in Python, the *first* write (per byte) that moves a value away from its baseline
  snapshot cut straight through 237 candidate PCs to the one family responsible for ~31% of the
  real content change, where eyeballing PC/address clusters had stalled for two prior passes. See
  the inline script pattern in this session (load both snapshots with `gfxview.load_ram`, diff
  byte-for-byte, then regex-parse `watch_wide.log`'s `WATCH: step=... pc=$... Write... $addr <-
  $val` lines and track running per-byte state to find the first change per address).
- `gfxview.load_ram(path)` returns `(ram_bytes, base)` — **that order**, not `(base, ram)`; passing
  it around the other way silently means "base is bytes", raising a `TypeError` on the first
  arithmetic use, not a value bug.
- `dotnet exec ... resume <snap> repl`'s printed `help` text does not list `kbd`/`mouse`/`disk`
  even though they exist and work (confirmed working, `Program.fs` line ~1396) — don't conclude a
  REPL command is missing just because `help`'s one-line summary omits it; check `Program.fs` for
  the `parts.[0] = "<cmd>"` match arms.
- The REPL's `watch <addr> <len>` parses `<len>` as a plain **decimal** integer, not hex (`watch
  20e00 7d00` throws a `FormatException` on `7d00`; use `watch 20e00 32000`). Only `<addr>` is hex.

## Next session

Start by reading `$0000d8ee` (`disassemble.py --linear 0xd8c0 80` or similar from
`room2_tunnel_entry.snap`) — the caller driving the confirmed `$0150b4` room-paint burst — to find
the room-tile source table, which likely also answers Open items 3 (room-record bytes) and 4
(room connectivity). Then fold this session's `$0150b4`/`$bba8`/`$5a99` findings into
`mechanics.md` as a new numbered section. Prompt: `/resume cadaver`.
