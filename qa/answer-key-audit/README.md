# Answer-key audit — 26 October 2026

**Verdict: the answer key is useful as an exploratory reference, but it is not a completely correct, complete gold standard.** This audit establishes one definite author error and two independently readable omissions. It also identifies label-specificity questions and reproduces scoring defects. These findings are a lower bound, not a measured overall error rate.

The original frozen answer key and benchmark evaluator have not been edited. Existing published benchmark scores have not been replaced or reinterpreted as scores for a corrected dataset.

## Scope and evidence standard

I read the complete local `ground_truth.json` and visually surveyed all six original photos, using EXIF-corrected views and targeted crops. The app's six photo files are byte-for-byte identical to those source photos. I inspected readable areas against the key and investigated specific doubtful labels. This was **not** an independently certified, book-by-book re-annotation or bibliographic verification of every one of the 295 entries. No correctness percentage is claimed for the remaining entries.

Crops use the actual pixels. Rotation and enlargement make the text easier to inspect; they do not reconstruct missing detail. A publisher or library record can corroborate a book's title or author, but cannot by itself prove that book is in the photograph. The two confirmed omissions below have direct visible title evidence in the photo, not merely model agreement or web-search matches.

| Photo | Entries in the frozen key |
| --- | ---: |
| a.jpg | 65 |
| b.jpg | 49 |
| c.png | 26 |
| d.jpg | 8 |
| e.jpg | 108 |
| f.jpg | 39 |
| Total | 295 |

The file parses correctly and no normalized exact duplicate titles were found within a photo. Structural validity does not establish annotation correctness.

## Confirmed findings

### AK-01 — Wrong author: The Works of Jacques Lacan, photo a

