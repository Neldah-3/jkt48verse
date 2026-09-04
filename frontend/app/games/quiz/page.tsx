import Link from "next/link";
import { PageHead } from "@/components/ui";
import { QuizGame } from "@/components/GameBits";
import { getViewer } from "@/lib/auth";
export const dynamic = "force-dynamic";
export default async function QuizPage() {
  const v = await getViewer();
  return (<><PageHead title="Quiz" sub="Trivia sejarah, member, theater & umum" right={<><Link href="/games" className="btn ghost sm">‹ Games</Link><Link href="/games/leaderboard?g=quiz" className="btn ghost sm">Leaderboard</Link></>} /><div className="max-w-[760px]"><QuizGame guest={!v.userId} /></div></>);
}
