import "server-only";
import { and, asc, count, desc, eq, gte, ilike, inArray, isNull, lt, lte, or, sql } from "drizzle-orm";
import { db } from "@/db";
import {
  members, news, schedules, scheduleMembers, chatMessages, chatReactions, gameScores, users,
  encyclopedia, glossary, motivations, notifications, bookmarks, scheduleReminders, birthdayWishes, userOshi,
} from "@/db/schema";
import { seedIfEmpty } from "@/db/seed";
import { wibParts, wibMidnight, wibDateKey } from "@/lib/time";

export async function ready() {
  await seedIfEmpty();
}

// ---------- Members ----------
export async function listMembers(opts: { status?: string; generation?: number; sort?: string } = {}) {
  await ready();
  const conds = [];
  if (opts.status === "active" || !opts.status) conds.push(inArray(members.status, ["regular", "trainee"]));
  else if (opts.status !== "all") conds.push(eq(members.status, opts.status));
  if (opts.generation) conds.push(eq(members.generation, opts.generation));
  const order = opts.sort === "generation" ? [asc(members.generation), asc(members.name)] : opts.sort === "status" ? [asc(members.status), asc(members.name)] : [asc(members.name)];
  return db.select().from(members).where(conds.length ? and(...conds) : undefined).orderBy(...order);
}

export async function getMemberBySlug(slug: string) {
  await ready();
  const [m] = await db.select().from(members).where(eq(members.slug, slug));
  return m ?? null;
}

export async function memberSchedules(memberId: number) {
  return db
    .select({ s: schedules })
    .from(scheduleMembers)
    .innerJoin(schedules, eq(schedules.id, scheduleMembers.scheduleId))
    .where(and(eq(scheduleMembers.memberId, memberId), gte(schedules.startAt, new Date())))
    .orderBy(asc(schedules.startAt))
    .limit(10)
    .then((r) => r.map((x) => x.s));
}

export async function memberNews(name: string) {
  const first = name.split(" ")[0];
  return db.select().from(news).where(or(ilike(news.body, `%${first}%`), ilike(news.title, `%${first}%`))).orderBy(desc(news.publishedAt)).limit(10);
}

// ---------- Schedule ----------
export async function upcomingSchedules(limit = 5, type?: string) {
  await ready();
  const conds = [gte(schedules.endAt, new Date())];
  if (type && type !== "all") conds.push(eq(schedules.type, type));
  return db.select().from(schedules).where(and(...conds)).orderBy(asc(schedules.startAt)).limit(limit);
}

export async function schedulesInRange(from: Date, to: Date, type?: string) {
  await ready();
  const conds = [gte(schedules.startAt, from), lt(schedules.startAt, to)];
  if (type && type !== "all") conds.push(eq(schedules.type, type));
  return db.select().from(schedules).where(and(...conds)).orderBy(asc(schedules.startAt));
}

export async function getSchedule(id: number) {
  await ready();
  const [s] = await db.select().from(schedules).where(eq(schedules.id, id));
  if (!s) return null;
  const lineup = await db
    .select({ m: members })
    .from(scheduleMembers)
    .innerJoin(members, eq(members.id, scheduleMembers.memberId))
    .where(eq(scheduleMembers.scheduleId, id))
    .orderBy(asc(members.name));
  const related = await db.select().from(news).where(ilike(news.title, `%${s.title.split(" ")[0]}%`)).limit(3);
  return { ...s, lineup: lineup.map((x) => x.m), related };
}

// ---------- News ----------
export async function listNews(category?: string, limit = 20) {
  await ready();
  const cond = category && category !== "latest" ? eq(news.category, category) : undefined;
  return db.select().from(news).where(cond).orderBy(desc(news.publishedAt)).limit(limit);
}
export async function highlightedNews() {
  await ready();
  return db.select().from(news).where(eq(news.isHighlighted, true)).orderBy(desc(news.publishedAt)).limit(3);
}
export async function popularNews() {
  return db.select().from(news).orderBy(desc(news.views)).limit(3);
}
export async function getNews(slug: string) {
  await ready();
  const [n] = await db.select().from(news).where(eq(news.slug, slug));
  if (n) await db.update(news).set({ views: n.views + 1 }).where(eq(news.id, n.id));
  return n ?? null;
}

