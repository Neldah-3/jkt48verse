"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { API_BASE, apiCall, apiFetch, applyBackendCookies, clearAuthCookies } from "@/lib/api";
import { clientKey, getViewer, type Viewer } from "@/lib/auth";
import type { AIAnswer } from "@/lib/ai";

export type ActionResult<T = undefined> = { ok: true; data?: T } | { ok: false; error: string; code?: string };

// ---------------- AUTH ----------------
export async function registerAction(_: unknown, form: FormData): Promise<ActionResult> {
  const username = String(form.get("username") ?? "");
  const email = String(form.get("email") ?? "").trim();
  const password = String(form.get("password") ?? "");
  const res = await fetch(`${API_BASE}/users/signup`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ username, email, password }),
    cache: "no-store",
  });
  const body = (await res.json().catch(() => ({}))) as { message?: string; devCode?: string };
  if (!res.ok || (body.message && body.message !== "" && !body.devCode && res.status !== 201)) {
    return { ok: false, error: body.message ?? "Pendaftaran gagal." };
  }
  if (body.message && (body.message.includes("Username") || body.message.includes("Password") || body.message.includes("Email"))) {
    return { ok: false, error: body.message };
  }
  redirect(`/auth/verify?email=${encodeURIComponent(email)}${body.devCode ? `&dev=${body.devCode}` : ""}`);
}

export async function loginAction(_: unknown, form: FormData): Promise<ActionResult> {
  const username = String(form.get("username") ?? "");
  const password = String(form.get("password") ?? "");
  // Code akses opsional di form ini (wajib hanya untuk akun Admin/Moderator).
  const accessCode = String(form.get("accessCode") ?? "");
  const body = new URLSearchParams({ username, password });
  if (accessCode) body.set("access_code", accessCode);
  const res = await apiFetch("/auth/signin", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });
  if (!res.ok) {
    const b = (await res.json().catch(() => ({}))) as { detail?: string };
    return { ok: false, error: b.detail ?? "Username atau password salah." };
  }
  await applyBackendCookies(res);
  redirect("/");
}

export async function staffLoginAction(_: unknown, form: FormData): Promise<ActionResult> {
  const username = String(form.get("username") ?? "");
  // Code akses TIDAK di-trim: besar/kecil huruf, spasi, dan karakter dihitung persis.
  const password = String(form.get("password") ?? "");
  const accessCode = String(form.get("accessCode") ?? "");
  const res = await apiFetch("/auth/signin", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username, password, access_code: accessCode }).toString(),
  });
  if (!res.ok) {
    const b = (await res.json().catch(() => ({}))) as { detail?: string };
    return { ok: false, error: b.detail ?? "Kredensial tidak valid" };
  }
  await applyBackendCookies(res);
  const me = await apiFetch("/auth/me");
  const viewer = (await me.json().catch(() => null)) as Viewer | null;
  if (!viewer || (viewer.role !== "ADMIN" && viewer.role !== "MODERATOR")) {
    return { ok: false, error: "Kredensial tidak valid" };
  }
  redirect(viewer.role === "ADMIN" ? "/admin" : "/moderator");
}

export async function verifyOtpAction(_: unknown, form: FormData): Promise<ActionResult> {
  const email = String(form.get("email") ?? "").trim();
  const code = String(form.get("code") ?? "").trim();
  const res = await fetch(`${API_BASE}/auth/verify-otp`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, code }),
    cache: "no-store",
  });
  const b = (await res.json().catch(() => ({}))) as { message?: string; verified?: boolean };
  if (!res.ok || !b.verified) return { ok: false, error: b.message ?? "Kode OTP tidak valid atau kedaluwarsa." };
  redirect("/auth/login?verified=1");
}

export async function resendOtpAction(email: string): Promise<ActionResult<{ devCode?: string }>> {
  const res = await fetch(`${API_BASE}/auth/resend-otp`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email }),
    cache: "no-store",
  });
  const b = (await res.json().catch(() => ({}))) as { devCode?: string };
  return { ok: true, data: { devCode: b.devCode } };
}

export async function logoutAction(all?: boolean) {
  void all;
  try {
    await apiFetch("/auth/logout", { method: "POST" });
  } catch {
    /* abaikan */
  }
  await clearAuthCookies();
  redirect("/");
}

// ---------------- CHAT ----------------
export async function sendChatAction(body: string, parentId?: number | null): Promise<ActionResult<{ id: number }>> {
  return apiCall("/chat", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ body, parentId: parentId ?? null }),
  });
}

export async function reactChatAction(messageId: number, emoji: string): Promise<ActionResult> {
  return apiCall(`/chat/${messageId}/react`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ emoji }),
  });
}

export async function reportChatAction(messageId: number, reason: string, description?: string): Promise<ActionResult> {
  return apiCall(`/chat/${messageId}/report`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ reason, description }),
  });
}

export async function deleteChatAction(messageId: number): Promise<ActionResult> {
  return apiCall(`/chat/${messageId}`, { method: "DELETE" });
}

export async function pinChatAction(messageId: number): Promise<ActionResult> {
  return apiCall(`/chat/${messageId}/pin`, { method: "POST" });
}

// ---------------- BOOKMARK / REMINDER / WISH / OSHI ----------------
export async function toggleBookmarkAction(entityType: string, entityId: number, path: string): Promise<ActionResult<{ on: boolean }>> {
  const v = await getViewer();
  if (!v.userId) redirect(`/auth/login?next=${encodeURIComponent(path)}`);
  const r = await apiCall<{ on: boolean }>("/bookmarks/toggle", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ entityType, entityId }),
  });
  revalidatePath(path);
  return r;
}

