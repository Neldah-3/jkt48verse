import "server-only";
import { and, asc, eq, gte, ilike, inArray, or, sql } from "drizzle-orm";
import { db } from "@/db";
import { members, news, schedules, encyclopedia, glossary, motivations } from "@/db/schema";
import { fmtDateLong, fmtTime, monthName, wibParts, wibMidnight } from "@/lib/time";

export type Source = { label: string; href: string; kind: "member" | "news" | "schedule" | "encyclopedia" | "birthday" | "motivation" };
export type AIAnswer = {
  mode: "db" | "llm";
  question: string;
  answer: string;
  confidence: number;
  sources: Source[];
  model?: string;
  fallback?: boolean;
};

const MONTHS = ["januari", "februari", "maret", "april", "mei", "juni", "juli", "agustus", "september", "oktober", "november", "desember"];

function stop(q: string) {
  return q
    .toLowerCase()
    .replace(/[?!.,]/g, " ")
    .split(/\s+/)
    .filter((w) => w.length > 2 && !["yang", "apa", "siapa", "adalah", "itu", "dan", "dari", "untuk", "dengan", "tentang", "kapan", "dimana", "di", "mana", "berita", "jadwal", "member"].includes(w));
}

export async function databaseSearch(question: string): Promise<AIAnswer> {
  const q = question.toLowerCase();
  const sources: Source[] = [];
  const nowP = wibParts(new Date());

  // Intent: birthday
  if (/ulang tahun|ultah|birthday|lahir/.test(q)) {
    let month = nowP.month;
    const mIdx = MONTHS.findIndex((m) => q.includes(m));
    if (mIdx >= 0) month = mIdx + 1;
    if (/hari ini/.test(q)) {
      const rows = await db.select().from(members).where(and(sql`extract(month from ${members.birthDate}) = ${nowP.month}`, sql`extract(day from ${members.birthDate}) = ${nowP.day}`));
      rows.forEach((m) => sources.push({ label: m.name, href: `/member/${m.slug}`, kind: "member" }));
      sources.push({ label: "Birthday Today", href: "/birthday", kind: "birthday" });
      return { mode: "db", question, confidence: 0.97, sources, answer: rows.length ? `Hari ini (${fmtDateLong(new Date())}) ada ${rows.length} member yang berulang tahun: ${rows.map((m) => m.name).join(", ")}. Kirim ucapanmu lewat halaman Birthday!` : `Tidak ada member yang berulang tahun hari ini (${fmtDateLong(new Date())}).` };
    }
    const rows = await db.select().from(members).where(sql`extract(month from ${members.birthDate}) = ${month}`).orderBy(sql`extract(day from ${members.birthDate})`);
    rows.slice(0, 8).forEach((m) => sources.push({ label: m.name, href: `/member/${m.slug}`, kind: "member" }));
    sources.push({ label: `Kalender Birthday`, href: `/birthday?tab=calendar&month=${month}`, kind: "birthday" });
    return { mode: "db", question, confidence: 0.95, sources, answer: rows.length ? `Member yang berulang tahun di bulan ${monthName(month)}: ${rows.map((m) => `${m.name} (${Number(m.birthDate!.split("-")[2])} ${monthName(month).slice(0, 3)})`).join(", ")}.` : `Belum ada data ulang tahun member di bulan ${monthName(month)}.` };
  }

  // Intent: generation
  const gen = q.match(/generasi\s*(\d{1,2})|gen\s*(\d{1,2})/);
  if (gen) {
    const g = Number(gen[1] ?? gen[2]);
    const rows = await db.select().from(members).where(and(eq(members.generation, g), inArray(members.status, ["regular", "trainee"]))).orderBy(asc(members.name));
    rows.slice(0, 10).forEach((m) => sources.push({ label: m.name, href: `/member/${m.slug}`, kind: "member" }));
    sources.push({ label: `Katalog Gen ${g}`, href: `/member?gen=${g}`, kind: "member" });
    return { mode: "db", question, confidence: rows.length ? 0.96 : 0.5, sources, answer: rows.length ? `Generasi ${g} JKT48 memiliki ${rows.length} member aktif: ${rows.map((m) => `${m.name} (${m.nickname})`).join(", ")}.` : `Tidak ditemukan member aktif dari generasi ${g} di database.` };
  }

  // Intent: schedule
  if (/jadwal|theater|show|konser|event|minggu (depan|ini)|besok|hari ini/.test(q)) {
    const start = wibMidnight(nowP.year, nowP.month, nowP.day);
    let end = new Date(start.getTime() + 7 * 86400_000);
    let label = "7 hari ke depan";
    if (/besok/.test(q)) { start.setUTCDate(start.getUTCDate() + 1); end = new Date(start.getTime() + 86400_000); label = "besok"; }
    else if (/hari ini/.test(q)) { end = new Date(start.getTime() + 86400_000); label = "hari ini"; }
    else if (/minggu depan/.test(q)) { start.setUTCDate(start.getUTCDate() + (8 - ((nowP.weekday + 6) % 7) - 1)); end = new Date(start.getTime() + 7 * 86400_000); label = "minggu depan"; }
    const type = /theater/.test(q) ? "theater" : /konser/.test(q) ? "concert" : /event|m&g|meet/.test(q) ? "event" : undefined;
    const rows = await db.select().from(schedules).where(and(gte(schedules.startAt, start), sql`${schedules.startAt} < ${end}`, type ? eq(schedules.type, type) : undefined)).orderBy(asc(schedules.startAt)).limit(8);
    rows.forEach((s) => sources.push({ label: s.title, href: `/schedule/${s.id}`, kind: "schedule" }));
    sources.push({ label: "Kalender Jadwal", href: "/schedule", kind: "schedule" });
    return { mode: "db", question, confidence: 0.93, sources, answer: rows.length ? `Jadwal ${type ?? "agenda"} ${label}: ${rows.map((s) => `${s.title} — ${fmtDateLong(s.startAt, false)} ${fmtTime(s.startAt)} WIB di ${s.location ?? "-"}`).join("; ")}.` : `Belum ada jadwal ${type ?? ""} untuk ${label}.` };
  }

  // Glossary / encyclopedia
  const terms = stop(q);
  const like = terms.map((t) => `%${t}%`);
  if (like.length) {
    const gl = await db.select().from(glossary).where(or(...like.map((l) => ilike(glossary.term, l)))).limit(3);
    if (gl.length) {
      sources.push({ label: "Wota Culture", href: "/encyclopedia/wota-culture", kind: "encyclopedia" });
      return { mode: "db", question, confidence: 0.94, sources, answer: gl.map((g) => `${g.term}: ${g.meaning}`).join(" ") };
    }
    const mem = await db.select().from(members).where(or(...like.map((l) => or(ilike(members.name, l), ilike(members.nickname, l))))).limit(3);
    if (mem.length) {
      mem.forEach((m) => sources.push({ label: m.name, href: `/member/${m.slug}`, kind: "member" }));
      const m = mem[0];
      return { mode: "db", question, confidence: 0.9, sources, answer: `${m.name} (${m.nickname}) adalah member JKT48 generasi ${m.generation ?? "-"} berstatus ${m.status.toUpperCase()}${m.birthDate ? `, lahir ${fmtDateLong(m.birthDate + "T00:00:00+07:00", false)}` : ""}${m.height ? `, tinggi ${m.height}` : ""}. Jikoshoukai: “${m.jikoshoukai ?? "-"}”.` };
    }
    const nw = await db.select().from(news).where(or(...like.map((l) => or(ilike(news.title, l), ilike(news.body, l))))).limit(3);
    if (nw.length) {
      nw.forEach((n) => sources.push({ label: n.title, href: `/news/${n.slug}`, kind: "news" }));
      return { mode: "db", question, confidence: 0.88, sources, answer: nw.map((n) => `${n.title}: ${n.summary}`).join(" ") };
    }
    const enc = await db.select().from(encyclopedia).where(or(...like.map((l) => or(ilike(encyclopedia.title, l), ilike(encyclopedia.content, l))))).limit(2);
    if (enc.length) {
      enc.forEach((e) => sources.push({ label: e.title, href: `/encyclopedia/${e.slug}`, kind: "encyclopedia" }));
      const e = enc[0];
      const idx = e.content.toLowerCase().indexOf(terms[0]);
      const snippet = e.content.slice(Math.max(0, idx - 80), idx + 260).replace(/[#*]/g, "").trim();
      return { mode: "db", question, confidence: 0.82, sources, answer: `Dari Encyclopedia “${e.title}”: …${snippet}…` };
    }
    const mo = await db.select().from(motivations).where(or(...like.map((l) => ilike(motivations.quote, l)))).limit(1);
    if (mo.length) {
      sources.push({ label: "Motivation", href: "/motivation", kind: "motivation" });
      return { mode: "db", question, confidence: 0.8, sources, answer: `“${mo[0].quote}” — ${mo[0].author ?? "JKT48Verse"}` };
    }
  }
  return { mode: "db", question, confidence: 0.2, sources: [], answer: "Aku belum menemukan jawaban di database JKT48Verse. Coba gunakan mode LLM AI Search untuk penjelasan lebih luas, atau ubah kata kuncimu." };
}

export function llmConfigured() {
  return !!process.env.LLM_API_KEY;
}

export async function llmSearch(question: string): Promise<AIAnswer> {
  const dbCtx = await databaseSearch(question);
  const key = process.env.LLM_API_KEY;
  const baseUrl = (process.env.LLM_BASE_URL ?? "https://api.groq.com/openai/v1").replace(/\/$/, "");
  const model = process.env.LLM_MODEL ?? "llama-3.1-8b-instant";
  if (!key) {
    return {
      mode: "llm",
      question,
      confidence: dbCtx.confidence,
      sources: dbCtx.sources,
      fallback: true,
      model: "belum dikonfigurasi",
      answer: `Mode LLM belum aktif di server ini (atur LLM_API_KEY, LLM_BASE_URL, LLM_MODEL untuk model open source seperti Llama 3 / Mistral / Qwen). Sementara itu, hasil dari Database AI: ${dbCtx.answer}`,
    };
  }
  try {
    const res = await fetch(`${baseUrl}/chat/completions`, {
      method: "POST",
      headers: { "content-type": "application/json", authorization: `Bearer ${key}` },
      body: JSON.stringify({
        model,
        temperature: Number(process.env.LLM_TEMPERATURE ?? 0.3),
        messages: [
          { role: "system", content: process.env.LLM_SYSTEM_PROMPT ?? "Kamu asisten komunitas fans JKT48 (JKT48Verse). Jawab hanya seputar JKT48, 48 Group, dan budaya idol. Jika pertanyaan di luar topik, tolak dengan sopan. Jawab ringkas dalam Bahasa Indonesia. Gunakan konteks database bila relevan." },
          { role: "user", content: `Konteks database (mungkin kosong): ${dbCtx.answer}\n\nPertanyaan: ${question}` },
        ],
      }),
    });
    const json = (await res.json()) as { choices?: { message?: { content?: string } }[]; error?: { message?: string } };
    const text = json.choices?.[0]?.message?.content?.trim();
    if (!text) throw new Error(json.error?.message ?? "Respon kosong");
    return { mode: "llm", question, confidence: 0.7, sources: dbCtx.sources, model, answer: text };
  } catch (e) {
    return { mode: "llm", question, confidence: 0.3, sources: dbCtx.sources, model, fallback: true, answer: `LLM tidak dapat dihubungi (${(e as Error).message}). Hasil Database AI: ${dbCtx.answer}` };
  }
}