// ---------- Birthday ----------
export async function birthdayToday() {
  await ready();
  const { month, day } = wibParts(new Date());
  return db
    .select()
    .from(members)
    .where(and(eq(members.showBirthday, true), sql`extract(month from ${members.birthDate}) = ${month}`, sql`extract(day from ${members.birthDate}) = ${day}`));
}

export async function birthdayThisWeek() {
  await ready();
  const { year, month, day, weekday } = wibParts(new Date());
  const monday = wibMidnight(year, month, day);
  monday.setUTCDate(monday.getUTCDate() - ((weekday + 6) % 7));
  const days: { key: string; month: number; day: number; date: Date }[] = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(monday);
    d.setUTCDate(d.getUTCDate() + i);
    const p = wibParts(d);
    days.push({ key: wibDateKey(d), month: p.month, day: p.day, date: d });
  }
  const all = await db.select().from(members).where(eq(members.showBirthday, true));
  return days.map((d) => ({
    ...d,
    members: all.filter((m) => m.birthDate && Number(m.birthDate.split("-")[1]) === d.month && Number(m.birthDate.split("-")[2]) === d.day),
  }));
}

export async function birthdaysInMonth(month: number) {
  await ready();
  return db.select().from(members).where(and(eq(members.showBirthday, true), sql`extract(month from ${members.birthDate}) = ${month}`)).orderBy(sql`extract(day from ${members.birthDate})`);
}

export async function wishesFor(memberId: number, year: number) {
  return db.select().from(birthdayWishes).where(and(eq(birthdayWishes.memberId, memberId), eq(birthdayWishes.year, year))).orderBy(desc(birthdayWishes.createdAt)).limit(50);
}

// ---------- Chat ----------
export async function recentChat(limit = 50, viewerId?: number | null) {
  await ready();
  const rows = await db
    .select()
    .from(chatMessages)
    .where(and(eq(chatMessages.isHidden, false), gte(chatMessages.createdAt, new Date(Date.now() - 3 * 86400_000))))
    .orderBy(desc(chatMessages.createdAt))
    .limit(limit);
  const ids = rows.map((r) => r.id);
  const reacts = ids.length ? await db.select().from(chatReactions).where(inArray(chatReactions.messageId, ids)) : [];
  const parentIds = rows.map((r) => r.parentId).filter((x): x is number => !!x);
  const parents = parentIds.length ? await db.select({ id: chatMessages.id, username: chatMessages.username, body: chatMessages.body }).from(chatMessages).where(inArray(chatMessages.id, parentIds)) : [];
  return rows.reverse().map((r) => {
    const rs = reacts.filter((x) => x.messageId === r.id);
    const grouped: Record<string, number> = {};
    for (const x of rs) grouped[x.emoji] = (grouped[x.emoji] ?? 0) + 1;
    return {
      ...r,
      createdAt: r.createdAt.toISOString(),
      reactions: Object.entries(grouped).map(([emoji, n]) => ({ emoji, n, mine: rs.some((x) => x.emoji === emoji && x.userId === viewerId) })),
      parent: r.parentId ? parents.find((p) => p.id === r.parentId) ?? null : null,
    };
  });
}
export type ChatRow = Awaited<ReturnType<typeof recentChat>>[number];

export async function pinnedChat() {
  return db.select().from(chatMessages).where(and(eq(chatMessages.isPinned, true), eq(chatMessages.isHidden, false))).orderBy(desc(chatMessages.createdAt)).limit(3);
}

// ---------- Games ----------
export async function dailyLeaderboard(game?: string, limit = 10) {
  await ready();
  const { year, month, day } = wibParts(new Date());
  const start = wibMidnight(year, month, day);
  const conds = [gte(gameScores.createdAt, start)];
  if (game) conds.push(eq(gameScores.game, game));
  return db
    .select({ userId: gameScores.userId, username: users.username, avatarSeed: users.avatarSeed, streak: users.streak, total: sql<number>`sum(${gameScores.score})::int` })
    .from(gameScores)
    .innerJoin(users, eq(users.id, gameScores.userId))
    .where(and(...conds))
    .groupBy(gameScores.userId, users.username, users.avatarSeed, users.streak)
    .orderBy(desc(sql`sum(${gameScores.score})`))
    .limit(limit);
}

