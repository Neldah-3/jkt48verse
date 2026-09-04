import { StaffLoginForm } from "@/components/AuthForms";
export const metadata = { robots: { index: false, follow: false } };
export default function AdminLoginPage() {
  return (
    <div className="dark max-w-[420px] mx-auto mt-6 text-text">
      <div className="card w" style={{ background: "#151a22", borderColor: "#232b38", color: "#eef1f6" }}>
        <div className="flex items-center gap-3"><span className="brand">jv</span><div><div className="font-bold text-[15px]">Panel Admin / Moderator</div><div className="text-[11.5px]" style={{ color: "#95a0b1" }}>Halaman internal — jangan dibagikan</div></div></div>
        <StaffLoginForm />
        <p className="text-[10.5px]" style={{ color: "#95a0b1" }}>Kredensial hanya tersimpan di server (3 Admin · 10 Moderator). Maks 5 percobaan / 15 menit.</p>
      </div>
    </div>
  );
}
