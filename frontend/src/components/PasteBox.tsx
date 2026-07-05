import { useEffect, useRef, useState } from 'react';
import type { DragEvent, FormEvent } from 'react';
import type { UserProvidedInstitution } from '../types';
import type { DecodeRun } from '../hooks/useDecodeRuns';
import ThinkingPanel from './ThinkingPanel';

interface Attachment {
  id: string;
  name: string;
  kind: 'image' | 'pdf';
  url: string; // object URL
}

function attachmentKind(file: File): Attachment['kind'] | null {
  if (file.type.startsWith('image/')) return 'image';
  if (file.type === 'application/pdf' || /\.pdf$/i.test(file.name)) return 'pdf';
  return null;
}

interface PasteBoxProps {
  text: string;
  jurisdiction: string;
  run: DecodeRun;
  onTextChange: (text: string) => void;
  onJurisdictionChange: (jurisdiction: string) => void;
  onDecode: (institution?: UserProvidedInstitution | null) => void;
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
  run,
  onTextChange,
  onJurisdictionChange,
  onDecode,
}: PasteBoxProps) {
  // Decode state is owned by the app-level useDecodeRuns hook.
  const { loading, error, prompt, events } = run;

  const [institutionText, setInstitutionText] = useState('');
  const [dragging, setDragging] = useState(false);
  const [dropped, setDropped] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const dragDepth = useRef(0);
  const fileInput = useRef<HTMLInputElement>(null);

  // Release object URLs when the component unmounts.
  useEffect(() => {
    return () => attachments.forEach((a) => URL.revokeObjectURL(a.url));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function removeAttachment(id: string) {
    setAttachments((prev) => {
      const found = prev.find((a) => a.id === id);
      if (found) URL.revokeObjectURL(found.url);
      return prev.filter((a) => a.id !== id);
    });
  }

  function bounce() {
    setDropped(true);
    window.setTimeout(() => setDropped(false), 550);
  }

  async function ingestFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setFileError(null);

    const all = Array.from(files);
    // Images and PDFs are shown as previews — never read as text.
    const previews = all
      .map((f) => {
        const kind = attachmentKind(f);
        return kind
          ? {
              id: `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
              name: f.name,
              kind,
              url: URL.createObjectURL(f),
            }
          : null;
      })
      .filter((a): a is Attachment => a !== null);

    const textFiles = all.filter((f) => attachmentKind(f) === null);

    if (previews.length > 0) {
      setAttachments((prev) => [...prev, ...previews]);
      bounce();
    }

    if (textFiles.length > 0) {
      try {
        const parts = await Promise.all(textFiles.map((f) => f.text()));
        const joined = parts.join('\n\n').trim();
        if (joined) {
          onTextChange(joined);
          bounce();
        } else if (previews.length === 0) {
          setFileError('That file looks empty — try a plain-text document.');
        }
      } catch {
        setFileError(
          'Could not read that file. Paste the text instead, or try a .txt file.'
        );
      }
    }
  }

  function handleDragEnter(e: DragEvent) {
    e.preventDefault();
    if (loading) return;
    dragDepth.current += 1;
    setDragging(true);
  }

  function handleDragLeave(e: DragEvent) {
    e.preventDefault();
    dragDepth.current -= 1;
    if (dragDepth.current <= 0) {
      dragDepth.current = 0;
      setDragging(false);
    }
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    dragDepth.current = 0;
    setDragging(false);
    if (loading) return;
    void ingestFiles(e.dataTransfer.files);
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!text.trim() || loading) return;
    onDecode();
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

      <div
        className={`relative ${dropped ? 'animate-plop' : ''}`}
        onDragEnter={handleDragEnter}
        onDragOver={(e) => e.preventDefault()}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <textarea
          id="doc-text"
          value={text}
          onChange={(e) => onTextChange(e.target.value)}
          placeholder="Paste the text here — or drop a file anywhere on this box..."
          rows={12}
          className={`w-full resize-y rounded-xl border bg-stone-50 p-4 text-sm leading-relaxed text-stone-800 shadow-inner transition-colors focus:border-indigo-400 focus:bg-surface focus:outline-none focus:ring-2 focus:ring-indigo-100 ${
            dragging ? 'border-indigo-400' : 'border-stone-300'
          }`}
        />

        {dragging && (
          <div className="animate-overlay-in pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-indigo-400 bg-indigo-50/85 backdrop-blur-sm">
            <svg
              className="h-9 w-9 text-indigo-600"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              aria-hidden
            >
              <path
                d="M12 16V4m0 0L8 8m4-4 4 4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M4 14v3a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3v-3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <p className="text-sm font-bold text-indigo-700">
              Drop to read your document
            </p>
          </div>
        )}

        <input
          ref={fileInput}
          type="file"
          accept=".txt,.md,.csv,.eml,.text,text/*,image/*,application/pdf"
          multiple
          className="hidden"
          onChange={(e) => {
            void ingestFiles(e.target.files);
            e.target.value = '';
          }}
        />
      </div>

      {attachments.length > 0 && (
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {attachments.map((a) => (
            <div
              key={a.id}
              className="animate-plop group relative overflow-hidden rounded-xl border border-stone-200 bg-stone-50"
            >
              {a.kind === 'image' ? (
                <img
                  src={a.url}
                  alt={a.name}
                  className="h-32 w-full object-cover"
                />
              ) : (
                <object
                  data={`${a.url}#toolbar=0&navpanes=0&view=FitH`}
                  type="application/pdf"
                  aria-label={a.name}
                  className="pointer-events-none h-32 w-full bg-stone-100"
                >
                  <div className="flex h-32 w-full flex-col items-center justify-center gap-1 text-stone-400">
                    <svg
                      className="h-8 w-8"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      aria-hidden
                    >
                      <path
                        d="M7 3h7l4 4v14a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z"
                        strokeLinejoin="round"
                      />
                      <path d="M14 3v4h4" strokeLinejoin="round" />
                    </svg>
                    <span className="text-[10px] font-semibold">PDF</span>
                  </div>
                </object>
              )}

              <div className="flex items-center justify-between gap-2 border-t border-stone-200 px-2 py-1.5">
                <span className="flex items-center gap-1 truncate text-[11px] font-medium text-stone-600">
                  <span
                    aria-hidden
                    className="rounded bg-indigo-100 px-1 text-[9px] font-bold uppercase text-indigo-700"
                  >
                    {a.kind}
                  </span>
                  <span className="truncate" title={a.name}>
                    {a.name}
                  </span>
                </span>
                <button
                  type="button"
                  onClick={() => removeAttachment(a.id)}
                  aria-label={`Remove ${a.name}`}
                  className="shrink-0 rounded p-0.5 text-stone-400 transition hover:bg-stone-200 hover:text-red-600"
                >
                  <svg
                    className="h-3.5 w-3.5"
                    viewBox="0 0 20 20"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    aria-hidden
                  >
                    <path d="M5 5l10 10M15 5L5 15" strokeLinecap="round" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="mt-2 text-xs text-stone-400">
        Drag &amp; drop a document, image, or PDF, or{' '}
        <button
          type="button"
          onClick={() => fileInput.current?.click()}
          className="font-semibold text-indigo-600 hover:text-indigo-700 hover:underline"
        >
          browse for a file
        </button>
        .
      </p>

      {fileError && (
        <p className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {fileError}
        </p>
      )}

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
          {loading ? 'Decoding…' : 'Decode this document'}
        </button>
      </div>

      {events.length > 0 && <ThinkingPanel events={events} active={loading} />}

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
                  onClick={() => onDecode({ body_id: s.body_id })}
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
              onClick={() => onDecode({ display_name: institutionText.trim() })}
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
