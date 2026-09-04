"use client";

import Link from "next/link";
import { useEffect, useRef, useState, useTransition } from "react";
import { Avatar, Icon, RoleTag } from "@/components/ui";
import { deleteChatAction, pinChatAction, reactChatAction, reportChatAction, sendChatAction } from "@/app/actions";
import type { ChatRow } from "@/lib/data";
import { fmtTime } from "@/lib/time";

const EMOJI = ["😃", "😀", "😱", "😎", "😑", "🤫", "🙃", "🤔", "😉", "😊", "😆", "😍", "🥰", "🤩", "😂", "🥳", "🤗", "🤓", "😭", "👌", "💪", "☝", "🙏", "👏", "🤲", "🤝", "👍"];
type Pinned = { id: number; username: string; body: string };
type Viewer = { role: string; userId: number | null; username: string; isMuted?: boolean; mutedUntil?: string | null };

export default function ChatRoom({ initial, pinned: initPinned, viewer }: { initial: ChatRow[]; pinned: Pinned[]; viewer: Viewer }) {
  const [msgs, setMsgs] = useState(initial);
  const [pinned, setPinned] = useState(initPinned);
  const [text, setText] = useState("");
  const [reply, setReply] = useState<ChatRow | null>(null);
  const [toast, setToast] = useState<{ text: string; code?: string } | null>(null);
  const [reportFor, setReportFor] = useState<number | null>(null);
  const [pending, start] = useTransition();
  const listRef = useRef<HTMLDivElement>(null);
  const canWrite = viewer.role !== "GUEST";
  const isStaff = viewer.role === "ADMIN" || viewer.role === "MODERATOR";

  const load = async () => {
    try {
      const r = await fetch("/api/chat", { cache: "no-store" });
      if (!r.ok) return;
      const j = (await r.json()) as { messages: ChatRow[]; pinned: Pinned[] };
      setMsgs(j.messages);
      setPinned(j.pinned);
    } catch { /* offline */ }
  };
  useEffect(() => {
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [msgs.length]);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 5000);
    return () => clearTimeout(t);
  }, [toast]);

  const send = () => {
    if (!text.trim()) return;
    start(async () => {
      const r = await sendChatAction(text, reply?.id ?? null);
      if (r.ok) { setText(""); setReply(null); await load(); }
      else setToast({ text: r.error, code: r.code });
    });
  };
  const act = (fn: () => Promise<{ ok: boolean; error?: string; code?: string }>) => start(async () => { const r = await fn(); if (!r.ok) setToast({ text: r.error ?? "Gagal", code: r.code }); await load(); });

  return (
    <div className="card flex flex-col" style={{ height: "calc(100dvh - 210px)", minHeight: 480 }}>
      {toast && <div className="toast"><div className="font-semibold">Pesan tidak terkirim</div><div className="text-[12.5px]">{toast.text}</div>{toast.code && <code>{toast.code}</code>}</div>}
      {pinned.length > 0 && (
        <div className="px-4 py-2 border-b border-border flex flex-col gap-1" style={{ background: "var(--primary-soft)" }}>
          {pinned.map((p) => (<div key={p.id} className="flex items-center gap-2 text-[12px]"><Icon name="pin" size={13} className="text-primary" /><b>{p.username}:</b><span className="truncate flex-1">{p.body}</span>{viewer.role === "ADMIN" && <button className="link" onClick={() => act(() => pinChatAction(p.id))}>Lepas</button>}</div>))}
        </div>
      )}
      <div ref={listRef} className="flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-3">
        {msgs.length === 0 && <p className="muted text-[12.5px] text-center py-8">Belum ada pesan dalam 3 hari terakhir. Sapa duluan yuk!</p>}
        {msgs.map((m) => (
          <div key={m.id} className="flex gap-2 group">
            <Avatar name={m.username} size={28} seed={m.avatarSeed} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap"><b className="text-[12.5px]">{m.username}</b><RoleTag role={m.role} /><span className="muted text-[10.5px]">{fmtTime(m.createdAt)}</span>{m.isPinned && <Icon name="pin" size={12} className="text-primary" />}</div>
              {m.parent && <div className="text-[11px] muted border-l-2 border-border-2 pl-2 mt-1 truncate">↩ {m.parent.username}: {m.parent.body}</div>}
              <div className="bubble inline-block mt-1">{m.body}</div>
              <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                {m.reactions.map((r) => (<button key={r.emoji} className={`react ${r.mine ? "on" : ""}`} onClick={() => canWrite ? act(() => reactChatAction(m.id, r.emoji)) : setToast({ text: "Login untuk memberi reaksi.", code: "AUTH_REQUIRED" })}>{r.emoji} {r.n}</button>))}
                {canWrite && (
                  <span className="opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition flex items-center gap-1">
                    {["👍", "😂", "😍"].map((e) => (<button key={e} className="react" onClick={() => act(() => reactChatAction(m.id, e))}>{e}</button>))}
                    <button className="react" onClick={() => setReply(m)}>↩ Balas</button>
                    {m.userId !== viewer.userId && <button className="react" onClick={() => setReportFor(m.id)}><Icon name="flag" size={11} /> Lapor</button>}
                    {(isStaff || m.userId === viewer.userId) && <button className="react" onClick={() => act(() => deleteChatAction(m.id))}><Icon name="x" size={11} /> Hapus</button>}
                    {viewer.role === "ADMIN" && <button className="react" onClick={() => act(() => pinChatAction(m.id))}><Icon name="pin" size={11} /> {m.isPinned ? "Lepas" : "Pin"}</button>}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="border-t border-border px-3 py-2 flex flex-col gap-2" style={{ background: "var(--surface)" }}>
        {canWrite && <div className="flex flex-wrap gap-0.5">{EMOJI.map((e) => (<button key={e} className="emo" onClick={() => setText((t) => (t + e).slice(0, 500))} aria-label={`emoji ${e}`}>{e}</button>))}</div>}
        {reply && <div className="text-[11.5px] flex items-center gap-2 bg-surface-2 rounded-[8px] px-2 py-1"><span className="muted">Membalas</span><b>{reply.username}</b><span className="truncate flex-1">{reply.body}</span><button onClick={() => setReply(null)}><Icon name="x" size={13} /></button></div>}
        {viewer.isMuted && <div className="text-[12px] rounded-[9px] px-3 py-2" style={{ background: "var(--warn-soft)", color: "var(--warn)" }}>Kamu sedang di-mute hingga {viewer.mutedUntil ? fmtTime(viewer.mutedUntil) : "-"} WIB.</div>}
        {canWrite ? (
          <div className="flex items-end gap-2">
            <div className="relative flex-1">
              <textarea value={text} onChange={(e) => setText(e.target.value.slice(0, 500))} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} className="input resize-none" rows={1} placeholder="Tulis pesan… (@username untuk mention)" style={{ minHeight: 40, paddingRight: 54 }} />
              <span className="absolute right-3 bottom-2.5 muted text-[10.5px] tabular">{text.length}/500</span>
            </div>
            <button className="btn pri icon" onClick={send} disabled={pending || !text.trim()} aria-label="Kirim"><Icon name="send" size={16} /></button>
          </div>
        ) : (
          <div className="flex items-center gap-3 rounded-[11px] border border-border-2 bg-surface-2 px-3 py-2"><span className="muted text-[13px] flex-1">Login untuk ikut mengobrol…</span><Link href="/auth/login?next=/chat" className="btn pri sm">Login</Link></div>
        )}
        <p className="muted text-[10.5px]">Emoji whitelist aktif · pesan disimpan 3 hari · word-filter & anti-spam aktif (5 pesan/10 dtk)</p>
      </div>

      {reportFor !== null && (
        <div className="modal-bg" onClick={() => setReportFor(null)}>
          <form className="card w modal" onClick={(e) => e.stopPropagation()} onSubmit={(e) => { e.preventDefault(); const fd = new FormData(e.currentTarget); const id = reportFor; setReportFor(null); act(async () => { const r = await reportChatAction(id, String(fd.get("reason")), String(fd.get("desc") ?? "")); if (r.ok) setToast({ text: "Laporan terkirim. Terima kasih sudah menjaga komunitas." }); return r; }); }}>
            <h3 className="text-[15px] font-bold">Laporkan pesan</h3>
            <label className="label">Alasan (wajib)</label>
            <select name="reason" className="input" required><option value="spam">Spam</option><option value="harassment">Pelecehan</option><option value="nsfw">NSFW</option><option value="provocation">Provokasi</option><option value="other">Lainnya</option></select>
            <label className="label">Deskripsi (opsional)</label>
            <textarea name="desc" className="input" rows={2} maxLength={300} />
            <div className="flex gap-2 justify-end"><button type="button" className="btn ghost" onClick={() => setReportFor(null)}>Batal</button><button className="btn pri">Kirim Laporan</button></div>
          </form>
        </div>
      )}
    </div>
  );
}
