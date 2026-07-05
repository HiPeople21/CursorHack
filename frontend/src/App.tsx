import { useEffect, useState } from 'react';
import type { HealthStatus, UserProfile } from './types';
import PasteBox from './components/PasteBox';
import ResultView from './components/ResultView';
import Sidebar from './components/Sidebar';
import ProfilePanel, { PROFILE_ID_KEY } from './components/ProfilePanel';
import { getHealth, getProfile } from './api/client';
import { useSessions } from './hooks/useSessions';

function App() {
  const {
    sessions,
    active,
    activeId,
    select,
    create,
    remove,
    setText,
    setJurisdiction,
    setResult,
  } = useSessions();

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

  const result = active?.result ?? null;

  return (
    <div className="flex h-screen overflow-hidden bg-stone-100">
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        onSelect={select}
        onCreate={create}
        onDelete={remove}
        onOpenProfile={() => setProfileOpen(true)}
        profileName={profile?.full_name ?? null}
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

        <header className="sticky top-0 z-10 border-b border-stone-200 bg-white/90 backdrop-blur">
          <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6">
            <h1 className="text-lg font-bold tracking-tight text-stone-900">
              {active?.title || 'New document'}
            </h1>
            <p className="mt-0.5 text-sm text-stone-500">
              Paste an official letter. We check whether it's even lawful, cite
              every claim to a source, and draft your response.
            </p>
          </div>
        </header>

        <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6 sm:py-8">
          {active && (
            <PasteBox
              key={active.id}
              text={active.text}
              jurisdiction={active.jurisdiction}
              onTextChange={(t) => setText(active.id, t)}
              onJurisdictionChange={(j) => setJurisdiction(active.id, j)}
              onResult={(r) => setResult(active.id, r)}
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
