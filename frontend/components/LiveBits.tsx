"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Avatar, Icon } from "@/components/ui";
import { fmtDuration } from "@/lib/time";

export function LiveDuration({ startedAt }: { startedAt: string }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const secs = Math.max(0, (now - new Date(startedAt).getTime()) / 1000);
  return <span className="muted text-[11px] font-semibold tabular">{fmtDuration(secs)}</span>;
}

export type LiveItem = { id: number; memberName: string; slug?: string; platform: string; title: string; startedAt: string; viewers: number | null; imageUrl: string | null; streamUrl: string | null; roomKey: string | null };

function Player({ item, compact, onRemove, registerVideo }: { item: LiveItem | null; compact?: boolean; onRemove?: () => void; registerVideo?: (el: HTMLVideoElement | null) => void }) {
  const ref = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [canPip, setCanPip] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setCanPip(typeof document !== "undefined" && "pictureInPictureEnabled" in document && document.pictureInPictureEnabled);
    registerVideo?.(ref.current);
    return () => registerVideo?.(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item?.id]);

  const play = async () => {
    const el = ref.current;
    if (!el || !item?.streamUrl) return;
    setErr(null);
    try {
      if (el.canPlayType("application/vnd.apple.mpegurl")) {
        el.src = item.streamUrl;
      } else {
        const mod = await import("hls.js");
        const Hls = mod.default;
        if (Hls.isSupported()) {
          const hls = new Hls();
          hls.loadSource(item.streamUrl);
          hls.attachMedia(el);
          hls.on(Hls.Events.ERROR, (_e: unknown, d: { fatal: boolean }) => { if (d.fatal) setErr("Stream tidak dapat dimuat (CORS/geo-block). Buka di platform asli."); });
        } else {
          el.src = item.streamUrl;
        }
      }
      await el.play();
      setPlaying(true);
    } catch {
      setErr("Tidak bisa memutar di browser ini. Buka di platform asli.");
    }
  };
  const stop = () => { const el = ref.current; if (el) { el.pause(); el.removeAttribute("src"); el.load(); } setPlaying(false); };
  const fs = () => { const el = ref.current?.parentElement; el?.requestFullscreen?.(); };
  const pip = async () => { try { await ref.current?.requestPictureInPicture(); } catch { /* ignore */ } };
  const external = item?.platform === "showroom" && item.roomKey ? `https://www.showroom-live.com/r/${item.roomKey}` : item?.streamUrl ?? "#";

  if (!item) {
    return (
      <div className={`player flex flex-col items-center justify-center gap-2 ${compact ? "rounded-[12px]" : ""}`}>
        <Icon name="radio" size={40} className="opacity-50" />
        <p className="text-[13px] opacity-80">Pilih member yang sedang live</p>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <div className={`player ${compact ? "rounded-[12px]" : ""}`}>
        {item.imageUrl && !playing && <img src={item.imageUrl} alt="" className="absolute inset-0 w-full h-full object-cover opacity-70" />}
        <video ref={ref} className="absolute inset-0 w-full h-full object-contain bg-black" style={{ display: playing ? "block" : "none" }} playsInline controls={false} />
        <span className="badge-live absolute left-3 top-3">LIVE</span>
        {onRemove && <button onClick={onRemove} className="absolute right-2 top-2 btn icon" style={{ background: "rgba(0,0,0,.45)", color: "#fff" }} aria-label="Hapus slot"><Icon name="x" size={15} /></button>}
        {!playing && (
          <button onClick={play} className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full flex items-center justify-center" style={{ width: compact ? 46 : 66, height: compact ? 46 : 66, background: "rgba(255,255,255,.18)", backdropFilter: "blur(6px)", border: "1px solid rgba(255,255,255,.35)" }} aria-label="Play">
            <Icon name="play" size={compact ? 20 : 28} />
          </button>
        )}
        <div className="absolute left-3 right-3 bottom-3 flex items-end justify-between gap-2">
          <div className="min-w-0">
            <div className={`font-bold truncate ${compact ? "text-[12px]" : "text-[14px]"}`}>{item.title}</div>
            <div className="text-[11px] opacity-85 flex items-center gap-2 flex-wrap">
              <span>{item.memberName}</span>·<span className="uppercase">{item.platform}</span>·<LiveDuration startedAt={item.startedAt} />·<span>{item.viewers != null ? `${item.viewers.toLocaleString("id-ID")} penonton` : "—"}</span>
            </div>
          </div>
        </div>
        {err && <div className="absolute inset-x-3 top-10 text-[11.5px] rounded-[8px] px-2 py-1" style={{ background: "rgba(0,0,0,.6)" }}>{err} <a href={external} target="_blank" rel="noreferrer" className="underline">Buka ↗</a></div>}
      </div>
      {!compact && (
        <div className="flex items-center gap-2 flex-wrap">
          {playing ? <button onClick={stop} className="btn pri sm"><Icon name="stop" size={15} /> Stop</button> : <button onClick={play} className="btn pri sm"><Icon name="play" size={15} /> Play</button>}
          <button onClick={() => { stop(); setTimeout(play, 200); }} className="btn ghost sm"><Icon name="refresh" size={15} /> Refresh</button>
          {canPip && <button onClick={pip} className="btn ghost sm" disabled={!playing}><Icon name="pip" size={15} /> PiP</button>}
          <button onClick={fs} className="btn ghost sm"><Icon name="fullscreen" size={15} /> Fullscreen</button>
          <span className="flex-1" />
          <a href={external} target="_blank" rel="noreferrer" className="btn ghost sm"><Icon name="external" size={15} /> Buka di {item.platform}</a>
        </div>
      )}
    </div>
  );
}

