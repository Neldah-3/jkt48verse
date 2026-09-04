import { getViewer } from "@/lib/auth";
import { pinnedChat, recentChat } from "@/lib/data";

export const dynamic = "force-dynamic";

export async function GET() {
  const v = await getViewer();
  const [messages, pinned] = await Promise.all([recentChat(50, v.userId), pinnedChat()]);
  return Response.json({ messages, pinned: pinned.map((p) => ({ id: p.id, username: p.username, body: p.body })) });
}
