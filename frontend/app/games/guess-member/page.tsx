import Link from "next/link";
import { Disclaimer, PageHead } from "@/components/ui";
import { GuessGame } from "@/components/GameBits";
import { getViewer } from "@/lib/auth";
import { playerCount } from "@/lib/data";

export const dynamic = "force-dynamic";

export default async function GuessMemberPage() {
  const [v, players] = await Promise.all([getViewer(), playerCount("guess")]);
  return (
    <>
      <PageHead
        title="Guess Member"
        sub={`Tebak member dari jikoshoukai · ${players} pemain tercatat`}
        right={<Link href="/games" className="btn ghost sm">‹ Games</Link>}
      />
      <div className="grid12">
        <div className="c8">
          <GuessGame guest={!v.userId} />
        </div>
        <div className="c4 card w self-start">
          <h3 className="text-[13.5px] font-bold">Aturan</h3>
          <ul className="muted text-[12px] flex flex-col gap-1.5 list-disc pl-4">
            <li>5 soal per sesi; nama & nickname disensor dari jikoshoukai.</li>
            <li>100 poin awal per soal, −20 per hint (maks 3 hint).</li>
            <li>Bonus kecepatan: max(0, 20 − detik).</li>
          </ul>
        </div>
      </div>
      <Disclaimer />
    </>
  );
}
