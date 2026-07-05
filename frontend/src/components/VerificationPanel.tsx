import type { Verification, VerificationVerdict } from '../types';
import SourceReceipt from './SourceReceipt';

interface VerificationPanelProps {
  verification: Verification[];
}

const VERDICT_META: Record<
  VerificationVerdict,
  { label: string; card: string; badge: string; icon: string }
> = {
  mismatch: {
    label: 'MISMATCH',
    card: 'border-red-300 bg-red-50 ring-1 ring-red-100',
    badge: 'bg-red-600 text-white',
    icon: '⚠', // warning triangle-ish
  },
  matches: {
    label: 'Matches',
    card: 'border-stone-200 bg-white',
    badge: 'bg-emerald-100 text-emerald-800',
    icon: '✓',
  },
  cannot_determine: {
    label: 'Cannot determine',
    card: 'border-amber-200 bg-amber-50/60',
    badge: 'bg-amber-100 text-amber-800',
    icon: '?',
  },
};

export default function VerificationPanel({
  verification,
}: VerificationPanelProps) {
  const mismatchCount = verification.filter(
    (v) => v.verdict === 'mismatch'
  ).length;

  return (
    <section aria-labelledby="verification-heading">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2
          id="verification-heading"
          className="text-lg font-bold tracking-tight text-stone-900 sm:text-xl"
        >
          Is this document even lawful?
        </h2>
        {mismatchCount > 0 && (
          <span className="inline-flex items-center gap-1 rounded-full bg-red-600 px-3 py-1 text-xs font-bold text-white shadow-sm">
            {mismatchCount} problem{mismatchCount > 1 ? 's' : ''} found
          </span>
        )}
      </div>

      <div className="space-y-3">
        {verification.map((v, i) => (
          <VerificationItem key={i} v={v} />
        ))}
      </div>
    </section>
  );
}

function VerificationItem({ v }: { v: Verification }) {
  const meta = VERDICT_META[v.verdict];
  const isMismatch = v.verdict === 'mismatch';

  return (
    <article
      className={`rounded-2xl border p-4 shadow-sm transition sm:p-5 ${meta.card} ${
        isMismatch ? 'shadow-red-100' : ''
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span
            aria-hidden
            className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${meta.badge}`}
          >
            {meta.icon}
          </span>
          <span
            className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wide ${meta.badge}`}
          >
            {meta.label}
          </span>
        </div>
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
            The letter says
          </p>
          <p
            className={`mt-0.5 text-sm font-medium ${isMismatch ? 'text-red-800' : 'text-stone-800'}`}
          >
            {v.assertion}
          </p>
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
            The rule says
          </p>
          <p
            className={`mt-0.5 text-sm font-medium ${isMismatch ? 'text-red-900' : 'text-stone-800'}`}
          >
            {v.rule_value}
          </p>
        </div>
      </div>

      <p
        className={`mt-3 text-sm leading-relaxed ${isMismatch ? 'text-red-800' : 'text-stone-600'}`}
      >
        {v.explanation}
      </p>

      <div className="mt-3">
        {v.source ? (
          <SourceReceipt source={v.source} tone={isMismatch ? 'alert' : 'neutral'} />
        ) : (
          <p className="rounded-lg border border-dashed border-stone-300 px-3 py-2 text-xs text-stone-400">
            No source could be retrieved to verify this point.
          </p>
        )}
      </div>
    </article>
  );
}
