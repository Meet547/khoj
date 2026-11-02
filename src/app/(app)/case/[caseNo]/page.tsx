import type { Metadata } from 'next';
import { CasePage } from '@/features/case/CasePage';
export const metadata: Metadata = { title: 'Case status' };
export default async function Page({ params }: { params: Promise<{ caseNo: string }> }) {
  const { caseNo } = await params;
  return <CasePage caseNo={caseNo} />;
}
