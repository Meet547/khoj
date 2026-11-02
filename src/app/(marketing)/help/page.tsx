import type { Metadata } from 'next';
import { HelpPage } from '@/features/marketing/HelpPage';
export const metadata: Metadata = { title: 'Help, safety & privacy' };
export default function Page() {
  return <HelpPage />;
}
