# Gnani synthetic-to-STT round trip

Source: Sarvam TTS, model bulbul v4 flash, preset voices, `source=sarvam_tts`, `human_speaker=false`.
Terms confirmed by the owner on 3 November 2026.
Synthetic-to-STT round trip. Not human speech. Not valid for accuracy claims about real users.

## Sarvam provider presets

Counts cover the prepared manifest, including unscored split segments.

- `aparna_hi_customer` · 7
- `arnab_bn_conversation` · 7
- `bhavik_gu_conversation` · 3
- `chaitra_kn_conversation` · 8
- `chetan_kn_conversation` · 8
- `dev_en_conversational` · 5
- `gokul_ta_narration` · 8
- `ishita_en_customer` · 5
- `ishita_enhi_customer` · 8
- `ishita_mr_conversational` · 9
- `kavitha_te_conversation` · 6
- `mani_hi_conversational` · 8
- `nilesh_mr_conversation` · 9
- `pooja` · 9
- `pooja_gu_conversational` · 2
- `pooja_te_conversation` · 6
- `ritu_hi_conversation` · 7
- `ritu_mr_narration` · 6
- `roopa_bn_conversational` · 7
- `roopa_en_conversational` · 5
- `roopa_hi_conversational` · 7
- `shalini_enhi_companion` · 9
- `shubh` · 8
- `shubh_enhi_companion` · 8
- `shubh_hi_customer` · 6
- `simran_en_conversation` · 5
- `simran_enhi_customer` · 7
- `tarun_te_narration` · 5
- `vijay_ta_narration` · 8

## Gnani request configuration

- STT model sent · prisma-v3.0.
- 141 eligible clips, 141 clip results, 141 HTTP attempts of the 300-request budget. Attempts include production retries.
- Punjabi had no clips. The 55 split segments were excluded.
- bn · `bn-IN,en-IN`
- en · `en-IN,hi-IN`
- gu · `gu-IN,en-IN`
- hi · `hi-IN,en-IN`
- hinglish · `hi-IN,en-IN`
- kn · `kn-IN,en-IN`
- ml · `ml-IN,en-IN`
- mr · `mr-IN,en-IN`
- ta · `ta-IN,en-IN`
- te · `te-IN,en-IN`

## Scoring

Scores measure how Gnani recognises Sarvam-generated speech. They do not estimate performance on human speech.
Cell sizes are small (141 clips across 10 languages).
Reference texts are draft_unverified until native review.
Split segments were not scored, because their reference covers the whole item.

WER and CER pool edit counts and reference lengths within each group. CER counts Unicode code points including collapsed spaces. Empty and truncated responses are scored as returned. Failed requests are excluded from metric denominators.

- Overall · n=141 · WER 23.51% · CER 16.67%
- Median per-clip WER 11.11% · median per-clip CER 7.41%.

### By language

- bn · n=10 · WER 10.95% · CER 5.92% · eligible 10
- en · n=20 · WER 5.47% · CER 3.03% · eligible 20
- gu · n=1 · WER 5.41% · CER 5.06% · eligible 1
- hi · n=26 · WER 9.78% · CER 8.53% · eligible 26
- hinglish · n=28 · WER 69.55% · CER 53.05% · eligible 28
- kn · n=10 · WER 7.32% · CER 6.25% · eligible 10
- ml · n=9 · WER 14.94% · CER 9.40% · eligible 9
- mr · n=18 · WER 9.38% · CER 6.62% · eligible 18
- ta · n=10 · WER 18.21% · CER 9.06% · eligible 10
- te · n=9 · WER 20.00% · CER 7.83% · eligible 9

### By category

- clean · n=17 · WER 22.09% · CER 14.68% · eligible 17
- code_mixed · n=17 · WER 30.11% · CER 22.51% · eligible 17
- conflict · n=15 · WER 20.76% · CER 14.26% · eligible 15
- correction · n=17 · WER 27.00% · CER 20.22% · eligible 17
- dialect · n=14 · WER 22.39% · CER 15.26% · eligible 14
- emotional · n=13 · WER 13.15% · CER 9.18% · eligible 13
- injection · n=16 · WER 18.84% · CER 12.91% · eligible 16
- stt_noise · n=16 · WER 33.17% · CER 25.53% · eligible 16
- unclear · n=16 · WER 25.32% · CER 16.44% · eligible 16

