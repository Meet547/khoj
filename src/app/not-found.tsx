import Link from 'next/link';
import { Search } from 'lucide-react';
export default function NotFound() {
  return (
    <main className="app-main" id="main">
      <div className="app-panel offline-panel">
        <Search size={35} className="mx-auto" />
        <h1>A little off track.</h1>
        <p>This page could not be found. Let’s get you back to your search.</p>
        <Link href="/" className="button dark">
          Go home →
        </Link>
      </div>
    </main>
  );
}
