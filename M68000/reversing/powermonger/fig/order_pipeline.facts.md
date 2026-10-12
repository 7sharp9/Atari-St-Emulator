# order_pipeline.svg: facts and sources

| fact in the figure | section |
|---|---|
| player icon + target click into the local slot; natural clicks from `m1_s0` | strategy.md "The order senders and arrival executors, proven"; "The player's commands" |
| `$67ee` packs `x << 8 | y`; `$6822` refuses when `76()` = `$6888[type]` (group 0 with `$0c` excepted) | strategy.md "The commander AI `$6522`" (order writes); "`$6822`: issuing an order" |
| `$6822` own group into slot bytes 1/2; other group: header `base+1/+2`, slot `$22` param D7, `4(A1) := D7` | "`$6822`: issuing an order" |
| gate_cmdai.py leaves 160 states, 666 changed bytes, 38 issuing | "`$6822`: issuing an order" |
| `$22` → `$6d90` → `$3ce8` (code read); queued header copied into the slot by `$6522` | "`$6822`: issuing an order"; "The commander AI `$6522`" first bullet |
| k25 transfer: `$04` through the pending record and slot `$22`, pigeon lands 6,279,910 steps later | "Transfer `$664c`, `$668c`" |
| `$6a3a` slots 1..4, `$6a80` table, clears type/param; gate_exec.py 80/80 (2393 bytes), 288 natural (157 bytes, 9 pigeon launches) | "The executor, proven" |
| `$6ac6` routing on type `>= $22` and sender word 48; exec_census.py 44/44 | "The executor, proven"; ai.md "`$4562` how an order reaches a subordinate captain" |
| run now `$6b2e`; live order `$12` from `m1_s0`, `$4562` 0 hits | ai.md same section |
| `$6b20` dead direct branch: reads `$51b5a`, cell (0,0) only, 0 hits in 21 stretches, 5/5 poked | ai.md same section ("The dead direct branch", Evidence) |
| `$4562`: first free of 47, rider = lead, byte 16 `$78`, none free: lost; gate_pigeon_send.py 1567/1567, 125 states | ai.md same section; "The `$4562` gate" |
| flight `$3e06` `$416e..$4326`, re-steer to the rider | ai.md "The carrier-pigeon pool" |
| flight about 70M steps (side 3); 1 of 1 landing cleared the pending word | strategy.md "The pending word" |
| `$41dc` arrival, rider alive, packet to `$6b38` | ai.md "An arrival of another lord's pigeon" |
| `$4220 clr.w -72(A0)` | strategy.md "The pending word"; disassembly (it is inside the `$41dc` block) |
| rand1_s1 side 4: 150M steps, 0 writes, 12 pigeons | strategy.md "The pending word" |
| `$6b38`, types `>= $34` exit, `$6b5a + word`; handler 32/32; 12 dispatches over 6 handlers on k60_s2 | strategy.md order executor table note; "The executor, proven" |
| senders list; gate_orders.py 61143/61143 over 2273 states; wrapper_check.py 36/36 | "The order senders and arrival executors, proven"; "The executor, proven" |
| arrival executors `$3956` (`$74`), `$3da4` (`$7a`), `$5fa0` (`$22`) | "The order senders and arrival executors, proven" |
| `$0e`: handler 157k..181k steps after `$6822` (4 issues); arrival 295k..525k after `$6c48` (22 of 22); 26 of 30 reach `$5fa0` | "What an AI invention order does" |

## Flags

- strategy.md "The pending word" calls `$6b20` "the local immediate path"; ai.md calls the same branch dead (taken only
  for a sender at cell (0, 0), 0 hits in 21 stretches). In natural play the pending word is cleared only at `$4220`.
  Suggest strategy.md say "and by the direct branch `$6b20`, which is dead in play (ai.md)".
- strategy.md says the arrival is `$4220`, ai.md `$41dc`: not a contradiction. `$41dc` is the arrival block's entry,
  `$4220` its `clr.w -72(A0)` (disassembly).
- The `$22` box is now live (coordinator, from the captain2 agent, `py/captain2/drive_order.sh` on `pm142/rand1.snap`):
  clicking captain 1's figure posts `$22` param 2; `$6ac6`, `$6b2e`, `$6b38`, `$6d90`, `$3ce8` 1 hit each; `$3ce8` sets
  `$57fd2` and `$58042[side]` to `$18a`. The posture click then launches `$4562` (1 hit), the pigeon counter `$57fd8+2`
  goes 0 to 1, `$41dc` (at `$4206`) writes it back to 0 about 9.97M steps later, and `$35a0` sets group 1's posture 3 to 2.
  `$6d90` passes a local `$22` to `$3ce8` only while `$2df96` is set. The pigeon icon is drawn in the top status strip at
  (71 + 40j, -4), only 4 rows visible (not in the figure). The AI's header-copy step is live end to end once (k25).

## Revision 2 (merged strategy.md, "Stuck pending words are a game bug")

- The pending box now gives the mechanism: `$2776` frees the side's pigeons (`clr.b 6(A1)` at `$27c6`) and leaves the
  pending words set; `$4562` copies the dead sender's owner byte (`$45a8`); `$3e06` skips owner <= 0 (`$417a`).
- `py/arms/pending_census.py` over the 183 snapshots of live play (frozen post-game chunks skipped), 357 set words:
  70 flying, 142 dead sender, 141 no pigeon, 4 queued; the 4 with a live first group are explained in strategy.md "The
  pending word". The 159-snapshot counts (185 of 250, 41 of 394) moved to cmdai_decision.
