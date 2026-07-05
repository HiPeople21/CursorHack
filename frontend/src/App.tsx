import { useEffect, useRef, useState } from 'react';
import type { HealthStatus, UserProfile } from './types';
import PasteBox from './components/PasteBox';
import ResultView from './components/ResultView';
import Sidebar from './components/Sidebar';
import ProfilePanel, { PROFILE_ID_KEY } from './components/ProfilePanel';
import { getHealth, getProfile } from './api/client';
import { useSessions } from './hooks/useSessions';
import { useDecodeRuns } from './hooks/useDecodeRuns';
import { useTheme } from './hooks/useTheme';

function App() {
  const {
    sessions,
    active,
    activeId,
    select,
    create,
    remove,
    rename,
    setText,
    setJurisdiction,
    setResult,
    setDecoding,
  } = useSessions();

  const { getRun, startDecode, resumeDecode, loadingIds } = useDecodeRuns(
    setResult,
    setDecoding
  );

  const { isGhost, toggle: toggleTheme } = useTheme();
  const [profileOpen, setProfileOpen] = useState(false);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);

  // Restore the saved profile name for the sidebar footer on load.
  useEffect(() => {
    const id = localStorage.getItem(PROFILE_ID_KEY);
    if (!id) return;
    getProfile(id)
      .then((p) => {
        if (p) setProfile(p);
      })
      .catch(() => {
        /* offline / not found — sidebar just shows "Set up profile" */
      });
  }, []);

  // Environment/demo indicator.
  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  // Reconnect to any decode that was in flight when the page was refreshed.
  // The job kept running on the server; we replay its progress and finish it.
  const resumedRef = useRef(false);
  useEffect(() => {
    if (resumedRef.current) return;
    resumedRef.current = true;
    for (const s of sessions) {
      if (s.decoding && !s.result) void resumeDecode(s.id);
    }
  }, [sessions, resumeDecode]);

  const result = active?.result ?? null;

  return (
    <div className="flex h-screen overflow-hidden bg-stone-100">
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        onSelect={select}
        onCreate={create}
        onDelete={remove}
        onRename={rename}
        onOpenProfile={() => setProfileOpen(true)}
        profileName={profile?.full_name ?? null}
        loadingIds={loadingIds}
        isGhost={isGhost}
        onToggleTheme={toggleTheme}
      />

      <div className="flex min-w-0 flex-1 flex-col overflow-y-auto">
        {health?.demo_mode && (
          <div className="flex items-center justify-center gap-2 bg-indigo-800 px-4 py-1.5 text-center text-xs font-medium text-indigo-50">
            <span
              aria-hidden
              className="inline-block h-1.5 w-1.5 rounded-full bg-indigo-300"
            />
            Demo mode — using fixture data, live search is disabled.
          </div>
        )}

        <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6 sm:py-8">
          <div className="mb-4 flex items-center gap-1.5 text-sm font-medium text-stone-500">
            <svg
              className="h-3.5 w-3.5 shrink-0 text-stone-400"
              viewBox="0 0 20 20"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              aria-hidden
            >
              <path
                d="M5 3h6l4 4v10a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z"
                strokeLinejoin="round"
              />
              <path d="M11 3v4h4" strokeLinejoin="round" />
            </svg>
            <span className="truncate">{active?.title || 'New document'}</span>
          </div>

          {active && (
            <PasteBox
              key={active.id}
              text={active.text}
              jurisdiction={active.jurisdiction}
              run={getRun(active.id)}
              onTextChange={(t) => setText(active.id, t)}
              onJurisdictionChange={(j) => setJurisdiction(active.id, j)}
              onDecode={(institution) =>
                startDecode(
                  active.id,
                  active.text,
                  active.jurisdiction || undefined,
                  institution
                )
              }
            />
          )}

          {result && (
            <div className="mt-8">
              <ResultView result={result} />
            </div>
          )}

          <footer className="mt-10 border-t border-stone-200 pt-4 pb-2">
            <p className="text-xs leading-relaxed text-stone-400">
              {result?.disclaimer ??
                'Information, not legal advice. Standing cites the sources it uses so you can verify them yourself.'}
            </p>
          </footer>
        </main>
      </div>

      <ProfilePanel
        open={profileOpen}
        onClose={() => setProfileOpen(false)}
        onSaved={setProfile}
        onDeleted={() => setProfile(null)}
      />
    </div>
  );
}

export default App;
