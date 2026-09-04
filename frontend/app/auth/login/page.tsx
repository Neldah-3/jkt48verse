import { LoginForm } from "@/components/AuthForms";
export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string }> }) {
  const { next } = await searchParams;
  return (<div className="max-w-[400px] mx-auto mt-6"><div className="card w"><div className="flex items-center gap-3"><span className="brand">jv</span><div><div className="font-bold text-[15px]">Masuk ke JKT48Verse</div><div className="muted text-[11.5px]">Fan-made Platform</div></div></div><LoginForm next={next} /></div></div>);
}
