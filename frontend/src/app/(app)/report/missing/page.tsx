import type { Metadata } from 'next';
import { Report } from '@/features/intake/Report';
export const metadata: Metadata = { title: 'Report a missing person' };
export default function MissingPage() {
  return <Report kind="missing" />;
}
