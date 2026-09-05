import "server-only";
import { cookies, headers } from "next/headers";
import { backendAuthCookies, expiredAuthCookies } from "@/lib/session-cookies";

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

async function rawFetch(path: string, init: RequestInit = {}, cookieStr: string, csrf?: string): Promise<Response> {
  const h = new Headers(init.headers);
  if (cookieStr) h.set("cookie", cookieStr);
  if (csrf) h.set("x-csrf-token", csrf);
  h.set("x-client-key", await clientKey());
  h.set("user-agent", (await headers()).get("user-agent") ?? "jkt48verse-next");
  return fetch(`${API_BASE}${path}`, { ...init, headers: h, cache: "no-store" });
}

/** Forward the session prepared by middleware. Never rotate tokens during RSC
 * rendering: Server Components cannot persist Set-Cookie to the browser. */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const c = await cookies();
  return rawFetch(path, init, c.toString(), c.get("csrf_token")?.value);
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

/** Called only inside Server Actions / Route Handlers, where cookies are writable. */
export async function applyBackendCookies(res: Response) {
  const c = await cookies();
  for (const cookie of backendAuthCookies(res.headers)) c.set(cookie);
}

export async function clearAuthCookies() {
  const c = await cookies();
  for (const cookie of expiredAuthCookies()) c.set(cookie);
}
