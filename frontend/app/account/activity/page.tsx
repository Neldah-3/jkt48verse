import Link from "next/link";
import { redirect } from "next/navigation";
import { PageHead, Tag } from "@/components/ui";
import { getViewer } from "@/lib/auth";
import { accountOverview } from "@/lib/data";
import { fmtDateTime } from "@/lib/time";
export const dynamic = "force-dynamic";
export default async function ActivityPage({ searchParams }: { searchParams: Promise<{ tab?: string }> }) {
  const { tab = "sessions" } = await searchParams;
  const v = await getViewer();
  if (!v.userId) redirect("/auth/login?next=/account/activity");
  const ov = await accountOverview();
  const tabs = [["sessions", "Login & Sesi"], ["interaksi", "Interaksi"], ["bookmarks", "Bookmarks"], ["games", "Games"], ["chat", "Chat"], ["sorter", "Oshi Sorter"]];
  let body: React.ReactNode = null;
  if (tab === "sessions") {
    body = (<><h3 className="text-[13px] font-bold">Sesi / perangkat tersimpan ({ov.sessions.length})</h3><table className="tb"><thead><tr><th>Perangkat</th><th>Dibuat</th><th>Terakhir dipakai</th></tr></thead><tbody>{ov.sessions.map((s) => (<tr key={s.id}><td className="max-w-[260px] truncate">{[s.device, s.browser].filter(Boolean).join(" · ") || "-"}</td><td>{s.createdAt ? fmtDateTime(s.createdAt) : "-"}</td><td>{s.lastUsedAt ? fmtDateTime(s.lastUsedAt) : "-"}</td></tr>))}</tbody></table><p className="text-[12px]"><Link href="/account/settings" className="link">Kelola sesi (keluar) ›</Link></p><h3 className="text-[13px] font-bold mt-3">Riwayat login</h3><table className="tb"><thead><tr><th>Waktu</th><th>Status</th><th>IP</th></tr></thead><tbody>{ov.loginLogs.map((l) => (<tr key={l.id}><td>{fmtDateTime(l.createdAt)}</td><td>{l.success ? <span className="tag t-ok">Sukses</span> : <span className="tag t-red">Gagal</span>}</td><td className="muted">{l.ip}</td></tr>))}</tbody></table></>);
  } else if (tab === "interaksi") {
    body = ov.activity.length ? <table className="tb"><tbody>{ov.activity.map((r) => (<tr key={r.id}><td><span className="tag t-gray">{r.action}</span></td><td>{r.detail}</td><td className="muted whitespace-nowrap">{fmtDateTime(r.createdAt)}</td></tr>))}</tbody></table> : <p className="muted text-[12.5px]">Belum ada interaksi.</p>;
  } else if (tab === "bookmarks") {
    const groups = (["news", "schedule", "encyclopedia"] as const).map((t) => [
      t[0].toUpperCase() + t.slice(1),
      ov.bookmarks.filter((b) => b.entityType === t),
    ] as [string, typeof ov.bookmarks]);
    body = (<div className="flex flex-col gap-3">{groups.map(([label, items]) => (<div key={label}><h3 className="text-[12px] uppercase font-bold muted mb-1">{label}</h3>{items.length === 0 ? <p className="muted text-[12px]">—</p> : items.map((i) => (<Link key={`${label}-${i.id}`} href={i.href} className="row text-[13px] font-semibold">📌 {i.title}</Link>))}</div>))}</div>);
  } else if (tab === "games") {
    body = ov.gameScores.length ? <table className="tb"><thead><tr><th>Game</th><th>Skor</th><th>Detail</th><th>Waktu</th></tr></thead><tbody>{ov.gameScores.map((r) => (<tr key={r.id}><td><Tag kind="type" value={r.game} /></td><td className="tabular font-bold">{r.score}</td><td className="muted">{r.detail}</td><td className="muted whitespace-nowrap">{fmtDateTime(r.createdAt)}</td></tr>))}</tbody></table> : <p className="muted text-[12.5px]">Belum ada capaian. <Link href="/games" className="link">Main sekarang ›</Link></p>;
  } else if (tab === "chat") {
    body = ov.chat.length ? <div>{ov.chat.map((r) => (<div key={r.id} className="row"><div className="flex-1 text-[13px]">{r.body}{r.isHidden && <span className="tag t-red ml-2">Dihapus</span>}</div><span className="muted text-[11px] whitespace-nowrap">{fmtDateTime(r.createdAt)}</span></div>))}</div> : <p className="muted text-[12.5px]">Tidak ada pesan dalam 3 hari terakhir.</p>;
  } else {
    body = ov.sorter.length ? <div>{ov.sorter.map((r) => (<div key={r.id} className="row items-center"><div className="flex-1 text-[13px]">Top 3: <b>{r.top3.join(", ")}</b> <span className="muted">({r.count} member)</span></div><span className="muted text-[11px]">{fmtDateTime(r.createdAt)}</span></div>))}</div> : <p className="muted text-[12.5px]">Belum ada hasil Oshi Sorter. <Link href="/games/oshi-sorter" className="link">Coba sekarang ›</Link></p>;
  }
  return (<><PageHead title="Activity" right={<Link href="/account" className="btn ghost sm">‹ Akun</Link>} /><div className="flex flex-wrap gap-2 mb-3">{tabs.map(([k, l]) => (<Link key={k} href={`/account/activity?tab=${k}`} className={`chip ${tab === k ? "on" : ""}`}>{l}</Link>))}</div><div className="card w overflow-x-auto">{body}</div></>);
}
