import "server-only";

import { apiGet } from "@/lib/api";

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

export type LiveHistoryRow = LiveNow & { endedAt: Date | null; replayUrl: string | null };

type ApiLive = Omit<LiveNow, "startedAt"> & { startedAt: string; slug?: string | null };

export async function getLiveNow(): Promise<LiveNow[]> {
  const rows = await apiGet<ApiLive[]>("/live/now", []);
  return rows.map((r) => ({ ...r, slug: r.slug ?? undefined, startedAt: new Date(r.startedAt) }));
}

export async function getLiveHistory(days = 3): Promise<LiveHistoryRow[]> {
  const rows = await apiGet<(ApiLive & { endedAt: string | null; replayUrl: string | null })[]>(
    `/live/history?days=${days}`,
    [],
  );
  return rows.map((r) => ({
    ...r,
    slug: r.slug ?? undefined,
    startedAt: new Date(r.startedAt),
    endedAt: r.endedAt ? new Date(r.endedAt) : null,
  }));
}
