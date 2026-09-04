import Link from "next/link";
import { notFound } from "next/navigation";
import { Avatar, Disclaimer, Icon, Tag, WidgetHead } from "@/components/ui";
import { BookmarkButton, ReminderButton } from "@/components/ActionButtons";
import { getSchedule, isBookmarked, reminderSet } from "@/lib/data";
import { getViewer } from "@/lib/auth";
import { fmtDateLong, fmtTime } from "@/lib/time";

export const dynamic = "force-dynamic";

export default async function ScheduleDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const s = await getSchedule(Number(id));
  if (!s) notFound();
  const v = await getViewer();
  const [bm, rem] = await Promise.all([isBookmarked(v.userId, "schedule", s.id), reminderSet(v.userId)]);
  const path = `/schedule/${s.id}`;
  return (
    <>
      <Link href="/schedule" className="link text-[12px] inline-flex items-center gap-1 mb-3"><Icon name="chevronL" size={14} /> Kalender</Link>
      <div className="card w mb-3.5">
        <div className="flex gap-1.5 flex-wrap"><Tag kind="type" value={s.type} /><Tag kind="ticket" value={s.ticketStatus} />{s.flag && <span className="tag t-warn">{s.flag}</span>}</div>
        <h1 className="h1">{s.title}</h1>
        <div className="grid sm:grid-cols-2 gap-3 text-[13px]">
          <div className="flex items-start gap-2"><Icon name="clock" size={16} className="muted mt-0.5" /><div><b>{fmtDateLong(s.startAt)}</b><div className="muted">{fmtTime(s.startAt)}{s.endAt ? ` – ${fmtTime(s.endAt)}` : ""} WIB</div></div></div>
          <div className="flex items-start gap-2"><Icon name="location" size={16} className="muted mt-0.5" /><div><b>{s.location ?? "—"}</b>{s.mapUrl && <div><a href={s.mapUrl} target="_blank" rel="noreferrer" className="link">Buka peta ↗</a></div>}</div></div>
        </div>
        {s.setlist && <p className="text-[13px]"><span className="muted">Setlist:</span> <b>{s.setlist}</b></p>}
        {s.description && <p className="text-[13.5px] leading-relaxed">{s.description}</p>}
        <div className="flex gap-2 flex-wrap">
          {v.userId ? <ReminderButton scheduleId={s.id} on={rem.has(s.id)} path={path} /> : <Link href={`/auth/login?next=${path}`} className="btn pri"><Icon name="bell" size={15} /> Ingatkan</Link>}
          {v.userId ? <BookmarkButton type="schedule" id={s.id} on={bm} path={path} /> : <Link href={`/auth/login?next=${path}`} className="btn ghost sm"><Icon name="bookmark" size={14} /> Simpan</Link>}
          {s.ticketUrl && <a href={s.ticketUrl} className="btn ghost sm" target="_blank" rel="noreferrer">Tiket ↗</a>}
        </div>
      </div>
      <div className="grid12">
        <div className="c8 card w">
          <WidgetHead title={`Lineup Member (${s.lineup.length})`} />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {s.lineup.map((m) => (<Link key={m.id} href={`/member/${m.slug}`} className="flex items-center gap-2 rounded-[10px] border border-border p-2 hover:bg-surface-2"><Avatar name={m.name} size={30} /><span className="min-w-0"><span className="block text-[12.5px] font-semibold truncate">{m.nickname}</span><span className="muted text-[10.5px]">Gen {m.generation ?? "-"}</span></span></Link>))}
            {s.lineup.length === 0 && <p className="muted text-[12.5px] col-span-full">Lineup belum diumumkan.</p>}
          </div>
        </div>
        <div className="c4 card w">
          <WidgetHead title="Berita Terkait" href="/news" />
          {s.related.length === 0 && <p className="muted text-[12.5px]">Belum ada berita terkait.</p>}
          {s.related.map((n) => (<Link key={n.id} href={`/news/${n.slug}`} className="row"><span className="text-[13px] font-semibold">{n.title}</span></Link>))}
        </div>
      </div>
      <Disclaimer />
    </>
  );
}
