import { LoginForm } from "@/components/AuthForms";
import Logo from "@/components/Logo";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string; reset?: string; verified?: string }>;
}) {
  const { next, reset, verified } = await searchParams;
  return (
    <div className="max-w-[400px] mx-auto mt-6">
      <div className="card w">
        <div className="flex items-center gap-3">
          <Logo size={34} />
          <div>
            <div className="font-bold text-[15px]">Masuk ke JKT48Verse</div>
            <div className="muted text-[11.5px]">Fan-made Platform</div>
          </div>
        </div>
        {reset && (
          <p className="text-[12.5px] mb-2" style={{ color: "var(--ok)" }}>
            ✅ Password berhasil direset. Silakan masuk dengan password barumu.
          </p>
        )}
        {verified && !reset && (
          <p className="text-[12.5px] mb-2" style={{ color: "var(--ok)" }}>
            ✅ Email terverifikasi. Silakan masuk.
          </p>
        )}
        <LoginForm next={next} />
      </div>
    </div>
  );
}
