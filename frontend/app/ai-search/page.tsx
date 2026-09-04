import { Disclaimer, PageHead } from "@/components/ui";
import AISearch from "@/components/AISearch";
import { getViewer } from "@/lib/auth";
import { llmConfigured } from "@/lib/ai";
export const dynamic = "force-dynamic";
export default async function AISearchPage() {
  const v = await getViewer();
  return (<><PageHead title="AI Search" sub="Pencarian cerdas dua mode · Guest 3/hari · Member 20/hari" /><AISearch guest={!v.userId} llmReady={llmConfigured()} /><Disclaimer /></>);
}
