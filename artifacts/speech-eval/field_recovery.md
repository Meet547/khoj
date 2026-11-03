# Synthetic speech field recovery

Preregistration SHA-256 `4414eb309b3b06a69cbb0549e4f5bc1c3f7860ad33ea2e2af56608e142c48a2f`.

135 of 141 complete pairs. 272 extraction invocations and 282 Ollama chat attempts. 0 Gnani requests.
The durable intake turn ran with an empty draft, no current question, and production model routing, prompt, schema and grounding. The local Redis usage ledger was unavailable. The run enforced an independent hard cap on invocations and provider attempts.
Reference labels are draft_unverified. The speech is Sarvam-generated, so results describe the pipeline on synthetic speech only. Cell sizes are small. The alias list affects the result and was fixed before scoring.
Differences are transcript minus reference. Provider failures in completed pairs count as zero recovery and zero predictions.

- Overall · n=135 · reference recall 60.23% (312/518), precision 60.23% (312/518) · transcript recall 55.41% (287/518), precision 55.84% (287/514) · Δ recall -4.83 pp, Δ precision -4.40 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0

## By language

- bn · n=10 · reference recall 59.52% (25/42), precision 59.52% (25/42) · transcript recall 54.76% (23/42), precision 56.10% (23/41) · Δ recall -4.76 pp, Δ precision -3.43 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- en · n=20 · reference recall 75.00% (57/76), precision 75.00% (57/76) · transcript recall 59.21% (45/76), precision 60.00% (45/75) · Δ recall -15.79 pp, Δ precision -15.00 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- gu · n=1 · reference recall 66.67% (2/3), precision 66.67% (2/3) · transcript recall 66.67% (2/3), precision 66.67% (2/3) · Δ recall +0.00 pp, Δ precision +0.00 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- hi · n=26 · reference recall 55.21% (53/96), precision 55.21% (53/96) · transcript recall 55.21% (53/96), precision 55.21% (53/96) · Δ recall +0.00 pp, Δ precision +0.00 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- hinglish · n=28 · reference recall 68.18% (75/110), precision 68.18% (75/110) · transcript recall 60.91% (67/110), precision 62.04% (67/108) · Δ recall -7.27 pp, Δ precision -6.14 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- kn · n=10 · reference recall 40.54% (15/37), precision 40.54% (15/37) · transcript recall 43.24% (16/37), precision 43.24% (16/37) · Δ recall +2.70 pp, Δ precision +2.70 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- ml · n=9 · reference recall 59.38% (19/32), precision 59.38% (19/32) · transcript recall 56.25% (18/32), precision 56.25% (18/32) · Δ recall -3.12 pp, Δ precision -3.12 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- mr · n=18 · reference recall 54.17% (39/72), precision 54.17% (39/72) · transcript recall 54.17% (39/72), precision 54.17% (39/72) · Δ recall +0.00 pp, Δ precision +0.00 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- ta · n=10 · reference recall 53.85% (21/39), precision 53.85% (21/39) · transcript recall 48.72% (19/39), precision 48.72% (19/39) · Δ recall -5.13 pp, Δ precision -5.13 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- te · n=3 · reference recall 54.55% (6/11), precision 54.55% (6/11) · transcript recall 45.45% (5/11), precision 45.45% (5/11) · Δ recall -9.09 pp, Δ precision -9.09 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0

## By category

- clean · n=16 · reference recall 65.79% (50/76), precision 65.79% (50/76) · transcript recall 57.89% (44/76), precision 57.89% (44/76) · Δ recall -7.89 pp, Δ precision -7.89 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- code_mixed · n=17 · reference recall 62.34% (48/77), precision 62.34% (48/77) · transcript recall 58.44% (45/77), precision 59.21% (45/76) · Δ recall -3.90 pp, Δ precision -3.13 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- conflict · n=14 · reference recall 57.14% (28/49), precision 57.14% (28/49) · transcript recall 48.98% (24/49), precision 48.98% (24/49) · Δ recall -8.16 pp, Δ precision -8.16 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- correction · n=17 · reference recall 63.86% (53/83), precision 63.86% (53/83) · transcript recall 59.04% (49/83), precision 59.76% (49/82) · Δ recall -4.82 pp, Δ precision -4.10 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- dialect · n=13 · reference recall 57.38% (35/61), precision 57.38% (35/61) · transcript recall 59.02% (36/61), precision 60.00% (36/60) · Δ recall +1.64 pp, Δ precision +2.62 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- emotional · n=13 · reference recall 65.52% (38/58), precision 65.52% (38/58) · transcript recall 62.07% (36/58), precision 62.07% (36/58) · Δ recall -3.45 pp, Δ precision -3.45 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- injection · n=15 · reference recall 65.15% (43/66), precision 65.15% (43/66) · transcript recall 60.61% (40/66), precision 61.54% (40/65) · Δ recall -4.55 pp, Δ precision -3.61 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- stt_noise · n=16 · reference recall 35.42% (17/48), precision 35.42% (17/48) · transcript recall 27.08% (13/48), precision 27.08% (13/48) · Δ recall -8.33 pp, Δ precision -8.33 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- unclear · n=14 · reference recall unavailable (0/0), precision unavailable (0/0) · transcript recall unavailable (0/0), precision unavailable (0/0) · Δ recall unavailable, Δ precision unavailable · quote drops 0/0 (reference/transcript) · blank drops 0/0

## By field

- name · n=135 · reference recall 76.86% (93/121), precision 76.86% (93/121) · transcript recall 61.98% (75/121), precision 61.98% (75/121) · Δ recall -14.88 pp, Δ precision -14.88 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- age · n=135 · reference recall 0.00% (0/121), precision 0.00% (0/121) · transcript recall 0.00% (0/121), precision 0.00% (0/121) · Δ recall +0.00 pp, Δ precision +0.00 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- gender · n=135 · reference recall 100.00% (37/37), precision 100.00% (37/37) · transcript recall 89.19% (33/37), precision 100.00% (33/33) · Δ recall -10.81 pp, Δ precision +0.00 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- marks · n=135 · reference recall 83.33% (10/12), precision 83.33% (10/12) · transcript recall 83.33% (10/12), precision 83.33% (10/12) · Δ recall +0.00 pp, Δ precision +0.00 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- last_seen_place · n=135 · reference recall 62.81% (76/121), precision 62.81% (76/121) · transcript recall 62.81% (76/121), precision 62.81% (76/121) · Δ recall +0.00 pp, Δ precision +0.00 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- clothing · n=135 · reference recall 97.80% (89/91), precision 97.80% (89/91) · transcript recall 95.60% (87/91), precision 94.57% (87/92) · Δ recall -2.20 pp, Δ precision -3.24 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0
- language_spoken · n=135 · reference recall 46.67% (7/15), precision 46.67% (7/15) · transcript recall 40.00% (6/15), precision 42.86% (6/14) · Δ recall -6.67 pp, Δ precision -3.81 pp · quote drops 0/0 (reference/transcript) · blank drops 0/0

## Five largest recall drops

- mr-011 · 50.00 pp
- en-014 · 40.00 pp
- en-001 · 33.33 pp
- en-012 · 33.33 pp
- hinglish-003 · 33.33 pp

## Extraction outcomes

- reference · ok 135
- transcript · ok 135

The run is partial. Aggregate scores use complete pairs only.
