Owner-labelled, unreviewed held-out labels. Promotion blocked pending reviewer sign-off.

# Age v2 held-out evaluation

- Preregistration SHA-256 `3b7fad2511507ea255e5981dcbf69b353a25e8c2549be7a1e218c983fab088af`
- Extractions 100/120
- Ollama chat attempts 103/170
- Gnani requests 0
- Default schema v1
- Primary case IDs heldout-v2-en-001, heldout-v2-en-002, heldout-v2-en-003, heldout-v2-en-004, heldout-v2-en-005, heldout-v2-en-006, heldout-v2-en-007, heldout-v2-en-008, heldout-v2-en-009, heldout-v2-en-010, heldout-v2-en-011, heldout-v2-en-012, heldout-v2-en-013, heldout-v2-en-014, heldout-v2-en-015, heldout-v2-hi-001, heldout-v2-hi-002, heldout-v2-hi-003, heldout-v2-hi-004, heldout-v2-hi-005, heldout-v2-hi-006, heldout-v2-hi-007, heldout-v2-hi-008, heldout-v2-hi-009, heldout-v2-hi-010, heldout-v2-hi-011, heldout-v2-hi-012, heldout-v2-hi-013, heldout-v2-hi-014, heldout-v2-hi-015, heldout-v2-hinglish-001, heldout-v2-hinglish-002, heldout-v2-hinglish-003, heldout-v2-hinglish-004, heldout-v2-hinglish-005, heldout-v2-hinglish-006, heldout-v2-hinglish-007, heldout-v2-hinglish-008, heldout-v2-hinglish-009, heldout-v2-hinglish-010, heldout-v2-hinglish-011, heldout-v2-hinglish-012, heldout-v2-hinglish-013, heldout-v2-hinglish-014, heldout-v2-hinglish-015

## Age

- v1 overall (n=45) — recall 47.6% (10/21), precision 50.0% (10/20)
- v1 en (n=15) — recall 57.1% (4/7), precision 66.7% (4/6)
- v1 hi (n=15) — recall 37.5% (3/8), precision 37.5% (3/8)
- v1 hinglish (n=15) — recall 50.0% (3/6), precision 50.0% (3/6)
- v2 overall (n=45) — recall 71.4% (15/21), precision 100.0% (15/15)
- v2 en (n=15) — recall 71.4% (5/7), precision 100.0% (5/5)
- v2 hi (n=15) — recall 75.0% (6/8), precision 100.0% (6/6)
- v2 hinglish (n=15) — recall 66.7% (4/6), precision 100.0% (4/4)

## Other fields

- name, v1 — recall 66.7% (30/45), exact accuracy 66.7% (30/45), wrong values 15
- name, v2 — recall 97.8% (44/45), exact accuracy 97.8% (44/45), wrong values 0
- relation, v1 — recall 78.6% (11/14), exact accuracy 93.3% (42/45), wrong values 3
- relation, v2 — recall 78.6% (11/14), exact accuracy 93.3% (42/45), wrong values 3
- gender, v1 — recall 33.3% (3/9), exact accuracy 86.7% (39/45), wrong values 3
- gender, v2 — recall 33.3% (3/9), exact accuracy 86.7% (39/45), wrong values 3
- last_seen_place, v1 — recall 57.1% (8/14), exact accuracy 86.7% (39/45), wrong values 6
- last_seen_place, v2 — recall 64.3% (9/14), exact accuracy 88.9% (40/45), wrong values 5
- last_seen_time, v1 — recall 42.9% (6/14), exact accuracy 80.0% (36/45), wrong values 8
- last_seen_time, v2 — recall 50.0% (7/14), exact accuracy 84.4% (38/45), wrong values 7
- height_build, v1 — recall 16.7% (1/6), exact accuracy 88.9% (40/45), wrong values 5
- height_build, v2 — recall 33.3% (2/6), exact accuracy 91.1% (41/45), wrong values 4
- marks, v1 — recall 70.0% (7/10), exact accuracy 93.3% (42/45), wrong values 3
- marks, v2 — recall 70.0% (7/10), exact accuracy 93.3% (42/45), wrong values 3
- clothing, v1 — recall 100.0% (12/12), exact accuracy 100.0% (45/45), wrong values 0
- clothing, v2 — recall 91.7% (11/12), exact accuracy 97.8% (44/45), wrong values 1
- language_spoken, v1 — recall 100.0% (7/7), exact accuracy 100.0% (45/45), wrong values 0
- language_spoken, v2 — recall 100.0% (7/7), exact accuracy 100.0% (45/45), wrong values 0
- health_or_special_needs, v1 — recall 83.3% (5/6), exact accuracy 97.8% (44/45), wrong values 1
- health_or_special_needs, v2 — recall 66.7% (4/6), exact accuracy 95.6% (43/45), wrong values 2

## Repeat spread

- heldout-v2-en-009 — 0/2 correct, 0/2 emitted, bound spread unavailable
- heldout-v2-en-010 — 0/2 correct, 0/2 emitted, bound spread unavailable
- heldout-v2-en-011 — 0/2 correct, 0/2 emitted, bound spread unavailable
- heldout-v2-en-012 — 0/2 correct, 0/2 emitted, bound spread unavailable
- heldout-v2-en-013 — 0/2 correct, 0/2 emitted, bound spread unavailable

## Grounding and model failures

- v1 — quote_missing 0, number_missing 0, model unavailable 0
- v2 — quote_missing 0, number_missing 6, model unavailable 0
- v2 repeat — quote_missing 2, number_missing 2, model unavailable 0

## Promotion

- Age recall at least 75% — unmet
- All other field recall drops at most five points — unmet
- Zero v2 gender wrong values — unmet
- Reviewer sign-off — unmet

`promotion_blocked: unreviewed labels`
