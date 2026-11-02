import { LoginPage } from '@/features/auth/LoginPage';
import { safeNext } from '@/features/auth/redirect';
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ next?: string | string[] }>;
}) {
  const value = (await searchParams).next;
  return <LoginPage next={safeNext(typeof value === 'string' ? value : undefined)} />;
}
