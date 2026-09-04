import Link from "next/link";
import { redirect } from "next/navigation";
import { desc, eq, inArray } from "drizzle-orm";
import { Avatar, PageHead } from "@/components/ui";
import { ReportActions, SanctionButton } from "@/components/AdminBits";
import { getViewer } from "@/lib/auth";
import { db } from "@/db";
import { reports, users } from "@/db/schema";
import { fmtDateTime } from "@/lib/time";
export const dynamic = "force-dynamic";
export default async function ModeratorPage({ searchParams }: { searchParams: Promise<{ s?: string }> }) {
  const v = await getViewer();
  if (v.role !== "MODERATOR" && v.role !== "ADMIN") redirect("/auth/admin-login");
  const { s = "pending" } = await searchParams;
  const reps = await db.select().from(reports).where(s === "all" ? undefined : eq(reports.status, s)).orderBy(desc(reports.createdAt)).limit(30);
  const ids = [...new Set(reps.map((r) => r.targetUserId).filter((x): x is number => !!x))];
  const targets = ids.length ? await db.select().from(users).where(inArray(users.id, ids)) : [];
  const visible = reps.filter((r) => { const t = targets.find((u) => u.id === r.targetUserId); return !t || t.role === "MEMBER" || v.role === "ADMIN"; });
  return (
    <>
      <PageHead title="Moderator Panel" sub={`Masuk sebagai ${v.username} (${v.staffId ?? v.role})`} />
      <div className="rounded-[12px] px-4 py-3 mb-3.5 text-[12.5px]" style={{ background: "var(--warn-soft)", color: "var(--warn)" }}>Ban permanen memerlukan approval Admin · wajib sertakan alasan & bukti (link pesan/gambar) · hanya akun MEMBER yang bisa ditindak.</div>
      <div className="card w">
        <div className="w-head"><h3>Antrian Report (chat & akun member)</h3><div className="flex gap-1.5">{["pending", "approved", "rejected", "all"].map((k) => (<Link key={k} href={`/moderator?s=${k}`} className={`chip ${s === k ? "on" : ""}`}>{k}</Link>))}</div></div>
        <div className="overflow-x-auto"><table className="tb min-w-[600px]"><thead><tr><th>User</th><th>Alasan</th><th>Status</th><th>Waktu</th><th>Aksi</th></tr></thead><tbody>
          {visible.length === 0 && <tr><td colSpan={5} className="muted text-center py-6">Tidak ada report.</td></tr>}
          {visible.map((r) => { const t = targets.find((u) => u.id === r.targetUserId); return (<tr key={r.id}><td><span className="inline-flex items-center gap-2 font-semibold">{t && <Avatar name={t.username} size={22} seed={t.avatarSeed} />}{r.targetUsername ?? "-"}</span></td><td><span className="tag t-warn">{r.reason}</span><div className="muted text-[11px] max-w-[220px] truncate">{r.description}</div></td><td><span className={`tag ${r.status === "pending" ? "t-warn" : r.status === "approved" ? "t-ok" : "t-gray"}`}>{r.status}</span></td><td className="muted whitespace-nowrap">{fmtDateTime(r.createdAt)}</td><td className="flex gap-1.5 items-center">{r.status === "pending" && <ReportActions reportId={r.id} />}{t && <SanctionButton userId={t.id} username={t.username} role={t.role} moderator={v.role === "MODERATOR"} />}</td></tr>); })}
        </tbody></table></div>
      </div>
    </>
  );
}
