import "server-only";
import { cache } from "react";

import { apiGet } from "@/lib/api";

export const SESSION_COOKIE = "token";
export type Role = "GUEST" | "MEMBER" | "MODERATOR" | "ADMIN";

export type ViewerUser = {
  id: number;
  username: string;
  email: string;
  name: string;
  role: Role;
  bio: string | null;
  avatarSeed: number;
  theme: string;
  lang: string;
  multiLiveLayout: string;
  isPrivate: boolean;
  hideOshi: boolean;
  notifPrefs: Record<string, boolean>;
  blockedUntil: string | null;
  blockReason: string | null;
  mutedUntil: string | null;
  points: number;
  streak: number;
  lastDailyDate: string | null;
  createdAt: string;
  isEmailVerified: boolean;
};

export type Viewer = {
  role: Role;
  userId: number | null;
  username: string;
  avatarSeed: number;
  staffId?: string | null;
  user?: ViewerUser;
  isBlocked?: boolean;
  isMuted?: boolean;
};

export const GUEST: Viewer = { role: "GUEST", userId: null, username: "Tamu", avatarSeed: 1 };

/** Sesi berasal dari backend FastAPI (cookie token JWT diteruskan). */
export const getViewer = cache(async (): Promise<Viewer> => {
  return apiGet<Viewer>("/auth/me", GUEST as Viewer);
});

export async function clientKey() {
  const { clientKey: ck } = await import("@/lib/api");
  return ck();
}

export function isStaff(v: Viewer) {
  return v.role === "ADMIN" || v.role === "MODERATOR";
}
