import Link from "next/link";
import { Disclaimer, PageHead } from "@/components/ui";
import { OshiSorter, type SorterMember } from "@/components/GameBits";
import { getViewer } from "@/lib/auth";
import { listMembers } from "@/lib/data";

export const dynamic = "force-dynamic";

export default async function OshiSorterPage() {
  const [v, members] = await Promise.all([getViewer(), listMembers({ status: "active" })]);
  const sorterMembers: SorterMember[] = members.map((m) => ({
    id: m.id,
    name: m.name,
    nickname: m.nickname,
    generation: m.generation,
  }));
  return (
    <>
      <PageHead
        title="Oshi Sorter"
        sub="Susun peringkat oshi-mu — posisi 1 adalah kami-oshi"
        right={<Link href="/games" className="btn ghost sm">‹ Games</Link>}
      />
      {sorterMembers.length === 0 ? (
        <div className="card w">
          <p className="muted text-[13px]">Data member belum tersedia. Jalankan seeder atau tunggu sync scraper.</p>
        </div>
      ) : (
        <OshiSorter members={sorterMembers} guest={!v.userId} />
      )}
      <Disclaimer />
    </>
  );
}
