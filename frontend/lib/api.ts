import "server-only";
import { cookies, headers } from "next/headers";

/** Base URL API FastAPI yang dijangkau dari server Next.js (bukan browser). */
export const API_BASE = (process.env.API_BASE_URL ?? "http://127.0.0.1:8000/api").replace(/\/$/, "");

export type ApiResult<T> = { ok: true; data: T } | { ok: false; status: number; error: string; code?: string };

function errMessage(status: number, body: unknown): string {
  if (body && typeof body === "object") {
    const b = body as Record<string, unknown>;
    const d = b.detail ?? b.error ?? b.message;
    if (typeof d === "string") return d;
    if (d && typeof d === "object") {
      const msg = (d as Record<string, unknown>).message;
      if (typeof msg === "string") return msg;
    }
  }
  return `Terjadi kesalahan (${status}).`;
}

/** Kunci anonim (kuota AI guest) — stabil dari IP+UA, sama seperti implementasi lama. */
export async function clientKey() {
  const h = await headers();
  const ip = (h.get("x-forwarded-for") ?? "local").split(",")[0];
  const ua = h.get("user-agent") ?? "";
  return Buffer.from(`${ip}|${ua}`).toString("base64").slice(0, 60);
}

async function cookieHeader(): Promise<string> {
  const c = await cookies();
  return c.toString();
}

async function rawFetch(path: string, init: RequestInit = {}, cookieStr: string, csrf?: string): Promise<Response> {
  const h = new Headers(init.headers);
  if (cookieStr) h.set("cookie", cookieStr);
  if (csrf) h.set("x-csrf-token", csrf);
  h.set("x-client-key", await clientKey());
  h.set("user-agent", (await headers()).get("user-agent") ?? "jkt48verse-next");
  return fetch(`${API_BASE}${path}`, { ...init, headers: h, cache: "no-store" });
}

/**
 * Panggil API backend dengan meneruskan cookie permintaan masuk.
 * Bila 401, coba refresh token sekali (best-effort).
 */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const c = await cookies();
  const cookieStr = c.toString();
  const csrf = c.get("csrf_token")?.value ?? "";
  const res = await rawFetch(path, init, cookieStr, csrf);
  if (res.status !== 401 || !c.get("refresh_token")) return res;

  // coba refresh
  let refreshed: Response | null = null;
  try {
    refreshed = await rawFetch("/auth/refresh", { method: "POST" }, cookieStr, csrf);
  } catch {
    refreshed = null;
  }
  if (!refreshed || !refreshed.ok) return res;

  // token baru ada di cookie respons refresh — pakai untuk request ulang
  const setCookies: string[] = [];
  refreshed.headers.getSetCookie?.().forEach((sc) => setCookies.push(sc.split(";")[0]));
  const merged = [cookieStr, ...setCookies].filter(Boolean).join("; ");
  let csrf2 = csrf;
  for (const sc of setCookies) {
    const [k, v] = sc.split("=");
    if (k === "csrf_token") csrf2 = v;
  }
  return rawFetch(path, init, merged, csrf2);
}

/** GET JSON dengan nilai default saat 404. */
export async function apiGet<T>(path: string, fallback: T): Promise<T> {
  try {
    const res = await apiFetch(path);
    if (!res.ok) return fallback;
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}

/** Panggil endpoint yang mengembalikan {ok, data|error} (konvensi verse). */
export async function apiCall<T = undefined>(path: string, init: RequestInit = {}): Promise<ApiResult<T>> {
  try {
    const res = await apiFetch(path, init);
    const body = await res.json().catch(() => ({}));
    const b = body as Record<string, unknown>;
    if (res.ok && b.ok !== false) {
      return { ok: true, data: ("data" in b ? b.data : undefined) as T };
    }
    return { ok: false, status: res.status, error: typeof b.error === "string" ? b.error : errMessage(res.status, body), code: typeof b.code === "string" ? b.code : undefined };
  } catch (e) {
    return { ok: false, status: 0, error: `Tidak dapat menghubungi server (${(e as Error).message}).` };
  }
}

/** Terapkan Set-Cookie dari respons backend ke cookie Next.js (dipakai server action login). */
export async function applyBackendCookies(res: Response) {
  const c = await cookies();
  const list = res.headers.getSetCookie?.() ?? [];
  for (const sc of list) {
    const [pair, ...attrs] = sc.split(";");
    const idx = pair.indexOf("=");
    if (idx < 0) continue;
    const name = pair.slice(0, idx).trim();
    const value = pair.slice(idx + 1).trim();
    const opt: Record<string, unknown> = { path: "/" };
    for (const a of attrs) {
      const [k, v] = a.split("=").map((x) => x.trim());
      const kl = k.toLowerCase();
      if (kl === "max-age") opt.maxAge = Number(v);
      else if (kl === "httponly") opt.httpOnly = true;
      else if (kl === "samesite") opt.sameSite = v === "lax" ? "lax" : v === "strict" ? "strict" : "none";
      else if (kl === "secure") opt.secure = true;
      else if (kl === "domain") { /* drop domain agar cookie first-party */ }
    }
    try {
      c.set(name, value, opt as never);
    } catch {
      /* cookie hanya bisa di-set di Server Action / Route Handler */
    }
  }
}

export async function clearAuthCookies() {
  const c = await cookies();
  for (const name of ["token", "refresh_token", "csrf_token"]) {
    try {
      c.set(name, "", { path: "/", maxAge: 0 });
    } catch {
      /* ignore */
    }
  }
}
