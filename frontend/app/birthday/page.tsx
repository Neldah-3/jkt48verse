import Link from "next/link";
import Logo from "@/components/Logo";
import { Avatar, Disclaimer, Empty, GenChips, Icon, PageHead, Tag } from "@/components/ui";
import { Countdown, WishForm } from "@/components/BirthdayBits";
import { birthdayThisWeek, birthdayToday, birthdaysInMonth, wishesFor } from "@/lib/data";
import { getViewer } from "@/lib/auth";
import { ageFrom, dayName, fmtTime, monthName, wibParts } from "@/lib/time";

export const dynamic = "force-dynamic";

export default async function BirthdayPage({ searchParams }: { searchParams: Promise<{ tab?: string; month?: string; gen?: string; status?: string }> }) {
  const sp = await searchParams;
  const tab = sp.tab ?? "today";
  const now = wibParts(new Date());
  const v = await getViewer();
  const month = Number(sp.month ?? now.month);
  const [today, week, inMonth] = await Promise.all([birthdayToday(), birthdayThisWeek(), birthdaysInMonth(month)]);
  const wishes = today.length ? await wishesFor(today[0].id, now.year) : [];
  const calRows = inMonth.filter((m) => (!sp.gen || m.generation === Number(sp.gen)) && (!sp.status || m.status === sp.status));

  return (
    <>
      <PageHead title="Birthday" sub="Perayaan ulang tahun member · kalender WIB" right={
        <div className="seg">{[["today", "Today"], ["week", "This Week"], ["calendar", "Calendar"]].map(([k, l]) => (<Link key={k} href={`/birthday?tab=${k}`}><button className={tab === k ? "on" : ""}>{l}</button></Link>))}</div>
      } />

      {tab === "today" && (
        <div className="grid12">
          <div className="c8 flex flex-col gap-3.5">
            {today.length === 0 && <div className="card"><Empty icon="gift" title="Tidak ada yang berulang tahun hari ini" hint="Cek tab This Week untuk yang akan datang." action={<Link href="/birthday?tab=week" className="btn ghost sm">Lihat minggu ini</Link>} /></div>}
            {today.map((m) => (
              <div key={m.id} className="flex flex-col gap-3.5">
                <div className="bday flex items-center gap-4 flex-wrap">
                  <Avatar name={m.name} size={64} />
                  <div className="flex-1 min-w-0">
                    <span className="tag t-warn">🎂 Hari ini</span>
                    <h2 className="text-[19px] font-extrabold mt-1">{m.name}</h2>
                    <p className="muted text-[12.5px]">@{m.nickname} · Gen {m.generation ?? "-"} · {m.birthDate ? `${ageFrom(m.birthDate)} tahun` : ""} <Tag kind="status" value={m.status} /></p>
                  </div>
                  <Link href={`/member/${m.slug}`} className="btn ghost sm">Profil</Link>
                </div>
                <div className="card w">
                  <div className="flex items-center gap-2"><Logo size={28} /><b className="text-[13px]">Ucapan dari JKT48Verse</b><span className="tag t-gray ml-auto">Sistem</span></div>
                  <p className="text-[13.5px] italic">“Selamat ulang tahun, {m.nickname}! Semoga tahun ini penuh panggung yang bersinar, kesehatan, dan kebahagiaan. Terima kasih sudah selalu memberi energi untuk kami semua. 🎉”</p>
                </div>
                <div className="card w">
                  <div className="w-head"><h3>Kirim Ucapan untuk {m.nickname}</h3><span className="muted text-[11px]">{wishes.length} ucapan</span></div>
                  {v.userId ? <WishForm memberId={m.id} memberName={m.nickname} /> : <div className="flex items-center gap-3 rounded-[11px] border border-border-2 bg-surface-2 px-3 py-2"><span className="muted text-[13px] flex-1">Login untuk mengirim ucapan (maks 200 karakter)</span><Link href="/auth/login?next=/birthday" className="btn pri sm">Login</Link></div>}
                  <div className="flex flex-col gap-2 mt-2">{wishes.map((w) => (<div key={w.id} className="flex gap-2"><Avatar name={w.username} size={26} /><div className="bubble flex-1"><b className="text-[12px]">{w.username}</b> <span className="muted text-[10.5px]">{fmtTime(w.createdAt)}</span><div>{w.message}</div></div></div>))}</div>
                </div>
              </div>
            ))}
          </div>
          <div className="c4 card w self-start">
            <div className="w-head"><h3>Berikutnya minggu ini</h3><Link href="/birthday?tab=week">Semua ›</Link></div>
            {week.flatMap((d) => d.members.map((m) => ({ ...m, d }))).filter((m) => m.d.key > `${now.year}-${String(now.month).padStart(2, "0")}-${String(now.day).padStart(2, "0")}`).slice(0, 5).map((m) => (
              <Link key={m.id} href={`/member/${m.slug}`} className="row items-center"><Avatar name={m.name} size={30} /><div className="flex-1"><div className="text-[13px] font-semibold">{m.name}</div><div className="muted text-[11px]">{dayName(m.d.date.getUTCDay() === 6 ? 0 : (m.d.date.getUTCDay() + 1) % 7)} · {m.d.day} {monthName(m.d.month)}</div></div></Link>
            ))}
            <div className="border-t border-border pt-3 text-center"><p className="muted text-[11px] mb-1">Menuju 00:00 WIB</p><Countdown /></div>
          </div>
        </div>
      )}

      {tab === "week" && (
        <div className="grid12">
          <div className="c8 card w">
            <div className="w-head"><h3>Senin – Minggu (WIB)</h3></div>
            {week.map((d, i) => (
              <div key={d.key} className="row items-center">
                <div className="timebox"><b>{d.day}</b><span>{["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"][i]}</span></div>
                <div className="flex-1 flex flex-wrap gap-2">
                  {d.members.length === 0 && <span className="muted text-[12px]">—</span>}
                  {d.members.map((m) => (<Link key={m.id} href={`/member/${m.slug}`} className="chip"><Avatar name={m.name} size={18} /> {m.name}{d.key === `${now.year}-${String(now.month).padStart(2, "0")}-${String(now.day).padStart(2, "0")}` && " 🎂"}</Link>))}
                </div>
              </div>
            ))}
          </div>
          <div className="c4 card w text-center self-start"><p className="muted text-[11.5px]">Countdown ke 00:00 WIB</p><Countdown /><p className="muted text-[11px]">Daftar diperbarui setiap pergantian hari WIB.</p></div>
        </div>
      )}

      {tab === "calendar" && (
        <div className="card w">
          <div className="w-head">
            <Link href={`/birthday?tab=calendar&month=${month === 1 ? 12 : month - 1}`} className="btn icon ghost"><Icon name="chevronL" size={16} /></Link>
            <h3>{monthName(month)}</h3>
            <Link href={`/birthday?tab=calendar&month=${month === 12 ? 1 : month + 1}`} className="btn icon ghost"><Icon name="chevron" size={16} /></Link>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href={`/birthday?tab=calendar&month=${month}`} className={`chip ${!sp.gen && !sp.status ? "on" : ""}`}>Semua</Link>
            <GenChips current={sp.gen ? Number(sp.gen) : undefined} base={`/birthday?tab=calendar&month=${month}&`} />
            <Link href={`/birthday?tab=calendar&month=${month}&status=graduated`} className={`chip ${sp.status === "graduated" ? "on" : ""}`}>Lulusan</Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {calRows.length === 0 && <p className="muted text-[12.5px] col-span-full">Tidak ada member berulang tahun di bulan ini untuk filter tersebut.</p>}
            {calRows.map((m) => (<Link key={m.id} href={`/member/${m.slug}`} className="flex items-center gap-3 rounded-[11px] border border-border p-2 hover:bg-surface-2"><div className="timebox" style={{ width: 46 }}><b>{Number(m.birthDate!.split("-")[2])}</b><span>{monthName(month).slice(0, 3)}</span></div><Avatar name={m.name} size={30} /><div className="min-w-0"><div className="text-[13px] font-semibold truncate">{m.name}</div><div className="muted text-[11px]">Gen {m.generation ?? "-"} · <Tag kind="status" value={m.status} /></div></div></Link>))}
          </div>
        </div>
      )}
      <Disclaimer />
    </>
  );
}
