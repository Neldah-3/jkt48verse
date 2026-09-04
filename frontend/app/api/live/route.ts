import { getLiveNow } from "@/lib/live";

export const dynamic = "force-dynamic";

export async function GET() {
  const live = await getLiveNow();
  return Response.json({ live });
}
