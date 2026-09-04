"use client";

import Link from "next/link";
import { useEffect, useState, useTransition } from "react";
import { Avatar, Icon } from "@/components/ui";
import { answerGuessAction, answerQuizAction, guessHintAction, saveSorterAction, startGuessAction, startQuizAction, type GuessView, type QuizQuestionView } from "@/app/actions";

type Level = "easy" | "medium" | "hard";

export function QuizGame({ guest }: { guest: boolean }) {
  const [level, setLevel] = useState<Level>("easy");
  const [session, setSession] = useState<string | null>(null);
  const [q, setQ] = useState<QuizQuestionView | null>(null);
  const [score, setScore] = useState(0);
  const [fb, setFb] = useState<{ correct: boolean; correctIndex: number; gained: number } | null>(null);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const [sec, setSec] = useState(0);
  useEffect(() => { if (!q || fb) return; setSec(0); const t = setInterval(() => setSec((s) => s + 1), 1000); return () => clearInterval(t); }, [q, fb]);

  const begin = () => start(async () => { const r = await startQuizAction(level); if (!r.ok) return setErr(r.error); setSession(r.data!.sessionId); setQ(r.data!.q); setScore(0); setDone(false); setFb(null); setErr(null); });
  const answer = (i: number) => { if (!session || !q || fb) return; start(async () => { const r = await answerQuizAction(session, q.id, i); if (!r.ok) return setErr(r.error); setFb({ correct: r.data!.correct, correctIndex: r.data!.correctIndex, gained: r.data!.gained }); setScore(r.data!.score); setTimeout(() => { setFb(null); if (r.data!.finished) setDone(true); else setQ(r.data!.next); }, 1100); }); };

  if (!session || done) {
    return (
      <div className="card w">
        {done && <div className="rounded-[12px] p-4 text-center" style={{ background: "var(--primary-soft)" }}><div className="muted text-[11px] uppercase font-bold">Skor akhir</div><div className="text-[34px] font-extrabold text-primary tabular">{score}</div>{guest ? <p className="muted text-[12px]">Tamu: skor tidak disimpan. <Link href="/auth/login?next=/games/quiz" className="link">Login</Link> untuk leaderboard & streak.</p> : <p className="text-[12px]">Skor tersimpan ke leaderboard! 🎉</p>}</div>}
        <h3 className="text-[14px] font-bold">Pilih level</h3>
        <div className="grid grid-cols-3 gap-2">
          {(["easy", "medium", "hard"] as Level[]).map((l) => (<button key={l} onClick={() => setLevel(l)} className={`rounded-[12px] border p-3 text-left ${level === l ? "border-primary bg-primary-soft" : "border-border"}`}><div className="font-bold capitalize text-[13px]">{l}</div><div className="muted text-[11px]">{{ easy: "10 soal · 30 poin", medium: "20 soal · 60 poin", hard: "30 soal · 90 poin" }[l]}</div></button>))}
        </div>
        <p className="muted text-[11.5px]">Bonus waktu: max(0, 10 − ⌊detik/3⌋). Penilaian sepenuhnya di server.</p>
        {err && <p className="text-primary text-[12.5px]">{err}</p>}
        <button className="btn pri self-start" onClick={begin} disabled={pending}><Icon name="play" size={15} /> {done ? "Main lagi" : "Mulai Quiz"}</button>
      </div>
    );
  }
  return (
    <div className="card w">
      <div className="flex items-center justify-between text-[12px]"><span className="tag t-red">{q?.category}</span><span className="muted">Soal {(q?.index ?? 0) + 1}/{q?.total}</span><span className="tabular font-bold"><Icon name="clock" size={12} /> {sec}s</span><b className="tabular">Skor {score}</b></div>
      <div className="skeleton h-1.5 !bg-surface-3"><div className="h-full bg-primary rounded-full transition-all" style={{ width: `${(((q?.index ?? 0) + (fb ? 1 : 0)) / (q?.total ?? 1)) * 100}%` }} /></div>
      <h3 className="text-[16px] font-bold leading-snug">{q?.question}</h3>
      <div className="grid sm:grid-cols-2 gap-2">
        {q?.options.map((o, i) => {
          let cls = "border-border hover:bg-surface-2";
          if (fb) { if (i === fb.correctIndex) cls = "border-ok bg-ok-soft"; else if (!fb.correct && i !== fb.correctIndex) cls = "border-border opacity-60"; }
          return <button key={i} disabled={!!fb || pending} onClick={() => answer(i)} className={`rounded-[12px] border p-3 text-left text-[13.5px] font-semibold transition ${cls}`}><span className="muted mr-2">{String.fromCharCode(65 + i)}.</span>{o}</button>;
        })}
      </div>
      {fb && <p className={`text-[13px] font-bold ${fb.correct ? "text-ok" : "text-primary"}`}>{fb.correct ? `Benar! +${fb.gained} poin` : "Salah. 0 poin"}</p>}
      {err && <p className="text-primary text-[12.5px]">{err}</p>}
    </div>
  );
}

