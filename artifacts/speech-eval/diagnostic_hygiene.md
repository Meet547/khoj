# Speech evaluation diagnostic hygiene

This audit used saved data. Gnani requests 0. Ollama requests 0.

## Hindi item-level agreement

All 182 paired item-field rows agree across reference and transcript. Among 96 labelled rows, 53 are recovered in both and 43 have identical miss classifications. The other 86 rows have no expected label on either side. Differing item IDs: none.

The original diagnostic was coded by one reviewer after seeing the misses. The review was not blind and was not double-coded. Ambiguous cases count as misses in the 91/96 diagnostic recall.

## Hinglish reference-to-transcript losses

Eight name losses and three gender losses. Name judgments compare the grounded values on each side after case folding and retaining Latin letters in word order. Spelling variants were judged case by case. Letter similarity alone does not establish name equivalence.

- Name, spelling variant (7). hinglish-003, hinglish-012, hinglish-016, hinglish-020, hinglish-022, hinglish-024, hinglish-029.
- Name, different name (1). hinglish-030.
- Gender, omitted (3). hinglish-011, hinglish-015, hinglish-027.

## Fields outside the run 1 scoring scope

Label counts are shown as completed run 1 pairs / full source corpus. The extraction columns count saved item-condition outputs with at least one nonblank value. Counts include outputs regardless of label presence and are separate from recall. Height and build are counted together. Health or special needs maps to the conditions output.

| Language | Completed pairs | Last seen time | Relation | Height or build | Health or special needs |
|---|---:|---:|---:|---:|---:|
| bn | 10 | 8 / 10 | 9 / 11 | 1 / 1 | 0 / 0 |
| en | 20 | 16 / 16 | 18 / 18 | 5 / 5 | 0 / 0 |
| gu | 1 | 1 / 10 | 1 / 11 | 0 / 2 | 0 / 0 |
| hi | 26 | 20 / 24 | 23 / 27 | 0 / 0 | 1 / 1 |
| hinglish | 28 | 21 / 23 | 25 / 27 | 5 / 5 | 0 / 2 |
| kn | 10 | 8 / 10 | 9 / 11 | 0 / 0 | 0 / 0 |
| ml | 9 | 7 / 10 | 8 / 11 | 3 / 3 | 0 / 1 |
| mr | 18 | 14 / 16 | 16 / 18 | 1 / 1 | 0 / 0 |
| pa | 0 | 0 / 10 | 0 / 11 | 0 / 2 | 0 / 2 |
| ta | 10 | 8 / 10 | 9 / 11 | 3 / 3 | 1 / 1 |
| te | 3 | 2 / 9 | 3 / 10 | 1 / 2 | 0 / 0 |

All four fields have extraction output in the saved detail.

| Field | Hindi ref / transcript | Hinglish ref / transcript | All saved pairs ref / transcript |
|---|---:|---:|---:|
| last_seen_time | 20 / 20 | 21 / 21 | 105 / 104 |
| relation | 23 / 23 | 25 / 25 | 112 / 112 |
| height_build | 0 / 0 | 5 / 5 | 19 / 19 |
| health_or_special_needs | 1 / 1 | 0 / 0 | 1 / 1 |

## Held-out status

The speech pack is no longer a clean held-out set. These artifacts used speech-pack examples to classify misses, diagnose error patterns, or define follow-up methods.

- `field_diagnostic.md` classified age and language misses from 20 and 15 sampled pairs.
- `hinglish_script_check.md` used observed script mismatches to propose follow-up transliteration options.
- `normalisation_preregistration.md` designated development items from the earlier diagnostic. The rules were supplied before the rescore, and the preregistration specifies that the development items check implementation.
- `normalisation_rescore.md` applied the frozen rules and attributed language mismatches and specific transcript misses.
- `hindi_hinglish_diagnostic.md` classified all 164 published Hindi and Hinglish misses after inspecting them.
- `diagnostic_hygiene.md` audited those labels and classified Hinglish name losses by comparing the saved values.

The original field recovery preregistration lists fixed aliases, but their item-level provenance is undocumented. The original field recovery and WER reports publish aggregate scores. The run 2 preregistration used prior items to select follow-up cohorts, and the run 2 report records the stopped run and a replay comparison.
