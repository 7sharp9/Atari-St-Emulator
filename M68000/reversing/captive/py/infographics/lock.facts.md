# lock.svg: facts and sources

Figure: `gen_lock.py` writes `lock.svg` to `scratchpad/captive/infographics/` (PNG:
`rsvg-convert -z 2 lock.svg -o lock.png`). Run from `M68000/` with
`uv run python -I reversing/captive/py/infographics/gen_lock.py [--emu]`; its printout is kept in
`scratchpad/captive/infographics/gen_lock.out`. Emulator results are cached in `data/lock_emu.json` (the census) and
`data/lock_runs/` (the curios scripts' re-runs and the re-rendered `die_faces.png`); `data/compound.json` holds the 40
compound generator calls. `--emu` re-runs all of it (about 20 s) and needs the curios helper scripts
(`HELPERS`, default `scratchpad/captive/agents/curios/`). Code read: `tools/disassemble.py --snap
scratchpad/captive/agents/ai/req4.snap --all e270 e358` and `--all 1207c 12168`. Docs: `reversing/captive/ai.md`
"Getting into a base", `mapgen.md` "After the flow field" ("Coded doors"); the curios agent's report, sections A, B, C, (2).
States: `agents/ai/req4.snap` (D0 = 1 base, three kind-2 coded doors), `base1/outside.snap` (mission 1 compound, door
(22,21) state `$0080`), `base1/in.snap`, `agents/curios/base30.snap`.

| fact in the figure | source |
|---|---|
| state word: bits 0-3 pressed corners (bit c), bits 4-8 code, bits 10-15 the 1st, 2nd, 3rd corner pressed; example `$6087` = code 8 after TL, BL, TR | `$e2e4`-`$e30e` (bset c in byte 1; c << 2n ORed into byte 0, n = lit count including this one); `$e320`-`$e324` code = (state >> 4) & `$1f`; `$6087` from the census |
| 4th press: high byte & `$fc` compared with each table byte & `$fc`; opens via `$c420` only at index = code; else clear to state & `$1f0`; the 4th corner is never stored | `$e312`-`$e348` (read); census below |
| corner c = 2 x bottom + right; click zones | `$e294`-`$e2dc` |
| table `$e358`: 24 bytes `1b 1e 27 ... e1 e4`, identical in req4 and outside.snap; bits 2-7 give 24 distinct first-three triples, so with the 4th = the corner left over every order of 4 corners occurs once | read from both snapshots; asserted |
| code 9 = `$6e`: bits 0-1 = BL, already its 2nd corner (the left-over corner is TL; `$6c` would be clean); the other 23 entries' bits 0-1 equal the left-over corner | computed from the table; asserted (`odd4 == [9]`) |
| lock census: all 256 four-press sequences x 24 codes = 6144 sequences, 24576 calls of `$e270`; state word = model on every press; opened 24 times, each code on its own order | **proven**: `gen_lock.py --emu` (stserver on outside.snap, labelled pokes: state word = code << 4, click x/y `15152/15154(A6)`, `68(A6)` = door cell; D2 = `$44`) |
| non-opening sequences clear at press 2: 1536, 3: 2304, 4: 2280 (sum 6120 = 6144 - 24); all 552 wrong orders of 4 distinct corners clear on press 4 with nothing cleared before; an early clear is a repeated corner | census, counted by the model replay that matched it press by press |
| rows in B: TL BL TR BR `$0081 $2085 $6087 $608f` opens; TL BL BR TR `$0081 $2085 $e08d $0080`; TR BL TL BR `$0482 $2486 $2487 $0080`; TL TL `$0081 $0080` | census; the 1st, 3rd and 4th rows also equal `die_hint.py` part B (re-run, 5/5 lines = model) |
| every in-zone press calls `$e370`, right or wrong | `$e2de` `bsr $e370` (read); "click sound" is **inferred** (report says `$111f2` D0 = 29) |
| die roll: LCG at `15218(A6)` (x`$5e5` + `$29`, ror 3, & `$f`, retried above 11), 12 faces `$20`-`$2b` | `$120aa`-`$120c6` (read) |
| faces drawn by `$12168`: `$20`-`$25` and `$26`-`$2b` = values 1-6 in two 90-degree orientations; odd values red, even black; hint faces `$30`-`$33` = a four with one red pip at TL, TR, BL, BR | `die_faces.py req4.snap` re-run into `data/lock_runs/die_faces.png`, crops embedded; red-pip quadrant of `$30+c` asserted for c = 0..3; red faces `$20 $22 $24 $26 $28 $2a` computed; values read by eye from the crops |
| hint: only facing a closed kind-2 door (tile & `$7f` in `$40`-`$5f`, tile & `$17` = 2) listed in `$1bee8`; face = `$30` + ((table[code] ror 2(n+1)) & 3), n = lit corners counted, not checked | `$120ca`-`$1213c` (read); census below |
| code 8 `$63` = 01 10 00 11: n = 0..3 gives TL, BL, TR, BR | computed with the model |
| die_all.py: 2400/2400 hints, 6400/6400 control on req4 (codes 12, 8, 1) | **proven**, re-run (`data/lock_runs/die_all_req4.txt`) |
| census: 24 codes x 15 lit sets (nibble 0..14, 264 of them not a prefix of the order) x 3 calls = 1080/1080 = model; control, tile left `$44` (kind 4), 24 codes: 72/72 random faces | **proven**: `gen_lock.py --emu` (outside.snap; labelled pokes: party (22,20) facing S, door tile `$42` or `$44`, state word; 120,000 steps before the calls; cell-ahead `15408(A6)` read back `$42` / `$44`) |
| compound door (tile `$44`, kind 4) facing it: 1200/1200 random; tile poked to `$42`: `$30`, `$32`, `$31`, `$33` 300/300 each for 0-3 lit | **proven**: `die_hint.py`, `DIE_TILE=42 die_hint.py` re-run |
| code 9: after BR BL TR the die shows `$32` (BL) 3/3; pressing BL clears to `$0090`; TL opens | **proven**: census rows `9:3212` (clears) and `9:3210` (opens), die census `9:14` |
| RATT text `407(A6)` = 1: "TOP-LEFT, BOTTOM-LEFT, TOP-RIGHT, BOTTOM-RIGHT." at `$13906`, same in in.snap, req4.snap, base30.snap; that order is code 8 only | **proven**: `ratt_msg.py` re-run (stops at `$bb4c`, A0 = `$13906` in all three); code match computed from the table |
| code 8 in 3 of 40 compound seeds ((0,0), (2,`$1234`), (3,`$1234`)); seed (0,0) = (22,21) `$0080` | `compound.json` re-parsed (doorcodes logic) and `doorcodes.py` re-run; seed (0,0) asserted equal to outside.snap's list |
| cost: blind worst 24 x 4 = 96 presses, mean 4 x 12.5 = 50; with the die 4 rolls + 4 presses = 8, or 7 with 3 rolls since the 4th corner is forced | computed; mean assumes a uniform code and a player who never repeats an order |
| a failed attempt always costs 4 presses (no carry-over) | the census: every 4-distinct wrong order ends at state = code << 4 |
| that the die runs on "use", and how the RATT note reaches the party | **inferred** (report A, B: `$fe60`-`$fe66`; the type-`$66` source not found) |

## Flags

- **New: table entry 9 is `$6e`, not a clean order byte.** Its bits 0-1 say BL, which is already code 9's 2nd corner
  (BR, BL, TR, then TL). The lock masks bits 0-1 and is unaffected (BR BL TR TL opens, census), but the die reads them
  for its 4th hint: on a code-9 door with three corners lit it shows BL, and pressing BL clears the lock. A player who
  trusts the die's last face on a code-9 door fails; the 3 earlier hints are right. Report (2)'s "4th at bits 0-1" and
  ai.md's "one byte per order of the four corners" hold for 23 of 24 entries. Whether this is a typo for `$6c` is
  inferred.
- Report A says `$26`-`$2b` are "the same in a second colour". The re-rendered crops show the same six values in a
  layout turned 90 degrees, with the same colours: odd values red, even black, in both sets.
- `die_all.py`'s counts are repeats: 2400 = 24 distinct conditions (3 doors x 2 sides x 0-3 lit) x 100 identical calls,
  and the 6400 control is 64 conditions that each replay the same 100-roll sequence, because `restore` resets the LCG
  (one distinct tally in its output). The hint does not use the RNG, so the repeats add no evidence; the census here
  (360 distinct conditions, every code) is the broader check.
- The die counts lit corners and does not check them: with a wrong corner lit it still shows the next corner of the
  true order (264 non-prefix sets in the census). Not in the report.
- Not run: the `$e270` branch on D2 bit 4 (`$e312`, `$e34e`: with it set, a 4th press does nothing and a repeated corner
  jumps to `$c420`; inferred to be the open-door case). The census always passed D2 = `$44`.
- Not run: `$120f0` `jsr $cac6` (D3 = -1) before the die's list lookup, and `$1210a`: a kind-2 tile not in the list
  gives face `$20` (a 1) instead of the roll (code reading).
- Not checked: how a click reaches `$e270` for a kind-2 base door. ai.md's click route says tile `$40`-`$5f` with "low
  bits 4"; every lock result here calls `$e270` directly with the cell poked into `68(A6)`.
- `compound.json` (the 40 generator calls behind "3 of 40") was not regenerated, only re-parsed; seed (0,0) agrees
  with `outside.snap`.
- `req4.snap` was written by a different DLL (stserver warning); every re-run matched the report's numbers.
