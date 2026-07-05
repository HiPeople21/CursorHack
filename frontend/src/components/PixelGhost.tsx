interface PixelGhostProps {
  className?: string;
}

// Blocky pixel-art ghost. Each '#' is one pixel cell; the gaps at the eyes and
// the wavy hem are left empty so the background shows through.
const ROWS = [
  '   #####   ',
  '  #######  ',
  ' ######### ',
  ' ## ### ## ',
  '### ### ###',
  '###########',
  '###########',
  '###########',
  '###########',
  '###########',
  '###########',
  '## ## ## ##',
];

const CELL = 10;

export default function PixelGhost({ className = '' }: PixelGhostProps) {
  const cols = ROWS[0].length;
  const rows = ROWS.length;
  const cells: { x: number; y: number }[] = [];
  ROWS.forEach((row, y) => {
    [...row].forEach((c, x) => {
      if (c === '#') cells.push({ x, y });
    });
  });

  return (
    <svg
      viewBox={`0 0 ${cols * CELL} ${rows * CELL}`}
      className={className}
      fill="currentColor"
      shapeRendering="crispEdges"
      aria-hidden
    >
      {cells.map(({ x, y }) => (
        <rect
          key={`${x}-${y}`}
          x={x * CELL}
          y={y * CELL}
          width={CELL}
          height={CELL}
        />
      ))}
    </svg>
  );
}
