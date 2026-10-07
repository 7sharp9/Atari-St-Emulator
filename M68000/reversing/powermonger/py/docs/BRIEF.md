# Brief: rewrite the PowerMonger reversing docs as prose of the working, not a diary

You are editing documentation only. Nothing here runs the emulator.

## Why

The PowerMonger docs (`M68000/reversing/powermonger/*.md`) grew over ~148 analysis passes. The repo rule
(`CLAUDE.md`, "Docs") is: docs are definitive reference text; correct stale claims in place; a new finding is
integrated into the surrounding prose, not appended as one more clause; a section that has become an unreadable
run-on is rewritten into a normal narrative of current understanding. "What changed this pass" belongs in `git log`
and `M68000/sessions/powermonger.md`, never in the docs.

Dave wants that applied to every doc: remove the diary, keep the working. The reader is an experienced
programmer who wants to know how the game works, what is proven, how it was proven, and how to reproduce it.

## What you receive

Pieces of the docs, split at `## ` headings: `docclean/in/<doc>/<NN>_<slug>.md` (your assignment names them).
Write each rewritten piece to the **same relative path under `docclean/out/`** (`out/<doc>/<NN>_<slug>.md`).
A piece that is already clean is copied verbatim to `out/`; do not churn it. Concatenating the pieces rebuilds the doc,
so a piece starts with its own `## ` heading line and you keep it, byte for byte.
(`docclean` = the work dir `$DOCCLEAN_WORK`, default `M68000/scratchpad/docclean`; the orchestrator copies this BRIEF there and fills `in/` with `py/docs/doc_pieces.py split`.)

## Hard rules

1. **No fact is lost.** Every address (`$xxxx`), count and ratio (`4119/4119`, "5 hits in 75 lands"), script and
   snapshot name, step count that reproduces something (`bp 668c` after 313,678,190 steps), field offset, and every
   evidence label (proven, live, code read, inferred, not checked) survives, attached to the same claim. A negative
   control or falsifier is evidence and stays. If a number is superseded by a later number in the same piece, state the
   current one only.
2. **No new claims.** Do not run anything, do not "improve" a finding, do not resolve a contradiction by choosing a
   side: keep both statements and flag it in your report. Do not upgrade a label ("inferred" never becomes "proven").
3. **Do not touch or rename `##` and `###` heading lines.** Other docs and the handoff cite sections by their heading
   text ("Natural coverage", "Mode `$36`"). You may add `####` sub-headings and bold lead-ins inside a section.
   Code blocks, C structs, pseudocode and tables stay verbatim unless the diary lives inside them.
4. Write only under `docclean/out/`. No git, no build, no `dotnet`, no emulator, no edits anywhere else, no
   background processes. You may read the repo (the untouched docs in `M68000/reversing/powermonger/`, `py/` scripts,
   `.sym`) to confirm that a cross-reference target exists or that a script named in a pointer exists.

## What counts as diary (remove or rewrite)

- Pass, session or agent numbers and "this pass", "new this time", "a later pass", "the 148th pass ran".
- Chronology of the investigation: "first read as X, then found Y", "an earlier reading said", "previously",
  "was missing", "turned out", "used to", "originally", "stale". Superseded readings are dropped. Keep one present-tense
  clause only where a reader of the old scripts, identifiers or the `.sym` would hit a live trap
  ("`shepherd_*` identifiers in `tools/pm_fsm_ref.py` are legacy names; the array is the tree array").
- Loose ends narrated inside a finding ("two more hits were not examined", "not yet fed to the gate"). Move them to
  one closing sentence of the section that says what is open and how it would be proven, or, if the section already
  has an open-items list, to it.
- "Measured:" and "Natural coverage" style paragraphs that tell the order in which runs were made. Rewrite as: what
  was run (population, budget), what it showed (counts), where the data is.
- Mega-bullets and mega-paragraphs (over about 1,200 characters) that carry a claim, its mechanism, three
  instances, the rates and the caveats in one run-on.

## How to rewrite

Per topic, in this order, in short paragraphs (or a short list where the items really are parallel):

1. **What it is / does**: the current understanding, in the present tense.
2. **Mechanism**: how it works (routine addresses, tables, conditions).
3. **Evidence**: the gate or live check, with its match count and the script (`py/...`), including negative controls.
4. **Reproduce**: snapshot, step count, `bp`/`hits` line, only what is needed to repeat it.
5. **Status and limits**: code read vs proven vs inferred; what is open and how it would be proven.

Split a run-on into a bold lead-in per instance, for example `**k25 (natural, executed).** ...`, one short paragraph each.
Where several instances share structure, a small table is better than three sentences.

Style: plain prose, no em dashes in text you write (existing headings keep theirs), no emojis, no exclamation marks, no
buzzwords or metaphors. Keep the surrounding doc's terminology and its backtick conventions. Expect the result to be
shorter by about 10 to 30 % where narrative is removed; never cut data to reach a length.

### Example (strategy.md, "Natural coverage")

Before (diary, one bullet, abridged):

> Short runs are the wrong instrument for the rare arms: the 148th pass ran 75 unpoked Play Random Land lands for 2G
> steps each (`py/arms/`: ...) ... Over them: arm 1 `$65c8` 3507, ... the food fallback `$66a4` 0, the refusal `$6884` 0.
> (The 60M-step census on the same roll, 3.5G steps in all, saw none of `$664c`, `$666c`, `$668c`: they need a few
> hundred million steps.)

After (reference):

> **Natural coverage.** The rare arms need long runs. The reference census is 75 unpoked Play Random Land lands, each
> run 2G steps (`py/arms/`: `batch1.sh` the 39 lands of `pm143/lands`, `batch2.sh` 36 further rolls; `hits` per
> 250M-step chunk), about 150G steps in all and about 78G with the land still alive; 44 of the 75 ended when the player's
> captain group dissolved (`$d2c8`). Hit counts over the census: arm 1 `$65c8` 3507, escort `$65f4` 2286, attack
> `$6638` 31122, arm 4 `$666c` 145, arm 5 `$668c` 5, transfer head `$664c` 6913, food fallback `$66a4` 0, refusal
> `$6884` 0 (`py/arms/summarize.py L2G M2G`). A 60M-step census of the same roll (3.5G steps in all) saw none of
> `$664c`, `$666c`, `$668c`: those arms need a few hundred million steps per land.

(The same facts, the investigation's order removed, the label of each count kept.)

## Report (your final message; subagents cannot write report files)

Run `python3 py/docs/doc_facts.py <doc>/<piece>.md ...` on every piece you wrote. It lists facts (addresses, file names,
ratios, numbers of 3+ digits, backticked identifiers) present in the original and absent from your rewrite
(`MISSING`) and new ones (`NEW`). Every MISSING item must be restored, or listed in your report with the reason (for
example "restated as 4/4 instead of 4 of 4" does not show up, but a number merged into a later one does). Every NEW item
must be a restatement (a sum, a normalised form), never an invented fact.

The report has, per piece: (a) one line on what you changed; (b) DROPPED: each fact you removed on purpose and why
(expected: rare); (c) NOTICED: contradictions between pieces or docs, labels you could not place, claims that look
stale but you left alone; (d) the final `check.py` residue and why each item is acceptable. Keep it under 80 lines.
