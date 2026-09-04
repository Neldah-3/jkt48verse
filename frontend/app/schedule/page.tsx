import Link from "next/link";
import { Disclaimer, Empty, Icon, PageHead, Tag, TYPE_TAG } from "@/components/ui";
import { ReminderButton } from "@/components/ActionButtons";
import { reminderSet, schedulesInRange, upcomingSchedules } from "@/lib/data";
import { getViewer } from "@/lib/auth";
import { fmtDateLong, fmtDateShort, fmtTime, monthName, wibDateKey, wibMidnight, wibParts } from "@/lib/time";

export const dynamic = "force-dynamic";
const COLORS: Record<string, string> = { theater: "var(--primary)", event: "var(--warn)", concert: "var(--violet)", media: "var(--info)", other: "var(--muted)" };

export default async function SchedulePage({ searchParams }: { searchParams: Promise<{ type?: string; m?: string; y?: string; mode?: string; d?: string }> }) {
  const sp = await searchParams;
  const now = wibParts(new Date());
  const y = Number(sp.y ?? now.year);
  const m = Number(sp.m ?? now.month);
  const type = sp.type ?? "all";
  const mode = sp.mode ?? "monthly";
  const v = await getViewer();
  const monthStart = wibMidnight(y, m, 1);
  const nextMonth = wibMidnight(m === 12 ? y + 1 : y, m === 12 ? 1 : m + 1, 1);
  const [monthRows, rem] = await Promise.all([schedulesInRange(monthStart, nextMonth, type), reminderSet(v.userId)]);

  let list = monthRows;
  let listLabel = `${monthName(m)} ${y}`;
  if (mode === "daily") {
    const key = sp.d ?? wibDateKey();
    list = monthRows.filter((s) => wibDateKey(s.startAt) === key);
    if (!sp.d && list.length === 0) list = await upcomingSchedules(10, type);
    listLabel = sp.d ? fmtDateLong(key + "T12:00:00+07:00") : "Hari ini & mendatang";
  } else if (mode === "weekly") {
    const start = wibMidnight(now.year, now.month, now.day);
    start.setUTCDate(start.getUTCDate() - ((now.weekday + 6) % 7));
    const end = new Date(start.getTime() + 7 * 86400_000);
    list = await schedulesInRange(start, end, type);
    listLabel = `Minggu ini (${fmtDateShort(start)} – ${fmtDateShort(new Date(end.getTime() - 1))})`;
  }

  const firstWeekday = wibParts(monthStart).weekday; // 0 sun
  const offset = (firstWeekday + 6) % 7; // monday first
  const daysInMonth = Math.round((nextMonth.getTime() - monthStart.getTime()) / 86400_000);
  const cells: { day: number | null; key?: string; types: string[] }[] = [];
  for (let i = 0; i < offset; i++) cells.push({ day: null, types: [] });
  for (let d = 1; d <= daysInMonth; d++) {
    const key = `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    cells.push({ day: d, key, types: [...new Set(monthRows.filter((s) => wibDateKey(s.startAt) === key).map((s) => s.type))] });
  }
  const prev = m === 1 ? { y: y - 1, m: 12 } : { y, m: m - 1 };
  const next = m === 12 ? { y: y + 1, m: 1 } : { y, m: m + 1 };
  const q = (o: Record<string, string | number | undefined>) => { const p = new URLSearchParams(); Object.entries({ ...sp, ...o }).forEach(([k, val]) => val !== undefined && val !== "" && p.set(k, String(val))); const s = p.toString(); return `/schedule${s ? `?${s}` : ""}`; };
  const todayKey = wibDateKey();

  return (
    <>
      <PageHead title="Jadwal" sub="Theater, event, konser & media · semua waktu WIB" right={
        <div className="flex flex-wrap gap-2">
          {["all", "theater", "event", "concert", "media"].map((t) => (<Link key={t} href={q({ type: t === "all" ? undefined : t })} className={`chip ${type === t ? "on" : ""}`}>{t === "all" ? "Semua" : TYPE_TAG[t].label}</Link>))}
        </div>
      } />
      <div className="grid12">
        <div className="c4">
          <div className="card w">
            <div className="seg self-start">
              {[["daily", "Harian"], ["weekly", "Mingguan"], ["monthly", "Bulanan"]].map(([k, l]) => (<Link key={k} href={q({ mode: k, d: undefined })}><button className={mode === k ? "on" : ""}>{l}</button></Link>))}
            </div>
            <div className="w-head">
              <Link href={q({ y: prev.y, m: prev.m })} className="btn icon ghost" aria-label="Bulan sebelumnya"><Icon name="chevronL" size={16} /></Link>
              <h3>{monthName(m)} {y}</h3>
              <Link href={q({ y: next.y, m: next.m })} className="btn icon ghost" aria-label="Bulan berikutnya"><Icon name="chevron" size={16} /></Link>
            </div>
            <div className="cal">
              {["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"].map((d) => (<div key={d} className="text-center muted text-[10.5px] font-bold uppercase">{d}</div>))}
              {cells.map((c, i) => c.day === null ? <div key={i} /> : (
                <Link key={i} href={q({ mode: "daily", d: c.key })} className={`cell ${c.key === todayKey ? "today" : c.types.length ? "has" : ""}`}>
                  <span>{c.day}</span>
                  <span className="dots">{c.types.slice(0, 3).map((t) => (<span key={t} className="dot" style={{ background: c.key === todayKey ? "#fff" : COLORS[t] }} />))}</span>
                </Link>
              ))}
            </div>
            <div className="flex flex-wrap gap-3 text-[11px] muted">{Object.entries(COLORS).map(([t, c]) => (<span key={t} className="inline-flex items-center gap-1"><span className="dot inline-block w-2 h-2 rounded-full" style={{ background: c }} />{TYPE_TAG[t].label}</span>))}</div>
          </div>
        </div>
        <div className="c8">
          <div className="card w">
            <div className="w-head"><h3>{listLabel}</h3><span className="muted text-[11.5px]">{list.length} agenda</span></div>
            {list.length === 0 && <Empty icon="calendar" title="Tidak ada agenda" hint="Coba pilih tanggal atau filter lain." />}
            {list.map((s) => (
              <div key={s.id} className="sch">
                <Link href={`/schedule/${s.id}`} className="timebox"><b>{fmtTime(s.startAt)}</b><span>{fmtDateShort(s.startAt)}</span></Link>
                <div className="flex-1 min-w-0">
                  <Link href={`/schedule/${s.id}`} className="text-[13.5px] font-semibold hover:underline">{s.title}{s.flag && <span className="tag t-warn ml-2 align-middle">{s.flag}</span>}</Link>
                  <div className="muted text-[11.5px] flex items-center gap-1 mt-0.5"><Icon name="location" size={12} />{s.mapUrl ? <a href={s.mapUrl} target="_blank" rel="noreferrer" className="hover:underline">{s.location}</a> : s.location}</div>
                  <div className="flex gap-1.5 mt-1 flex-wrap"><Tag kind="type" value={s.type} /><Tag kind="ticket" value={s.ticketStatus} /></div>
                </div>
                {v.userId ? <ReminderButton scheduleId={s.id} on={rem.has(s.id)} path="/schedule" small /> : <Link href={`/auth/login?next=/schedule`} className="btn ghost sm"><Icon name="bell" size={14} /> Ingatkan</Link>}
              </div>
            ))}
            <p className="muted text-[11px]">Ingatkan Saya mengirim notifikasi 30 & 5 menit sebelum acara · khusus terdaftar</p>
          </div>
        </div>
      </div>
      <Disclaimer />
    </>
  );
}
