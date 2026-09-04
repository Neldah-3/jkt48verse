"use server";

import { and, count, desc, eq, gte, inArray, sql } from "drizzle-orm";
import { randomBytes } from "node:crypto";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { db } from "@/db";
import {
  users, chatMessages, chatReactions, reports, bookmarks, scheduleReminders, birthdayWishes, userOshi,
  notifications, quizQuestions, guessQuestions, gameSessions, gameScores, members, sorterResults,
  aiSearchHistory, activityLogs, moderationLogs, loginLogs,
} from "@/db/schema";
import { createSession, destroySession, getViewer, hashPassword, verifyPassword, logLogin, clientKey } from "@/lib/auth";
import { verifyStaff } from "@/lib/credentials";
import { checkEmoji, checkText, rateCheck, EMOJI_WHITELIST } from "@/lib/moderation";
import { databaseSearch, llmSearch, type AIAnswer } from "@/lib/ai";
import { wibDateKey, wibParts, wibMidnight } from "@/lib/time";

export type ActionResult<T = undefined> = { ok: true; data?: T } | { ok: false; error: string; code?: string };

const staffAttempts = new Map<string, number[]>();

// ---------------- AUTH ----------------
export async function registerAction(_: unknown, form: FormData): Promise<ActionResult> {
  const username = String(form.get("username") ?? "").trim();
  const password = String(form.get("password") ?? "");
  if (!/^[a-zA-Z0-9]{3,20}$/.test(username)) return { ok: false, error: "Username 3–20 karakter alfanumerik." };
  if (password.length < 8) return { ok: false, error: "Password minimal 8 karakter." };
  if (/^(admin|mod|moderator)/i.test(username)) return { ok: false, error: "Username tidak tersedia." };
  const [exists] = await db.select({ id: users.id }).from(users).where(sql`lower(${users.username}) = ${username.toLowerCase()}`);
  if (exists) return { ok: false, error: "Username sudah dipakai." };
  const [u] = await db.insert(users).values({ username, passwordHash: hashPassword(password), avatarSeed: 1 + Math.floor(Math.random() * 6) }).returning();
  await db.insert(notifications).values({ userId: u.id, type: "SYSTEM", title: "Selamat datang di JKT48Verse!", body: "Atur oshi-mu di halaman Akun agar Live Alert & Birthday Alert aktif.", href: "/account" });
  await createSession({ userId: u.id, role: "MEMBER", remember: true });
  await logLogin({ userId: u.id, username, success: true, kind: "member" });
  redirect("/");
}

export async function loginAction(_: unknown, form: FormData): Promise<ActionResult> {
  const username = String(form.get("username") ?? "").trim();
  const password = String(form.get("password") ?? "");
  const remember = form.get("remember") === "on";
  const [u] = await db.select().from(users).where(sql`lower(${users.username}) = ${username.toLowerCase()}`);
  if (!u || !verifyPassword(password, u.passwordHash)) {
    await logLogin({ username, success: false, kind: "member" });
    return { ok: false, error: "Username atau password salah." };
  }
  if (u.blockedUntil && u.blockedUntil.getTime() > Date.now()) {
    return { ok: false, error: `Akun diblokir hingga ${u.blockedUntil.toLocaleString("id-ID", { timeZone: "Asia/Jakarta" })} WIB. Alasan: ${u.blockReason ?? "-"}` };
  }
  await createSession({ userId: u.id, role: u.role as "MEMBER", remember });
  await logLogin({ userId: u.id, username, success: true, kind: "member" });
  redirect("/");
}

export async function staffLoginAction(_: unknown, form: FormData): Promise<ActionResult> {
  const key = await clientKey();
  const now = Date.now();
  const arr = (staffAttempts.get(key) ?? []).filter((t) => now - t < 15 * 60_000);
  if (arr.length >= 5) return { ok: false, error: "Kredensial tidak valid" };
  const input = {
    username: String(form.get("username") ?? ""),
    id: String(form.get("id") ?? ""),
    password: String(form.get("password") ?? ""),
    code: String(form.get("code") ?? ""),
  };
  const cred = verifyStaff(input);
  if (!cred) {
    arr.push(now);
    staffAttempts.set(key, arr);
    await logLogin({ username: input.username, success: false, kind: "staff" });
    return { ok: false, error: "Kredensial tidak valid" };
  }
  staffAttempts.delete(key);
  await createSession({ staffId: cred.id, staffName: cred.username, role: cred.role });
  await logLogin({ username: cred.username, success: true, kind: "staff" });
  redirect(cred.role === "ADMIN" ? "/admin" : "/moderator");
}

