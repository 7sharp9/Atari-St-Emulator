# Continuity profile

Repo-specific data for `continuity:session-resume` and `continuity:session-handoff`. Rules that apply outside
sessions (shell pitfalls, git, running the emulator) stay in `CLAUDE.md`; this file points at them.

## Paths

- Sessions: `M68000/sessions/` (template `M68000/sessions/_template.md`, index `M68000/sessions/README.md`, whose
  "Rules" and "Shared resources" sections bind every session).
- Decision record: no separate file. Settled positions about a game live in its topic docs under
  `M68000/reversing/<game>/` (README + topic docs, "Design digest" where present); the session file's
  "Proven so far" points at them.
- Evidence: the topic docs plus the scripts that reproduce each match count, promoted into
  `M68000/reversing/<game>/py/` with a README table. Bulky outputs (snapshots, corpora, decompiles) go under a
  named dir in the gitignored `M68000/scratchpad/` and reusable snapshots are indexed in
  `M68000/scratchpad/ANCHORS.md`.
- Tool index: `M68000/DEVELOPING.md` "Other tools" (check it before writing any helper).
- Findings ledger: none.
- Tests: none for reversing work. Emulator code: the regression net, `reverse-engineer-st-game` skill section 6.
- Topic docs are read by section, never whole: `grep -n '^#' <doc>`, then the sections the plan or Dave's question
  needs (`reverse-engineer-st-game` skill, "Context budget").
- Cross-cutting tasks (docs, tools, an emulator fix outside a workstream) have no session file: check the shared
  resources they touch and write no handoff unless Dave asks for one.

## Resume checks

- Emulator processes, possibly another session's: `tasklist | grep -i dotnet` on Windows,
  `ps aux | grep '[M]68000.dll'` on the Mac (quote the pattern under zsh). Never kill one you did not start.
- The working data and the snapshot named in the session file's "Resume point" exist. If not, rebuild them with
  the recipe the file points to before any live test.
- Before scoping a live test for a carried-over "Open" item, grep the game's topic docs for a numbered section
  that already answers it: an Open item goes stale when a later section settles it.
- Dropped pass (uncommitted files and no live session on this workstream in `ListAgents`): commit it as its own
  commit only if the diff is coherent, finished-looking prose (not a half-written fragment) and every tool or
  script it names exists in `M68000/tools/` or `reversing/<game>/py/`; verify, commit, and say so in the report.
  Otherwise leave it and tell Dave.
- Before touching a shared resource (`M68000/sessions/README.md`, "Shared resources"), message the live
  sessions and wait for an answer or an idle notice.

## Handoff: land the work

- Emulator changes land only after the regression net (`reverse-engineer-st-game` skill, section 6;
  `CLAUDE.md` "Emulator changes").
- A build into `bin/` (`bin/Debug/net8.0/M68000.dll`) only after checking `ListAgents` and messaging live
  sessions (`M68000/sessions/README.md`, "Shared resources").
- A changed file you leave uncommitted goes under the session file's "Resume point" as "Uncommitted work left
  behind", with the reason.
- Session file content (from `_template.md`): "Resume point" names the last commit, the working-data location
  with its rebuild recipe, and the snapshot to start from. "Proven so far" is short, each line with its match
  count and script, pointing at the topic-doc section. "Open, in priority order" gives each item how it would be
  proven (script, snapshot, match count to reach), ordered by what unblocks the most, not by what is easiest.
- Older continuation notes to fold in and delete: a scratchpad `NEXT_SESSION.md`, a root `next_session.md`, a
  memory RESUME block.

## Handoff: extra checks

### Mechanical diff checks

Over the session's diff (`git diff <start>..HEAD`, `<start>` = the session file's last commit when the session
began):

- docs that cite a script only under `scratchpad/`: promote the script into `reversing/<game>/py/` or label the
  result a record;
- scripts touched that hard-code a machine (`py -3`, `C:/...`, a literal repo path, a fixed `../` count);
- tools written this session that duplicate one in `M68000/DEVELOPING.md` "Other tools", and new `tools/`
  scripts missing their row there.

### Design digest

If the game's `reversing/<game>/README.md` has a "Design digest" section (the game's rules restated for re-use:
what carries the game, what limits became features, what are bugs), check it against this session's work:

- List the session's changes to the topic docs and reference models: `git diff <start>..HEAD --stat` over
  `reversing/<game>/`.
- For each change, find every digest line that relies on the changed section, and each digest line that names a
  routine, rule or count this session touched. Correct it in place, or add the rule if the session proved a new
  core mechanic or bug.
- Every digest line cites the topic-doc section that proves it; a line whose section no longer says so is wrong
  until fixed. Anything not proven stays labelled inferred.
- Commit the digest with the session's work, and say in the report whether it changed.

## Lesson routing

| lesson | goes to |
|---|---|
| a step in reverse-engineering a game | `.claude/skills/reverse-engineer-st-game/SKILL.md` |
| a tool missing or rewritten ad hoc, or a helper written inline | the tool in `M68000/tools/` (or the game's `py/`), plus its row in `M68000/DEVELOPING.md` "Other tools" |
| a fact about a game | that game's topic doc, as definitive text (`CLAUDE.md` "Docs") |
| a repo-wide rule or shell/tool pitfall | `CLAUDE.md`, one line per rule |

Write each rule as it is now, with one worked example and a pointer to the doc that proves it. Before adding a
line, grep `CLAUDE.md` and the skill for one that already covers it.

## Commit rules

- No `Co-Authored-By` trailer: history was scrubbed of them. This overrides any harness attribution reminder
  (`CLAUDE.md` "Git").
- Named files only, never `git add -A` (ROMs, disks and archives sit untracked); read `git diff --cached --stat`
  first (`CLAUDE.md` "Git").
- `CLAUDE.md` and skill edits (including this profile): check `ListAgents`, tell each live session what you are
  changing, and commit those files in their own small commit, never mixed into a workstream commit.
- The session file is committed at the end of every session, in its own commit or with the last work commit.

## Agent rules

Every reviewer or runner brief carries these; most live in `CLAUDE.md`, cited by section.

- No build, no git, no `taskkill`; write only under the agent's own directory (`CLAUDE.md` "Running";
  `reverse-engineer-st-game` skill 3c "HARD RULES" for the `agents/<area>/` and `$<GAME>_WORK/<area>/` layout).
  Tools that write to the cwd run with an explicit output path; read `git status` after the agent returns.
- `ATARI_NOTRACE=1` on every raw `dotnet exec` (`CLAUDE.md` "Running"). Bound runs by step counts, not
  `timeout` (absent on macOS; `CLAUDE.md` "Shell pitfalls").
- Derive the repo root by walking up to the directory holding `tools/rdis.py` (or `M68000_ROOT`), never a
  literal path or a fixed `../` count; temp files in one named scratchpad dir (`CLAUDE.md` "Proving routines
  with parallel subagents").
- Timing: an interleaved A/B of two builds, `uptime` recorded per run, median and min reported, a gap under about
  5% is noise unless it repeats in every pair (`CLAUDE.md` "Emulator changes").
- Stop every emulator process the agent started before its final message: a finished agent's run held `bin/`'s
  DLL and blocked the parent's build (skill 3c).
- The report is the final message; the parent saves it (`agents/<area>/report.md`).
- An agent that changes emulator code runs in its own worktree and builds there, never into the shared `bin/`
  (`CLAUDE.md` "Emulator changes").
