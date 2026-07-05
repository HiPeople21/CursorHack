import type { DecodeResult } from '../types';
import VerificationPanel from './VerificationPanel';
import ClaimCard from './ClaimCard';
import ActionCard from './ActionCard';

interface ResultViewProps {
  result: DecodeResult;
}

const DOC_TYPE_LABEL: Record<string, string> = {
  tenancy: 'Tenancy notice',
  insurance: 'Insurance letter',
  medical_bill: 'Medical bill',
  gov_letter: 'Government letter',
  other: 'Document',
};

export default function ResultView({ result }: ResultViewProps) {
  return (
    <div className="space-y-8">
      {/* Summary */}
      <section className="rounded-2xl border border-stone-200 bg-surface p-5 shadow-sm sm:p-6">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <span className="inline-flex rounded-full bg-stone-900 px-3 py-1 text-xs font-bold uppercase tracking-wide text-white">
            {DOC_TYPE_LABEL[result.doc_type] ?? result.doc_type}
          </span>
          <span className="inline-flex rounded-full bg-stone-100 px-3 py-1 text-xs font-medium text-stone-500">
            Jurisdiction: {result.jurisdiction}
          </span>
        </div>
        <h2 className="text-lg font-bold text-stone-900 sm:text-xl">
          Plain-language summary
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-stone-700 sm:text-base">
          {result.plain_summary}
        </p>

        {result.extracted_facts.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {result.extracted_facts.map((fact) => (
              <span
                key={fact.key}
                title={fact.span ?? undefined}
                className="inline-flex items-center gap-1.5 rounded-full border border-stone-200 bg-stone-50 px-3 py-1 text-xs text-stone-600"
              >
                <span className="font-semibold text-stone-800">
                  {fact.key.replace(/_/g, ' ')}:
                </span>
                {fact.value}
              </span>
            ))}
          </div>
        )}
      </section>

      {/* Verification — the hero */}
      <VerificationPanel verification={result.verification} />

      {/* Claims */}
      {result.claims.length > 0 && (
        <section aria-labelledby="claims-heading">
          <h2
            id="claims-heading"
            className="mb-3 text-lg font-bold tracking-tight text-stone-900 sm:text-xl"
          >
            Claims checked
          </h2>
          <div className="space-y-3">
            {result.claims.map((claim, i) => (
              <ClaimCard key={i} claim={claim} />
            ))}
          </div>
        </section>
      )}

      {/* Actions */}
      {result.actions.length > 0 && (
        <section aria-labelledby="actions-heading">
          <h2
            id="actions-heading"
            className="mb-3 text-lg font-bold tracking-tight text-stone-900 sm:text-xl"
          >
            What you can do next
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {result.actions.map((action, i) => (
              <ActionCard key={i} action={action} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
