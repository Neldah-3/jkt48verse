import Link from "next/link";
import { Avatar, PageHead } from "@/components/ui";
import { allTimeLeaderboard, dailyLeaderboard } from "@/lib/data";
import { getViewer } from "@/lib/auth";
export const dynamic = "force-dynamic";
export default async function LeaderboardPage({ searchParams }: { searchParams: Promise<{ g?: string }> }) {
  const { g = "quiz" } = await searchParams;
  const [v, daily, all] = await Promise.all([getViewer(), dailyLeaderboard(g === "daily" ? undefined : g, 10), allTimeLeaderboard(g === "daily" ? "daily" : g, 20)]);
  const Table = ({ rows }: { rows: { userId: number; username: string; avatarSeed: number; total: number; streak: number }[] }) => rows.length === 0 ? <p className="muted text-[12.5px]">Belum ada data.</p> : (
    <table className="tb"><thead><tr><th>#</th><th>User</th><th>Skor</th><th>Streak</th></tr></thead><tbody>{rows.map((r, i) => (<tr key={r.userId} style={r.userId === v.userId ? { background: "var(--primary-soft)" } : undefined}><td><span className="w-6 h-6 rounded-[6px] inline-flex items-center justify-center text-[11px] font-bold" style={i < 3 ? { background: ["#d4a017", "#9aa3ad", "#b87333"][i], color: "#fff" } : { background: "var(--surface-3)" }}>{i + 1}</span></td><td><span className="inline-flex items-center gap-2"><Avatar name={r.username} size={24} seed={r.avatarSeed} />{r.username}{r.userId === v.userId && <span className="tag t-red">kamu</span>}</span></td><td className="tabular font-bold">{r.total.toLocaleString("id-ID")}</td><td>🔥 {r.streak}</td></tr>))}</tbody></table>
  );
  return (
    <>
      <PageHead title="Leaderboard" sub="Peringkat harian (reset 00:00 WIB) & sepanjang masa" right={<div className="seg">{[["quiz", "Quiz"], ["guess", "Guess Member"], ["daily", "Daily"]].map(([k, l]) => (<Link key={k} href={`/games/leaderboard?g=${k}`}><button className={g === k ? "on" : ""}>{l}</button></Link>))}</div>} />
      <div className="grid12"><div className="c6 card w"><div className="w-head"><h3>Hari ini</h3></div><Table rows={daily} /></div><div className="c6 card w"><div className="w-head"><h3>Sepanjang masa</h3></div><Table rows={all} /></div></div>
      <p className="muted text-[11.5px] mt-3"><Link href="/games" className="link">‹ Kembali ke Games</Link></p>
    </>
  );
}
