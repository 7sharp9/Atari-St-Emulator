# Facts behind `fsm_jobs.svg` and `fsm_army.svg`

Generated: `py/mode_edges.py` (code read of `scratchpad/pm123/win/m1_ready.ram`, text `$1050..$1d000`) then
`py/build_fsm.py`. Edge data: `out/mode_edges.json` (raw writes per walk), `out/fsm_edges.json` (177 derived edges:
76 set, 41 walk, 1 prev-only, 59 calls). `py/dump_edges.py` prints the raw writes.

## Structure (code)

| fact | source |
|---|---|
| mode byte = record offset 31, previous mode = 30 | ai.md "The object record" table |
| dispatch `handler = $14bb4 + s16 word[$14bb4 + mode]`, modes `$00..$94` step 2 = 75 entries | ai.md "The behaviour modes"; `$14bac`/`$14bb0` in the iterator listing; read from RAM by `mode_edges.py` |
| `$94`'s table word gives `$15bdd`, an odd address: never a valid handler | `mode_edges.py` (`dead` entry); ai.md says every valid entry `$00..$94` resolves inside `$14c48..$1620e` (FLAG, below) |
| the walk: `$10` advances, `$12` is the leg, arrival `$14fdc` copies byte 30 into 31 (`move.b 30(A1),31(A1)`) | text.lst `$14fdc`; ai.md `$10`/`$12` rows |
| path terminators: `farm` (cursor `$50`) ends `$7d26` -> mode `$24`; `pots` (cursor `$76`) ends `$7d6c` -> mode `$6a`; `$7d00` (mode `$92`, `$14efe`) ends only `fp2`, never loaded | read from RAM by `build_fsm.py` `path_end`; ai.md walk-path row ("only farm and pots are ever loaded") |
| `$3c08` previous modes by flag: bit 7 `$7e`, bit 0 `$16`, bit 1 `$4e`, bit 2 `$5e`, bit 3 `$80`, bit 4 `$4c`, none `$7e`; then mode `$10` | text.lst `$3c08..$3cd0`; pm_fsm_ref `_FLAGBIT_MODE30` |
| `$3c74 move.b #$92,30(A1)` inside `$3c08` has no branch to it in the whole listing (unreached) | `grep 3c74 out/text.lst`: one line, the instruction itself |
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
- **Never set as a mode** (no write of byte 31 and no walk arrival that ends in it): `$04` (alias), `$64`, `$70` (fsm15 glue, synthetic only), `$94`. `$66` is written only as a previous mode (`$5106`, with mode `$36`); `$36` leaves by `$38` or `$68`, never through `$10`, so how a man reaches mode `$66` is open (fsm15: `$66` synthetic only).
- **`$3c` (rout)**: only `$5590` stamps prev `$3c` on the target; the mode is entered at that man's next walk arrival. Census shows 7956 natural `$3c` entries; the path is inferred from the code, not traced.
- Mode/prev pairing is by nearest write address within a walk. It matches every pair checked by hand (`$16`, `$52`, `$54`, `$56`, `$86`, `$88`, `$3c08`, `$600a`, `$4f68` tail), but it is a heuristic.
- The call edges stop at depth 1 (a mode's direct callees and one intermediate). The `$16848 -> $5c2c -> $4bc8` owner-mismatch path, reachable from every job arrival, is not drawn.
