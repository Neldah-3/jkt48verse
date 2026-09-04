import Link from "next/link";
import { Avatar, Disclaimer, GenChips, PageHead, Tag } from "@/components/ui";
import { listMembers } from "@/lib/data";

export const dynamic = "force-dynamic";

export default async function MemberPage({ searchParams }: { searchParams: Promise<{ status?: string; gen?: string; sort?: string }> }) {
  const sp = await searchParams;
  const gen = sp.gen ? Number(sp.gen) : undefined;
  const status = sp.status ?? "active";
  const rows = await listMembers({ status, generation: gen, sort: sp.sort });
  const q = (o: Record<string, string | undefined>) => { const p = new URLSearchParams(); Object.entries({ ...sp, ...o }).forEach(([k, v]) => v && p.set(k, v)); const s = p.toString(); return `/member${s ? `?${s}` : ""}`; };
  return (
    <>
      <PageHead title="Member" sub={`${rows.length} member · katalog default hanya member aktif`} right={
        <div className="flex flex-wrap gap-2">
          <Link href={q({ status: undefined })} className={`chip ${status === "active" ? "on" : ""}`}>Semua Aktif</Link>
          <Link href={q({ status: "regular" })} className={`chip ${status === "regular" ? "on" : ""}`}>Regular</Link>
          <Link href={q({ status: "trainee" })} className={`chip ${status === "trainee" ? "on" : ""}`}>Trainee</Link>
          <Link href={q({ status: "graduated" })} className={`chip ${status === "graduated" ? "on" : ""}`}>Lulusan</Link>
        </div>
      } />
      <div className="flex flex-wrap gap-2 mb-3 items-center">
        <Link href={q({ gen: undefined })} className={`chip ${!gen ? "on" : ""}`}>Semua Gen</Link>
        <GenChips current={gen} base={q({ gen: undefined }).includes("?") ? q({ gen: undefined }) + "&" : "/member?"} />
        <span className="flex-1" />
        <span className="muted text-[11.5px]">Urut:</span>
        <Link href={q({ sort: undefined })} className={`chip ${!sp.sort ? "on" : ""}`}>A–Z</Link>
        <Link href={q({ sort: "generation" })} className={`chip ${sp.sort === "generation" ? "on" : ""}`}>Generasi</Link>
        <Link href={q({ sort: "status" })} className={`chip ${sp.sort === "status" ? "on" : ""}`}>Status</Link>
      </div>
      <div className="member-grid">
        {rows.map((m) => (
          <Link key={m.id} href={`/member/${m.slug}`} className="card member-card">
            <span className="relative">
              <Avatar name={m.name} size={62} />
              <span className="absolute right-0.5 bottom-0.5 w-3 h-3 rounded-full border-2 border-surface" style={{ background: m.status === "trainee" ? "var(--info)" : m.status === "regular" ? "var(--ok)" : "var(--muted)" }} />
            </span>
            <div className="font-bold text-[13.5px] leading-tight mt-1">{m.name}</div>
            <div className="muted text-[11.5px]">@{m.nickname} · Gen {m.generation ?? "-"}</div>
            <div className="flex gap-1 flex-wrap justify-center"><Tag kind="status" value={m.status} />{m.team && <span className="tag t-gray">{m.team}</span>}</div>
          </Link>
        ))}
      </div>
      {rows.length === 0 && <div className="card"><p className="empty"><b>Tidak ada member untuk filter ini.</b></p></div>}
      <Disclaimer />
    </>
  );
}
