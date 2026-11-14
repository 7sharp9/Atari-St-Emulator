# Captain Blood: the alien rule language

How the UPCOM conversation decides what an alien says back. The interpreter is the reply engine `$e45a` and four
routines it calls; `py/rules/cbmodel.py` is an executable model of all of them, gated against `callcap`. Names come
from each routine's own body. Race data is `BLOOD.COM` ("The conversation data" in `README.md`).

## Evidence and caveats

- Gate: `cd M68000 && uv run python reversing/captainblood/py/rules/gate.py` (also `uv run python tools/gates.py run
  captainblood`). It starts from `scratchpad/captainblood/rules/snap/i1.snap` (Izwals, conversation screen), pokes
  each case's inputs, runs `callcap` of the real routine, runs the model on the same pre-state RAM (it never sees the
  emulator's output) and compares the whole memory delta and the exit registers. Result: `e45a: 600/600`, `e6a2: 300/300`,
  `e58a: 250/250`, `e628: 200/200`, `e22e: 200/200`, coin-threshold cases `e6a2coin: 100/100`, roll-threshold cases
  `e45aroll: 100/100`, `TOTAL 1750/1750`; the same on a second seed (`--seed 7`).
- Ignored writes, bounded: the user stack window, TOS's trap #14 register save area `$900..$93f` and the supervisor
  exception frame `$4d80..$4dc0` (XBIOS Random's side effects). The model's Random seed bytes at `$29b8` are compared.
- **The gate NOPs `bsr $de74` at `$e584` (a poke).** The no-reply path queues a redraw that waits for an interrupt
  `callcap` masks. The redraw, `$e284` (reply to icons) and `$e344` (sentence to tokens) are not modelled.
- Broken-model controls (one constant changed, `--break NAME`): `roll` (`$f000` to `$e000`), `coin` (`$8000` to
  `$7fff`), `clock` (divisor 100 to 60), `retry` (7 to 6), `req_mask`, `ign_mask`, `compose_mask` (mask byte
  swapped). Each fails the gate (1655, 1733, 1716, 1623, 1738, 1677, 1566 of 1750 on the default seed). The coin
  and roll thresholds fail only because the corpus has cases with the Random draw on and beside the threshold, which
  the gate solves seeds for.
- Not reached by the corpus: a condition that holds and is followed directly by an empty action (`$e4fe` then
  `$e56c`); the real data may not contain it (inferred).
- Only the Izwal conversation was driven. `i1.snap` descends from the labelled `$d5c0` poke that skips the canyon
  flight, so every conversation result stands on a poked route. In the click drives the sentences are poked into the
  sentence buffer (`$dc32` length, `$dc34` icons; icon = the `$60000` token-to-icon table); the mouth click, the
  engine and the reply are real. Croolis and Yukas rules are decoded from the data only (inferred).

## Tokens

A token is the vocabulary index (1-based; read from the data, tokens 1 to 3 are HEURE, FREQ, COORDONNEES). Tokens 1 to
3 carry a 2-byte big-endian operand (3 bytes in all); tokens 4 to 120 are one byte; digits are 111 (`0`) to 120. The
player's sentence is encoded by `$e344` into the token list `$e3f2`, 0 terminated.

## Records

A race's stream A is a list of records: header byte (type in the top 3 bits, payload length in the low 5), flag byte,
payload. `$ff` ends the list. Rows are gate-proven unless marked.

| type | name | payload | meaning |
|---|---|---|---|
| `$00` | plain rule | tokens | the pattern and the reply in one |
| `$40` | action | words | positive word sets state bit n, negative clears it. Empty payload sets bit 7 of `$e3f0`, which ends the conversation after the reply (consumer `$e1be`, `$e1dc` read, not run). Runs only after a held condition or a matched rule, never when the scan walks past it |
| `$80` | state condition | words | holds when every word's bit tests true (positive: set, negative: clear) |
| `$a0` | clock condition | clock word, then state words | clock word `<=` the clock in hours (`$cb32` / 100), then the state words |
| `$c0` | clock condition | clock word, then state words | clock word `>` the clock, then the state words |

Types `$20`, `$60`, `$e0` do not occur in the data; the engine would treat `$20` and `$60` as plain rules (read).

Conditions chain with AND, and consecutive condition records are evaluated together. A held chain makes the following
plain and action records live. A failed chain skips them up to the next condition record.

### Plain-rule flag byte

| bit | meaning |
|---|---|
| 0 | repeatable: with the used bit set and this bit clear the rule never matches again |
| 1 | always matches when reached |
| 2 | exact: the sentence must equal the payload token for token |
| 3 | coin: one Random draw, fails when the top 16 bits exceed `$8000` (each rescan re-flips) |
| 7 | used: set by compose and by an executed action |

With neither bit 1 nor bit 2 the rule is masked and order-free: every element whose required bit is set must be in the
player's sentence, and at least one element must be found. Extra words are ignored.

### Stream B masks

Three mask bytes per 8 payload elements (element `e` of the race's plain rules, in order, uses byte `3*(e/8)` plus 0, 1
or 2 and bit `7 - e mod 8`; every plain rule the scan passes consumes its element count):

| mask byte | meaning |
|---|---|
| 0 | required: not found means fail |
| 1 | omit from the reply (compose drops the token and its operand): the key word is not echoed |
| 2 | not looked for: the element is reply text only |

The reply is the matched rule's own payload minus the omit-marked elements, composed into `$e412`.

### Condition flag byte

(Mechanism gate-proven; the names are inferred.) A failed chain ORs its records' flag bytes. Bit 7 set: scanning
stops. Bit 6 set: the next condition record is evaluated only if its own flag has bit 5 set; otherwise it is skipped
too.

## Engine flow (`$e45a`)

1. Roll Random (`seed = seed * 3141592621 + 1`, result `seed >> 8`; seed long at `$29b8`). If the low 16 bits are
   `>= $f000` (1 in 16), set state bit 7 (byte `$61c10`, bit 7) and OR `$100` into `$7dd36`. `$da74` clears bit 7 at
   conversation start (read).
2. Run the leading `$40` records.
3. Walk the records. A plain rule goes to the matcher `$e6a2`. A match runs the following `$40` records, saves D4, D5,
   A4, A5 at `$e3c2`, composes the reply, and returns if it is non-empty (bit 0 of `$e3f0`: more to say).
4. List end: decrement the retry word `$e3ee` and rescan from the top while no reply was made (each rescan re-rolls);
   otherwise clear `$e412`, reload the counter to 7, clear `$dc34..$dc3b` and queue a redraw.
5. Mouth handler `$e1b4` (read): `$e3f0` negative leaves the conversation, non-zero resumes at `$e494` from the saved
   position, otherwise `$e344` then `$e45a`.

Variable block at `$e3d4`: +0 stream A pointer, +4 stream B pointer, +8 matched rule, +12 its stream B pointer, +16 its
length, +18 its element bit, +20 match flags, +21 condition-failed flag, +22 copy of the rule's flag, +24 reply count,
+26 retry counter, +28 status byte (`$e3f0`).

## Routines

| address | name |
|---|---|
| `$e43c` | read_header (D0 type, D5 length, Z at `$ff`); `$e432` skip_record |
| `$e44e` | next_bit (stream B position) |
| `$e6a2` | match; `$e7ae` advance past a rule; `$e7dc` coin |
| `$e58a` | condition |
| `$e628` | state action; `$e67c` run_actions (loop over `$40` records) |
| `$e22e` | compose |
| `$e45a` | reply engine |

## Say X, the alien answers Y (Izwals, 10/10 equal to the model)

`uv run python reversing/captainblood/py/rules/drive_pairs.py TELEPORTER ALLER AIMER PAIX ARGENT KOSM BONJOUR MORT
FEMELLE "MOI VOULOIR AIDER TOI"` pokes the sentence, clicks the mouth, saves the RAM at `$e45a`'s entry and compares
the real `$e412` with the model run on it. Rule numbers are lines of `tables/izwals_rules.txt` (regenerate:
`uv run python reversing/captainblood/py/rules/dump_rules.py 0`).

| player says | alien answers |
|---|---|
| TELEPORTER | MOI VOULOIR TOI TELEPORTER MOI (rule 86, sets state bit 6) |
| ALLER | NON MOI PAS ALLER (128) |
| AIMER | OUI OUI FEMELLE (126) |
| PAIX | PLANETE VOULOIR PAIX |
| ARGENT | MOI PAS PAUVRE (112, the key word is not echoed) |
| KOSM | KOSM ? |
| BONJOUR | BONJOUR GRAND GUERRIER |
| MORT | MOI PAS VOULOIR CONNAITRE MORT |
| FEMELLE | MOI CHERCHER FEMELLE |
| MOI VOULOIR AIDER TOI | the same four words |

The exact rules `BLOOD 2` (sets state bit 998) and `INFORMATION 1 2 8 0 0 0` (sets state bit 1) echo the sentence.
Not isolated one sentence per rule: the first matching rule in stream order wins, and the always-rules that
precede the topic rules answer any unmatched sentence in turn until used.

## Inferred (read from the decoded rules, not driven)

- Izwals rule 78 (`COND80 f=40 -40 +7`) turns the roll's state bit 7 into a hostile outburst followed by an empty
  action (end of conversation).
- State bit 1, set by the INFORMATION code, opens a block of always-rules that gives planet coordinates one part per
  mouth click.
- Rule 196 (`MORT[011]`, every other element ignored) has no key word and cannot match.
- The vocabulary flag bytes (`$40`, `$c0`, `$41`) and races 3, 4 and 6 in the emulator are not explored.
