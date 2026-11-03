# Age and language normalisation rescore

Preregistration SHA-256 `8a95b25fbe927ee919df3113bb117c5a699eece4ef97fae57e4ce119a8cc25ee`.

Zero provider requests. Development pairs are excluded separately by field.
8 of 8 reference language mismatches resolve (bn-009, hi-017, hi-021, kn-006, mr-003, mr-009, mr-012, ta-009).
en-002 remains a transcript-side language omission. bn-009 remains a transcript-side age mismatch.

## Native-script expected labels across the source corpus

- name. 12 of 166.
- relation. 0 of 166.
- gender. 0 of 54.
- age. 0 of 166.
- height_build. 0 of 24.
- marks. 0 of 21.
- language_spoken. 12 of 19.
- clothing. 0 of 130.
- last_seen_place. 0 of 166.
- last_seen_time. 0 of 148.
- health_or_special_needs. 0 of 7.

## age test set

- reference, Overall, n=101. original recall 0.00% (0/101), precision 0.00% (0/101) · corrected recall 79.21% (80/101), precision 79.21% (80/101)
- reference, lang=en, n=7. original recall 0.00% (0/7), precision 0.00% (0/7) · corrected recall 100.00% (7/7), precision 100.00% (7/7)
- reference, lang=gu, n=1. original recall 0.00% (0/1), precision 0.00% (0/1) · corrected recall 100.00% (1/1), precision 100.00% (1/1)
- reference, lang=hi, n=23. original recall 0.00% (0/23), precision 0.00% (0/23) · corrected recall 100.00% (23/23), precision 100.00% (23/23)
- reference, lang=hinglish, n=25. original recall 0.00% (0/25), precision 0.00% (0/25) · corrected recall 16.00% (4/25), precision 16.00% (4/25)
- reference, lang=kn, n=9. original recall 0.00% (0/9), precision 0.00% (0/9) · corrected recall 100.00% (9/9), precision 100.00% (9/9)
- reference, lang=ml, n=8. original recall 0.00% (0/8), precision 0.00% (0/8) · corrected recall 100.00% (8/8), precision 100.00% (8/8)
- reference, lang=mr, n=16. original recall 0.00% (0/16), precision 0.00% (0/16) · corrected recall 100.00% (16/16), precision 100.00% (16/16)
- reference, lang=ta, n=9. original recall 0.00% (0/9), precision 0.00% (0/9) · corrected recall 100.00% (9/9), precision 100.00% (9/9)
- reference, lang=te, n=3. original recall 0.00% (0/3), precision 0.00% (0/3) · corrected recall 100.00% (3/3), precision 100.00% (3/3)
- reference, category=clean, n=14. original recall 0.00% (0/14), precision 0.00% (0/14) · corrected recall 78.57% (11/14), precision 78.57% (11/14)
- reference, category=code_mixed, n=14. original recall 0.00% (0/14), precision 0.00% (0/14) · corrected recall 64.29% (9/14), precision 64.29% (9/14)
- reference, category=conflict, n=11. original recall 0.00% (0/11), precision 0.00% (0/11) · corrected recall 72.73% (8/11), precision 72.73% (8/11)
- reference, category=correction, n=14. original recall 0.00% (0/14), precision 0.00% (0/14) · corrected recall 100.00% (14/14), precision 100.00% (14/14)
- reference, category=dialect, n=12. original recall 0.00% (0/12), precision 0.00% (0/12) · corrected recall 83.33% (10/12), precision 83.33% (10/12)
- reference, category=emotional, n=9. original recall 0.00% (0/9), precision 0.00% (0/9) · corrected recall 88.89% (8/9), precision 88.89% (8/9)
- reference, category=injection, n=14. original recall 0.00% (0/14), precision 0.00% (0/14) · corrected recall 78.57% (11/14), precision 78.57% (11/14)
- reference, category=stt_noise, n=13. original recall 0.00% (0/13), precision 0.00% (0/13) · corrected recall 69.23% (9/13), precision 69.23% (9/13)
- transcript, Overall, n=101. original recall 0.00% (0/101), precision 0.00% (0/101) · corrected recall 79.21% (80/101), precision 79.21% (80/101)
- transcript, lang=en, n=7. original recall 0.00% (0/7), precision 0.00% (0/7) · corrected recall 100.00% (7/7), precision 100.00% (7/7)
- transcript, lang=gu, n=1. original recall 0.00% (0/1), precision 0.00% (0/1) · corrected recall 100.00% (1/1), precision 100.00% (1/1)
- transcript, lang=hi, n=23. original recall 0.00% (0/23), precision 0.00% (0/23) · corrected recall 100.00% (23/23), precision 100.00% (23/23)
- transcript, lang=hinglish, n=25. original recall 0.00% (0/25), precision 0.00% (0/25) · corrected recall 24.00% (6/25), precision 24.00% (6/25)
- transcript, lang=kn, n=9. original recall 0.00% (0/9), precision 0.00% (0/9) · corrected recall 100.00% (9/9), precision 100.00% (9/9)
- transcript, lang=ml, n=8. original recall 0.00% (0/8), precision 0.00% (0/8) · corrected recall 100.00% (8/8), precision 100.00% (8/8)
- transcript, lang=mr, n=16. original recall 0.00% (0/16), precision 0.00% (0/16) · corrected recall 87.50% (14/16), precision 87.50% (14/16)
- transcript, lang=ta, n=9. original recall 0.00% (0/9), precision 0.00% (0/9) · corrected recall 100.00% (9/9), precision 100.00% (9/9)
- transcript, lang=te, n=3. original recall 0.00% (0/3), precision 0.00% (0/3) · corrected recall 100.00% (3/3), precision 100.00% (3/3)
- transcript, category=clean, n=14. original recall 0.00% (0/14), precision 0.00% (0/14) · corrected recall 78.57% (11/14), precision 78.57% (11/14)
- transcript, category=code_mixed, n=14. original recall 0.00% (0/14), precision 0.00% (0/14) · corrected recall 64.29% (9/14), precision 64.29% (9/14)
- transcript, category=conflict, n=11. original recall 0.00% (0/11), precision 0.00% (0/11) · corrected recall 81.82% (9/11), precision 81.82% (9/11)
- transcript, category=correction, n=14. original recall 0.00% (0/14), precision 0.00% (0/14) · corrected recall 100.00% (14/14), precision 100.00% (14/14)
- transcript, category=dialect, n=12. original recall 0.00% (0/12), precision 0.00% (0/12) · corrected recall 75.00% (9/12), precision 75.00% (9/12)
- transcript, category=emotional, n=9. original recall 0.00% (0/9), precision 0.00% (0/9) · corrected recall 88.89% (8/9), precision 88.89% (8/9)
- transcript, category=injection, n=14. original recall 0.00% (0/14), precision 0.00% (0/14) · corrected recall 78.57% (11/14), precision 78.57% (11/14)
- transcript, category=stt_noise, n=13. original recall 0.00% (0/13), precision 0.00% (0/13) · corrected recall 69.23% (9/13), precision 69.23% (9/13)

## language_spoken test set

- reference, Overall, n=0. original recall unavailable (0/0), precision unavailable (0/0) · corrected recall unavailable (0/0), precision unavailable (0/0)
- transcript, Overall, n=0. original recall unavailable (0/0), precision unavailable (0/0) · corrected recall unavailable (0/0), precision unavailable (0/0)

