import Link from "next/link";
import { redirect } from "next/navigation";
import { PageHead } from "@/components/ui";
import { getViewer } from "@/lib/auth";
import { logoutAction, updateSettingsAction } from "@/app/actions";
export const dynamic = "force-dynamic";
const NOTIF = [["LIVE_ALERT", "Live Alert", "Oshi mulai live"], ["SCHEDULE_REMINDER", "Schedule Reminder", "30 & 5 menit sebelum acara"], ["BIRTHDAY_ALERT", "Birthday Alert", "Oshi ulang tahun (00:05 WIB)"], ["NEWS_ALERT", "News Alert", "Berita kategori langganan"], ["CHAT_MENTION", "Chat Mention", "@username disebut"]];
export default async function SettingsPage() {
  const v = await getViewer();
  if (!v.userId || !v.user) redirect("/auth/login?next=/account/settings");
  const u = v.user;
  const Row = ({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) => (<div className="flex items-center justify-between gap-4 py-3 border-b border-border last:border-0"><div><div className="text-[13px] font-semibold">{label}</div>{hint && <div className="muted text-[11.5px]">{hint}</div>}</div><div>{children}</div></div>);
  return (
    <>
      <PageHead title="Settings" right={<Link href="/account" className="btn ghost sm">‹ Akun</Link>} />
      <form action={async (fd) => { "use server"; await updateSettingsAction(fd); }} className="card w max-w-[720px]">
        <Row label="Bahasa" hint="id (default) / en"><select name="lang" defaultValue={u.lang} className="input"><option value="id">Indonesia</option><option value="en">English</option></select></Row>
        <Row label="Tema" hint="system mengikuti prefers-color-scheme"><select name="theme" defaultValue={u.theme} className="input"><option value="light">Light</option><option value="dark">Dark</option><option value="system">System</option></select></Row>
        <Row label="Multi-Live layout"><select name="multiLiveLayout" defaultValue={u.multiLiveLayout} className="input"><option value="row-2">row-2</option><option value="row-3">row-3</option></select></Row>
        <div className="pt-3"><div className="text-[11px] uppercase font-bold muted">Notifikasi</div></div>
        {NOTIF.map(([k, l, h]) => (<Row key={k} label={l} hint={h}><input type="checkbox" name={k} defaultChecked={u.notifPrefs?.[k] !== false} className="w-5 h-5 accent-[var(--primary)]" /></Row>))}
        <div className="pt-3"><div className="text-[11px] uppercase font-bold muted">Privasi</div></div>
        <Row label="Profil privat" hint="Hanya username + avatar default yang terlihat"><input type="checkbox" name="isPrivate" defaultChecked={u.isPrivate} className="w-5 h-5 accent-[var(--primary)]" /></Row>
        <Row label="Sembunyikan oshi"><input type="checkbox" name="hideOshi" defaultChecked={u.hideOshi} className="w-5 h-5 accent-[var(--primary)]" /></Row>
        <div className="flex gap-2 pt-2"><button className="btn pri">Simpan Pengaturan</button></div>
      </form>
      <div className="card w max-w-[720px] mt-3.5">
        <h3 className="text-[13.5px] font-bold">Sesi</h3>
        <div className="flex gap-2 flex-wrap"><form action={async () => { "use server"; await logoutAction(false); }}><button className="btn ghost sm">Keluar sesi ini</button></form><form action={async () => { "use server"; await logoutAction(true); }}><button className="btn pri sm">Keluar semua sesi</button></form></div>
      </div>
    </>
  );
}
