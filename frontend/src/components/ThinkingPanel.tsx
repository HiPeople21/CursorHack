import type { DecodeProgressEvent, DecodeStage } from '../types';

interface ThinkingPanelProps {
  events: DecodeProgressEvent[];
  /** True while the stream is still open (drives the header spinner). */
  active: boolean;
}

// The visible pipeline steps, in order. Terminal stages (complete /
// needs_institution) are intentionally excluded — they carry the result, not a
// progress line.
const STAGES: Array<{ id: DecodeStage; label: string }> = [
  { id: 'classify', label: 'Read the document' },
  { id: 'identify', label: 'Identify the issuing authority' },
  { id: 'extract', label: 'Extract your specific facts' },
  { id: 'retrieve', label: 'Search the governing rules' },
  { id: 'ground', label: 'Read the source pages' },
  { id: 'verify', label: 'Check the document against the law' },
  { id: 'act', label: 'Draft what you can do next' },
  { id: 'refer', label: 'Check for a lawyer referral' },
];

type StageState = 'pending' | 'running' | 'done';

export default function ThinkingPanel({ events, active }: ThinkingPanelProps) {
  // Latest running label + done detail per stage.
  const byStage = new Map<DecodeStage, { running?: string; detail?: string }>();
  for (const e of events) {
    const entry = byStage.get(e.stage) ?? {};
    if (e.status === 'running' && e.label) entry.running = e.label;
    if (e.status === 'done' && e.detail) entry.detail = e.detail;
    byStage.set(e.stage, entry);
  }

  return (
    <div className="mt-6 overflow-hidden rounded-2xl border border-indigo-200 bg-indigo-50/60">
      <div className="flex items-center gap-2 border-b border-indigo-100 px-5 py-3">
        {active ? (
          <span
            aria-hidden
            className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-indigo-300 border-t-indigo-600"
          />
        ) : (
          <span aria-hidden className="text-indigo-600">
            ✓
          </span>
        )}
        <span className="text-sm font-semibold text-indigo-900">
          {active ? 'Working through your document…' : 'Analysis complete'}
        </span>
      </div>

      <ol className="divide-y divide-indigo-100">
        {STAGES.map(({ id, label }) => {
          const entry = byStage.get(id);
          const state: StageState = entry?.detail
            ? 'done'
            : entry?.running
              ? 'running'
              : 'pending';
          const line =
            state === 'done'
              ? entry?.detail
              : state === 'running'
                ? entry?.running
                : null;

          return (
            <li key={id} className="flex items-start gap-3 px-5 py-2.5">
              <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center">
                {state === 'done' && (
                  <span className="text-sm font-bold text-emerald-600">✓</span>
                )}
                {state === 'running' && (
                  <span
                    aria-hidden
                    className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-indigo-300 border-t-indigo-600"
                  />
                )}
                {state === 'pending' && (
                  <span
                    aria-hidden
                    className="h-1.5 w-1.5 rounded-full bg-stone-300"
                  />
                )}
              </span>

              <div className="min-w-0">
                <p
                  className={
                    state === 'pending'
                      ? 'text-sm text-stone-400'
                      : 'text-sm font-medium text-stone-800'
                  }
                >
                  {label}
                </p>
                {line && (
                  <p className="mt-0.5 text-xs leading-relaxed text-stone-500">
                    {line}
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
