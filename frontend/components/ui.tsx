import type { ReactNode, SVGProps } from "react";
import Link from "next/link";

// ---------- Icons (Lucide-style, stroke 2, no CDN) ----------
const PATHS: Record<string, ReactNode> = {
  home: <><path d="M3 11 12 3l9 8" /><path d="M5 10v10h14V10" /></>,
  radio: <><circle cx="12" cy="12" r="2" /><path d="M16.2 7.8a6 6 0 0 1 0 8.4M7.8 16.2a6 6 0 0 1 0-8.4M19.1 4.9a10 10 0 0 1 0 14.2M4.9 19.1a10 10 0 0 1 0-14.2" /></>,
  users: <><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20a6.5 6.5 0 0 1 13 0" /><circle cx="17" cy="9" r="2.5" /><path d="M16 15.5a5 5 0 0 1 5.5 4.5" /></>,
  user: <><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></>,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="3" /><path d="M3 10h18M8 3v4M16 3v4" /></>,
  news: <><rect x="3" y="4" width="18" height="16" rx="3" /><path d="M7 8h10M7 12h10M7 16h6" /></>,
  chat: <><path d="M4 5h16v11H9l-5 4z" /></>,
  gamepad: <><rect x="2" y="7" width="20" height="11" rx="5" /><path d="M7 11v3M5.5 12.5h3M15.5 12h.01M18 14h.01" /></>,
  spark: <><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8" /></>,
  shield: <><path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z" /></>,
  search: <><circle cx="11" cy="11" r="6.5" /><path d="m20 20-4.2-4.2" /></>,
  bell: <><path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z" /><path d="M10 21h4" /></>,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
  moon: <><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" /></>,
  menu: <><path d="M4 7h16M4 12h16M4 17h16" /></>,
  x: <><path d="M6 6l12 12M18 6 6 18" /></>,
  play: <><path d="M7 5v14l12-7z" /></>,
  stop: <><rect x="6" y="6" width="12" height="12" rx="2" /></>,
  refresh: <><path d="M20 12a8 8 0 1 1-2.3-5.7" /><path d="M20 4v5h-5" /></>,
  pip: <><rect x="3" y="5" width="18" height="14" rx="2" /><rect x="12" y="11" width="7" height="5" rx="1" /></>,
  fullscreen: <><path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5" /></>,
  heart: <><path d="M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 10c0 5.5-7 10-7 10z" /></>,
  gift: <><rect x="3" y="9" width="18" height="12" rx="2" /><path d="M12 9v12M3 13h18M12 9c-2-4-6-4-6-1s4 1 6 1zm0 0c2-4 6-4 6-1s-4 1-6 1z" /></>,
  trophy: <><path d="M8 4h8v5a4 4 0 0 1-8 0zM8 6H5a3 3 0 0 0 3 4M16 6h3a3 3 0 0 1-3 4M12 13v4M8 21h8M9 17h6" /></>,
  flame: <><path d="M12 3c1 4 5 5 5 10a5 5 0 0 1-10 0c0-2 1-3 2-4 0 2 1 3 2 3 0-4 0-6 1-9z" /></>,
  clock: <><circle cx="12" cy="12" r="8" /><path d="M12 8v4l3 2" /></>,
  bookmark: <><path d="M6 4h12v17l-6-4-6 4z" /></>,
  send: <><path d="M21 3 3 10l8 3 3 8z" /></>,
  zap: <><path d="M13 2 4 14h7l-1 8 9-12h-7z" /></>,
  chevron: <><path d="m9 6 6 6-6 6" /></>,
  chevronL: <><path d="m15 6-6 6 6 6" /></>,
  plus: <><path d="M12 5v14M5 12h14" /></>,
  location: <><path d="M12 21s-6-5.5-6-11a6 6 0 0 1 12 0c0 5.5-6 11-6 11z" /><circle cx="12" cy="10" r="2" /></>,
  cast: <><path d="M3 18a3 3 0 0 1 3 3M3 14a7 7 0 0 1 7 7M3 10a11 11 0 0 1 11 11" /><path d="M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3" /></>,
  book: <><path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z" /><path d="M4 19a2 2 0 0 1 2-2h13" /></>,
  check: <><path d="m5 12 5 5L20 7" /></>,
  flag: <><path d="M5 21V4h11l-1.5 3.5L16 11H5" /></>,
  pin: <><path d="M12 17v5M8 7l1 5-3 3h12l-3-3 1-5zM8 3h8v4H8z" /></>,
  logout: <><path d="M10 4H5v16h5M14 8l4 4-4 4M18 12H9" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1" /></>,
  thumbUp: <><path d="M7 11v9H4v-9zM7 11l4-7a2 2 0 0 1 3 2l-1 4h5a2 2 0 0 1 2 2l-1.5 7a2 2 0 0 1-2 1H7" /></>,
  thumbDown: <><path d="M17 13V4h3v9zM17 13l-4 7a2 2 0 0 1-3-2l1-4H6a2 2 0 0 1-2-2l1.5-7a2 2 0 0 1 2-1H17" /></>,
  eye: <><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12z" /><circle cx="12" cy="12" r="3" /></>,
  external: <><path d="M14 4h6v6M20 4l-9 9M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5" /></>,
};
export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 18, ...rest }: { name: IconName; size?: number } & SVGProps<SVGSVGElement>) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...rest}>
      {PATHS[name]}
    </svg>
  );
}

