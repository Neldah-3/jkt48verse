import Link from "next/link";
import { Avatar, Disclaimer, Icon, PageHead, type IconName } from "@/components/ui";
import { dailyLeaderboard, playerCount } from "@/lib/data";
import { getViewer } from "@/lib/auth";

export const dynamic = "force-dynamic";

const GAMES: { href: string; title: string; desc: string; icon: IconName; bg: string }[] = [
  {
    href: "/games/quiz",
    title: "Quiz JKT48",
    desc: "Uji wawasanmu soal JKT48 & 48 Group. 3 level, bonus kecepatan, skor di-server.",
    icon: "spark",
    bg: "linear-gradient(135deg,#8f6bf2,#5a2fd0)",
  },
  {
    href: "/games/guess-member",
    title: "Guess Member",
    desc: "Tebak member dari jikoshoukai yang disensor. 5 soal, 3 hint tersedia.",
    icon: "users",
    bg: "linear-gradient(135deg,#f26b8f,#c2255c)",
  },
  {
    href: "/games/oshi-sorter",
    title: "Oshi Sorter",
    desc: "Susun peringkat oshi-mu, simpan ke akun, dan bagikan top 10 ke teman.",
    icon: "heart",
    bg: "linear-gradient(135deg,#f2a06b,#d0732a)",
  },
  {
    href: "/games/leaderboard",
    title: "Leaderboard",
    desc: "Klasemen poin harian & sepanjang masa komunitas JKT48Verse.",
    icon: "trophy",
    bg: "linear-gradient(135deg,#38bdf8,#1d6fb8)",
  },
];

export default async function GamesPage() {
  const [v, lb, quizPlayers, guessPlayers] = await Promise.all([
    getViewer(),
    dailyLeaderboard(undefined, 5),
    playerCount("quiz"),
    playerCount("guess"),
  ]);
  const guest = !v.userId;
  return (
    <>
      <PageHead
        title="Games"
        sub={guest ? "Main sebagai tamu — login agar skor tersimpan & masuk leaderboard" : `Main sebagai ${v.username} — skor otomatis masuk leaderboard`}
      />
      <div className="grid sm:grid-cols-2 gap-3.5">
        {GAMES.map((g) => (
          <Link key={g.href} href={g.href} className="card w hover:border-primary transition group">
            <span
              className="w-10 h-10 rounded-[12px] inline-flex items-center justify-center text-white mb-2"
              style={{ background: g.bg }}
            >
              <Icon name={g.icon} size={20} />
            </span>
            <h3 className="text-[14.5px] font-bold group-hover:text-primary">{g.title}</h3>
            <p className="muted text-[12.5px]">{g.desc}</p>
          </Link>
        ))}
      </div>
      <div className="grid12 mt-3.5">
        <div className="c8 card w">
          <div className="w-head">
            <h3>Leaderboard Hari Ini</h3>
            <Link href="/games/leaderboard" className="link">
              Semua ›
            </Link>
          </div>
          {lb.length === 0 ? (
            <p className="muted text-[12.5px]">
              Belum ada skor hari ini — jadilah yang pertama <Link href="/games/quiz" className="link">main</Link>!
            </p>
          ) : (
            <ol className="flex flex-col gap-2">
              {lb.map((r, i) => (
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
                  <b className="tabular text-[13px]">{r.total} poin</b>
                </li>
              ))}
            </ol>
          )}
        </div>
        <div className="c4 flex flex-col gap-3.5">
          <div className="card w">
            <h3 className="text-[13.5px] font-bold">Statistik</h3>
            <div className="flex flex-col gap-1.5 text-[13px]">
              <div className="row">
                <span className="muted flex-1">Pemain Quiz</span>
                <b className="tabular">{quizPlayers}</b>
              </div>
              <div className="row">
                <span className="muted flex-1">Pemain Guess Member</span>
                <b className="tabular">{guessPlayers}</b>
              </div>
            </div>
          </div>
          <div className="card w">
            <h3 className="text-[13.5px] font-bold">Cara main</h3>
            <ul className="muted text-[12px] flex flex-col gap-1 list-disc pl-4">
              <li>Semua penilaian dilakukan di server — anti curang.</li>
              <li>Selesaikan game untuk menambah poin & streak harian.</li>
              <li>Streak 7/30/100 hari memberi bonus poin.</li>
            </ul>
          </div>
        </div>
      </div>
      <Disclaimer />
    </>
  );
}
