import type { PersonDraft } from '@/lib/api';
export interface SearchContext {
  version: 1;
  id: string;
  caseNo?: string;
  description: string;
  draft: PersonDraft;
  verified: boolean;
  demoOnly?: boolean;
  source: 'report' | 'search';
  startedAt: string;
  state?: string;
  district?: string;
}
export type SampleCohort = 'adult' | 'child' | 'senior';
export type ComparisonKey = 'age' | 'gender' | 'clothing' | 'language' | 'marks' | 'place' | 'time';
export interface Comparison {
  key: ComparisonKey;
  query?: string;
  record: string;
  score: number | null;
  weight: number;
}
export interface SampleMatch {
  id: string;
  cohort: SampleCohort;
  row: number;
  female: boolean;
  age: number;
  gender: string;
  clothing: string;
  language: string;
  marks: string;
  city: string;
  lastSeen: string;
  lastSeenAt: string;
  station: string;
  description: string;
  confidence: number | null;
  comparisons: Comparison[];
}
export const AGENT_PHASES = [
  { key: 'coordinator', at: 0, icon: 'route' },
  { key: 'records', at: 2400, icon: 'database' },
  { key: 'semantic', at: 5200, icon: 'scan' },
  { key: 'review', at: 8000, icon: 'shield' },
] as const;
export const DEMO_DONE_MS = 12000;
export const REVEAL_INTERVAL_MS = 900;
export function demoProgress(elapsed: number) {
  return {
    done: elapsed >= DEMO_DONE_MS,
    phase: Math.min(3, AGENT_PHASES.filter((p) => elapsed >= p.at).length - 1),
    revealed:
      elapsed < DEMO_DONE_MS
        ? 0
        : Math.min(3, 1 + Math.floor((elapsed - DEMO_DONE_MS) / REVEAL_INTERVAL_MS)),
  };
}
const normalize = (value: string) =>
  value
    .toLowerCase()
    .replace(/navy/g, 'blue')
    .replace(/spectacles|specs/g, 'glasses')
    .replace(/हिंदी|हिन्दी/g, 'hindi')
    .replace(/अंग्रेज़ी|अंग्रेजी/g, 'english')
    .replace(/बंगाली/g, 'bengali')
    .replace(/नील[ाीे]/g, 'blue')
    .replace(/कमीज|शर्ट/g, 'shirt')
    .replace(/काल[ाीे]/g, 'black')
    .replace(/पैंट/g, 'trousers')
    .replace(/नई दिल्ली/g, 'new delhi')
    .replace(/निशान/g, 'scar')
    .replace(/शुक्रवार/g, 'friday')
    .replace(/शनिवार/g, 'saturday')
    .replace(/रविवार/g, 'sunday')
    .replace(/शाम|evening/g, 'pm')
    .replace(/सुबह|morning/g, 'am')
    .replace(/बाईं/g, 'left')
    .replace(/भौंह/g, 'eyebrow')
    .replace(/[^\p{L}\p{N}\s]/gu, ' ');
