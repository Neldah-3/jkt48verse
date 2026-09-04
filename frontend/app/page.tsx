import Link from "next/link";
import { Avatar, Disclaimer, Empty, Icon, Tag, WidgetHead, type IconName } from "@/components/ui";
import { LiveDuration } from "@/components/LiveBits";
import { getViewer } from "@/lib/auth";
import { getLiveNow } from "@/lib/live";
import { birthdayToday, dailyLeaderboard, highlightedNews, listNews, recentChat, upcomingSchedules } from "@/lib/data";
import { fmtDateLong, fmtDateShort, fmtTime, relTime, wibParts } from "@/lib/time";

export const dynamic = "force-dynamic";

const QUICK: { href: string; label: string; icon: IconName; bg: string }[] = [
  { href: "/live", label: "Live", icon: "radio", bg: "linear-gradient(135deg,#ff7a59,#e01b3c)" },
  { href: "/schedule", label: "Kalender", icon: "calendar", bg: "linear-gradient(135deg,#4f8ef7,#2b4fd8)" },
  { href: "/news", label: "News", icon: "news", bg: "linear-gradient(135deg,#f7b733,#e0741b)" },
  { href: "/chat", label: "Chat", icon: "chat", bg: "linear-gradient(135deg,#38b2a3,#1c7c8c)" },
  { href: "/games", label: "Games", icon: "gamepad", bg: "linear-gradient(135deg,#8f6bf2,#5a2fd0)" },
  { href: "/ai-search", label: "AI Search", icon: "spark", bg: "linear-gradient(135deg,#f56a9d,#c2255c)" },
];

