#!/usr/bin/env python3
"""Run the real Hatari emulator headlessly against this project's own TOS ROM and capture a
trace - ground truth for comparing against this project's own emulator, instead of guessing at
undocumented ROM/AES internals. See [[atari-st-emulator-next-instructions]]'s twenty-eighth pass
for how this was discovered and why it matters.

Windows note: tools/hconsole/hconsole.py's live control-socket mode does NOT work here - Hatari's
--control-socket/--cmd-fifo are compiled out on Windows (HAVE_UNIX_DOMAIN_SOCKETS), and hconsole.py
itself needs AF_UNIX. What DOES work, fully non-interactively with no window/console interaction
needed: --run-vbls (auto-exits after N VBLs) + --trace/--trace-file. That's what this script wraps.

Usage:
    python3 tools/hatari_trace.py --vbls 4000 --trace cpu_exception --out trace.txt
    python3 tools/hatari_trace.py --vbls 500 --trace cpu_disasm --out disasm.txt

Common --trace flags (comma-separated, see Hatari's doc/manual.html "Debug options" section for
the full list): cpu_exception (one line per real CPU exception/interrupt - cheap, safe for a full
boot), cpu_disasm (one line per instruction - very large fast, only use for a narrow, already-
bisected window), aes (AES call tracing), os_bios/os_gemdos (BIOS/GEMDOS call tracing).

To narrow cpu_disasm to a specific window without a live control connection, bisect first with
--trace cpu_exception (cheap) to find the approximate VBL count of interest, then re-run with
cpu_disasm and a --vbls just past that point - full-boot cpu_disasm is too large to be usable.
"""
import argparse
import pathlib
import subprocess
import sys

DEFAULT_HATARI_DIR = pathlib.Path(__file__).resolve().parents[2] / "hatari-v2.6.1-480"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--vbls", type=int, required=True, help="exit after this many VBLs (50 VBLs ~= 1s of ST time)")
    p.add_argument("--trace", default="cpu_exception", help="Hatari --trace flags, comma-separated (default: cpu_exception)")
    p.add_argument("--out", required=True, help="path to write the trace file to")
    p.add_argument("--hatari-dir", default=str(DEFAULT_HATARI_DIR), help="directory containing hatari.exe and tos.img")
    p.add_argument("--tos-file", default="tos.img", help="ROM filename within --hatari-dir, for comparing a different TOS revision without disturbing the default tos.img")
    p.add_argument("--memsize", default="1", help="ST RAM in MB (default: 1, matching this project's target machine)")
    p.add_argument("--machine", default="st", help="Hatari --machine value (default: st, i.e. plain STF)")
    p.add_argument("--timeout", type=int, default=180, help="subprocess timeout in seconds (default: 180)")
    p.add_argument("--disk-a", default=None, help="path to a floppy disk image (.st/.msa) to mount in drive A - omit for a diskless boot")
    args = p.parse_args()

    hatari_dir = pathlib.Path(args.hatari_dir)
    hatari_exe = hatari_dir / "hatari.exe"
    tos_img = hatari_dir / args.tos_file
    if not hatari_exe.exists():
        sys.exit(f"hatari.exe not found at {hatari_exe} - pass --hatari-dir")
    if not tos_img.exists():
        sys.exit(f"tos.img not found at {tos_img} - pass --hatari-dir")

    out_path = pathlib.Path(args.out).resolve()
    cmd = [
        str(hatari_exe),
        "--tos", str(tos_img),
        "--machine", args.machine,
        "--memsize", args.memsize,
        "--confirm-quit", "off",
        "--run-vbls", str(args.vbls),
        "--trace", args.trace,
        "--trace-file", str(out_path),
    ]
    if args.disk_a:
        cmd += ["--disk-a", str(pathlib.Path(args.disk_a).resolve())]
    result = subprocess.run(cmd, cwd=str(hatari_dir), capture_output=True, text=True, timeout=args.timeout)
    if result.returncode != 0:
        sys.exit(f"hatari.exe exited {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}")
    lines = out_path.read_text(errors="replace").count("\n") if out_path.exists() else 0
    print(f"wrote {lines} line(s) to {out_path}")


if __name__ == "__main__":
    main()
