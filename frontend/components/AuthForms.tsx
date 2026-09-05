"use client";
import Link from "next/link";
import { useState } from "react";
import { useFormState, useFormStatus } from "react-dom";
import { forgotPasswordOtpAction, loginAction, registerAction, resendOtpAction, resendResetOtpAction, resetPasswordOtpAction, resetPasswordTokenAction, staffLoginAction, verifyOtpAction, type ActionResult } from "@/app/actions";

const init: ActionResult = { ok: true };

/** Tombol submit yang tahu status pending form (React 18 / Next 14). */
function SubmitButton({ label, pendingLabel }: { label: string; pendingLabel: string }) {
  const { pending } = useFormStatus();
  return (
    <button className="btn pri" disabled={pending}>
      {pending ? pendingLabel : label}
    </button>
  );
}

export function LoginForm({ next }: { next?: string }) {
  const [state, action] = useFormState(loginAction, init);
  return (
    <form action={action} className="flex flex-col gap-3">
      <input type="hidden" name="next" value={next ?? "/"} />
      <div><label className="label">Username atau Email</label><input name="username" className="input" required autoComplete="username" /></div>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1"><label className="label">Password</label><input name="password" type="password" className="input" required autoComplete="current-password" /></div>
        <div className="flex-1 text-right self-end pb-1"><Link href="/auth/forgot-password" className="link text-[11.5px]">Lupa password?</Link></div>
      </div>
      <div>
        <label className="label">Code Akses <span className="muted">(khusus Admin/Moderator)</span></label>
        <input name="accessCode" className="input" autoComplete="off" spellCheck={false} />
        <p className="muted text-[10.5px] mt-1">Kosongkan bila kamu user biasa. Dibaca persis: besar/kecil huruf & karakter dihitung.</p>
      </div>
      <label className="flex items-center gap-2 text-[12.5px]"><input type="checkbox" name="remember" defaultChecked /> Ingat saya (30 hari)</label>
      {!state.ok && <p className="text-primary text-[12.5px]">{state.error}</p>}
      <SubmitButton label="Masuk" pendingLabel="Masuk…" />
      <p className="muted text-[12.5px] text-center">Belum punya akun? <Link href="/auth/register" className="link">Daftar</Link></p>
    </form>
  );
}

export function RegisterForm() {
  const [state, action] = useFormState(registerAction, init);
  return (
    <form action={action} className="flex flex-col gap-3">
      <div><label className="label">Username (3–20 alfanumerik)</label><input name="username" className="input" required pattern="[a-zA-Z0-9]{3,20}" autoComplete="username" /></div>
      <div><label className="label">Email</label><input name="email" type="email" className="input" required autoComplete="email" /></div>
      <div><label className="label">Password (min. 8 karakter)</label><input name="password" type="password" className="input" required minLength={8} autoComplete="new-password" /></div>
      {!state.ok && <p className="text-primary text-[12.5px]">{state.error}</p>}
      <SubmitButton label="Daftar" pendingLabel="Mendaftar…" />
      <p className="muted text-[11px]">Kode OTP verifikasi akan dikirim ke email-mu. Dengan mendaftar kamu menyetujui <Link href="/terms" className="link">Ketentuan</Link> & <Link href="/privacy" className="link">Privasi</Link>.</p>
      <p className="muted text-[12.5px] text-center">Sudah punya akun? <Link href="/auth/login" className="link">Masuk</Link> · <Link href="/auth/verify" className="link">Verifikasi OTP</Link></p>
    </form>
  );
}

export function StaffLoginForm() {
  const [state, action] = useFormState(staffLoginAction, init);
  return (
    <form action={action} className="flex flex-col gap-3">
      <div><label className="label">Username Staff</label><input name="username" className="input" required autoComplete="off" /></div>
      <div><label className="label">Password</label><input name="password" type="password" className="input" required autoComplete="off" /></div>
      <div>
        <label className="label">Code Akses</label>
        <input name="accessCode" className="input" required autoComplete="off" spellCheck={false} />
        <p className="muted text-[10.5px] mt-1">Dibaca persis: besar/kecil huruf, spasi, dan karakter dihitung.</p>
      </div>
      {!state.ok && <p className="text-primary text-[12.5px]">{state.error}</p>}
      <SubmitButton label="Masuk Panel" pendingLabel="Memverifikasi…" />
      <p className="muted text-[11px]">
        Login staff butuh username + password + code akses. Kalau salah satu kredensial di server tidak lengkap,
        akun otomatis nonaktif dan tidak bisa masuk.
      </p>
    </form>
  );
}

