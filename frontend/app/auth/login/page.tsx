import { LoginForm } from "@/components/AuthForms";
import Logo from "@/components/Logo";
export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string; verified?: string; reset?: string }> }) {
  const { next, verified, reset } = await searchParams;
  return (
    <div className="max-w-[400px] mx-auto mt-6">
      <div className="card w">
        <div className="flex items-center gap-3"><Logo size={34} /><div><div className="font-bold text-[15px]">Masuk ke JKT48Verse</div><div className="muted text-[11.5px]">Fan-made Platform</div></div></div>
        {verified && <p className="text-[12.5px] mb-2" style={{ color: "var(--ok, #16a34a)" }}>Email berhasil diverifikasi. Silakan login.</p>}
        {reset && <p className="text-[12.5px] mb-2" style={{ color: "var(--ok, #16a34a)" }}>Password berhasil direset. Silakan login dengan password baru.</p>}
        <LoginForm next={next} />
      </div>
    </div>
  );
}
