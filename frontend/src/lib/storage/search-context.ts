'use client';
import { get, set, del, keys } from 'idb-keyval';
import type { SearchContext } from '@/features/search/demo';
const LATEST = 'khoj-latest-search-context';
export async function rememberSearchContext(context: SearchContext) {
  if (context.draft.kind !== 'missing') return;
  await set(`khoj-search-context:${context.id}`, context);
  await set(LATEST, context);
}
export async function loadSearchContext(id?: string): Promise<SearchContext | null> {
  const value = await get<SearchContext>(id ? `khoj-search-context:${id}` : LATEST);
  return value?.version === 1 &&
    value.draft?.kind === 'missing' &&
    typeof value.description === 'string' &&
    Number.isFinite(Date.parse(value.startedAt))
    ? value
    : null;
}
export async function clearSearchContexts() {
  const stored = await keys();
  await Promise.all(
    stored
      .filter(
        (k) => typeof k === 'string' && (k === LATEST || k.startsWith('khoj-search-context:')),
      )
      .map((k) => del(k)),
  );
}
