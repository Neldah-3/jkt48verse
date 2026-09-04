export const TZ = "Asia/Jakarta";

const MONTHS_ID = [
  "Januari", "Februari", "Maret", "April", "Mei", "Juni",
  "Juli", "Agustus", "September", "Oktober", "November", "Desember",
];
const DAYS_ID = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];

export function wibParts(d: Date | string | number) {
  const date = new Date(d);
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: TZ,
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
    hour12: false, weekday: "short",
  });
  const p: Record<string, string> = {};
  for (const part of fmt.formatToParts(date)) p[part.type] = part.value;
  const weekdayMap: Record<string, number> = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  return {
    year: Number(p.year), month: Number(p.month), day: Number(p.day),
    hour: Number(p.hour === "24" ? "0" : p.hour), minute: Number(p.minute), second: Number(p.second),
    weekday: weekdayMap[p.weekday] ?? 0,
  };
}

export function wibDateKey(d: Date | string | number = new Date()) {
  const { year, month, day } = wibParts(d);
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

export function fmtTime(d: Date | string | number) {
  const { hour, minute } = wibParts(d);
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

export function fmtDateLong(d: Date | string | number, withDay = true) {
  const { year, month, day, weekday } = wibParts(d);
  return `${withDay ? DAYS_ID[weekday] + ", " : ""}${day} ${MONTHS_ID[month - 1]} ${year}`;
}

export function fmtDateShort(d: Date | string | number) {
  const { month, day } = wibParts(d);
  return `${day} ${MONTHS_ID[month - 1].slice(0, 3)}`;
}

export function fmtDateTime(d: Date | string | number) {
  return `${fmtDateLong(d, false)} · ${fmtTime(d)} WIB`;
}

export function relTime(d: Date | string | number, now = Date.now()) {
  const diff = Math.round((now - new Date(d).getTime()) / 1000);
  const abs = Math.abs(diff);
  const s = diff >= 0 ? "lalu" : "lagi";
  if (abs < 60) return diff >= 0 ? "baru saja" : "sebentar lagi";
  if (abs < 3600) return `${Math.floor(abs / 60)} menit ${s}`;
  if (abs < 86400) return `${Math.floor(abs / 3600)} jam ${s}`;
  return `${Math.floor(abs / 86400)} hari ${s}`;
}

export function fmtDuration(seconds: number) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

/** Date object for a WIB calendar date at 00:00 WIB */
export function wibMidnight(year: number, month: number, day: number) {
  return new Date(Date.UTC(year, month - 1, day, -7, 0, 0));
}

export function monthName(m: number) {
  return MONTHS_ID[m - 1];
}
export function dayName(w: number) {
  return DAYS_ID[w];
}

/** Birthday date string "YYYY-MM-DD" → {month, day} */
export function mdOf(dateStr: string) {
  const [, m, d] = dateStr.split("-").map(Number);
  return { month: m, day: d };
}

export function ageFrom(dateStr: string) {
  const { year, month, day } = wibParts(new Date());
  const [by, bm, bd] = dateStr.split("-").map(Number);
  let age = year - by;
  if (month < bm || (month === bm && day < bd)) age--;
  return age;
}

export function formatNumber(n: number) {
  return n.toLocaleString("id-ID");
}
