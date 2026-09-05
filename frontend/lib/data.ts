import "server-only";

import { apiGet } from "@/lib/api";

/**
 * Lapisan data JKT48Verse — semua fungsi memanggil API FastAPI.
 * Tanda tangan fungsi dipertahankan sama dengan implementasi Drizzle lama
 * agar seluruh halaman tidak perlu berubah.
 */

// ---------- Tipe (bentuk baris identik dengan schema lama) ----------
export type Member = {
  id: number;
  slug: string;
  name: string;
  nickname: string;
  generation: number | null;
  status: string;
  team: string | null;
  birthDate: string | null;
  height: string | null;
  bloodType: string | null;
  horoscope: string | null;
  jikoshoukai: string | null;
  hobbies: string | null;
  trivia: string | null;
  socials: Record<string, string>;
  showBirthday: boolean;
  createdAt: Date;
};

export type ScheduleRow = {
  id: number;
  title: string;
  type: string;
  startAt: Date;
  endAt: Date | null;
  location: string | null;
  mapUrl: string | null;
  setlist: string | null;
  ticketStatus: string;
  ticketUrl: string | null;
  description: string | null;
  flag: string | null;
  createdAt: Date;
  memberIds?: number[];
};

export type NewsItem = {
  id: number;
  slug: string;
  title: string;
  summary: string;
  body: string;
  category: string;
  isHighlighted: boolean;
  views: number;
  publishedAt: Date;
};

export type Wish = {
  id: number;
  memberId: number;
  userId: number;
  username: string;
  message: string;
  year: number;
  createdAt: Date;
};

export type ChatRow = {
  id: number;
  userId: number | null;
  username: string;
  role: string;
  avatarSeed: number;
  body: string;
  parentId: number | null;
  isPinned: boolean;
  isHidden: boolean;
  createdAt: string;
  reactions: { emoji: string; n: number; mine: boolean }[];
  parent: { id: number; username: string; body: string } | null;
};

export type EncyclopediaRow = {
  id: number;
  slug: string;
  title: string;
  content: string;
  sortOrder: number;
  updatedAt: Date;
};

export type MotivationRow = {
  id: number;
  quote: string;
  author: string | null;
  template: string;
  isPublished: boolean;
  featuredOn: string | null;
  createdAt: Date;
};

type ApiMember = Omit<Member, "createdAt"> & { createdAt: string | null };
type ApiSchedule = Omit<ScheduleRow, "startAt" | "endAt" | "createdAt"> & { startAt: string; endAt: string | null; createdAt: string | null };
type ApiNews = Omit<NewsItem, "publishedAt"> & { publishedAt: string };
type ApiWish = Omit<Wish, "createdAt"> & { createdAt: string };
type ApiEncyclopedia = Omit<EncyclopediaRow, "updatedAt"> & { updatedAt: string | null };
type ApiMotivation = Omit<MotivationRow, "createdAt"> & { createdAt: string };

const D = (v: string | null | undefined) => (v ? new Date(v) : new Date());

const toMember = (m: ApiMember): Member => ({ ...m, createdAt: D(m.createdAt) });
const toSchedule = (s: ApiSchedule): ScheduleRow => ({ ...s, startAt: D(s.startAt), endAt: s.endAt ? new Date(s.endAt) : null, createdAt: D(s.createdAt) });
const toNews = (n: ApiNews): NewsItem => ({ ...n, publishedAt: new Date(n.publishedAt) });
const toWish = (w: ApiWish): Wish => ({ ...w, createdAt: new Date(w.createdAt) });
const toEnc = (e: ApiEncyclopedia): EncyclopediaRow => ({ ...e, updatedAt: D(e.updatedAt) });
const toMot = (m: ApiMotivation): MotivationRow => ({ ...m, createdAt: new Date(m.createdAt) });

// ---------- Members ----------
export async function listMembers(opts: { status?: string; generation?: number; sort?: string } = {}): Promise<Member[]> {
  const p = new URLSearchParams();
  if (opts.status) p.set("status", opts.status);
  if (opts.generation) p.set("generation", String(opts.generation));
  if (opts.sort) p.set("sort", opts.sort);
  const q = p.toString();
  const rows = await apiGet<ApiMember[]>(`/members${q ? `?${q}` : ""}`, []);
  return rows.map(toMember);
}

