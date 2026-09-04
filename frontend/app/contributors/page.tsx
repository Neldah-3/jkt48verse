import { Avatar, Disclaimer, PageHead } from "@/components/ui";
import { db } from "@/db";
import { contributors } from "@/db/schema";
import { ready } from "@/lib/data";
export const dynamic = "force-dynamic";
export default async function ContributorsPage() {
  await ready();
  const rows = await db.select().from(contributors);
  return (<><PageHead title="Contributors" sub="Orang-orang di balik JKT48Verse" /><div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">{rows.map((c) => (<div key={c.id} className="card w"><div className="flex items-center gap-3"><Avatar name={c.name} size={44} /><div><b className="text-[14px]">{c.name}</b><div><span className="tag t-info">{c.role}</span></div></div></div><p className="muted text-[12.5px]">{c.contribution}</p></div>))}</div><div className="card w article mt-4"><h2>Hak Cipta & Atribusi</h2><p>JKT48Verse adalah proyek komunitas non-komersial dan tidak terafiliasi, disponsori, atau dioperasikan oleh JKT48 Operation Team. Nama JKT48, logo resmi, foto member, setlist, dan lagu adalah properti pemegang hak cipta resmi. Kode orisinal dan tulisan kontributor adalah milik komunitas.</p></div><Disclaimer /></>);
}
