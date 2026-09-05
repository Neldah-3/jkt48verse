import { ResetPasswordForm } from "@/components/AuthForms";
import Logo from "@/components/Logo";

export const dynamic = "force-dynamic";

export const metadata = { title: "Reset Password — JKT48Verse" };

export default async function ResetPasswordPage({ searchParams }: { searchParams: Promise<{ email?: string; dev?: string }> }) {
  const { email, dev } = await searchParams;
  return (
    <div className="max-w-[420px] mx-auto mt-6">
      <div className="card w">
        <div className="flex items-center gap-3 mb-2">
          <Logo size={34} />
          <div>
            <div className="font-bold text-[15px]">Reset Password</div>
            <div className="muted text-[11.5px]">Masukkan kode OTP & password baru</div>
          </div>
        </div>
        <p className="muted text-[12.5px] mb-3">Masukkan kode 6 digit yang dikirim ke email-mu (berlaku 10 menit), lalu atur password baru.</p>
        <ResetPasswordForm email={email} devCode={dev} />
      </div>
    </div>
  );
}
