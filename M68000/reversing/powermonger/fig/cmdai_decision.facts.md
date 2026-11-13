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
| transfer `$668c`: D7 != 0, men != 0; `$04`, `D7 << 8`; all five natural hits (k25, k8, k106, k34, k50) executed; `py/arms/gate_nat_arms.py` 6/6 states, 28/28 changed bytes (the five plus k143's arm-4 decision) | decide item 5; "Transfer `$668c`: natural, all five hits examined, all executed" |
| group 0 / empty group falls to `$66c8` (at `$6684` / `$6686`) | The exact arm conditions |
| 75-land counts: `$65c8` 3507, `$65f4` 2286, `$6638` 31122, `$666c` 145, `$668c` 5, `$664c` 6913, `$66a4` 0, `$6884` 0 | Natural coverage |
| short census (29 snapshots x 150M): `$69b4` 95, escort 2, attack 77, `$6762` 179, `$66e8` 137 | Natural coverage |
| arm 4 split 140 k143, 5 k106 and k50 | "Arm 4 (`$666c`) is natural too" |
| refusal `$6884`: 5 call sites, 25 triples, 0 refuse | Refusal `$6884` cannot hold from any caller |
| gate_cmdai.py 323/323 natural, 280/280 synthetic | Proof of the commander AI |
| predicate_check.py 5724/5724 | The exact arm conditions |

## Flags

- The code makes `$664c` the head of arm 4 (`$69b4(8)`, then `$68fe(men + T)`); the transfer `$668c` sits after the
  fall-through at `$6680`. The figure labels `$664c` as arm 4's predicate.
- 65 deciding groups = the 24 first groups + 41 of the 394 non-lead groups; the figure says so.
- The short census counts `$69b4` calls (95) and the 75-land census counts `$65c8` issues (3507): different addresses, not
  comparable. The figure labels each.

## Lead and captions

| text added | source |
|---|---|
| game, publisher, year; "you give orders, not controls"; the AI uses the same order path | README.md title line, "Design digest" ("What carries the game") |
| one group per tick per side; `$6564` walks 5..0; skip no group / pending | strategy.md "The commander AI `$6522`" ("At most one order is issued per slot per tick") |
| fixed priority list; with the entity modes it is the whole autonomous AI | strategy.md "The AI as modern pseudocode" ("there is nothing else") |
| follow-up table chains food, men, equipment, invention orders | README "Design digest" ("Get men, food, follow-ups") |
| posture 2/3/4 = aggressive/neutral/passive | strategy.md `$51538` table (posture row) |
| order codes `$08` get men, `$0c` march and engage, `$06` get food, `$04` transfer, `$02` from the recheck | the figure's own arm boxes; strategy.md orders table |
| AI groups start with `$5fff` food; the food test never binds in any run; the AI writes posture 4 on attackers | README "Design digest" ("The opponent is simple"; "Combat") |
| census counts compared in the takeaway (31122, 3507, 2286) | the figure's own numbers (strategy.md "Natural coverage") |
