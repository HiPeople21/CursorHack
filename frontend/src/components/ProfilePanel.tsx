import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import type { UserProfile, UserProfileInput } from '../types';
import {
  createProfile,
  deleteProfile,
  getProfile,
  updateProfile,
} from '../api/client';

const PROFILE_ID_KEY = 'standing.profileId.v1';

interface ProfilePanelProps {
  open: boolean;
  onClose: () => void;
  onSaved: (profile: UserProfile) => void;
  onDeleted: () => void;
}

type FormState = {
  full_name: string;
  email: string;
  phone: string;
  address_line1: string;
  address_line2: string;
  city: string;
  county: string;
  eircode: string;
  date_of_birth: string;
  pps_number: string;
};

const EMPTY: FormState = {
  full_name: '',
  email: '',
  phone: '',
  address_line1: '',
  address_line2: '',
  city: '',
  county: '',
  eircode: '',
  date_of_birth: '',
  pps_number: '',
};

function toForm(p: UserProfile): FormState {
  return {
    full_name: p.full_name ?? '',
    email: p.email ?? '',
    phone: p.phone ?? '',
    address_line1: p.address_line1 ?? '',
    address_line2: p.address_line2 ?? '',
    city: p.city ?? '',
    county: p.county ?? '',
    eircode: p.eircode ?? '',
    date_of_birth: p.date_of_birth ?? '',
    pps_number: p.pps_number ?? '',
  };
}

function toInput(f: FormState): UserProfileInput {
  const clean = (v: string) => (v.trim() === '' ? null : v.trim());
  return {
    full_name: f.full_name.trim(),
    email: clean(f.email),
    phone: clean(f.phone),
    address_line1: f.address_line1.trim(),
    address_line2: clean(f.address_line2),
    city: f.city.trim(),
    county: f.county.trim(),
    eircode: clean(f.eircode),
    date_of_birth: clean(f.date_of_birth),
    pps_number: clean(f.pps_number),
    jurisdiction: 'IE',
  };
}

function Field({
  label,
  value,
  onChange,
  type = 'text',
  placeholder,
  className = '',
  secret = false,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
  className?: string;
  secret?: boolean;
}) {
  const [revealed, setRevealed] = useState(false);
  const inputType = secret && !revealed ? 'password' : type;
  return (
    <label className={`block ${className}`}>
      <span className="mb-1 block text-xs font-semibold text-stone-600">
        {label}
      </span>
      <div className="relative">
        <input
          type={inputType}
          value={value}
          placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)}
          className={`w-full rounded-lg border border-stone-300 bg-stone-50 px-3 py-2 text-sm text-stone-800 focus:border-indigo-400 focus:bg-surface focus:outline-none focus:ring-2 focus:ring-indigo-100 ${
            secret ? 'pr-14' : ''
          }`}
        />
        {secret && (
          <button
            type="button"
            onClick={() => setRevealed((r) => !r)}
            className="absolute inset-y-0 right-2 my-auto h-fit text-xs font-semibold text-indigo-600 hover:text-indigo-700"
          >
            {revealed ? 'Hide' : 'Show'}
          </button>
        )}
      </div>
    </label>
  );
}

