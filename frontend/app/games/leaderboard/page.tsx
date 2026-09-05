import Link from "next/link";
import { Avatar, Disclaimer, PageHead } from "@/components/ui";
import { allTimeLeaderboard, dailyLeaderboard } from "@/lib/data";
import { getViewer } from "@/lib/auth";

export const dynamic = "force-dynamic";

type Row = { userId: number; username: string; avatarSeed: number; streak: number; total: number; plays?: number };

function Board({ title, rows, showPlays }: { title: string; rows: Row[]; showPlays?: boolean }) {
  return (
    <div className="card w">
      <h3 className="text-[13.5px] font-bold mb-2">{title}</h3>
      {rows.length === 0 ? (
        <p className="muted text-[12.5px]">
          Belum ada skor. <Link href="/games" className="link">Main sekarang ›</Link>
        </p>
      ) : (
        <ol className="flex flex-col gap-2">
          {rows.map((r, i) => (
            <li key={r.userId} className="row">
              <span
                className={`w-6 h-6 rounded-[7px] inline-flex items-center justify-center text-[11px] font-bold ${i < 3 ? "text-white" : "bg-surface-3"}`}
                style={i < 3 ? { background: ["#d4a017", "#9aa3ad", "#b87333"][i] } : undefined}
              >
                {i + 1}
              </span>
              <Avatar name={r.username} seed={r.avatarSeed} size={26} />
              <span className="flex-1 text-[13px] font-semibold truncate">{r.username}</span>
              {r.streak > 0 && <span className="tag t-red">🔥 {r.streak}</span>}
              {showPlays && <span className="muted text-[11.5px] tabular">{r.plays}×</span>}
              <b className="tabular text-[13px]">{r.total}</b>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export default async function LeaderboardPage() {
  const [v, daily, quizAll, guessAll] = await Promise.all([
    getViewer(),
    dailyLeaderboard(undefined, 10),
    allTimeLeaderboard("quiz", 20),
    allTimeLeaderboard("guess", 20),
  ]);
  return (
    <>
      <PageHead
        title="Leaderboard"
        sub={v.userId ? `Kamu login sebagai ${v.username} — ayo kejar posisi teratas!` : "Login agar skormu tercatat di klasemen"}
        right={<Link href="/games" className="btn ghost sm">‹ Games</Link>}
      />
      <div className="grid12">
        <div className="c6 flex flex-col gap-3.5">
          <Board title="Hari Ini (semua game)" rows={daily} />
          <Board title="Quiz — Sepanjang Masa" rows={quizAll} showPlays />
        </div>
        <div className="c6 flex flex-col gap-3.5">
          <Board title="Guess Member — Sepanjang Masa" rows={guessAll} showPlays />
          <div className="card w">
            <h3 className="text-[13.5px] font-bold">Sistem poin</h3>
            <ul className="muted text-[12px] flex flex-col gap-1 list-disc pl-4">
              <li>Quiz: 30/60/90 poin per soal (easy/medium/hard) + bonus kecepatan.</li>
              <li>Guess Member: 100 poin per soal, −20 per hint, bonus kecepatan.</li>
              <li>Leaderboard harian di-reset pukul 00:00 WIB.</li>
            </ul>
          </div>
        </div>
      </div>
      <Disclaimer />
    </>
  );
}