export async function logoutAction(all?: boolean) {
  await destroySession(!!all);
  redirect("/");
}

// ---------------- CHAT ----------------
export async function sendChatAction(body: string, parentId?: number | null): Promise<ActionResult<{ id: number }>> {
  const v = await getViewer();
  if (v.role === "GUEST") return { ok: false, error: "Login untuk mengirim pesan.", code: "AUTH_REQUIRED" };
  if (v.isBlocked) return { ok: false, error: "Akun kamu sedang diblokir.", code: "ACCOUNT_BLOCKED" };
  if (v.isMuted) return { ok: false, error: `Kamu sedang di-mute hingga ${v.user?.mutedUntil?.toLocaleTimeString("id-ID", { timeZone: "Asia/Jakarta" })} WIB.`, code: "MUTED" };
  const text = body.trim();
  if (!text) return { ok: false, error: "Pesan kosong." };
  if (text.length > 500) return { ok: false, error: "Maksimal 500 karakter." };
  const rate = rateCheck(`chat:${v.userId ?? v.staffId}`);
  if (!rate.ok) return { ok: false, error: `Slow-mode aktif. Tunggu ${rate.waitSec} detik.`, code: "SLOW_MODE" };
  const em = checkEmoji(text);
  if (!em.ok) return { ok: false, error: `Emoji ${em.emoji} tidak diizinkan. Gunakan emoji whitelist.`, code: "EMOJI_BLOCKED" };
  const wf = await checkText(text);
  if (wf.blocked) {
    if (v.userId) await db.insert(moderationLogs).values({ userId: v.userId, kind: "MESSAGE_BLOCKED", detail: text.slice(0, 120) });
    return { ok: false, error: "Pesan mengandung kata yang tidak diperbolehkan. Mari jaga ruang chat tetap nyaman.", code: "MESSAGE_BLOCKED" };
  }
  const [m] = await db.insert(chatMessages).values({ userId: v.userId, username: v.username, role: v.role, avatarSeed: v.avatarSeed, body: text, parentId: parentId ?? null }).returning();
  // mentions
  const mentions = [...text.matchAll(/@([a-zA-Z0-9]{3,20})/g)].map((x) => x[1].toLowerCase());
  if (mentions.length) {
    const targets = await db.select().from(users).where(inArray(sql`lower(${users.username})`, mentions));
    for (const t of targets) {
      if (t.id !== v.userId && t.notifPrefs?.CHAT_MENTION !== false) {
        await db.insert(notifications).values({ userId: t.id, type: "CHAT_MENTION", title: `${v.username} menyebut kamu di chat`, body: text.slice(0, 120), href: "/chat" });
      }
    }
  }
  if (v.userId) await db.insert(activityLogs).values({ userId: v.userId, action: "chat", detail: text.slice(0, 80) });
  return { ok: true, data: { id: m.id } };
}

export async function reactChatAction(messageId: number, emoji: string): Promise<ActionResult> {
  const v = await getViewer();
  if (!v.userId) return { ok: false, error: "Login untuk memberi reaksi.", code: "AUTH_REQUIRED" };
  if (!EMOJI_WHITELIST.includes(emoji)) return { ok: false, error: "Emoji tidak diizinkan." };
  const [ex] = await db.select().from(chatReactions).where(and(eq(chatReactions.messageId, messageId), eq(chatReactions.userId, v.userId)));
  if (ex && ex.emoji === emoji) await db.delete(chatReactions).where(eq(chatReactions.id, ex.id));
  else if (ex) await db.update(chatReactions).set({ emoji }).where(eq(chatReactions.id, ex.id));
  else await db.insert(chatReactions).values({ messageId, userId: v.userId, emoji });
  return { ok: true };
}