export default function LivePanel({ initial, watchId, defaultLayout }: { initial: LiveItem[]; watchId?: number; defaultLayout: string }) {
  const [live, setLive] = useState(initial);
  const [mainId, setMainId] = useState<number | null>(watchId ?? initial[0]?.id ?? null);
  const [slots, setSlots] = useState<(number | null)[]>(() => [initial[0]?.id ?? null, initial[1]?.id ?? null, null, null, null, null]);
  const [layout, setLayout] = useState(defaultLayout);
  const [picker, setPicker] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const videos = useRef<Map<number, HTMLVideoElement>>(new Map());

  useEffect(() => {
    const stored = localStorage.getItem("jv_multi_layout");
    if (stored && defaultLayout === "row-2") setLayout(stored);
  }, [defaultLayout]);

  const refresh = async () => {
    setLoading(true);
    try {
      const r = await fetch("/api/live?refresh=1");
      const j = (await r.json()) as { live: LiveItem[] };
      setLive(j.live);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    const t = setInterval(() => { fetch("/api/live").then((r) => r.json()).then((j: { live: LiveItem[] }) => setLive(j.live)).catch(() => {}); }, 60_000);
    return () => clearInterval(t);
  }, []);

  const main = live.find((l) => l.id === mainId) ?? null;
  const setL = (v: string) => { setLayout(v); localStorage.setItem("jv_multi_layout", v); };
  const cols = layout === "row-3" ? 3 : 2;

  return (
    <div className="grid12">
      <div className="c8 flex flex-col gap-3.5">
        <Player item={main} />
        <div className="card w">
          <div className="w-head"><h3>Sedang Live ({live.length})</h3><button onClick={refresh} className="btn ghost sm" disabled={loading}><Icon name="refresh" size={14} /> {loading ? "Memuat…" : "Refresh"}</button></div>
          {live.length === 0 && <p className="muted text-[12.5px]">Belum ada member JKT48 yang live di Showroom saat ini. Data diperbarui otomatis tiap menit.</p>}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {live.map((l) => (
              <button key={l.id} onClick={() => setMainId(l.id)} className={`flex items-center gap-3 rounded-[11px] border p-2 text-left ${mainId === l.id ? "border-primary bg-primary-soft" : "border-border hover:bg-surface-2"}`}>
                <div className="relative w-[72px] h-[46px] rounded-[8px] overflow-hidden flex-shrink-0 bg-surface-3">{l.imageUrl && <img src={l.imageUrl} alt="" className="w-full h-full object-cover" />}<span className="badge-live absolute left-1 top-1" style={{ fontSize: 8, padding: "1px 4px" }}>Live</span></div>
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] font-semibold truncate">{l.memberName}</div>
                  <div className="text-[11px] muted truncate">{l.title}</div>
                  <div className="flex items-center gap-2 mt-0.5"><span className={`tag ${l.platform === "idn" ? "t-info" : "t-red"}`}>{l.platform}</span><LiveDuration startedAt={l.startedAt} /><span className="muted text-[11px]">{l.viewers != null ? `${l.viewers.toLocaleString("id-ID")} 👀` : "—"}</span></div>
                </div>
                {l.slug && <Link href={`/member/${l.slug}`} className="btn icon ghost" onClick={(e) => e.stopPropagation()} aria-label="Profil"><Icon name="user" size={15} /></Link>}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="c4">
        <div className="card w">
          <div className="w-head"><h3>Multi Live</h3><span className="muted text-[11px]">maks 6 slot</span></div>
          <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0,1fr))` }}>
            {slots.map((sid, i) => {
              const it = sid ? live.find((l) => l.id === sid) ?? null : null;
              if (it) return <Player key={i} item={it} compact onRemove={() => setSlots((s) => s.map((x, j) => (j === i ? null : x)))} registerVideo={(el) => { if (el) videos.current.set(i, el); else videos.current.delete(i); }} />;
              return (
                <button key={i} className="slot empty" onClick={() => setPicker(i)}>
                  <Icon name="plus" size={18} />
                  <span>Pilih member live</span>
                </button>
              );
            })}
          </div>
          <div className="flex flex-wrap gap-2 items-center">
            <button className="btn ghost sm" onClick={() => videos.current.forEach((v) => v.play().catch(() => {}))}><Icon name="play" size={14} /> Play Semua</button>
            <button className="btn ghost sm" onClick={() => videos.current.forEach((v) => v.pause())}><Icon name="stop" size={14} /> Stop Semua</button>
            <button className="btn ghost sm" onClick={refresh}><Icon name="refresh" size={14} /> Refresh</button>
          </div>
          <div className="flex items-center gap-2"><span className="muted text-[11.5px]">Layout:</span><button className={`chip ${layout === "row-2" ? "on" : ""}`} onClick={() => setL("row-2")}>row-2</button><button className={`chip ${layout === "row-3" ? "on" : ""}`} onClick={() => setL("row-3")}>row-3</button></div>
          {picker !== null && (
            <div className="rounded-[11px] border border-border p-2 flex flex-col gap-1 max-h-[220px] overflow-y-auto">
              <div className="flex items-center justify-between px-1"><b className="text-[12px]">Pilih untuk slot {picker + 1}</b><button onClick={() => setPicker(null)} className="btn icon ghost" style={{ width: 26, height: 26 }}><Icon name="x" size={13} /></button></div>
              {live.filter((l) => !slots.includes(l.id)).map((l) => (
                <button key={l.id} onClick={() => { setSlots((s) => s.map((x, j) => (j === picker ? l.id : x))); setPicker(null); }} className="sb-item text-[12.5px]"><Avatar name={l.memberName} size={22} /> {l.memberName} <span className="tag t-gray ml-auto">{l.platform}</span></button>
              ))}
              {live.filter((l) => !slots.includes(l.id)).length === 0 && <p className="muted text-[12px] px-1 py-2">Semua yang live sudah ada di slot.</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
