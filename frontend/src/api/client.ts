import type {
  DecodeProgressEvent,
  DecodeRequest,
  DecodeResponse,
  DecodeResult,
  HealthStatus,
  UserProfile,
  UserProfileInput,
  UserProvidedInstitution,
} from '../types';
import { sampleResult } from '../mocks/sampleResult';

const USE_MOCK = import.meta.env.VITE_MOCK === '1';

// Simulate network latency in mock mode so loading states are visible.
function delay<T>(value: T, ms = 700): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

async function readError(res: Response): Promise<string> {
  const detail = await res.text().catch(() => '');
  return `${res.status} ${res.statusText}${detail ? ` — ${detail}` : ''}`;
}

export async function decode(
  text: string,
  jurisdiction?: string,
  institution?: UserProvidedInstitution | null
): Promise<DecodeResponse> {
  if (USE_MOCK) {
    return delay({
      status: 'complete',
      institution_prompt: null,
      result: { ...sampleResult, jurisdiction: jurisdiction || sampleResult.jurisdiction },
      lawyer_referral_eligible: false,
      lawyer_referral_reason: '',
    });
  }

  const payload: DecodeRequest = { text };
  if (jurisdiction) payload.jurisdiction = jurisdiction;
  if (institution) payload.institution = institution;

  const res = await fetch('/api/decode', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`decode request failed: ${await readError(res)}`);
  }

  return (await res.json()) as DecodeResponse;
}

export async function uploadDocument(
  file: File,
  jurisdiction?: string,
  institution?: UserProvidedInstitution | null
): Promise<DecodeResponse> {
  if (USE_MOCK) {
    return delay({
      status: 'complete',
      institution_prompt: null,
      result: { ...sampleResult, jurisdiction: jurisdiction || sampleResult.jurisdiction },
      lawyer_referral_eligible: false,
      lawyer_referral_reason: '',
    });
  }

  const form = new FormData();
  form.append('file', file);
  form.append('jurisdiction', jurisdiction || 'IE');
  if (institution?.body_id) form.append('institution_body_id', institution.body_id);
  if (institution?.display_name)
    form.append('institution_name', institution.display_name);

  // No Content-Type header — the browser sets the multipart boundary itself.
  const res = await fetch('/api/decode/upload', {
    method: 'POST',
    body: form,
  });

  if (!res.ok) {
    throw new Error(`upload failed: ${await readError(res)}`);
  }

  return (await res.json()) as DecodeResponse;
}

// Ordered (stage, running-label, done-detail) tuples used to fake a live
// pipeline in mock mode so the ThinkingPanel looks identical to the real thing.
const MOCK_STEPS: Array<[DecodeProgressEvent['stage'], string, string]> = [
  ['classify', 'Reading the document and working out what it is…', 'Looks like a tenancy notice · IE'],
  ['identify', 'Identifying the issuing authority…', 'Authority: Residential Tenancies Board'],
  ['extract', 'Extracting your specific facts…', 'Pulled out 4 fact(s)'],
  ['retrieve', 'Searching for the current governing rules…', 'Found 2 candidate source(s)'],
  ['ground', 'Reading the source pages…', 'Read 6 passage(s)'],
  ['verify', 'Checking the document against the law…', '4 check(s) · 2 mismatch(es) found'],
  ['act', 'Drafting what you can do next…', 'Prepared 4 recommended action(s)'],
  ['refer', 'Checking whether a lawyer referral applies…', 'No lawyer referral needed'],
];

// Reads an SSE response body, invoking `onEvent` per frame. Returns the final
// DecodeResponse (from a terminal frame) or null if the stream ended without
// one. Throws if the server emitted an explicit error frame.
async function readSse(
  res: Response,
  onEvent: (event: DecodeProgressEvent) => void
): Promise<DecodeResponse | null> {
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let final: DecodeResponse | null = null;
  let errorDetail: string | null = null;

  const handleFrame = (raw: string) => {
    // An SSE frame is one or more "data: ..." lines; we only send single-line
    // JSON payloads, but concatenate defensively.
    const data = raw
      .split('\n')
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trim())
      .join('');
    if (!data) return;
    const event = JSON.parse(data) as DecodeProgressEvent;
    onEvent(event);
    if (event.response) final = event.response;
    if (event.stage === ('error' as DecodeProgressEvent['stage'])) {
      errorDetail = event.detail ?? 'The decode failed on the server.';
    }
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sep: number;
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      if (frame.trim()) handleFrame(frame);
    }
  }
  if (buffer.trim()) handleFrame(buffer);

  if (errorDetail) throw new Error(errorDetail);
  return final;
}