export async function reportChatAction(messageId: number, reason: string, description?: string): Promise<ActionResult> {
  const v = await getViewer();
  if (!v.userId) return { ok: false, error: "Login untuk melaporkan.", code: "AUTH_REQUIRED" };
  const [m] = await db.select().from(chatMessages).where(eq(chatMessages.id, messageId));
  if (!m) return { ok: false, error: "Pesan tidak ditemukan." };
  await db.insert(reports).values({ messageId, reporterId: v.userId, targetUserId: m.userId, targetUsername: m.username, reason, description: description?.slice(0, 300) });
  const [{ n }] = await db.select({ n: sql<number>`count(distinct ${reports.reporterId})::int` }).from(reports).where(and(eq(reports.messageId, messageId), gte(reports.createdAt, new Date(Date.now() - 10 * 60_000))));
  if (n >= 5) await db.update(chatMessages).set({ isHidden: true }).where(eq(chatMessages.id, messageId));
  return { ok: true };
}

export async function deleteChatAction(messageId: number): Promise<ActionResult> {
  const v = await getViewer();
  const [m] = await db.select().from(chatMessages).where(eq(chatMessages.id, messageId));
  if (!m) return { ok: false, error: "Tidak ditemukan." };
  const own = v.userId && m.userId === v.userId;
  if (!own && v.role !== "ADMIN" && v.role !== "MODERATOR") return { ok: false, error: "Tidak diizinkan." };
  await db.update(chatMessages).set({ isHidden: true }).where(eq(chatMessages.id, messageId));
  return { ok: true };
}

export async function pinChatAction(messageId: number): Promise<ActionResult> {
  const v = await getViewer();
  if (v.role !== "ADMIN") return { ok: false, error: "Hanya ADMIN yang dapat menyematkan." };
  const [m] = await db.select().from(chatMessages).where(eq(chatMessages.id, messageId));
  if (!m) return { ok: false, error: "Tidak ditemukan." };
  if (!m.isPinned) {
    const [{ n }] = await db.select({ n: count() }).from(chatMessages).where(eq(chatMessages.isPinned, true));
    if (n >= 3) return { ok: false, error: "Maksimal 3 pin aktif." };
  }
  await db.update(chatMessages).set({ isPinned: !m.isPinned }).where(eq(chatMessages.id, messageId));
  return { ok: true };
}

// ---------------- BOOKMARK / REMINDER / WISH / OSHI ----------------
export async function toggleBookmarkAction(entityType: string, entityId: number, path: string): Promise<ActionResult<{ on: boolean }>> {
  const v = await getViewer();
  if (!v.userId) redirect(`/auth/login?next=${encodeURIComponent(path)}`);
  const [ex] = await db.select().from(bookmarks).where(and(eq(bookmarks.userId, v.userId), eq(bookmarks.entityType, entityType), eq(bookmarks.entityId, entityId)));
  if (ex) await db.delete(bookmarks).where(eq(bookmarks.id, ex.id));
  else await db.insert(bookmarks).values({ userId: v.userId, entityType, entityId });
  revalidatePath(path);
  return { ok: true, data: { on: !ex } };
}

export async function toggleReminderAction(scheduleId: number, path: string): Promise<ActionResult<{ on: boolean }>> {
  const v = await getViewer();
  if (!v.userId) redirect(`/auth/login?next=${encodeURIComponent(path)}`);
  const [ex] = await db.select().from(scheduleReminders).where(and(eq(scheduleReminders.userId, v.userId), eq(scheduleReminders.scheduleId, scheduleId)));
  if (ex) await db.delete(scheduleReminders).where(eq(scheduleReminders.id, ex.id));
  else {
    await db.insert(scheduleReminders).values({ userId: v.userId, scheduleId });
    await db.insert(notifications).values({ userId: v.userId, type: "SCHEDULE_REMINDER", title: "Pengingat diaktifkan", body: "Kamu akan diingatkan 30 & 5 menit sebelum acara dimulai.", href: `/schedule/${scheduleId}` });
  }
  revalidatePath(path);
  return { ok: true, data: { on: !ex } };
}

export async function sendWishAction(memberId: number, message: string): Promise<ActionResult> {
  const v = await getViewer();
  if (!v.userId) redirect(`/auth/login?next=/birthday`);
  if (v.isBlocked) return { ok: false, error: "Akun kamu sedang diblokir.", code: "ACCOUNT_BLOCKED" };
  const text = message.trim();
  if (!text || text.length > 200) return { ok: false, error: "Ucapan 1–200 karakter." };
  const wf = await checkText(text);
  if (wf.blocked) return { ok: false, error: "Ucapan mengandung kata yang tidak diperbolehkan.", code: "MESSAGE_BLOCKED" };
  const em = checkEmoji(text);
  if (!em.ok) return { ok: false, error: `Emoji ${em.emoji} tidak diizinkan.`, code: "EMOJI_BLOCKED" };
  const year = wibParts(new Date()).year;
  try {
    await db.insert(birthdayWishes).values({ memberId, userId: v.userId, username: v.username, message: text, year });
  } catch {
    return { ok: false, error: "Kamu sudah mengirim ucapan untuk member ini tahun ini." };
  }
  revalidatePath("/birthday");
  return { ok: true };
}

