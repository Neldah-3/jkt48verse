import Link from "next/link";
import { PageHead, Disclaimer } from "@/components/ui";
import LivePanel from "@/components/LiveBits";
import { getLiveNow } from "@/lib/live";
import { getViewer } from "@/lib/auth";
import { LiveHistoryTable } from "@/components/LiveHistoryTable";

export const dynamic = "force-dynamic";

export default async function LivePage({ searchParams }: { searchParams: Promise<{ watch?: string; demo?: string }> }) {
  const sp = await searchParams;
  const [live, v] = await Promise.all([getLiveNow(), getViewer()]);
  const items = live.map((l) => ({ ...l, startedAt: l.startedAt.toISOString() }));
  if (sp.demo === "1") {
    items.unshift({ id: -1, memberId: null, memberName: "DEMO", slug: undefined, platform: "showroom", title: "DEMO stream — bukan siaran nyata (uji player)", startedAt: new Date(Date.now() - 5 * 60_000).toISOString(), viewers: null, imageUrl: null, streamUrl: "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8", roomKey: null });
  }
  return (
    <>
      <PageHead title="Live Member" sub="Pantau member JKT48 yang sedang siaran langsung — data Showroom real-time" right={<><span className="chip on"><span className="live-dot" /> {live.length} live sekarang</span>{sp.demo === "1" ? <Link href="/live" className="chip">Keluar demo</Link> : <Link href="/live?demo=1" className="chip" title="Uji player dengan stream contoh">Uji player (demo)</Link>}</>} />
      <LivePanel initial={items} watchId={sp.watch ? Number(sp.watch) : undefined} defaultLayout={v.user?.multiLiveLayout ?? "row-2"} />
      <div className="card w mt-3.5">
        <div className="w-head"><h3>Riwayat Live 3 Hari</h3><Link href="/live/recent">Semua ›</Link></div>
        <LiveHistoryTable limit={8} />
      </div>
      <Disclaimer />
    </>
  );
}
