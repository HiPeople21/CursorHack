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

export interface DecodeRequest {
  text: string;
  jurisdiction?: string; // defaults to "IE"
}
