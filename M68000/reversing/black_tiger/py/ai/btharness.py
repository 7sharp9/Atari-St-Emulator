"""Minimal callcap differential harness for Black Tiger (one REPL per batch).

States are {name, pokes {addr: byte}, presets {reg: int}, target}.  Pokes are applied through the
REPL `w` command (4-byte longwords, merged per aligned longword from the final desired bytes);
pokes of the previous state that the next one does not set are reset to the snapshot's values.
callcap restores the snapshot (pokes included) after each call, so pokes persist between states.
"""
import json, os, subprocess, struct, sys
from btram import ROOT, WORK, OUT, load

DISK = os.path.relpath(os.path.join(WORK, "bt_auto.st"), ROOT)


class Harness:
    def __init__(self, snap, outdir=None, steps=300000):
        self.snap = snap if os.path.isabs(snap) else os.path.join(WORK, snap)
        self.base = load(self.snap)
        self.outdir = outdir or os.path.join(OUT, "work", "cc")
        os.makedirs(self.outdir, exist_ok=True)
        self.steps = steps

    def run(self, states, tag="run"):
        """states: list of dict(name, pokes, presets, target, steps).  Returns {name: json}."""
        cur = {}
        lines = []
        for st in states:
            want = dict(st.get("pokes", {}))
            ram = self.base
            todo = {}
            for a in cur:
                if a not in want:
                    todo[a] = ram[a]
            todo.update(want)
            # merge to aligned longwords
            bases = sorted({a & ~3 for a in todo})
            buf = bytearray(ram)
            for a, v in list(cur.items()):
                pass
            for a, v in todo.items():
                buf[a] = v & 0xFF
            # bytes of the longword not in `todo` must equal the *currently poked* RAM, which is
            # base + cur; reconstruct that.
            curram = bytearray(ram)
            for a, v in cur.items():
                curram[a] = v
            for base in bases:
                lw = bytearray(curram[base:base + 4])
                for k in range(4):
                    if base + k in todo:
                        lw[k] = todo[base + k] & 0xFF
                lines.append("w %x %08x" % (base, struct.unpack(">I", bytes(lw))[0]))
            cur = {a: v for a, v in cur.items() if a in want}
            cur.update(want)
            out = os.path.join(self.outdir, "o_%s.json" % st["name"])
            if os.path.exists(out):
                os.remove(out)
            pre = "".join(" %s=%x" % (k, v) for k, v in st.get("presets", {}).items())
            relout = os.path.relpath(out, ROOT)
            lines.append("callcap %s %d %s%s" % (st["target"], st.get("steps", self.steps), relout, pre))
        script = "\n".join(lines) + "\nq\n"
        env = dict(os.environ, ATARI_NOTRACE="1")
        p = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume",
                            os.path.relpath(self.snap, ROOT), "repl", "--disk-a", DISK],
                           input=script, capture_output=True, text=True, cwd=ROOT, env=env,
                           timeout=3000)
        res = {}
        for st in states:
            out = os.path.join(self.outdir, "o_%s.json" % st["name"])
            if os.path.exists(out):
                res[st["name"]] = json.load(open(out))
        return res, p.stdout + p.stderr
