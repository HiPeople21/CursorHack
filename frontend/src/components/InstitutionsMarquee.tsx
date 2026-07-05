import LogoLoop, { type LogoItem } from './LogoLoop/LogoLoop';

const INSTITUTION_LOGOS: LogoItem[] = [
  { src: '/institution-logos/rtb.svg', alt: 'Residential Tenancies Board' },
  {
    src: '/institution-logos/revenue-ie.png',
    alt: 'Revenue Commissioners',
    invert: false,
  },
  { src: '/institution-logos/irs.svg', alt: 'Internal Revenue Service' },
  { src: '/institution-logos/fda.svg', alt: 'Food & Drug Administration' },
  { src: '/institution-logos/cms.svg', alt: 'Centers for Medicare & Medicaid Services' },
];

export default function InstitutionsMarquee() {
  return (
    <section
      aria-label="Institutions we support"
      className="bg-stone-900 py-6"
    >
      <div className="mx-auto mb-3 max-w-6xl px-5 sm:px-8">
        <h2 className="text-center text-sm font-semibold uppercase tracking-wider text-stone-400">
          Institutions we support
        </h2>
      </div>

      <div className="relative h-[52px] overflow-hidden">
        <LogoLoop
          logos={INSTITUTION_LOGOS}
          speed={100}
          direction="left"
          logoHeight={28}
          gap={60}
          hoverSpeed={0}
          scaleOnHover
          fadeOut
          fadeOutColor="#1c1917"
          ariaLabel="Institutions we support"
        />
      </div>
    </section>
  );
}