export async function setOshiAction(form: FormData): Promise<ActionResult> {
  const v = await getViewer();
  if (!v.userId) return { ok: false, error: "Login diperlukan." };
  const kami = Number(form.get("kami") || 0);
  const others = form.getAll("oshi").map(Number).filter((n) => n && n !== kami).slice(0, 5);
  await db.delete(userOshi).where(eq(userOshi.userId, v.userId));
  const rows = [] as { userId: number; memberId: number; rank: number }[];
  if (kami) rows.push({ userId: v.userId, memberId: kami, rank: 0 });
  others.forEach((id, i) => rows.push({ userId: v.userId!, memberId: id, rank: i + 1 }));
  if (rows.length) await db.insert(userOshi).values(rows).onConflictDoNothing();
  revalidatePath("/account");
  return { ok: true };
}

export async function updateProfileAction(form: FormData): Promise<ActionResult> {
  const v = await getViewer();
  if (!v.userId) return { ok: false, error: "Login diperlukan." };
  const bio = String(form.get("bio") ?? "").slice(0, 160);
  const avatarSeed = Math.min(6, Math.max(1, Number(form.get("avatarSeed") || 1)));
  await db.update(users).set({ bio, avatarSeed }).where(eq(users.id, v.userId));
  revalidatePath("/account");
  return { ok: true };
}

export async function updateSettingsAction(form: FormData): Promise<ActionResult> {
  const v = await getViewer();
  if (!v.userId) return { ok: false, error: "Login diperlukan." };
  const prefs: Record<string, boolean> = {};
  for (const k of ["LIVE_ALERT", "SCHEDULE_REMINDER", "BIRTHDAY_ALERT", "NEWS_ALERT", "CHAT_MENTION"]) prefs[k] = form.get(k) === "on";
  await db.update(users).set({
    theme: String(form.get("theme") ?? "system"),
    lang: String(form.get("lang") ?? "id"),
    multiLiveLayout: String(form.get("multiLiveLayout") ?? "row-2"),
    isPrivate: form.get("isPrivate") === "on",
    hideOshi: form.get("hideOshi") === "on",
    notifPrefs: prefs,
  }).where(eq(users.id, v.userId));
  revalidatePath("/account/settings");
  return { ok: true };
}

export async function markAllReadAction() {
  const v = await getViewer();
  if (!v.userId) return;
  await db.update(notifications).set({ isRead: true }).where(eq(notifications.userId, v.userId));
  revalidatePath("/notifications");
}

// ---------------- GAMES (server-authoritative scoring) ----------------
const QUIZ_COUNT = { easy: 10, medium: 20, hard: 30 } as const;
const QUIZ_POINTS = { easy: 30, medium: 60, hard: 90 } as const;
type Level = keyof typeof QUIZ_COUNT;

function shuffle<T>(arr: T[]) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export type QuizQuestionView = { id: number; question: string; options: string[]; index: number; total: number; category: string };

export async function startQuizAction(level: Level): Promise<ActionResult<{ sessionId: string; q: QuizQuestionView; level: Level }>> {
  const v = await getViewer();
  const lv: Level = ["easy", "medium", "hard"].includes(level) ? level : "easy";
  const pool = await db.select().from(quizQuestions).where(eq(quizQuestions.active, true));
  if (!pool.length) return { ok: false, error: "Bank soal kosong." };
  const preferred = shuffle(pool.filter((q) => q.level === lv));
  const filler = shuffle(pool.filter((q) => q.level !== lv));
  const chosen = [...preferred, ...filler].slice(0, QUIZ_COUNT[lv]);
  const ids = chosen.map((q) => q.id);
  const id = randomBytes(12).toString("hex");
  await db.insert(gameSessions).values({ id, userId: v.userId, game: "quiz", level: lv, questionIds: ids });
  const q = chosen[0];
  return { ok: true, data: { sessionId: id, level: lv, q: { id: q.id, question: q.question, options: q.options, index: 0, total: ids.length, category: q.category } } };
}

