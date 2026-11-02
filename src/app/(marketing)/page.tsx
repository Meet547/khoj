import { Landing } from '@/features/marketing/Landing';
export default function Home() {
  return (
    <>
      <link
        rel="preload"
        as="image"
        href="/characters/indian-crowd.avif"
        type="image/avif"
        fetchPriority="high"
      />
      <Landing />
    </>
  );
}
