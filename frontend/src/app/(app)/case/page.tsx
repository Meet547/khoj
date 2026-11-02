import type { Metadata } from 'next';
import { CasePage } from '@/features/case/CasePage';
export const metadata: Metadata = { title: 'Check my case' };
export default function Page() {
  return <CasePage />;
}
