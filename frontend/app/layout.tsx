import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import AppShell from "@/components/AppShell";
import { getViewer } from "@/lib/auth";
import { getLiveNow } from "@/lib/live";
import { listNotifications, ready, unreadCount } from "@/lib/data";

export const metadata: Metadata = {
  title: { default: "JKT48Verse — Fan-made Platform", template: "%s · JKT48Verse" },
  description: "Platform komunitas penggemar JKT48: live member, jadwal, news, birthday, games, chat, dan AI search. Proyek non-komersial, tidak berafiliasi dengan JKT48 Operation Team.",
};
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [{ media: "(prefers-color-scheme: light)", color: "#ffffff" }, { media: "(prefers-color-scheme: dark)", color: "#151a22" }],
};
export const dynamic = "force-dynamic";

export default async function RootLayout({ children }: { children: ReactNode }) {
  let viewer = { role: "GUEST", username: "Tamu", avatarSeed: 1, userId: null as number | null, theme: "system" };
  let liveCount = 0;
  let unread = 0;
  let notifs: { id: number; type: string; title: string; href: string | null; isRead: boolean }[] = [];
  try {
    await ready();
    const v = await getViewer();
    viewer = { role: v.role, username: v.username, avatarSeed: v.avatarSeed, userId: v.userId, theme: v.user?.theme ?? "system" };
    const [live, n, list] = await Promise.all([getLiveNow(), unreadCount(v.userId), v.userId ? listNotifications(v.userId, 3) : Promise.resolve([])]);
    liveCount = live.length;
    unread = n;
    notifs = list.map((x) => ({ id: x.id, type: x.type, title: x.title, href: x.href, isRead: x.isRead }));
  } catch (e) {
    console.error("layout bootstrap failed", e);
  }
  return (
    <html lang="id" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: `(function(){try{var t=localStorage.getItem('jv_theme');var d=t==='dark'||(t!=='light'&&matchMedia('(prefers-color-scheme: dark)').matches);if(d)document.documentElement.classList.add('dark');}catch(e){}})();` }} />
      </head>
      <body>
        <AppShell viewer={viewer} liveCount={liveCount} unread={unread} notifs={notifs} theme={viewer.theme}>
          {children}
        </AppShell>
      </body>
    </html>
  );
}
