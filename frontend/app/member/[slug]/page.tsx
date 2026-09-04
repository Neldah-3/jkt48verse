import Link from "next/link";
import { notFound } from "next/navigation";
import { Avatar, Disclaimer, Empty, Icon, Tag, WidgetHead } from "@/components/ui";
import { getMemberBySlug, memberNews, memberSchedules } from "@/lib/data";
import { ageFrom, fmtDateLong, fmtDateShort, fmtTime, relTime } from "@/lib/time";

export const dynamic = "force-dynamic";

const SOCIAL_LABEL: Record<string, string> = { twitter: "X / Twitter", instagram: "Instagram", tiktok: "TikTok", threads: "Threads", showroom: "Showroom", idn_app: "IDN Live" };

export default async function MemberDetail({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const m = await getMemberBySlug(slug);
  if (!m) notFound();
  const [sch, nws] = await Promise.all([memberSchedules(m.id), memberNews(m.name)]);
  const socials = Object.entries(m.socials ?? {}).filter(([, v]) => v);
  return (
    <>
      <Link href="/member" className="link text-[12px] inline-flex items-center gap-1 mb-3"><Icon name="chevronL" size={14} /> Semua member</Link>
      <div className="card w mb-3.5">
        <div className="flex flex-col sm:flex-row gap-5 items-start">
          <Avatar name={m.name} size={110} className="!text-[34px]" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap"><Tag kind="status" value={m.status} />{m.team && <span className="tag t-gray">{m.team}</span>}<span className="tag t-violet">Gen {m.generation ?? "-"}</span></div>
            <h1 className="h1 mt-2">{m.name}</h1>
            <p className="muted text-[13px]">@{m.nickname}</p>
            <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4 text-[12.5px]">
              <div><dt className="muted text-[11px] uppercase font-bold">Tanggal lahir</dt><dd className="font-semibold">{m.birthDate ? `${fmtDateLong(m.birthDate + "T00:00:00+07:00", false)} (${ageFrom(m.birthDate)} th)` : "—"}</dd></div>
              <div><dt className="muted text-[11px] uppercase font-bold">Tinggi</dt><dd className="font-semibold">{m.height ?? "—"}</dd></div>
              <div><dt className="muted text-[11px] uppercase font-bold">Gol. darah</dt><dd className="font-semibold">{m.bloodType ?? "—"}</dd></div>
              <div><dt className="muted text-[11px] uppercase font-bold">Zodiak</dt><dd className="font-semibold">{m.horoscope ?? "—"}</dd></div>
            </dl>
          </div>
        </div>
      </div>
      <div className="grid12">
        <div className="c8 flex flex-col gap-3.5">
          <div className="card w">
            <WidgetHead title="Jikoshoukai" />
            <blockquote className="border-l-4 border-primary pl-4 italic text-[14.5px] leading-relaxed">“{m.jikoshoukai ?? "—"}”</blockquote>
          </div>
          <div className="card w">
            <WidgetHead title="Informasi Personal" />
            <div className="grid sm:grid-cols-2 gap-3 text-[13px]"><div><div className="muted text-[11px] uppercase font-bold">Hobi</div>{m.hobbies ?? "—"}</div><div><div className="muted text-[11px] uppercase font-bold">Trivia</div>{m.trivia ?? "—"}</div></div>
          </div>
          <div className="card w">
            <WidgetHead title="Jadwal Tampil" href="/schedule" />
            {sch.length === 0 && <Empty icon="calendar" title="Belum ada jadwal mendatang" />}
            {sch.map((s) => (
              <Link key={s.id} href={`/schedule/${s.id}`} className="sch">
                <div className="timebox"><b>{fmtTime(s.startAt)}</b><span>{fmtDateShort(s.startAt)}</span></div>
                <div className="flex-1 min-w-0"><div className="text-[13px] font-semibold truncate">{s.title}</div><div className="muted text-[11.5px] flex items-center gap-1"><Icon name="location" size={12} />{s.location}</div></div>
                <Tag kind="type" value={s.type} />
              </Link>
            ))}
          </div>
          <div className="card w">
            <WidgetHead title="Riwayat News Terkait" href="/news" />
            {nws.length === 0 && <Empty icon="news" title="Belum ada berita yang menyebut member ini" />}
            {nws.map((n) => (<Link key={n.id} href={`/news/${n.slug}`} className="row items-center"><div className="flex-1 min-w-0"><div className="text-[13px] font-semibold truncate">{n.title}</div><div className="muted text-[11px]">{relTime(n.publishedAt)}</div></div><Tag kind="type" value={n.category} /></Link>))}
          </div>
        </div>
        <div className="c4 flex flex-col gap-3.5">
          <div className="card w">
            <WidgetHead title="Media Sosial" />
            {socials.length === 0 && <p className="muted text-[12.5px]">Belum ada tautan resmi.</p>}
            {socials.map(([k, v]) => (<a key={k} href={v} target="_blank" rel="noreferrer" className="sb-item text-[13px]"><Icon name="external" size={15} /><span className="flex-1">{SOCIAL_LABEL[k] ?? k}</span><span className="muted text-[11px] truncate max-w-[120px]">{v.replace(/^https?:\/\/(www\.)?/, "")}</span></a>))}
          </div>
          <div className="card w">
            <WidgetHead title="Galeri" />
            <div className="grid grid-cols-3 gap-2">{[1, 2, 3, 4, 5, 6].map((i) => (<div key={i} className={`aspect-square rounded-[12px] g${((m.id + i) % 6) + 1} opacity-80 flex items-center justify-center text-white text-[11px] font-bold`}>{m.nickname[0]}</div>))}</div>
            <p className="muted text-[10.5px]">Foto resmi tidak ditampilkan sebagai aset UI — kunjungi akun resmi member.</p>
          </div>
        </div>
      </div>
      <Disclaimer />
    </>
  );
}
