import { apiGet } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET() {
  const r = await apiGet<{ status?: string }>("/health", { status: "down" });
  const ok = r.status === "ok";
  return Response.json({ ok }, { status: ok ? 200 : 500 });
}
