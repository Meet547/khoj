import type { Metadata } from 'next';
import { Report } from '@/features/intake/Report';
export const metadata: Metadata = { title: 'Report a found person' };
export default function FoundPage() {
  return <Report kind="found" />;
}
