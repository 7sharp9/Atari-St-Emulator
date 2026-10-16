"""posture_filter.py <count_file>: stdin = REPL stderr; keep WATCH lines whose address is a posture word (offset
134..147 of a $13c side record from $51538), pass other lines to stderr, write the total WATCH line count."""
import sys
n = 0
for line in sys.stdin:
    if line.startswith("WATCH:"):
        n += 1
        a = int(line.split()[4][1:], 16)
        if 134 <= (a - 0x51538) % 0x13c < 148:
            sys.stdout.write(line); sys.stdout.flush()
    else:
        sys.stderr.write(line)
open(sys.argv[1], "w").write(f"{n}\n")
