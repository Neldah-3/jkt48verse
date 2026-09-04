import { VerifyOtpForm } from "@/components/AuthForms";

export const dynamic = "force-dynamic";

export default async function VerifyPage({ searchParams }: { searchParams: Promise<{ email?: string; dev?: string }> }) {
  const { email, dev } = await searchParams;
  return (
    <>
      <div className="card w max-w-[420px] mx-auto">
        <div className="w-head"><h3>Verifikasi Email (OTP)</h3></div>
        <p className="muted text-[12.5px] mb-3">Masukkan kode 6 digit yang dikirim ke email-mu. Kode berlaku 10 menit.</p>
        <VerifyOtpForm email={email} devCode={dev} />
      </div>
    </>
  );
}