export async function getMemberBySlug(slug: string): Promise<Member | null> {
  const m = await apiGet<ApiMember | null>(`/members/slug/${encodeURIComponent(slug)}`, null);
  return m ? toMember(m) : null;
}

export async function memberSchedules(memberId: number): Promise<ScheduleRow[]> {
  const rows = await apiGet<ApiSchedule[]>(`/members/id/${memberId}/schedules`, []);
  return rows.map(toSchedule);
}

export async function memberNews(name: string): Promise<NewsItem[]> {
  const rows = await apiGet<ApiNews[]>(`/news?q=${encodeURIComponent(name)}&limit=10`, []);
  return rows.map(toNews);
}

// ---------- Schedule ----------
export async function upcomingSchedules(limit = 5, type?: string): Promise<ScheduleRow[]> {
  const p = new URLSearchParams({ limit: String(limit) });
  if (type) p.set("type", type);
  const rows = await apiGet<ApiSchedule[]>(`/schedules/upcoming?${p}`, []);
  return rows.map(toSchedule);
}

export async function schedulesInRange(from: Date, to: Date, type?: string): Promise<ScheduleRow[]> {
  const p = new URLSearchParams({ start: from.toISOString(), end: to.toISOString() });
  if (type) p.set("type", type);
  const rows = await apiGet<ApiSchedule[]>(`/schedules/range?${p}`, []);
  return rows.map(toSchedule);
}

export async function getSchedule(id: number): Promise<(ScheduleRow & { lineup: Member[]; related: NewsItem[] }) | null> {
  const s = await apiGet<(ApiSchedule & { lineup: ApiMember[]; related: ApiNews[] }) | null>(`/schedules/${id}`, null);
  if (!s) return null;
  return { ...toSchedule(s), lineup: (s.lineup ?? []).map(toMember), related: (s.related ?? []).map(toNews) };
}

// ---------- News ----------
export async function listNews(category?: string, limit = 20): Promise<NewsItem[]> {
  const p = new URLSearchParams({ limit: String(limit) });
  if (category && category !== "latest") p.set("category", category);
  const rows = await apiGet<ApiNews[]>(`/news?${p}`, []);
  return rows.map(toNews);
}

export async function highlightedNews(): Promise<NewsItem[]> {
  const rows = await apiGet<ApiNews[]>("/news/highlighted", []);
  return rows.map(toNews);
}

export async function popularNews(): Promise<NewsItem[]> {
  const rows = await apiGet<ApiNews[]>("/news/popular", []);
  return rows.map(toNews);
}

export async function getNews(slug: string): Promise<NewsItem | null> {
  const n = await apiGet<ApiNews | null>(`/news/slug/${encodeURIComponent(slug)}`, null);
  return n ? toNews(n) : null;
}

// ---------- Birthday ----------
export async function birthdayToday(): Promise<Member[]> {
  const rows = await apiGet<ApiMember[]>("/birthday/today", []);
  return rows.map(toMember);
}

export async function birthdayThisWeek(): Promise<{ key: string; month: number; day: number; date: Date; members: Member[] }[]> {
  const days = await apiGet<{ key: string; month: number; day: number; date: string; members: ApiMember[] }[]>("/birthday/week", []);
  return days.map((d) => ({ ...d, date: new Date(d.date), members: d.members.map(toMember) }));
}

export async function birthdaysInMonth(month: number): Promise<Member[]> {
  const rows = await apiGet<ApiMember[]>(`/birthday/month/${month}`, []);
  return rows.map(toMember);
}

export async function wishesFor(memberId: number, year: number): Promise<Wish[]> {
  const rows = await apiGet<ApiWish[]>(`/birthday/${memberId}/wishes?year=${year}`, []);
  return rows.map(toWish);
}

// ---------- Chat ----------
export async function recentChat(limit = 50, viewerId?: number | null): Promise<ChatRow[]> {
  void viewerId;
  return apiGet<ChatRow[]>(`/chat?limit=${limit}`, []);
}

export async function pinnedChat(): Promise<{ id: number; username: string; body: string; createdAt: string }[]> {
  return apiGet("/chat/pinned", []);
}

// ---------- Games ----------
export async function dailyLeaderboard(game?: string, limit = 10) {
  const p = new URLSearchParams({ limit: String(limit) });
  if (game) p.set("game", game);
  return apiGet<{ userId: number; username: string; avatarSeed: number; streak: number; total: number }[]>(`/games/leaderboard/daily?${p}`, []);
}

