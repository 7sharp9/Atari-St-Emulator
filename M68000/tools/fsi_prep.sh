#!/bin/sh
# fsi_prep.sh: copy the built emulator to scratchpad/fsi/dll for tools/fsi_drive.fsx, so fsi never holds bin/Debug/net8.0/M68000.dll
# (a held DLL fails another session's build at the copy step) and a run is pinned to one build. Re-run after every rebuild.
root=$(cd "$(dirname "$0")/.." && pwd)
src=${1:-$root/bin/Debug/net8.0}
mkdir -p "$root/scratchpad/fsi/dll" || exit 1
cp -R "$src"/. "$root/scratchpad/fsi/dll/" || exit 1
ls -l "$root/scratchpad/fsi/dll/M68000.dll"
