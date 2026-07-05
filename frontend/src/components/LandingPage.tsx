import HeroDocument from './HeroDocument';
import Logo from './Logo';
import InstitutionsMarquee from './InstitutionsMarquee';

interface LandingPageProps {
  onGetStarted: () => void;
}

const STEPS = [
  {
    num: '01',
    title: 'Paste your document',
    body: 'Drop in a tenancy notice, insurance denial, medical bill, or government letter — the full text, not a summary.',
  },
  {
    num: '02',
    title: 'We extract your facts',
    body: 'Dates, amounts, notice periods, and deadlines are pulled out with the exact span each one came from.',
  },
  {
    num: '03',
    title: 'We find the governing rule',
    body: 'Live search retrieves the current statute or guidance for your jurisdiction — RTB, Citizens Information, gov.ie.',
  },
  {
    num: '04',
    title: 'We verify and respond',
    body: 'Every claim is checked against the rule. Mismatches get cited sources and a draft appeal letter.',
  },
] as const;

const FEATURES = [
  {
    title: 'Verification, not summaries',
    body: 'A clear verdict for each assertion: matches the rule, contradicts it, or cannot be determined from available sources.',
    icon: (
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
      />
    ),
  },
  {
    title: 'Receipts on every claim',
    body: 'Each claim links to a real source — URL, title, and a verbatim quote under 15 words. No citation is ever invented.',
    icon: (
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
      />
    ),
  },
  {
    title: 'Actions ready to send',
    body: 'Appeal letters, dispute forms, deadline reminders, and contact steps — generated from verified facts, not guesses.',
    icon: (
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10"
      />
    ),
  },
] as const;

function NavLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      className="text-sm font-medium text-stone-600 transition hover:text-indigo-700"
    >
      {children}
    </a>
  );
}

