import { ResetPasswordOtpForm, ResetPasswordTokenForm } from "@/components/AuthForms";
import Logo from "@/components/Logo";

export const dynamic = "force-dynamic";

export const metadata = { title: "Reset Password - JKT48Verse" };

/** Dua mode:
 * - `?token=...`  → link dari email (alur forgot-password link, berlaku 1 jam)
 * - tanpa token   → alur OTP 6 digit (`?email=` & `?dev=` opsional, dari halaman lupa password)
 */
export default async function ResetPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string; email?: string; dev?: string }>;
}) {
  const { token, email, dev } = await searchParams;
  return (
    <div className="max-w-[420px] mx-auto mt-6">
      <div className="card w">
        <div className="flex items-center gap-3">
          <Logo size={34} />
          <div>
            <div className="font-bold text-[15px]">Reset password</div>
            <div className="muted text-[11.5px]">
              {token ? "Pakai link dari email" : "Pakai kode OTP email"}
            </div>
          </div>
        </div>
        {token ? (
          <>
            <p className="muted text-[12.5px] mb-3">Buat password baru untuk akunmu. Setelah berhasil, semua perangkat lain akan otomatis logout.</p>
            <ResetPasswordTokenForm token={token} />
          </>
        ) : (
          <>
            <p className="muted text-[12.5px] mb-3">Masukkan kode 6 digit yang dikirim ke email-mu beserta password baru. Kode berlaku 10 menit.</p>
            <ResetPasswordOtpForm email={email} devCode={dev} />
          </>
        )}
      </div>
    </div>
  );
}
