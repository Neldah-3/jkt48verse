import Link from "next/link";
import { notFound } from "next/navigation";
import { Disclaimer, Icon } from "@/components/ui";
import { BookmarkButton } from "@/components/ActionButtons";
import { getEncyclopedia, isBookmarked, listEncyclopedia, listGlossary } from "@/lib/data";
import { getViewer } from "@/lib/auth";
import { fmtDateLong } from "@/lib/time";
export const dynamic = "force-dynamic";

function render(md: string) {
  const blocks = md.split("\n\n");
  return blocks.map((b, i) => {
    if (b.startsWith("## ")) return <h2 key={i}>{b.slice(3)}</h2>;
    if (b.trim().startsWith("- ")) return <ul key={i}>{b.split("\n").map((l, j) => <li key={j} dangerouslySetInnerHTML={{ __html: inline(l.replace(/^- /, "")) }} />)}</ul>;
    return <p key={i} dangerouslySetInnerHTML={{ __html: inline(b) }} />;
  });
}
function inline(s: string) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\*(.+?)\*/g, "<i>$1</i>").replace(/\n/g, "<br/>");
}

export default async function EncyclopediaPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const [e, all, v] = await Promise.all([getEncyclopedia(slug), listEncyclopedia(), getViewer()]);
  if (!e) notFound();
  const [gl, bm] = await Promise.all([slug === "wota-culture" ? listGlossary() : Promise.resolve([]), isBookmarked(v.userId, "encyclopedia", e.id)]);
  const path = `/encyclopedia/${slug}`;
  return (
    <>
      <div className="grid12">
        <aside className="c3 self-start"><div className="card w"><h3 className="text-[13.5px] font-bold">Encyclopedia</h3><nav className="flex flex-col gap-0.5">{all.map((a) => (<Link key={a.slug} href={`/encyclopedia/${a.slug}`} className={`sb-item ${a.slug === slug ? "active" : ""}`}><Icon name="book" size={15} />{a.title}</Link>))}</nav><p className="muted text-[10.5px]">Dikelola manual oleh admin · tanpa scraper</p></div></aside>
        <div className="c8"><article className="card w article">
          <div className="flex items-center gap-2 flex-wrap"><span className="tag t-violet">Encyclopedia</span><span className="muted text-[11.5px]">Diperbarui {fmtDateLong(e.updatedAt, false)}</span><span className="flex-1" />{v.userId ? <BookmarkButton type="encyclopedia" id={e.id} on={bm} path={path} /> : <Link href={`/auth/login?next=${path}`} className="btn ghost sm"><Icon name="bookmark" size={14} /> Simpan</Link>}</div>
          <h1 className="h1" style={{ fontSize: 24 }}>{e.title}</h1>
          <div>{render(e.content)}</div>
          {gl.length > 0 && <div className="mt-4"><h2>Glosarium Wota</h2><div className="grid sm:grid-cols-2 gap-2 mt-2">{gl.map((g) => (<div key={g.id} className="rounded-[11px] border border-border p-3"><b className="text-[13px]">{g.term}</b><p className="muted text-[12.5px] !leading-snug mt-0.5">{g.meaning}</p></div>))}</div></div>}
        </article></div>
      </div>
      <Disclaimer />
    </>
  );
}
