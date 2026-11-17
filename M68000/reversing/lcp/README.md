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
request, and that two of the eight personalities are copies of two others. The control keys include one the crack's
list omits (Ctrl-B, a book at the door), petting resets happiness to its lowest level rather than raising it, and the
roughly hourly house event the clock raises is a phone call ("Control keys and house events").

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

The main loop `$16ee4` runs forever the frame wait `$26914` ("Needs and the clock") then `$16f50`. `$16f50` is the
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
see `$284ac`); whether enough drops leave him permanently deaf in a session is open.

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

## Needs and the clock

**Frames.** The main loop's `$26914` is the frame wait: called with N, it runs N+1 frames, each one waiting until
the frame counter `$51424` moves and then running the per-frame services (the clock tick `$24648`, the phone and
alarm sounds, the house-event queue `$27222`'s consumers, the player's keys). Only `$263a6` advances the counter
(`$268b4`, the one writer in a whole-image census and the only one a 30M-step watch saw), and only when 25 or more
ticks of the 200 Hz clock (low word of `_hz_200`, `$4bc`) have passed since the last frame and `_vbclock` (`$462`)
has moved by 2 or more. A frame is therefore at least 125 ms: the game runs at most 8 frames a second, whatever the
machine's speed.

**The clock.** `$24648` counts a game second on every frame whose counter is a multiple of 8 (`$4c592`, 0..59), so
a game second is 8 frames and the clock keeps real time while the frame rate holds at 8. Every 60 seconds it runs
the minute body below, then advances the minute `$55102`; at 60 minutes the hour `$4ca20`; at 24 hours it clears the
daily-appointment flags (`$17f0c`) and advances the zero-based day `$4ca22`, month `$3dcd0` and the year `$4097c`
(month lengths from `$2c7b8`; February has 29 days when the year is divisible by 4, `$24a04`). The guestbook routine
sets month, day, year, hour and minute from what the player types (`$17fec`, read in the decompile only), so the
house clock starts at the typed time. Measured on `house.snap` (`py/clock_rate.py 30 1000000`): 30M steps are 2500
VBLs and 10000 ticks of the 200 Hz clock, i.e. 50 emulated seconds; the frame counter rose 398 and the game counted
50 seconds. A game hour is about 1.8G emulator steps.

**The minute body**, in order:

1. Thirst: its countdown `$51468` drops by one; at 0 it restarts from the man's timer length `$51466` (45..75
   minutes, "A new person") and thirst `$51464` rises by one, up to 3. A need already at 3 that runs out again
   calls `$2489e`: illness `$5145a` is set to 1 with a 60-minute countdown `$5145c` rising (`$5145e = +1`),
   happiness `$5144e` rises by one (up to 2) with its direction `$51458` set to +1, and `$24900` sets palette entry 6
   to `$453` (ill) or `$754` (well).
2. Hunger: the same with `$5146e`, timer length `$5146c` (75..120) and hunger `$5146a`.
3. Illness, when above 0: its countdown drops; at 0 illness moves one step in its direction, any level 2 or more
   forces happiness to 2, and the countdown restarts at 60 minutes, or 5 when recovering (direction -1). Recovery
   is started by `$248d8` when hunger and thirst are both 0; its only callers sit in the routines that zero hunger
   (`$225c2`) and thirst (`$23444`), so it starts when eating or drinking leaves both needs met (from the call sites;
   not driven). Illness at 0 restores the well colour. A test of illness above 4 computes a value nothing reads.
4. Bladder: the countdown `$51474` drops; at 0 it is parked at 9999 and "needs to pee" `$51470` is set. Its five
   writers (`tools/find_field_writers.py house.snap '$51474'`) are this tick, the new person (`$17ec4`), the toilet
   routine `$2142c` (clears the need, parks the countdown at 9999, `$217b2`) and the eating routine `$225c2`, which
   alone restarts it from the man's length `$51472` (20..40 minutes, `$2298c`, beside its hunger = 0 write). So he
   needs the toilet a fixed time after eating; drinking plays no part (writer census, not driven).
5. House event: between 08:00 and 21:59, `rnd(0,100) < 2` (2 chances in 101 each minute, about once an hour), with
   `$2ae16` and the away flag `$51418` both clear, sets `$2ae12` (the per-frame ring sound in `$26914`) and queues house
   event `$1e`, a phone call (`$27222`: first free slot of the ten at `$2c948`, nothing if he is away or the last slot is taken).