export async function allTimeLeaderboard(game: string, limit = 20) {
  return apiGet<{ userId: number; username: string; avatarSeed: number; streak: number; total: number; plays: number }[]>(
    `/games/leaderboard/all-time?game=${encodeURIComponent(game)}&limit=${limit}`,
    [],
  );
}

export async function playerCount(game: string) {
  const r = await apiGet<{ n: number }>(`/games/${encodeURIComponent(game)}/players`, { n: 0 });
  return r?.n ?? 0;
}

// ---------- Encyclopedia / Glossary / Motivation ----------
export async function getEncyclopedia(slug: string): Promise<EncyclopediaRow | null> {
  const e = await apiGet<ApiEncyclopedia | null>(`/encyclopedia/${encodeURIComponent(slug)}`, null);
  return e ? toEnc(e) : null;
}

export async function listEncyclopedia(): Promise<EncyclopediaRow[]> {
  const rows = await apiGet<ApiEncyclopedia[]>("/encyclopedia", []);
  return rows.map(toEnc);
}

export async function listGlossary() {
  return apiGet<{ id: number; term: string; meaning: string }[]>("/glossary", []);
}

export async function dailyMotivation(): Promise<MotivationRow | null> {
  const m = await apiGet<ApiMotivation | null>("/motivation/daily", null);
  return m ? toMot(m) : null;
}

export async function listMotivations(): Promise<MotivationRow[]> {
  const rows = await apiGet<ApiMotivation[]>("/motivation/list", []);
  return rows.map(toMot);
}

// ---------- Notifications / Bookmarks / Reminders ----------
export async function unreadCount(userId: number | null) {
  if (!userId) return 0;
  const r = await apiGet<{ n: number }>("/notifications/unread-count", { n: 0 });
  return r?.n ?? 0;
}

export async function listNotifications(userId: number, limit = 50) {
  void userId;
  const rows = await apiGet<{ id: number; userId: number; type: string; title: string; body: string | null; href: string | null; isRead: boolean; createdAt: string }[]>(
    `/notifications?limit=${limit}`,
    [],
  );
  return rows.map((n) => ({ ...n, createdAt: new Date(n.createdAt) }));
}

export async function isBookmarked(userId: number | null, type: string, id: number) {
  if (!userId) return false;
  const r = await apiGet<{ on: boolean }>(`/bookmarks/check?type=${encodeURIComponent(type)}&id=${id}`, { on: false });
  return !!r.on;
}

export async function reminderSet(userId: number | null): Promise<Set<number>> {
  if (!userId) return new Set<number>();
  const r = await apiGet<{ ids: number[] }>("/schedules/reminders", { ids: [] });
  return new Set(r.ids ?? []);
}

export async function userOshiList(userId: number) {
  void userId;
  const rows = await apiGet<{ m: ApiMember; rank: number }[]>("/account/oshi", []);
  return rows.map((r) => ({ m: toMember(r.m), rank: r.rank }));
}

// ---------- Misc ----------
export async function counts() {
  return apiGet<{ users: number; chat24h: number }>("/stats/counts", { users: 0, chat24h: 0 });
}

export async function listContributors() {
  return apiGet<{ id: number; name: string; role: string; contribution: string }[]>("/contributors", []);
}

export async function accountSummary() {
  return apiGet<{ gameSessions: number; interactions: number; oshi: { m: ApiMember; rank: number }[] }>(
    "/account/summary",
    { gameSessions: 0, interactions: 0, oshi: [] },
  );
}

export async function accountOverview() {
  return apiGet<{
    sessions: { id: string; device: string; ip: string; browser: string; createdAt: string | null; lastUsedAt: string | null }[];
    loginLogs: { id: string; createdAt: string; success: boolean; ip: string; device: string }[];
    activity: { id: number; action: string; detail: string | null; createdAt: string }[];
    bookmarks: { entityType: string; id: number; title: string; href: string }[];
    gameScores: { id: number; game: string; score: number; detail: string | null; createdAt: string }[];
    chat: { id: number; body: string; isHidden: boolean; createdAt: string }[];
    sorter: { id: number; createdAt: string; top3: string[]; count: number }[];
  }>("/account/overview", { sessions: [], loginLogs: [], activity: [], bookmarks: [], gameScores: [], chat: [], sorter: [] });
}

