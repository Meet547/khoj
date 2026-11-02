import type { Lang } from './config';
const loaders = {
  en: () => import('@/messages/en.json'),
  hi: () => import('@/messages/hi.json'),
  mr: () => import('@/messages/mr.json'),
  bn: () => import('@/messages/bn.json'),
  ta: () => import('@/messages/ta.json'),
  pa: () => import('@/messages/pa.json'),
  gu: () => import('@/messages/gu.json'),
  kn: () => import('@/messages/kn.json'),
  ml: () => import('@/messages/ml.json'),
  te: () => import('@/messages/te.json'),
};
export async function loadMessages(lang: Lang): Promise<Record<string, string>> {
  return (await loaders[lang]()).default;
}
