"use client";

import Link from "next/link";
import { useEffect, useState, useTransition } from "react";
import { Icon } from "@/components/ui";
import { aiFeedbackAction, aiSearchAction } from "@/app/actions";
import type { AIAnswer } from "@/lib/ai";

const EXAMPLES = ["Siapa member yang ulang tahun bulan ini?", "Jadwal theater minggu ini", "Member generasi 12", "Apa itu wotagei?"];
const KIND_CLS: Record<string, string> = { member: "t-info", news: "t-red", schedule: "t-ok", encyclopedia: "t-violet", birthday: "t-warn", motivation: "t-gray" };

export default function AISearch({ guest, llmReady }: { guest: boolean; llmReady: boolean }) {
  const [mode, setMode] = useState<"db" | "llm">("db");
  const [q, setQ] = useState("");
  const [ans, setAns] = useState<(AIAnswer & { remaining: number }) | null>(null);
  const [err, setErr] = useState<{ text: string; code?: string } | null>(null);
  const [hist, setHist] = useState<string[]>([]);
  const [fb, setFb] = useState<1 | -1 | null>(null);
  const [pending, start] = useTransition();
  useEffect(() => { try { setHist(JSON.parse(localStorage.getItem("jv_ai_hist") ?? "[]")); } catch { /* */ } }, []);

  const ask = (text = q) => {
    const question = text.trim();
    if (question.length < 3) return;
    setQ(question); setErr(null); setFb(null);
    start(async () => {
      const r = await aiSearchAction(mode, question);
      if (!r.ok) { setErr({ text: r.error, code: r.code }); return; }
      setAns(r.data!);
      const h = [question, ...hist.filter((x) => x !== question)].slice(0, 50);
      setHist(h); localStorage.setItem("jv_ai_hist", JSON.stringify(h));
    });
  };

  return (
    <div className="flex flex-col gap-3.5 max-w-[860px]">
      <div className="flex flex-wrap items-center gap-3">
        <div className="seg"><button className={mode === "db" ? "on" : ""} onClick={() => setMode("db")}>Database AI</button><button className={mode === "llm" ? "on" : ""} onClick={() => setMode("llm")}>LLM AI Search</button></div>
        <span className="muted text-[12px]">{mode === "db" ? "Jawaban akurat dari data platform, selalu dengan sumber." : llmReady ? "Model open source · jawaban perlu verifikasi." : "LLM belum dikonfigurasi (LLM_API_KEY) — fallback ke Database AI."}</span>
      </div>
      <form className="bigsearch" onSubmit={(e) => { e.preventDefault(); ask(); }}>
        <Icon name="spark" size={20} className="text-primary" />
        <input value={q} onChange={(e) => setQ(e.target.value.slice(0, 200))} placeholder="Tanya apa saja seputar JKT48…" aria-label="Pertanyaan" />
        <button className="btn pri" disabled={pending || q.trim().length < 3}>{pending ? "Mencari…" : "Cari"}</button>
      </form>
      <div className="flex flex-wrap gap-2">{EXAMPLES.map((e) => (<button key={e} className="chip" onClick={() => ask(e)}>{e}</button>))}</div>
      {hist.length > 0 && <details className="text-[12px]"><summary className="muted cursor-pointer">Riwayat pencarian ({hist.length})</summary><div className="flex flex-wrap gap-1.5 mt-2">{hist.slice(0, 12).map((h) => (<button key={h} className="chip" onClick={() => ask(h)}>{h}</button>))}</div></details>}
      {err && <div className="card w" style={{ borderLeft: "4px solid var(--primary)" }}><b className="text-[13px]">{err.code === "RATE_LIMIT" ? "Kuota habis" : "Gagal mencari"}</b><p className="text-[12.5px]">{err.text}</p>{err.code && <code className="text-[10.5px] muted">{err.code}</code>}{guest && <Link href="/auth/login?next=/ai-search" className="link">Login untuk kuota 20/hari ›</Link>}</div>}
      {pending && <div className="card w"><div className="skeleton h-4 w-2/3" /><div className="skeleton h-3 w-full" /><div className="skeleton h-3 w-5/6" /></div>}
      {ans && !pending && (
        <div className="card w ans">
          <div className="flex items-center gap-2 flex-wrap"><span className="muted text-[12px]">Pertanyaan:</span><b className="text-[13px]">{ans.question}</b><span className="flex-1" />{ans.mode === "db" ? <span className="tag t-ok">Confidence {Math.round(ans.confidence * 100)}%</span> : <span className="tag t-warn">AI Generated — Perlu Verifikasi</span>}</div>
          <p>{ans.answer}</p>
          {ans.mode === "llm" && <p className="muted text-[11.5px] italic">Jawaban dihasilkan model {ans.model ?? "LLM"} dan bukan informasi resmi JKT48. Batasan topik: JKT48 & idol culture.</p>}
          {ans.sources.length > 0 && <div className="flex flex-wrap gap-1.5"><span className="muted text-[11px] self-center">Sumber:</span>{ans.sources.map((s, i) => (<Link key={i} href={s.href} className={`src ${KIND_CLS[s.kind]}`}>{s.label} ›</Link>))}</div>}
          <div className="flex items-center gap-2 border-t border-border pt-2">
            <button className={`btn ghost sm ${fb === 1 ? "!text-ok" : ""}`} onClick={() => { setFb(1); aiFeedbackAction(ans.question, 1); }}><Icon name="thumbUp" size={13} /> Membantu</button>
            <button className={`btn ghost sm ${fb === -1 ? "!text-primary" : ""}`} onClick={() => { setFb(-1); aiFeedbackAction(ans.question, -1); }}><Icon name="thumbDown" size={13} /> Kurang</button>
            <span className="muted text-[11px] ml-auto">Sisa kuota hari ini: {ans.remaining}</span>
          </div>
        </div>
      )}
    </div>
  );
}