export async function answerQuizAction(sessionId: string, questionId: number, answerIndex: number): Promise<ActionResult<{ correct: boolean; correctIndex: number; gained: number; score: number; next: QuizQuestionView | null; finished: boolean }>> {
  const [s] = await db.select().from(gameSessions).where(eq(gameSessions.id, sessionId));
  if (!s || s.finished) return { ok: false, error: "Sesi tidak valid." };
  const qid = s.questionIds[s.currentIndex];
  if (qid !== questionId) return { ok: false, error: "Urutan soal tidak sesuai." };
  const [q] = await db.select().from(quizQuestions).where(eq(quizQuestions.id, qid));
  const secs = (Date.now() - s.questionShownAt.getTime()) / 1000;
  const correct = q.correctIndex === answerIndex;
  const base = QUIZ_POINTS[(s.level as Level) ?? "easy"];
  const gained = correct ? base + Math.max(0, 10 - Math.floor(secs / 3)) : 0;
  const nextIndex = s.currentIndex + 1;
  const finished = nextIndex >= s.questionIds.length;
  const score = s.score + gained;
  await db.update(gameSessions).set({ score, correct: s.correct + (correct ? 1 : 0), currentIndex: nextIndex, finished, questionShownAt: new Date() }).where(eq(gameSessions.id, sessionId));
  let next: QuizQuestionView | null = null;
  if (!finished) {
    const [nq] = await db.select().from(quizQuestions).where(eq(quizQuestions.id, s.questionIds[nextIndex]));
    next = { id: nq.id, question: nq.question, options: nq.options, index: nextIndex, total: s.questionIds.length, category: nq.category };
  } else if (s.userId) {
    await recordScore(s.userId, "quiz", score, `level ${s.level}`);
  }
  return { ok: true, data: { correct, correctIndex: q.correctIndex, gained, score, next, finished } };
}

async function recordScore(userId: number, game: string, score: number, detail: string) {
  await db.insert(gameScores).values({ userId, game, score, detail });
  const [u] = await db.select().from(users).where(eq(users.id, userId));
  const today = wibDateKey();
  let streak = u.streak;
  let bonus = 0;
  if (u.lastDailyDate !== today) {
    const y = wibDateKey(new Date(Date.now() - 86400_000));
    streak = u.lastDailyDate === y ? u.streak + 1 : 1;
    if (streak === 7) bonus = 50;
    if (streak === 30) bonus = 200;
    if (streak === 100) bonus = 1000;
    if (bonus) {
      await db.insert(gameScores).values({ userId, game: "daily", score: bonus, detail: `streak ${streak}` });
      await db.insert(notifications).values({ userId, type: "GAME_BADGE", title: `Streak ${streak} hari! +${bonus} poin`, href: "/games" });
    }
  }
  await db.update(users).set({ points: u.points + score + bonus, streak, lastDailyDate: today }).where(eq(users.id, userId));
  await db.insert(activityLogs).values({ userId, action: `game:${game}`, detail: `${score} poin (${detail})` });
}

export type GuessView = { sessionId: string; jiko: string; hints: string[]; hintsUsed: number; options: { id: number; name: string }[]; index: number; total: number; score: number };

export async function startGuessAction(): Promise<ActionResult<GuessView>> {
  const v = await getViewer();
  const pool = await db.select({ g: guessQuestions, status: members.status }).from(guessQuestions).innerJoin(members, eq(members.id, guessQuestions.memberId)).where(and(eq(guessQuestions.active, true), inArray(members.status, ["regular", "trainee"])));
  if (pool.length < 4) return { ok: false, error: "Bank soal Guess Member belum cukup." };
  const chosen = shuffle(pool).slice(0, 5).map((p) => p.g.id);
  const id = randomBytes(12).toString("hex");
  await db.insert(gameSessions).values({ id, userId: v.userId, game: "guess", questionIds: chosen });
  return { ok: true, data: await guessView(id) };
}