6. Once an hour, unless he is ill with happiness at 2, the happiness countdown `$51456` drops; at 0 happiness takes a
   step in its direction and bounces between 0 and 2, and the countdown restarts from that level's duration
   (`$51450 + 2*level`, 6..24, 6..24 and 6..12 hours). So happiness is a slow triangle wave 0, 1, 2, 1, 0, ..., pushed
   up by starvation and held at 2 while he is ill. Petting (Ctrl-P) sets it to 0, so 0 is probably the happy end
   ("Control keys and house events"; the level's on-screen text is not read).

Proof: `py/gate_tick.py 1000 1` pokes 1000 states (every word above, the event queue and the TOS seed; biased so
that each counter is often one tick from rolling over, and 30% of seeds win the event roll), calls `$24648` and
compares every word it can change with `lcp_model.needs_tick`: **1000/1000**, every branch reached (79 events, 59
year ends, 14 leap Februaries, 203 starvations, 21 cures). Controls: no illness restart while ill 855, event roll
`rnd(1,100)` 924, happiness counting down while ill 750, no leap year 978, illness capped at 2 840. On a natural run,
`py/natural_tick.py` replays the model at each of the tick's own reads of the frame counter (a read watch at
`$2464e`), applies every other routine's writes as observed, and checks the tick's writes: over 2.2G steps (`natural_tick.py 2.2e9 1e8`, 12:08:10 to 13:08:58 game time)
**29123/29123** ticks, crossing the bladder running out at 12:36, thirst rising at 12:47 and the hour, with the
toilet (`$217ac`, `$217b2`), a drink (`$23538`, `$2353e`) and the recovery start (`$248ec`, `$248f4`) writing in between.

**The clock loses frames.** In that hour the frame counter was written 29233 times but the tick ran 29123 times:
110 frames (0.4%) never reach `$24648`. `$26914` takes the counter's value on entry, and its last frame's trailing
`$263a6` call can advance the counter just before it returns, so the next `$26914` waits for a further frame and
that one is never ticked (read from the body; a 30M-step window of the same run lost none). The game counted 3648
seconds in 3666.7 emulated seconds (2.2G steps at 12000 per VBL), so the house clock runs about 0.5% slow.

**Neglect cannot make him very ill.** Because each starvation resets illness to 1 rather than adding to it, and
thirst runs out again within 75 minutes, illness under neglect never passes 2. Running the gated model for a week
of minutes with both needs at 3, over every thirst and hunger timer pair (45..75 by 75..120): 690 pairs never pass
illness 1 (thirst timer 59 minutes or less), 736 peak at 2, and no man spends more than 21% of the week at illness 2. This
is arithmetic on the model, not a run of the game.

## Control keys and house events

The crack's `READ.ME` lists seven control keys. The code handles eight. Every frame, `$26914` reads a key with
`$17b5c` (GEMDOS) unless he is away or busy; Ctrl-A, B, C, D, F, P, R and W go straight to `$26fe0`, and any other key
opens the typing line. `$26fe0` jumps through the 23-entry table at `$2cc18`, one entry per Ctrl-letter. The entries
not listed below fall through to the typing line. Five keys queue a house event with `$27222`, and `$1721c` later runs
it:

| key | `READ.ME` | what `$26fe0` does | event and handler |
|---|---|---|---|
| Ctrl-A | set off alarm clock | sets `$3df6c`; the wait loop `$18656` runs `$1fb36`, which clears it | none |
| Ctrl-B | not listed | queues the event | `$20` `$224ac` |
| Ctrl-C | make phone ring | unless a call is under way (`$2ae16`): sets the ring flag `$2ae12`, queues the event | `$1e` `$21c30` |
| Ctrl-D | dog food at the door | queues the event | `$1f` `$21f62` |
| Ctrl-F | food at the door if needed | if the cans (bits 9..11 of `$5147e`) are below 4, queues the event; at 4, sets `$3e26e` instead | `$1d` `$222ea` |
| Ctrl-P | pet him in his chair | only while `$2c944` is set and no pet is running: happiness `$5144e` = 0, direction +1, countdown from `t0`, starts the pet animation (`$2c946`) | none |
| Ctrl-R | record at the door | unless the typing line is open: queues the event | `$1c` `$21f7c` |
| Ctrl-W | fill the water bottle | unless the bottle `$5141a` is already 10: calls `$1eff6($13)`, then `$23568(1)`, which fills it | none |

