import { useState } from 'react';
import type { DecodeResult } from './types';
import PasteBox from './components/PasteBox';
import ResultView from './components/ResultView';

function App() {
  const [result, setResult] = useState<DecodeResult | null>(null);

  return (
    <div className="min-h-screen bg-stone-100">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto max-w-3xl px-4 py-5 sm:px-6">
          <div className="flex items-center gap-2">
            <span
              aria-hidden
              className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-black text-white"
            >
              S
            </span>
            <h1 className="text-xl font-black tracking-tight text-stone-900">
              Standing
            </h1>
          </div>
          <p className="mt-1 text-sm text-stone-500">
            Paste an official letter. We check whether it's even lawful, cite
            every claim to a source, and draft your response.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-8">
        <PasteBox onResult={setResult} />

        {result && (
          <div className="mt-8">
            <ResultView result={result} />
          </div>
        )}

        <footer className="mt-10 border-t border-stone-200 pt-4 pb-2">
          <p className="text-xs leading-relaxed text-stone-400">
            {result?.disclaimer ??
              'Information, not legal advice. Standing cites the sources it uses so you can verify them yourself.'}
          </p>
        </footer>
      </main>
    </div>
  );
}

export default App;
