# Captive: handoff

Updated 2026-11-12 by the session that started the workstream (ended at `fd04566`).

## Resume point

- Last commit of this workstream: `fd04566` captive: first pass (emulator fix `62219ec`).
- Working data: `M68000/scratchpad/captive/` (indexed in `scratchpad/ANCHORS.md`). Disk: `tmb097.st`, made from
  `The Medway Boys #97.zip` with `tools/msa2st.py`. Extracted files: `fed/` (`py/fedfs.py <disk> extract fed`).
- Start from: `mission1.snap` (planet screen, from `reversing/captive/drive.txt`). Later states, all from it with
  the clicks below: `ptr.snap` (pointer on LAND), `star.snap` (star 14 selected), `go_1.snap` (in orbit of star
  14, state 6), `mg_entry.snap` (stopped at federation's `jsr 32(A4)` into `fed_MapGen` on landing),
  `mg_ret.snap` (its return), `ld_1.snap` (on the planet surface).
- Uncommitted work left behind: none.

## Proven so far

- Emulator: FDC Step-in/Step-out with update now move the head (`MMU.fs` Type I decode). Net: verify, 30M
  snapshot, Cadaver game, watch and DMA compares identical; selftest 0 wrong 9 skip; `gates.py run all` 54/54.
- Drive to the mission 1 planet screen, byte-identical over two cold boots (`drive.txt`).
- Disk format: all 31 files pass every unit checksum and every packed file unpacks to its directory length
  (`py/fedfs.py`); depack independently confirmed by code-hunk alignment against RAM: `fed_MapView`
  10180/10180, `federation` 97619/97808, `fed_BootFile` 9261/9264 (`py/hunks.py`).
- `fed_MapGen` runs on landing: called once from `$b5c2`, returns after 841,721 steps; `callcap $1f7d0` from
  `mg_entry.snap` matches the natural return on all returned registers and on all 4096 bytes callcap printed.
  That call (D2 = 14) fills the output from `$1d9e8` with one value (`$1e` = 30): a planet surface, not a base.

## Running

Nothing running.

## Open, in priority order

1. Enter a base so `fed_MapGen` builds one: find a base on the surface (PLANET PROBE, or walk), and capture its
   entry state as with `mg_entry.snap`. Read the mode word `13564(A6)` and the request word `14788(A6)` at the
   call. Proof: a snapshot at the call with a base's mode, and the output region decoded as a grid.
2. Read `fed_MapGen`'s generator (code offset `$4000`-`$719c`, runtime base + 32 + offset; the module was at
   `$1f7b0` on landing) and the protection prologue at offset 0 (what it decrypts, whether the crack disarmed it).
3. A full callcap-versus-natural compare: callcap prints only 4096 `mem` lines of 8919 changed bytes. Use
   `stserver` (`tools/stclient.py`) to read the whole post-call RAM.
4. The output grid's layout (cell size, width; D0 = 48 and D1 = 30 on return) and the tile table it indexes.
5. Unit 1's 176-byte table (between the volume name and the directory): role unknown.

## Known traps

- The menu key must be released before Captive's boot code takes over (it overwrites `$118`): `drive.txt`
  releases it 30,000 steps after the make.
- `ATARI_TRACE_GEMDOS=1` crashes the emulator in this game (its Pexec detector peeks a junk A7 during TOS's
  bomb loop). Use `ATARI_TRACE_OS=1` and `ATARI_TRACE_FDC=1` instead.
- Flight: select a star by clicking it on the map first, then ORBIT. ORBIT with nothing selected prints
  "FLIGHT PATH SET" with destination `$ff00` and the ship never moves. Ship state is `14858(A6)` (6 = in orbit),
  destination `14848(A6)`, selection `14856(A6)`, A6 = `$1b5ce`.
- Pointer arithmetic: from `mission1.snap`, three `mouse move -127 -127` pin it at the top left; then
  `mouse move 125 0` and `mouse move 125 72` put it on LAND, ORBIT is 50 to the left, star 14 at (120, 103).

## Waiting on Dave

Nothing.

## Next session

`/resume captive`. Start from `go_1.snap` (in orbit) or `ld_1.snap` (landed), find and enter a base, and
capture `fed_MapGen`'s base-building call (open item 1). Then read the generator body (item 2).
