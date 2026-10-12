# Facts behind `fsm_jobs.svg` and `fsm_army.svg`

Generated: `py/fsm/mode_edges.py` (code read of `scratchpad/pm123/win/m1_ready.ram`, text `$1050..$1d000`) then
`py/fsm/build_fsm.py`. Edge data: `out/mode_edges.json` (raw writes per walk), `out/fsm_edges.json` (178 derived edges:
76 set, 42 walk (one of them the water veto `$36 -> $66`), 1 prev-only, 59 calls).

## Structure (code)

| fact | source |
|---|---|
| mode byte = record offset 31, previous mode = 30 | ai.md "The object record" table |
| dispatch `handler = $14bb4 + s16 word[$14bb4 + mode]`, modes `$00..$94` step 2 = 75 entries | ai.md "The behaviour modes"; `$14bac`/`$14bb0` in the iterator listing; read from RAM by `mode_edges.py` |
| `$94`'s table word gives `$15bdd`, an odd address: never a valid handler | `mode_edges.py` (`dead` entry); ai.md says every valid entry `$00..$94` resolves inside `$14c48..$1620e` (FLAG, below) |
| the walk: `$10` advances, `$12` is the leg, arrival `$14fdc` copies byte 30 into 31 (`move.b 30(A1),31(A1)`) | text.lst `$14fdc`; ai.md `$10`/`$12` rows |
| path terminators: `farm` (cursor `$50`) ends `$7d26` -> mode `$24`; `pots` (cursor `$76`) ends `$7d6c` -> mode `$6a`; `$7d00` (mode `$92`, `$14efe`) ends only `fp2`, never loaded | read from RAM by `build_fsm.py` `path_end`; ai.md walk-path row ("only farm and pots are ever loaded") |
| `$3c08` previous modes by flag: bit 7 `$7e`, bit 0 `$16`, bit 1 `$4e`, bit 2 `$5e`, bit 3 `$80`, bit 4 `$4c`, none `$7e`; then mode `$10` | text.lst `$3c08..$3cd0`; pm_fsm_ref `_FLAGBIT_MODE30` |
| `$3c74 move.b #$92,30(A1)` inside `$3c08` has no branch to it in the whole listing (unreached): no decode at any even address, no longword and no PC-relative word table names it. The four bytes at `$3c10` are `bgt.s $3c14 / nop`; a `bra.s $3c74` (`6060`) in place of the `nop` would make it the owner `<= 0` arm (an inferred patch). `$3c08` ran 3565 times, every one with owner > 0, in 4.1G steps over 41 snapshots; with `w 3c10 6e026060` a `callcap` of `$3c08` on a corpse writes prev `$92` | `grep 3c74 out/text.lst`: one line, the instruction itself; `py/fsm/mode_write_scan.py` |
| `$16892` D2 = `$8e` from `$4f7e`/`$4f82` (picker), `$90` from `$157ce`/`$157d2` (`$7c` regroup) | text.lst |
| `$5cde`/`$5fa0` stamp `31 := D2`, D2 in {`$40` build, `$3e` fell, `$6a` fallback} | text.lst `$5dd0`, `$5e7a`, `$5ede`, `$5ee4`, `$5f78`; ai.md `$5cde` block |
| `$3154` prev D4 per order: `$1a` (`$6bce`), `$1c` (`$6bfa`), `$22` (`$6c58`), `$6e` (`$6c7a`), `$78` (`$6d22`), `$76` (`$6d42`), `$7a` (`$6d66`) | text.lst, seven `jsr $3154` sites |
| other order executors: `$3888` prev `$1e`, `$38ce` `$72`, `$390e` `$74`, `$3248` `$6c`, `$4a7a` `$30`, `$6128` `$6e` | `mode_edges.json` routines; call sites `$6b9e..$6d08`; strategy.md orders table |
| `$600a` sets mode `$46` and prev `$40`/`$3e`/`$c` by gather kind (table `$6062`) | text.lst `$600a..$60ce`; economy.md 2a |
| `$4f68` dispatch table `$4fa2`: arms `$4fc2`(nop)->`$4fc4`, `$503c`, `$50b2`, `$50da` (`$36`/prev `$66`), `$5150` (`$34`), `$519a` (`$10`/prev `$3a`), `$51dc`, `$5240`; shared tail `$531c` (`$34`) / `$5334` (`$10` prev `$2e`) | `mode_edges.json` `tables`; ai.md `$2c` note |
| `$35f4`: each member `$10`/prev `$20` (`$36ec`, A0), the lead `$6868` (`$371a`) | text.lst; pm_fsm_ref `call_35f4` |
| `$34f2`: town's men `$10`/prev `$14` (`$3578`); `$1d70`: followers `$08`/`$08` (`$1e56`) | text.lst |
| `$56a6`: target `$32`/`$32` (`$5702`, A3); `$5590`: target prev `$3c` (`$561c`, A3); `$4bc8` via `$4dae`: other party `$2c`/`$2c` | text.lst |
| whole-image check: every mode-byte write in `$1050..$1d000` lies in a walked routine except `$2d04` (`init_dum`, `$92`), `$3c74` (unreached) and `$161f0` (the `$161c4` water veto, mode `$00`, common to every mode ending there; not drawn) | ad-hoc scan in this pass over `out/text.lst` |

