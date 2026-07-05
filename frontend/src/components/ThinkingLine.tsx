import { useEffect, useState } from 'react';
import GhostSpinner from './GhostSpinner';

// Legal-flavoured "thinking" buzzwords the ghost cycles through while the
// six-stage pipeline runs. Playful, but they track the real stages:
// classify → extract → retrieve → ground → verify → act.
const BUZZWORDS = [
  'Perusing',
  'Fact-marshalling',
  'Statute-sifting',
  'Cross-examining',
  'Grounding',
  'Receipt-hunting',
  'Precedent-chasing',
  'Adjudicating',
  'Deliberating',
  'Drafting',
];

export default function ThinkingLine() {
  const [i, setI] = useState(() => Math.floor(Math.random() * BUZZWORDS.length));

  useEffect(() => {
    const id = setInterval(() => {
      setI((n) => (n + 1) % BUZZWORDS.length);
    }, 1700);
    return () => clearInterval(id);
  }, []);

  return (
    <div
      role="status"
      aria-live="polite"
      className="animate-overlay-in mt-4 flex items-center gap-3 rounded-xl border border-stone-200 bg-stone-50 px-4 py-3"
    >
      <GhostSpinner className="h-8 w-8" />
      <div className="flex min-w-0 items-baseline gap-1">
        {/* key forces the fade-in each time the word changes */}
        <span
          key={i}
          className="thinking-word animate-word-in text-sm font-bold tracking-wide"
        >
          {BUZZWORDS[i]}
        </span>
        <span className="flex gap-0.5">
          {[0, 1, 2].map((d) => (
            <span
              key={d}
              className="h-1 w-1 animate-bounce rounded-full bg-stone-400"
              style={{ animationDelay: `${d * 150}ms` }}
            />
          ))}
        </span>
      </div>
      <span className="ml-auto text-xs font-medium text-stone-400">
        checking against the rules
      </span>
    </div>
  );
}
