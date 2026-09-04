import { RegisterForm } from "@/components/AuthForms";
export default function RegisterPage() {
  return (<div className="max-w-[400px] mx-auto mt-6"><div className="card w"><div className="flex items-center gap-3"><span className="brand">jv</span><div><div className="font-bold text-[15px]">Buat akun</div><div className="muted text-[11.5px]">Gratis · tanpa email</div></div></div><RegisterForm /></div></div>);
}
