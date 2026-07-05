import { useState } from 'react';
import type { Action, ActionKind } from '../types';

interface ActionCardProps {
  action: Action;
}

const KIND_LABEL: Record<ActionKind, string> = {
  letter: 'Letter',
  form: 'Form',
  email: 'Email',
  deadline: 'Deadline',
  contact: 'Contact',
};

export default function ActionCard({ action }: ActionCardProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(action.body);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // clipboard API unavailable; silently ignore
    }
  }

  return (
    <div className="rounded-2xl border border-stone-200 bg-surface p-4 shadow-sm sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="inline-flex rounded-full bg-indigo-100 px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-indigo-700">
            {KIND_LABEL[action.kind]}
          </span>
          <h3 className="text-sm font-bold text-stone-900">{action.title}</h3>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-1.5 rounded-lg border border-stone-300 bg-stone-50 px-2.5 py-1 text-xs font-semibold text-stone-600 transition hover:bg-stone-100"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>

      {action.deadline && (
        <div className="mt-3 inline-flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-1.5 text-xs font-bold text-amber-800 ring-1 ring-amber-200">
          <span aria-hidden>⏰</span>
          Deadline: {formatDeadline(action.deadline)}
        </div>
      )}

      <pre className="mt-3 max-h-72 overflow-y-auto whitespace-pre-wrap rounded-xl bg-stone-50 p-3 font-sans text-sm leading-relaxed text-stone-700">
        {action.body}
      </pre>
    </div>
  );
}

function formatDeadline(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  } catch {
    return iso;
  }
}
