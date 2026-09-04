import Link from "next/link";
import { PageHead } from "@/components/ui";
import { GuessGame } from "@/components/GameBits";
import { getViewer } from "@/lib/auth";
export const dynamic = "force-dynamic";
export default async function GuessPage() {
  const v = await getViewer();
  return (<><PageHead title="Guess Member" sub="Tebak member dari jikoshoukai-nya" right={<><Link href="/games" className="btn ghost sm">‹ Games</Link><Link href="/games/leaderboard?g=guess" className="btn ghost sm">Leaderboard</Link></>} /><div className="max-w-[760px]"><GuessGame guest={!v.userId} /></div></>);
}
