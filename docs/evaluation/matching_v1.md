# Matching prototype v1

Seed 20261103. The prototype ranks found reports for each missing query. It uses fictional data and deterministic scoring.

The requested 50 two-record pairs and 150 distractors imply 250 records. The 200-record core uses the first 100 distractors. The 250-record stress run adds the remaining 50. Both use the same 50 queries and true matches.

Distractors copy one or two fields from a fixed set of six identity or location fields of an anchor report. Their state is shared for blocking. Other independently generated attributes can coincide.

Blocking uses state and the found record kind. Scores are additive, with ties broken by ascending fictional ID. Strong begins at 62 points and Possible at 37. Strong precision includes every Strong query-candidate link. The rank histogram tracks the true found report.

| Corpus | Noise | Recall@5 |
|---|---|---:|
| Core | Overall | 50/50 (100.00%) |
| Core | none | 17/17 (100.00%) |
| Core | one | 17/17 (100.00%) |
| Core | two or more | 16/16 (100.00%) |
| Stress | Overall | 50/50 (100.00%) |
| Stress | none | 17/17 (100.00%) |
| Stress | one | 17/17 (100.00%) |
| Stress | two or more | 16/16 (100.00%) |

## Core

- Records 200. Queries 50. Indexed found reports 150.
- Strong precision 50/50 (100.00%). Distractors reaching Strong 0 (0 links).
- Candidate bands. Strong 50, Possible 22, Weak 1428.
- True-match rank histogram. 1 → 50.
- Every reason maps to a signal key. Yes.
- Recall@5 reaches 75%. Yes.

## Stress

- Records 250. Queries 50. Indexed found reports 200.
- Strong precision 50/50 (100.00%). Distractors reaching Strong 0 (0 links).
- Candidate bands. Strong 50, Possible 32, Weak 1918.
- True-match rank histogram. 1 → 50.
- Every reason maps to a signal key. Yes.
- Recall@5 reaches 75%. Yes.

We designed these records. They show that the ranking logic works on this fixture and do not measure ZIPNET accuracy.

Gnani requests 0. Ollama requests 0.