**Ctrl-B delivers a book.** `$224ac` has the same body as the record handler `$21f7c`: walk to the door, open it, take
the object, carry it away. The two differ only in which object flag they clear (`$2c9be` against `$2c9c0`), and the
record handler also counts records in `$4c9ee`. In the frames he carries a green object from the door, up to the
study, and puts it on the bookcase, which gains a green book on its top shelf (`py/book_frames.py`, frames `$LCP_WORK/keys/Bseq_*.png`, one run). The crack
list leaves it out; Kroah's pages have not been checked for it.

**The phone call is the hourly house event.** Event `$1e` is the one the clock tick raises (2 chances in 101 each
minute, "Needs and the clock" step 5), and the same event Ctrl-C queues. `$21c30` walks him to his chair (`$21a8c`,
which sets the seated flag `$2c944` once he gets there), answers, talks for a random number of rounds with random
gestures, then waits for any pet in progress to finish before he gets up. So "friends call" about once an hour of
daytime without the player.

**Petting resets happiness to 0.** Ctrl-P does not add a step of happiness. It restarts the triangle wave at level 0,
rising, with the level-0 duration `t0` (6..24 hours). Starvation pushes the level toward 2 (`$2489e`) and petting
sets it to 0. That makes 0 the happy end, inferred from what the two writers do; the level's on-screen text has not
been read. Pressing it outside a call is a no-op, because the seated flag `$2c944` is 0 (seen in the drive below). The
`READ.ME` says he must be in his easy chair. In the code, `$21a8c` sets the flag when he arrives at an object and
sits: the phone handler, the action dispatcher `$172a6` and two other routines call it.

**Event `$23` is a gesture nothing can trigger.** `$1721c` has a case for event `$23`, and `$172a6` has a case for
action `$23`. Both call `$2310a`, the gesture that rule 7 of the cascade calls by Kroah's name, "agree". Its body picks a pose for
`$2ae06` from the man's current one (`$2ae04 & 7`: 8, 9, 10, 14 or 15) and waits for him to reach it (`$268f8` steps
until `$2ae04` equals `$2ae06`). It then alternates four times between the pose `$2ae04 & 7` and `$2ae04 | $10`, and
returns him to where he was. That reads as a short repeated head or body movement; what the pose bits look like has
not been rendered. Neither case can be reached:
- **As an event.** A raw scan of the text segment finds six calls to `$27222`: the tick and the five keys above,
  pushing events `$1c`..`$20`. Only `$27222` and `$27270` refer to the queue `$2c948`, and no longword holding `$27222`
  exists for a pointer call.
- **As an action.** The action word `$2ae0c` has eleven absolute writers in the text segment. Eight are constants
  in `$16f50` (`$29`, `$15`, `$0d`, `$12`, `$19` twice, `$2b`, `$2c`), and `$172a6` clears it to `$ffff`. One is the secondary desire's
  draw from lists A, B and C, which hold no `$23`. One is the player-query head, filled by the parser `$28208` from
  the 33 rules at `$2d066`, none of which yields `$23`.

The gesture itself does run. Four call sites in the whole image call `$2310a` directly: the two dead cases, the
cascade before it obeys a request for action `$10` or `$1a` (`$171ac`), and `$1f76e` (`$1f940`), a routine not yet
named. So event and action `$23` look like a way to trigger the gesture on demand that was never
wired to a key or a word (inferred).

