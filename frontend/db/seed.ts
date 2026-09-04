import { count, eq } from "drizzle-orm";
import { db } from "@/db";
import {
  members, news, schedules, scheduleMembers, encyclopedia, glossary, motivations,
  quizQuestions, guessQuestions, bannedWords, contributors, appMeta, liveSessions,
} from "@/db/schema";
import membersJson from "@/data/members.json";
import { wibMidnight, wibParts } from "@/lib/time";

type RawMember = {
  slug: string; name: string; nickname: string; generation: number | null; team: string | null;
  birthDate: string | null; height: string | null; bloodType: string | null; horoscope: string | null;
  jikoshoukai: string | null; socials: Record<string, string>; status: string;
};

const HOBBIES = ["Menyanyi & menari", "Menggambar", "Membaca novel", "Bermain game", "Memasak", "Fotografi", "Menonton anime", "Bermain gitar", "Olahraga", "Menulis jurnal"];
const TRIVIA = [
  "Suka minum es teh manis setelah show.",
  "Punya koleksi boneka di kamar.",
  "Paling semangat kalau setlist favoritnya dimainkan.",
  "Sering bikin fans tertawa lewat MC theater.",
  "Hafal hampir semua chant setlist.",
  "Selalu bawa lightstick mini di tas.",
];

let seeding: Promise<void> | null = null;

export async function seedIfEmpty() {
  if (seeding) return seeding;
  seeding = (async () => {
    const [{ value }] = await db.select({ value: count() }).from(members);
    if (value > 0) return;
    await seedAll();
  })().finally(() => {
    seeding = null;
  });
  return seeding;
}

