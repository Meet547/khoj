import type { Metadata } from 'next';
import { SearchPage } from '@/features/search/SearchPage';
export const metadata: Metadata = { title: 'Search by description' };
export default function Page() {
  return <SearchPage />;
}