/**
 * Start a decode job and stream its progress. `sessionId` is used as the server
 * job id so the run can be reconnected to after a page refresh. Resolves with
 * the final DecodeResponse.
 */
export async function decodeStream(
  sessionId: string,
  text: string,
  onEvent: (event: DecodeProgressEvent) => void,
  jurisdiction?: string,
  institution?: UserProvidedInstitution | null
): Promise<DecodeResponse> {
  if (USE_MOCK) {
    for (const [stage, label, detail] of MOCK_STEPS) {
      onEvent({ stage, status: 'running', label });
      await delay(null, 450);
      onEvent({ stage, status: 'done', detail });
    }
    const response: DecodeResponse = {
      status: 'complete',
      institution_prompt: null,
      result: { ...sampleResult, jurisdiction: jurisdiction || sampleResult.jurisdiction },
      lawyer_referral_eligible: false,
      lawyer_referral_reason: '',
    };
    onEvent({ stage: 'complete', status: 'done', response });
    return response;
  }

  const payload: DecodeRequest = { text };
  if (jurisdiction) payload.jurisdiction = jurisdiction;
  if (institution) payload.institution = institution;

  const res = await fetch(`/api/decode/stream?job_id=${encodeURIComponent(sessionId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok || !res.body) {
    throw new Error(`decode request failed: ${await readError(res)}`);
  }

  const final = await readSse(res, onEvent);
  if (!final) {
    throw new Error(
      'The server closed the stream without a final result. It may be running ' +
        'an older version — try restarting the backend and decoding again.'
    );
  }
  return final;
}

/**
 * Reconnect to a decode job started earlier (e.g. before a page refresh),
 * replaying its progress and streaming until it finishes. Returns the final
 * DecodeResponse, or null if the job is gone (server never had it, restarted,
 * or it expired) so the caller can prompt the user to re-run.
 */
export async function resumeDecodeStream(
  sessionId: string,
  onEvent: (event: DecodeProgressEvent) => void
): Promise<DecodeResponse | null> {
  if (USE_MOCK) return null; // no server-side job to reconnect to

  const res = await fetch(`/api/decode/stream/${encodeURIComponent(sessionId)}`);
  if (res.status === 404) return null;
  if (!res.ok || !res.body) {
    throw new Error(`resume request failed: ${await readError(res)}`);
  }
  return readSse(res, onEvent);
}

// --- History ---

export async function listDocuments(): Promise<DecodeResult[]> {
  const res = await fetch('/api/documents');
  if (!res.ok) throw new Error(`list documents failed: ${await readError(res)}`);
  return (await res.json()) as DecodeResult[];
}

export async function getDocument(id: string): Promise<DecodeResult | null> {
  const res = await fetch(`/api/documents/${id}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`get document failed: ${await readError(res)}`);
  return (await res.json()) as DecodeResult;
}

// --- Health ---

export async function getHealth(): Promise<HealthStatus | null> {
  if (USE_MOCK) {
    return {
      status: 'ok',
      demo_mode: true,
      tls_enabled: false,
      profile_encryption: false,
    };
  }
  try {
    const res = await fetch('/api/health');
    if (!res.ok) return null;
    return (await res.json()) as HealthStatus;
  } catch {
    return null;
  }
}

// --- Profile ---

export async function getProfile(id: string): Promise<UserProfile | null> {
  const res = await fetch(`/api/profile/${id}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`load profile failed: ${await readError(res)}`);
  return (await res.json()) as UserProfile;
}

export async function createProfile(
  input: UserProfileInput
): Promise<UserProfile> {
  const res = await fetch('/api/profile', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`create profile failed: ${await readError(res)}`);
  return (await res.json()) as UserProfile;
}

export async function updateProfile(
  id: string,
  input: UserProfileInput
): Promise<UserProfile> {
  const res = await fetch(`/api/profile/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`update profile failed: ${await readError(res)}`);
  return (await res.json()) as UserProfile;
}

export async function deleteProfile(id: string): Promise<void> {
  const res = await fetch(`/api/profile/${id}`, { method: 'DELETE' });
  if (!res.ok && res.status !== 404) {
    throw new Error(`delete profile failed: ${await readError(res)}`);
  }
}