async function guessView(sessionId: string): Promise<GuessView> {
  const [s] = await db.select().from(gameSessions).where(eq(gameSessions.id, sessionId));
  const [g] = await db.select().from(guessQuestions).where(eq(guessQuestions.id, s.questionIds[s.currentIndex]));
  const [m] = await db.select().from(members).where(eq(members.id, g.memberId));
  const others = shuffle(await db.select({ id: members.id, name: members.name }).from(members).where(and(inArray(members.status, ["regular", "trainee"]), sql`${members.id} <> ${m.id}`))).slice(0, 5);
  const seed = s.questionIds[s.currentIndex] % 6;
  const opts = [...others.slice(0, seed), { id: m.id, name: m.name }, ...others.slice(seed)];
  const jiko = (m.jikoshoukai ?? "").replace(new RegExp(m.nickname, "gi"), "▮▮▮").replace(new RegExp(m.name.split(" ")[0], "gi"), "▮▮▮");
  return { sessionId, jiko, hints: g.hints.slice(0, s.hintsUsed), hintsUsed: s.hintsUsed, options: opts, index: s.currentIndex, total: s.questionIds.length, score: s.score };
}

export async function guessHintAction(sessionId: string): Promise<ActionResult<GuessView>> {
  const [s] = await db.select().from(gameSessions).where(eq(gameSessions.id, sessionId));
  if (!s || s.finished) return { ok: false, error: "Sesi tidak valid." };
  if (s.hintsUsed >= 3) return { ok: false, error: "Maksimal 3 hint." };
  await db.update(gameSessions).set({ hintsUsed: s.hintsUsed + 1 }).where(eq(gameSessions.id, sessionId));
  return { ok: true, data: await guessView(sessionId) };
}

export async function answerGuessAction(sessionId: string, memberId: number): Promise<ActionResult<{ correct: boolean; answer: string; gained: number; score: number; finished: boolean; next: GuessView | null }>> {
  const [s] = await db.select().from(gameSessions).where(eq(gameSessions.id, sessionId));
  if (!s || s.finished) return { ok: false, error: "Sesi tidak valid." };
  const [g] = await db.select().from(guessQuestions).where(eq(guessQuestions.id, s.questionIds[s.currentIndex]));
  const [m] = await db.select().from(members).where(eq(members.id, g.memberId));
  const secs = (Date.now() - s.questionShownAt.getTime()) / 1000;
  const correct = m.id === memberId;
  const gained = correct ? Math.max(0, 100 - 20 * s.hintsUsed) + Math.max(0, 20 - Math.floor(secs)) : 0;
  const nextIndex = s.currentIndex + 1;
  const finished = nextIndex >= s.questionIds.length;
  const score = s.score + gained;
  await db.update(gameSessions).set({ score, correct: s.correct + (correct ? 1 : 0), currentIndex: nextIndex, finished, hintsUsed: 0, questionShownAt: new Date() }).where(eq(gameSessions.id, sessionId));
  if (finished && s.userId) await recordScore(s.userId, "guess", score, "5 soal");
  return { ok: true, data: { correct, answer: m.name, gained, score, finished, next: finished ? null : await guessView(sessionId) } };
}

export async function saveSorterAction(ranking: number[]): Promise<ActionResult> {
  const v = await getViewer();
  if (!v.userId) return { ok: false, error: "Login untuk menyimpan hasil.", code: "AUTH_REQUIRED" };
  await db.insert(sorterResults).values({ userId: v.userId, ranking: ranking.slice(0, 100) });
  await db.insert(activityLogs).values({ userId: v.userId, action: "sorter", detail: `${ranking.length} member` });
  return { ok: true };
}

// ---------------- AI SEARCH ----------------
export async function aiSearchAction(mode: "db" | "llm", question: string): Promise<ActionResult<AIAnswer & { remaining: number }>> {
  const v = await getViewer();
  const q = question.trim().slice(0, 200);
  if (q.length < 3) return { ok: false, error: "Pertanyaan terlalu pendek." };
  const limit = v.userId ? 20 : 3;
  const key = await clientKey();
  const { year, month, day } = wibParts(new Date());
  const since = wibMidnight(year, month, day);
  const [{ n }] = await db.select({ n: count() }).from(aiSearchHistory).where(and(v.userId ? eq(aiSearchHistory.userId, v.userId) : eq(aiSearchHistory.clientKey, key), gte(aiSearchHistory.createdAt, since)));
  if (n >= limit) return { ok: false, error: `Kuota harian habis (${limit}/${limit}). Reset pukul 00:00 WIB.`, code: "RATE_LIMIT" };
  let ans = mode === "llm" ? await llmSearch(q) : await databaseSearch(q);
  if (mode === "db" && ans.confidence < 0.5) {
    const l = await llmSearch(q);
    if (!l.fallback) ans = l;
  }
  await db.insert(aiSearchHistory).values({ userId: v.userId, clientKey: key, mode, query: q, answer: ans.answer.slice(0, 2000) });
  return { ok: true, data: { ...ans, remaining: limit - n - 1 } };
}

