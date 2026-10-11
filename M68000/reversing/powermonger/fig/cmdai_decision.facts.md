# cmdai_decision.svg: facts and sources

All from `reversing/powermonger/strategy.md` unless marked. Branch addresses were also checked against
`tools/disassemble.py --rom scratchpad/pm123/win/m1_map.ram --base 0 --all 6564 66e8` (code read).

| fact in the figure | section |
|---|---|
| `$6564` walks D7 = 10..0, A1 = base + D7 | The commander AI `$6522` |
| `28(A1) <= 0` skip (owner side, not men); `4(A1) != 0` skip (pending) | The commander AI `$6522` |
| pending set on 185 of 250 camped AI groups; 41 of 394 non-lead groups offered | The commander AI `$6522`, "The pending word" |
| state 9 decide; 6 camp wait `256()+$14 > $2df72` signed; other `$66e8` | The commander AI `$6522` |
| `$6762` returns 1: slot done; 179 issues (short census) | Natural coverage; The follow-up table |
| arm 1 `52() < $16` and `$69b4(8)`; posture 2; order `$08` | decide item 1; The exact arm conditions |
| escort: D7 != 0, group 0 state `$d`, `280 == 4`; posture 2; `$0c` to `292(A3)`; packed {y_hi,x_hi}; live 1 of 1 k25; k25 182 | decide item 2 |
| attack `$661a`/`$6638`: men-4 > 0, `$68fe(men-4)`, `$68ee` score <= `112()`; posture 4; `$0c` | decide item 3 |
| `$68ee` score formula `(d/2)((men-4)/8+1) + d/2` | decide item 3; The lord scans |
| food fallback `$66a4`: `$69b4(6)`, `$06`, no posture write; 15/15 poked; natural 0; seed `$5fff` | Food fallback `$66a4` |
| arm 4 `$666c` via head `$664c`: `$69b4(8)` then `$68fe(men + T)`; posture 2; `$08` | decide item 4; The exact arm conditions |
| transfer `$668c`: D7 != 0, men != 0; `$04`, `D7 << 8`; k25, k8, k106 executed; k34, k50 not examined | decide item 5; Transfer `$664c`, `$668c` |
| group 0 / empty group falls to `$66c8` (at `$6684` / `$6686`) | The exact arm conditions |
| 75-land counts: `$65c8` 3507, `$65f4` 2286, `$6638` 31122, `$666c` 145, `$668c` 5, `$664c` 6913, `$66a4` 0, `$6884` 0 | Natural coverage |
| short census (29 snapshots x 150M): `$69b4` 95, escort 2, attack 77, `$6762` 179, `$66e8` 137 | Natural coverage |
| arm 4 split 140 k143, 5 k106 and k50 | Transfer ..., "Arm 4 (`$666c`) is natural too" |
| refusal `$6884`: 5 call sites, 25 triples, 0 refuse | Refusal `$6884` cannot hold from any caller |
| gate_cmdai.py 323/323 natural, 280/280 synthetic | Proof of the commander AI |
| predicate_check.py 5724/5724 | The exact arm conditions |

## Flags

- "Natural coverage" calls `$664c` "the transfer head"; "The exact arm conditions" puts arm 4 `$666c` "in `$664c`'s head".
  The code makes `$664c` the head of arm 4 (`$69b4(8)`, then `$68fe(men + T)`); the transfer `$668c` sits after the
  fall-through at `$6680`. The figure labels `$664c` as arm 4's predicate.
- (Resolved by the merged strategy.md) 65 deciding = the 24 first groups + 41 of the 394 non-lead groups; the figure
  now says so.
- The short census counts `$69b4` calls (95) and the 75-land census counts `$65c8` issues (3507): different addresses, not
  comparable. The figure labels each.

## Revision

- Arm 2 now reads "group 0 is fighting another group (state `$d`, opponent class `280(group 0) == 4`)", and the escort
  goes to group 0's opponent (`292`). Source: the coordinator, from the sim_unread agent (`280` = opponent class, 4 = a
  group; `292` = the opponent's record, written by `$4d6c`); see group_soa.facts.md.
- Transfer: all five natural `$668c` hits examined and executed (k25, k8, k106, k34, k50);
  `py/arms/gate_nat_arms.py` 6/6 states, 28/28 changed bytes (the five plus k143's arm-4 decision). Section:
  "Transfer `$668c`: natural, all five hits examined, all executed".
