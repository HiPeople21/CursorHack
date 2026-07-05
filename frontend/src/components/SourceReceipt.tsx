import type { Source } from '../types';

interface SourceReceiptProps {
  source: Source;
  tone?: 'neutral' | 'alert';
}

export default function SourceReceipt({
  source,
  tone = 'neutral',
}: SourceReceiptProps) {
  const toneClasses =
    tone === 'alert'
      ? 'border-red-200 bg-red-50/70 text-red-900'
      : 'border-stone-200 bg-stone-50 text-stone-700';

  return (
    <div className={`rounded-lg border ${toneClasses} px-3 py-2.5`}>
      <div className="flex items-start gap-2">
        <span
          aria-hidden
          className="mt-0.5 select-none font-serif text-lg leading-none text-stone-400"
        >
          &ldquo;
        </span>
        <p className="receipt-quote flex-1 text-sm italic leading-snug">
          {source.quote}
        </p>
      </div>
      <div className="mt-1.5 flex items-center justify-between gap-2 pl-4">
        <a
          href={source.url}
          target="_blank"
          rel="noreferrer"
          className="truncate text-xs font-medium text-indigo-600 underline decoration-indigo-300 underline-offset-2 hover:text-indigo-800"
          title={source.url}
        >
          {source.title}
        </a>
        <span className="shrink-0 text-[11px] text-stone-400">
          retrieved {formatDate(source.retrieved_at)}
        </span>
      </div>
    </div>
  );
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return iso;
  }
}
