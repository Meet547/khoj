'use client';
export default function Error({ reset }: { reset: () => void }) {
  return (
    <main className="app-main" id="main">
      <div className="app-panel offline-panel">
        <h1>Let’s try that again.</h1>
        <p>The page could not load. Your saved draft stays on this device.</p>
        <button className="button dark" onClick={reset}>
          Try again
        </button>
      </div>
    </main>
  );
}
