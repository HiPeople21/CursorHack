import { useCallback, useRef, useState } from 'react';
import type {
  DecodeProgressEvent,
  DecodeResponse,
  DecodeResult,
  InstitutionPrompt,
  UserProvidedInstitution,
} from '../types';
import { decodeStream, resumeDecodeStream, uploadDocument } from '../api/client';

// Per-session decode state. Lives at the App level (not inside PasteBox) so that
// switching sessions — e.g. clicking "New document" mid-decode — never unmounts
// the in-flight stream. The actual work runs as a server-side job keyed by the
// session id, so it also survives a full page refresh: on load we reconnect to
// any session still flagged as decoding.
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

const INTERRUPTED =
  'The previous decode was interrupted (the server may have restarted). ' +
  'Please run it again.';

export function useDecodeRuns(
  onResult: (sessionId: string, result: DecodeResult) => void,
  onDecodingChange: (sessionId: string, decoding: boolean) => void
) {
  const [runs, setRuns] = useState<Record<string, DecodeRun>>({});
  // Guards against double-submitting / double-resuming a session.
  const inFlight = useRef<Set<string>>(new Set());

  const patchRun = useCallback((id: string, changes: Partial<DecodeRun>) => {
    setRuns((prev) => ({ ...prev, [id]: { ...(prev[id] ?? EMPTY_RUN), ...changes } }));
  }, []);

  const pushEvent = useCallback((id: string, event: DecodeProgressEvent) => {
    setRuns((prev) => {
      const cur = prev[id] ?? EMPTY_RUN;
      return { ...prev, [id]: { ...cur, events: [...cur.events, event] } };
    });
  }, []);

  const applyResponse = useCallback(
    (sessionId: string, response: DecodeResponse) => {
      if (response.status === 'needs_institution') {
        patchRun(sessionId, { loading: false, prompt: response.institution_prompt });
      } else if (response.result) {
        onResult(sessionId, response.result);
        patchRun(sessionId, { loading: false, prompt: null });
      } else {
        patchRun(sessionId, { loading: false, error: UNEXPECTED_RESPONSE });
      }
      onDecodingChange(sessionId, false);
    },
    [onResult, onDecodingChange, patchRun]
  );

  const fail = useCallback(
    (sessionId: string, message: string) => {
      patchRun(sessionId, { loading: false, error: message });
      onDecodingChange(sessionId, false);
    },
    [onDecodingChange, patchRun]
  );

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
      onDecodingChange(sessionId, true);
      try {
        const response = await decodeStream(
          sessionId,
          text,
          (event) => pushEvent(sessionId, event),
          jurisdiction,
          institution
        );
        applyResponse(sessionId, response);
      } catch (err) {
        fail(sessionId, err instanceof Error ? err.message : 'Something went wrong.');
      } finally {
        inFlight.current.delete(sessionId);
      }
    },
    [applyResponse, fail, onDecodingChange, pushEvent]
  );

  // Upload a PDF/image and decode it. This path is a single request (not the
  // resumable SSE job), so it doesn't survive a refresh — but it shares the same
  // app-level run state, prompt handling, and result wiring as startDecode.
  const uploadDecode = useCallback(
    async (
      sessionId: string,
      file: File,
      jurisdiction?: string,
      institution?: UserProvidedInstitution | null
    ) => {
      if (inFlight.current.has(sessionId)) return;
      inFlight.current.add(sessionId);
      setRuns((prev) => ({
        ...prev,
        [sessionId]: { loading: true, events: [], error: null, prompt: null },
      }));
      onDecodingChange(sessionId, true);
      try {
        const response = await uploadDocument(file, jurisdiction, institution);
        applyResponse(sessionId, response);
      } catch (err) {
        fail(sessionId, err instanceof Error ? err.message : 'Could not read that file.');
      } finally {
        inFlight.current.delete(sessionId);
      }
    },
    [applyResponse, fail, onDecodingChange]
  );

  // Reconnect to a job that was already running (used after a page refresh).
  const resumeDecode = useCallback(
    async (sessionId: string) => {
      if (inFlight.current.has(sessionId)) return;
      inFlight.current.add(sessionId);
      setRuns((prev) => ({
        ...prev,
        [sessionId]: { loading: true, events: [], error: null, prompt: null },
      }));
      try {
        const response = await resumeDecodeStream(sessionId, (event) =>
          pushEvent(sessionId, event)
        );
        if (response === null) {
          fail(sessionId, INTERRUPTED);
        } else {
          applyResponse(sessionId, response);
        }
      } catch (err) {
        fail(sessionId, err instanceof Error ? err.message : 'Something went wrong.');
      } finally {
        inFlight.current.delete(sessionId);
      }
    },
    [applyResponse, fail, pushEvent]
  );

  const getRun = useCallback(
    (id: string): DecodeRun => runs[id] ?? EMPTY_RUN,
    [runs]
  );

  const loadingIds = Object.keys(runs).filter((id) => runs[id].loading);

  return { getRun, startDecode, uploadDecode, resumeDecode, loadingIds };
}
