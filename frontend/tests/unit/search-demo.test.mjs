import { test } from 'vitest';
import assert from 'node:assert/strict';
import { extractDemoDescription } from '@/mocks/data/extract';
import {
  buildSampleMatches,
  createSearchContext,
  demoProgress,
  DEMO_DONE_MS,
  sampleCohort,
  createSamplePreviewContext,
} from '@/features/search/demo';
const description =
  'My brother Rahul Sharma is about 24 years old. He speaks Hindi and English. He was wearing a blue shirt and black trousers. He has a scar on his left eyebrow. He was last seen at New Delhi station on Friday evening.';
const draft = { kind: 'missing', ...extractDemoDescription(description) };
test('the verified handoff preserves the description and a detached copy of the extracted details', () => {
  const c = createSearchContext(description, draft, {
    caseNo: 'KHOJ-2026-ABC123',
    verified: true,
    source: 'report',
  });
  assert.equal(c.description, description);
  assert.equal(c.caseNo, 'KHOJ-2026-ABC123');
  assert.equal(c.draft.name, 'Rahul Sharma');
  assert.equal(c.verified, true);
  c.draft.name = 'Changed';
  assert.equal(draft.name, 'Rahul Sharma');
});
test('no candidates are revealed before the demonstration finishes', () => {
  assert.deepEqual(demoProgress(0), { done: false, phase: 0, revealed: 0 });
  assert.equal(demoProgress(DEMO_DONE_MS - 1).revealed, 0);
  assert.equal(demoProgress(DEMO_DONE_MS).revealed, 1);
  assert.equal(demoProgress(DEMO_DONE_MS + 900).revealed, 2);
  assert.equal(demoProgress(DEMO_DONE_MS + 1800).revealed, 3);
  assert.equal(demoProgress(DEMO_DONE_MS + 100000).revealed, 3);
});
test('sample candidates are ranked with bounded evidence-based scores and age-appropriate photo cohorts', () => {
  const m = buildSampleMatches(draft, description);
  assert.equal(m.length, 3);
  assert.equal(m[0].row, 0);
  assert.equal(m[0].age, 24);
  assert.equal(m[0].cohort, 'adult');
  assert.ok(m[0].confidence > m[1].confidence);
  assert.ok(m[1].confidence >= m[2].confidence);
  for (const hit of m) {
    assert.ok(hit.confidence >= 0 && hit.confidence <= 99);
    assert.equal(
      hit.comparisons.reduce((sum, c) => sum + c.weight, 0),
      100,
    );
  }
  assert.equal(sampleCohort({ kind: 'missing', age: '9 years', fieldConfidence: {} }), 'child');
  assert.equal(sampleCohort({ kind: 'missing', age: '७० साल', fieldConfidence: {} }), 'senior');
  assert.equal(sampleCohort({ kind: 'missing', fieldConfidence: {} }, 'A lost child'), 'child');
});
test('missing evidence stays unscored and a single generic detail cannot produce high confidence', () => {
  const empty = buildSampleMatches({ kind: 'missing', fieldConfidence: {} });
  assert.ok(empty.every((m) => m.confidence === null));
  const one = buildSampleMatches({
    kind: 'missing',
    gender: 'Male',
    fieldConfidence: { gender: 1 },
  });
  assert.ok(one.every((m) => m.confidence < 40));
  const partial = buildSampleMatches({ kind: 'missing', age: '24', fieldConfidence: { age: 1 } });
  assert.ok(partial.every((m) => m.comparisons.find((c) => c.key === 'marks').score === null));
});
test('found-person reports cannot enter the match handoff or expose sample results', () => {
  const found = { kind: 'found', fieldConfidence: {} };
  assert.throws(() => createSearchContext('Found someone', found), /must not expose/);
  assert.throws(() => buildSampleMatches(found), /must not expose/);
});

test('the direct sample preview never claims phone verification or an official case', () => {
  const context = createSamplePreviewContext();
  assert.equal(context.demoOnly, true);
  assert.equal(context.verified, false);
  assert.equal(context.caseNo, undefined);
  assert.equal(context.id, 'SAMPLE-DEMO');
  assert.equal(buildSampleMatches(context.draft, context.description).length, 3);
});
