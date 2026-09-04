"use client";
import { useRef, useState } from "react";
import { Icon } from "@/components/ui";

export function ShareCard({ quote, author, template, date }: { quote: string; author: string; template: string; date: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [tpl, setTpl] = useState(template);
  const [msg, setMsg] = useState<string | null>(null);
  const download = () => {
    const w = 1080, h = 1080;
    const c = document.createElement("canvas"); c.width = w; c.height = h;
    const ctx = c.getContext("2d")!;
    const g = ctx.createLinearGradient(0, 0, w, h);
    if (tpl === "minimal") { g.addColorStop(0, "#ffffff"); g.addColorStop(1, "#f6f7f9"); } else if (tpl === "dark-elegant") { g.addColorStop(0, "#1d2333"); g.addColorStop(1, "#0f1220"); } else { g.addColorStop(0, "#ff4d6d"); g.addColorStop(0.55, "#d90429"); g.addColorStop(1, "#8f0b1f"); }
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = tpl === "minimal" ? "#141821" : "#ffffff";
    ctx.font = "bold 52px system-ui, sans-serif";
    const words = quote.split(" "); const lines: string[] = []; let line = "";
    for (const wd of words) { const t = line ? `${line} ${wd}` : wd; if (ctx.measureText(t).width > w - 200) { lines.push(line); line = wd; } else line = t; }
    lines.push(line);
    const startY = h / 2 - (lines.length * 66) / 2;
    lines.forEach((l, i) => ctx.fillText(l, 100, startY + i * 66));
    ctx.font = "500 30px system-ui, sans-serif"; ctx.globalAlpha = 0.85;
    ctx.fillText(`— ${author}`, 100, startY + lines.length * 66 + 40);
    ctx.font = "600 24px system-ui, sans-serif"; ctx.fillText(`JKT48Verse · ${date}`, 100, h - 90);
    const a = document.createElement("a"); a.download = "jkt48verse-motivation.png"; a.href = c.toDataURL("image/png"); a.click();
  };
  const share = async () => { const text = `“${quote}” — ${author}\n(JKT48Verse)`; if (navigator.share) { try { await navigator.share({ text }); return; } catch { /* */ } } await navigator.clipboard.writeText(text); setMsg("Teks disalin ke clipboard."); };
  return (
    <div className="card w">
      <div ref={ref} className={`mcard ${tpl}`}>
        <div className="text-[10.5px] uppercase tracking-widest opacity-75">Pesan Harian · {date}</div>
        <p className="text-[22px] sm:text-[26px] font-extrabold leading-snug" style={{ letterSpacing: "-0.4px" }}>“{quote}”</p>
        <div className="flex items-center justify-between"><span className="text-[13px] font-semibold opacity-90">— {author}</span><span className="text-[11px] opacity-70">JKT48Verse</span></div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <div className="seg">{["jkt48-red-white", "minimal", "dark-elegant"].map((t) => (<button key={t} className={tpl === t ? "on" : ""} onClick={() => setTpl(t)}>{t}</button>))}</div>
        <span className="flex-1" />
        <button className="btn pri sm" onClick={download}><Icon name="zap" size={14} /> Unduh PNG</button>
        <button className="btn ghost sm" onClick={share}><Icon name="send" size={14} /> Bagikan</button>
      </div>
      {msg && <p className="text-[12px]" style={{ color: "var(--ok)" }}>{msg}</p>}
    </div>
  );
}
