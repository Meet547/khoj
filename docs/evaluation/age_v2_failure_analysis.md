Development analysis of a held-out set that has now been used. Findings are hypotheses for v3, not validated fixes.

# Age v2 failure analysis

The scored report contains aggregate field results and per-case repeat emission totals. The attempt log contains case IDs, repeat numbers and provider attempt metadata. It does not contain extracted values, proposed evidence, case-level grounding decisions or label comparisons. A successful chat attempt indicates a valid model response, so it cannot distinguish an omitted field from a wrong or dropped value. Counts below are confirmed where the two files support them. “Unresolved” means the evidence is insufficient to assign a requested category or case ID.

## Primary cases

- **V2 age misses: 6.** English 2, Hindi 2, Hinglish 2. Across the primary v2 pass, grounding recorded 6 `number_missing` and 0 `quote_missing`. The files do not link these drops to individual missed labels. Category counts for a range wider than the evidence supports, an uncovered number word, a model-invented range from an approximation, and other are all unresolved. Case IDs are unresolved for all 6 misses.
- **V2 gender: 3 wrong values and 3 omissions.** The report shows 6 incorrect cases in total and 3 wrong emissions. Suspected label error, model error and ambiguous counts are unresolved, as are the case IDs.
- **V2 clothing: 1 wrong value and 0 omissions.** Suspected label error, model error and ambiguous counts are unresolved for the wrong value. Its case ID is unresolved.
- **V2 health or special needs: 2 wrong values and 0 omissions.** The report shows 43/45 exact matches and 2 wrong values. Both incorrect cases are accounted for by wrong emissions, so the report does not support a separate omission. Suspected label error, model error and ambiguous counts are unresolved, as are the case IDs.
- **V1 age: 10 wrong emissions out of 20.** English 2, Hindi 5, Hinglish 3. Counts for conflict label, range mismatch, null label and other are unresolved. Case IDs are unresolved for all 10 wrong emissions.

## Repeat turns

Each listed case had two repeat turns. Neither turn emitted an age for any case. The report cannot distinguish a grounding drop from a null proposal at the individual turn level.

| Case ID | Repeat 1 emitted | Repeat 2 emitted | Drop vs. null |
| --- | --- | --- | --- |
| heldout-v2-en-009 | 0 | 0 | Unresolved for both turns |
| heldout-v2-en-010 | 0 | 0 | Unresolved for both turns |
| heldout-v2-en-011 | 0 | 0 | Unresolved for both turns |
| heldout-v2-en-012 | 0 | 0 | Unresolved for both turns |
| heldout-v2-en-013 | 0 | 0 | Unresolved for both turns |

Across all ten repeat turns, 0 emitted, 4 were dropped by grounding (2 `quote_missing`, 2 `number_missing`), and 6 returned no age without a recorded grounding drop. There were no model-unavailable repeat turns.

Completing the case-level analysis requires an authorized case-level export of the original run's extracted fields, grounding decisions and label comparisons.
