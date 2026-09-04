"use client";
import { useState, useTransition } from "react";
import { Icon } from "@/components/ui";
import { resolveReportAction, sanctionUserAction } from "@/app/actions";

export function ReportActions({ reportId }: { reportId: number }) {
  const [pending, start] = useTransition();
  return (<span className="flex gap-1.5"><button className="btn ghost sm" disabled={pending} onClick={() => start(async () => { await resolveReportAction(reportId, "rejected"); })}>Tolak</button><button className="btn pri sm" disabled={pending} onClick={() => start(async () => { await resolveReportAction(reportId, "approved"); })}>Setujui</button></span>);
}

export function SanctionButton({ userId, username, role, moderator }: { userId: number; username: string; role: string; moderator?: boolean }) {
  const [open, setOpen] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const disabled = moderator && role !== "MEMBER";
  return (
    <>
      <button className="btn pri sm" disabled={disabled} onClick={() => setOpen(true)} title={disabled ? "Moderator hanya bisa menindak MEMBER" : ""}>Tindak</button>
      {open && (
        <div className="modal-bg" onClick={() => setOpen(false)}>
          <form className="card w modal" onClick={(e) => e.stopPropagation()} onSubmit={(e) => { e.preventDefault(); const fd = new FormData(e.currentTarget); start(async () => { const r = await sanctionUserAction(fd); if (r.ok) setOpen(false); else setErr(r.error); }); }}>
            <h3 className="text-[15px] font-bold">Tindak akun @{username}</h3>
            <input type="hidden" name="userId" value={userId} />
            <label className="label">Jenis</label>
            <select name="kind" className="input"><option value="mute">Mute chat</option><option value="block">Blokir akun</option><option value="unblock">Cabut sanksi</option></select>
            <label className="label">Durasi</label>
            <select name="duration" className="input"><option value="1">1 jam</option><option value="24">24 jam (1 hari)</option><option value="168">7 hari</option><option value="720">30 hari</option>{!moderator && <option value="permanent">Permanen</option>}</select>
            <label className="label">Alasan (wajib, tampil ke user)</label>
            <textarea name="reason" className="input" rows={2} required />
            {moderator && <p className="muted text-[11px]">Ban permanen memerlukan approval Admin · wajib sertakan bukti (link pesan).</p>}
            {err && <p className="text-primary text-[12.5px]">{err}</p>}
            <div className="flex gap-2 justify-end"><button type="button" className="btn ghost" onClick={() => setOpen(false)}>Batal</button><button className="btn pri" disabled={pending}><Icon name="shield" size={14} /> Terapkan</button></div>
          </form>
        </div>
      )}
    </>
  );
}
