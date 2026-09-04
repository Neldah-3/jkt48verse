import Link from "next/link";
import { redirect } from "next/navigation";
import { Avatar, PageHead } from "@/components/ui";
import { ReportActions, SanctionButton } from "@/components/AdminBits";
import { getViewer } from "@/lib/auth";
import { moderationReports } from "@/lib/data";
import { fmtDateTime } from "@/lib/time";
export const dynamic = "force-dynamic";
export default async function ModeratorPage({ searchParams }: { searchParams: Promise<{ s?: string }> }) {
  const v = await getViewer();
  if (v.role !== "MODERATOR" && v.role !== "ADMIN") redirect("/auth/admin-login");
  const { s = "pending" } = await searchParams;
  const reps = await moderationReports(s);
  const visible = reps.filter((r) => !r.targetRole || r.targetRole === "MEMBER" || v.role === "ADMIN");
  return (
    <>
      <PageHead title="Moderator Panel" sub={`Masuk sebagai ${v.username} (${v.role})`} />
      <div className="rounded-[12px] px-4 py-3 mb-3.5 text-[12.5px]" style={{ background: "var(--warn-soft)", color: "var(--warn)" }}>Ban permanen memerlukan approval Admin · wajib sertakan alasan & bukti (link pesan/gambar) · hanya akun MEMBER yang bisa ditindak.</div>
      <div className="card w">
        <div className="w-head"><h3>Antrian Report (chat & akun member)</h3><div className="flex gap-1.5">{["pending", "approved", "rejected", "all"].map((k) => (<Link key={k} href={`/moderator?s=${k}`} className={`chip ${s === k ? "on" : ""}`}>{k}</Link>))}</div></div>
        <div className="overflow-x-auto"><table className="tb min-w-[600px]"><thead><tr><th>User</th><th>Alasan</th><th>Status</th><th>Waktu</th><th>Aksi</th></tr></thead><tbody>
          {visible.length === 0 && <tr><td colSpan={5} className="muted text-center py-6">Tidak ada report.</td></tr>}
          {visible.map((r) => (<tr key={r.id}><td><span className="inline-flex items-center gap-2 font-semibold">{r.targetAvatarSeed != null && <Avatar name={r.targetUsername ?? "?"} size={22} seed={r.targetAvatarSeed} />}{r.targetUsername ?? "-"}</span></td><td><span className="tag t-warn">{r.reason}</span><div className="muted text-[11px] max-w-[220px] truncate">{r.description}</div></td><td><span className={`tag ${r.status === "pending" ? "t-warn" : r.status === "approved" ? "t-ok" : "t-gray"}`}>{r.status}</span></td><td className="muted whitespace-nowrap">{fmtDateTime(r.createdAt)}</td><td className="flex gap-1.5 items-center">{r.status === "pending" && <ReportActions reportId={r.id} />}{r.targetUserId && r.targetRole && <SanctionButton userId={r.targetUserId} username={r.targetUsername ?? String(r.targetUserId)} role={r.targetRole} moderator={v.role === "MODERATOR"} />}</td></tr>))}
        </tbody></table></div>
      </div>
    </>
  );
}
