import "server-only";
import { and, desc, eq, gte, isNull } from "drizzle-orm";
import { db } from "@/db";
import { liveSessions, members } from "@/db/schema";

export type LiveNow = {
  id: number;
  memberId: number | null;
  memberName: string;
  slug?: string;
  platform: string;
  title: string;
  startedAt: Date;
  viewers: number | null;
  imageUrl: string | null;
  streamUrl: string | null;
  roomKey: string | null;
};

type ShowroomRoom = {
  room_id: number;
  room_url_key?: string;
  main_name?: string;
  image?: string;
  view_num?: number;
  started_at?: number;
  telop?: string;
  streaming_url_list?: { url: string; type?: string; is_default?: boolean }[];
};

let lastSync = 0;
const SYNC_INTERVAL = 60_000;

function norm(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9]/g, "");
}

/** Pull live rooms from Showroom public API, match to member table, upsert into live_sessions. */
export async function syncShowroom(force = false) {
  const now = Date.now();
  if (!force && now - lastSync < SYNC_INTERVAL) return;
  lastSync = now;
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 5000);
    const res = await fetch("https://www.showroom-live.com/api/live/onlives", {
      signal: ctrl.signal,
      headers: { "user-agent": "Mozilla/5.0 (JKT48Verse fan project)" },
      cache: "no-store",
    });
    clearTimeout(t);
    if (!res.ok) return;
    const data = (await res.json()) as { onlives?: { lives?: ShowroomRoom[] }[] };
    const rooms: ShowroomRoom[] = [];
    for (const g of data.onlives ?? []) for (const r of g.lives ?? []) rooms.push(r);
    const jkt = rooms.filter((r) => {
      const key = (r.room_url_key ?? "").toUpperCase();
      const name = (r.main_name ?? "").toUpperCase();
      return key.startsWith("JKT48") || name.includes("JKT48");
    });

    const allMembers = await db.select({ id: members.id, name: members.name, nickname: members.nickname, socials: members.socials }).from(members);
    const open = await db.select().from(liveSessions).where(and(eq(liveSessions.platform, "showroom"), isNull(liveSessions.endedAt)));
    const liveKeys = new Set<string>();

    for (const r of jkt) {
      const key = r.room_url_key ?? String(r.room_id);
      liveKeys.add(key);
      const nk = norm(key.replace(/^JKT48_?/i, "")).replace(/officer$|official$/, "");
      const found =
        allMembers.find((m) => (m.socials?.showroom ?? "").toLowerCase().endsWith("/" + key.toLowerCase())) ??
        allMembers.find((m) => nk && norm(m.nickname) === nk) ??
        allMembers.find((m) => nk && norm(m.name).includes(nk) && nk.length > 3);
      const displayName = found?.nickname ?? (r.main_name ?? key).replace(/^JKT48\s*[-–:]?\s*/i, "").trim();
      const stream = r.streaming_url_list?.find((s) => s.is_default)?.url ?? r.streaming_url_list?.[0]?.url ?? null;
      const existing = open.find((o) => o.roomKey === key);
      if (existing) {
        await db.update(liveSessions).set({ viewers: r.view_num ?? existing.viewers, title: r.telop || existing.title, streamUrl: stream ?? existing.streamUrl, imageUrl: r.image ?? existing.imageUrl }).where(eq(liveSessions.id, existing.id));
      } else {
        await db.insert(liveSessions).values({
          memberId: found?.id ?? null,
          memberName: displayName || key,
          platform: "showroom",
          title: r.telop || `Live ${displayName}`,
          roomKey: key,
          streamUrl: stream,
          imageUrl: r.image ?? null,
          viewers: r.view_num ?? null,
          startedAt: r.started_at ? new Date(r.started_at * 1000) : new Date(),
        });
      }
    }
    for (const o of open) {
      if (o.roomKey && !liveKeys.has(o.roomKey)) {
        await db.update(liveSessions).set({ endedAt: new Date() }).where(eq(liveSessions.id, o.id));
      }
    }
  } catch {
    // network unavailable — keep last known state
  }
}

export async function getLiveNow(): Promise<LiveNow[]> {
  await syncShowroom();
  const rows = await db
    .select({
      id: liveSessions.id, memberId: liveSessions.memberId, memberName: liveSessions.memberName,
      slug: members.slug, platform: liveSessions.platform, title: liveSessions.title,
      startedAt: liveSessions.startedAt, viewers: liveSessions.viewers, imageUrl: liveSessions.imageUrl,
      streamUrl: liveSessions.streamUrl, roomKey: liveSessions.roomKey,
    })
    .from(liveSessions)
    .leftJoin(members, eq(members.id, liveSessions.memberId))
    .where(isNull(liveSessions.endedAt))
    .orderBy(desc(liveSessions.startedAt));
  return rows.map((r) => ({ ...r, slug: r.slug ?? undefined, title: r.title ?? `Live ${r.memberName}` }));
}

export async function getLiveHistory(days = 3) {
  const since = new Date(Date.now() - days * 86400_000);
  return db
    .select({
      id: liveSessions.id, memberName: liveSessions.memberName, slug: members.slug, platform: liveSessions.platform,
      title: liveSessions.title, startedAt: liveSessions.startedAt, endedAt: liveSessions.endedAt,
      replayUrl: liveSessions.replayUrl, viewers: liveSessions.viewers, memberId: liveSessions.memberId,
    })
    .from(liveSessions)
    .leftJoin(members, eq(members.id, liveSessions.memberId))
    .where(gte(liveSessions.startedAt, since))
    .orderBy(desc(liveSessions.startedAt))
    .limit(100);
}