export function VerifyOtpForm({ email, devCode }: { email?: string; devCode?: string }) {
  const [state, action] = useFormState(verifyOtpAction, init);
  const [resending, setResending] = useState(false);
  const [resent, setResent] = useState<string | null>(null);
  return (
    <form action={action} className="flex flex-col gap-3">
      <div><label className="label">Email</label><input name="email" type="email" className="input" required defaultValue={email} autoComplete="email" /></div>
      <div><label className="label">Kode OTP (6 digit)</label><input name="code" className="input" required pattern="[0-9]{6}" maxLength={6} inputMode="numeric" autoComplete="one-time-code" /></div>
      {!state.ok && <p className="text-primary text-[12.5px]">{state.error}</p>}
      {devCode && <p className="text-[12.5px]" style={{ color: "var(--warn)" }}>Mode dev (RESEND belum diatur) — kode OTP kamu: <b>{devCode}</b></p>}
      <SubmitButton label="Verifikasi" pendingLabel="Memverifikasi…" />
      <button
        type="button"
        className="btn ghost sm"
        disabled={resending}
        onClick={async () => {
          const el = document.querySelector<HTMLInputElement>("input[name=email]");
          if (!el?.value) return;
          setResending(true);
          const r = await resendOtpAction(el.value);
          setResending(false);
          setResent(r.ok && r.data?.devCode ? `Kode dev baru: ${r.data.devCode}` : "Jika email terdaftar, kode OTP baru telah dikirim.");
        }}
      >
        {resending ? "Mengirim…" : "Kirim ulang kode"}
      </button>
      {resent && <p className="muted text-[12px]">{resent}</p>}
      <p className="muted text-[12.5px] text-center"><Link href="/auth/login" className="link">‹ Kembali ke login</Link></p>
    </form>
  );
}

export function ForgotPasswordForm({ email }: { email?: string }) {
  const [state, action] = useFormState(forgotPasswordOtpAction, init);
  return (
    <form action={action} className="flex flex-col gap-3">
      <div><label className="label">Email</label><input name="email" type="email" className="input" required defaultValue={email} autoComplete="email" /></div>
      {!state.ok && <p className="text-primary text-[12.5px]">{state.error}</p>}
      <SubmitButton label="Kirim kode OTP" pendingLabel="Mengirim…" />
      <p className="muted text-[11px]">Kode OTP 6 digit akan dikirim ke email-mu dan berlaku 10 menit. Cek juga folder spam bila email tidak muncul.</p>
      <p className="muted text-[12.5px] text-center"><Link href="/auth/login" className="link">‹ Kembali ke login</Link></p>
    </form>
  );
}

export function ResetPasswordOtpForm({ email, devCode }: { email?: string; devCode?: string }) {
  const [state, action] = useFormState(resetPasswordOtpAction, init);
  const [resending, setResending] = useState(false);
  const [resent, setResent] = useState<string | null>(null);
  return (
    <form action={action} className="flex flex-col gap-3">
      <div><label className="label">Email</label><input name="email" type="email" className="input" required defaultValue={email} autoComplete="email" /></div>
      <div><label className="label">Kode OTP (6 digit)</label><input name="code" className="input" required pattern="[0-9]{6}" maxLength={6} inputMode="numeric" autoComplete="one-time-code" /></div>
      <div><label className="label">Password baru (min. 8 karakter)</label><input name="password" type="password" className="input" required minLength={8} autoComplete="new-password" /></div>
      <div><label className="label">Ulangi password baru</label><input name="confirmPassword" type="password" className="input" required minLength={8} autoComplete="new-password" /></div>
      {!state.ok && <p className="text-primary text-[12.5px]">{state.error}</p>}
      {devCode && <p className="text-[12.5px]" style={{ color: "var(--warn)" }}>Mode dev (RESEND belum diatur) — kode OTP kamu: <b>{devCode}</b></p>}
      <SubmitButton label="Reset password" pendingLabel="Mereset…" />
      <button
        type="button"
        className="btn ghost sm"
        disabled={resending}
        onClick={async () => {
          const el = document.querySelector<HTMLInputElement>("input[name=email]");
          if (!el?.value) return;
          setResending(true);
          const r = await resendResetOtpAction(el.value);
          setResending(false);
          setResent(r.ok && r.data?.devCode ? `Kode dev baru: ${r.data.devCode}` : "Jika email terdaftar, kode OTP baru telah dikirim.");
        }}
      >
        {resending ? "Mengirim…" : "Kirim ulang kode"}
      </button>
      {resent && <p className="muted text-[12px]">{resent}</p>}
      <p className="muted text-[12.5px] text-center"><Link href="/auth/forgot-password" className="link">‹ Minta kode baru</Link> · <Link href="/auth/login" className="link">Kembali ke login</Link></p>
    </form>
  );
}

export function ResetPasswordTokenForm({ token }: { token: string }) {
  const [state, action] = useFormState(resetPasswordTokenAction, init);
  return (
    <form action={action} className="flex flex-col gap-3">
      <input type="hidden" name="token" value={token} />
      <div><label className="label">Password baru (min. 8 karakter)</label><input name="password" type="password" className="input" required minLength={8} autoComplete="new-password" /></div>
      <div><label className="label">Ulangi password baru</label><input name="confirmPassword" type="password" className="input" required minLength={8} autoComplete="new-password" /></div>
      {!state.ok && <p className="text-primary text-[12.5px]">{state.error}</p>}
      <SubmitButton label="Reset password" pendingLabel="Mereset…" />
      <p className="muted text-[11px]">Link reset berlaku 1 jam. Semua sesi login lama akan otomatis dikeluarkan.</p>
      <p className="muted text-[12.5px] text-center"><Link href="/auth/forgot-password" className="link">Minta kode OTP</Link> · <Link href="/auth/login" className="link">Kembali ke login</Link></p>
    </form>
  );
}
