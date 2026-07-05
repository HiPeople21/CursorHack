interface LogoProps {
  className?: string;
  size?: 'sm' | 'md';
}

const SIZES = {
  sm: { mark: 'h-8', wordmark: 'h-[14px]' },
  md: { mark: 'h-10', wordmark: 'h-[18px]' },
} as const;

export default function Logo({ className = '', size = 'md' }: LogoProps) {
  const s = SIZES[size];

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <img
        src="/reywal-mark.png"
        alt=""
        aria-hidden
        draggable={false}
        className={`block ${s.mark} w-auto shrink-0 dark:brightness-0 dark:invert`}
      />
      <img
        src="/reywal-wordmark.png"
        alt="Reywal"
        draggable={false}
        className={`block ${s.wordmark} w-auto translate-y-px dark:brightness-0 dark:invert`}
      />
    </div>
  );
}