export default function LandingPage({ onGetStarted }: LandingPageProps) {
  return (
    <div className="font-brand min-h-screen bg-stone-100">
      {/* Navbar — fixed over full-viewport hero */}
      <header className="fixed top-0 left-0 right-0 z-50 px-4 pt-3 sm:px-6">
        <nav className="mx-auto flex max-w-5xl items-center justify-between rounded-full border border-white/60 bg-white/45 px-4 py-2 shadow-[0_2px_16px_rgba(28,25,23,0.06)] backdrop-blur-xl backdrop-saturate-150 sm:px-6">
          <Logo size="sm" />
          <div className="hidden items-center gap-7 md:flex">
            <NavLink href="#how-it-works">How it works</NavLink>
            <NavLink href="#features">Features</NavLink>
            <NavLink href="#example">Example</NavLink>
          </div>
          <button
            type="button"
            onClick={onGetStarted}
            className="rounded-full bg-indigo-600 px-4 py-1.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700"
          >
            Get started
          </button>
        </nav>
      </header>

      {/* Hero — exactly one viewport tall */}
      <section className="relative h-dvh min-h-dvh overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-10%,rgba(92,110,58,0.14),transparent)]"
        />
        <div className="relative mx-auto flex h-full max-w-6xl items-center px-5 sm:px-8">
          <div className="grid w-full items-center gap-10 py-20 lg:grid-cols-2 lg:gap-16 lg:py-24">
            <div className="animate-fade-up">
              <h1 className="text-4xl font-semibold leading-[1.1] tracking-[-0.02em] text-black sm:text-5xl lg:text-[3.25rem]">
                They wrote the letter.
                <br />
                We check the law.
              </h1>
              <p className="mt-5 max-w-lg text-lg leading-relaxed text-stone-600">
                Paste an official document. reywal extracts your specific facts,
                retrieves the current governing rule, verifies whether the
                document is even lawful, and drafts your response — with a
                cited source for every claim.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-4">
                <button
                  type="button"
                  onClick={onGetStarted}
                  className="rounded-lg bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-md transition hover:bg-indigo-700 hover:shadow-lg"
                >
                  Decode a document
                </button>
                <a
                  href="#how-it-works"
                  className="text-sm font-semibold text-indigo-700 underline-offset-4 transition hover:underline"
                >
                  See how it works
                </a>
              </div>
            </div>

            <div className="animate-fade-up-delay flex h-full min-h-0 items-center justify-center lg:justify-end">
              <HeroDocument />
            </div>
          </div>
        </div>
      </section>

      <InstitutionsMarquee />

      {/* How it works */}
      <section
        id="how-it-works"
        className="border-t border-stone-200 bg-white py-20 sm:py-24"
      >
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="max-w-2xl">
            <h2 className="text-3xl font-semibold tracking-tight text-stone-900 sm:text-4xl">
              How it works
            </h2>
            <p className="mt-3 text-lg text-stone-600">
              Not &ldquo;here&apos;s what this document means&rdquo; —{' '}
              <em className="not-italic font-medium text-stone-800">
                here&apos;s what they got wrong and here&apos;s your appeal.
              </em>
            </p>
          </div>
          <ol className="mt-14 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((step) => (
              <li key={step.num} className="relative">
                <span className="text-4xl font-semibold text-indigo-200">
                  {step.num}
                </span>
                <h3 className="mt-2 text-lg font-semibold text-stone-900">
                  {step.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-stone-600">
                  {step.body}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-20 sm:py-24">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-semibold tracking-tight text-stone-900 sm:text-4xl">
              Why not just ask a chatbot?
            </h2>
            <p className="mx-auto mt-3 max-w-2xl text-lg text-stone-600">
              A general LLM can summarize and guess. reywal grounds every claim
              in a live source and tells you explicitly when something
              doesn&apos;t add up.
            </p>
          </div>
          <ul className="mt-14 grid gap-6 md:grid-cols-3">
            {FEATURES.map((f) => (
              <li
                key={f.title}
                className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm transition hover:border-indigo-200 hover:shadow-md"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                  <svg
                    className="h-5 w-5"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    aria-hidden
                  >
                    {f.icon}
                  </svg>
                </div>
                <h3 className="mt-4 text-lg font-semibold text-stone-900">
                  {f.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-stone-600">
                  {f.body}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Example */}
      <section
        id="example"
        className="border-y border-stone-200 bg-indigo-950 py-20 text-white sm:py-24"
      >
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="grid items-center gap-12 lg:grid-cols-2">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wider text-indigo-300">
                The money demo
              </p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
                Defective RTB termination notice
              </h2>
              <p className="mt-4 leading-relaxed text-indigo-100/90">
                Paste a tenancy termination with a notice period shorter than the
                statutory minimum. The verification panel fires{' '}
                <span className="font-semibold text-white">MISMATCH</span> with
                a cited Citizens Information quote — plus a generated appeal
                letter ready to send.
              </p>
              <button
                type="button"
                onClick={onGetStarted}
                className="mt-8 rounded-lg bg-white px-6 py-3 text-sm font-semibold text-indigo-950 transition hover:bg-indigo-50"
              >
                Try it now
              </button>
            </div>
            <div className="rounded-2xl border border-indigo-800 bg-indigo-900/50 p-6 backdrop-blur">
              <p className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
                Document types supported
              </p>
              <ul className="mt-4 grid grid-cols-2 gap-3">
                {[
                  'Tenancy notices',
                  'Insurance denials',
                  'Medical bills',
                  'Government letters',
                ].map((type) => (
                  <li
                    key={type}
                    className="flex items-center gap-2 rounded-lg bg-indigo-900/60 px-3 py-2.5 text-sm text-indigo-50"
                  >
                    <svg
                      className="h-4 w-4 shrink-0 text-indigo-400"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      aria-hidden
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
                        clipRule="evenodd"
                      />
                    </svg>
                    {type}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 sm:py-24">
        <div className="mx-auto max-w-3xl px-5 text-center sm:px-8">
          <h2 className="text-3xl font-semibold tracking-tight text-stone-900 sm:text-4xl">
            Ready to decode your document?
          </h2>
          <p className="mt-4 text-lg text-stone-600">
            Paste the full text of an official letter. We&apos;ll tell you what
            holds up, what doesn&apos;t, and what to do next.
          </p>
          <button
            type="button"
            onClick={onGetStarted}
            className="mt-8 rounded-lg bg-indigo-600 px-8 py-3.5 text-sm font-semibold text-white shadow-md transition hover:bg-indigo-700"
          >
            Get started — it&apos;s free
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-stone-200 bg-white py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 px-5 sm:flex-row sm:px-8">
          <Logo />
          <p className="max-w-md text-center text-xs leading-relaxed text-stone-400 sm:text-right">
            Information, not legal advice. reywal cites the sources it uses so
            you can verify them yourself.
          </p>
        </div>
      </footer>
    </div>
  );
}
