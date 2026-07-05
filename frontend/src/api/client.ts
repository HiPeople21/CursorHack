import type { DecodeRequest, DecodeResult } from '../types';
import { sampleResult } from '../mocks/sampleResult';

const USE_MOCK = import.meta.env.VITE_MOCK === '1';

// Simulate network latency in mock mode so loading states are visible.
function delay<T>(value: T, ms = 700): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

export async function decode(
  text: string,
  jurisdiction: string = 'IE'
): Promise<DecodeResult> {
  if (USE_MOCK) {
    return delay({ ...sampleResult, jurisdiction });
  }

  const payload: DecodeRequest = { text, jurisdiction };

  const res = await fetch('/api/decode', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(
      `decode request failed: ${res.status} ${res.statusText}${detail ? ` — ${detail}` : ''}`
    );
  }

  return (await res.json()) as DecodeResult;
}
