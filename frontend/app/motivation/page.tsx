import Link from "next/link";
import { Disclaimer, PageHead } from "@/components/ui";
import { dailyMotivation, listMotivations } from "@/lib/data";
import { fmtDateLong } from "@/lib/time";
import { ShareCard } from "@/components/ShareCard";
export const dynamic = "force-dynamic";
export default async function MotivationPage({ searchParams }: { searchParams: Promise<{ id?: string }> }) {
  const { id } = await searchParams;
  const [daily, all] = await Promise.all([dailyMotivation(), listMotivations()]);
  const cur = (id ? all.find((m) => m.id === Number(id)) : null) ?? daily;
  return (
    <>
      <PageHead title="Motivation" sub="Pesan inspiratif harian · kartu siap dibagikan" />
      <div className="grid12">
        <div className="c8 flex flex-col gap-3">
          {cur ? <ShareCard quote={cur.quote} author={cur.author ?? "JKT48Verse"} template={cur.template} date={fmtDateLong(cur.featuredOn ? cur.featuredOn + "T12:00:00+07:00" : cur.createdAt, false)} /> : <div className="card w"><p className="muted">Belum ada pesan.</p></div>}
        </div>
        <div className="c4 card w self-start">
          <div className="w-head"><h3>Galeri Harian</h3></div>
          {all.map((m) => (<Link key={m.id} href={`/motivation?id=${m.id}`} className={`row flex-col gap-0.5 ${cur?.id === m.id ? "text-primary" : ""}`}><span className="text-[12.5px] font-semibold line-clamp-2">“{m.quote}”</span><span className="muted text-[11px]">{fmtDateLong(m.featuredOn ? m.featuredOn + "T12:00:00+07:00" : m.createdAt, false)} · {m.template}</span></Link>))}
        </div>
      </div>
      <Disclaimer />
    </>
  );
}
