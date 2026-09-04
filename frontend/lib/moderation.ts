import "server-only";
import { db } from "@/db";
import { bannedWords } from "@/db/schema";

export const EMOJI_WHITELIST = ["😃", "😀", "😱", "😎", "😑", "🤫", "🙃", "🤔", "😉", "😊", "😆", "😍", "🥰", "🤩", "😂", "🥳", "🤗", "🤓", "😭", "👌", "💪", "☝", "🙏", "👏", "🤲", "🤝", "👍"];

const LEET: Record<string, string> = { "4": "a", "@": "a", "3": "e", "1": "i", "!": "i", "0": "o", "5": "s", "$": "s", "7": "t" };

export function normalizeText(s: string) {
  let out = s.toLowerCase();
  out = out.replace(/[4@31!05$7]/g, (c) => LEET[c] ?? c);
  out = out.replace(/[^a-z\s]/g, "");
  // collapse repeated letters (baaaagus -> bagus) but keep double letters once
  out = out.replace(/(.)\1{2,}/g, "$1$1");
  return out;
}

let cache: { words: string[]; at: number } | null = null;
async function words() {
  if (cache && Date.now() - cache.at < 60_000) return cache.words;
  const rows = await db.select().from(bannedWords);
  cache = { words: rows.map((r) => r.word.toLowerCase()), at: Date.now() };
  return cache.words;
}

/** Layer 1: local word filter. Returns matched word or null. */
export async function checkText(text: string): Promise<{ blocked: boolean; reason?: string }> {
  const list = await words();
  const n = normalizeText(text);
  const compact = n.replace(/\s+/g, "");
  const nDouble = n.replace(/(.)\1+/g, "$1");
  for (const w of list) {
    const ww = w.replace(/(.)\1+/g, "$1");
    if (n.includes(w) || compact.includes(w) || nDouble.includes(ww)) {
      return { blocked: true, reason: `Kata terlarang terdeteksi` };
    }
  }
  return { blocked: false };
}

/** Emoji whitelist check: any emoji (extended pictographic) that isn't whitelisted is rejected. */
export function checkEmoji(text: string) {
  const re = /\p{Extended_Pictographic}/gu;
  const found = text.match(re) ?? [];
  for (const e of found) {
    if (!EMOJI_WHITELIST.some((w) => w.startsWith(e))) return { ok: false, emoji: e };
  }
  return { ok: true };
}

// ---- Anti-spam (in-memory sliding window) ----
const windowMap = new Map<string, number[]>();
const slowUntil = new Map<string, number>();

export function rateCheck(key: string): { ok: boolean; waitSec?: number } {
  const now = Date.now();
  const until = slowUntil.get(key) ?? 0;
  if (until > now) return { ok: false, waitSec: Math.ceil((until - now) / 1000) };
  const arr = (windowMap.get(key) ?? []).filter((t) => now - t < 60_000);
  const last10s = arr.filter((t) => now - t < 10_000).length;
  if (last10s >= 5 || arr.length >= 30) {
    slowUntil.set(key, now + 20_000);
    return { ok: false, waitSec: 20 };
  }
  arr.push(now);
  windowMap.set(key, arr);
  return { ok: true };
}
