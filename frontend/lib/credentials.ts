import fs from "node:fs";
import path from "node:path";
import { timingSafeEqual } from "node:crypto";

export type StaffCredential = {
  username: string;
  id: string;
  password: string;
  code: string;
  role: "ADMIN" | "MODERATOR";
  activeUntil?: string;
};

/**
 * Admin (max 3) and Moderator (max 10) credentials live ONLY in server-side
 * credential storage: env `STAFF_CREDENTIALS` (JSON) or `credentials.json` in
 * project root. They are never stored in the database and cannot be edited via web.
 */
function loadRaw(): StaffCredential[] {
  const env = process.env.STAFF_CREDENTIALS;
  if (env) {
    try {
      return JSON.parse(env) as StaffCredential[];
    } catch {
      console.error("STAFF_CREDENTIALS env is not valid JSON");
    }
  }
  const file = path.join(process.cwd(), "credentials.json");
  if (fs.existsSync(file)) {
    try {
      return JSON.parse(fs.readFileSync(file, "utf8")) as StaffCredential[];
    } catch {
      console.error("credentials.json is not valid JSON");
    }
  }
  return [];
}

export function loadStaffCredentials(): StaffCredential[] {
  const all = loadRaw();
  const admins = all.filter((c) => c.role === "ADMIN").slice(0, 3);
  const mods = all.filter((c) => c.role === "MODERATOR").slice(0, 10);
  return [...admins, ...mods];
}

function safeEq(a: string, b: string) {
  const ab = Buffer.from(a);
  const bb = Buffer.from(b);
  if (ab.length !== bb.length) return false;
  return timingSafeEqual(ab, bb);
}

export function verifyStaff(input: { username: string; id: string; password: string; code: string }) {
  const list = loadStaffCredentials();
  for (const c of list) {
    const ok =
      safeEq(c.username, input.username) &&
      safeEq(c.id, input.id) &&
      safeEq(c.password, input.password) &&
      safeEq(c.code, input.code);
    if (ok) {
      if (c.activeUntil && new Date(c.activeUntil).getTime() < Date.now()) return null;
      return c;
    }
  }
  return null;
}

export function staffCount() {
  const list = loadStaffCredentials();
  return {
    admins: list.filter((c) => c.role === "ADMIN").length,
    moderators: list.filter((c) => c.role === "MODERATOR").length,
  };
}