export async function allTimeLeaderboard(game: string, limit = 20) {
  return db
    .select({ userId: gameScores.userId, username: users.username, avatarSeed: users.avatarSeed, streak: users.streak, total: sql<number>`sum(${gameScores.score})::int`, plays: count() })
    .from(gameScores)
    .innerJoin(users, eq(users.id, gameScores.userId))
    .where(eq(gameScores.game, game))
    .groupBy(gameScores.userId, users.username, users.avatarSeed, users.streak)
    .orderBy(desc(sql`sum(${gameScores.score})`))
    .limit(limit);
}

export async function playerCount(game: string) {
  const [r] = await db.select({ n: sql<number>`count(distinct ${gameScores.userId})::int` }).from(gameScores).where(eq(gameScores.game, game));
  return r?.n ?? 0;
}

// ---------- Misc ----------
export async function getEncyclopedia(slug: string) {
  await ready();
  const [e] = await db.select().from(encyclopedia).where(eq(encyclopedia.slug, slug));
  return e ?? null;
}
export async function listEncyclopedia() {
  await ready();
  return db.select().from(encyclopedia).orderBy(asc(encyclopedia.sortOrder));
}
export async function listGlossary() {
  return db.select().from(glossary).orderBy(asc(glossary.term));
}
export async function dailyMotivation() {
  await ready();
  const today = wibDateKey();
  const [f] = await db.select().from(motivations).where(and(eq(motivations.isPublished, true), eq(motivations.featuredOn, today)));
  if (f) return f;
  const [l] = await db.select().from(motivations).where(eq(motivations.isPublished, true)).orderBy(desc(motivations.createdAt)).limit(1);
  return l ?? null;
}
export async function listMotivations() {
  return db.select().from(motivations).where(eq(motivations.isPublished, true)).orderBy(desc(motivations.createdAt));
}

export async function unreadCount(userId: number | null) {
  if (!userId) return 0;
  const [r] = await db.select({ n: count() }).from(notifications).where(and(eq(notifications.userId, userId), eq(notifications.isRead, false)));
  return r?.n ?? 0;
}
export async function listNotifications(userId: number, limit = 50) {
  return db.select().from(notifications).where(eq(notifications.userId, userId)).orderBy(desc(notifications.createdAt)).limit(limit);
}

export async function isBookmarked(userId: number | null, type: string, id: number) {
  if (!userId) return false;
  const [b] = await db.select().from(bookmarks).where(and(eq(bookmarks.userId, userId), eq(bookmarks.entityType, type), eq(bookmarks.entityId, id)));
  return !!b;
}
export async function reminderSet(userId: number | null) {
  if (!userId) return new Set<number>();
  const rows = await db.select().from(scheduleReminders).where(eq(scheduleReminders.userId, userId));
  return new Set(rows.map((r) => r.scheduleId));
}
export async function userOshiList(userId: number) {
  return db
    .select({ m: members, rank: userOshi.rank })
    .from(userOshi)
    .innerJoin(members, eq(members.id, userOshi.memberId))
    .where(eq(userOshi.userId, userId))
    .orderBy(asc(userOshi.rank));
}

export async function counts() {
  await ready();
  const [u] = await db.select({ n: count() }).from(users);
  const [c] = await db.select({ n: count() }).from(chatMessages).where(gte(chatMessages.createdAt, new Date(Date.now() - 86400_000)));
  return { users: u?.n ?? 0, chat24h: c?.n ?? 0 };
}

// ---------- Global search ----------
export async function globalSearch(q: string) {
  await ready();
  const term = `%${q.slice(0, 80)}%`;
  const [ms, ns, ss, es, gs, mo] = await Promise.all([
    db.select().from(members).where(or(ilike(members.name, term), ilike(members.nickname, term), ilike(members.jikoshoukai, term))).limit(6),
    db.select().from(news).where(or(ilike(news.title, term), ilike(news.summary, term), ilike(news.body, term))).orderBy(desc(news.publishedAt)).limit(5),
    db.select().from(schedules).where(or(ilike(schedules.title, term), ilike(schedules.location, term))).orderBy(asc(schedules.startAt)).limit(5),
    db.select().from(encyclopedia).where(or(ilike(encyclopedia.title, term), ilike(encyclopedia.content, term))).limit(4),
    db.select().from(glossary).where(or(ilike(glossary.term, term), ilike(glossary.meaning, term))).limit(4),
    db.select().from(motivations).where(ilike(motivations.quote, term)).limit(3),
  ]);
  return { members: ms, news: ns, schedules: ss, encyclopedia: es, glossary: gs, motivations: mo };
}

export { isNull, lte };
