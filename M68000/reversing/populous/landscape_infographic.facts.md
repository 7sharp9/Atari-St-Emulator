# landscape_infographic.html: facts and sources

Page: `reversing/populous/landscape_infographic.html`, built by `uv run python reversing/populous/py/landscape_infographic.py`
(from `M68000/`) from `py/landscape_infographic.tmpl.html` and `py/landscape_core.js`. The build runs the JS-vs-Python
check first (375/375 at the last build; needs node and `$POP_WORK/game_start.snap`, no emulator). This file lists the
sources of the prose added in the expansion pass; earlier facts on the page are unchanged.
Docs: `reversing/populous/terrain.md` (T), `graphics.md` (G), `README.md` "Design digest" (D).

| fact on the page | source |
|---|---|
| Populous, Bullfrog 1989, ST version; god game; followers seek flat land, settle, earn mana; player reshapes land; powers earthquake, volcano, swamp, flood | README title line; D "What carries the game" (land is the interface, flat land is wealth, one growth loop, powers) |
| neighbouring corners differ by at most one level after any raise/lower | T 2 raise_point / lower_point ("no slope limit other than this difference of at most 1") |
| frame rebuilt every frame from the backdrop copy, blocks pasted far to near | G Summary, "Frame composition" |
| neighbouring cells share corners, so no cracks | derived from the corner layout (T 1); stated as reasoning |
| cell rule steps (average, mask, flat drop one level, shore +16, sea clears feature, rock `$2f` survives unless fully sea) | T 1 "Cell derivation"; G "Block selection" |
| blocks 1..14 are slopes with mask of raised corners; 15 flat drawn one level lower because its art is a full level tall; 17..30 shoreline versions | G "LAND0..LAND3" block table, "Block selection" |
| mask 0 implies all four corners equal; mask 15 impossible | arithmetic on the rule (floor of the mean); reasoning, not a doc claim |
| x always a multiple of 16, so the blit never shifts bits | G "Projection" |
| minimap is the book at the top left; 128 x 64 diamond | G "Minimap" |
| sea shimmer by alternating blocks 0 and 16 each frame, no palette cycling | G Summary, "Per-cell draw" |
| raise neighbour order E SE S SW W NW N NE; clamp 0..8; lower is the mirror | T 2 |
| cost 4n + 10; only 10 checked before; mana can go negative; raise at (11,16) 134 corners, 542 to -4 | T 2 cmd_raise and `verify_cmd.py` result; D "Bugs" |
| opening mana 399 | T 1 (`$bbd4` initial mana 399) and the template's `WB.mana = 399` |
| paint map mode: edits and powers cost nothing | T 2 (paint-map commands), T 4 gate ("if paint map: skip the checks and the cost") |
| PRNG 15-bit LCG, period 32768 | T 3 PRNG `$16702` |
| conquest seed = LEVEL.w8 + (world & 7); one LEVEL record per 25 worlds | T 3 new_world step 1, LEVEL.DAT table |
| reset consumes 4 rand calls; custom path draws one more for the landscape coin flip (hence 5 pre-rolls for `$1234`) | T 3 steps 1 and 2; PRESETS in the builder (4, 4, 5). The "one more" is read from step 1's condition order |
| walk steps x by rand()%(2rx+1)-rx; stops when raise_point returns 6 | T 3 walk `$bebc` |
| scatter: 22 clusters, 9 x 9 boxes, 30 tries, clusters 0-6 rocks, 7-21 trees, valid only on non-sea, non-`$2f` cells | T 3 scatter `$12e06`; `landscape_core.js` line 229 |
| LANDn files hold no heights; worlds are generated | T 3 step 1 |
| two-link evidence: Python vs emulator (3 worlds byte-identical, 2670/2670, 12/12 frames 64000/64000 px, 134/134), JS vs Python on scribbled random states | T 3, T 4 "Proof", G "Verification", builder docstring |
| callcap meaning | CLAUDE.md / skill usage; generic description |

## Notes

- Corrected on the page: the generation log said trees "only need non-sea land". Both the doc (T 3: a try is valid when
  the shape is not 0 and not `$2f`) and the JS port (`landscape_core.js` 229) apply the same test to rocks and trees. The
  JS string in the template now says so.
- The rules-table header "cost and gate" uses "gate" for the game's pre-check; it is not the proof sense of "gate".
- No numbers were changed. No doc/figure numeric disagreement found.
