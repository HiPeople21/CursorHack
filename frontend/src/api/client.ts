import type {
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
  jurisdiction: string = 'IE',
  institution?: UserProvidedInstitution | null
): Promise<DecodeResponse> {
  if (USE_MOCK) {
    return delay({
      status: 'complete',
      institution_prompt: null,
      result: { ...sampleResult, jurisdiction },
    });
  }

  const payload: DecodeRequest = { text, jurisdiction };
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
