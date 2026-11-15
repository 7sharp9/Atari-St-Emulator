# Writing for readers: figures, posts and README openings

The topic docs under `reversing/<game>/` are written for the next session that reasons about the game: dense,
address-heavy, every claim with its evidence. That density is the point. A game workstream builds the docs up as
compressed knowledge, and later work reads them cheaply. They are not rewritten for newcomers.

The expansion happens where the knowledge is published: the infographics, the blog posts drafted from them, and
the opening of each game's README. The reader there is a competent programmer who knows nothing about the Atari
ST, the 68000, the game or this repo's tooling. Shared terms are defined once in `GLOSSARY.md`; link it rather than
redefine them.

## Rules for every edit

- No new facts. A clearer sentence uses only what the figure, its facts file or the cited doc section already
  says. A correction cites the doc section or script output that proves it and goes in the facts file too. A
  premise or genre word no doc states is not written from memory: use the doc's own words and ask Dave.
- Honest hedges ("inferred", "not covered") are moved, never dropped.
- Run `tools/docguard.py` on every changed file before committing. It lists each number, address, match count
  and backticked name the edit added or removed; each one listed is either an intended change (a pass number
  removed, a citation moved to the Sources line, a correction) or a mistake to undo.

## Figures

1. A key line directly under the lead: `$` numbers are addresses in the game's memory, given as citations; the
   evidence words are **proven** (checked against the game's own code with a match count), **observed** (seen in
   the running game) and **inferred** (read from the code or reasoned, not run). Legends use the same three words.
2. Titles, subtitles, panel headings and box headlines say the role or the problem in words; an address follows
   only as a citation ("the scoring routine ($2337a)").
3. No snapshot names, script names, file paths or tooling words (callcap, gate, poke, corpus, census, stserver,
   REPL, port) in titles, panels, captions or takeaways: "a saved game state", "set by hand", "a check script",
   "our Python model". The "How we know" footer defines callcap in one plain clause, and a final Sources line in
   the smallest type carries the names for anyone reproducing the figure.
4. Every term is defined at its first use, not in the footer. 68000 notation (`D0`, `52(A1)`, `bvs`) appears only
   as a small citation after the plain description.
5. Each takeaway draws a lesson the reader can reuse; counts support it in a clause.
6. The lead says the game is an Atari ST game (or an arcade board) and that the figure comes from
   reverse-engineering it in an emulator.
7. Edit the generator or template, not only its output, regenerate from cached data, and look at the result for
   clipped or overlapping text. Each new sentence gets a row with its source in the figure's facts file.

## README openings

In this order: one paragraph on what the game is (publisher, year, what the player does, in the docs' own words);
two or three sentences on what the doc set has established; a "Where to find what" map phrased as reader
questions; the line "Terms used here are defined in `../GLOSSARY.md`." Provenance, hashes, the boot path and
emulator fixes follow the map. Pass numbers and session history do not belong in headings or the opening. Before
renaming a heading, grep `reversing/`, `sessions/`, `DEVELOPING.md`, `CLAUDE.md` and the skills for references to
its old text and fix them in the same edit.
