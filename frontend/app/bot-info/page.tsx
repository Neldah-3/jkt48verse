import { Disclaimer, PageHead } from "@/components/ui";
export default function BotInfoPage() {
  return (<><PageHead title="Bot Info" /><div className="card w article"><h2>Identitas</h2><p>Bot <b>JKT48Verse Live Watcher</b> (User-Agent: <code>JKT48Verse fan project</code>) membaca daftar siaran publik Showroom untuk menampilkan status live member.</p><h2>Tujuan & Etika</h2><ul><li>Hanya mengakses endpoint publik, tanpa login atau bypass.</li><li>Interval minimal 60 detik dan menghormati batas server.</li><li>Tidak menyimpan file media; hanya metadata siaran (judul, waktu mulai, jumlah penonton).</li></ul><h2>Kontak</h2><p>Hubungi kontributor melalui halaman Contributors untuk permintaan penghentian akses.</p></div><Disclaimer /></>);
}
