#!/bin/bash
# Checks for tools/docguard.py: a pure rewording is CLEAN, each kind of fact change is caught.
# Run from anywhere: bash tools/tests/docguard_check.sh. Prints raw output and PASS/FAIL per case.
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
tmp=$(mktemp -d)
g() { uv run --project "$here" python "$here/tools/docguard.py" --pair "$@"; }
base='The scorer `$2337a` matched 65,455 of 65,455 cells at $1d22c, worst error 11.8% over 3 runs (D0 = 5).'
printf '%s\n%s\n' "$base" 'A second line with 42 and pm88_f1.' > "$tmp/a.md"
fails=0
case_() {  # name, expected exit, after-text
  printf '%s\n' "$3" > "$tmp/b.md"
  out=$(g "$tmp/a.md" "$tmp/b.md"); rc=$?
  echo "--- $1 (expect rc $2)"; echo "$out"
  if [ "$rc" = "$2" ]; then echo "PASS $1"; else echo "FAIL $1 (rc $rc)"; fails=$((fails+1)); fi
}
case_ reworded-and-moved 0 "$(printf '%s\n%s' 'Here is 42, beside pm88_f1.' 'Over 3 runs the scoring routine (`$2337a`) at $1d22c reproduced 65455/65455 cells; its worst error was 11.8% (D0 = 5).')"
case_ digit-changed 1 "$(printf '%s\n%s' "${base/11.8%/11.9%}" 'A second line with 42 and pm88_f1.')"
case_ ratio-changed 1 "$(printf '%s\n%s' "${base/65,455 of 65,455/65,454 of 65,455}" 'A second line with 42 and pm88_f1.')"
case_ address-dropped 1 "$(printf '%s\n%s' "${base/ at \$1d22c/}" 'A second line with 42 and pm88_f1.')"
case_ backticks-dropped 1 "$(printf '%s\n%s' "${base/\`\$2337a\`/\$2337a}" 'A second line with 42 and pm88_f1.')"
case_ number-removed 1 "$(printf '%s\n%s' "$base" 'A second line with pm88_f1.')"
printf '<p>matched <b>65,455</b> of 65,455 &amp; $1d22c</p>\n' > "$tmp/a.html"
printf '<div>65455/65455 matched, at $1d22c</div>\n' > "$tmp/b.html"
out=$(g "$tmp/a.html" "$tmp/b.html"); rc=$?
echo "--- html-tags-ignored (expect rc 0)"; echo "$out"
if [ "$rc" = 0 ]; then echo "PASS html-tags-ignored"; else echo "FAIL html-tags-ignored (rc $rc)"; fails=$((fails+1)); fi
rm -r "$tmp"
echo "failures: $fails"
exit $fails
