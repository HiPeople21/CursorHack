import { useCallback, useEffect, useState } from 'react';

const STORAGE_KEY = 'standing.theme.v1';

export type Theme = 'light' | 'ghost';

function initialTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'ghost' || stored === 'light') return stored;
  // Respect the OS preference on first visit.
  if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
    return 'ghost';
  }
  return 'light';
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(initialTheme);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('ghost', theme === 'ghost');
    root.classList.toggle('dark', theme === 'ghost'); // for Tailwind dark: variants
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const toggle = useCallback(
    () => setTheme((t) => (t === 'ghost' ? 'light' : 'ghost')),
    []
  );

  return { theme, toggle, isGhost: theme === 'ghost' };
}