export async function aiFeedbackAction(query: string, value: 1 | -1) {
  const v = await getViewer();
  if (!v.userId) return;
  const [row] = await db.select().from(aiSearchHistory).where(and(eq(aiSearchHistory.userId, v.userId), eq(aiSearchHistory.query, query))).orderBy(desc(aiSearchHistory.createdAt)).limit(1);
  if (row) await db.update(aiSearchHistory).set({ feedback: value }).where(eq(aiSearchHistory.id, row.id));
}

// ---------------- ADMIN / MODERATOR ----------------
export async function resolveReportAction(reportId: number, decision: "approved" | "rejected"): Promise<ActionResult> {
  const v = await getViewer();
  if (v.role !== "ADMIN" && v.role !== "MODERATOR") return { ok: false, error: "Tidak diizinkan." };
  const [r] = await db.select().from(reports).where(eq(reports.id, reportId));
  if (!r) return { ok: false, error: "Report tidak ditemukan." };
  await db.update(reports).set({ status: decision }).where(eq(reports.id, reportId));
  if (decision === "approved") await db.update(chatMessages).set({ isHidden: true }).where(eq(chatMessages.id, r.messageId));
  revalidatePath("/admin");
  revalidatePath("/moderator");
  return { ok: true };
}

export async function sanctionUserAction(form: FormData): Promise<ActionResult> {
  const v = await getViewer();
  if (v.role !== "ADMIN" && v.role !== "MODERATOR") return { ok: false, error: "Tidak diizinkan." };
  const userId = Number(form.get("userId"));
  const kind = String(form.get("kind")); // mute | block | unblock
  const duration = String(form.get("duration")); // hours or 'permanent'
  const reason = String(form.get("reason") ?? "").trim();
  if (kind !== "unblock" && reason.length < 3) return { ok: false, error: "Alasan wajib diisi." };
  const [target] = await db.select().from(users).where(eq(users.id, userId));
  if (!target) return { ok: false, error: "User tidak ditemukan." };
  if (v.role === "MODERATOR") {
    if (target.role !== "MEMBER") return { ok: false, error: "Moderator hanya dapat memblokir akun MEMBER." };
    if (duration === "permanent") return { ok: false, error: "Ban permanen memerlukan approval Admin." };
    if (kind === "block" && Number(duration) > 30 * 24) return { ok: false, error: "Moderator maksimal ban 30 hari." };
  }
  const until = duration === "permanent" ? new Date("2099-01-01") : new Date(Date.now() + Number(duration) * 3600_000);
  if (kind === "mute") await db.update(users).set({ mutedUntil: until }).where(eq(users.id, userId));
  else if (kind === "block") await db.update(users).set({ blockedUntil: until, blockReason: reason }).where(eq(users.id, userId));
  else await db.update(users).set({ blockedUntil: null, mutedUntil: null, blockReason: null }).where(eq(users.id, userId));
  if (kind !== "unblock") {
    await db.insert(notifications).values({ userId, type: "SYSTEM", title: kind === "mute" ? "Kamu di-mute dari chat" : "Akun kamu diblokir", body: `Alasan: ${reason}. Berlaku hingga ${duration === "permanent" ? "permanen" : until.toLocaleString("id-ID", { timeZone: "Asia/Jakarta" }) + " WIB"}.` });
  }
  await db.insert(moderationLogs).values({ userId, kind: `${kind}:${duration}`, detail: `${reason} — oleh ${v.username} (${v.role})` });
  revalidatePath("/admin");
  revalidatePath("/moderator");
  return { ok: true };
}

export async function recentLoginLogs(limit = 20) {
  const v = await getViewer();
  if (v.role !== "ADMIN") return [];
  return db.select().from(loginLogs).orderBy(desc(loginLogs.createdAt)).limit(limit);
}
