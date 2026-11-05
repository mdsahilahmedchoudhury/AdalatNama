/**
 * AdalatNama mark: an open case diary with a brass ribbon marking today's page.
 * Colours are fixed (not theme tokens) so the mark reads the same everywhere.
 */
export function LogoMark({ size = 32, className }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      role="img"
      aria-label="AdalatNama"
      className={className}
    >
      <rect x="2" y="2" width="44" height="44" rx="11" fill="#12343B" />
      <path d="M9.5 14.6c4.7-1.7 9.4-1.4 14.5 1.2v20c-5.1-2.6-9.8-2.9-14.5-1.2z" fill="#F6F2E9" />
      <path d="M38.5 14.6c-4.7-1.7-9.4-1.4-14.5 1.2v20c5.1-2.6 9.8-2.9 14.5-1.2z" fill="#E6DCC6" />
      <path d="M29 14.9V27l2.6-2.1 2.6 2.1V14.2c-1.7-.1-3.4.1-5.2.7z" fill="#B5832A" />
      <path
        d="M13.2 20.2h7.2M13.2 24.2h7.2M13.2 28.2h4.8"
        stroke="#12343B"
        strokeWidth="1.7"
        strokeLinecap="round"
        opacity=".6"
      />
    </svg>
  );
}

export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={className} style={{ fontFamily: "var(--font-serif)" }}>
      <span className="font-semibold text-primary">Adalat</span>
      <span className="font-semibold text-accent">Nama</span>
    </span>
  );
}
