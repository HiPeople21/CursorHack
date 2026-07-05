import type { DecodeResult } from '../types';

// Canned response for VITE_MOCK=1 and for local dev without a backend.
// Money demo: a defective RTB termination notice whose stated notice
// period (14 days) is shorter than the statutory minimum (28 days),
// so the verification panel fires a clear MISMATCH.
export const sampleResult: DecodeResult = {
  id: 'demo-rtb-001',
  doc_type: 'tenancy',
  jurisdiction: 'IE',
  plain_summary:
    'Your landlord sent a Notice of Termination ending your tenancy of 2 years and 3 months, ' +
    'giving you 14 days to vacate. Under Irish law, tenancies of this length require a minimum ' +
    'of 84 days’ notice, and the notice may also be invalid for other reasons below.',
  extracted_facts: [
    {
      key: 'notice_period_days',
      value: '14',
      span: 'you are required to vacate the property within 14 days of this notice',
    },
    {
      key: 'tenancy_duration',
      value: '2 years, 3 months',
      span: 'tenancy commenced on 3 April 2023',
    },
    {
      key: 'termination_reason',
      value: 'landlord intends to sell the property',
      span: 'the landlord intends to sell the property within the next 3 months',
    },
    {
      key: 'notice_date',
      value: '2026-06-21',
      span: 'Date of this notice: 21 June 2026',
    },
  ],
  claims: [
    {
      statement:
        'The tenancy has lasted 2 years and 3 months as of the notice date.',
      status: 'supported',
      source: {
        url: 'https://www.citizensinformation.ie/en/housing/renting-a-home/ending-a-tenancy/notice-periods-for-landlords/',
        title: 'Notice periods for landlords - Citizens Information',
        quote: 'notice periods increase with the length of the tenancy',
        retrieved_at: '2026-07-05T09:12:00Z',
      },
    },
    {
      statement:
        'Sale of the property is a valid ground for termination during the first two years for some tenancies, but this tenancy has passed that threshold.',
      status: 'contradicted',
      source: {
        url: 'https://www.rtb.ie/beginning-a-tenancy/ending-a-tenancy',
        title: 'Ending a tenancy - RTB',
        quote: 'landlords must have a valid reason to end a tenancy after 6 months',
        retrieved_at: '2026-07-05T09:13:00Z',
      },
    },
    {
      statement: 'The notice states the correct date it was served.',
      status: 'unverifiable',
      source: null,
    },
  ],
  verification: [
    {
      assertion: '14 days to vacate the property',
      rule_value:
        '84 days’ minimum notice for a tenancy of between 2 and 3 years',
      verdict: 'mismatch',
      explanation:
        'The letter gives 14 days, but this tenancy has lasted over 2 years, which under the ' +
        'Residential Tenancies Act requires a minimum of 84 days’ notice from the landlord. ' +
        'This notice is defective and likely invalid.',
      source: {
        url: 'https://www.citizensinformation.ie/en/housing/renting-a-home/ending-a-tenancy/notice-periods-for-landlords/',
        title: 'Notice periods for landlords - Citizens Information',
        quote: '2 years or more but less than 3 years: 84 days',
        retrieved_at: '2026-07-05T09:12:00Z',
      },
    },
    {
      assertion: 'Termination is valid because landlord intends to sell',
      rule_value:
        'Sale is a valid ground, but the notice must meet the statutory notice period and be in the prescribed form',
      verdict: 'mismatch',
      explanation:
        'Selling the property can be a valid ground for termination, but it does not override the ' +
        'minimum notice period requirement, which this notice fails to meet.',
      source: {
        url: 'https://www.rtb.ie/beginning-a-tenancy/ending-a-tenancy',
        title: 'Ending a tenancy - RTB',
        quote: 'the required notice period must still be given',
        retrieved_at: '2026-07-05T09:13:00Z',
      },
    },
    {
      assertion: 'Notice was served in the prescribed statutory form',
      rule_value:
        'Notice of termination must be in writing, signed, and use the RTB-approved format',
      verdict: 'cannot_determine',
      explanation:
        'The pasted text does not show a signature or explicit statement of tenant rights required ' +
        'by the prescribed form, but this cannot be fully confirmed from the extracted text alone.',
      source: null,
    },
    {
      assertion: 'Notice date is 21 June 2026',
      rule_value: 'No specific statutory format requirement contradicts this',
      verdict: 'matches',
      explanation:
        'The stated notice date is consistent with a validly dated notice; no rule conflict found.',
      source: {
        url: 'https://www.rtb.ie/beginning-a-tenancy/ending-a-tenancy',
        title: 'Ending a tenancy - RTB',
        quote: 'the notice period begins on the date the notice is served',
        retrieved_at: '2026-07-05T09:13:00Z',
      },
    },
  ],
  actions: [
    {
      title: 'Appeal letter to landlord disputing notice period',
      kind: 'letter',
      body:
        'Dear [Landlord Name],\n\n' +
        'I am writing regarding the Notice of Termination dated 21 June 2026 in respect of the ' +
        'tenancy at [Address], which states that I must vacate within 14 days.\n\n' +
        'Under the Residential Tenancies Acts, as summarised by Citizens Information, a tenancy that ' +
        'has lasted “2 years or more but less than 3 years” requires a minimum notice period of ' +
        '84 days. As my tenancy commenced on 3 April 2023 and has therefore lasted over 2 years, the ' +
        '14-day notice period given falls well short of this statutory minimum.\n\n' +
        'I consider this Notice of Termination to be invalid on this basis. I do not intend to vacate ' +
        'the property within 14 days and reserve my right to remain until a valid notice, meeting the ' +
        'correct statutory notice period, is served.\n\n' +
        'I would welcome the opportunity to discuss this further, and I am also entitled to refer this ' +
        'matter to the Residential Tenancies Board (RTB) for a determination if needed.\n\n' +
        'Yours sincerely,\n[Your Name]',
      deadline: '2026-07-19',
    },
    {
      title: 'File a dispute with the Residential Tenancies Board (RTB)',
      kind: 'form',
      body:
        'RTB Dispute Resolution Application — Referral of a dispute regarding validity of Notice of ' +
        'Termination. Pre-filled details: Notice date 21 June 2026; Notice period given 14 days; ' +
        'Statutory minimum applicable 84 days; Ground for dispute: invalid notice period under the ' +
        'Residential Tenancies Act. Submit via the RTB online portal at rtb.ie within the relevant time ' +
        'limit after receiving the notice.',
      deadline: '2026-09-19',
    },
    {
      title: 'Contact Threshold (tenant support service) for advice',
      kind: 'contact',
      body:
        'Threshold provides free, confidential advice to tenants facing termination notices. ' +
        'National Freephone: 1800 454 454. Have your notice and tenancy start date ready when you call.',
      deadline: null,
    },
    {
      title: 'Response deadline before any action is required',
      kind: 'deadline',
      body:
        'You are not required to vacate by the date stated in the notice, because the notice period ' +
        'given (14 days) is shorter than the legal minimum (84 days) for a tenancy of this length. ' +
        'Treat 14 days as invalid; the true earliest valid vacate date is calculated at 21 June 2026 + 84 days.',
      deadline: '2026-09-13',
    },
  ],
  disclaimer:
    'This is information, not legal advice. reywal cites the sources it used above so you can ' +
    'verify them yourself; for advice specific to your situation, contact Threshold or a solicitor.',
};
