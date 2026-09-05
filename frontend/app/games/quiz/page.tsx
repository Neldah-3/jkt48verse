import Link from "next/link";
import { Disclaimer, PageHead } from "@/components/ui";
import { QuizGame } from "@/components/GameBits";
import { getViewer } from "@/lib/auth";
import { playerCount } from "@/lib/data";

export const dynamic = "force-dynamic";

export default async function QuizPage() {
  const [v, players] = await Promise.all([getViewer(), playerCount("quiz")]);
  return (
    <>
      <PageHead
        title="Quiz JKT48"
        sub={`Jawab cepat, poin besar · ${players} pemain tercatat`}
        right={<Link href="/games" className="btn ghost sm">‹ Games</Link>}
      />
      <div className="grid12">
        <div className="c8">
          <QuizGame guest={!v.userId} />
        </div>
        <div className="c4 card w self-start">
          <h3 className="text-[13.5px] font-bold">Aturan</h3>
          <ul className="muted text-[12px] flex flex-col gap-1.5 list-disc pl-4">
            <li>Easy 10 soal (30 poin/soal), Medium 20 soal (60), Hard 30 soal (90).</li>
            <li>Bonus kecepatan: max(0, 10 − ⌊detik/3⌋) per jawaban benar.</li>
            <li>Jawaban dinilai server; soal diacak setiap sesi.</li>
          </ul>
        </div>
      </div>
      <Disclaimer />
    </>
  );
}
