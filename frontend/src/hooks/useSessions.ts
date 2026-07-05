import { useCallback, useEffect, useState } from 'react';
import type { DecodeResult, Session } from '../types';

const STORAGE_KEY = 'standing.sessions.v1';
const ACTIVE_KEY = 'standing.activeSession.v1';

function uid(): string {
  return `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

function now(): string {
  return new Date().toISOString();
}

export function newSession(): Session {
  const ts = now();
  return {
    id: uid(),
    title: 'New document',
    text: '',
    jurisdiction: '',
    result: null,
    createdAt: ts,
    updatedAt: ts,
  };
}

// Derive a short, human title from the pasted text.
export function titleFromText(text: string): string {
  const firstLine = text
    .split('\n')
    .map((l) => l.trim())
    .find((l) => l.length > 0);
  if (!firstLine) return 'New document';
  return firstLine.length > 40 ? `${firstLine.slice(0, 40)}…` : firstLine;
}

function load(): Session[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as Session[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function useSessions() {
  const [sessions, setSessions] = useState<Session[]>(() => {
    const loaded = load();
    return loaded.length > 0 ? loaded : [newSession()];
  });
  const [activeId, setActiveId] = useState<string>(() => {
    const stored = localStorage.getItem(ACTIVE_KEY);
    if (stored) return stored;
    return null as unknown as string;
  });

  // Keep an always-valid active id.
  useEffect(() => {
    if (!activeId || !sessions.some((s) => s.id === activeId)) {
      setActiveId(sessions[0]?.id ?? '');
    }
  }, [sessions, activeId]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  }, [sessions]);

  useEffect(() => {
    if (activeId) localStorage.setItem(ACTIVE_KEY, activeId);
  }, [activeId]);

  const active = sessions.find((s) => s.id === activeId) ?? sessions[0] ?? null;

  const patch = useCallback((id: string, changes: Partial<Session>) => {
    setSessions((prev) =>
      prev.map((s) =>
        s.id === id ? { ...s, ...changes, updatedAt: now() } : s
      )
    );
  }, []);

  const setText = useCallback(
    (id: string, text: string) => {
      // Keep a manually-renamed title; otherwise derive it from the text.
      setSessions((prev) =>
        prev.map((s) =>
          s.id === id
            ? {
                ...s,
                text,
                title: s.renamed ? s.title : titleFromText(text),
                updatedAt: now(),
              }
            : s
        )
      );
    },
    []
  );

  const rename = useCallback((id: string, title: string) => {
    const clean = title.trim();
    setSessions((prev) =>
      prev.map((s) =>
        s.id === id
          ? {
              ...s,
              title: clean || titleFromText(s.text),
              renamed: clean.length > 0,
              updatedAt: now(),
            }
          : s
      )
    );
  }, []);

  const setJurisdiction = useCallback(
    (id: string, jurisdiction: string) => patch(id, { jurisdiction }),
    [patch]
  );

  const setResult = useCallback(
    (id: string, result: DecodeResult) => patch(id, { result }),
    [patch]
  );

  const setDecoding = useCallback(
    (id: string, decoding: boolean) => patch(id, { decoding }),
    [patch]
  );

  const create = useCallback(() => {
    const s = newSession();
    setSessions((prev) => [s, ...prev]);
    setActiveId(s.id);
    return s;
  }, []);

  const remove = useCallback((id: string) => {
    setSessions((prev) => {
      const next = prev.filter((s) => s.id !== id);
      return next.length > 0 ? next : [newSession()];
    });
  }, []);

  return {
    sessions,
    active,
    activeId: active?.id ?? '',
    select: setActiveId,
    create,
    remove,
    rename,
    setText,
    setJurisdiction,
    setResult,
    setDecoding,
  };
}
