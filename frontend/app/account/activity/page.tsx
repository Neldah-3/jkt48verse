import Link from "next/link";
import { redirect } from "next/navigation";
import { and, desc, eq, gte, inArray } from "drizzle-orm";
import { PageHead, Tag } from "@/components/ui";
import { getViewer } from "@/lib/auth";
import { db } from "@/db";
import { activityLogs, bookmarks, chatMessages, gameScores, loginLogs, news, schedules, encyclopedia, sessions, sorterResults, members } from "@/db/schema";
import { fmtDateTime } from "@/lib/time";
export const dynamic = "force-dynamic";
export default async function ActivityPage({ searchParams }: { searchParams: Promise<{ tab?: string }> }) {
  const { tab = "sessions" } = await searchParams;
  const v = await getViewer();
  if (!v.userId) redirect("/auth/login?next=/account/activity");
  const uid = v.userId;
  const tabs = [["sessions", "Login & Sesi"], ["interaksi", "Interaksi"], ["bookmarks", "Bookmarks"], ["games", "Games"], ["chat", "Chat"], ["sorter", "Oshi Sorter"]];
  let body: React.ReactNode = null;
  if (tab === "sessions") {
    const [ss, ll] = await Promise.all([db.select().from(sessions).where(eq(sessions.userId, uid)).orderBy(desc(sessions.createdAt)), db.select().from(loginLogs).where(eq(loginLogs.userId, uid)).orderBy(desc(loginLogs.createdAt)).limit(20)]);
    body = (<><h3 className="text-[13px] font-bold">Sesi aktif ({ss.length})</h3><table className="tb"><thead><tr><th>Perangkat</th><th>Dibuat</th><th>Berakhir</th></tr></thead><tbody>{ss.map((s) => (<tr key={s.token}><td className="max-w-[260px] truncate">{s.userAgent ?? "-"}</td><td>{fmtDateTime(s.createdAt)}</td><td>{fmtDateTime(s.expiresAt)}</td></tr>))}</tbody></table><p className="text-[12px]"><Link href="/account/settings" className="link">Kelola sesi (keluar) ›</Link></p><h3 className="text-[13px] font-bold mt-3">Riwayat login</h3><table className="tb"><thead><tr><th>Waktu</th><th>Status</th><th>IP</th></tr></thead><tbody>{ll.map((l) => (<tr key={l.id}><td>{fmtDateTime(l.createdAt)}</td><td>{l.success ? <span className="tag t-ok">Sukses</span> : <span className="tag t-red">Gagal</span>}</td><td className="muted">{l.ip}</td></tr>))}</tbody></table></>);
  } else if (tab === "interaksi") {
    const rows = await db.select().from(activityLogs).where(eq(activityLogs.userId, uid)).orderBy(desc(activityLogs.createdAt)).limit(50);
    body = rows.length ? <table className="tb"><tbody>{rows.map((r) => (<tr key={r.id}><td><span className="tag t-gray">{r.action}</span></td><td>{r.detail}</td><td className="muted whitespace-nowrap">{fmtDateTime(r.createdAt)}</td></tr>))}</tbody></table> : <p className="muted text-[12.5px]">Belum ada interaksi.</p>;
  } else if (tab === "bookmarks") {
    const bs = await db.select().from(bookmarks).where(eq(bookmarks.userId, uid)).orderBy(desc(bookmarks.createdAt));
    const ids = (t: string) => bs.filter((b) => b.entityType === t).map((b) => b.entityId);
    const [ns, ss, es] = await Promise.all([ids("news").length ? db.select().from(news).where(inArray(news.id, ids("news"))) : [], ids("schedule").length ? db.select().from(schedules).where(inArray(schedules.id, ids("schedule"))) : [], ids("encyclopedia").length ? db.select().from(encyclopedia).where(inArray(encyclopedia.id, ids("encyclopedia"))) : []]);
    body = (<div className="flex flex-col gap-3">{[["News", ns.map((n) => ({ id: n.id, t: n.title, h: `/news/${n.slug}` }))], ["Schedule", ss.map((s) => ({ id: s.id, t: s.title, h: `/schedule/${s.id}` }))], ["Encyclopedia", es.map((e) => ({ id: e.id, t: e.title, h: `/encyclopedia/${e.slug}` }))]].map(([label, items]) => (<div key={label as string}><h3 className="text-[12px] uppercase font-bold muted mb-1">{label as string}</h3>{(items as { id: number; t: string; h: string }[]).length === 0 ? <p className="muted text-[12px]">—</p> : (items as { id: number; t: string; h: string }[]).map((i) => (<Link key={i.id} href={i.h} className="row text-[13px] font-semibold">📌 {i.t}</Link>))}</div>))}</div>);
  } else if (tab === "games") {
    const rows = await db.select().from(gameScores).where(eq(gameScores.userId, uid)).orderBy(desc(gameScores.createdAt)).limit(50);
    body = rows.length ? <table className="tb"><thead><tr><th>Game</th><th>Skor</th><th>Detail</th><th>Waktu</th></tr></thead><tbody>{rows.map((r) => (<tr key={r.id}><td><Tag kind="type" value={r.game} /></td><td className="tabular font-bold">{r.score}</td><td className="muted">{r.detail}</td><td className="muted whitespace-nowrap">{fmtDateTime(r.createdAt)}</td></tr>))}</tbody></table> : <p className="muted text-[12.5px]">Belum ada capaian. <Link href="/games" className="link">Main sekarang ›</Link></p>;
  } else if (tab === "chat") {
    const rows = await db.select().from(chatMessages).where(and(eq(chatMessages.userId, uid), gte(chatMessages.createdAt, new Date(Date.now() - 3 * 86400_000)))).orderBy(desc(chatMessages.createdAt)).limit(50);
    body = rows.length ? <div>{rows.map((r) => (<div key={r.id} className="row"><div className="flex-1 text-[13px]">{r.body}{r.isHidden && <span className="tag t-red ml-2">Dihapus</span>}</div><span className="muted text-[11px] whitespace-nowrap">{fmtDateTime(r.createdAt)}</span></div>))}</div> : <p className="muted text-[12.5px]">Tidak ada pesan dalam 3 hari terakhir.</p>;
  } else {
    const rows = await db.select().from(sorterResults).where(eq(sorterResults.userId, uid)).orderBy(desc(sorterResults.createdAt)).limit(10);
    const allIds = [...new Set(rows.flatMap((r) => r.ranking.slice(0, 3)))];
    const ms = allIds.length ? await db.select().from(members).where(inArray(members.id, allIds)) : [];
    body = rows.length ? <div>{rows.map((r) => (<div key={r.id} className="row items-center"><div className="flex-1 text-[13px]">Top 3: <b>{r.ranking.slice(0, 3).map((id) => ms.find((m) => m.id === id)?.nickname ?? "?").join(", ")}</b> <span className="muted">({r.ranking.length} member)</span></div><span className="muted text-[11px]">{fmtDateTime(r.createdAt)}</span></div>))}</div> : <p className="muted text-[12.5px]">Belum ada hasil Oshi Sorter. <Link href="/games/oshi-sorter" className="link">Coba sekarang ›</Link></p>;
  }
  return (<><PageHead title="Activity" right={<Link href="/account" className="btn ghost sm">‹ Akun</Link>} /><div className="flex flex-wrap gap-2 mb-3">{tabs.map(([k, l]) => (<Link key={k} href={`/account/activity?tab=${k}`} className={`chip ${tab === k ? "on" : ""}`}>{l}</Link>))}</div><div className="card w overflow-x-auto">{body}</div></>);
}
