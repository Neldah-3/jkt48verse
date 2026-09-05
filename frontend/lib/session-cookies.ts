/** Shared by middleware and Server Actions. No Next.js request globals here. */
export const AUTH_COOKIE_NAMES = ["token", "refresh_token", "csrf_token"] as const;

export type AuthCookie = {
  name: string;
  value: string;
  path: string;
  httpOnly: boolean;
  sameSite: "lax" | "strict" | "none";
  secure?: boolean;
  maxAge?: number;
  expires?: Date;
};

export function cookieMap(header: string): Map<string, string> {
  const result = new Map<string, string>();
  for (const part of header.split(";")) {
    const index = part.indexOf("=");
    if (index < 0) continue;
    result.set(part.slice(0, index).trim(), part.slice(index + 1).trim());
  }
  return result;
}

export function backendAuthCookies(headers: Headers): AuthCookie[] {
  const result: AuthCookie[] = [];
  for (const line of headers.getSetCookie()) {
    const [pair, ...attributes] = line.split(";");
    const index = pair.indexOf("=");
    if (index < 0) continue;
    const name = pair.slice(0, index).trim();
    if (!(AUTH_COOKIE_NAMES as readonly string[]).includes(name)) continue;
    const cookie: AuthCookie = {
      name, value: pair.slice(index + 1).trim(), path: "/",
      httpOnly: name !== "csrf_token", sameSite: "lax",
    };
    for (const attr of attributes) {
      const separator = attr.indexOf("=");
      const key = (separator < 0 ? attr : attr.slice(0, separator)).trim().toLowerCase();
      const value = separator < 0 ? "" : attr.slice(separator + 1).trim();
      if (key === "secure") cookie.secure = true;
      if (key === "max-age" && /^-?\d+$/.test(value)) cookie.maxAge = Number(value);
      if (key === "expires") {
        const date = new Date(value);
        if (!Number.isNaN(date.getTime())) cookie.expires = date;
      }
      if (key === "samesite" && ["lax", "strict", "none"].includes(value.toLowerCase())) {
        cookie.sameSite = value.toLowerCase() as AuthCookie["sameSite"];
      }
      // Backend Domain/Path must not leak into the first-party frontend cookies.
    }
    result.push(cookie);
  }
  return result;
}

export function expiredAuthCookies(): AuthCookie[] {
  return AUTH_COOKIE_NAMES.map((name) => ({
    name, value: "", path: "/", maxAge: 0, httpOnly: name !== "csrf_token", sameSite: "lax",
  }));
}

export function mergeCookies(header: string, changes: AuthCookie[]): string {
  const jar = cookieMap(header);
  for (const cookie of changes) {
    if ((cookie.maxAge !== undefined && cookie.maxAge <= 0) || (cookie.expires && cookie.expires.getTime() <= Date.now())) {
      jar.delete(cookie.name);
    } else {
      jar.set(cookie.name, cookie.value);
    }
  }
  return [...jar].map(([name, value]) => `${name}=${value}`).join("; ");
}

/** Only a refresh scheduling hint; the backend always verifies the JWT/session. */
export function needsSessionRefresh(token: string | undefined, now = Date.now()): boolean {
  if (!token) return true;
  try {
    const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const payload = JSON.parse(atob(base64)) as { exp?: number; sid?: string };
    return !payload.sid || typeof payload.exp !== "number" || payload.exp * 1000 <= now + 30_000;
  } catch {
    return true;
  }
}

export async function refreshSessionCookies(
  requestHeaders: Headers, apiBase: string, fetcher: typeof fetch = fetch, now = Date.now(),
): Promise<AuthCookie[]> {
  const header = requestHeaders.get("cookie") ?? "";
  const jar = cookieMap(header);
  if (!jar.get("refresh_token") || !needsSessionRefresh(jar.get("token"), now)) return [];
  try {
    const response = await fetcher(`${apiBase.replace(/\/$/, "")}/auth/refresh`, {
      method: "POST", cache: "no-store", signal: AbortSignal.timeout(8_000),
      headers: {
        cookie: header,
        "x-csrf-token": jar.get("csrf_token") ?? "",
        "user-agent": requestHeaders.get("user-agent") ?? "jkt48verse-next",
      },
    });
    if (response.status === 401 || response.status === 403) return expiredAuthCookies();
    if (!response.ok) return []; // An outage must not destroy a valid refresh token.
    return backendAuthCookies(response.headers);
  } catch {
    return [];
  }
}
