import { NextRequest, NextResponse } from "next/server";
import { mergeCookies, refreshSessionCookies } from "./lib/session-cookies";

/** Refresh before RSC rendering: cookie writes inside Server Components are not
 * supported. Both the current server render and the browser get the new tokens. */
export async function middleware(request: NextRequest) {
  const apiBase = process.env.API_BASE_URL ?? "http://127.0.0.1:8000/api";
  const changes = await refreshSessionCookies(request.headers, apiBase);
  if (!changes.length) return NextResponse.next();

  const headers = new Headers(request.headers);
  headers.set("cookie", mergeCookies(headers.get("cookie") ?? "", changes));
  const response = NextResponse.next({ request: { headers } });
  for (const cookie of changes) response.cookies.set(cookie);
  return response;
}

export const config = {
  matcher: ["/((?!_next/|manifest.webmanifest|.*\\.(?:png|jpg|jpeg|svg|webp|ico)$).*)"],
};
