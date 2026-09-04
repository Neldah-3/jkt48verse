import "server-only";
import { cookies, headers } from "next/headers";
import { randomBytes, scryptSync, timingSafeEqual } from "node:crypto";
import { and, eq, gt } from "drizzle-orm";
import { db } from "@/db";
import { sessions, users, loginLogs } from "@/db/schema";
import { cache } from "react";

export const SESSION_COOKIE = "jv_session";
export type Role = "GUEST" | "MEMBER" | "MODERATOR" | "ADMIN";

export type Viewer = {
  role: Role;
  userId: number | null;
  username: string;
  avatarSeed: number;
  staffId?: string;
  user?: typeof users.$inferSelect;
  isBlocked?: boolean;
  isMuted?: boolean;
};

export const GUEST: Viewer = { role: "GUEST", userId: null, username: "Tamu", avatarSeed: 1 };

export function hashPassword(pw: string) {
  const salt = randomBytes(16).toString("hex");
  const hash = scryptSync(pw, salt, 64).toString("hex");
  return `${salt}:${hash}`;
}

export function verifyPassword(pw: string, stored: string) {
  const [salt, hash] = stored.split(":");
  if (!salt || !hash) return false;
  const calc = scryptSync(pw, salt, 64);
  const orig = Buffer.from(hash, "hex");
  return calc.length === orig.length && timingSafeEqual(calc, orig);
}

export async function createSession(opts: {
  userId?: number;
  staffId?: string;
  staffName?: string;
  role: Role;
  remember?: boolean;
}) {
  const token = randomBytes(32).toString("hex");
  const days = opts.remember ? 30 : 1;
  const expiresAt = new Date(Date.now() + days * 86400_000);
  const h = await headers();
  await db.insert(sessions).values({
    token,
    userId: opts.userId ?? null,
    staffId: opts.staffId ?? null,
    staffName: opts.staffName ?? null,
    role: opts.role,
    userAgent: h.get("user-agent")?.slice(0, 200) ?? null,
    expiresAt,
  });
  const c = await cookies();
  c.set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    expires: expiresAt,
  });
  return token;
}

export async function destroySession(all = false) {
  const c = await cookies();
  const token = c.get(SESSION_COOKIE)?.value;
  if (token) {
    const [s] = await db.select().from(sessions).where(eq(sessions.token, token));
    if (s) {
      if (all && s.userId) await db.delete(sessions).where(eq(sessions.userId, s.userId));
      else await db.delete(sessions).where(eq(sessions.token, token));
    }
  }
  c.delete(SESSION_COOKIE);
}

export const getViewer = cache(async (): Promise<Viewer> => {
  try {
    const c = await cookies();
    const token = c.get(SESSION_COOKIE)?.value;
    if (!token) return GUEST;
    const [s] = await db
      .select()
      .from(sessions)
      .where(and(eq(sessions.token, token), gt(sessions.expiresAt, new Date())));
    if (!s) return GUEST;
    if (s.userId) {
      const [u] = await db.select().from(users).where(eq(users.id, s.userId));
      if (!u) return GUEST;
      const now = Date.now();
      const isBlocked = !!u.blockedUntil && u.blockedUntil.getTime() > now;
      const isMuted = !!u.mutedUntil && u.mutedUntil.getTime() > now;
      return {
        role: u.role as Role,
        userId: u.id,
        username: u.username,
        avatarSeed: u.avatarSeed,
        user: u,
        isBlocked,
        isMuted,
      };
    }
    return {
      role: s.role as Role,
      userId: null,
      username: s.staffName ?? "staff",
      staffId: s.staffId ?? undefined,
      avatarSeed: 4,
    };
  } catch {
    return GUEST;
  }
});

export async function logLogin(entry: { userId?: number; username: string; success: boolean; kind: "member" | "staff" }) {
  const h = await headers();
  await db.insert(loginLogs).values({
    userId: entry.userId ?? null,
    username: entry.username,
    success: entry.success,
    kind: entry.kind,
    ip: (h.get("x-forwarded-for") ?? "local").split(",")[0].slice(0, 60),
    userAgent: h.get("user-agent")?.slice(0, 200) ?? null,
  });
}

export async function clientKey() {
  const h = await headers();
  const ip = (h.get("x-forwarded-for") ?? "local").split(",")[0];
  const ua = h.get("user-agent") ?? "";
  return Buffer.from(`${ip}|${ua}`).toString("base64").slice(0, 60);
}

export function isStaff(v: Viewer) {
  return v.role === "ADMIN" || v.role === "MODERATOR";
}