### By language and category

- bn / clean · n=2 · WER 12.77% · CER 4.28% · eligible 2
- bn / code_mixed · n=1 · WER 15.79% · CER 13.78% · eligible 1
- bn / conflict · n=1 · WER 11.76% · CER 5.21% · eligible 1
- bn / correction · n=1 · WER 11.11% · CER 6.13% · eligible 1
- bn / dialect · n=1 · WER 8.82% · CER 4.42% · eligible 1
- bn / emotional · n=1 · WER 8.89% · CER 4.82% · eligible 1
- bn / injection · n=1 · WER 9.76% · CER 3.07% · eligible 1
- bn / stt_noise · n=1 · WER 20.83% · CER 13.28% · eligible 1
- bn / unclear · n=1 · WER 0.00% · CER 0.00% · eligible 1
- en / clean · n=3 · WER 3.88% · CER 1.65% · eligible 3
- en / code_mixed · n=2 · WER 5.43% · CER 2.90% · eligible 2
- en / conflict · n=2 · WER 2.30% · CER 0.94% · eligible 2
- en / correction · n=2 · WER 4.62% · CER 1.85% · eligible 2
- en / dialect · n=2 · WER 1.20% · CER 0.73% · eligible 2
- en / emotional · n=3 · WER 7.46% · CER 4.17% · eligible 3
- en / injection · n=2 · WER 5.68% · CER 1.89% · eligible 2
- en / stt_noise · n=2 · WER 13.73% · CER 11.40% · eligible 2
- en / unclear · n=2 · WER 7.23% · CER 4.16% · eligible 2
- gu / conflict · n=1 · WER 5.41% · CER 5.06% · eligible 1
- hi / clean · n=3 · WER 5.38% · CER 4.42% · eligible 3
- hi / code_mixed · n=3 · WER 13.04% · CER 11.49% · eligible 3
- hi / conflict · n=2 · WER 8.51% · CER 6.27% · eligible 2
- hi / correction · n=3 · WER 7.14% · CER 6.89% · eligible 3
- hi / dialect · n=3 · WER 9.60% · CER 5.80% · eligible 3
- hi / emotional · n=3 · WER 7.19% · CER 7.50% · eligible 3
- hi / injection · n=3 · WER 14.65% · CER 12.72% · eligible 3
- hi / stt_noise · n=3 · WER 11.46% · CER 13.35% · eligible 3
- hi / unclear · n=3 · WER 8.73% · CER 6.10% · eligible 3
- hinglish / clean · n=3 · WER 70.69% · CER 53.90% · eligible 3
- hinglish / code_mixed · n=5 · WER 65.00% · CER 47.91% · eligible 5
- hinglish / conflict · n=3 · WER 67.74% · CER 51.77% · eligible 3
- hinglish / correction · n=4 · WER 71.43% · CER 56.08% · eligible 4
- hinglish / dialect · n=2 · WER 80.21% · CER 63.32% · eligible 2
- hinglish / emotional · n=1 · WER 72.97% · CER 58.06% · eligible 1
- hinglish / injection · n=3 · WER 49.66% · CER 38.58% · eligible 3
- hinglish / stt_noise · n=4 · WER 72.50% · CER 57.10% · eligible 4
- hinglish / unclear · n=3 · WER 87.50% · CER 62.73% · eligible 3
- kn / clean · n=1 · WER 8.00% · CER 6.82% · eligible 1
- kn / code_mixed · n=1 · WER 9.68% · CER 12.33% · eligible 1
- kn / conflict · n=1 · WER 3.33% · CER 3.23% · eligible 1
- kn / correction · n=1 · WER 5.41% · CER 4.31% · eligible 1
- kn / dialect · n=1 · WER 7.41% · CER 4.40% · eligible 1
- kn / emotional · n=1 · WER 6.45% · CER 6.36% · eligible 1
- kn / injection · n=2 · WER 7.35% · CER 6.02% · eligible 2
- kn / stt_noise · n=1 · WER 21.05% · CER 11.85% · eligible 1
- kn / unclear · n=1 · WER 0.00% · CER 0.00% · eligible 1
- ml / clean · n=1 · WER 31.58% · CER 12.32% · eligible 1
- ml / code_mixed · n=1 · WER 21.88% · CER 15.86% · eligible 1
- ml / conflict · n=1 · WER 24.14% · CER 10.13% · eligible 1
- ml / correction · n=1 · WER 8.70% · CER 15.48% · eligible 1
- ml / dialect · n=1 · WER 14.29% · CER 7.83% · eligible 1
- ml / emotional · n=1 · WER 8.33% · CER 2.80% · eligible 1
- ml / injection · n=1 · WER 12.90% · CER 8.06% · eligible 1
- ml / stt_noise · n=1 · WER 15.79% · CER 15.27% · eligible 1
- ml / unclear · n=1 · WER 0.00% · CER 0.00% · eligible 1
- mr / clean · n=2 · WER 6.15% · CER 2.62% · eligible 2
- mr / code_mixed · n=2 · WER 14.08% · CER 12.71% · eligible 2
- mr / conflict · n=2 · WER 4.82% · CER 5.00% · eligible 2
- mr / correction · n=2 · WER 9.84% · CER 8.72% · eligible 2
- mr / dialect · n=2 · WER 14.71% · CER 6.93% · eligible 2
- mr / emotional · n=2 · WER 10.11% · CER 6.26% · eligible 2
- mr / injection · n=2 · WER 7.69% · CER 5.52% · eligible 2
- mr / stt_noise · n=2 · WER 20.00% · CER 12.35% · eligible 2
- mr / unclear · n=2 · WER 1.45% · CER 0.33% · eligible 2
- ta / clean · n=1 · WER 4.35% · CER 1.71% · eligible 1
- ta / code_mixed · n=1 · WER 26.67% · CER 16.24% · eligible 1
- ta / conflict · n=1 · WER 6.67% · CER 3.83% · eligible 1
- ta / correction · n=2 · WER 25.00% · CER 13.92% · eligible 2
- ta / dialect · n=1 · WER 10.34% · CER 6.94% · eligible 1
- ta / emotional · n=1 · WER 23.33% · CER 9.46% · eligible 1
- ta / injection · n=1 · WER 6.06% · CER 4.74% · eligible 1
- ta / stt_noise · n=1 · WER 33.33% · CER 14.41% · eligible 1
- ta / unclear · n=1 · WER 25.93% · CER 5.78% · eligible 1
- te / clean · n=1 · WER 16.00% · CER 8.28% · eligible 1
- te / code_mixed · n=1 · WER 31.03% · CER 17.67% · eligible 1
- te / conflict · n=1 · WER 20.00% · CER 5.10% · eligible 1
- te / correction · n=1 · WER 22.22% · CER 6.36% · eligible 1
- te / dialect · n=1 · WER 14.29% · CER 5.24% · eligible 1
- te / injection · n=1 · WER 18.18% · CER 6.58% · eligible 1
- te / stt_noise · n=1 · WER 23.81% · CER 13.48% · eligible 1
- te / unclear · n=2 · WER 17.02% · CER 3.26% · eligible 2

### Five worst clips by WER

- hinglish-006 · WER 90.00% · CER 62.87%
- hinglish-007 · WER 88.37% · CER 63.76%
- hinglish-005 · WER 83.78% · CER 61.38%
- hinglish-027 · WER 83.02% · CER 67.53%
- hinglish-015 · WER 77.50% · CER 61.19%

## Transcript outcomes

- Empty · 0.
- Truncated · 0.
- Failed · 0.
