import Link from "next/link";
import { Empty } from "@/components/ui";
import { getLiveHistory } from "@/lib/live";
import { fmtDateTime, fmtDuration, wibDateKey } from "@/lib/time";

export async function LiveHistoryTable({ limit, member, platform, date }: { limit?: number; member?: string; platform?: string; date?: string }) {
  let rows = await getLiveHistory(3);
  if (member) rows = rows.filter((r) => r.memberName.toLowerCase().includes(member.toLowerCase()));
  if (platform) rows = rows.filter((r) => r.platform === platform);
  if (date) rows = rows.filter((r) => wibDateKey(r.startedAt) === date);
  if (limit) rows = rows.slice(0, limit);
  if (!rows.length) return <Empty icon="clock" title="Belum ada riwayat" hint="Riwayat siaran 3 hari terakhir akan tampil di sini." />;
  return (
    <div className="overflow-x-auto">
      <table className="tb min-w-[560px]">
        <thead><tr><th>Member</th><th>Platform</th><th>Judul</th><th>Durasi</th><th>Waktu (WIB)</th><th>Replay</th></tr></thead>
        <tbody>
          {rows.map((r) => {
            const end = r.endedAt ?? new Date();
            const dur = (end.getTime() - r.startedAt.getTime()) / 1000;
            return (
              <tr key={r.id}>
                <td className="font-semibold">{r.slug ? <Link href={`/member/${r.slug}`} className="hover:underline">{r.memberName}</Link> : r.memberName}</td>
                <td><span className={`tag ${r.platform === "idn" ? "t-info" : "t-red"}`}>{r.platform}</span></td>
                <td className="muted max-w-[200px] truncate">{r.title ?? "—"}</td>
                <td className="tabular">{fmtDuration(dur)}{!r.endedAt && <span className="tag t-red ml-1">Live</span>}</td>
                <td className="muted whitespace-nowrap">{fmtDateTime(r.startedAt)}</td>
                <td>{r.replayUrl ? <a href={r.replayUrl} target="_blank" rel="noreferrer" className="link">Replay ↗</a> : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

