# Captive system scripts

These scripts back `../../system.md`: the game OS (`trap #9`), the volume block, the Copylock in `fed_MapGen` and the
Medway crack. Run them from `M68000/` with `uv run python -I reversing/captive/py/system/<x>.py ...`. Each one finds the
repo root by walking up to `tools/rdis.py` (or reads `M68000_ROOT`). Working data lives under
`scratchpad/captive/agents/protect/`; the snapshots come from `scratchpad/captive/` (`mg_entry.snap` is the
`jsr 32(A4)` into `fed_MapGen` at `$b5c2` on landing).

**stserver DLL.** This game's loader needs the FDC Step-in/Step-out fix in stserver's core DLL
(`server/bin/Debug/net8.0/M68000.dll`); a build without it fails every disk read. `trap9_log.py --boot` reads the disk,
`heap_proof.py` does not. When `cmp` shows `server/bin`'s DLL equal to `bin/`'s, the stock stserver works and
`STSERVER_DLL` can be left unset (`trap9_log.py --boot` ran that way). Otherwise point `STSERVER_DLL` at a copy of
`server/bin/Debug/net8.0/` holding the current `bin/` DLL, as at `scratchpad/captive/agents/protect/srv/stserver.dll`.

| script | proves | command | expected |
|---|---|---|---|
| `volblock.py` | volume block layout: data bytes 12-23 are six per-type geometry words, bytes 24-187 are the unit allocation map (one byte per unit, value = owning file's 1-based directory index) | `volblock.py scratchpad/captive/tmb097.st` | `31 of 31 files: map bytes == their unit span; free (0) units: 23; other values: [253, 254]`, type words all `0x4b0a`, hash `1ce20047` |
| `trap9_table.py` | the 33-slot `trap #9` dispatch table (word offsets from `$228`) | `trap9_table.py scratchpad/captive/mg_entry.snap` | fn 28 `$030e`, fn 96 `$045c`, fn 108 `$0f8c`, fn 112 `$0eac`, fn 124 `$0f1c` (full table in `system.md`) |
| `trap9_log.py` | each `trap #9` call's entry registers, string argument and returned D0 | `STSERVER_DLL=... trap9_log.py --boot scratchpad/captive/tmb097.st s:39999999,k:02,s:30000,k:82,s:170000000,k:39,s:60000,k:b9,s:90000000 out.tsv` | 48 calls (49 lines with the header; a re-run is byte-identical), first fn 104 at `$7516c` (step 40,064,261), fn 28 loads `fed1:fed_BootFile` to `$1216` and returns `$2454`, fn 124 returns `$f8300 $f7b00 $f7590 $f51e0` |
| `heap_proof.py` | fn 108/112/116: first-fit split, merge on free, flag 4 clears the block | `STSERVER_DLL=... heap_proof.py scratchpad/captive/mg_entry.snap 100 4` | alloc `$7c14e`, remainder `$78f82`, free merges back to `$79092`; marker kept with flags 0, cleared to `00000000` with flags 4 |
| `ramdiff.py` | the Copylock prologue's memory side effects (`mg_entry` against `mg_plain`, which stops at `$20040`) | `ramdiff.py scratchpad/captive/mg_entry.snap scratchpad/captive/agents/protect/mg_plain.snap` | 14 changed ranges. Inside the module image (`$1f7b0`-`$268f0`) only the entry register save `$20379`-`$203a9` and the vector save `$20440`-`$2045d` changed (written by the plain prologue at `$1f7d6` and `$1f800`), and `$1f280` did not change |
| `cold_watch.sh` | who writes the crack's bytes, from a cold boot through `drive.txt`'s inputs | `cold_watch.sh 140 48` / `cold_watch.sh 222 6` / `cold_watch.sh b514 12` | `pc=$010452` at step 40,055,110 / `pc=$075164` at 40,062,226 / depacker `$31b2` at 223,946,750 then `$14e`/`$158`/`$162` at 224,603,006 |
| `evt.py`, `evtdump.py`, `evtfind.py` | read an `ATARI_TRACE_EVENTS` file: page timeline, record dump, PC-range search | `evtfind.py <evt> 237d0 271d0` | on the full trace of the `fed_MapGen` call, the plain code at `$237d0`+ is first reached at record 631,746 |
| `util.py` | shared: repo root and snapshot RAM access (`gfxview.load_ram`) | - | - |

Making `mg_plain.snap`: `printf 'u 20040 900000\nsnap scratchpad/captive/agents/protect/mg_plain.snap\nq\n' | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/captive/mg_entry.snap repl` (`reached PC=$00020040 after 603675 step(s)`).

The decoded Copylock instruction stream is a bounded text trace. Make `pre_trace.snap` = `mg_entry.snap` + 141,336 steps
(PC `$1f892`). Then run `printf 's 490420\nq\n' | dotnet exec bin/Debug/net8.0/M68000.dll resume <pre_trace.snap> repl`
**without** `ATARI_NOTRACE`, piped through `grep -v '^\$0f8'`. It prints every instruction as decrypted at the moment it ran,
about 450,000 lines in all.