// ---------- Admin ----------
export type AdminUserRow = {
  id: number;
  username: string;
  email: string;
  role: string;
  avatarSeed: number;
  points: number;
  isBlocked: boolean;
  isMuted: boolean;
  createdAt: string;
  blockedUntil: string | null;
  mutedUntil: string | null;
};

export async function adminUsers(limit = 100): Promise<(Omit<AdminUserRow, "createdAt" | "blockedUntil" | "mutedUntil"> & { createdAt: Date; blockedUntil: Date | null; mutedUntil: Date | null })[]> {
  const rows = await apiGet<AdminUserRow[]>(`/admin/users?limit=${limit}`, []);
  return rows.map((u) => ({
    ...u,
    createdAt: new Date(u.createdAt),
    blockedUntil: u.blockedUntil ? new Date(u.blockedUntil) : null,
    mutedUntil: u.mutedUntil ? new Date(u.mutedUntil) : null,
  }));
}

export async function adminStats() {
  return apiGet<{ admins: number; moderators: number; pendingReports: number }>("/admin/stats", { admins: 0, moderators: 0, pendingReports: 0 });
}

export async function moderationReports(status = "pending") {
  return apiGet<
    {
      id: number;
      messageId: number;
      reporterId: number;
      targetUserId: number | null;
      targetUsername: string | null;
      targetRole: string | null;
      targetAvatarSeed: number | null;
      reason: string;
      description: string | null;
      status: string;
      createdAt: string;
      message: { username: string; body: string; isHidden: boolean };
    }[]
  >(`/moderation/reports?status=${status}`, []);
}

export async function moderationLogs(limit = 10) {
  const rows = await apiGet<{ id: number; userId: number | null; kind: string; detail: string | null; createdAt: string }[]>(
    `/admin/moderation-logs?limit=${limit}`,
    [],
  );
  return rows.map((r) => ({ ...r, createdAt: new Date(r.createdAt) }));
}

export async function staffLoginLogs(limit = 10) {
  const rows = await apiGet<{ id: string; userId: string; username: string | null; success: boolean; kind: string; device: string; ip: string; browser: string; createdAt: string }[]>(
    `/admin/login-logs?limit=${limit}`,
    [],
  );
  return rows.map((r) => ({ ...r, createdAt: new Date(r.createdAt) }));
}

// ---------- Global search ----------
export async function globalSearch(q: string) {
  const r = await apiGet<{
    members: ApiMember[];
    news: ApiNews[];
    schedules: ApiSchedule[];
    encyclopedia: ApiEncyclopedia[];
    glossary: { id: number; term: string; meaning: string }[];
    motivations: ApiMotivation[];
  }>(`/search?q=${encodeURIComponent(q.slice(0, 80))}`, { members: [], news: [], schedules: [], encyclopedia: [], glossary: [], motivations: [] });
  return {
    members: r.members.map(toMember),
    news: r.news.map(toNews),
    schedules: r.schedules.map(toSchedule),
    encyclopedia: r.encyclopedia.map(toEnc),
    glossary: r.glossary,
    motivations: r.motivations.map(toMot),
  };
}

/** Kompatibilitas import lama — kini API selalu siap. */
export async function ready() {}

// ---------- Kredensial staff & router API key AI ----------
export type CredentialSlot = {
  role: string;
  slot: number;
  label: string;
  active: boolean;
  defined: boolean;
  username: string;
  email: string;
  missing: string[];
  reason: string;
};

export type CredentialSummary = {
  summary: Record<string, { active: number; slots: number; inactive: number }>;
  slots: CredentialSlot[];
};

export async function credentialSlots(): Promise<CredentialSummary> {
  return apiGet<CredentialSummary>("/admin/credentials", { summary: {}, slots: [] });
}

export type AiKeyStat = {
  label: string;
  key: string;
  ok: number;
  errors: number;
  coolingDown: boolean;
  cooldownSeconds: number;
  lastError: string | null;
  lastUsedAgo: number | null;
};

export type AiKeyRouter = {
  configured: boolean;
  baseUrl: string;
  model: string;
  totalKeys: number;
  ready: number;
  coolingDown: number;
  keys: AiKeyStat[];
};

export async function aiKeyStats(): Promise<AiKeyRouter> {
  return apiGet<AiKeyRouter>("/admin/ai/keys", {
    configured: false,
    baseUrl: "",
    model: "",
    totalKeys: 0,
    ready: 0,
    coolingDown: 0,
    keys: [],
  });
}
