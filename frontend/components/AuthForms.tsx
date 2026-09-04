"use client";
import Link from "next/link";
import { useActionState } from "react";
import { loginAction, registerAction, staffLoginAction, type ActionResult } from "@/app/actions";

const init: ActionResult = { ok: true };

export function LoginForm({ next }: { next?: string }) {
  const [state, action, pending] = useActionState(loginAction, init);
  return (
    <form action={action} className="flex flex-col gap-3">
      <input type="hidden" name="next" value={next ?? "/"} />
      <div><label className="label">Username</label><input name="username" className="input" required autoComplete="username" /></div>
      <div><label className="label">Password</label><input name="password" type="password" className="input" required autoComplete="current-password" /></div>
      <label className="flex items-center gap-2 text-[12.5px]"><input type="checkbox" name="remember" /> Ingat saya (30 hari)</label>
      {!state.ok && <p className="text-primary text-[12.5px]">{state.error}</p>}
      <button className="btn pri" disabled={pending}>{pending ? "Masuk…" : "Masuk"}</button>
      <p className="muted text-[12.5px] text-center">Belum punya akun? <Link href="/auth/register" className="link">Daftar</Link></p>
    </form>
  );
}
export function RegisterForm() {
  const [state, action, pending] = useActionState(registerAction, init);
  return (
    <form action={action} className="flex flex-col gap-3">
      <div><label className="label">Username (3–20 alfanumerik)</label><input name="username" className="input" required pattern="[a-zA-Z0-9]{3,20}" autoComplete="username" /></div>
      <div><label className="label">Password (min. 8 karakter)</label><input name="password" type="password" className="input" required minLength={8} autoComplete="new-password" /></div>
      {!state.ok && <p className="text-primary text-[12.5px]">{state.error}</p>}
      <button className="btn pri" disabled={pending}>{pending ? "Mendaftar…" : "Daftar"}</button>
      <p className="muted text-[11px]">Kami tidak mengumpulkan email/HP. Dengan mendaftar kamu menyetujui <Link href="/terms" className="link">Ketentuan</Link> & <Link href="/privacy" className="link">Privasi</Link>.</p>
      <p className="muted text-[12.5px] text-center">Sudah punya akun? <Link href="/auth/login" className="link">Masuk</Link></p>
    </form>
  );
}
export function StaffLoginForm() {
  const [state, action, pending] = useActionState(staffLoginAction, init);
  return (
    <form action={action} className="flex flex-col gap-3">
      <div><label className="label">Username</label><input name="username" className="input" required autoComplete="off" /></div>
      <div><label className="label">ID (mis. ADM001 / MOD005)</label><input name="id" className="input" required autoComplete="off" /></div>
      <div><label className="label">Password</label><input name="password" type="password" className="input" required autoComplete="off" /></div>
      <div><label className="label">Code Akses</label><input name="code" className="input" required autoComplete="off" maxLength={8} /></div>
      {!state.ok && <p className="text-primary text-[12.5px]">{state.error}</p>}
      <button className="btn pri" disabled={pending}>{pending ? "Memverifikasi…" : "Masuk Panel"}</button>
    </form>
  );
}
