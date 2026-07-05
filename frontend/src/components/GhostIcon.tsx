interface GhostIconProps {
  className?: string;
  /** Outline for UI chrome; filled for the brand mark. */
  variant?: 'outline' | 'filled';
}

export default function GhostIcon({
  className = '',
  variant = 'filled',
}: GhostIconProps) {
  if (variant === 'outline') {
    return (
      <svg
        viewBox="0 0 20 20"
        fill="none"
        className={className}
        aria-hidden
      >
        <path
          d="M4 16V9a6 6 0 0 1 12 0v7l-2-1.3-2 1.3-2-1.3-2 1.3L4 16Z"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
        <circle cx="8" cy="9" r="0.9" fill="currentColor" stroke="none" />
        <circle cx="12" cy="9" r="0.9" fill="currentColor" stroke="none" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 20 20" fill="none" className={className} aria-hidden>
      <path
        d="M4 16V9a6 6 0 0 1 12 0v7l-2-1.3-2 1.3-2-1.3-2 1.3L4 16Z"
        fill="currentColor"
      />
      <circle cx="8" cy="9" r="0.9" fill="#ffffff" />
      <circle cx="12" cy="9" r="0.9" fill="#ffffff" />
    </svg>
  );
}
