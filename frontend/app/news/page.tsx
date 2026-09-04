import Link from "next/link";
import { Avatar, Disclaimer, Empty, Icon, PageHead, Tag } from "@/components/ui";
import { listNews, popularNews } from "@/lib/data";
import { getViewer } from "@/lib/auth";
import { relTime } from "@/lib/time";

export const dynamic = "force-dynamic";
const CATS = [["latest", "Terbaru"], ["theater", "Theater"], ["event", "Event"], ["release", "Release"], ["birthday", "Birthday"], ["other", "Lainnya"]];

export default async function NewsPage({ searchParams }: { searchParams: Promise<{ c?: string }> }) {
  const { c = "latest" } = await searchParams;
  const [rows, pop, v] = await Promise.all([listNews(c, 30), popularNews(), getViewer()]);
  const hl = rows.find((n) => n.isHighlighted);
  const rest = rows.filter((n) => n.id !== hl?.id);
  return (
    <>
      <PageHead title="News" sub="Warta & pengumuman resmi seputar JKT48" right={<div className="flex flex-wrap gap-2">{CATS.map(([k, l]) => (<Link key={k} href={`/news?c=${k}`} className={`chip ${c === k ? "on" : ""}`}>{l}</Link>))}</div>} />
      <div className="grid12">
        <div className="c8 flex flex-col gap-3">
          {rows.length === 0 && <div className="card"><Empty icon="news" title="Belum ada berita" hint="Kategori ini belum memiliki artikel." /></div>}
          {hl && (
            <div className="card w" style={{ borderLeft: "4px solid var(--primary)" }}>
              <div className="flex items-center gap-2"><span className="tag t-red">★ Highlight</span><Tag kind="type" value={hl.category} /><span className="muted text-[11px]">{relTime(hl.publishedAt)}</span></div>
              <h2 className="text-[17px] font-bold leading-snug">{hl.title}</h2>
              <p className="muted text-[13px]">{hl.summary}</p>
              <div className="flex gap-2"><Link href={`/news/${hl.slug}`} className="btn pri sm">Baca</Link><Link href={v.userId ? `/news/${hl.slug}` : "/auth/login?next=/news"} className="btn ghost sm"><Icon name="bookmark" size={14} /> Simpan</Link></div>
            </div>
          )}
          {rest.map((n) => (
            <Link key={n.id} href={`/news/${n.slug}`} className="card w hover:shadow-lg transition">
              <div className="flex items-center gap-2"><Tag kind="type" value={n.category} /><span className="muted text-[11px]">{relTime(n.publishedAt)}</span><span className="muted text-[11px] ml-auto inline-flex items-center gap-1"><Icon name="eye" size={12} />{n.views.toLocaleString("id-ID")}</span></div>
              <h3 className="text-[14px] font-bold leading-snug">{n.title}</h3>
              <p className="muted text-[12.5px]">{n.summary}</p>
            </Link>
          ))}
        </div>
        <div className="c4 flex flex-col gap-3.5">
          <div className="card w">
            <div className="w-head"><h3>Berita Terpopuler</h3></div>
            {pop.map((n, i) => (<Link key={n.id} href={`/news/${n.slug}`} className="flex gap-3 py-2 border-b border-border last:border-0"><span className="w-6 h-6 rounded-[6px] inline-flex items-center justify-center text-[11px] font-bold text-white flex-shrink-0" style={{ background: ["#d4a017", "#9aa3ad", "#b87333"][i] }}>{i + 1}</span><span className="text-[12.5px] font-semibold leading-snug">{n.title}</span></Link>))}
          </div>
          <div className="card w">
            <div className="w-head"><h3>Berlangganan Alert</h3></div>
            <p className="muted text-[12.5px]">Dapatkan notifikasi <b>NEWS_ALERT</b> untuk kategori favoritmu.</p>
            <div className="flex gap-1.5 flex-wrap">{["theater", "event", "release", "birthday"].map((k) => <Tag key={k} kind="type" value={k} />)}</div>
            <Link href={v.userId ? "/account/settings" : "/auth/login?next=/account/settings"} className="btn ghost sm self-start">Kelola Preferensi</Link>
          </div>
          {v.role !== "GUEST" && <div className="card w flex-row items-center gap-3"><Avatar name={v.username} size={32} seed={v.avatarSeed} /><span className="text-[12.5px]">Halo <b>{v.username}</b>, selamat membaca!</span></div>}
        </div>
      </div>
      <Disclaimer />
    </>
  );
}
