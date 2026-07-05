interface GhostSpinnerProps {
  className?: string;
}

/**
 * A friendly ghost that bobs, blinks, and casts a pulsing shadow.
 * Used in place of a plain spinner while the pipeline is thinking.
 */
export default function GhostSpinner({
  className = 'h-7 w-7',
}: GhostSpinnerProps) {
  return (
    <span
      className={`relative inline-flex shrink-0 items-center justify-center ${className}`}
      aria-hidden
    >
      <svg
        viewBox="0 0 32 34"
        fill="none"
        className="animate-ghost-bob h-full w-full text-indigo-600 drop-shadow-[0_2px_6px_rgba(51,73,122,0.35)]"
      >
        {/* body with a wavy hem */}
        <path
          d="M16 3c-6.1 0-11 4.9-11 11v13.1c0 1.2 1.4 1.9 2.4 1.2l2.2-1.6 2.6 1.9c.5.4 1.2.4 1.7 0l2.1-1.6 2.6 1.9c.5.4 1.2.4 1.7 0l2.2-1.6 2.2 1.6c1 .7 2.4 0 2.4-1.2V14c0-6.1-4.9-11-11-11Z"
          fill="currentColor"
        />
        {/* eyes (blink together) */}
        <g className="animate-ghost-blink" fill="#0b1226">
          <ellipse cx="12" cy="15" rx="1.7" ry="2.2" />
          <ellipse cx="20" cy="15" rx="1.7" ry="2.2" />
        </g>
        {/* cheek highlights */}
        <circle cx="9.6" cy="18.5" r="1.3" fill="#ffffff" opacity="0.18" />
        <circle cx="22.4" cy="18.5" r="1.3" fill="#ffffff" opacity="0.18" />
      </svg>
      {/* ground shadow */}
      <span className="animate-ghost-glow absolute -bottom-0.5 h-1 w-1/2 rounded-full bg-indigo-500/50 blur-[1.5px]" />
    </span>
  );
}
