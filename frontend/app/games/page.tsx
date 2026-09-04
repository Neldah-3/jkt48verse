import Link from "next/link";
import { Avatar, Disclaimer, Icon, PageHead } from "@/components/ui";
import { dailyLeaderboard, playerCount } from "@/lib/data";
import { getViewer } from "@/lib/auth";
import { fmtDateLong } from "@/lib/time";

export const dynamic = "force-dynamic";

export default async function GamesPage() {
  const v = await getViewer();
  const [lb, pq, pg] = await Promise.all([dailyLeaderboard(undefined, 10), playerCount("quiz"), playerCount("guess")]);
  const streak = v.user?.streak ?? 0;
  const games = [
    { href: "/games/quiz", title: "Quiz", desc: "Benar = 30/60/90 poin (easy/medium/hard) + bonus waktu. 10/20/30 soal per sesi.", icon: "zap" as const, bg: "linear-gradient(135deg,#ff7a59,#e01b3c)", players: pq },
    { href: "/games/guess-member", title: "Guess Member", desc: "Tebak member dari jikoshoukai. 100 poin, −20 per hint, bonus kecepatan.", icon: "users" as const, bg: "linear-gradient(135deg,#8f6bf2,#5a2fd0)", players: pg },
    { href: "/games/oshi-sorter", title: "Oshi Sorter", desc: "Urutkan member aktif sesuai preferensimu. Simpan & bagikan kartu hasil.", icon: "heart" as const, bg: "linear-gradient(135deg,#38b2a3,#1c7c8c)", players: null },
  ];
  return (
    <>
      <PageHead title="Games" sub="Gamifikasi seru untuk wota · skor dihitung di server" right={<Link href="/games/leaderboard" className="btn ghost sm"><Icon name="trophy" size={14} /> Leaderboard</Link>} />
      <div className="daily mb-3.5">
        <span className="flame"><Icon name="flame" size={26} /></span>
        <div className="flex-1 min-w-[200px]">
          <div className="text-[11px] uppercase tracking-wider opacity-75">Daily Challenge · {fmtDateLong(new Date(), false)}</div>
          <div className="font-extrabold text-[16px]">Selesaikan 1 sesi Quiz atau Guess Member hari ini</div>
          <div className="flex gap-1.5 mt-2 flex-wrap"><span className="pill hit">🔥 {streak} hari</span><span className={`pill ${streak >= 7 ? "hit" : ""}`}>7 hari +50</span><span className={`pill ${streak >= 30 ? "hit" : ""}`}>30 hari +200</span><span className={`pill ${streak >= 100 ? "hit" : ""}`}>100 hari +1000</span></div>
        </div>
        <Link href="/games/quiz" className="btn white">Kerjakan Sekarang</Link>
      </div>
      <div className="grid12 mb-3.5">
        {games.map((g) => (
          <div key={g.href} className="c4 card w">
            <span className="qicon" style={{ background: g.bg, width: 44, height: 44 }}><Icon name={g.icon} /></span>
            <h3 className="text-[14px] font-extrabold">{g.title}</h3>
            <p className="muted text-[12px] flex-1">{g.desc}</p>
            <div className="flex items-center justify-between"><span className="muted text-[11.5px]">{g.players !== null ? `${g.players.toLocaleString("id-ID")} pemain` : "Tanpa skor"}</span><Link href={g.href} className="btn pri sm">Main</Link></div>
          </div>
        ))}
      </div>
      <div className="grid12">
        <div className="c8 card w">
          <div className="w-head"><h3>Leaderboard Harian</h3><Link href="/games/leaderboard">Semua ›</Link></div>
          {lb.length === 0 && <p className="muted text-[12.5px]">Belum ada skor hari ini. Jadilah yang pertama!</p>}
          {lb.length > 0 && (
            <table className="tb"><thead><tr><th>#</th><th>User</th><th>Skor</th><th>Streak</th></tr></thead><tbody>
              {lb.map((r, i) => (<tr key={r.userId} style={r.userId === v.userId ? { background: "var(--primary-soft)" } : undefined}><td><span className="w-6 h-6 rounded-[6px] inline-flex items-center justify-center text-[11px] font-bold" style={i < 3 ? { background: ["#d4a017", "#9aa3ad", "#b87333"][i], color: "#fff" } : { background: "var(--surface-3)" }}>{i + 1}</span></td><td className="flex items-center gap-2"><Avatar name={r.username} size={24} seed={r.avatarSeed} />{r.username}{r.userId === v.userId && <span className="tag t-red">kamu</span>}</td><td className="tabular font-bold">{r.total.toLocaleString("id-ID")}</td><td>🔥 {r.streak}</td></tr>))}
            </tbody></table>
          )}
        </div>
        <div className="c4 card w">
          <div className="w-head"><h3>Badge Koleksi</h3></div>
          {v.userId ? (<><div className="flex items-center gap-2"><Avatar name={v.username} size={36} seed={v.avatarSeed} /><div><b className="text-[13px]">{v.username}</b><div className="muted text-[11px]">{(v.user?.points ?? 0).toLocaleString("id-ID")} poin total</div></div></div><div className="flex flex-wrap gap-1.5">{(v.user?.points ?? 0) > 0 && <span className="chip on">🎮 Pemain Pertama</span>}{streak >= 3 && <span className="chip on">🔥 Streak 3</span>}{streak >= 7 && <span className="chip on">🏅 Streak 7</span>}{(v.user?.points ?? 0) >= 1000 && <span className="chip on">💎 1.000 Poin</span>}{(v.user?.points ?? 0) === 0 && <span className="muted text-[12px]">Belum ada badge — mainkan game pertamamu!</span>}</div></>) : <p className="muted text-[12.5px]">Tamu bisa main — skor tidak disimpan. <Link href="/auth/login?next=/games" className="link">Login</Link> untuk leaderboard & streak.</p>}
        </div>
      </div>
      <Disclaimer />
    </>
  );
}