export default async function Dashboard() {
  const v = await getViewer();
  const [live, highlights, latest, upcoming, bday, chat, lb] = await Promise.all([
    getLiveNow(), highlightedNews(), listNews("latest", 5), upcomingSchedules(5), birthdayToday(), recentChat(5), dailyLeaderboard(undefined, 3),
  ]);
  const hero = highlights[0];
  const minis = highlights.slice(1, 3);
  const { hour } = wibParts(new Date());
  const greet = hour < 11 ? "Selamat pagi" : hour < 15 ? "Selamat siang" : hour < 18 ? "Selamat sore" : "Selamat malam";

  return (
    <>
      <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
        <div>
          <h1 className="h1">{greet}, {v.role === "GUEST" ? "wota" : v.username}! 👋</h1>
          <p className="muted text-[12.5px]">{fmtDateLong(new Date())} · WIB</p>
        </div>
        <Link href="/live" className="chip on"><span className="live-dot" /> {live.length} member sedang live</Link>
      </div>

      <div className="card w mb-3.5">
        <WidgetHead title="Akses Cepat" />
        <div className="quick-grid">
          {QUICK.map((q) => (
            <Link key={q.href} href={q.href} className="quick"><span className="qicon" style={{ background: q.bg }}><Icon name={q.icon} /></span>{q.label}</Link>
          ))}
        </div>
      </div>

      <div className="grid12">
        <div className="c8 flex flex-col gap-3.5">
          {hero ? (
            <div className="hero">
              <span className="tag" style={{ background: "rgba(255,255,255,.18)", color: "#fff", alignSelf: "flex-start" }}>★ Highlight</span>
              <h2>{hero.title}</h2>
              <p className="text-[13px] opacity-90 max-w-[560px]">{hero.summary}</p>
              <div className="flex items-center gap-3 flex-wrap">
                <Link href={`/news/${hero.slug}`} className="btn white">Baca selengkapnya</Link>
                <span className="text-[11.5px] opacity-80">{relTime(hero.publishedAt)}</span>
              </div>
            </div>
          ) : null}
          {minis.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {minis.map((n) => (
                <Link key={n.id} href={`/news/${n.slug}`} className="card w hover:shadow-lg transition">
                  <div className="flex items-center gap-2"><Tag kind="type" value={n.category} /><span className="muted text-[11px]">{relTime(n.publishedAt)}</span></div>
                  <h3 className="text-[14px] font-bold leading-snug">{n.title}</h3>
                  <p className="muted text-[12.5px] line-clamp-2">{n.summary}</p>
                </Link>
              ))}
            </div>
          )}
          <div className="grid12">
            <div className="c6 card w">
              <WidgetHead title="Info Terbaru" href="/news" />
              <div>
                {latest.map((n) => (
                  <Link key={n.id} href={`/news/${n.slug}`} className="row items-center">
                    <div className="flex-1 min-w-0">
                      <div className="text-[13px] font-semibold truncate">{n.title}</div>
                      <div className="flex items-center gap-2 mt-1"><Tag kind="type" value={n.category} /><span className="muted text-[11px]">{relTime(n.publishedAt)}</span></div>
                    </div>
                    <Icon name="chevron" size={15} className="muted" />
                  </Link>
                ))}
              </div>
            </div>
            <div className="c6 card w">
              <WidgetHead title="Jadwal Mendatang" href="/schedule" />
              <div>
                {upcoming.length === 0 && <Empty icon="calendar" title="Belum ada jadwal" hint="Cek lagi nanti ya." />}
                {upcoming.map((s) => (
                  <Link key={s.id} href={`/schedule/${s.id}`} className="sch">
                    <div className="timebox"><b>{fmtTime(s.startAt)}</b><span>{fmtDateShort(s.startAt)}</span></div>
                    <div className="flex-1 min-w-0">
                      <div className="text-[13px] font-semibold truncate">{s.title}</div>
                      <div className="flex items-center gap-2 mt-1 flex-wrap"><Tag kind="type" value={s.type} /><Tag kind="ticket" value={s.ticketStatus} /></div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="c4 flex flex-col gap-3.5">
          <div className="card w">
            <WidgetHead title="Member Live" href="/live" />
            {live.length === 0 && <Empty icon="radio" title="Belum ada yang live sekarang" hint="Nyalakan Live Alert untuk oshi-mu." />}
            {live.slice(0, 3).map((l) => (
              <Link key={l.id} href={`/live?watch=${l.id}`} className="flex items-center gap-3">
                <div className="relative w-[64px] h-[40px] rounded-[8px] overflow-hidden flex-shrink-0" style={{ background: "linear-gradient(135deg,#1d2333,#0f1220)" }}>
                  {l.imageUrl && <img src={l.imageUrl} alt="" className="w-full h-full object-cover" />}
                  <span className="badge-live absolute left-1 top-1" style={{ fontSize: 8, padding: "1px 4px" }}>Live</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[13px] font-semibold truncate">{l.memberName}</div>
                  <div className="flex items-center gap-2"><span className={`tag ${l.platform === "idn" ? "t-info" : "t-red"}`}>{l.platform}</span><LiveDuration startedAt={l.startedAt.toISOString()} /></div>
                </div>
              </Link>
            ))}
          </div>

          <div className="card w">
            <WidgetHead title="Birthday Hari Ini" href="/birthday" />
            {bday.length === 0 ? (
              <p className="muted text-[12.5px]">Tidak ada member yang berulang tahun hari ini. <Link href="/birthday?tab=week" className="link">Lihat minggu ini ›</Link></p>
            ) : (
              bday.map((m) => (
                <div key={m.id} className="bday flex items-center gap-3">
                  <Avatar name={m.name} size={44} />
                  <div className="flex-1 min-w-0">
                    <span className="tag t-warn">🎂 Hari ini</span>
                    <div className="font-bold text-[13.5px] mt-1 truncate">{m.name}</div>
                  </div>
                  <Link href="/birthday" className="btn pri sm">Ucapan</Link>
                </div>
              ))
            )}
          </div>

          <div className="card w">
            <WidgetHead title="Aktivitas Komunitas" href="/chat" />
            <div className="flex flex-col gap-2">
              {chat.length === 0 && <p className="muted text-[12.5px]">Belum ada pesan. Jadilah yang pertama menyapa!</p>}
              {chat.slice(-2).map((c) => (
                <div key={c.id} className="flex gap-2">
                  <Avatar name={c.username} size={28} seed={c.avatarSeed} />
                  <div className="bubble flex-1"><b className="text-[12px]">{c.username}</b> <span className="muted text-[10.5px]">{fmtTime(c.createdAt)}</span><div>{c.body}</div></div>
                </div>
              ))}
            </div>
            <div className="border-t border-border pt-2">
              <div className="flex items-center justify-between mb-1"><span className="text-[12px] font-bold">Leaderboard harian</span><Link href="/games/leaderboard" className="link">Semua ›</Link></div>
              {lb.length === 0 && <p className="muted text-[12px]">Belum ada skor hari ini — <Link href="/games" className="link">main sekarang</Link>.</p>}
              {lb.map((r, i) => (
                <div key={r.userId} className="flex items-center gap-2 py-1.5 text-[12.5px]">
                  <span className="w-5 h-5 rounded-[6px] inline-flex items-center justify-center text-[10px] font-bold text-white" style={{ background: ["#d4a017", "#9aa3ad", "#b87333"][i] }}>{i + 1}</span>
                  <Avatar name={r.username} size={22} seed={r.avatarSeed} />
                  <span className="flex-1 truncate">{r.username}</span>
                  <b className="tabular">{r.total.toLocaleString("id-ID")}</b>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <Disclaimer />
    </>
  );
}