Drive: `py/ctrl_keys.py 150e6 -ABCDFPRW` forks `house.snap` once per key. Each fork holds Ctrl and the letter for
30,000 steps, then runs 150M steps with write watches on the queue and the keys' flags, and instruction-read watches
on each handler's entry. In the no-key control nothing is queued and no handler runs. B, C, D, F and R each queue
exactly their event (`$20`, `$1e`, `$1f`, `$1d`, `$1c`, written by `$27268`), and the handler starts within 10M steps (the drive polls in 5M-step chunks);
D's `$21f62` enters `$222ea` as its body says. A runs `$1fb36` within 25M steps, which clears `$3df6c` at `$1fb76`. W writes 10 to the
bottle at `$2365c`. P writes nothing (seated flag 0). `py/pet_key.py` makes the phone ring, stops when `$21ade` sets
`$2c944`, and forks there. With Ctrl-P, happiness goes 1 → 0, countdown 18 → 7 (`t0`), direction -1 → +1 (writes at
`$2708c`, `$2709a`, `$27092`), and the pet flag is set and later cleared at `$26be8`. In the no-key control from the
same fork, none of these words is written. One run per key, so these are single observations, not rates.

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
| `$4097c`, `$3dcd0`, `$4ca22` | words | year (86 = 1986), month and day of month, both zero-based | `$24648` and `$24a04` bodies; tick gate |
| `$4c592`, `$55102` | words | game second, minute (0..59) | `$24648` body; tick gate; natural run |
| `$4c5a4` | word | last action started | `$172a6` body; gate |
| `$4ca20` | word | current hour | `$1747e` body; gate |
| `$51424` | word | frame counter (one writer, `$268b4`) | `$263a6` body; census; watch |
| `$51418` | word | away (no house event is queued) | `$24648`, `$27222` bodies; tick gate (meaning Kroah's) |
| `$2ae12` | word | house event `$1e` ringing | `$24648` body; tick gate |
| `$51426` | 128 bytes | the `HYBER` record in RAM (offsets below) | equal to the file but for the player name |
| `$5144e`..`$51458` | words | happiness 0..2, its three durations, countdown, direction | `$24648` body; tick gate |
| `$5145a`, `$5145c`, `$5145e` | words | illness, its countdown, its direction | `$24648`, `$2489e` bodies; tick gate |
| `$51464`..`$51468`, `$5146a`..`$5146e` | 3 words each | thirst and hunger: level 0..3, timer length, countdown | `$24648` body; tick gate |
| `$51470`, `$51472`, `$51474` | words | needs to pee, bladder timer length, countdown | `$24648` body; writer census; tick gate |
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
| `$24648` | clock and needs tick (every 8th frame a second; the minute body) | body; gate 1000/1000 |
| `$2489e` | a need at 3 ran out again: illness 1, happiness up | body; tick gate |
| `$248d8` | start recovering if hunger and thirst are both 0 | body |
| `$24900` | set palette entry 6 by illness | body (XBIOS 6) |
| `$24a04` | days in the month | body; tick gate |
| `$263a6` | the frame: 125 ms and 2-VBL gate, then draw and count `$51424` | body; watch |
| `$26914` | frame wait: N+1 frames of per-frame services | body |
| `$17b5c` | read a key (GEMDOS; F1..F10 to `$f1`..`$fa`) | body |
| `$18656` | wait for a key, running alarm, toilet, drink and house events meanwhile | body |
| `$1fb36` | ring the alarm clock | called when `$3df6c` is set (call site; drive) |
| `$21a8c` | walk to an object and sit (sets `$2c944`) | body |
| `$21c30` | house event `$1e`: phone call | body; Ctrl-C drive |
| `$21f62` | house event `$1f`: dog food at the door (`$222ea` with `$409ec` set) | body; Ctrl-D drive |
| `$21f7c` | house event `$1c`: record at the door | body; Ctrl-R drive |
| `$222ea` | house event `$1d`: food at the door, cans filled to 4 | body; Ctrl-F drive |
| `$224ac` | house event `$20`: book at the door, shelved in the study | body and frames; Ctrl-B drive |
| `$2310a` | the "agree" gesture (Kroah's name): a pose, then four alternations of pose and pose `\| $10` | body; callers by raw scan; event and action `$23` unreachable |
| `$26fe0` | act on a key (Ctrl-letter table `$2cc18`, else the typing line) | body; drive |
| `$27222` | queue a house event (first free of ten; not when away or full) | body; tick gate |
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
| `py/lcp_model.py` | Python models of `$1876a`, `$1747e`, `$16f50`, `$17c46`, `$24648` and TOS `Random` |
| `py/gate_toplevel.py`, `py/gate_secondary.py`, `py/gate_newperson.py`, `py/gate_tick.py` | the four gates (counts above) |
| `py/clock_rate.py` | frames, VBLs, 200 Hz ticks and game seconds per chunk of a natural run, as CSV ("Needs and the clock") |
| `py/natural_tick.py` | the tick model replayed against a natural run's own writes ("Needs and the clock") |
| `py/ctrl_keys.py`, `py/pet_key.py`, `py/book_frames.py` | the control-key drives ("Control keys and house events"); frames in `$LCP_WORK/keys/` |
| `gates.toml` | the gates for `tools/gates.py` |

## Not exercised in the emulator

What the man does when ill or unhappy beyond the cascade's rules, the happiness level's on-screen text, what each
house-event handler writes beyond the flags listed in "Control keys and house events", the query parser and its vocabulary, the word puzzle and card games,
the letters, saving to `HYBER` (the leak drive wrote one disk sector, not decoded), a new person made through a real boot
without `HYBER`, and a session made deaf by drops alone.