export function GuessGame({ guest }: { guest: boolean }) {
  const [view, setView] = useState<GuessView | null>(null);
  const [fb, setFb] = useState<{ correct: boolean; answer: string; gained: number } | null>(null);
  const [done, setDone] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const begin = () => start(async () => { const r = await startGuessAction(); if (!r.ok) return setErr(r.error); setView(r.data!); setDone(null); setFb(null); });
  const hint = () => start(async () => { if (!view) return; const r = await guessHintAction(view.sessionId); if (r.ok) setView(r.data!); else setErr(r.error); });
  const answer = (id: number) => start(async () => { if (!view || fb) return; const r = await answerGuessAction(view.sessionId, id); if (!r.ok) return setErr(r.error); setFb({ correct: r.data!.correct, answer: r.data!.answer, gained: r.data!.gained }); setTimeout(() => { setFb(null); if (r.data!.finished) { setDone(r.data!.score); setView(null); } else setView(r.data!.next); }, 1400); });

  if (!view) {
    return (
      <div className="card w">
        {done !== null && <div className="rounded-[12px] p-4 text-center" style={{ background: "var(--violet-soft)" }}><div className="muted text-[11px] uppercase font-bold">Skor akhir</div><div className="text-[34px] font-extrabold tabular" style={{ color: "var(--violet)" }}>{done}</div>{guest ? <p className="muted text-[12px]">Tamu: skor tidak disimpan. <Link href="/auth/login?next=/games/guess-member" className="link">Login</Link> untuk leaderboard.</p> : <p className="text-[12px]">Skor tersimpan! 🎉</p>}</div>}
        <h3 className="text-[14px] font-bold">Tebak member dari jikoshoukai</h3>
        <p className="muted text-[12.5px]">5 soal · 100 poin awal, −20 per hint (maks 3), bonus kecepatan max(0, 20 − detik).</p>
        {err && <p className="text-primary text-[12.5px]">{err}</p>}
        <button className="btn pri self-start" onClick={begin} disabled={pending}><Icon name="play" size={15} /> {done !== null ? "Main lagi" : "Mulai"}</button>
      </div>
    );
  }
  return (
    <div className="card w">
      <div className="flex items-center justify-between text-[12px]"><span className="tag t-violet">Guess Member</span><span className="muted">Soal {view.index + 1}/{view.total}</span><b className="tabular">Skor {view.score}</b></div>
      <blockquote className="border-l-4 pl-4 italic text-[15px] leading-relaxed" style={{ borderColor: "var(--violet)" }}>“{view.jiko}”</blockquote>
      <div className="flex flex-wrap gap-2 items-center">
        {view.hints.map((h, i) => (<span key={i} className="chip on">💡 {h}</span>))}
        {view.hintsUsed < 3 && !fb && <button className="btn ghost sm" onClick={hint} disabled={pending}>Hint ({3 - view.hintsUsed} tersisa · −20)</button>}
      </div>
      <div className="grid sm:grid-cols-2 gap-2">
        {view.options.map((o) => (<button key={o.id} disabled={!!fb || pending} onClick={() => answer(o.id)} className={`rounded-[12px] border p-3 text-left text-[13.5px] font-semibold flex items-center gap-2 ${fb && o.name === fb.answer ? "border-ok bg-ok-soft" : "border-border hover:bg-surface-2"}`}><Avatar name={o.name} size={26} />{o.name}</button>))}
      </div>
      {fb && <p className={`text-[13px] font-bold ${fb.correct ? "text-ok" : "text-primary"}`}>{fb.correct ? `Benar! +${fb.gained} poin` : `Salah. Jawabannya: ${fb.answer}`}</p>}
      {err && <p className="text-primary text-[12.5px]">{err}</p>}
    </div>
  );
}

export type SorterMember = { id: number; name: string; nickname: string; generation: number | null };