// ---------- Brand logo (identik dengan app/icon.svg) ----------
export function Logo({ size = 34, className = "", title = "JKT48Verse" }: { size?: number; className?: string; title?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 512 512" role="img" aria-label={title} className={`logo ${className}`.trim()} style={{ flexShrink: 0 }}>
      <defs>
        <linearGradient id="jv-logo-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#ff4d6d" />
          <stop offset="1" stopColor="#b60f2c" />
        </linearGradient>
        <radialGradient id="jv-logo-hl" cx="0.2" cy="0.08" r="0.95">
          <stop offset="0" stopColor="#fff" stopOpacity="0.18" />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="512" height="512" rx="118" fill="url(#jv-logo-bg)" />
      <rect width="512" height="512" rx="118" fill="url(#jv-logo-hl)" />
      <rect x="1.5" y="1.5" width="509" height="509" rx="116.5" fill="none" stroke="#fff" strokeOpacity="0.12" strokeWidth="3" />
      <path d="M190 151v168a42 42 0 0 1-84 0M273 151l66 210 66-210" fill="none" stroke="#fff" strokeWidth="60" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ---------- Avatar ----------
export function initials(name: string) {
  return name.split(/\s+/).slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("");
}
export function seedFor(s: string) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 6;
  return h + 1;
}
export function Avatar({ name, size = 32, seed, className = "" }: { name: string; size?: number; seed?: number; className?: string }) {
  const g = `g${seed ?? seedFor(name)}`;
  return (
    <span className={`avatar ${g} ${className}`} style={{ width: size, height: size, fontSize: Math.max(10, size * 0.36) }} aria-label={name}>
      {initials(name)}
    </span>
  );
}

// ---------- Tag helpers ----------
export const TYPE_TAG: Record<string, { cls: string; label: string }> = {
  theater: { cls: "t-red", label: "Theater" },
  event: { cls: "t-warn", label: "Event" },
  concert: { cls: "t-violet", label: "Konser" },
  media: { cls: "t-info", label: "Media" },
  other: { cls: "t-gray", label: "Lainnya" },
  release: { cls: "t-info", label: "Release" },
  birthday: { cls: "t-violet", label: "Birthday" },
};
export const TICKET_TAG: Record<string, { cls: string; label: string }> = {
  available: { cls: "t-ok", label: "Tersedia" },
  sold_out: { cls: "t-red", label: "Terjual" },
  closed: { cls: "t-gray", label: "Ditutup" },
  unknown: { cls: "t-gray", label: "—" },
};
export const STATUS_TAG: Record<string, { cls: string; label: string }> = {
  regular: { cls: "t-ok", label: "Regular" },
  trainee: { cls: "t-info", label: "Trainee" },
  graduated: { cls: "t-gray", label: "Graduated" },
  former: { cls: "t-gray", label: "Former" },
};
export function Tag({ kind, value }: { kind: "type" | "ticket" | "status"; value: string }) {
  const map = kind === "type" ? TYPE_TAG : kind === "ticket" ? TICKET_TAG : STATUS_TAG;
  const t = map[value] ?? { cls: "t-gray", label: value };
  return <span className={`tag ${t.cls}`}>{t.label}</span>;
}
export function RoleTag({ role }: { role: string }) {
  if (role === "ADMIN") return <span className="tag t-red">Admin</span>;
  if (role === "MODERATOR") return <span className="tag t-info">Moderator</span>;
  return null;
}

// ---------- Page head ----------
export function PageHead({ title, sub, right }: { title: string; sub?: ReactNode; right?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
      <div>
        <h1 className="h1">{title}</h1>
        {sub && <p className="muted text-[12.5px] mt-0.5">{sub}</p>}
      </div>
      {right && <div className="flex flex-wrap gap-2 items-center">{right}</div>}
    </div>
  );
}

export function WidgetHead({ title, href, label = "Semua ›" }: { title: string; href?: string; label?: string }) {
  return (
    <div className="w-head">
      <h3>{title}</h3>
      {href && <Link href={href}>{label}</Link>}
    </div>
  );
}

export function Empty({ icon = "radio", title, hint, action }: { icon?: IconName; title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="empty">
      <Icon name={icon} />
      <b>{title}</b>
      {hint && <span className="text-[12.5px]">{hint}</span>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function LoginCta({ text, next }: { text: string; next: string }) {
  return (
    <div className="flex items-center gap-3 rounded-[11px] border border-border-2 bg-surface-2 px-3 py-2">
      <span className="muted text-[13px] flex-1">{text}</span>
      <Link href={`/auth/login?next=${encodeURIComponent(next)}`} className="btn pri sm">Login</Link>
    </div>
  );
}

export function Disclaimer() {
  return (
    <footer className="muted text-[11px] mt-6 text-center flex flex-col gap-1">
      <span>Proyek komunitas non-komersial — tidak berafiliasi dengan JKT48 Operation Team.</span>
      <span className="flex justify-center gap-3"><Link href="/terms">Ketentuan</Link>·<Link href="/privacy">Privasi</Link>·<Link href="/bot-info">Bot Info</Link>·<Link href="/contributors">Contributors</Link></span>
    </footer>
  );
}

export function GenChips({ current, base }: { current?: number; base: string }) {
  const gens = [3, 6, 7, 8, 9, 10, 11, 12, 13, 14];
  return (
    <>
      {gens.map((g) => (
        <Link key={g} href={`${base}gen=${g}`} className={`chip ${current === g ? "on" : ""}`}>Gen {g}</Link>
      ))}
    </>
  );
}
