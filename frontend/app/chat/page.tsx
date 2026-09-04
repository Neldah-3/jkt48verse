import { PageHead, Disclaimer } from "@/components/ui";
import ChatRoom from "@/components/ChatRoom";
import { pinnedChat, recentChat } from "@/lib/data";
import { getViewer } from "@/lib/auth";

export const dynamic = "force-dynamic";

export default async function ChatPage() {
  const v = await getViewer();
  const [messages, pinned] = await Promise.all([recentChat(50, v.userId), pinnedChat()]);
  const online = new Set(messages.filter((m) => Date.now() - new Date(m.createdAt).getTime() < 15 * 60_000).map((m) => m.username)).size + (v.role !== "GUEST" ? 1 : 0);
  return (
    <>
      <PageHead title="Public Chat" sub="Kanal #general · ruang ngobrol sesama fans" right={<span className="chip"><span className="inline-block w-2 h-2 rounded-full" style={{ background: "var(--ok)" }} /> {online} aktif</span>} />
      <ChatRoom initial={messages} pinned={pinned.map((p) => ({ id: p.id, username: p.username, body: p.body }))} viewer={{ role: v.role, userId: v.userId, username: v.username, isMuted: v.isMuted, mutedUntil: v.user?.mutedUntil?.toISOString() ?? null }} />
      <Disclaimer />
    </>
  );
}