export function OshiSorter({ members, guest }: { members: SorterMember[]; guest: boolean }) {
  const gens = [...new Set(members.map((m) => m.generation ?? 0))].sort((a, b) => a - b);
  const [gen, setGen] = useState<number | "all">("all");
  const [list, setList] = useState<SorterMember[]>(members);
  const [drag, setDrag] = useState<number | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [pending, start] = useTransition();
  useEffect(() => { setList(gen === "all" ? members : members.filter((m) => (m.generation ?? 0) === gen)); }, [gen, members]);

  const move = (from: number, to: number) => { if (from === to || to < 0 || to >= list.length) return; setList((l) => { const a = [...l]; const [it] = a.splice(from, 1); a.splice(to, 0, it); return a; }); };
  const shuffle = () => setList((l) => [...l].sort(() => Math.random() - 0.5));
  const save = () => start(async () => { const r = await saveSorterAction(list.map((m) => m.id)); setSaved(r.ok ? "Peringkat tersimpan di akunmu." : r.error); });
  const share = async () => { const txt = `Oshi ranking saya (JKT48Verse):\n${list.slice(0, 10).map((m, i) => `${i + 1}. ${m.name}`).join("\n")}`; try { await navigator.clipboard.writeText(txt); setSaved("Top 10 disalin ke clipboard — siap dibagikan!"); } catch { setSaved(txt); } };

  return (
    <div className="grid12">
      <div className="c8 card w">
        <div className="flex flex-wrap gap-2 items-center">
          <button className={`chip ${gen === "all" ? "on" : ""}`} onClick={() => setGen("all")}>Semua ({members.length})</button>
          {gens.map((g) => (<button key={g} className={`chip ${gen === g ? "on" : ""}`} onClick={() => setGen(g)}>Gen {g || "?"}</button>))}
          <span className="flex-1" />
          <button className="btn ghost sm" onClick={shuffle}><Icon name="refresh" size={13} /> Acak</button>
        </div>
        <p className="muted text-[11.5px]">Seret kartu (drag & drop) atau gunakan tombol ▲▼. Peringkat 1 = <i>kami-oshi</i>.</p>
        <ol className="flex flex-col gap-1.5">
          {list.map((m, i) => (
            <li key={m.id} draggable onDragStart={() => setDrag(i)} onDragOver={(e) => e.preventDefault()} onDrop={() => { if (drag !== null) move(drag, i); setDrag(null); }} className={`flex items-center gap-3 rounded-[11px] border p-2 cursor-grab active:cursor-grabbing ${i === 0 ? "border-primary bg-primary-soft" : "border-border bg-surface"}`}>
              <span className={`w-7 h-7 rounded-[8px] inline-flex items-center justify-center text-[11px] font-bold ${i < 3 ? "text-white" : "bg-surface-3"}`} style={i < 3 ? { background: ["#d4a017", "#9aa3ad", "#b87333"][i] } : undefined}>{i + 1}</span>
              <Avatar name={m.name} size={30} />
              <span className="flex-1 min-w-0"><span className="block text-[13px] font-semibold truncate">{m.name}</span><span className="muted text-[11px]">@{m.nickname} · Gen {m.generation ?? "-"}</span></span>
              {i === 0 && <span className="tag t-red">Kami-oshi</span>}
              <span className="flex flex-col"><button onClick={() => move(i, i - 1)} className="btn icon ghost" style={{ width: 26, height: 22, minHeight: 22 }} aria-label="Naik">▲</button><button onClick={() => move(i, i + 1)} className="btn icon ghost" style={{ width: 26, height: 22, minHeight: 22 }} aria-label="Turun">▼</button></span>
            </li>
          ))}
        </ol>
      </div>
      <div className="c4 flex flex-col gap-3.5">
        <div className="card w">
          <h3 className="text-[13.5px] font-bold">Hasil Kamu</h3>
          <div className="mcard jkt48-red-white" style={{ minHeight: 0, padding: 18 }}>
            <div className="text-[10px] uppercase tracking-widest opacity-80">Oshi Ranking · JKT48Verse</div>
            <ol className="text-[13px] font-semibold flex flex-col gap-1">{list.slice(0, 5).map((m, i) => (<li key={m.id}>{i + 1}. {m.name}</li>))}</ol>
          </div>
          <div className="flex gap-2 flex-wrap">
            {guest ? <Link href="/auth/login?next=/games/oshi-sorter" className="btn pri sm">Login untuk simpan</Link> : <button className="btn pri sm" onClick={save} disabled={pending}>Simpan</button>}
            <button className="btn ghost sm" onClick={share}>Bagikan</button>
          </div>
          {saved && <p className="text-[12px] whitespace-pre-wrap" style={{ color: "var(--ok)" }}>{saved}</p>}
        </div>
      </div>
    </div>
  );
}