const stop = new Set([
  'a',
  'an',
  'the',
  'on',
  'at',
  'in',
  'of',
  'his',
  'her',
  'their',
  'with',
  'and',
  'was',
  'is',
  'has',
  'he',
  'she',
  'wearing',
  'about',
  'approximately',
  'near',
  'station',
  'years',
  'old',
  'में',
  'पर',
  'है',
  'उसकी',
  'उसका',
]);
function tokens(value: string) {
  return new Set(
    normalize(value)
      .split(/\s+/)
      .filter((w) => w.length > 1 && !stop.has(w)),
  );
}
export function textSimilarity(query: string, record: string) {
  const q = tokens(query),
    r = tokens(record);
  if (!q.size) return 0;
  return [...q].filter((v) => r.has(v)).length / q.size;
}
function known(value: string | undefined) {
  return (
    !!value?.trim() &&
    !/^(not known|unknown|not mentioned|पता नहीं|नहीं बताया गया)$/i.test(value.trim())
  );
}
export function ageNumber(value: string | undefined) {
  if (!value) return;
  const n = Number(
    value.replace(/[०-९]/g, (d) => String('०१२३४५६७८९'.indexOf(d))).match(/\d{1,3}/)?.[0],
  );
  return Number.isFinite(n) && n > 0 && n <= 120 ? n : undefined;
}
export function sampleCohort(draft: PersonDraft, description = ''): SampleCohort {
  const age = ageNumber(draft.age);
  if (age === undefined && /\b(?:child|boy|girl|kid)\b|बच्चा|बच्ची|लड़का|लड़की/i.test(description))
    return 'child';
  if (
    age === undefined &&
    /\b(?:elderly|grandmother|grandfather)\b|बुज़ुर्ग|बुजुर्ग|दादी|दादा/i.test(description)
  )
    return 'senior';
  return age !== undefined && age < 16
    ? 'child'
    : age !== undefined && age >= 60
      ? 'senior'
      : 'adult';
}
export function createSearchContext(
  description: string,
  draft: PersonDraft,
  options: {
    caseNo?: string;
    verified?: boolean;
    source?: 'report' | 'search';
    state?: string;
    district?: string;
  } = {},
): SearchContext {
  if (draft.kind !== 'missing')
    throw new Error('Found-person reports must not expose match results.');
  return {
    version: 1,
    id: options.caseNo || `SEARCH-${crypto.randomUUID().slice(0, 8).toUpperCase()}`,
    caseNo: options.caseNo,
    description: description.trim(),
    draft: structuredClone(draft),
    verified: options.verified ?? false,
    source: options.source || 'search',
    startedAt: new Date().toISOString(),
    state: options.state,
    district: options.district,
  };
}
export function buildSampleMatches(draft: PersonDraft, description = ''): SampleMatch[] {
  if (draft.kind !== 'missing')
    throw new Error('Found-person reports must not expose match results.');
  const cohort = sampleCohort(draft, description),
    targetAge = ageNumber(draft.age),
    explicitFemale = /^(?:female|woman|girl|महिला|लड़की|लड़की)$/i.test(draft.gender || ''),
    explicitMale = /^(?:male|man|boy|पुरुष|लड़का|लड़का)$/i.test(draft.gender || '');
  const ages = { child: [8, 10, 12], adult: [24, 38, 48], senior: [64, 69, 75] }[cohort];
  const fixtures = [
    {
      clothing: 'Blue shirt, black trousers',
      language: 'Hindi, English',
      marks: 'Small scar above the left eyebrow',
      city: 'New Delhi',
      lastSeen: 'Near New Delhi railway station, Paharganj side',
      lastSeenAt: 'Friday, around 6:30 PM',
      station: 'Illustrative New Delhi station',
    },
    {
      clothing: 'Light-blue shirt, grey trousers',
      language: 'Hindi, Marathi',
      marks: 'Small mole near the right cheek',
      city: 'Ghaziabad',
      lastSeen: 'Near the bus terminal at Kaushambi',
      lastSeenAt: 'Saturday, around 10:00 AM',
      station: 'Illustrative Kaushambi station',
    },
    {
      clothing: 'White shirt, blue jeans',
      language: 'Bengali, Hindi',
      marks: 'No identifying mark recorded',
      city: 'Faridabad',
      lastSeen: 'Near the Old Faridabad market entrance',
      lastSeenAt: 'Sunday, around 4:15 PM',
      station: 'Illustrative Faridabad station',
    },
  ];
  return fixtures
    .map((f, row) => {
      const age = ages[row];
      const female = explicitFemale || (!explicitMale && !explicitFemale && row === 1);
      const comparisons: Comparison[] = [
        {
          key: 'age',
          query: draft.age,
          record: `${age} years`,
          score:
            targetAge === undefined
              ? null
              : Math.max(0, 1 - Math.abs(targetAge - age) / (cohort === 'child' ? 8 : 25)),
          weight: 20,
        },
        {
          key: 'gender',
          query: draft.gender,
          record: female ? 'Female' : 'Male',
          score: explicitFemale || explicitMale ? 1 : null,
          weight: 8,
        },
        {
          key: 'clothing',
          query: draft.clothing,
          record: f.clothing,
          score: known(draft.clothing) ? textSimilarity(draft.clothing!, f.clothing) : null,
          weight: 17,
        },
        {
          key: 'language',
          query: draft.language,
          record: f.language,
          score: known(draft.language) ? textSimilarity(draft.language!, f.language) : null,
          weight: 10,
        },
        {
          key: 'marks',
          query: draft.marks,
          record: f.marks,
          score: known(draft.marks) ? textSimilarity(draft.marks!, f.marks) : null,
          weight: 20,
        },
        {
          key: 'place',
          query: draft.place,
          record: `${f.city}. ${f.lastSeen}`,
          score: known(draft.place)
            ? textSimilarity(draft.place!, `${f.city} ${f.lastSeen}`)
            : null,
          weight: 15,
        },
        {
          key: 'time',
          query: draft.time,
          record: f.lastSeenAt,
          score: known(draft.time) ? textSimilarity(draft.time!, f.lastSeenAt) : null,
          weight: 10,
        },
      ];
      const available = comparisons.filter((c) => c.score !== null);
      const confidence = available.length
        ? Math.min(
            99,
            Math.round(
              ((100 * available.reduce((s, c) => s + c.score! * c.weight, 0)) /
                available.reduce((s, c) => s + c.weight, 0)) *
                Math.sqrt(available.reduce((s, c) => s + c.weight, 0) / 100),
            ),
          )
        : null;
      return {
        id: `SAMPLE-${cohort.toUpperCase()}-${row + 1}`,
        cohort,
        row,
        female,
        age,
        gender: female ? 'Female' : 'Male',
        ...f,
        description: `${age}-year-old ${female ? 'female' : 'male'} in ${f.clothing.toLowerCase()}. Languages recorded: ${f.language}. ${f.marks}.`,
        confidence,
        comparisons,
      };
    })
    .sort((a, b) => (b.confidence ?? -1) - (a.confidence ?? -1));
}

/** An ephemeral preview; it never replaces a person's saved/verified report. */
export function createSamplePreviewContext(): SearchContext {
  return {
    version: 1,
    id: 'SAMPLE-DEMO',
    description:
      'A fictional 24-year-old man who speaks Hindi and English, wearing a blue shirt and black trousers, with a small scar above the left eyebrow. Last seen near New Delhi railway station on Friday evening.',
    draft: {
      kind: 'missing',
      age: 'About 24 years',
      gender: 'Male',
      language: 'Hindi, English',
      clothing: 'Blue shirt, black trousers',
      marks: 'Small scar above the left eyebrow',
      place: 'New Delhi railway station',
      time: 'Friday evening',
      fieldConfidence: {},
    },
    verified: false,
    demoOnly: true,
    source: 'search',
    startedAt: new Date().toISOString(),
  };
}
