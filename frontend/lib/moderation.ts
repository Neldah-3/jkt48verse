/**
 * Moderasi sisi klien (pre-check UX).
 * Penegakan sesungguhnya ada di backend FastAPI (banned words + whitelist emoji).
 */

export const EMOJI_WHITELIST = ["😃", "😀", "😱", "😎", "😑", "🤫", "🙃", "🤔", "😉", "😊", "😆", "😍", "🥰", "🤩", "😂", "🥳", "🤗", "🤓", "😭", "👌", "💪", "☝", "🙏", "👏", "🤲", "🤝", "👍"];

const LEET: Record<string, string> = { "4": "a", "@": "a", "3": "e", "1": "i", "!": "i", "0": "o", "5": "s", "$": "s", "7": "t" };

export function normalizeText(s: string) {
  let out = s.toLowerCase();
  out = out.replace(/[4@31!05$7]/g, (c) => LEET[c] ?? c);
  out = out.replace(/[^a-z\s]/g, "");
  out = out.replace(/(.)\1{2,}/g, "$1$1");
  return out;
}

const FALLBACK_BANNED = ["anjing", "bangsat", "kontol", "memek", "goblok", "tolol", "bajingan", "ngentot", "babi", "asu"];

/** Pre-check lokal (informative); keputusan final ada di server. */
export async function checkText(text: string): Promise<{ blocked: boolean; reason?: string }> {
  const n = normalizeText(text);
  const compact = n.replace(/\s+/g, "");
  for (const w of FALLBACK_BANNED) {
    if (n.includes(w) || compact.includes(w)) return { blocked: true, reason: w };
  }
  return { blocked: false };
}

export function checkEmoji(text: string) {
  for (const ch of text) {
    if (ch.codePointAt(0)! > 0x2000 && !EMOJI_WHITELIST.includes(ch) && !/^[\w\s.,!?()\-+*/=:;'"\u0000-\u2000@#%&$]/.test(ch)) {
      return { ok: false as const, emoji: ch };
    }
  }
  return { ok: true as const, emoji: null };
}

/** Slow-mode sisi klien (server tetap menegaskan). */
const lastSend = new Map<string, number>();
export function rateCheck(key: string, seconds = 5): { ok: boolean; waitSec?: number } {
  const last = lastSend.get(key) ?? 0;
  const elapsed = (Date.now() - last) / 1000;
  if (elapsed < seconds) return { ok: false, waitSec: Math.ceil(seconds - elapsed) };
  lastSend.set(key, Date.now());
  return { ok: true };
}
