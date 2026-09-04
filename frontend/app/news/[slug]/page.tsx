import Link from "next/link";
import { notFound } from "next/navigation";
import { Disclaimer, Icon, Tag } from "@/components/ui";
import { BookmarkButton } from "@/components/ActionButtons";
import { getNews, isBookmarked, listNews } from "@/lib/data";
import { getViewer } from "@/lib/auth";
import { fmtDateTime } from "@/lib/time";

export const dynamic = "force-dynamic";

export default async function NewsDetail({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const n = await getNews(slug);
  if (!n) notFound();
  const v = await getViewer();
  const [bm, more] = await Promise.all([isBookmarked(v.userId, "news", n.id), listNews(n.category, 4)]);
  const path = `/news/${n.slug}`;
  return (
    <>
      <Link href="/news" className="link text-[12px] inline-flex items-center gap-1 mb-3"><Icon name="chevronL" size={14} /> Semua berita</Link>
      <article className="card w article mx-auto">
        <div className="flex items-center gap-2 flex-wrap"><Tag kind="type" value={n.category} />{n.isHighlighted && <span className="tag t-red">★ Highlight</span>}<span className="muted text-[11.5px]">{fmtDateTime(n.publishedAt)}</span></div>
        <h1 className="h1" style={{ fontSize: 24 }}>{n.title}</h1>
        <p className="muted text-[14px] italic">{n.summary}</p>
        <div className="flex gap-2">{v.userId ? <BookmarkButton type="news" id={n.id} on={bm} path={path} /> : <Link href={`/auth/login?next=${path}`} className="btn ghost sm"><Icon name="bookmark" size={14} /> Simpan</Link>}<span className="muted text-[11.5px] self-center inline-flex items-center gap-1"><Icon name="eye" size={12} />{(n.views + 1).toLocaleString("id-ID")} dibaca</span></div>
        <div className="border-t border-border pt-3">{n.body.split("\n\n").map((p, i) => (<p key={i} className="mb-3">{p}</p>))}</div>
        <p className="muted text-[11px]">Sumber: pengumuman resmi / kurasi admin JKT48Verse.</p>
      </article>
      <div className="article mx-auto mt-4">
        <h3 className="text-[13.5px] font-bold mb-2">Berita lain · {n.category}</h3>
        <div className="flex flex-col gap-2">{more.filter((x) => x.id !== n.id).slice(0, 3).map((x) => (<Link key={x.id} href={`/news/${x.slug}`} className="card w py-3"><span className="text-[13px] font-semibold">{x.title}</span></Link>))}</div>
      </div>
      <Disclaimer />
    </>
  );
}
