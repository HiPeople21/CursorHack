import { useState } from 'react';
import App from './App';
import LandingPage from './components/LandingPage';

export default function Root() {
  const [started, setStarted] = useState(false);

  if (!started) {
    return <LandingPage onGetStarted={() => setStarted(true)} />;
  }

  return <App onHome={() => setStarted(false)} />;
}
