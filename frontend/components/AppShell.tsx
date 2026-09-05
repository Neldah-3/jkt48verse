"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Avatar, Icon, type IconName } from "@/components/ui";
import Logo from "@/components/Logo";
import { logoutAction } from "@/app/actions";

export type ShellViewer = { role: string; username: string; avatarSeed: number; userId: number | null };
export type ShellNotif = { id: number; type: string; title: string; href: string | null; isRead: boolean };

const MAIN: { href: string; label: string; icon: IconName }[] = [
  { href: "/", label: "Dashboard", icon: "home" },
  { href: "/live", label: "Live Member", icon: "radio" },
  { href: "/member", label: "Member", icon: "users" },
  { href: "/schedule", label: "Jadwal", icon: "calendar" },
  { href: "/news", label: "News", icon: "news" },
  { href: "/chat", label: "Public Chat", icon: "chat" },
];
const INTERACTIVE: { href: string; label: string; icon: IconName }[] = [
  { href: "/games", label: "Games", icon: "gamepad" },
  { href: "/birthday", label: "Birthday", icon: "gift" },
  { href: "/encyclopedia/jkt48", label: "Encyclopedia", icon: "book" },
  { href: "/motivation", label: "Motivation", icon: "heart" },
  { href: "/ai-search", label: "AI Search", icon: "spark" },
];

type SearchResult = {
  members: { slug: string; name: string; nickname: string; generation: number | null }[];
  news: { slug: string; title: string }[];
  schedules: { id: number; title: string }[];
  encyclopedia: { slug: string; title: string }[];
  glossary: { term: string; meaning: string }[];
};

