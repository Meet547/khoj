# Extraction evaluation, version 1

Each JSONL row has `id`, `transcript`, `lang`, `category`, `intent`, and `expected_fields`.
Each expected field has `name`, English `value`, and original-script `evidence`. Optional
`aliases` explicitly annotate equally acceptable translated values. They affect scoring only;
the production grounding/merge code does not read these labels. Compare numbers without
optional year/age unit wording. Other values are case/punctuation normalized; broad semantic
judging is deliberately not used.

The 30 handwritten seed cases cover Hindi (8), English (8), Hinglish (8), Marathi (6), including
code mixing, rambling, missing/wrong details, noise-like STT artifacts, ambiguous names,
explicit spelling variants, corrections, and prompt injection. Extend this dataset with more
reviewed examples; this small set cannot establish production-wide accuracy.

From the backend directory:

```sh
uv run python scripts/eval_extraction.py --fake
uv run python scripts/eval_extraction.py --models chain --output evals/extraction/report.json
uv run python scripts/eval_extraction.py --models gemma4:31b,gpt-oss:20b
```

`chain` uses `config/models.yaml`, including Indic overrides and fallbacks. A named model runs
alone so its accuracy can be compared. Reports include dataset/prompt hashes, per-language
chain, field precision/recall/F1, raw and kept-field hallucination rates, failures, and case-level
mismatches. Rates count extra or incorrect name/value field pairs. Missing fields reduce recall.
The command fails for any kept false positive or provider failure, enforcing the CI target 0.

`--fake` uses canned expected fields plus one intentionally unsupported hallucination on every
case. This is a deterministic grounding/metric regression check, explicitly labelled
`fake_harness`. It is not a model accuracy result. The separate real-provider report is labelled
`live`. Supported translation synonyms were annotated explicitly after inspecting initial
scoring mismatches; they do not turn off grounding or accept unrelated field values.

## B2 follow-up: frozen development and held-out splits

`cases.v1.jsonl` remains the original 30 tuned cases. `development.v2.jsonl` retains those
rows and adds seven, for 37 cases. `heldout.v1.jsonl` has 35 new cases, never used to tune
prompts. All seven requested diagnostic categories have at least five cases in each split.
Hinglish is a cross-cutting category, so totals overlap. `followup-splits.json` freezes file
hashes, membership, labels and the prompt hash before the follow-up provider runs. Do not
rewrite held-out labels or add post-hoc aliases to obtain a pass; create a new version when
reviewing/expanding annotations.

The default runner now uses the expanded development set. Include held-out evaluation with:

```sh
uv run python scripts/eval_extraction.py --heldout evals/extraction/heldout.v1.jsonl
uv run python scripts/eval_extraction.py --fake --heldout evals/extraction/heldout.v1.jsonl
```

Reports include per-category, per-language, category × language, and per-split F1 and strict
hallucination counts, plus every scored case and attempt. The legacy `results[model][lang]`
shape is retained. F1 is null when both labels and predictions contain no positive fields;
correct abstention counts evaluate injection/conflict cases instead of inventing a positive F1.
The strict metric counts unmatched name/value pairs; it can penalize a valid paraphrase not
included in frozen aliases. Mismatch evidence is retained for separate review. The live
held-out zero-FP gate currently fails on three such scored mismatches; fake CI success is a
harness regression check, not evidence of model quality.

Thinking comparison (20 fixed paired development inputs, randomized arm ordering):

```sh
uv run python scripts/benchmark_extraction.py --arms false,true --attempt-timeout 90 \
  --output ../artifacts/b2-followup/think-paired-20.json
```

The 90-second override is only for the uncensored thinking experiment. Production defaults to
6 seconds per attempt in `config/models.yaml`; timeout moves directly to the next model.
`think_by_model` prevents Gemma inheriting a GPT-OSS named level. Models with boolean controls
receive booleans (Gemma is explicitly false), while GPT-OSS retains its valid named levels.

[Measured before/after report](../../../artifacts/b2-followup/README.md) preserves the missing
historical trace limitation and lists every newly observed slow run with model/attempt timing.
