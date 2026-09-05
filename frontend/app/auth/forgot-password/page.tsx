import { ForgotPasswordForm } from "@/components/AuthForms";
import Logo from "@/components/Logo";

export const dynamic = "force-dynamic";

export const metadata = { title: "Lupa Password — JKT48Verse" };

export default async function ForgotPasswordPage({ searchParams }: { searchParams: Promise<{ email?: string }> }) {
  const { email } = await searchParams;
  return (
    <div className="max-w-[420px] mx-auto mt-6">
      <div className="card w">
        <div className="flex items-center gap-3 mb-2">
          <Logo size={34} />
          <div>
            <div className="font-bold text-[15px]">Lupa Password</div>
            <div className="muted text-[11.5px]">Reset lewat kode OTP email</div>
          </div>
        </div>
        <p className="muted text-[12.5px] mb-3">Masukkan email akun JKT48Verse-mu. Kami akan mengirimkan kode OTP 6 digit untuk mengatur ulang password.</p>
        <ForgotPasswordForm email={email} />
      </div>
    </div>
  );
}
