# Evidence and provenance

This directory separates verification evidence from application source. Only reviewed documentation,
synthetic input and minimal frozen regression sources are published; generated runs remain local or
in CI artifact storage.

- [B1 speech verification](b1/README.md): real Gnani/Ollama measurements and the explicitly synthetic 8-second Hindi WAV.
- [B2 intake verification](b2/README.md): real/fake conversations, restart recovery and historical 20-run stage latencies.
- [B2 follow-up](b2-followup/README.md): harder/held-out evaluation, thinking trials, attempt trails and latency limitations.
- `b2-followup/baseline/`: frozen input sources and hashes needed to reproduce the before/after comparison; do not edit them.
- [F0 checkpoint](f0/accepted/README.md): historical frontend evidence notes.
- [Character artwork](character-artwork.md) and [synthetic portraits](sample-portraits.md): origin and intended use of runtime images.

JSON run reports, screenshots, video, MP3 output, publication audits and ZIPNET captures may exist
locally but are ignored. A note referencing a local file is not a claim that the file was published.
Runtime images live in `../frontend/public/`; no real-person case photo is published here.

See [project status](../docs/project-status.md) for current readiness. Historical counts describe
their checkpoint and do not replace the latest validation results.
