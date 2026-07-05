import type { Session } from '../types';

interface SidebarProps {
  sessions: Session[];
  activeId: string;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
  onOpenProfile: () => void;
  profileName: string | null;
  isGhost: boolean;
  onToggleTheme: () => void;
}

function verdictDot(session: Session): string {
  const v = session.result?.verification ?? [];
  if (v.some((x) => x.verdict === 'mismatch')) return 'bg-red-500';
  if (v.length > 0 && v.every((x) => x.verdict === 'matches'))
    return 'bg-emerald-500';
  if (session.result) return 'bg-amber-400';
  return 'bg-stone-300';
}

export default function Sidebar({
  sessions,
  activeId,
  onSelect,
  onCreate,
  onDelete,
  onOpenProfile,
  profileName,
  isGhost,
  onToggleTheme,
}: SidebarProps) {
  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-stone-200 bg-surface">
      {/* Brand */}
      <div className="flex items-center gap-2 px-4 py-4">
        <span
          aria-hidden
          className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-black text-white"
        >
          S
        </span>
        <span className="text-lg font-black tracking-tight text-stone-900">
          Standing
        </span>
      </div>

      {/* New document */}
      <div className="px-3">
        <button
          type="button"
          onClick={onCreate}
          className="flex w-full items-center gap-2 rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-sm font-semibold text-stone-700 transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700"
        >
          <svg
            className="h-4 w-4"
            viewBox="0 0 20 20"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden
          >
            <path d="M10 4v12M4 10h12" strokeLinecap="round" />
          </svg>
          New document
        </button>
      </div>

      {/* Session list */}
      <div className="mt-3 min-h-0 flex-1 overflow-y-auto px-2 pb-2">
        <p className="px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-stone-400">
          Documents
        </p>
        <ul className="space-y-0.5">
          {sessions.map((s) => {
            const isActive = s.id === activeId;
            return (
              <li key={s.id}>
                <div
                  className={`group flex items-center gap-2 rounded-lg px-2 py-2 text-sm transition ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-900'
                      : 'text-stone-600 hover:bg-stone-100'
                  }`}
                >
                  <span
                    aria-hidden
                    className={`h-2 w-2 shrink-0 rounded-full ${verdictDot(s)}`}
                  />
                  <button
                    type="button"
                    onClick={() => onSelect(s.id)}
                    className="min-w-0 flex-1 truncate text-left"
                    title={s.title}
                  >
                    {s.title || 'New document'}
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(s.id);
                    }}
                    aria-label="Delete document"
                    className="shrink-0 rounded p-0.5 text-stone-400 opacity-0 transition hover:bg-stone-200 hover:text-red-600 group-hover:opacity-100"
                  >
                    <svg
                      className="h-3.5 w-3.5"
                      viewBox="0 0 20 20"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      aria-hidden
                    >
                      <path
                        d="M4 6h12M8 6V4h4v2m1 0-.5 10h-5L7 6"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      </div>

      {/* Ghost mode toggle */}
      <div className="px-2 pt-2">
        <button
          type="button"
          onClick={onToggleTheme}
          role="switch"
          aria-checked={isGhost}
          className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition hover:bg-stone-100"
        >
          <span
            aria-hidden
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-stone-100 text-stone-500"
          >
            {/* ghost glyph */}
            <svg
              className="h-4 w-4"
              viewBox="0 0 20 20"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              aria-hidden
            >
              <path
                d="M4 16V9a6 6 0 0 1 12 0v7l-2-1.3-2 1.3-2-1.3-2 1.3L4 16Z"
                strokeLinejoin="round"
              />
              <circle cx="8" cy="9" r="0.9" fill="currentColor" stroke="none" />
              <circle cx="12" cy="9" r="0.9" fill="currentColor" stroke="none" />
            </svg>
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-sm font-semibold text-stone-800">
              Ghost mode
            </span>
            <span className="block text-xs text-stone-400">
              {isGhost ? 'On — dark theme' : 'Off — light theme'}
            </span>
          </span>
          <span
            aria-hidden
            className={`relative h-5 w-9 shrink-0 rounded-full transition ${
              isGhost ? 'bg-indigo-600' : 'bg-stone-300'
            }`}
          >
            <span
              className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${
                isGhost ? 'left-4' : 'left-0.5'
              }`}
            />
          </span>
        </button>
      </div>

      {/* Profile — pinned bottom */}
      <div className="border-t border-stone-200 p-2">
        <button
          type="button"
          onClick={onOpenProfile}
          className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition hover:bg-stone-100"
        >
          <span
            aria-hidden
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white"
          >
            {profileName
              ? profileName
                  .split(' ')
                  .map((p) => p[0])
                  .slice(0, 2)
                  .join('')
                  .toUpperCase()
              : '?'}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-semibold text-stone-800">
              {profileName ?? 'Set up profile'}
            </span>
            <span className="block truncate text-xs text-stone-400">
              {profileName ? 'Edit your details' : 'For document autofill'}
            </span>
          </span>
          <svg
            className="h-4 w-4 shrink-0 text-stone-400"
            viewBox="0 0 20 20"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden
          >
            <path
              d="M7 4l6 6-6 6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>
    </aside>
  );
}
