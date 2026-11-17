# lcp: Little Computer People (Activision 1985; Atari ST version 1986)

Little Computer People ("House-on-a-Disk") is a toy, not a game: a cut-away house in which one small man lives his
day, eats, drinks, plays records, writes letters to the player and answers typed requests. The design team was David
Crane, Rich Gold and Sam Nelson; the ST conversion is 1986. The copy analysed is a scene crack on a compilation disk
(see "Provenance").

**What this doc set has established.** The program is compiled C (355 `LINK A6` frames, an Alcyon-style runtime), so a
Ghidra decompile exists. The man's behaviour is a fixed-priority cascade, not a needs-weighted (utility) scheduler:
each time he is idle, `$16f50` takes the first rule that fires, from house events down to a random draw from one of
three 16-action lists chosen by time of day and an 8-valued personality. Needs (hunger, thirst, the bladder) are gates
on that cascade, not scores. Three routines are proved against the emulator with callcap-style gates in `stserver`:
the top-level chooser (1000/1000), the time-of-day/personality chooser (2000/2000) and the new-person generator
(100/100), each with broken-model controls that fail. Kroah's 2006 reverse engineering of the same ST version
(see "Prior art") described this structure first; the gates here confirm it at the instruction level and add three
things it does not state: the no-immediate-repeat draw, a player-query queue that leaks a slot whenever it drops a
request, and that two of the eight personalities are copies of two others.

## Provenance

| item | value |
|---|---|
| source | `The Mockingbird #3.zip` (Dropbox `ST games`, not in the repo), sha256 `4e8f673a3eceb7cb7e72e53770d6b6585b1659f8462c31da3a06e211d369fd08` |
| disk | `TMBIRD03.MSA`, sha256 `902236f1...4cfa`; as `.ST` (`tools/msa2st.py`) 839,680 bytes, sha256 `d93de9c782d8834d8ae2cbf554c91e2f69d79c913d5cd0481df159c298d72dea` |
| run disk | `tmbird03_even.st`, sha256 `2b71bec3d5e0652d256a60dec3417c048974dabe3de5f9c5d3eb38efe7084963`: the same image with one patch to `LCP.PRG`, below |
| titles | `\AUTO\MENU.PRG` (The Mockingbird menu: "1-Afterburner (1 meg)", "2-Little Computer People"), `AFTRBURN.PRG` (After Burner), `\LCP\` (this program) |
| crack | `\LCP\READ.ME`: "Cracked by Pedro", dated 27/09/86, listing the control keys below |
| packer | `LCP.PRG` (53,177 bytes) and `MENU.PRG` are both packed with "AUTOMATION PACKER V5.0.1" (string in the stub); the depacked program replaces the stub at its own TEXT address |
| version | the in-program title page reads "(c)1985,1986 ACTIVISION INC."; no other version string found |

**Disk layout.** `\LCP\DATA\` holds the program's data files: `HOUSE.SCN` and `TITLE.SCN` (pictures), `BODY.LCP`,
`PE2.LCP`..`PE6.LCP` (five 11,092-byte files; Kroah's head types 2..6, see "A new person"; inferred, not loaded in a
gate), `SPRITES`, `OBJECTS`, `CARDS`, `SOUNDS.LCP`, eleven `*.SNG` and five `*.ORG` music files (header "Studio"),
`NAMES` (266 ten-byte name entries), `WORDS` and `WORDPZ.TXT` (the word puzzle), `LETTER.TXT` and `HYBER`.

**The crack ships someone else's man.** `HYBER` (128 bytes) is the saved state of a man who has already moved in, and
the game loads it instead of making a new person (`$16d36`): this copy's man is "Bart" (personality 2, wakes at 5,
sleeps at 23), and the player-name field held "CHAS RUST" until our guestbook entry overwrote it in RAM (bytes
`$5e..$62` of the record; the rest is byte-identical to the file, checked against `house.snap`). Every user of this
compilation gets the same Bart. Delete `HYBER` from a disk copy to get a new person (open item 3).

**The repack does not run on TOS 1.00 as shipped.** `LCP.PRG`'s header gives an odd DATA size (`$cc71`). TOS 1.00's
`Pexec` then clears memory from the odd end of DATA with `move.l #0,(A0)` (`$fc858c`) and takes an address error
(vector 3 at `$1e207`, the frame at `$3cc`); the machine bombs and reboots into the menu. The run disk changes the
size to `$cc72` and adds one zero byte at the end of the file (the directory entry grows to 53,178); the depacker
reads nothing past its data, and the game then loads and runs. `py/patch_odd.py <in.st> <out.st>` makes it: header long at file offset 6 = `$0000cc72`, byte at file offset
53,177 = 0 (the cluster slack was already 0), directory size = 53,178.
Mockingbird's packer is later than TOS 1.00-era cracks; presumably the repack was tested on a later TOS (inferred).

