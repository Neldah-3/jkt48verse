import assert from "node:assert/strict";
import test from "node:test";
import { NextRequest } from "next/server";
import { middleware } from "../middleware";
import {
  backendAuthCookies, cookieMap, expiredAuthCookies, mergeCookies,
  needsSessionRefresh, refreshSessionCookies,
} from "../lib/session-cookies";

const now = Date.now();
const jwt = (exp: number) => `header.${Buffer.from(JSON.stringify({ exp, sid: "session" })).toString("base64url")}.signature`;
const oldHeader = "token=expired; refresh_token=old-refresh; csrf_token=old-csrf; theme=dark";
const refreshed = () => new Response("{}", {
  status: 200,
  headers: [
    ["set-cookie", "token=new-access; Max-Age=900; Path=/; HttpOnly; Secure; SameSite=Lax; Domain=backend.example"],
    ["set-cookie", "refresh_token=new-refresh; Max-Age=2592000; Path=/; HttpOnly; Secure; SameSite=Lax"],
    ["set-cookie", "csrf_token=new-csrf; Max-Age=2592000; Path=/; Secure; SameSite=Lax"],
  ],
});


test("cookie forwarding preserves security attributes but is first-party", () => {
  const cookies = backendAuthCookies(refreshed().headers);
  assert.equal(cookies.length, 3);
  assert.deepEqual(cookies[0], {
    name: "token", value: "new-access", maxAge: 900, path: "/", httpOnly: true, secure: true, sameSite: "lax",
  });
  assert.equal(cookies[2].httpOnly, false);
  assert.ok(cookies.every((cookie) => !("domain" in cookie)));
});

test("cookie parser preserves equals and Expires, and ignores unrelated cookies", () => {
  const response = new Response(null, { headers: [
    ["set-cookie", "token=a=b==; Expires=Wed, 01 Jan 2031 00:00:00 GMT; Path=/api"],
    ["set-cookie", "unrelated=ignored; Path=/"],
  ] });
  const cookies = backendAuthCookies(response.headers);
  assert.equal(cookies.length, 1);
  assert.equal(cookies[0].value, "a=b==");
  assert.equal(cookies[0].path, "/");
  assert.equal(cookies[0].expires?.toISOString(), "2031-01-01T00:00:00.000Z");
});

test("new cookies replace stale names instead of creating duplicate pairs", () => {
  const merged = mergeCookies(oldHeader, backendAuthCookies(refreshed().headers));
  assert.equal(merged, "token=new-access; refresh_token=new-refresh; csrf_token=new-csrf; theme=dark");
  assert.equal(mergeCookies(merged, expiredAuthCookies()), "theme=dark");
});

test("refresh scheduling handles missing, malformed, expired and near-expiry tokens", () => {
  assert.equal(needsSessionRefresh(undefined, now), true);
  assert.equal(needsSessionRefresh("invalid", now), true);
  assert.equal(needsSessionRefresh(jwt(now / 1000 - 10), now), true);
  assert.equal(needsSessionRefresh(jwt(now / 1000 + 10), now), true);
  assert.equal(needsSessionRefresh(jwt(now / 1000 + 900), now), false);
});

test("guests and unexpired sessions do not call the refresh endpoint", async () => {
  const fetcher: typeof fetch = async () => { throw new Error("must not fetch"); };
  assert.deepEqual(await refreshSessionCookies(new Headers(), "https://backend.example/api", fetcher), []);
  const headers = new Headers({ cookie: `token=${jwt(now / 1000 + 900)}; refresh_token=valid` });
  assert.deepEqual(await refreshSessionCookies(headers, "https://backend.example/api", fetcher, now), []);
});

test("refresh forwards CSRF and the original user-agent and returns all rotated cookies", async () => {
  let called = false;
  const fetcher: typeof fetch = async (url, init) => {
    called = true;
    assert.equal(url, "https://backend.example/api/auth/refresh");
    assert.equal(init?.method, "POST");
    const headers = new Headers(init?.headers);
    assert.equal(headers.get("cookie"), oldHeader);
    assert.equal(headers.get("x-csrf-token"), "old-csrf");
    assert.equal(headers.get("user-agent"), "original-browser");
    return refreshed();
  };
  const changes = await refreshSessionCookies(new Headers({ cookie: oldHeader, "user-agent": "original-browser" }), "https://backend.example/api/", fetcher);
  assert.equal(called, true);
  assert.equal(changes.length, 3);
});

test("invalid sessions are cleared; transient backend failures do not log users out", async () => {
  for (const status of [401, 403, 500, 503]) {
    const fetcher: typeof fetch = async () => new Response(null, { status });
    const changes = await refreshSessionCookies(new Headers({ cookie: oldHeader }), "https://backend.example/api", fetcher);
    if (status < 500) assert.deepEqual(changes, expiredAuthCookies());
    else assert.deepEqual(changes, []);
  }
  const offline: typeof fetch = async () => { throw new TypeError("offline"); };
  assert.deepEqual(await refreshSessionCookies(new Headers({ cookie: oldHeader }), "https://backend.example/api", offline), []);
});

test("middleware persists cookies for the browser AND the current server render", async (t) => {
  t.mock.method(globalThis, "fetch", async () => refreshed());
  const request = new NextRequest("https://preview.example/account", { headers: { cookie: oldHeader } });
  const response = await middleware(request);
  assert.equal(response.cookies.get("token")?.value, "new-access");
  assert.equal(response.cookies.get("refresh_token")?.value, "new-refresh");
  assert.equal(response.cookies.get("csrf_token")?.value, "new-csrf");
  const serverCookies = cookieMap(response.headers.get("x-middleware-request-cookie") ?? "");
  assert.equal(serverCookies.get("token"), "new-access");
  assert.equal(serverCookies.get("refresh_token"), "new-refresh");
  assert.equal(serverCookies.get("theme"), "dark");
});
