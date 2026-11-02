import { test } from 'vitest';
import assert from 'node:assert/strict';
import { extractDemoDescription } from '@/mocks/data/extract';
test('one narrative yields known details and leaves unstated fields unknown', () => {
  const d = extractDemoDescription(
    'My brother Rahul Sharma is about 24 years old. He speaks Hindi and English. He was wearing a blue shirt and black trousers. He has a scar on his left eyebrow. He was last seen at New Delhi station on Friday evening.',
  );
  assert.equal(d.name, 'Rahul Sharma');
  assert.equal(d.gender, 'Male');
  assert.equal(d.age, 'about 24 years old');
  assert.equal(d.language, 'Hindi, English');
  assert.equal(d.clothing, 'a blue shirt and black trousers');
  assert.equal(d.place, 'New Delhi station');
  assert.equal(d.time, 'Friday evening');
  assert.equal(d.conditions, undefined);
  assert.ok(d.marks.includes('left eyebrow'));
  const sparse = extractDemoDescription(
    'I found a person near the bus stop. I do not know their name or age.',
  );
  assert.equal(sparse.name, undefined);
  assert.equal(sparse.age, undefined);
  assert.equal(sparse.gender, undefined);
  assert.equal(sparse.language, undefined);
  assert.equal(sparse.clothing, undefined);
});
test('explicit negative details are preserved and cannot confirm identity', () => {
  const d = extractDemoDescription(
    'A woman about 40 years old. No visible scars or tattoos. She speaks Tamil.',
  );
  assert.equal(d.gender, 'Female');
  assert.match(d.marks, /No visible scars/);
  assert.equal(d.name, undefined);
  assert.equal(d.place, undefined);
});

test('Hindi narratives preserve names, location, time and identifying-mark context', () => {
  const d = extractDemoDescription(
    'मेरा भाई राहुल शर्मा लगभग 24 साल का है। वह हिंदी बोलता है। उसकी बाईं भौंह पर निशान है। उसे आखिरी बार नई दिल्ली स्टेशन पर शुक्रवार शाम देखा गया था।',
  );
  assert.equal(d.name, 'राहुल शर्मा');
  assert.equal(d.age, '24 साल');
  assert.equal(d.language, 'हिंदी');
  assert.match(d.marks, /बाईं भौंह/);
  assert.equal(d.place, 'नई दिल्ली स्टेशन');
  assert.equal(d.time, 'शुक्रवार शाम');
  assert.equal(d.clothing, undefined);
});
