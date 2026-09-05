import { RegisterForm } from "@/components/AuthForms";
import Logo from "@/components/Logo";
export default function RegisterPage() {
  return (<div className="max-w-[400px] mx-auto mt-6"><div className="card w"><div className="flex items-center gap-3"><Logo size={34} /><div><div className="font-bold text-[15px]">Buat akun</div><div className="muted text-[11.5px]">Gratis · tanpa email</div></div></div><RegisterForm /></div></div>);
}
