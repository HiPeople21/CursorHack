import { useState } from 'react';
import type { FormEvent } from 'react';
import type {
  DecodeResult,
  InstitutionPrompt,
  UserProvidedInstitution,
} from '../types';
import { decode } from '../api/client';

interface PasteBoxProps {
  text: string;
  jurisdiction: string;
  onTextChange: (text: string) => void;
  onJurisdictionChange: (jurisdiction: string) => void;
  onResult: (result: DecodeResult) => void;
}

const SAMPLE_TEXT = `NOTICE OF TERMINATION

Address: 14 Oakwood Grove, Dublin 9
Tenancy commenced on 3 April 2023.

Dear Tenant,

The landlord intends to sell the property within the next 3 months and is
therefore terminating your tenancy. You are required to vacate the property
within 14 days of this notice.

Date of this notice: 21 June 2026`;

const JURISDICTIONS = [
  { value: '', label: 'Auto-detect' },
  { value: 'IE', label: 'Ireland (IE)' },
  { value: 'GB', label: 'United Kingdom (GB)' },
];

export default function PasteBox({
  text,
  jurisdiction,
  onTextChange,
  onJurisdictionChange,
  onResult,
}: PasteBoxProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prompt, setPrompt] = useState<InstitutionPrompt | null>(null);
  const [institutionText, setInstitutionText] = useState('');

  async function submit(institution?: UserProvidedInstitution | null) {
    if (!text.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const response = await decode(text, jurisdiction || undefined, institution);
      if (response.status === 'needs_institution') {
        setPrompt(response.institution_prompt);
        return;
      }
      if (response.result) {
        setPrompt(null);
        setInstitutionText('');
        onResult(response.result);
        return;
      }
      // Reached only if the server returns a shape we don't understand
      // (e.g. a stale backend on the old contract). Fail loudly rather than
      // leaving the user staring at a spinner that silently resolved.
      setError(
        'The server returned an unexpected response. It may be running an ' +
          'older version — try restarting the backend and decoding again.'
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setPrompt(null);
    void submit();
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-surface rounded-2xl border border-stone-200 shadow-sm p-5 sm:p-7"
    >
      <div className="flex items-center justify-between gap-3 mb-3">
        <label
          htmlFor="doc-text"
          className="text-sm font-semibold text-stone-700"
        >
          Paste your letter, notice, or bill
        </label>
        {jurisdiction && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-stone-100 px-2.5 py-1 text-xs font-medium text-stone-500">
            <span
              aria-hidden
              className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500"
            />
            Hint: {jurisdiction}
          </span>
        )}
      </div>

      <textarea
        id="doc-text"
        value={text}
        onChange={(e) => onTextChange(e.target.value)}
        placeholder="Paste the full text of the tenancy notice, insurance letter, medical bill, or government letter here..."
        rows={12}
        className="w-full resize-y rounded-xl border border-stone-300 bg-stone-50 p-4 text-sm leading-relaxed text-stone-800 shadow-inner focus:border-indigo-400 focus:bg-surface focus:outline-none focus:ring-2 focus:ring-indigo-100"
      />

      <div className="mt-4 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-2 text-xs text-stone-500">
          <span>Jurisdiction:</span>
          <select
            value={jurisdiction}
            onChange={(e) => onJurisdictionChange(e.target.value)}
            className="rounded-md border border-stone-300 bg-surface px-2 py-1 text-xs font-medium text-stone-700"
          >
            {JURISDICTIONS.map((j) => (
              <option key={j.value || 'auto'} value={j.value}>
                {j.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => onTextChange(SAMPLE_TEXT)}
            className="ml-1 rounded-md border border-stone-200 px-2 py-1 font-medium text-indigo-600 hover:bg-indigo-50"
          >
            Try sample notice
          </button>
        </div>

        <button
          type="submit"
          disabled={loading || !text.trim()}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-stone-300"
        >
          {loading && (
            <span
              aria-hidden
              className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
            />
          )}
          {loading ? 'Checking against the rules...' : 'Decode this document'}
        </button>
      </div>

      {prompt && (
        <div className="mt-4 rounded-xl border border-amber-300 bg-amber-50 p-4">
          <p className="text-sm font-semibold text-amber-900">
            {prompt.message}
          </p>
          {prompt.suggestions.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {prompt.suggestions.map((s) => (
                <button
                  key={s.body_id}
                  type="button"
                  disabled={loading}
                  onClick={() => void submit({ body_id: s.body_id })}
                  className="rounded-lg border border-amber-300 bg-surface px-3 py-1.5 text-sm font-medium text-amber-900 transition hover:bg-amber-100 disabled:opacity-50"
                >
                  {s.display_name}
                </button>
              ))}
            </div>
          )}
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <input
              type="text"
              value={institutionText}
              onChange={(e) => setInstitutionText(e.target.value)}
              placeholder="Or type the authority's name (e.g. Residential Tenancies Board)"
              className="min-w-0 flex-1 rounded-lg border border-amber-300 bg-surface px-3 py-2 text-sm text-stone-800 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
            />
            <button
              type="button"
              disabled={loading || institutionText.trim() === ''}
              onClick={() =>
                void submit({ display_name: institutionText.trim() })
              }
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-stone-300"
            >
              Continue
            </button>
          </div>
        </div>
      )}

      {error && (
        <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
    </form>
  );
}
