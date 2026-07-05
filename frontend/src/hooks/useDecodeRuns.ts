import { useCallback, useRef, useState } from 'react';
import type {
  DecodeProgressEvent,
  DecodeResult,
  InstitutionPrompt,
  UserProvidedInstitution,
} from '../types';
import { decodeStream } from '../api/client';

// Per-session decode state. Lives at the App level (not inside PasteBox) so that
// switching sessions — e.g. clicking "New document" mid-decode — never unmounts
// the in-flight stream. The run keeps going and its progress is preserved, so
// returning to the session shows it still working (or finished).
export interface DecodeRun {
  loading: boolean;
  events: DecodeProgressEvent[];
  error: string | null;
  prompt: InstitutionPrompt | null;
}

export const EMPTY_RUN: DecodeRun = {
  loading: false,
  events: [],
  error: null,
  prompt: null,
};

const UNEXPECTED_RESPONSE =
  'The server returned an unexpected response. It may be running an older ' +
  'version — try restarting the backend and decoding again.';

export function useDecodeRuns(
  onResult: (sessionId: string, result: DecodeResult) => void
) {
  const [runs, setRuns] = useState<Record<string, DecodeRun>>({});
  // Guards against double-submitting the same session while a run is in flight.
  const inFlight = useRef<Set<string>>(new Set());

  const patchRun = useCallback((id: string, changes: Partial<DecodeRun>) => {
    setRuns((prev) => ({ ...prev, [id]: { ...(prev[id] ?? EMPTY_RUN), ...changes } }));
  }, []);

  const startDecode = useCallback(
    async (
      sessionId: string,
      text: string,
      jurisdiction?: string,
      institution?: UserProvidedInstitution | null
    ) => {
      if (!text.trim() || inFlight.current.has(sessionId)) return;
      inFlight.current.add(sessionId);
      setRuns((prev) => ({
        ...prev,
        [sessionId]: { loading: true, events: [], error: null, prompt: null },
      }));

      try {
        const response = await decodeStream(
          text,
          (event) =>
            setRuns((prev) => {
              const cur = prev[sessionId] ?? EMPTY_RUN;
              return { ...prev, [sessionId]: { ...cur, events: [...cur.events, event] } };
            }),
          jurisdiction,
          institution
        );

        if (response.status === 'needs_institution') {
          patchRun(sessionId, { loading: false, prompt: response.institution_prompt });
        } else if (response.result) {
          onResult(sessionId, response.result);
          patchRun(sessionId, { loading: false, prompt: null });
        } else {
          patchRun(sessionId, { loading: false, error: UNEXPECTED_RESPONSE });
        }
      } catch (err) {
        patchRun(sessionId, {
          loading: false,
          error: err instanceof Error ? err.message : 'Something went wrong.',
        });
      } finally {
        inFlight.current.delete(sessionId);
      }
    },
    [onResult, patchRun]
  );

  const getRun = useCallback(
    (id: string): DecodeRun => runs[id] ?? EMPTY_RUN,
    [runs]
  );

  const loadingIds = Object.keys(runs).filter((id) => runs[id].loading);

  return { getRun, startDecode, loadingIds };
}
