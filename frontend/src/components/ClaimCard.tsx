import type { Claim, ClaimStatus } from '../types';
import SourceReceipt from './SourceReceipt';

interface ClaimCardProps {
  claim: Claim;
}

const STATUS_META: Record<ClaimStatus, { label: string; badge: string }> = {
  supported: { label: 'Supported', badge: 'bg-emerald-100 text-emerald-800' },
  contradicted: { label: 'Contradicted', badge: 'bg-red-100 text-red-800' },
  unverifiable: { label: 'Unverifiable', badge: 'bg-stone-200 text-stone-600' },
};

export default function ClaimCard({ claim }: ClaimCardProps) {
  const meta = STATUS_META[claim.status];
  const isContradicted = claim.status === 'contradicted';

  return (
    <div
      className={`rounded-xl border p-4 ${
        isContradicted ? 'border-red-200 bg-red-50/50' : 'border-stone-200 bg-white'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium leading-snug text-stone-800">
          {claim.statement}
        </p>
        <span
          className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide ${meta.badge}`}
        >
          {meta.label}
        </span>
      </div>

      <div className="mt-3">
        {claim.source ? (
          <SourceReceipt source={claim.source} tone={isContradicted ? 'alert' : 'neutral'} />
        ) : (
          <p className="rounded-lg border border-dashed border-stone-300 px-3 py-2 text-xs text-stone-400">
            No verified source — treat this claim as unconfirmed.
          </p>
        )}
      </div>
    </div>
  );
}