export async function seedAll() {
  // ----- Members -----
  const raw = membersJson as RawMember[];
  const inserted = await db
    .insert(members)
    .values(
      raw.map((m, i) => ({
        slug: m.slug,
        name: m.name,
        nickname: m.nickname,
        generation: m.generation,
        team: m.team === "TRAINEE" ? null : m.team === "JKT48_VIRTUAL" ? "VIRTUAL" : m.team,
        status: m.team === "TRAINEE" ? "trainee" : "regular",
        birthDate: m.birthDate,
        height: m.height,
        bloodType: m.bloodType,
        horoscope: m.horoscope,
        jikoshoukai: m.jikoshoukai,
        hobbies: `${HOBBIES[i % HOBBIES.length]}, ${HOBBIES[(i + 3) % HOBBIES.length]}`,
        trivia: TRIVIA[i % TRIVIA.length],
        socials: m.socials ?? {},
      })),
    )
    .onConflictDoNothing()
    .returning();

  // a few graduated members for archive
  await db.insert(members).values([
    { slug: "shani-indira-natio", name: "Shani Indira Natio", nickname: "Shani", generation: 3, status: "graduated", team: null, birthDate: "1998-10-07", height: "160cm", jikoshoukai: "Hai, aku Shani!", socials: {}, hobbies: "Bermain game", trivia: "Mantan kapten JKT48." },
    { slug: "melody-nurramdhani-laksani", name: "Melody Nurramdhani Laksani", nickname: "Melody", generation: 1, status: "graduated", team: null, birthDate: "1992-03-24", height: "158cm", jikoshoukai: "Hai, aku Melody!", socials: {}, hobbies: "Berkebun", trivia: "General Manager JKT48 pasca lulus." },
  ]).onConflictDoNothing();

  const byGen = (g: number) => inserted.filter((m) => m.generation === g);
  const pick = (arr: typeof inserted, n: number, offset = 0) => arr.slice(offset, offset + n);

  // ----- Schedules (relative to today WIB) -----
  const now = new Date();
  const { year, month, day } = wibParts(now);
  const at = (dayOffset: number, hour: number, minute = 0) => {
    const d = wibMidnight(year, month, day);
    d.setUTCDate(d.getUTCDate() + dayOffset);
    d.setUTCHours(d.getUTCHours() + hour, minute);
    return d;
  };
  const theater = "Theater JKT48, fX Sudirman Lt. 4, Jakarta";
  const mapUrl = "https://maps.google.com/?q=fX+Sudirman";
  const schedRows = [
    { title: "Pajama Drive", type: "theater", startAt: at(0, 19), endAt: at(0, 21), location: theater, mapUrl, setlist: "Pajama Drive", ticketStatus: "sold_out", flag: null, description: "Pertunjukan reguler setlist Pajama Drive." },
    { title: "Aturan Anti Cinta", type: "theater", startAt: at(1, 19), endAt: at(1, 21), location: theater, mapUrl, setlist: "Aturan Anti Cinta", ticketStatus: "available", flag: "shonichi", description: "Shonichi setlist Aturan Anti Cinta (Renai Kinshi Jourei)." },
    { title: "Cara Meminum Ramune", type: "theater", startAt: at(2, 14), endAt: at(2, 16), location: theater, mapUrl, setlist: "Cara Meminum Ramune", ticketStatus: "available", flag: null, description: "Show siang akhir pekan." },
    { title: "Meet & Greet Gen 12", type: "event", startAt: at(3, 13), endAt: at(3, 17), location: "Mall Kota Kasablanka, Jakarta", mapUrl: "https://maps.google.com/?q=Kota+Kasablanka", setlist: null, ticketStatus: "available", flag: null, description: "Sesi Meet & Greet member generasi 12." },
    { title: "JKT48 Summer Festival", type: "concert", startAt: at(9, 18), endAt: at(9, 22), location: "Istora Senayan, Jakarta", mapUrl: "https://maps.google.com/?q=Istora+Senayan", setlist: null, ticketStatus: "closed", flag: null, description: "Konser besar musim panas dengan seluruh member." },
    { title: "Talkshow Radio Prambors", type: "media", startAt: at(4, 16), endAt: at(4, 17), location: "Prambors FM", mapUrl: null, setlist: null, ticketStatus: "unknown", flag: null, description: "Bincang santai bersama member di radio." },
    { title: "2-Shot Session Online", type: "event", startAt: at(6, 10), endAt: at(6, 15), location: "Online (Video Call)", mapUrl: null, setlist: null, ticketStatus: "sold_out", flag: null, description: "Sesi foto berdua secara daring." },
    { title: "Fly Away", type: "theater", startAt: at(8, 19), endAt: at(8, 21), location: theater, mapUrl, setlist: "Fly Away", ticketStatus: "available", flag: "senshuuraku", description: "Senshuuraku setlist Fly Away." },
    { title: "Ingin Bertemu", type: "theater", startAt: at(-1, 19), endAt: at(-1, 21), location: theater, mapUrl, setlist: "Ingin Bertemu", ticketStatus: "closed", flag: null, description: "Show kemarin." },
    { title: "Handshake Festival", type: "event", startAt: at(15, 10), endAt: at(15, 18), location: "JIExpo Kemayoran, Jakarta", mapUrl: "https://maps.google.com/?q=JIExpo", setlist: null, ticketStatus: "available", flag: null, description: "Festival jabat tangan seluruh member." },
    { title: "Boku no Taiyou", type: "theater", startAt: at(12, 19), endAt: at(12, 21), location: theater, mapUrl, setlist: "Boku no Taiyou", ticketStatus: "available", flag: null, description: "Pertunjukan reguler." },
    { title: "Anniversary Concert 14th", type: "concert", startAt: at(30, 19), endAt: at(30, 22), location: "Tennis Indoor Senayan", mapUrl: "https://maps.google.com/?q=Tennis+Indoor+Senayan", setlist: null, ticketStatus: "unknown", flag: null, description: "Perayaan ulang tahun grup." },
  ];
  const schedIns = await db.insert(schedules).values(schedRows).returning();
  const smRows: { scheduleId: number; memberId: number }[] = [];
  schedIns.forEach((s, i) => {
    const gen = [10, 11, 12, 13][i % 4];
    const group = byGen(gen).length ? byGen(gen) : inserted;
    const chosen = s.type === "concert" ? pick(inserted, 16) : s.title.includes("Gen 12") ? byGen(12) : pick(group, 8, i % 3);
    chosen.forEach((m) => smRows.push({ scheduleId: s.id, memberId: m.id }));
  });
  if (smRows.length) await db.insert(scheduleMembers).values(smRows).onConflictDoNothing();

  // ----- News -----
  const hoursAgo = (h: number) => new Date(now.getTime() - h * 3600_000);
  const m0 = inserted[0]?.name ?? "Member";
  const m1 = inserted[5]?.name ?? "Member";
  await db.insert(news).values([
    { slug: "shonichi-aturan-anti-cinta", title: "Shonichi Setlist “Aturan Anti Cinta” Resmi Diumumkan", summary: "Setlist legendaris kembali ke panggung Theater JKT48 dengan lineup generasi terbaru.", body: "Theater JKT48 mengumumkan shonichi (hari pertama) setlist Aturan Anti Cinta. Pertunjukan perdana akan menampilkan lineup gabungan generasi 11, 12, dan 13.\n\nTiket dapat dibeli melalui kanal resmi. Pastikan datang lebih awal karena antrean diperkirakan panjang.\n\n" + `Member ${m0} dan ${m1} dipastikan tampil pada shonichi.`, category: "theater", isHighlighted: true, views: 1284, publishedAt: hoursAgo(2) },
    { slug: "summer-festival-2026", title: "JKT48 Summer Festival: Tiket Presale Dibuka", summary: "Konser besar musim panas di Istora Senayan, presale untuk member OFC dibuka lebih dulu.", body: "JKT48 Summer Festival akan digelar di Istora Senayan. Presale tiket untuk anggota OFC dibuka mulai pukul 10:00 WIB, sedangkan penjualan umum menyusul dua hari kemudian.\n\nSetlist konser akan memadukan lagu klasik dan single terbaru.", category: "event", isHighlighted: true, views: 980, publishedAt: hoursAgo(6) },
    { slug: "single-baru-rilis", title: "Single Baru JKT48 Rilis di Seluruh Platform Digital", summary: "Single terbaru resmi dirilis dengan MV yang syuting di Bandung.", body: "Single terbaru JKT48 kini tersedia di Spotify, Apple Music, dan YouTube Music. MV resmi dapat disaksikan di kanal YouTube JKT48.\n\nSenbatsu single ini terdiri dari 16 member lintas generasi.", category: "release", isHighlighted: true, views: 2210, publishedAt: hoursAgo(20) },
    { slug: "meet-greet-gen-12", title: "Meet & Greet Generasi 12 di Kota Kasablanka", summary: "Sesi tatap muka spesial bersama seluruh member generasi 12.", body: "Member generasi 12 akan menyapa fans dalam sesi Meet & Greet di Mall Kota Kasablanka. Tiket dijual per sesi dengan kuota terbatas.", category: "event", isHighlighted: false, views: 540, publishedAt: hoursAgo(30) },
    { slug: "ulang-tahun-member-bulan-ini", title: "Daftar Member yang Berulang Tahun Bulan Ini", summary: "Cek jadwal perayaan ulang tahun member dan event birthday theater bulan ini.", body: "Setiap bulan Theater JKT48 mengadakan pertunjukan spesial ulang tahun member. Fans dapat mengirim ucapan melalui fitur Birthday di JKT48Verse.", category: "birthday", isHighlighted: false, views: 410, publishedAt: hoursAgo(48) },
    { slug: "aturan-baru-theater", title: "Pembaruan Aturan Menonton di Theater JKT48", summary: "Beberapa aturan baru terkait chant, lightstick, dan fotografi selama pertunjukan.", body: "Manajemen theater memperbarui aturan: lightstick maksimal 2 buah, dilarang memotret saat pertunjukan, dan chant mengikuti arahan MC.", category: "theater", isHighlighted: false, views: 780, publishedAt: hoursAgo(70) },
    { slug: "kolaborasi-brand", title: "JKT48 Umumkan Kolaborasi dengan Brand Lokal", summary: "Kolaborasi merchandise edisi terbatas segera hadir.", body: "JKT48 mengumumkan kolaborasi dengan brand fashion lokal untuk merchandise edisi terbatas yang dijual di theater dan online.", category: "other", isHighlighted: false, views: 320, publishedAt: hoursAgo(96) },
    { slug: "senshuuraku-fly-away", title: "Senshuuraku Setlist Fly Away Segera Digelar", summary: "Pertunjukan terakhir setlist Fly Away sebelum rotasi setlist berikutnya.", body: "Setlist Fly Away akan memasuki senshuuraku (hari terakhir). Tiket diprediksi habis dalam hitungan menit.", category: "theater", isHighlighted: false, views: 655, publishedAt: hoursAgo(120) },
  ]).onConflictDoNothing();

  // ----- Encyclopedia -----
  await db.insert(encyclopedia).values([
    { slug: "jkt48", title: "JKT48", sortOrder: 1, content: "## Sejarah\nJKT48 adalah *sister group* AKB48 pertama di luar Jepang, dibentuk pada tahun 2011 di Jakarta, Indonesia. Nama JKT diambil dari singkatan Jakarta.\n\n## Konsep\nMengusung konsep **\"Idol yang dapat kamu temui\"** (*idols you can meet*), JKT48 tampil hampir setiap hari di theater khusus sehingga fans bisa bertemu langsung.\n\n## Struktur Generasi\nMember direkrut melalui audisi per generasi. Setiap generasi memiliki karakter dan lagu debut sendiri. Saat ini generasi aktif mencakup generasi 3 hingga 14.\n\n## Filosofi\nJKT48 menekankan pertumbuhan bersama fans: member berkembang dari *trainee* hingga menjadi member regular melalui kerja keras yang disaksikan langsung oleh penggemar." },
    { slug: "theater", title: "Theater JKT48", sortOrder: 2, content: "## Lokasi\nTheater JKT48 berada di **fX Sudirman lantai 4**, Jalan Jenderal Sudirman, Jakarta Pusat.\n\n## Kapasitas & Fungsi\nTheater berkapasitas sekitar 180–200 penonton dengan panggung menghadap tribun bertingkat. Selain pertunjukan reguler, theater juga digunakan untuk event ulang tahun member, *shonichi*, dan *senshuuraku*.\n\n## Tradisi\nSetiap pertunjukan diawali *overture* dan diakhiri sesi *high-touch* atau salam perpisahan. Fans membawa lightstick dan melakukan chant yang khas untuk tiap lagu.\n\n## Denah\nArea theater terdiri dari lobi merchandise, ruang tunggu, dan ruang pertunjukan utama." },
    { slug: "history", title: "Sejarah & Timeline", sortOrder: 3, content: "## Timeline\n- **2011** — JKT48 diumumkan sebagai sister group AKB48 pertama di luar Jepang.\n- **2012** — Theater JKT48 di fX Sudirman resmi dibuka; Team J dibentuk.\n- **2013** — Debut single \"River\"; generasi 2 bergabung.\n- **2014** — Team KIII terbentuk; Senbatsu Sousenkyo pertama.\n- **2015** — Konser akbar di berbagai kota; Team T dibentuk (2016).\n- **2018** — Janken Tournament pertama JKT48.\n- **2021** — Restrukturisasi besar; sistem tim ditiadakan.\n- **2023–2026** — Era baru dengan generasi 11–14, konser stadion, dan popularitas yang meningkat pesat.\n\n## Momen Monumental\nSenbatsu Sousenkyo, Janken Tournament, dan konser ulang tahun adalah momen yang paling ditunggu fans setiap tahun." },
    { slug: "wota-culture", title: "Budaya Wota", sortOrder: 4, content: "## Apa itu Wota?\n*Wota* adalah sebutan untuk penggemar idol yang aktif mendukung, menonton theater, dan mengikuti event.\n\n## Etika Penggemar\n- Hormati member dan sesama fans di theater maupun ruang publik.\n- Ikuti arahan staf, jangan memotret saat pertunjukan.\n- Chant mengikuti tempo lagu, tidak berlebihan sehingga mengganggu penonton lain.\n- Di ruang digital: tidak menyebarkan informasi pribadi member.\n\n## Glosarium\nLihat daftar istilah di bawah artikel ini." },
  ]).onConflictDoNothing();

  await db.insert(glossary).values([
    { term: "Oshi", meaning: "Member favorit yang paling didukung oleh seorang fans." },
    { term: "Kami-oshi", meaning: "Oshi utama; member nomor satu di hati fans." },
    { term: "Chant", meaning: "Teriakan dukungan berirama yang dilakukan fans selama lagu tertentu." },
    { term: "Wotagei", meaning: "Gerakan tangan dan lightstick terkoordinasi yang dilakukan fans." },
    { term: "Lightstick", meaning: "Tongkat cahaya (biasanya warna sesuai member) yang dibawa fans ke theater." },
    { term: "M&G", meaning: "Meet & Greet — sesi bertemu langsung dengan member." },
    { term: "2-Shot", meaning: "Sesi foto berdua fans dan member." },
    { term: "Shonichi", meaning: "Hari pertama pertunjukan sebuah setlist." },
    { term: "Senshuuraku", meaning: "Hari terakhir pertunjukan sebuah setlist." },
    { term: "Jikoshoukai", meaning: "Kalimat perkenalan diri khas tiap member." },
    { term: "Senbatsu", meaning: "Member terpilih yang tampil pada single utama." },
    { term: "Setlist", meaning: "Rangkaian lagu yang ditampilkan dalam satu pertunjukan theater." },
  ]);

  // ----- Motivations -----
  const todayKey = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  await db.insert(motivations).values([
    { quote: "Mimpi tidak akan lari darimu. Kamulah yang harus mengejarnya, satu langkah kecil setiap hari.", author: "JKT48Verse", template: "jkt48-red-white", featuredOn: todayKey },
    { quote: "Panggung terbaik adalah tempat kamu berani tampil apa adanya.", author: "JKT48Verse", template: "minimal" },
    { quote: "Setiap latihan yang melelahkan adalah investasi untuk sorak sorai di masa depan.", author: "JKT48Verse", template: "dark-elegant" },
    { quote: "Dukung oshi-mu dengan cara yang membuatnya bangga: jadilah fans yang baik.", author: "Komunitas Wota", template: "jkt48-red-white" },
  ]);

  // ----- Quiz -----
  const genMembers = (g: number) => byGen(g).map((m) => m.name);
  const opt4 = (correct: string, pool: string[]) => {
    const others = pool.filter((p) => p !== correct).slice(0, 3);
    const options = [correct, ...others];
    const shuffled = options.map((o, i) => ({ o, r: (i * 7919) % 5 })).sort((a, b) => a.r - b.r).map((x) => x.o);
    return { options: shuffled, correctIndex: shuffled.indexOf(correct) };
  };
  const quizRows: (typeof quizQuestions.$inferInsert)[] = [
    { question: "Tahun berapa JKT48 dibentuk?", options: ["2010", "2011", "2012", "2013"], correctIndex: 1, level: "easy", category: "sejarah" },
    { question: "Di mana lokasi Theater JKT48?", options: ["fX Sudirman", "Grand Indonesia", "Kota Kasablanka", "Senayan City"], correctIndex: 0, level: "easy", category: "theater" },
    { question: "JKT48 adalah sister group dari?", options: ["SKE48", "NMB48", "AKB48", "HKT48"], correctIndex: 2, level: "easy", category: "sejarah" },
    { question: "Apa arti 'shonichi'?", options: ["Hari terakhir", "Hari pertama", "Hari libur", "Hari ulang tahun"], correctIndex: 1, level: "easy", category: "umum" },
    { question: "Sebutan member favorit utama seorang fans adalah?", options: ["Senbatsu", "Kami-oshi", "Wotagei", "Chant"], correctIndex: 1, level: "easy", category: "umum" },
    { question: "Theater JKT48 berada di lantai berapa fX Sudirman?", options: ["2", "3", "4", "5"], correctIndex: 2, level: "medium", category: "theater" },
    { question: "Apa nama single debut JKT48?", options: ["Heavy Rotation", "River", "Fortune Cookie", "Flying Get"], correctIndex: 1, level: "medium", category: "sejarah" },
    { question: "Apa istilah untuk hari terakhir sebuah setlist?", options: ["Shonichi", "Senshuuraku", "Sousenkyo", "Janken"], correctIndex: 1, level: "medium", category: "umum" },
    { question: "Kota asal konsep 48 Group adalah?", options: ["Osaka", "Tokyo", "Nagoya", "Fukuoka"], correctIndex: 1, level: "hard", category: "sejarah" },
    { question: "Turnamen 'batu-gunting-kertas' di JKT48 disebut?", options: ["Sousenkyo", "Janken Tournament", "Request Hour", "Setlist Battle"], correctIndex: 1, level: "hard", category: "sejarah" },
  ];
  for (const g of [10, 11, 12, 13]) {
    const names = genMembers(g);
    const all = inserted.map((m) => m.name);
    if (names.length >= 1) {
      const correct = names[0];
      const pool = all.filter((n) => !names.includes(n));
      const { options, correctIndex } = opt4(correct, pool);
      quizRows.push({ question: `Siapa member yang berasal dari generasi ${g}?`, options, correctIndex, level: "medium", category: "member" });
    }
  }
  inserted.slice(0, 8).forEach((m, i) => {
    if (!m.nickname) return;
    const pool = inserted.map((x) => x.name);
    const { options, correctIndex } = opt4(m.name, pool.slice(i + 1).concat(pool));
    quizRows.push({ question: `Siapa member dengan nama panggilan "${m.nickname}"?`, options, correctIndex, level: i % 2 ? "hard" : "easy", category: "member" });
  });
  await db.insert(quizQuestions).values(quizRows);

  // ----- Guess member -----
  const guessRows = inserted
    .filter((m) => m.jikoshoukai && m.jikoshoukai.length > 10)
    .slice(0, 30)
    .map((m) => ({
      memberId: m.id,
      hints: [
        `Generasi ${m.generation ?? "?"}`,
        m.birthDate ? `Lahir bulan ${Number(m.birthDate.split("-")[1])}` : `Tinggi ${m.height ?? "-"}`,
        `Nama depan diawali huruf "${m.name[0]}"`,
      ],
    }));
  if (guessRows.length) await db.insert(guessQuestions).values(guessRows);

  // ----- Banned words & contributors -----
  await db.insert(bannedWords).values(["anjing", "bangsat", "kontol", "memek", "goblok", "tolol", "bajingan", "ngentot", "babi", "asu"].map((w) => ({ word: w }))).onConflictDoNothing();
  await db.insert(contributors).values([
    { name: "Neldah", role: "Lead Developer", contribution: "Arsitektur platform, backend, scraper, dan spesifikasi produk." },
    { name: "Komunitas JKT48Verse", role: "Content Curator", contribution: "Kurasi ensiklopedia, glosarium wota, dan bank soal quiz." },
    { name: "UI/UX Volunteer", role: "UI/UX Designer", contribution: "Design system merah-putih, komponen, dan mode gelap." },
  ]);

  // ----- Live history (3 days) -----
  const hist = inserted.slice(10, 20).map((m, i) => {
    const started = new Date(now.getTime() - (i + 1) * 7 * 3600_000);
    return {
      memberId: m.id,
      memberName: m.nickname,
      platform: i % 2 ? "idn" : "showroom",
      title: `Live ${m.nickname}`,
      startedAt: started,
      endedAt: new Date(started.getTime() + (25 + i * 9) * 60_000),
      replayUrl: i % 3 === 0 ? (m.socials?.idn_app ?? null) : null,
      viewers: 300 + i * 120,
    };
  });
  await db.insert(liveSessions).values(hist);

  await db.insert(appMeta).values({ key: "seeded_at", value: new Date().toISOString() }).onConflictDoUpdate({ target: appMeta.key, set: { value: new Date().toISOString() } });
  void eq;
}
