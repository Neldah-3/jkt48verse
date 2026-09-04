import Link from "next/link";
import { redirect } from "next/navigation";
import { Avatar, Disclaimer, Icon, PageHead, Tag } from "@/components/ui";
import { getViewer } from "@/lib/auth";
import { listMembers, userOshiList } from "@/lib/data";
import { setOshiAction, updateProfileAction } from "@/app/actions";
import { db } from "@/db";
import { activityLogs, gameScores } from "@/db/schema";
import { count, eq, sql } from "drizzle-orm";
export const dynamic = "force-dynamic";

export default async function AccountPage() {
  const v = await getViewer();
  if (!v.userId || !v.user) redirect("/auth/login?next=/account");
  const [oshi, members, [g], [a]] = await Promise.all([userOshiList(v.userId), listMembers({ status: "active" }), db.select({ n: count(), total: sql<number>`coalesce(sum(${gameScores.score}),0)::int` }).from(gameScores).where(eq(gameScores.userId, v.userId)), db.select({ n: count() }).from(activityLogs).where(eq(activityLogs.userId, v.userId))]);
  const kami = oshi.find((o) => o.rank === 0);
  const others = oshi.filter((o) => o.rank > 0);
  return (
    <>
      <PageHead title="Akun Saya" right={<><Link href="/account/settings" className="btn ghost sm"><Icon name="settings" size={14} /> Settings</Link><Link href="/account/activity" className="btn ghost sm"><Icon name="clock" size={14} /> Activity</Link></>} />
      <div className="grid12">
        <div className="c8 flex flex-col gap-3.5">
          <div className="card w">
            <div className="flex items-center gap-4"><Avatar name={v.username} size={72} seed={v.user.avatarSeed} /><div className="flex-1"><div className="flex items-center gap-2"><h2 className="text-[18px] font-extrabold">{v.username}</h2><span className="tag t-gray">{v.role}</span>{v.user.isPrivate && <span className="tag t-warn">🔒 Profil privat</span>}</div><p className="muted text-[13px]">{v.user.bio || "Belum ada bio."}</p><div className="flex gap-1.5 mt-1 flex-wrap">{(v.user.points > 0) && <span className="chip on">🎮 Pemain</span>}{v.user.streak >= 3 && <span className="chip on">🔥 Streak {v.user.streak}</span>}{v.user.points >= 1000 && <span className="chip on">💎 1.000 Poin</span>}</div></div></div>
            <form action={async (fd) => { "use server"; await updateProfileAction(fd); }} className="grid sm:grid-cols-[1fr_auto] gap-3 items-end border-t border-border pt-3">
              <div><label className="label">Bio (maks 160)</label><input name="bio" defaultValue={v.user.bio ?? ""} maxLength={160} className="input" /></div>
              <div><label className="label">Warna avatar</label><select name="avatarSeed" defaultValue={v.user.avatarSeed} className="input">{[1, 2, 3, 4, 5, 6].map((i) => <option key={i} value={i}>Gradien {i}</option>)}</select></div>
              <button className="btn pri sm sm:col-span-2 justify-self-start">Simpan Profil</button>
            </form>
          </div>
          <div className="card w">
            <div className="w-head"><h3>Kartu Oshi</h3><span className="muted text-[11px]">1 kami-oshi + hingga 5 oshi</span></div>
            <div className="flex flex-wrap gap-3 items-center">
              {kami ? <Link href={`/member/${kami.m.slug}`} className="flex items-center gap-2 rounded-[12px] p-2 pr-3" style={{ background: "var(--primary-soft)" }}><Avatar name={kami.m.name} size={44} /><div><span className="tag t-red">Kami-oshi</span><div className="font-bold text-[13px]">{kami.m.name}</div></div></Link> : <p className="muted text-[12.5px]">Belum memilih kami-oshi.</p>}
              <div className="flex -space-x-2">{others.map((o) => (<Link key={o.m.id} href={`/member/${o.m.slug}`} title={o.m.name}><Avatar name={o.m.name} size={36} className="border-2 border-surface" /></Link>))}</div>
            </div>
            <form action={async (fd) => { "use server"; await setOshiAction(fd); }} className="grid sm:grid-cols-2 gap-3 border-t border-border pt-3">
              <div><label className="label">Kami-oshi</label><select name="kami" defaultValue={kami?.m.id ?? ""} className="input"><option value="">— pilih —</option>{members.map((m) => <option key={m.id} value={m.id}>{m.name} (Gen {m.generation ?? "-"})</option>)}</select></div>
              <div><label className="label">Oshi pendukung (Ctrl/⌘ + klik, maks 5)</label><select name="oshi" multiple defaultValue={others.map((o) => String(o.m.id))} className="input h-[120px]">{members.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</select></div>
              <button className="btn pri sm justify-self-start">Simpan Oshi</button>
            </form>
            <p className="muted text-[11px]">Live Alert & Birthday Alert merujuk ke seluruh oshi-mu.</p>
          </div>
        </div>
        <div className="c4 flex flex-col gap-3.5">
          <div className="card w stat"><div className="lbl"><Icon name="trophy" size={13} /> Total poin</div><div className="num tabular">{v.user.points.toLocaleString("id-ID")}</div><div className="muted text-[11.5px]">{g.n} sesi game · streak 🔥 {v.user.streak} hari</div></div>
          <div className="card w stat"><div className="lbl"><Icon name="zap" size={13} /> Interaksi</div><div className="num tabular">{a.n}</div><Link href="/account/activity" className="link">Lihat riwayat ›</Link></div>
          <div className="card w"><h3 className="text-[13px] font-bold">Status akun</h3><div className="flex flex-col gap-1 text-[12.5px]"><span>Role: <Tag kind="status" value={v.role.toLowerCase()} /></span>{v.isMuted && <span className="text-warn">Di-mute hingga {v.user.mutedUntil?.toLocaleString("id-ID", { timeZone: "Asia/Jakarta" })} WIB</span>}{!v.isMuted && !v.isBlocked && <span style={{ color: "var(--ok)" }}>Aktif · tidak ada sanksi</span>}</div></div>
        </div>
      </div>
      <Disclaimer />
    </>
  );
}
