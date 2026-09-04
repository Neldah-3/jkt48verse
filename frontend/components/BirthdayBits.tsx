"use client";

import { useEffect, useState, useTransition } from "react";
import { sendWishAction } from "@/app/actions";
import { Icon } from "@/components/ui";

export function Countdown() {
  const [left, setLeft] = useState("--:--:--");
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      const wib = new Date(now.getTime() + 7 * 3600_000);
      const secs = 86400 - (wib.getUTCHours() * 3600 + wib.getUTCMinutes() * 60 + wib.getUTCSeconds());
      const h = Math.floor(secs / 3600), m = Math.floor((secs % 3600) / 60), s = secs % 60;
      setLeft(`${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`);
    };
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, []);
  return <span className="tabular font-bold text-[18px]">{left}</span>;
}

export function WishForm({ memberId, memberName }: { memberId: number; memberName: string }) {
  const [text, setText] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string; code?: string } | null>(null);
  const [pending, start] = useTransition();
  return (
    <form className="flex flex-col gap-2" onSubmit={(e) => { e.preventDefault(); start(async () => { const r = await sendWishAction(memberId, text); if (r.ok) { setText(""); setMsg({ ok: true, text: `Ucapan untuk ${memberName} terkirim! 🎉` }); } else setMsg({ ok: false, text: r.error, code: r.code }); }); }}>
      <div className="relative">
        <textarea value={text} onChange={(e) => setText(e.target.value.slice(0, 200))} className="input min-h-[74px] resize-none" placeholder={`Tulis ucapan untuk ${memberName}…`} />
        <span className="absolute right-3 bottom-2 muted text-[10.5px] tabular">{text.length}/200</span>
      </div>
      <div className="flex items-center gap-2"><button className="btn pri sm" disabled={pending || !text.trim()}><Icon name="send" size={14} /> Kirim Ucapan</button><span className="muted text-[11px]">1 ucapan / member / tahun</span></div>
      {msg && <div className={`text-[12.5px] rounded-[9px] px-3 py-2 ${msg.ok ? "bg-ok-soft text-ok" : "bg-primary-soft text-primary"}`}>{msg.text} {msg.code && <code className="text-[10.5px] opacity-70">{msg.code}</code>}</div>}
    </form>
  );
}
