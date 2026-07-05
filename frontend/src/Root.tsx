import { useEffect, useState } from 'react';
import App from './App';
import LandingPage from './components/LandingPage';

// Persist whether the user has entered the app so a refresh keeps them on
// their document instead of bouncing back to the landing page.
const STARTED_KEY = 'standing.started.v1';

export default function Root() {
  const [started, setStarted] = useState<boolean>(
    () => localStorage.getItem(STARTED_KEY) === '1'
  );

  useEffect(() => {
    if (started) localStorage.setItem(STARTED_KEY, '1');
    else localStorage.removeItem(STARTED_KEY);
  }, [started]);

  if (!started) {
    return <LandingPage onGetStarted={() => setStarted(true)} />;
  }

  return <App onGoHome={() => setStarted(false)} />;
}
