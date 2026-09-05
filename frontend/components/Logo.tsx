// JKT48Verse brand mark — inline SVG so it stays crisp at any size and
// inherits the red/white brand palette. Mirrors app/icon.svg.
import { useId } from "react";

const SHAPE = "M256 0 C396.8 0 512 115.2 512 256 C512 396.8 396.8 512 256 512 C115.2 512 0 396.8 0 256 C0 115.2 115.2 0 256 0 Z";

export default function Logo({ size = 34, className = "", title = "JKT48Verse" }: { size?: number; className?: string; title?: string }) {
  const uid = useId().replace(/[^a-zA-Z0-9]/g, "");
  const bg = `jv-bg-${uid}`;
  const sheen = `jv-sheen-${uid}`;
  const shape = `jv-shape-${uid}`;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 512 512"
      role="img"
      aria-label={title}
      className={className}
      style={{ flexShrink: 0, display: "inline-block", borderRadius: size * 0.22, boxShadow: "0 4px 10px -2px rgba(224, 27, 60, 0.5)" }}
    >
      <defs>
        <linearGradient id={bg} x1="0" y1="0" x2="0.25" y2="1">
          <stop offset="0" stopColor="#ff5573" />
          <stop offset="0.48" stopColor="#e81f40" />
          <stop offset="1" stopColor="#b30c2a" />
        </linearGradient>
        <linearGradient id={sheen} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.18" />
          <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
        </linearGradient>
        <clipPath id={shape}>
          <path d={SHAPE} />
        </clipPath>
      </defs>

      <path d={SHAPE} fill={`url(#${bg})`} />

      <g clipPath={`url(#${shape})`}>
        <path d={SHAPE} fill={`url(#${sheen})`} transform="matrix(1 0 0 0.32 0 26)" />
        <path d={SHAPE} fill="#000000" opacity="0.08" transform="matrix(1 0 0 0.3 0 332)" />
      </g>

      <path d="M292 158 L292 296 C292 344 262 372 224 372 C196 372 176 352 172 326" fill="none" stroke="#ffffff" strokeWidth="66" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M392 96 Q400 122 426 130 Q400 138 392 164 Q384 138 358 130 Q384 122 392 96 Z" fill="#ffffff" />
      <path d="M128 384 Q133 397 146 402 Q133 407 128 420 Q123 407 110 402 Q123 397 128 384 Z" fill="#ffffff" opacity="0.92" />
    </svg>
  );
}
