import Link from "next/link";
import { Empty } from "@/components/ui";
export default function NotFound() {
  return <div className="card max-w-[520px] mx-auto mt-10"><Empty icon="search" title="Halaman tidak ditemukan" hint="Tautan mungkin sudah berubah atau dihapus." action={<Link href="/" className="btn pri sm">Ke Dashboard</Link>} /></div>;
}