export default function AppShell({ children, viewer, liveCount, unread, notifs, theme }: { children: ReactNode; viewer: ShellViewer; liveCount: number; unread: number; notifs: ShellNotif[]; theme: string }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [dark, setDark] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [q, setQ] = useState("");
  const [res, setRes] = useState<SearchResult | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);

  // theme
  useEffect(() => {
    const stored = theme !== "system" ? theme : localStorage.getItem("jv_theme");
    const prefers = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const d = stored === "dark" || (stored !== "light" && prefers);
    setDark(d);
    document.documentElement.classList.toggle("dark", d);
  }, [theme]);
  const toggleTheme = () => {
    const d = !dark;
    setDark(d);
    document.documentElement.classList.toggle("dark", d);
    localStorage.setItem("jv_theme", d ? "dark" : "light");
  };

  useEffect(() => {
    setOpen(false);
    setNotifOpen(false);
    setSearchOpen(false);
  }, [pathname]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen(true);
        setTimeout(() => searchRef.current?.focus(), 30);
      }
      if (e.key === "Escape") {
        setOpen(false);
        setNotifOpen(false);
        setSearchOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (q.trim().length < 2) {
      setRes(null);
      return;
    }
    const t = setTimeout(async () => {
      const r = await fetch(`/api/search?q=${encodeURIComponent(q.slice(0, 80))}`);
      if (r.ok) setRes(await r.json());
    }, 300);
    return () => clearTimeout(t);
  }, [q]);

  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href.split("/").slice(0, 2).join("/")));
  const staffPanel = viewer.role === "ADMIN" ? { href: "/admin", label: "Admin Panel" } : viewer.role === "MODERATOR" ? { href: "/moderator", label: "Moderator Panel" } : null;

  const navItem = (it: { href: string; label: string; icon: IconName }, badge?: number) => (
    <Link key={it.href} href={it.href} className={`sb-item ${isActive(it.href) ? "active" : ""}`} aria-label={it.label}>
      <Icon name={it.icon} />
      <span className="sb-label flex-1">{it.label}</span>
      {!!badge && <span className="counter sb-badge">{badge > 99 ? "99+" : badge}</span>}
    </Link>
  );

  const searchPanel = (
    <div className="card absolute left-0 right-0 top-[44px] z-50 max-h-[70vh] overflow-y-auto p-2 text-[13px]" style={{ boxShadow: "var(--shadow-lg)" }}>
      {!res && <p className="muted p-3">Ketik minimal 2 karakter…</p>}
      {res && Object.values(res).every((a) => a.length === 0) && <p className="muted p-3">Tidak ada hasil untuk “{q}”.</p>}
      {res?.members.length ? (<div><p className="sb-section">Member</p>{res.members.map((m) => (<Link key={m.slug} href={`/member/${m.slug}`} className="sb-item"><Avatar name={m.name} size={24} /><span>{m.name} <span className="muted">· @{m.nickname} · Gen {m.generation ?? "-"}</span></span></Link>))}</div>) : null}
      {res?.news.length ? (<div><p className="sb-section">News</p>{res.news.map((n) => (<Link key={n.slug} href={`/news/${n.slug}`} className="sb-item"><Icon name="news" size={15} /><span className="truncate">{n.title}</span></Link>))}</div>) : null}
      {res?.schedules.length ? (<div><p className="sb-section">Jadwal</p>{res.schedules.map((s) => (<Link key={s.id} href={`/schedule/${s.id}`} className="sb-item"><Icon name="calendar" size={15} /><span className="truncate">{s.title}</span></Link>))}</div>) : null}
      {res?.encyclopedia.length ? (<div><p className="sb-section">Encyclopedia</p>{res.encyclopedia.map((e) => (<Link key={e.slug} href={`/encyclopedia/${e.slug}`} className="sb-item"><Icon name="book" size={15} /><span>{e.title}</span></Link>))}</div>) : null}
      {res?.glossary.length ? (<div><p className="sb-section">Glosarium</p>{res.glossary.map((g) => (<Link key={g.term} href="/encyclopedia/wota-culture" className="sb-item"><Icon name="zap" size={15} /><span><b>{g.term}</b> <span className="muted">— {g.meaning}</span></span></Link>))}</div>) : null}
    </div>
  );

  return (
    <div className="app">
      {open && <div className="backdrop" onClick={() => setOpen(false)} />}
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="flex items-center gap-3 px-4 h-[58px] border-b border-border">
          <Logo size={34} />
          <div className="sb-brand-text leading-tight">
            <div className="font-bold text-[14.5px]">JKT48Verse</div>
            <div className="muted text-[11px]">Fan-made Platform</div>
          </div>
          <button className="ml-auto btn icon ghost hamburger" onClick={() => setOpen(false)} aria-label="Tutup menu"><Icon name="x" /></button>
        </div>
        <nav className="flex-1 px-2 py-2 flex flex-col gap-0.5">
          <p className="sb-section">Menu Utama</p>
          {MAIN.map((it) => navItem(it, it.href === "/live" ? liveCount : undefined))}
          <p className="sb-section">Interaktif</p>
          {INTERACTIVE.map((it) => navItem(it))}
          {staffPanel && (<><p className="sb-section">Panel</p>{navItem({ href: staffPanel.href, label: staffPanel.label, icon: "shield" })}</>)}
          {viewer.role === "MEMBER" && (<><p className="sb-section">Akun</p>{navItem({ href: "/account", label: "Akun Saya", icon: "user" })}</>)}
        </nav>
        <div className="sb-footer px-4 py-3 border-t border-border muted text-[10.5px]">v2.0 · Non-official · Fan project</div>
      </aside>

      <header className="topbar">
        <button className="btn icon ghost hamburger" onClick={() => setOpen(true)} aria-label="Buka menu"><Icon name="menu" /></button>
        <div className="relative search-top" style={{ width: "min(380px, 44vw)" }}>
          <div className="flex items-center gap-2 input py-2" onClick={() => { setSearchOpen(true); searchRef.current?.focus(); }}>
            <Icon name="search" size={15} className="muted" />
            <input ref={searchRef} value={q} onChange={(e) => { setQ(e.target.value); setSearchOpen(true); }} onFocus={() => setSearchOpen(true)} placeholder="Cari member, news, jadwal…" className="bg-transparent outline-none flex-1 text-[13px] min-w-0" maxLength={80} aria-label="Global search" />
            <span className="kbd">⌘K</span>
          </div>
          {searchOpen && q.length >= 2 && searchPanel}
        </div>
        <div className="flex-1" />
        <Link href="/ai-search" className="btn icon ghost md:hidden" aria-label="AI Search"><Icon name="search" /></Link>
        <div className="relative">
          <button className="btn icon ghost relative" onClick={() => setNotifOpen((v) => !v)} aria-label="Notifikasi">
            <Icon name="bell" />
            {unread > 0 && <span className="counter absolute -top-1 -right-1">{unread > 99 ? "99+" : unread}</span>}
          </button>
          {notifOpen && (
            <div className="card popover">
              <div className="w-head px-4 pt-3 pb-2"><h3>Notifikasi</h3>{unread > 0 && <span className="tag t-red">{unread} baru</span>}</div>
              <div className="px-2 pb-2">
                {viewer.userId == null && <p className="muted text-[12.5px] px-2 py-3">Login untuk menerima notifikasi Live Alert, Birthday, dan mention.</p>}
                {notifs.map((n) => (
                  <Link key={n.id} href={n.href ?? "/notifications"} className="sb-item text-[12.5px]">
                    <Icon name={n.type === "LIVE_ALERT" ? "radio" : n.type === "BIRTHDAY_ALERT" ? "gift" : n.type === "CHAT_MENTION" ? "chat" : n.type.startsWith("GAME") ? "trophy" : "bell"} size={15} />
                    <span className={`flex-1 ${n.isRead ? "muted" : "font-semibold"}`}>{n.title}</span>
                  </Link>
                ))}
                {viewer.userId != null && notifs.length === 0 && <p className="muted text-[12.5px] px-2 py-3">Belum ada notifikasi.</p>}
              </div>
              <div className="px-4 py-2 border-t border-border"><Link href="/notifications" className="link">Lihat semua</Link></div>
            </div>
          )}
        </div>
        <button className="btn icon ghost" onClick={toggleTheme} aria-label="Toggle tema"><Icon name={dark ? "sun" : "moon"} /></button>
        {viewer.role === "GUEST" ? (
          <Link href="/auth/login" className="btn pri sm">Login</Link>
        ) : (
          <div className="flex items-center gap-2">
            <Link href={viewer.role === "MEMBER" ? "/account" : viewer.role === "ADMIN" ? "/admin" : "/moderator"} className="flex items-center gap-2">
              <Avatar name={viewer.username} size={32} seed={viewer.avatarSeed} />
              <span className="user-chip-text leading-tight">
                <span className="block text-[12.5px] font-semibold">{viewer.username}</span>
                <span className="block text-[10px] muted uppercase tracking-wide">{viewer.role}</span>
              </span>
            </Link>
            <form action={() => logoutAction()}><button className="btn icon ghost" aria-label="Keluar" title="Keluar"><Icon name="logout" size={16} /></button></form>
          </div>
        )}
      </header>

      <main className="min-w-0">
        <div className="content">{children}</div>
      </main>

      <nav className="bottomnav">
        {[
          { href: "/", label: "Home", icon: "home" as IconName },
          { href: "/live", label: "Live", icon: "radio" as IconName },
          { href: "/schedule", label: "Jadwal", icon: "calendar" as IconName },
          { href: "/chat", label: "Chat", icon: "chat" as IconName },
        ].map((it) => (
          <Link key={it.href} href={it.href} className="flex flex-col items-center gap-0.5 py-2 text-[9.5px] font-semibold" style={{ color: isActive(it.href) ? "var(--primary)" : "var(--muted)", minHeight: 48 }}>
            <Icon name={it.icon} size={17} />
            {it.label}
          </Link>
        ))}
        <button onClick={() => setOpen(true)} className="flex flex-col items-center gap-0.5 py-2 text-[9.5px] font-semibold muted" style={{ minHeight: 48 }}>
          <Icon name="menu" size={17} />
          Menu
        </button>
      </nav>
    </div>
  );
}
