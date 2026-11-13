# Sourced by the t*.sh tests here. Sets M (the M68000/ dir, the cwd every test runs from), DLL (the
# build under test: first argument, default M68000/bin/Debug/net8.0/M68000.dll) and OUT (a fresh
# output dir under scratchpad/, one per test and build, so two builds can run side by side).
set -u
M=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
cd "$M"
DLL=${1:-bin/Debug/net8.0/M68000.dll}
case "$DLL" in /*) ;; *) DLL="$M/$DLL" ;; esac
tag=$(printf '%s' "$DLL" | shasum | cut -c1-8)
OUT="$M/scratchpad/repl_ergonomics/$(basename "$0" .sh)_$tag"
rm -rf "$OUT"; mkdir -p "$OUT"
echo "dll: $DLL ($(shasum -a 256 "$DLL" | cut -c1-12))  out: $OUT"
fails=0
check() { # check <description> <command...>: run the test command, print PASS/FAIL
    local d=$1; shift
    if "$@"; then echo "PASS  $d"; else echo "FAIL  $d"; fails=$((fails + 1)); fi
}
finish() {
    if [ "$fails" -eq 0 ]; then echo "RESULT PASS"; exit 0; else echo "RESULT FAIL ($fails)"; exit 1; fi
}
