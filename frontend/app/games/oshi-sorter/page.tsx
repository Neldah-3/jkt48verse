import Link from "next/link";
import { PageHead } from "@/components/ui";
import { OshiSorter } from "@/components/GameBits";
import { listMembers } from "@/lib/data";
import { getViewer } from "@/lib/auth";
export const dynamic = "force-dynamic";
export default async function SorterPage() {
  const [v, ms] = await Promise.all([getViewer(), listMembers({ status: "active", sort: "generation" })]);
  return (<><PageHead title="Oshi Sorter" sub="Urutkan member aktif sesuai hatimu" right={<Link href="/games" className="btn ghost sm">‹ Games</Link>} /><OshiSorter guest={!v.userId} members={ms.map((m) => ({ id: m.id, name: m.name, nickname: m.nickname, generation: m.generation }))} /></>);
}
