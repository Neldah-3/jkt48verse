import Link from "next/link";
import { redirect } from "next/navigation";
import { Avatar, Icon, PageHead } from "@/components/ui";
import { ReportActions, SanctionButton } from "@/components/AdminBits";
import { getViewer } from "@/lib/auth";
import { adminStats, adminUsers, counts, moderationLogs, moderationReports, staffLoginLogs } from "@/lib/data";
import { getLiveNow } from "@/lib/live";
import { fmtDateTime } from "@/lib/time";
export const dynamic = "force-dynamic";

export default async function AdminPage({ searchParams }: { searchParams: Promise<{ s?: string }> }) {
  const v = await getViewer();
  if (v.role !== "ADMIN") redirect("/auth/admin-login");
  const { s = "pending" } = await searchParams;
  const [stats, c, live, reps, us, logs, mods] = await Promise.all([
    adminStats(), counts(), getLiveNow(),
    moderationReports(s), adminUsers(30), staffLoginLogs(10), moderationLogs(10),
  ]);
  const content = [["Encyclopedia", "/encyclopedia/jkt48"], ["Games Bank Soal", "/games"], ["News", "/news"], ["Schedule", "/schedule"], ["Member", "/member"], ["Motivation", "/motivation"], ["Emoji Blocklist", "/chat"], ["AI Config", "/ai-search"], ["Keamanan AI", "/chat"], ["Contributors", "/contributors"]];
  return (
    <>
      <PageHead title="Admin Panel" sub={`Masuk sebagai ${v.username} · ${stats.admins} Admin · ${stats.moderators} Moderator terdaftar di database`} />
      <div className="grid12 mb-3.5">
        <div className="c3 card w stat"><div className="lbl"><Icon name="flag" size={13} /> Report Pending</div><div className="num" style={{ color: "var(--warn)" }}>{stats.pendingReports}</div></div>
        <div className="c3 card w stat"><div className="lbl"><Icon name="users" size={13} /> User Terdaftar</div><div className="num" style={{ color: "var(--info)" }}>{c.users}</div></div>
        <div className="c3 card w stat"><div className="lbl"><Icon name="chat" size={13} /> Pesan 24 Jam</div><div className="num" style={{ color: "var(--ok)" }}>{c.chat24h}</div></div>
        <div className="c3 card w stat"><div className="lbl"><span className="live-dot" /> Live Berlangsung</div><div className="num">{live.length}</div></div>
      </div>
      <div className="grid12">
        <div className="c8 flex flex-col gap-3.5">
          <div className="card w">
            <div className="w-head"><h3>Antrian Report</h3><div className="flex gap-1.5">{["pending", "approved", "rejected", "all"].map((k) => (<Link key={k} href={`/admin?s=${k}`} className={`chip ${s === k ? "on" : ""}`}>{k}</Link>))}</div></div>
            <div className="overflow-x-auto"><table className="tb min-w-[560px]"><thead><tr><th>User</th><th>Alasan</th><th>Tipe</th><th>Status</th><th>Waktu</th><th></th></tr></thead><tbody>
              {reps.length === 0 && <tr><td colSpan={6} className="muted text-center py-6">Tidak ada report.</td></tr>}
              {reps.map((r) => (<tr key={r.id}><td className="font-semibold">{r.targetUsername ?? "-"}</td><td><span className="tag t-warn">{r.reason}</span><div className="muted text-[11px] max-w-[200px] truncate">{r.description}</div></td><td>chat</td><td><span className={`tag ${r.status === "pending" ? "t-warn" : r.status === "approved" ? "t-ok" : "t-gray"}`}>{r.status}</span></td><td className="muted whitespace-nowrap">{fmtDateTime(r.createdAt)}</td><td>{r.status === "pending" && <ReportActions reportId={r.id} />}</td></tr>))}
            </tbody></table></div>
          </div>
          <div className="card w">
            <div className="w-head"><h3>Manajemen Akun</h3><span className="muted text-[11px]">Role tersimpan di database (users.role)</span></div>
            <div className="overflow-x-auto"><table className="tb min-w-[560px]"><thead><tr><th>User</th><th>Role</th><th>Poin</th><th>Status</th><th>Bergabung</th><th></th></tr></thead><tbody>
              {us.map((u) => { const blocked = u.blockedUntil && u.blockedUntil.getTime() > Date.now(); const muted = u.mutedUntil && u.mutedUntil.getTime() > Date.now(); return (<tr key={u.id as number}><td><span className="inline-flex items-center gap-2"><Avatar name={String(u.username)} size={22} seed={Number(u.avatarSeed)} />{String(u.username)}</span></td><td><span className="tag t-gray">{String(u.role)}</span></td><td className="tabular">{Number(u.points)}</td><td>{blocked ? <span className="tag t-red">Blokir</span> : muted ? <span className="tag t-warn">Mute</span> : <span className="tag t-ok">Aktif</span>}</td><td className="muted whitespace-nowrap">{fmtDateTime(u.createdAt)}</td><td><SanctionButton userId={u.id as number} username={String(u.username)} role={String(u.role)} /></td></tr>); })}
            </tbody></table></div>
          </div>
        </div>
        <div className="c4 flex flex-col gap-3.5">
          <div className="card w"><div className="w-head"><h3>Manajemen Konten</h3></div><div className="grid grid-cols-2 gap-2">{content.map(([l, h]) => (<Link key={l} href={h} className="btn ghost sm justify-start">{l}</Link>))}</div></div>
          <div className="card w"><div className="w-head"><h3>Log Moderasi</h3></div>{mods.length === 0 && <p className="muted text-[12px]">Belum ada.</p>}{mods.map((m) => (<div key={m.id} className="row flex-col gap-0.5"><span className="text-[12px]"><span className="tag t-gray">{m.kind}</span> user #{m.userId}</span><span className="muted text-[11px]">{m.detail} · {fmtDateTime(m.createdAt)}</span></div>))}</div>
          <div className="card w"><div className="w-head"><h3>Login Staff (terbaru)</h3></div>{logs.map((l) => (<div key={l.id} className="row items-center text-[12px]"><span className="flex-1">{l.username ?? l.userId}</span>{l.success ? <span className="tag t-ok">ok</span> : <span className="tag t-red">gagal</span>}<span className="muted text-[11px]">{fmtDateTime(l.createdAt)}</span></div>))}</div>
        </div>
      </div>
      <p className="muted text-[11px] mt-4">Moderator: maks ban 30 hari, permanen butuh approval Admin · akun staff dikelola via database (ROLE ADMIN/MODERATOR).</p>
    </>
  );
}
