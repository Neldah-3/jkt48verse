import Link from "next/link";
import { PageHead } from "@/components/ui";
import { LiveHistoryTable } from "@/components/LiveHistoryTable";
import { wibDateKey } from "@/lib/time";

export const dynamic = "force-dynamic";

export default async function RecentPage({ searchParams }: { searchParams: Promise<{ member?: string; platform?: string; date?: string }> }) {
  const sp = await searchParams;
  const days = [0, 1, 2].map((i) => wibDateKey(new Date(Date.now() - i * 86400_000)));
  const q = (o: Record<string, string | undefined>) => { const p = new URLSearchParams(); Object.entries({ ...sp, ...o }).forEach(([k, v]) => v && p.set(k, v)); const s = p.toString(); return `/live/recent${s ? `?${s}` : ""}`; };
  return (
    <>
      <PageHead title="Riwayat Live" sub="Siaran 3 hari terakhir · waktu WIB" right={<Link href="/live" className="btn ghost sm">‹ Live</Link>} />
      <div className="card w">
        <div className="flex flex-wrap gap-2 items-center">
          <form className="flex gap-2 items-center"><input name="member" defaultValue={sp.member} placeholder="Filter member…" className="input" style={{ width: 180, padding: "6px 10px" }} />{sp.platform && <input type="hidden" name="platform" value={sp.platform} />}<button className="btn ghost sm">Cari</button></form>
          <Link href={q({ platform: undefined })} className={`chip ${!sp.platform ? "on" : ""}`}>Semua</Link>
          <Link href={q({ platform: "showroom" })} className={`chip ${sp.platform === "showroom" ? "on" : ""}`}>Showroom</Link>
          <Link href={q({ platform: "idn" })} className={`chip ${sp.platform === "idn" ? "on" : ""}`}>IDN</Link>
          <span className="muted text-[11px]">|</span>
          <Link href={q({ date: undefined })} className={`chip ${!sp.date ? "on" : ""}`}>3 hari</Link>
          {days.map((d) => <Link key={d} href={q({ date: d })} className={`chip ${sp.date === d ? "on" : ""}`}>{d.slice(5)}</Link>)}
        </div>
        <LiveHistoryTable member={sp.member} platform={sp.platform} date={sp.date} />
      </div>
    </>
  );
}