The key attributes **The Works of Jacques Lacan** to **Malcolm Bowie**. The pictured white spine names **Bice Benvenuto and Roger Kennedy**. The [Wellcome Collection's catalogue record](https://wellcomecollection.org/works/q55u89xg) independently confirms those authors.

The adjacent blue **Lacan** is a separate book by Malcolm Bowie. The key includes both books, so the finding is an author error on the former, not a duplicate-title error.

![The Works of Jacques Lacan spine showing Benvenuto and Kennedy](/Users/roshansingh/Desktop/bookshelf_demo/qa/answer-key-audit/crops/a_works_lacan.png)

Original location: photo a, lower shelf, just left of the narrow blue *Lacan* and blue *The Truth in Painting*. Key entry: 43 (one-based position within photo a's list).

**Effect:** the wrong author can penalize a correct author prediction. The benchmark scores authors separately, so this author correction alone would not change title precision, recall or F1.

### AK-02 — Readable omission: Images of Cornwall, photo b

The cyan spine on the lower shelf, between **Marcel Broodthaers** and **Modern Art and Modernism**, visibly reads **Images of Cornwall — Alan Bennett**. This title is absent from photo b's answer list.

![Images of Cornwall and Alan Bennett visible on the cyan spine](/Users/roshansingh/Desktop/bookshelf_demo/qa/answer-key-audit/crops/b_cyan_spine.png)

**Effect:** a model correctly naming this book can be counted as a false positive against the incomplete key.

### AK-03 — Readable omission: One Piece, Vol. 22, photo f

The purple/red back cover near the middle-right of the display visibly reads **ONE PIECE** and **22**. Photo f's key has no One Piece entry. The [publisher's volume-22 page](https://www.viz.com/manga-books/manga/one-piece-volume-22-0/product/1788) corroborates the title and credits **Eiichiro Oda**. The author's name is bibliographic corroboration, not text independently read from this crop.

![One Piece volume 22 visible on the back cover](/Users/roshansingh/Desktop/bookshelf_demo/qa/answer-key-audit/crops/f_one_piece.png)

There is also a nearby book marked 23, but its series/title is more obscured. This audit conservatively counts only the clearly readable volume 22 as a confirmed omission.

**Effect:** another correct recognition can be counted as a false positive.

## Additional findings that need annotation decisions or further confirmation

These are deliberately separate from the confirmed error/omission count.

| ID | Photo | Finding | Treatment |
| --- | --- | --- | --- |
| AK-04 | b | **VAN GOGH** is readable on the pale spine above Pissarro; there is no Van Gogh entry for b. | Strong omission candidate, but the precise edition and any longer title are not established. See `crops/b_gold_spine.png`. |
| AK-05 | f | The key says only **Timmy Failure**. The red cover appears to identify **Mistakes Were Made**, a specific volume documented by [Candlewick](https://www.candlewick.com/9780763669270/timmy-failure/). | Review the full title rather than using a generic series name. This is a specificity issue, not an extra physical book. See `crops/f_timmy_subtitle.png`. |
| AK-06 | e | The Magic Ballerina spine prints both **Delphie and the Magic Spell** and **Rosa and the Golden Bird**; the key records only the former. | Define a consistent rule for two-story omnibus titles. Do not automatically count one omnibus as two physical books. See `crops/e_children.png`. |
| AK-07 | f | The prominent black/gold book is **Hunt the Villain — Rina Kent**, already included separately. I could not independently locate the additional **The Villain — L.J. Shen** entry. | Unresolved. An obscured copy may be elsewhere in the photo; inability to locate it is not proof of absence. Do not delete it on this audit alone. See `crops/f_villain.png`. |
| AK-08 | e | **The Secret Life of Bees** is absent from the key. The [report itself](https://atharva-729.github.io/bookshelf-benchmark/) acknowledges it as a real excluded book, along with other examples. | Report-acknowledged incompleteness. Its dark, partly occluded spine is less clear than AK-02/03, so this is not presented as an equally strong new independent reading. See `crops/e_bees.png`. |

Null authors have not been treated as errors. For example, not knowing an author is allowed by the dataset's rules. Unfamiliar-looking author strings also need direct checking: the pictured *What Katy Did* actually prints **Susan M. Coolidge**, so that string has not been casually labelled wrong.

## Author-field consistency

Fourteen entries were flagged for role review because their author fields contain institutions, series imprints, publishers or similar labels. Examples include **Penguin Parallel Text**, **Tate Gallery**, **Arts Council 1978** and **Philip**. The complete list is in `findings.json`.

These are **14 review flags, not 14 newly proved wrong authors**: institutions can be legitimate corporate authors of some works. The issue is that author, editor, publisher and series roles are mixed in one field. The repository's own `notes/metrics.md` acknowledges that a model giving a real author can be marked wrong when the key stores an institution instead. Bibliographic roles need consistent annotation before author-accuracy scores are treated as precise.

## Separate problem: the scorer accepts insufficient or wrong identifications

I ran the repository's unmodified `benchmark/evaluate.py` title-scoring function. Its match threshold is 0.85. The following isolated pairs all received **1.0** and are therefore eligible matches:

| Model prediction | Reference title | Score | Problem |
| --- | --- | ---: | --- |
| A Life of Picasso (Volume I: 1881–1906) | A Life of Picasso (Volume III: 1917–1932) | 1.0 | Different volumes accepted as the same book. |
| Timmy Failure: We Meet Again | Timmy Failure | 1.0 | An underspecified series-only key can accept a different volume. |
| Diary of a Wimpy Kid | Diary of a Wimpy Kid: The Long Haul | 1.0 | A generic series label is eligible, although the report uses this as an example of an answer that is too vague. |

These are deterministic reproductions of eligibility for matching, not claims that every such pair was selected in every recorded run. Actual assignments also depend on the scorer's greedy one-to-one matching with the other predictions.

The repository already acknowledges the Picasso volume weakness in its scoring notes. This affects interpretation of precision/recall/F1 independently of whether the answer key has the right book. Wrong-volume acceptance can inflate successful identifications; omitted readable books can depress precision. Their net impact and any model-ranking changes cannot be quantified from this limited audit.

## Recommended next step

Keep the original key as **v1** for reproducibility. Build a reviewed **v2** with a source crop and status for each entry: confirmed, uncertain, or excluded with a stated reason. Correct the confirmed author error, adjudicate the omissions, separate author/editor/publisher roles, specify how omnibus titles count, and require volume-aware title matching. Then rescore every saved model output on the same v2 dataset and scorer before quoting updated accuracy or model rankings.

The findings above justify revising confidence in the benchmark's exact numbers. They do not justify inventing a replacement total, an error percentage, or a revised winning model.

## Integrity and machine-readable evidence

Original answer-key SHA-256 before and after this audit:

`7ffd22b754231c9b606edb769b4d60ad89b44d5de9d40a07f647360927eb5123`

`findings.json` records classifications, source-image hashes, crop coordinates in the EXIF-corrected frame, bibliographic sources, role-review flags, and scorer reproductions. `check_audit.py` checks file integrity and reproduces the scoring results; it does not automatically certify the visual judgements.