export default function ProfilePanel({
  open,
  onClose,
  onSaved,
  onDeleted,
}: ProfilePanelProps) {
  const [form, setForm] = useState<FormState>(EMPTY);
  const [profileId, setProfileId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  // Load existing profile whenever the panel opens.
  useEffect(() => {
    if (!open) return;
    const id = localStorage.getItem(PROFILE_ID_KEY);
    setError(null);
    setConfirmingDelete(false);
    if (!id) {
      setProfileId(null);
      setForm(EMPTY);
      return;
    }
    setProfileId(id);
    setLoading(true);
    getProfile(id)
      .then((p) => {
        if (p) setForm(toForm(p));
        else {
          localStorage.removeItem(PROFILE_ID_KEY);
          setProfileId(null);
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [open]);

  function set<K extends keyof FormState>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (saving) return;
    setSaving(true);
    setError(null);
    try {
      const input = toInput(form);
      const saved = profileId
        ? await updateProfile(profileId, input)
        : await createProfile(input);
      localStorage.setItem(PROFILE_ID_KEY, saved.id);
      setProfileId(saved.id);
      onSaved(saved);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save profile.');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!profileId) return;
    setSaving(true);
    setError(null);
    try {
      await deleteProfile(profileId);
      localStorage.removeItem(PROFILE_ID_KEY);
      setProfileId(null);
      setForm(EMPTY);
      setConfirmingDelete(false);
      onDeleted();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete profile.');
    } finally {
      setSaving(false);
    }
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#080d1c]/60 p-4"
      onClick={onClose}
    >
      <div
        className="flex max-h-[90vh] w-full max-w-lg flex-col overflow-hidden rounded-2xl bg-surface shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-stone-200 px-6 py-4">
          <div>
            <h2 className="text-lg font-black tracking-tight text-stone-900">
              Your profile
            </h2>
            <p className="mt-0.5 text-xs text-stone-500">
              Stored encrypted at rest. Used to autofill letters and forms.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-lg p-1 text-stone-400 hover:bg-stone-100 hover:text-stone-700"
          >
            <svg
              className="h-5 w-5"
              viewBox="0 0 20 20"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden
            >
              <path d="M5 5l10 10M15 5L5 15" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        <form
          onSubmit={handleSubmit}
          className="min-h-0 flex-1 overflow-y-auto px-6 py-5"
        >
          {loading ? (
            <p className="py-8 text-center text-sm text-stone-400">
              Loading profile…
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              <Field
                label="Full name"
                value={form.full_name}
                onChange={(v) => set('full_name', v)}
                placeholder="Jane Citizen"
                className="col-span-2"
              />
              <Field
                label="Email"
                type="email"
                value={form.email}
                onChange={(v) => set('email', v)}
                placeholder="jane@example.ie"
              />
              <Field
                label="Phone"
                value={form.phone}
                onChange={(v) => set('phone', v)}
                placeholder="+353 …"
              />
              <Field
                label="Address line 1"
                value={form.address_line1}
                onChange={(v) => set('address_line1', v)}
                placeholder="14 Oakwood Grove"
                className="col-span-2"
              />
              <Field
                label="Address line 2"
                value={form.address_line2}
                onChange={(v) => set('address_line2', v)}
                className="col-span-2"
              />
              <Field
                label="City / Town"
                value={form.city}
                onChange={(v) => set('city', v)}
                placeholder="Dublin"
              />
              <Field
                label="County"
                value={form.county}
                onChange={(v) => set('county', v)}
                placeholder="Dublin"
              />
              <Field
                label="Eircode"
                value={form.eircode}
                onChange={(v) => set('eircode', v)}
                placeholder="D09 XY12"
              />
              <Field
                label="Date of birth"
                type="date"
                value={form.date_of_birth}
                onChange={(v) => set('date_of_birth', v)}
              />
              <Field
                label="PPS number"
                value={form.pps_number}
                onChange={(v) => set('pps_number', v)}
                placeholder="1234567AB"
                className="col-span-2"
                secret
              />
            </div>
          )}

          {error && (
            <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}
        </form>

        <div className="flex items-center justify-end gap-2 border-t border-stone-200 px-6 py-4">
          {profileId &&
            (confirmingDelete ? (
              <div className="mr-auto flex items-center gap-2">
                <span className="text-xs font-medium text-stone-500">
                  Delete profile?
                </span>
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={saving}
                  className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700 disabled:opacity-50"
                >
                  Yes, delete
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmingDelete(false)}
                  className="rounded-lg px-2 py-1.5 text-xs font-semibold text-stone-500 hover:bg-stone-100"
                >
                  No
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setConfirmingDelete(true)}
                className="mr-auto rounded-lg px-3 py-2 text-sm font-semibold text-red-600 hover:bg-red-50"
              >
                Delete
              </button>
            ))}
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm font-semibold text-stone-600 hover:bg-stone-100"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={saving || loading || form.full_name.trim() === ''}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-stone-300"
          >
            {saving && (
              <span
                aria-hidden
                className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
              />
            )}
            {saving ? 'Saving…' : 'Save profile'}
          </button>
        </div>
      </div>
    </div>
  );
}

export { PROFILE_ID_KEY };
