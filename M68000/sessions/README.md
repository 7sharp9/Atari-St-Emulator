# Session handoffs

One file per workstream holds everything the next session needs to continue it. It is the only
continuation record: the next-session prompt is always the one line `/resume <workstream>`.

| file | workstream |
|---|---|
| `cadaver.md` | Cadaver spike (`reversing/cadaver/`) |
| `populous.md` | Populous reversing (`reversing/populous/`) |

Add a row when a workstream gets its first handoff (for example `powermonger.md`,
`emulator.md` for CPU/peripheral work that is not driven by one game).

## Rules

- **One writer per file.** A session writes only the handoff of the workstream it is working on. A
  session that finds another workstream's handoff stale says so to that session or to Dave; it does
  not edit it.
- **Rewrite, never append.** The file is the current state. Git history keeps the old versions, so
  there is no per-pass diary here (same rule as the docs).
- **Written by `/handoff`, read by `/resume`** (skills in `.claude/skills/`). `_template.md` is the
  shape.
- **Proof, not narrative.** "Proven" items carry their match count and the script that reproduces
  it; everything else is an open item with how it would be proven.
- **Committed at the end of every session**, in its own commit or with the session's last work
  commit, so a concurrent session and the next one see the same thing.

## Shared resources

Two sessions often share this checkout. These are shared, and a session changes them only after
checking who else is live (`ListAgents`) and messaging them, then waiting for an answer or an idle
notice:

- `bin/Debug/net8.0/M68000.dll`: any `dotnet build` into `bin/`, and `taskkill` of dotnet;
- the emulator sources `*.fs`;
- `CLAUDE.md`, `.claude/skills/*`, `M68000/DEVELOPING.md`, `tools/`.

Edits to `CLAUDE.md` and the skills go in their own small commit, never mixed into a workstream
commit, so the other session can build on them straight away.
