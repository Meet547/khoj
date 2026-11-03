# Held-out text evaluation v2

Frozen on 2026-11-03 (Asia/Kolkata). The set contains 45 newly authored fictional text cases. Case writing used only field names and types from the current items schema. Prior evaluation results were kept out of the authoring process.

| File | SHA-256 |
|---|---|
| `cases.jsonl` | `1e3832f4cd3f0be29f5fdb3a6a9a813c29946019147950a91b13365488a6c993` |
| `labels.jsonl` | `86628bbf0f78f5c5249e56cea46f06faa42f8e343346d31810d07d75268b6366` |

Both JSONL files are frozen byte for byte. Any later change requires a new version folder and manifest.

Join the files by `item_id`. Cases provide `lang`, `category`, and `text`. Labels use the existing `expected` field names. Each populated label has a `value` and a verbatim `evidence` quote. Age values contain inclusive integer `min` and `max` bounds. Gender uses `male`, `female`, or `unknown`. Explicit uncertainty about gender is labelled `unknown`. Fields without sufficient evidence are null, and the labels make no demographic inference from a name or pronoun. Names and places retain their source spelling.

For explicit corrections, label the final affirmed value and quote that clause. For unresolved contradictions, leave the affected field null and record both quotes in `conflicts`. Vague times retain the stated precision. The dataset contains no audio, photos, phone numbers, or real police records. No extraction was run.

Reviewer status: caveat accepted in writing by owner, 2026-11-03 (approval: "Approved: run v2 under caveat, promotion blocked until reviewer sign-off")
