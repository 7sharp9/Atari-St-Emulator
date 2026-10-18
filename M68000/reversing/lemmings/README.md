# Lemmings (Psygnosis, 1990)

Focus of the first workstream: lemming behaviour (`sessions/lemmings.md`).

## Provenance

`Lemmings (1990)(Psygnosis)[cr BBC][a].st`, 839,680 bytes, sha256
`118f33d900ad089dde85104f3635dc0a483f02944d55502d218de695ccb1a45d`. Source:
`~/Library/CloudStorage/Dropbox/Daves/ST games/`. Not committed; working copy in
`scratchpad/lemmings/lemmings.st`.

## Disk layout

Extracted with `tools/extract_disk.py` into `scratchpad/lemmings/files/`. `\AUTO\LEMMINGS.PRG`
(56,056 B) is the loader. Data files: `CODE` and `MAIN` (`Ice!` packed), `LEVEL000`-`LEVEL024`,
`LEVELDAT`, `LEMMING1`-`3`, `TIM1`-`10`, `GROUND1`-`5`, `OBJECTS1`-`5`, `SPECIAL0`-`3`, `ODDTABLE`,
`INTROPAR`, `ENDSAMPL`, `*.IMG` logos.

## Boot

Boot sector (BBC crack) prints a message, TOS runs `\AUTO\LEMMINGS.PRG`. Nothing is read through
GEMDOS afterwards. Trace: `ATARI_NOTRACE=1 ATARI_TRACE_GEMDOS=1 ATARI_TRACE_OS=1 dotnet exec
bin/Debug/net8.0/M68000.dll 300000000 --disk-a scratchpad/lemmings/lemmings.st`.
