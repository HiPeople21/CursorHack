// TS mirror of backend/app/schemas.py — THE CONTRACT.
// Keep this file in exact sync with the pydantic models in CLAUDE.md.
// If you change a shape here, change schemas.py too.

export interface Source {
  url: string;
  title: string;
  quote: string; // <15 words, verbatim from the page — the "receipt"
  retrieved_at: string; // ISO timestamp
}

export interface ExtractedFact {
  key: string; // e.g. "notice_period_days", "amount_due", "tenancy_start"
  value: string;
  span: string | null; // the exact text in the source doc it came from
}

export type ClaimStatus = 'supported' | 'contradicted' | 'unverifiable';

export interface Claim {
  statement: string;
  status: ClaimStatus;
  source: Source | null;
}

export type VerificationVerdict = 'matches' | 'mismatch' | 'cannot_determine';

export interface Verification {
  assertion: string; // what the LETTER claims ("14 days to respond")
  rule_value: string; // what the STATUTE says ("28 days minimum")
  verdict: VerificationVerdict;
  explanation: string;
  source: Source | null;
}

export type ActionKind = 'letter' | 'form' | 'email' | 'deadline' | 'contact';

export interface Action {
  title: string;
  kind: ActionKind;
  body: string; // drafted text, or contact/deadline detail
  deadline: string | null;
}

export type DocType =
  | 'tenancy'
  | 'insurance'
  | 'medical_bill'
  | 'gov_letter'
  | 'other';

export interface DecodeResult {
  id: string;
  doc_type: DocType;
  jurisdiction: string;
  plain_summary: string;
  extracted_facts: ExtractedFact[];
  claims: Claim[];
  verification: Verification[]; // the centerpiece — document vs rule
  actions: Action[];
  disclaimer: string;
}

export interface UserProvidedInstitution {
  body_id?: string | null; // registry slug, e.g. "rtb" or "IE:rtb"
  display_name?: string | null; // free text when slug is unknown
}

export interface DecodeRequest {
  text: string;
  jurisdiction?: string; // auto-detected from document when omitted
  institution?: UserProvidedInstitution | null;
}

export interface InstitutionSuggestion {
  body_id: string;
  display_name: string;
}

export interface InstitutionPrompt {
  message: string;
  field: string; // defaults to "institution"
  suggestions: InstitutionSuggestion[];
}

// POST /api/decode returns this wrapper, not a bare DecodeResult.
export interface DecodeResponse {
  status: 'complete' | 'needs_institution';
  institution_prompt: InstitutionPrompt | null;
  result: DecodeResult | null;
  lawyer_referral_eligible?: boolean;
  lawyer_referral_reason?: string;
}

// --- Lawyer referrals (standalone endpoint — not on DecodeResult) ---

export interface LawyerReferral {
  name: string;
  firm: string;
  practice_area: string;
  location: string;
  url: string | null;
  phone: string | null;
  reason: string;
}

export interface LawyerSearchLocation {
  city?: string | null;
  county?: string | null;
  jurisdiction?: string | null;
}

export interface LawyerRecommendRequest {
  doc_type?: DocType;
  jurisdiction?: string;
  location?: LawyerSearchLocation | null;
  profile_id?: string | null;
  plain_summary?: string;
  extracted_facts?: ExtractedFact[];
  claims?: Claim[];
  verification?: Verification[];
}

export interface LawyerRecommendResponse {
  referrals: LawyerReferral[];
  eligible: boolean;
  reason: string;
}

// GET /api/health
export interface HealthStatus {
  status: string;
  demo_mode: boolean;
  tls_enabled: boolean;
  profile_encryption: boolean;
}

// --- Profile (autofill) — mirrors UserProfile in schemas.py ---

export interface UserProfile {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  address_line1: string;
  address_line2: string | null;
  city: string;
  county: string;
  eircode: string | null;
  date_of_birth: string | null; // ISO date YYYY-MM-DD
  pps_number: string | null;
  jurisdiction: string;
  extra: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface UserProfileInput {
  full_name: string;
  email?: string | null;
  phone?: string | null;
  address_line1?: string;
  address_line2?: string | null;
  city?: string;
  county?: string;
  eircode?: string | null;
  date_of_birth?: string | null;
  pps_number?: string | null;
  jurisdiction?: string;
  extra?: Record<string, string>;
}

// --- Client-side only: a "chat" is one pasted document + its decode ---

export interface Session {
  id: string;
  title: string;
  text: string;
  jurisdiction: string;
  result: DecodeResult | null;
  createdAt: string;
  updatedAt: string;
  renamed?: boolean; // user set the title manually — don't auto-derive from text
}
