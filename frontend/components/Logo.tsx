// Logo brand JKT48Verse — mark PNG transparan dari folder public
// (jkt48verse-icon.png, dominan crimson #e01b3c + aksen putih, jadi aman
// untuk tema terang maupun gelap). Dipakai di sidebar AppShell, halaman
// auth, dan birthday. Server-safe: tanpa hook, tanpa "use client".

type LogoProps = {
  size?: number;
  className?: string;
};

export default function Logo({ size = 32, className = "" }: LogoProps) {
  return (
    <img
      src="/jkt48verse-icon.png"
      alt="Logo JKT48Verse"
      width={size}
      height={size}
      loading="eager"
      decoding="async"
      draggable={false}
      className={`block flex-shrink-0 select-none ${className}`}
    />
  );
}