export async function toggleReminderAction(scheduleId: number, path: string): Promise<ActionResult<{ on: boolean }>> {
  const v = await getViewer();
  if (!v.userId) redirect(`/auth/login?next=${encodeURIComponent(path)}`);
  const r = await apiCall<{ on: boolean }>("/schedules/reminders/toggle", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ scheduleId }),
  });
  revalidatePath(path);
  return r;
}

export async function sendWishAction(memberId: number, message: string): Promise<ActionResult> {
  const v = await getViewer();
  if (!v.userId) redirect(`/auth/login?next=/birthday`);
  return apiCall("/birthday/wishes", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ memberId, message }),
  });
}

export async function setOshiAction(form: FormData): Promise<ActionResult> {
  const kami = Number(form.get("kami") || 0);
  const others = form.getAll("oshi").map(Number).filter((n) => n && n !== kami).slice(0, 5);
  const r = await apiCall("/account/oshi", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ kami, others }),
  });
  revalidatePath("/account");
  return r;
}

export async function updateProfileAction(form: FormData): Promise<ActionResult> {
  const r = await apiCall("/account/profile", {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      bio: String(form.get("bio") ?? "").slice(0, 160),
      avatarSeed: Math.min(6, Math.max(1, Number(form.get("avatarSeed") || 1))),
    }),
  });
  revalidatePath("/account");
  return r;
}

export async function updateSettingsAction(form: FormData): Promise<ActionResult> {
  const prefs: Record<string, boolean> = {};
  for (const k of ["LIVE_ALERT", "SCHEDULE_REMINDER", "BIRTHDAY_ALERT", "NEWS_ALERT", "CHAT_MENTION"]) prefs[k] = form.get(k) === "on";
  const r = await apiCall("/account/settings", {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      theme: String(form.get("theme") ?? "system"),
      lang: String(form.get("lang") ?? "id"),
      multiLiveLayout: String(form.get("multiLiveLayout") ?? "row-2"),
      isPrivate: form.get("isPrivate") === "on",
      hideOshi: form.get("hideOshi") === "on",
      notifPrefs: prefs,
    }),
  });
  revalidatePath("/account/settings");
  return r;
}

export async function markAllReadAction() {
  const v = await getViewer();
  if (!v.userId) return;
  await apiCall("/notifications/read-all", { method: "POST" });
  revalidatePath("/notifications");
}

// ---------------- GAMES ----------------
type Level = "easy" | "medium" | "hard";

export type QuizQuestionView = { id: number; question: string; options: string[]; index: number; total: number; category: string };

export async function startQuizAction(level: Level): Promise<ActionResult<{ sessionId: string; q: QuizQuestionView; level: Level }>> {
  return apiCall(`/games/quiz/start?level=${level}`, { method: "POST" });
}

export async function answerQuizAction(sessionId: string, questionId: number, answerIndex: number): Promise<ActionResult<{ correct: boolean; correctIndex: number; gained: number; score: number; next: QuizQuestionView | null; finished: boolean }>> {
  return apiCall("/games/quiz/answer", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ sessionId, questionId, answerIndex }),
  });
}

export type GuessView = { sessionId: string; jiko: string; hints: string[]; hintsUsed: number; options: { id: number; name: string }[]; index: number; total: number; score: number };

export async function startGuessAction(): Promise<ActionResult<GuessView>> {
  return apiCall("/games/guess/start", { method: "POST" });
}

export async function guessHintAction(sessionId: string): Promise<ActionResult<GuessView>> {
  return apiCall("/games/guess/hint", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ sessionId }),
  });
}

export async function answerGuessAction(sessionId: string, memberId: number): Promise<ActionResult<{ correct: boolean; answer: string; gained: number; score: number; finished: boolean; next: GuessView | null }>> {
  return apiCall("/games/guess/answer", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ sessionId, memberId }),
  });
}

export async function saveSorterAction(ranking: number[]): Promise<ActionResult> {
  return apiCall("/games/sorter", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ ranking }),
  });
}

// ---------------- AI SEARCH ----------------
export async function aiSearchAction(mode: "db" | "llm", question: string): Promise<ActionResult<AIAnswer & { remaining: number }>> {
  const r = await apiCall<AIAnswer & { remaining: number }>("/ai/search", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ mode, question }),
  });
  if (!r.ok) return { ok: false, error: r.error, code: r.code };
  return { ok: true, data: { ...r.data, remaining: r.data?.remaining ?? 0 } };
}

export async function aiFeedbackAction(query: string, value: 1 | -1) {
  await apiCall("/ai/feedback", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ query, value }),
  });
}

// ---------------- MODERASI & ADMIN ----------------
export async function resolveReportAction(reportId: number, decision: "approved" | "rejected"): Promise<ActionResult> {
  const r = await apiCall(`/moderation/reports/${reportId}/resolve`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ decision }),
  });
  revalidatePath("/admin");
  revalidatePath("/moderator");
  return r;
}

export async function sanctionUserAction(form: FormData): Promise<ActionResult> {
  const r = await apiCall("/admin/sanction", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      userId: Number(form.get("userId")),
      kind: String(form.get("kind")),
      duration: String(form.get("duration") ?? "24"),
      reason: String(form.get("reason") ?? ""),
    }),
  });
  revalidatePath("/admin");
  revalidatePath("/moderator");
  return r;
}

export async function recentLoginLogs(limit = 20) {
  const v = await getViewer();
  if (v.role !== "ADMIN") return [];
  const { staffLoginLogs } = await import("@/lib/data");
  return staffLoginLogs(limit);
}

// dipakai ai-search page (kuota anonim)
export { clientKey };
