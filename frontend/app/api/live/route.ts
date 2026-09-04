import { getLiveNow, syncShowroom } from "@/lib/live";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const force = new URL(req.url).searchParams.get("refresh") === "1";
  if (force) await syncShowroom(true);
  const live = await getLiveNow();
  return Response.json({ live });
}
