import { globalSearch } from "@/lib/data";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const q = new URL(req.url).searchParams.get("q")?.trim() ?? "";
  if (q.length < 2) return Response.json({ members: [], news: [], schedules: [], encyclopedia: [], glossary: [], motivations: [] });
  const r = await globalSearch(q.slice(0, 80));
  return Response.json({
    members: r.members.map((m) => ({ slug: m.slug, name: m.name, nickname: m.nickname, generation: m.generation })),
    news: r.news.map((n) => ({ slug: n.slug, title: n.title })),
    schedules: r.schedules.map((s) => ({ id: s.id, title: s.title })),
    encyclopedia: r.encyclopedia.map((e) => ({ slug: e.slug, title: e.title })),
    glossary: r.glossary.map((g) => ({ term: g.term, meaning: g.meaning })),
    motivations: r.motivations.map((m) => ({ id: m.id, quote: m.quote })),
  });
}
