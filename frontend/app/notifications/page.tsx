import Link from "next/link";
import { redirect } from "next/navigation";
import { Icon, PageHead } from "@/components/ui";
import { getViewer } from "@/lib/auth";
import { listNotifications } from "@/lib/data";
import { markAllReadAction } from "@/app/actions";
import { fmtDateTime } from "@/lib/time";
export const dynamic = "force-dynamic";
export default async function NotificationsPage({ searchParams }: { searchParams: Promise<{ t?: string; r?: string }> }) {
  const v = await getViewer();
  if (!v.userId) redirect("/auth/login?next=/notifications");
  const { t, r } = await searchParams;
  let rows = await listNotifications(v.userId, 100);
  if (t) rows = rows.filter((n) => n.type === t);
  if (r === "unread") rows = rows.filter((n) => !n.isRead);
  const types = ["LIVE_ALERT", "SCHEDULE_REMINDER", "BIRTHDAY_ALERT", "NEWS_ALERT", "CHAT_MENTION", "GAME_DAILY", "GAME_BADGE", "SYSTEM"];
  return (
    <>
      <PageHead title="Notifikasi" right={<form action={async () => { "use server"; await markAllReadAction(); }}><button className="btn ghost sm"><Icon name="check" size={14} /> Tandai semua dibaca</button></form>} />
      <div className="flex flex-wrap gap-1.5 mb-3"><Link href="/notifications" className={`chip ${!t && !r ? "on" : ""}`}>Semua</Link><Link href="/notifications?r=unread" className={`chip ${r === "unread" ? "on" : ""}`}>Belum dibaca</Link>{types.map((k) => (<Link key={k} href={`/notifications?t=${k}`} className={`chip ${t === k ? "on" : ""}`}>{k}</Link>))}</div>
      <div className="card w">
        {rows.length === 0 && <p className="muted text-[12.5px] text-center py-6">Tidak ada notifikasi.</p>}
        {rows.map((n) => (<Link key={n.id} href={n.href ?? "#"} className="row items-start"><span className="w-8 h-8 rounded-[9px] inline-flex items-center justify-center flex-shrink-0" style={{ background: "var(--surface-2)" }}><Icon name={n.type === "LIVE_ALERT" ? "radio" : n.type === "BIRTHDAY_ALERT" ? "gift" : n.type === "CHAT_MENTION" ? "chat" : n.type.startsWith("GAME") ? "trophy" : n.type === "SCHEDULE_REMINDER" ? "calendar" : "bell"} size={15} /></span><div className="flex-1 min-w-0"><div className={`text-[13px] ${n.isRead ? "" : "font-bold"}`}>{n.title}</div>{n.body && <div className="muted text-[12px]">{n.body}</div>}<div className="muted text-[11px] mt-0.5"><span className="tag t-gray mr-1">{n.type}</span>{fmtDateTime(n.createdAt)}</div></div>{!n.isRead && <span className="w-2 h-2 rounded-full bg-primary mt-2" />}</Link>))}
      </div>
    </>
  );
}