## Prior art

- **Kroah, "Little Computer People" pages** (`http://bringerp.free.fr/RE/LCP/`: `ai.php5`, `actions.php5`,
  `stats.php5`, `hyber.php5`, `queries.php5`; linked from Atarimania's ST entry). A reverse engineering of the ST
  version: the four-tier priority order (house events, primary desires, player queries, secondary desires), the
  time-of-day periods and the personality-to-list mapping, the three action lists, hunger/thirst/illness/happiness
  rules with their timer ranges, the 128-byte `HYBER` layout with every field's initial range, and the query
  vocabulary with priorities. It gives no addresses and no proofs. The site forbids reproduction, so this doc cites
  it and does not copy its tables; the action names used below are Kroah's (labelled), since this pass has not
  named actions from their handlers.
- **Jaruzel (Matt Owen), "Hacking Little Computer People on the Amiga"** (`jaruzel.com/blog/...`; read through a
  translation at `habr.com/en/articles/760284`, the original did not fetch). Black-box byte poking of the Amiga data
  files: on the Amiga the person (head type, dog colour, hair, name index into `Names`) derives from a serial-number
  file `SN`, and a ~200-byte "brain" file holds needs and flags. That is a different mechanism from the ST build here,
  which draws every trait from XBIOS `Random` at move-in ("A new person").
- C64-Wiki says the serial number made each disk's person; Wikipedia notes the cassette versions kept no memory.
  Neither has mechanism. No disassembly, source or GitHub project for any version was found.

## How it was run

The man and the house run with no emulator change. The drive (keyboard and mouse into the menu, the GEM desktop and
the guestbook) is `drive.txt`, fed to the REPL from a 40M-step cold boot; `house.snap` is its end state.

```
cd M68000
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll 40000000 --disk-a scratchpad/lcp/disk/tmbird03_even.st \
    snapshot scratchpad/lcp/replay/boot40m.snap
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/lcp/replay/boot40m.snap repl \
    < reversing/lcp/drive.txt          # ends with snap scratchpad/lcp/replay/house_replay.snap
```

What the drive does, in order:

1. Menu: key `2` (make `$03`, break `$83`). The menu does not launch LCP: it quits to the GEM desktop with an
   `A:\LCP\` window open (`DESKTOP.INF`'s `#Z` autostart line is ignored by TOS 1.00).
2. Desktop: the pointer is clamped to the top left with two `mouse move -127 -127`, then moved `+135,+95` onto the
   `LCP.PRG` icon. The first double click (50,000-step presses) does not launch it; the second, 100M steps later,
   does (`Pexec` of `LCP.PRG`, basepage `$1116e`). Not investigated: the first click probably only selects.
3. Guestbook ("HOUSE-ON-A-DISK GUESTBOOK", read through GEMDOS `Crawcin`/`Cconis` at `$11388`): name `DAVE`, Return;
   date `111786` (shown as 11/17/86), Return; time `1200`, Return; `P`, Return. Each key is a separate make and break
   200,000 steps apart. The data files are opened only after the AM/PM answer, and the house appears.

`house.snap`: the house with Bart, hour word `$4ca20 = 12`, 1,092,090,000 steps from power-on. The 40M-step boot
snapshot is byte-identical across runs, and replaying `drive.txt` in one REPL run ends byte-identical (`cmp`) to
`house.snap`, which was made in six resumed segments.

`ATARI_TRACE_GEMDOS=1` is costly here: the guestbook and the main loop poll `Cconis` constantly (about 950,000 calls in
300M steps; a 73 MB log). Leave it off past the launch.

## The program

| item | value |
|---|---|
| basepage | `$1116e` |
| TEXT | `$1126e`, `$196dc` bytes (depacked; the basepage is rewritten by the depacker) |
| DATA | `$2a94a`, `$2fe4` bytes |
| BSS | `$2d92e`, `$2dc3a` bytes (to `$5b568`) |
| runtime | crt0 at `$1126e`; trap wrappers `$11368` XBIOS, `$11378` BIOS, `$11388` GEMDOS (return address parked in `$2d938`) |
| decompile | `scratchpad/lcp/decomp/lcp.c` (Ghidra 12.1.4, `tools/ghidra/DecompileAll.java` over a RAM dump of `house.snap` from `$1126e` to `$5b568`; 389 functions) |

## The behaviour scheduler

The main loop `$16ee4` runs forever `$26914` (role unknown: name it from its body) then `$16f50`. `$16f50` is the
decision point: it runs every time the man is free and hands at most one action number to `$172a6`, which records
it in `$4c5a4` ("last action"), clears the pending word `$2ae0c` and dispatches on the number to the action's
routine (action names below are Kroah's).

**`$16f50`, the cascade.** The first rule that fires wins:

1. A house event is queued (`$2c948 != -1`): `$27270` dequeues it and `$1721c` runs it (record, food, phone, dog
   food, book: Kroah's control keys).
2. The alarm clock is ringing (`$3df6c`): action `$29` (turn it off).
3. He needs to pee (`$51470`): action `$15`.
4. Thirst > 0 (`$51464`): draw `rnd(1,100)`; when well, he goes to drink (`$0d`) if the draw exceeds 66 (34%),
   whether or not the water bottle `$5141a` is empty; when ill (`$5145a > 0`) the threshold is 0, so he always
   drinks, but only if the bottle is not empty.
5. Hunger > 0 (`$5146a`): a second draw with the same threshold; when well, he eats (`$12`) unless his last action
   was already eating, so he tries an empty cupboard only once in a row; when ill, he eats only if a can is left
   (bits 9..11 of `$5147e`). Thirst has no such guard: a well man can walk to an empty bottle repeatedly.
6. A daily appointment whose hour has come and that has not run today (flags `$2ae18..$2ae1e`, cleared by
   `$17f0c`): lunch at `$5142e` and dinner at `$51430` (both action `$19`), wake-up at `$5142c` (`$2b`), bedtime at
   `$5142a` (`$2c`).
7. The player-query queue (count `$3dce2`, ten priorities at `$3e272`, ten actions at `$40966`): the head's priority
   decides. Below 4 the head is dropped; 4 to 7 it is raised by one and the cascade continues to rule 8; 8 or more
   it runs (actions `$10` and `$1a`, playing with the player and the piano, first run `$2310a`, Kroah's "agree").
   So a request waits in the queue gaining one point per idle pass until it is old enough to obey.
8. The secondary desire `$1747e` (below); a result of -1 means nothing to do.

Proof: `py/gate_toplevel.py 1000 3` calls `$16f50` on 1000 poked states (half "quiet", with no need pending), stops
it before any action runs (at `$27270`, `$172a6`, `$2310a` or `$1747e`) and compares the branch, the action and the
whole queue with `lcp_model.toplevel`: **1000/1000**, every branch above seen (event 37, secondary 324, 21 distinct
actions started and both agree cases). Controls: a queue whose drop frees the slot 839/1000, an ill man ignoring the bottle 953/1000, a well
man allowed to eat twice running 983/1000, obeying at priority 7 947/1000.

**The query queue leaks.** Rule 7's drop shifts the queue down (`$1712c..$17176`) but never decrements the count; the
only decrement is in the obey branch (`$171fc`), and the only increment is the enqueue `$28490`, which refuses a new
request once the count is 10 (`$284ac`; census by `tools/find_field_writers.py house.snap '$3dce2'`: two writers,
four readers). Each dropped request therefore leaves a phantom entry behind; the gate's drop control (839/1000)
shows the count is not decremented. A natural drive confirms it: `queue_leak30.txt` (REPL from `house.snap`, with a
`watch` on the count) types "DANCE" and Return 30 times, 30M steps apart. The count was raised 23 times by `$284dc`,
lowered 13 times by `$171fc`, the drop branch `$1712c` ran twice, and the count ends at 10 = 23 - 13, not 8. The queue
then holds ten copies of action 8 with priorities 8, 4, 4, 4, 5, 3, 6, 3, 3, 6, so it stays full. The queue also fills
for an ordinary reason: he reaches `$16f50` only once or twice per 30M steps, slower than requests were typed. That 7
of the 30 requests were refused at the cap is inferred (the `hits` windows started after each Return, so they could not
see `$284ac`); whether enough drops leave him permanently deaf in a session is open item 1.

**`$1747e`, the secondary desire.** Hours awake = current hour `$4ca20` minus wake hour `$5142c` (mod 24). At 18
hours or more, or with illness 2 or more, the result is "go to bed" (`$04`), or -1 if he is already in bed
(`$51460`). Otherwise the period is (hours awake / 2) mod 3, so the day runs begin, middle, end, begin, ... in
two-hour slots, and the list is the word at `$2b49e + period*16 + personality*2` (0 = A, 1 = B, 2 = C). List A
becomes C on Sunday and B on Saturday (weekday from `$2459c`, 0 = Sunday). An action is drawn uniformly from the
chosen 16-word list (A `$2b43e`, B `$2b45e`, C `$2b47e`) and redrawn while it equals the last action `$4c5a4`.

Proof: `py/gate_secondary.py 2000 7` pokes hour, day of month, wake hour, personality, illness, in-bed and last
action, reads the weekday from the game's own `$2459c` on the same state, calls `$1747e` and predicts the exact
action, including every redraw, by replaying TOS's `Random`: **2000/2000**. Controls: no weekday swap 1910, no redraw
1960, period = hours mod 3 1390, bed at illness 1 1726, draws over 15 entries 1000, table axes transposed 1290.

**Personality is a permutation, and only six exist.** The period table `$2b49e` gives each of the 8 personalities an
order of the lists A, B, C over begin/middle/end. The orders are the six permutations of three, plus personality 6 =
personality 0 (A C B) and personality 7 = personality 5 (B A C): read from the table in RAM, which the 2000/2000 gate
uses. List A (Kroah's "working day" list) holds the computer (`$02`) three times; the phone (`$1e`) is in every list,
twice in B, and the three lists share several actions, so they overlap more than their labels suggest. Repeats are
weights: an action listed twice is drawn twice as often.

**The random generator** is TOS 1.00's XBIOS 17 `Random` (seed long at `$29b8`: seed = seed * 3141592621 + 1,
result (seed >> 8) & `$ffffff`), wrapped by `$1876a` as `rnd(lo,hi) = lo + (Random() & $7fff) mod (hi-lo+1)`.
Every gate here predicts exact draws from the seed it reads, which is the check on this formula.

## A new person

`$17c46` makes the man when there is no `HYBER`: twelve independent uniform draws plus a name, in this order: head
type `$51480` rnd(2,6), name index rnd(0,265) (the routine seeks to index*10 in `NAMES`, reads ten bytes and zeroes
every byte below `A`), favourite clothes rnd(0,15), pyjamas rnd(0,7), bedtime rnd(22,24) (24 becomes 0), wake-up =
bedtime + 6 mod 24, lunch rnd(11,13), dinner rnd(17,19), an unused word rnd(0,3), personality rnd(0,7), three
happiness durations rnd(6,24), rnd(6,24), rnd(6,12) hours, tidiness rnd(20,80), and the thirst, hunger and bladder
timer lengths rnd(45,75), rnd(75,120), rnd(20,40) minutes. It sets happiness 1, the water bottle and its saved copy
to 7, four cans of food (`$5147e = $800`). There is no serial number: the person depends only on the TOS seed at
move-in.

Proof: `py/gate_newperson.py 100 1` pokes 100 seeds, calls `$17c46` (which reads `NAMES` from the disk) and checks
every field, the wake hour and the name: **100/100**; drawing personality before the unused word scores 18, bedtime
over 22..23 scores 39.

## Memory map (runtime addresses)

| address | width | meaning | evidence |
|---|---|---|---|
| `$29b8` | long | TOS `Random` seed | callcap diff of `$1747e`; gates |
| `$2ae0c` | word | action chosen, consumed by `$172a6` | `$16f50`/`$172a6` bodies; gate |
| `$2ae18`..`$2ae1e` | 4 words | lunch, dinner, wake-up, bedtime done today | `$16f50` body; gate |
| `$2b43e`, `$2b45e`, `$2b47e` | 16 words each | action lists A, B, C | `$1747e` body; gate |
| `$2b49e` | 24 words | list per (period, personality) | `$1747e` body; gate |
| `$2c948` | word | house-event queue head, -1 when empty | `$16f50` body; gate |
| `$3dce2` | word | player-query count (0..10) | writer census; gate |
| `$3df6c` | word | alarm ringing | `$16f50` body; gate |
| `$3e272`, `$40966` | 10 words each | query priorities, query actions | `$16f50`, `$28490` bodies; gate; typed "DANCE" stored action 8, priority 6 |
| `$4097c`, `$3dcd0`, `$4ca22` | words | year (86), month (10, so zero-based), day of month | `$2459c` body; values in `house.snap` (inferred meaning for the first two) |
| `$4c5a4` | word | last action started | `$172a6` body; gate |
| `$4ca20` | word | current hour | `$1747e` body; gate |
| `$51426` | 128 bytes | the `HYBER` record in RAM (offsets below) | equal to the file but for the player name |
| `$5539a` | word | priority of the request being enqueued | `$28490` body (who computes it: open item 2) |

`HYBER` offsets (record at `$51426`) that this pass's gates read or write: `+$00` clothes, `+$02` pyjamas, `+$04`
bedtime, `+$06` wake-up, `+$08` lunch, `+$0a` dinner, `+$0c` unused, `+$0e` personality, `+$28` happiness,
`+$2a..+$2e` happiness durations, `+$34` illness, `+$3a` in bed, `+$3c` tidiness, `+$3e` thirst, `+$40` thirst timer
length, `+$44` hunger, `+$46` hunger timer length, `+$4a` needs to pee, `+$4c` bladder timer length, `+$58` flags and
can count, `+$5a` head type, `+$5e` player name, `+$76` the man's name. They agree with Kroah's layout.

## Routines named so far

| address | name | from |
|---|---|---|
| `$16d36` | load `HYBER` and unpack its flag word into globals | body (Fopen, Fread, the bit splits of `$5147e`) |
| `$16ee4` | main loop | body |
| `$16f50` | decide the next action (the cascade) | body; gate 1000/1000 |
| `$1721c` | run a house event | body (switch on `$1c`..`$23`) |
| `$172a6` | start an action | body |
| `$1747e` | secondary desire | body; gate 2000/2000 |
| `$17c46` | make a new person | body; gate 100/100 |
| `$17f0c` | clear the daily appointment flags | body |
| `$1876a` | `rnd(lo,hi)` over XBIOS `Random` | body; every gate |
| `$2459c` | weekday of the game date (0 = Sunday) | body; used as an input by the secondary gate |
| `$27270` | dequeue a house event | called before `$1721c` (inferred from the call site) |
| `$28490` | enqueue a parsed player request | body |

`lcp.sym` holds these for the decompiler.

## Files

| file | what |
|---|---|
| `README.md` | this document |
| `drive.txt` | REPL drive from the 40M-step boot snapshot to `house.snap` |
| `queue_leak30.txt` | REPL drive: 30 typed requests with a watch on the query count ("The query queue leaks") |
| `lcp.sym` | routine names for `DecompileAll.java` |
| `py/patch_odd.py` | makes the run disk from the converted `.ST` ("Provenance") |
| `py/lcp_model.py` | Python models of `$1876a`, `$1747e`, `$16f50`, `$17c46` and TOS `Random` |
| `py/gate_toplevel.py`, `py/gate_secondary.py`, `py/gate_newperson.py` | the three gates (counts above) |
| `gates.toml` | the gates for `tools/gates.py` |

## Not exercised in the emulator

The hunger, thirst, illness and happiness clocks (how the levels rise; Kroah's stats page gives the rules), the
house-event handlers and the control keys, the query parser and its vocabulary, the word puzzle and card games,
the letters, saving to `HYBER` (the leak drive wrote one disk sector, not decoded), a new person made through a real boot
without `HYBER`, and a session made deaf by drops alone.
