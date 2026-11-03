# Hindi and Hinglish field recovery diagnostic

Source scope is the 26 Hindi and 28 Hinglish completed run 1 pairs. The published recovery score and production grounding were replayed in memory. Every published miss is assigned one category. Gnani requests 0. Ollama requests 0.

The denominator n is the number of labelled field instances in the cell. The five categories sum to misses. Format includes clear wording, translation or spelling variants within the same value. The diagnostic match calculation counts native_script_label and format as matches. Ambiguous cases are classified as other and counted as misses in diagnostic recall. They remain in the denominator.

One reviewer classified the cases after seeing the misses. The review was not blind and the cases were not double-coded.

| Language | Field | Condition | n | Recovered | Native script | Format | Omitted | Wrong value | Other |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| hi | name | reference | 23 | 14 | 3 | 5 | 0 | 0 | 1 |
| hi | name | transcript | 23 | 14 | 3 | 5 | 0 | 0 | 1 |
| hi | age | reference | 23 | 0 | 0 | 23 | 0 | 0 | 0 |
| hi | age | transcript | 23 | 0 | 0 | 23 | 0 | 0 | 0 |
| hi | gender | reference | 6 | 6 | 0 | 0 | 0 | 0 | 0 |
| hi | gender | transcript | 6 | 6 | 0 | 0 | 0 | 0 | 0 |
| hi | marks | reference | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| hi | marks | transcript | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| hi | last_seen_place | reference | 23 | 14 | 0 | 5 | 0 | 0 | 4 |
| hi | last_seen_place | transcript | 23 | 14 | 0 | 5 | 0 | 0 | 4 |
| hi | clothing | reference | 18 | 18 | 0 | 0 | 0 | 0 | 0 |
| hi | clothing | transcript | 18 | 18 | 0 | 0 | 0 | 0 | 0 |
| hi | language_spoken | reference | 2 | 0 | 2 | 0 | 0 | 0 | 0 |
| hi | language_spoken | transcript | 2 | 0 | 2 | 0 | 0 | 0 | 0 |
| hi | Total | reference | 96 | 53 | 5 | 33 | 0 | 0 | 5 |
| hi | Total | transcript | 96 | 53 | 5 | 33 | 0 | 0 | 5 |
| hinglish | name | reference | 25 | 25 | 0 | 0 | 0 | 0 | 0 |
| hinglish | name | transcript | 25 | 17 | 0 | 7 | 0 | 1 | 0 |
| hinglish | age | reference | 25 | 0 | 0 | 25 | 0 | 0 | 0 |
| hinglish | age | transcript | 25 | 0 | 0 | 25 | 0 | 0 | 0 |
| hinglish | gender | reference | 8 | 8 | 0 | 0 | 0 | 0 | 0 |
| hinglish | gender | transcript | 8 | 5 | 0 | 0 | 3 | 0 | 0 |
| hinglish | marks | reference | 4 | 4 | 0 | 0 | 0 | 0 | 0 |
| hinglish | marks | transcript | 4 | 4 | 0 | 0 | 0 | 0 | 0 |
| hinglish | last_seen_place | reference | 25 | 15 | 0 | 6 | 0 | 0 | 4 |
| hinglish | last_seen_place | transcript | 25 | 18 | 0 | 3 | 0 | 0 | 4 |
| hinglish | clothing | reference | 18 | 18 | 0 | 0 | 0 | 0 | 0 |
| hinglish | clothing | transcript | 18 | 18 | 0 | 0 | 0 | 0 | 0 |
| hinglish | language_spoken | reference | 5 | 5 | 0 | 0 | 0 | 0 | 0 |
| hinglish | language_spoken | transcript | 5 | 5 | 0 | 0 | 0 | 0 | 0 |
| hinglish | Total | reference | 110 | 75 | 0 | 31 | 0 | 0 | 4 |
| hinglish | Total | transcript | 110 | 67 | 0 | 35 | 3 | 1 | 4 |

## Hindi recall diagnostic

- reference · original 53/96 (55.21%). Native script 5 and format 33 explain 38/43 misses (88.37%). Diagnostic recall 91/96 (94.79%), a gain of 39.58 pp.
- transcript · original 53/96 (55.21%). Native script 5 and format 33 explain 38/43 misses (88.37%). Diagnostic recall 91/96 (94.79%), a gain of 39.58 pp.

The Hindi transcript-minus-reference recall gap is 0.00 pp in the published result and 0.00 pp in this diagnostic.

## Native-script name item IDs

- reference · hi-022, hi-023, hi-024.
- transcript · hi-022, hi-023, hi-024.

A transliteration rule must be preregistered before any rescoring.

## Fields without a published recovery score

These are label counts per condition, so no original miss classification is available.

- hi · relation · n=23.
- hi · height_build · n=0.
- hi · last_seen_time · n=20.
- hi · health_or_special_needs · n=1.
- hinglish · relation · n=25.
- hinglish · height_build · n=5.
- hinglish · last_seen_time · n=21.
- hinglish · health_or_special_needs · n=0.