Lanes: job bits of byte 7 (bit 0 farmer, 1 merchant, 2 fisher, 3 shepherd): ai.md object record row 7, `$3c08`.
Labels: ai.md mode tables, economy.md 2a, strategy.md orders table, `powermonger_orig.sym` (`pottery_` at `$156e0` = mode `$6a`).

## Evidence (node fill)

- Proven via `tools/pm_fsm_ref.py` blocks: `$02 $04/$06 $08 $0e $10 $12 $32 $68 $7c $8a` (ai.md Proven blocks).
- Proven via `py/fsm15/gate_fsm15.py` (18452/18452 over 1889 states): the 45 modes of the ai.md "`$15000` page" table.
- Proven via `gate_shepherd.py` (1043/1043): `$80..$88`. `$42` via `$600a` in `gate_orders.py` (economy.md 2a).
- Code read only: `$00 $0a $0c $8c $92 $22 $6c $6e $74 $76 $78 $7a` (ai.md "Not modelled" list, and no gate covers `$00/$0a/$0c/$8c/$92`).
- Routines proven: `$3c08 $16892 $5cde $600a $35f4 $34f2 $1d70 $4f68 $56a6 $5590(KILL) $4bc8` (pm_fsm_ref index); code read: the order executors, `$3956`, `$3da4`, `$5fa0`.
- Every edge is code read. A proven handler's gate also compares the mode byte it writes, except the arms it asserts off (`$10` -> `$15302`/`$1518a`, `$5590` ROUT, `$7c` -> `$5cde`/`$550e`).

## Could not pin down / flags

- **`$94`**: the table word resolves to `$15bdd` (odd). ai.md says every entry `$00..$94` resolves inside the handler block; nothing writes `$94`, so it is harmless, but the sentence is off by one entry. Contradiction flagged, not resolved.
- **Never set as a mode** (no write of byte 31 and no walk arrival that ends in it): `$04` (alias), `$64`, `$70` (fsm15 glue, synthetic only), `$94`. A whole-image scan of `$10a6..$1c48a` at every even address finds no immediate, register, table or walk-terminator write of `$04`, `$64` or `$70` to byte 30 or 31 (`py/fsm/mode_write_scan.py`).
- **`$66`** is entered only at a `$10` arrival (`$14fdc`) after prev `$66` (`$5106`, with mode `$36`) survives a water veto: a `$36` step onto water sets mode `$00` at `$161f0`, and `$00` goes to `$0a` (then `$10` at `$14e44` when word 28 is 0) or, with a Boat, to `$8c` (then `$10` on landing, `$14c66`). Live under a one-byte prev poke (`k108e_4`, 1 of 1); never seen unaided (0 over the pm148 long pool's 130G live steps and 11 sheep-click chases, `py/fsm/m66/`): a Boat-less follower goes `$0a` → `$08`, the vetoed lead walks to the order's cell, which an island sheep makes unreachable, and a group's camp (`$35f4`) rewrites the prev before a Boat man lands (ai.md, the `$36` row). Drawn as the dashed water-veto edge `$36 -> $66`, which `build_fsm.py` adds for every mode that stops at the `$161c4` epilogue with a pending prev (this one edge).
- **`$3c` (rout)**: only `$5590` stamps prev `$3c` on the target (`$561c`); the mode is entered at that man's next walk arrival (`$14fdc`). A routed group member does not enter `$3c` from that stamp: the rout tail's unlink `$1b8c` calls `$3c08` again and replaces the prev with his job home mode. That drops the mark (`$1534c`) that makes his attacker break off, so `$56a6` re-engages him (`$5708`, `$32`) and `$5590` routs him again as a man outside a group. Live, 100M steps each (`py/fsm/rout_fate.py`): `rand1` 23 of 44 stamps arrive as `$3c`, 3 arrive in another mode, 18 are re-routed; `k48` 54, 1 and 34 of 89; the 52 second stamps arrive as `$3c`, none dies or is left at the run end (ai.md, "`$5590`, outcomes").
- Mode/prev pairing is by nearest write address within a walk. It matches every pair checked by hand (`$16`, `$52`, `$54`, `$56`, `$86`, `$88`, `$3c08`, `$600a`, `$4f68` tail), but it is a heuristic.
- The call edges stop at depth 1 (a mode's direct callees and one intermediate). The `$16848 -> $5c2c -> $4bc8` owner-mismatch path, reachable from every job arrival, is not drawn.
