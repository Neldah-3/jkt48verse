# STRUKTUR FITUR & MODUL PLATFORM - JKT48Verse 

Konsep aplikasi/web platform bernama **JKT48Verse** berfokus pada penyediaan informasi terpusat, interaksi real-time, aktivitas interaktif, dan pencarian cerdas bagi komunitas penggemar JKT48. 

Kecuali dinyatakan lain, seluruh waktu tampilan memakai zona **Asia/Jakarta (WIB, UTC+7)**.

---

## 1. Dashboard

Pusat utama aplikasi (*main hub*) yang menyajikan ringkasan informasi terkini secara terintegrasi. Dapat diakses guest dalam mode baca.

- **Info Terbaru:** Rangkuman berita dan pengumuman terhangat (agregasi modul 2.5 News) — 5 item terbaru.
- **Jadwal Mendatang:** Cuplikan agenda terdekat (theater, konser, event) — 5 item berikutnya dari sekarang, terhubung ke modul 2.4 Schedule.
- **Member Live:** Indikator visual instan member yang sedang siaran langsung (modul 2.2 Live Member).
- **Birthday Hari Ini:** Informasi perayaan ulang tahun member hari ini menurut kalender WIB (modul 2.6 Birthday).
- **Highlight News:** Sorotan berita utama (flag `is_highlighted = true` pada modul 2.5 News). Maksimal 3 item.
- **Aktivitas Komunitas:** Cuplikan 5 pesan publik terbaru (2.9, tanpa gambar) dan 3 entri leaderboard harian Games (2.8).
- **Akses Cepat:** Tombol pintasan ke live stream (2.2), kalender (2.4), berita (2.5), chat (2.9), games (2.8), dan AI Search (2.12).

---

## 2. Live Member

Fitur pemantauan real-time untuk menampilkan member JKT48 yang sedang melakukan *live streaming*.

### Status & Informasi Live
- **Status Live Member:** Indikator visual instan (badge `LIVE` merah pulsing).
- **Platform Live:** Informasi platform streaming (`showroom`, `idn`) beserta ikon.
- **Judul Live:** Judul atau topik siaran (fallback: `Live {nickname}`).
- **Durasi Live:** Penghitung waktu berjalan real-time sejak `started_at`.
- **Jumlah Penonton:** Estimasi jika ada, jika tidak tampilkan `—`.

### Kontrol Pemutar Live
- **Play & Stop, Fullscreen, Refresh**
- **Picture-in-Picture (PiP):** Native browser API. Jika tidak didukung, tombol disembunyikan.
- **Screen casting:** Opsional, hanya jika API tersedia.

### Multi Live
- **Tampilan Multi:** Layout grid fleksibel (`row-2` atau `row-3`).
- **Batas slot:** Maksimal **6** siaran sekaligus.
- **Tambah / Hapus Siaran:** Slot kosong menampilkan pemilih member yang sedang live.
- **Kontrol Semua Media:** Play/stop semua, fullscreen salah satu, refresh semua.
- **Preferensi Pengguna:** Layout default tersimpan di `user_settings.multi_live_layout`. Guest: `localStorage`.

### Riwayat Live (Recent)
- **Daftar Histori:** Riwayat siaran 3 hari terakhir di `/live/recent`.
- **Informasi:** Member, platform, judul, durasi total, tanggal/waktu WIB, tautan replay jika ada.
- **Filter:** Berdasarkan member, platform, atau tanggal WIB.

---

## 3. Member

Direktori komprehensif data profil dan aktivitas member JKT48.

**Enum status keanggotaan** (`members.status`): `regular` | `trainee` | `graduated` | `former`.
- **Aktif** = `regular` + `trainee`.
- Default katalog hanya menampilkan member aktif. Lulusan tetap punya halaman detail dan bisa dimunculkan lewat filter.

### All Members
- Katalog lengkap member **aktif**. Filter: generasi, status, tim. Sort: alfabetis, generasi, status.

### Regular & Trainee
- Daftar khusus dengan kartu profil ringkas: foto, nama, nickname, generasi, badge status.

### Member Detail
- **Biodata Dasar:** Nama lengkap, nickname, generasi, tanggal lahir, tinggi badan.
- **Informasi Personal:** Hobi dan trivia.
- **Media Sosial:** Tautan resmi (X/Twitter, Instagram, TikTok, Showroom, IDN Live).
- **Galeri & Foto Profil:** Foto resmi resolusi tinggi.
- **Jadwal Tampil:** Kalender/daftar jadwal mendatang khusus member (junction `schedule_members`).
- **Jikoshoukai:** Teks perkenalan diri
- **Riwayat News Terkait:** Arsip artikel yang menyebutkan member.
- **Badge status:** `REGULAR` / `TRAINEE` / `GRADUATED` / `FORMER`.

---

## 4. Schedule

Manajemen jadwal dan agenda kegiatan JKT48. Semua `start_at` / `end_at` disimpan UTC dan ditampilkan WIB.

**Enum jenis agenda:** `theater` | `event` | `concert` | `media` | `other`.
**Enum tiket:** `available` | `sold_out` | `closed` | `unknown`.

### Calendar
- Kalender interaktif. Mode: harian, mingguan, bulanan. Filter jenis agenda.
- **Pengingat (Reminder):** Tombol “Ingatkan Saya” — notifikasi 30 menit dan 5 menit sebelum acara. Hanya login. Guest diarahkan ke login.

### Theater
- Jadwal pertunjukan rutin di Theater JKT48. Info setlist, lineup member, jam mulai WIB, status tiket.

### Event
- Jadwal event off-air maupun on-air, Meet & Greet, 2-Shot, handshake, dll.

### Schedule Detail
- Detail lengkap, lokasi/venue (tautan peta jika ada), waktu WIB, daftar member partisipan, tautan referensi & tiket, berita terkait.

---

## 5. News

Pusat warta dan pengumuman resmi.

**Enum kategori:** `theater` | `event` | `release` | `birthday` | `other`. `latest` adalah view agregat. `is_highlighted` hanya bisa diubah admin.

- **Latest:** Agregat semua kategori, urutan `published_at` terbaru.
- **Theater, Event, Birthday, Other:** Sesuai kategori masing-masing.

---

## 6. Birthday

Modul pemantauan hari ulang tahun member. “Hari ini” = tanggal kalender di `Asia/Jakarta`. Member `graduated`/`former` tetap muncul kecuali `show_birthday = false`.

### Today
- Daftar member ulang tahun hari ini (WIB) dengan highlight banner.
- **Ucapan sistem:** Satu kartu ucapan otomatis (template).
- **Kirim Ucapan:** User terdaftar dapat mengirim pesan (maks 200 karakter, 1 ucapan per user per member per tahun). Moderasi via word-filter + AI (2.17). Guest diarahkan ke login.

### This Week
- Daftar ulang tahun dalam **minggu kalender Senin–Minggu (WIB)** + countdown timer ke 00:00 WIB.

### Calendar
- Kalender ulang tahun sepanjang tahun, navigasi per bulan, filter generasi/status.

### Keterhubungan
- Terhubung ke Member (`birth_date`), News (kategori `birthday`), Dashboard widget, Notifikasi (`BIRTHDAY_ALERT`), Global Search, dan AI Search.

---

## 7. Encyclopedia 

Basis pengetahuan mendalam seputar ekosistem JKT48, dikelola **100% manual** oleh Admin.

### 7.1 JKT48
- Sejarah pendirian sebagai sister group AKB48 pertama.
- Profil grup, konsep “Idol yang dapat kamu temui”, filosofi, struktur generasi.
- Path: `/encyclopedia/jkt48`

### 7.2 Theater
- Informasi komprehensif Theater JKT48 (fX Sudirman, lantai 4), lokasi, denah panggung, kapasitas, fungsi, sejarah tradisi pertunjukan.
- Path: `/encyclopedia/theater`

### 7.3 History
- Kronologi timeline sejarah perjalanan JKT48 sejak 2011 hingga sekarang.
- Momen monumental (Senbatsu Sousenkyo, Janken, Konser Akbar), transformasi era (Tim J-KIII-T, Reorganisasi, New Era).
- Path: `/encyclopedia/history`

### 7.4 Wota Culture
- Panduan budaya fans / wota JKT48.
- Glosarium istilah (Oshi, Kami-oshi, Chant, Wotagei, Lightstick, M&G, 2-Shot, Shonichi, Senshuuraku, dll) yang dikurasi admin.
- Etika penggemar dalam theater, event, dan ruang publik.
- Path: `/encyclopedia/wota-culture`

### 7.5 System Encyclopedia 
- **Tanpa Scraper:** Semua CRUD melalui `/admin/encyclopedia/*`.
- **Admin Only:** Hanya role `ADMIN` yang bisa tambah/edit/hapus.
- **No Auto-Overwrite:** Tidak ada sistem kunci scraper karena scraper dihapus.
- **Media:** Upload gambar via Storage bucket `encyclopedia-images`, dikelola admin.
- **Terindeks:** Terhubung ke Global Search (2.16) dan AI Search (2.12).

---

## 8. Games 

Fitur gamifikasi interaktif. Bermain sebagai guest diizinkan (skor tidak disimpan). Login diperlukan untuk menyimpan skor, leaderboard, badge, streak.

### 8.1 Quiz
- Kuis trivia seputar sejarah, member, theater, umum.
- Level: `easy` | `medium` | `hard`.
- **Skor:** Benar = 30/60/90 poin (easy/medium/hard). Salah = 0. Bonus waktu: `max(0, 10 - floor(detik_jawab / 3))`. Satu sesi = 10/20/30 soal (easy/medium/hard).
- **Kategori:** Sejarah, Member, Theater, Umum.
- **Admin Panel:** Saat buat soal Quiz, admin wajib isi pertanyaan + 4 opsi jawaban. Di panel tersedia **Data Siap Pakai** (suggestion dropdown) yang mengambil dari database Member & Encyclopedia untuk memudahkan pemilihan jawaban benar. Contoh: Jika pertanyaan "Siapa member generasi 10 yang...", dropdown akan menampilkan salah satu member generasi 10 sebagai opsi jawaban yang valid. Admin tinggal klik untuk set sebagai jawaban benar.

### 8.2 Guess Member
- Tebak member berdasarkan Jikoshoukai (Teks perkenalan diri)
- Progressive hints, maksimal 3 hint.
- **Skor:** 100 poin awal; −20 per hint; bonus kecepatan `max(0, 20 - detik_jawab)`.
- **Admin Panel:** Saat buat soal, admin upload Jikoshoukai + isi petunjuk. Tersedia **Data Siap Pakai Member** — list member aktif dengan data Jikoshoukai. Admin pilih 1 sebagai jawaban benar, sistem otomatis link ke `member_id`. Jika member tersebut lulus, soal otomatis nonaktif.

### 8.3 Oshi Sorter
- Mengurutkan peringkat member **aktif** berdasarkan preferensi pribadi (1 = kami-oshi hingga terakhir).
- Pemisahan generasi, drag & drop, simpan & bandingkan (opsional share), shareable result sebagai kartu gambar (`html-to-image`).
- Update berkala mengikuti modul Member.

### 8.4 Daily Challenge
- Misi mini diperbarui setiap hari pukul **00:00 WIB**. Reward poin + streak.
- Jenis: Kombinasi Quiz + Guess Member secara acak (1 misi per hari).
- Reward Streak: Bonus +50 / +200 / +1000 poin untuk streak 7 / 30 / 100 hari.
- Streak putus jika tidak menyelesaikan hingga 23:59:59 WIB.

### 8.5 System Games v2
- Konten (bank soal) dikelola admin via `/admin/games/*`.
- **Keamanan skor:** Seluruh perhitungan skor dan penyerahan jawaban **wajib di server**. Klien hanya mengirim jawaban.
- **Leaderboard:** `/games/quiz/leaderboard`, `/games/guess-member/leaderboard`, `/games/daily/leaderboard`.
- Data referensi member diambil dari modul 2.3 (bukan lagi dari Songs).

---

## 9. Public Chat 

Ruang komunikasi real-time antar penggemar.

**Kanal v1:** satu kanal global `general`.

- **Baca tanpa login:** Guest dapat membaca 50 pesan terakhir (tanpa daftar user online).
- **Tulis wajib login:** Mengirim pesan, gambar, reaksi, reply, report memerlukan `MEMBER` / `MODERATOR` / `ADMIN`.

### 9.1 Pengiriman Pesan & Gambar 
- **Teks:** Maks. 500 karakter.
- **Gambar:** Maksimal 1 gambar per pesan, **max 3 MB**. format `jpg` / `png` / `webp`.
- **Flow Keamanan Gambar (NEW):**
  1. User pilih gambar -> Upload ke temp bucket.
  2. **AI Local Ringan** scan pertama (NSFW, kekerasan, gore). Proses < 2 detik.
  3. Jika **LOLOS** -> lanjut kirim.
  4. Jika **GAGAL / RAGU / ERROR** dari AI Local -> otomatis diteruskan ke **Model AI LLM** (vision model open source yang didukung sistem) untuk verifikasi kedua.
  5. Jika LLM juga menolak -> pesan diblokir, user dapat error `IMAGE_BLOCKED_AI`.
  6. Jika lolos -> gambar dipindah ke bucket `chat-images` permanen.
- **Retensi:** Pesan dan gambar dibersihkan otomatis setelah **3 hari**.

### 9.2 Emoji & Reaksi 
- **Tujuan:** Menambah kehangatan, mencegah penyalahgunaan oleh oknum.
- **Emoji yang DIIZINKAN 
  `😃` `😀` `😱` `😎` `😑` `🤫` `🙃` `🤔` `😉` `😊` `😆` `😍` `🥰` `🤩` `😂` `🥳` `🤗` `🤓` `😭` `👌` `💪` `☝` `🙏` `` `👏` `🤲` `🤝` `👍`
- **Emoji yang DILARANG:** Emoji provokatif, seksual, kasar, senjata, darah, mabuk, judi, atau yang bisa dipakai untuk bullying. Daftar blokir dikelola admin di `/admin/chat/emoji-blocklist`.
- **Sistem:** Satu user = satu jenis reaksi per pesan (toggle). Maks 1 reaksi per user per pesan.

### 9.3 Role Admin + Moderasi 
- **Role: MODERATOR**
  - Khusus untuk moderasi chat/image/account member.
  - **Bisa:** Hapus pesan chat, hapus gambar, block/unblock chat user member (mute 1 jam / 24 jam / 7 hari / permanen), approve/reject report, beri peringatan.
  - **Tidak Bisa:** Block akun ADMIN, block akun MODERATOR lain, akses setting sistem, akses encyclopedia/games management.
  - Ditunjuk via kredensial (2.20), bukan via web.
- **Role ADMIN:** Tetap bisa melakukan semua yang MODERATOR bisa + block akun member & moderator.
- **Sistem Pelaporan:** User melaporkan pesan dengan alasan wajib (spam, pelecehan, NSFW, lainnya). Masuk ke `/admin/reports` dan `/moderator/reports`.
- **Thread / Balas:** Reply satu tingkat (`parent_id`).
- **Pinned Message:** Hanya `ADMIN` yang dapat menyematkan / melepas pin. Maksimal 3 pin aktif.
- **Notifikasi Mention:** `@username` memicu `CHAT_MENTION` jika target mengaktifkan.

### 9.4 Anti-Spam 
- **Teks:** Maksimum **5 pesan / 10 detik / user** dan **30 pesan / menit / user**. Setelah ambang, slow-mode 20 detik.
- **Gambar (NEW - Diperketat):** Maksimum **2 gambar / 1 menit / user** dan **10 gambar / 10 menit / user**. Jika melanggar, slow-mode gambar 60 detik + notifikasi `SLOW_MODE_IMAGE`.
- **Word-filter + AI:** Lihat modul 2.17.

---

## 10. Motivation

Koleksi pesan inspiratif.

- **Pesan Harian:** Satu kartu unggulan (`is_featured_on` = tanggal WIB) per hari. Jika belum ada, pilih terbaru yang `is_published = true`.
- **Kartu Shareable:** Desain visual siap unduh/bagikan.
- **Galeri Harian:** Navigasi berdasarkan tanggal.
- **Template Kartu:** `jkt48-red-white` | `minimal` | `dark-elegant`. Dipilih admin saat membuat.
- **System:** 100% manual via `/admin/motivation`; terindeks pada Global Search & AI Search.

---

## 11. Account

Pusat manajemen profil. Seluruh rute `/account/*` wajib login.

### 11.1 Profile
- Avatar, username (3–20 alfanumerik, unik), bio (maks 160 karakter).
- **Preferensi Oshi:** 1 kami-oshi + hingga 5 oshi pendukung. Live Alert & Birthday Alert merujuk seluruh oshi.
- Ringkasan keaktifan, Kartu Oshi, Badge Koleksi.
- **Privasi:** Jika `private`, hanya username + avatar default terlihat. Oshi disembunyikan jika `hide_oshi = true`.

### 11.2 Settings
- Bahasa: `id` (default) | `en`.
- Notifikasi per tipe: Live Alert, Schedule Reminder, Birthday Alert, News Alert, Chat Mention.
- Tema: `light` | `dark` | `system`.
- Kurasi konten, kontrol privasi, preferensi Multi-Live (`row-2` | `row-3`), Ingat Saya (30 hari).

### 11.3 Activity
- Riwayat login & sesi keamanan (keluar sesi ini / semua sesi lain).
- Riwayat interaksi (50 entri terakhir).
- **Bookmark:** `/account/activity/bookmarks` — News, Schedule, Encyclopedia.
- Riwayat capaian games — `/account/activity/games`.
- Riwayat pesan chat milik sendiri (dalam retensi 3 hari).
- Riwayat Oshi Sorter.

---

## 12. AI Searching for Information

Tab modul pencarian cerdas untuk mencari informasi seputar JKT48 dengan dua mode.

Path: `/ai-search`

### 12.1 Database AI (Search dari Database)
- **Fungsi:** Mencari informasi yang **sudah ada di dalam database platform** (Member, News, Schedule, Encyclopedia, Motivation) menggunakan AI untuk memahami maksud pertanyaan (semantic search).
- **Mekanisme:**
  - User ketik pertanyaan natural: "Siapa member yang ulang tahun bulan ini?" atau "Jadwal theater minggu depan"
  - AI mengubah pertanyaan menjadi query terstruktur + embedding vector.
  - Sistem mencocokkan dengan data internal via vector similarity + full-text.
  - Jawaban diberikan dalam format ringkas + sumber data (link ke halaman terkait).
- **Keunggulan:** Akurat, real-time sesuai data platform, tidak halusinasi, selalu ada sumber.
- **Contoh Query:** "Member generasi 11", "Berita tentang shonichi", "Apa itu wotagei?"

### 12.2 LLM AI SEARCH (Search menggunakan AI LLM)
- **Fungsi:** Mencari informasi yang **tidak ada di database internal** atau membutuhkan penjelasan mendalam menggunakan model LLM open source.
- **Mekanisme:**
  - Model LLM open source yang didukung sistem (contoh: Llama 3, Mistral, Qwen, Gemma - dapat dikonfigurasi di admin panel).
  - Jika Database AI tidak menemukan jawaban (confidence < threshold), otomatis fallback ke LLM AI SEARCH.
  - LLM menjawab dengan pengetahuan umumnya tentang JKT48 + konteks dari database jika ada (RAG).
  - Setiap jawaban LLM wajib diberi label `AI Generated - Perlu Verifikasi` + disclaimer bukan informasi resmi.
- **Pengaturan Admin:** Admin bisa mengatur model yang dipakai, prompt system, temperature, dan batasan topik (hanya boleh jawab seputar JKT48 / idol culture, tolak topik di luar itu).
- **Rate Limit:** Guest: 3 pertanyaan/hari. Member: 20 pertanyaan/hari. Untuk mencegah abuse biaya inferensi.

### 12.3 System AI Search
- **Riwayat:** Riwayat pencarian AI tersimpan per user (maks 50).
- **Feedback:** User bisa like/dislike jawaban untuk training improvement.
- **Terhubung ke:** Semua modul sebagai sumber data.

---

## 13. Contributors & Hak Cipta

### 13.1 Daftar Kontributor
- Direktori kontributor: Nama / Display Name, Role / Peran (Lead Dev, UI/UX, Security Auditor, dll), Contribution / Lingkup Kontribusi.
- Dikelola via `/admin/contributors`.

### 13.2 Hak Cipta & Atribusi
- **Status Non-Official & Fan-Made:** Proyek komunitas non-komersial, tidak terafiliasi / disponsori / dioperasikan oleh JKT48 Operation Team.
- **Hak pemilik merek:** Nama JKT48, logo resmi, foto member, setlist, lagu adalah properti pemegang hak cipta resmi.
- **Hak platform:** Kode orisinal & tulisan kontributor adalah milik komunitas.
- **Atribusi sumber:** Data manual mencantumkan sumber asli.

### 13.3 Halaman Legal (`/terms`, `/privacy`, `/bot-info`)
- **/terms:** Status fan-made, larangan penyalahgunaan, akun dapat ditangguhkan, perubahan ketentuan.
- **/privacy:** Tidak kumpulkan email/HP, data disimpan (username, hash password, preferensi, chat 3 hari, log sesi), cookie HttpOnly, hak hapus akun, tidak jual data.
- **/bot-info:** Identitas bot (jika masih ada untuk Live/Schedule), tujuan, kontak, jadwal etis.

---

## 14. Sistem Notifikasi (Notification Center)

Pusat notifikasi terpadu. Hanya pemilik `user_id` yang dapat membaca (RLS).

### Jenis Notifikasi
| Tipe | Sumber | Pemicu |
| --- | --- | --- |
| `LIVE_ALERT` | Live Member | Oshi mulai live |
| `SCHEDULE_REMINDER` | Schedule | 30m & 5m sebelum jadwal |
| `BIRTHDAY_ALERT` | Birthday | Oshi ulang tahun (00:05 WIB) |
| `NEWS_ALERT` | News | Berita baru kategori subscribe |
| `CHAT_MENTION` | Public Chat | Username disebut |
| `GAME_DAILY` | Games | Daily Challenge baru (06:00 WIB) |
| `GAME_BADGE` | Games | Badge baru diperoleh |
| `SYSTEM` | Sistem | Pengumuman sistem / blokir |

### Fitur
- Halaman `/notifications` dengan filter tipe/status/tanggal. Wajib login.
- Badge Counter lonceng topbar (maks `99+`).
- Realtime delivery + Web Push API (Service Worker + VAPID).
- Mark as Read, Detail notifikasi, Deduplikasi LIVE_ALERT.

### Data Model
- `notifications`, `notification_preferences`, `schedule_reminders`, `push_subscriptions`.

---

## 15. Sistem Bookmark

- **Tambah/Hapus:** Tombol di detail News, Schedule, Encyclopedia. Guest diarahkan ke login.
- **Daftar:** `/account/activity/bookmarks`, kelompok per tipe.
- **Filter & Sort:** Filter tipe & tanggal.
- **Indikator Visual:** Ikon filled jika sudah bookmark.
- **Data Model:** `user_bookmarks` dengan unique `(user_id, entity_type, entity_id)`.

---

## 16. Sistem Pencarian Global (Global Search)

Mesin pencarian terpadu.

### Cakupan
| Entity | Kolom | Prioritas |
| --- | --- | --- |
| Members | name, nickname, jikoshoukai_id | Tinggi |
| News | title, summary, body | Tinggi |
| Schedule | title, location | Sedang |
| Encyclopedia | title, content | Sedang |
| Motivation | quote_text | Rendah |

### Fitur
- Real-time suggestions (debounce 300ms), minimal 2 karakter.
- Hasil terkelompok, highlight keyword, filter entity, empty state informatif, recent searches di `localStorage`.
- Batasan: `q` maks 80 karakter.

---

## 17. Sistem Keamanan Chat + Image menggunakan AI 

Sistem keamanan berlapis untuk menjaga chat tetap sopan dan aman.

### 17.1 Filter Kata Kasar / Tidak Baik (Text)
- **Tujuan:** Harus lolos dari akal-akalan kata (misal: `a n j i n g`, `4nj1ng`, `b@g0`, dll).
- **Layer 1 - Sistem Local (Ringkas & Cepat):**
  - Word-filter dengan normalisasi: lowercase, hapus spasi berlebih, leet-speak conversion (`4->a`, `0->o`, `@->a`, dll), pengulangan huruf (`baaaagus` -> `bagus` tapi `anjiiing` tetap terdeteksi).
  - Daftar kata terlarang dikelola admin + regex pattern.
  - Jika terdeteksi -> langsung blokir dengan error `MESSAGE_BLOCKED`.
- **Layer 2 - Model LLM AI (Jika Lolos Layer 1 / Ragu):**
  - Jika sistem local ragu (confidence sedang) atau user mencoba bypass, teks dikirim ke model LLM ringan (open source) untuk klasifikasi toxic/harassment/NSFW.
  - LLM menilai konteks, bukan hanya kata. Misal: "anjing" dalam konteks hewan peliharaan member -> lolos, tapi makian -> blokir.
  - Jika LLM menolak -> blokir + catat percobaan.

### 17.2 Filter Gambar Chat (Image)
- **Layer 1 - AI Local Ringan (Vision):** Model NSFW ringan (contoh: nsfwjs / open source NSFW detector) scan di server sebelum disimpan. Deteksi: porn, gore, kekerasan, senjata.
- **Layer 2 - AI LLM Vision:** Jika AI Local error / confidence rendah / gambar ambigu, otomatis diteruskan ke model LLM vision (open source) untuk verifikasi kedua.
- **Keputusan:** Hanya gambar yang lolos kedua layer yang disimpan.
- **Logging:** Gambar yang diblokir disimpan hash-nya (bukan file) untuk audit admin, file asli dibuang.

### 17.3 Sistem Report
- User dapat report pesan/gambar dengan alasan: spam, pelecehan, NSFW, provokasi, lainnya + deskripsi opsional.
- Report masuk ke antrian Admin & Moderator.
- Auto-hide: Jika 1 pesan di-report oleh 5 user berbeda dalam 10 menit, otomatis hidden sementara menunggu review moderator.

### 17.4 Sistem Anti-Spam (Diperketat untuk Gambar)
- Teks: 5/10 detik, 30/menit -> slow-mode 15 detik.
- Gambar: 2/1 menit, 10/10 menit -> slow-mode gambar 60 detik.
- **Spesial:** Jika user 3x berturut-turut mengirim pesan/gambar yang diblokir AI, auto-mute 10 menit + notifikasi ke moderator.
- Semua log disimpan untuk audit.

---

## 18. Admin Panel 

Panel kontrol penuh untuk Admin.

Path: `/admin/*` — Hanya bisa diakses role `ADMIN` dengan kredensial khusus (2.20).

### 18.1 Akses Penuh Sistem
- Mengakses penuh semua sistem yang menggunakan admin panel: Encyclopedia, Games, News, Schedule, Member, Motivation, Contributors, Chat Management, Emoji Blocklist, AI Search Config, Keamanan AI Config, Reports.
- CRUD penuh tanpa batasan.

### 18.2 Menjaga Akun Member dan Moderator
- Melihat daftar semua akun: Member, Moderator, Admin (read-only untuk admin lain).
- **Moderator bisa diakses Admin:** Admin dapat melihat, edit role, reset password, dan blokir akun moderator.
- Melihat aktivitas login, riwayat pelanggaran chat, riwayat report.

### 18.3 Blokir Akun
- **Bisa memblokir akun Member + Moderator.**
- Opsi blokir: Temporary (1 hari, 7 hari, 30 hari) atau Permanent.
- Alasan blokir wajib diisi, akan tampil di notifikasi user yang diblokir.
- Akun yang diblokir tidak bisa login, chat, atau kirim ucapan birthday.

### 18.4 User Admin Khusus (3 User)
- **Hanya 3 akun Admin** yang ada di kredensial (environment variable / file kredensial server, bukan di database yang bisa diotak-atik via web/browser).
- Tidak bisa ditambah, dihapus, atau diedit melalui web/browser. Hanya bisa diubah langsung via file kredensial di server oleh owner.
- Memiliki akses tertinggi, termasuk menghapus data permanen.

### 18.5 Mengakses Report User Member
- Dashboard report: semua report dari member (chat, gambar, akun).
- Filter: status (pending, approved, rejected), tipe, tanggal.
- Aksi: Approve report (hapus konten + beri sanksi), Reject report, Ban user.

---

## 19. Moderator Panel 

Panel khusus untuk Moderator dengan hak terbatas.

Path: `/moderator/*` — Hanya role `MODERATOR`.

### 19.1 Mengakses Report dari User Member
- Melihat antrian report yang ditujukan untuk moderasi chat & akun member.
- Tidak bisa melihat report yang menyangkut Admin atau Moderator lain (hanya Admin yang bisa).

### 19.2 Bisa Memblokir Akun Member
- **Hanya bisa memblokir akun MEMBER**, tidak bisa blokir Moderator atau Admin.
- Opsi blokir terbatas: Mute Chat (1 jam, 24 jam, 7 hari) dan Ban Akun Member (maks 30 hari, permanen butuh approval Admin).
- Wajib sertakan alasan & bukti (link pesan/gambar).

### 19.3 User Moderator Ada 10 User Saja di Kredensial
- **Hanya 10 akun Moderator** yang ada di kredensial (sama seperti Admin, disimpan di file kredensial server, tidak bisa diutak-atik via web).
- Tidak bisa menambah moderator via web. Jika butuh ganti, owner edit file kredensial di server.
- Akun moderator memiliki masa aktif yang bisa diatur admin.

---

## 20. Sistem Auth & Kredensial Khusus Admin/Moderator 

Sistem login terpisah untuk menjaga keamanan tingkat tinggi.

### 20.1 Page Login Khusus Admin + Moderator dengan Code Akses
- **Path Terpisah:** `/auth/admin-login` (bukan `/auth/login` member biasa). Halaman ini tidak di-link di UI publik, hanya diketahui oleh Admin/Moderator.
- **Form Login:** Membutuhkan 4 field:
  1. `username` (khusus admin/moderator)
  2. `id` (ID unik admin/moderator, contoh: ADM001, MOD005)
  3. `password`
  4. `code_akses` (kode rahasia 6-8 digit / alphanumeric, berbeda per akun, untuk mencari akun mana yang akan di-login dan verifikasi ganda)
- **Flow:** Sistem cek kombinasi ke-4 field di file kredensial. Jika salah satu salah -> error generic "Kredensial tidak valid" (tidak bocorkan field mana yang salah).
- **Keamanan Tambahan:** Rate limit ketat (max 5 percobaan / 15 menit / IP), log percobaan login, notifikasi ke Admin lain jika ada percobaan login gagal berulang.

### 20.2 Sistem Username, ID, Password, dan Code Akses Hanya di Kredensial
- **Penyimpanan:** Semua data login Admin (3 user) dan Moderator (10 user) **HANYA** disimpan di file kredensial server (misal: `.env.admin` atau `credentials.json` yang tidak di-commit ke git dan tidak bisa diakses via browser).
- **Tidak Mengikuti Aturan Member:** Aturan username/password member (3-20 alfanumerik, dll) **TIDAK BERLAKU** untuk Admin/Moderator. Mereka bisa pakai format khusus:
  - Username: `admin_jkt48_01`, `mod_jkt48verse_05` (bebas, tapi unik)
  - ID: `ADM001`, `MOD010` (format tetap untuk identifikasi cepat)
  - Password: Minimal 12 karakter, kombinasi huruf besar/kecil/angka/simbol, tidak ada batasan alfanumerik saja.
  - Code Akses: 6-8 digit unik, contoh: `A7X9K2`, `MOD99P`
- **Tujuan:** Biar member biasa tidak sama / tidak bisa menebak atau mendaftar sebagai admin/moderator. Pendaftaran admin/moderator via web **DINONAKTIFKAN TOTAL**.
- **Pengelolaan:** Hanya owner/server admin yang bisa menambah/menghapus/mengedit kredensial via SSH / akses server langsung.

### 20.3 Perbedaan Role
| Role | Jumlah Max | Penyimpanan | Bisa Blokir | Akses Panel |
| --- | --- | --- | --- | --- |
| `MEMBER` | Unlimited | Database | Tidak | `/account` |
| `MODERATOR` | 10 | Kredensial File | Member saja | `/moderator/*` |
| `ADMIN` | 3 | Kredensial File | Member + Moderator | `/admin/*` + `/moderator/*` (read) |

# Design System JKT48Verse

---

## Daftar Isi

1. [Prinsip Desain](#1-prinsip-desain)
2. [Brand Identity](#2-brand-identity)
3. [Design Tokens](#3-design-tokens)
4. [Tata Letak & Grid](#4-tata-letak--grid)
5. [Navigasi](#5-navigasi)
6. [Komponen UI](#6-komponen-ui)
7. [Ikonografi](#7-ikonografi)
8. [Spesifikasi Per Halaman](#8-spesifikasi-per-halaman)
9. [Dark Mode](#9-dark-mode)
10. [Motion & Animasi](#10-motion--animasi)
11. [Responsif & Multi-Device](#11-responsif--multi-device)
12. [Aksesibilitas](#12-aksesibilitas)
13. [Empty, Loading & Error State](#13-empty-loading--error-state)
14. [Konten & Tone of Voice](#14-konten--tone-of-voice)
15. [Larangan & Catatan Legal](#15-larangan--catatan-legal)

---

## 1. Prinsip Desain

| # | Prinsip | Artinya dalam praktik |
|---|---------|----------------------|
| 1 | **Merah Putih, Tegas & Hangat** | Identitas merah JKT48 (`#E01B3C`) sebagai warna aksi utama; netral abu-abu dingin untuk area kerja agar konten (foto member, live) yang jadi bintang. |
| 2 | **Information-Dense tapi Bernapas** | Halaman padat data (jadwal, chat, admin) tetap memakai spacing konsisten, hierarki tipografi jelas, dan whitespace secukupnya. |
| 3 | **Real-time First** | Status live, countdown, dan timer selalu terlihat: badge `LIVE` pulsing merah, indikator titik hijau online, durasi berjalan `HH:MM:SS`. |
| 4 | **Mobile-Grade Consistency** | Setiap fitur wajib layak dipakai di 390px; navigasi selalu punya jalur mobile (drawer + bottom nav). |
| 5 | **Aman & Sopan secara Visual** | Status moderasi (blocked, muted, reported, AI-flag) selalu ditampilkan dengan warna semantik yang jelas — tidak ada status yang "silently" berubah. |
| 6 | **Fan-made, Bukan Resmi** | Footer/branding selalu mencantumkan status non-official. Tidak meniru 1:1 aset resmi JKT48 Operation Team. |

---

## 2. Brand Identity

### 2.1 Logo / Brand Mark

- **Monogram "jkt48verse"** dalam rounded-square (`border-radius: 10px`) dengan gradien merah:
  - Light: `linear-gradient(135deg, #FF4D6D → #B60F2C)`
  - Bayangan warna: `0 4px 10px -2px rgba(224,27,60,.5)`
  - Teks putih `font-weight: 800`, `letter-spacing: -0.5px`
- Ukuran standar: **36×36** (toolbar), **34×34** (sidebar).
- Nama produk di samping mark: **"JKT48Verse"** (bold 14–15px) + sub-teks *"Fan-made Platform"* (11px, muted).

### 2.2 Mood & Arah Visual

- **Kata kunci:** energik, modern, bersih, sedikit "idol-pop" tapi tetap profesional.
- Gradien digunakan **hanya** pada: brand mark, hero/highlight banner, avatar inisial, ikon kategori. Tidak untuk body text atau area form.
- Fotografis: foto member selalu dalam frame membulat (`border-radius` 10–16px), rasio kotak untuk avatar, 16:9 untuk thumbnail live.

### 2.3 Avatar Inisial

Karena mockup tidak memakai foto asli, avatar memakai **inisial + gradien warna** (6 varian, dipilih stabil per user):

| Kelas | Gradien |
|-------|---------|
| `.g1` | `135deg, #FF7A59 → #E01B3C` |
| `.g2` | `135deg, #F7B733 → #E0741B` |
| `.g3` | `135deg, #38B2A3 → #1C7C8C` |
| `.g4` | `135deg, #8F6BF2 → #5A2FD0` |
| `.g5` | `135deg, #4F8EF7 → #2B4FD8` |
| `.g6` | `135deg, #F56A9D → #C2255C` |

Ukuran: 32 (topbar), 28 (chat), 44–46 (highlight/birthday), 62 (kartu member).

---

## 3. Design Tokens

### 3.1 Warna — Light Theme (default)

| Token | Nilai | Pemakaian |
|-------|-------|-----------|
| `--bg` | `#F6F7F9` | Latar area konten |
| `--surface` | `#FFFFFF` | Kartu, sidebar, topbar |
| `--surface-2` | `#EEF0F5` | Input, hover, bubble chat |
| `--surface-3` | `#E6E9F0` | Elemen tersier, rank netral |
| `--text` | `#141821` | Teks utama |
| `--muted` | `#6A7280` | Teks sekunder, meta |
| `--border` | `#E4E7EF` | Border kartu & divider |
| `--border-2` | `#D8DCE6` | Border tombol ghost/input |
| `--primary` | `#E01B3C` | Merah utama: CTA, aktif, live |
| `--primary-2` | `#B60F2C` | Hover primary |
| `--primary-soft` | `rgba(224,27,60,.09)` | Background item aktif, chip on |
| `--ok` | `#158A50` | Sukses, online, tiket tersedia |
| `--ok-soft` | `rgba(21,138,80,.12)` | Tag sukses |
| `--warn` | `#B45309` | Peringatan, streak, birthday |
| `--warn-soft` | `rgba(217,119,6,.14)` | Tag warning |
| `--info` | `#2563EB` | Informasi, platform IDN, link |
| `--info-soft` | `rgba(37,99,235,.11)` | Tag info |
| `--violet` | `#7C3AED` | Konser, kategori birthday, LLM |
| `--violet-soft` | `rgba(124,58,237,.11)` | Tag violet |
| Live accent | `#FF2B4E` | Badge LIVE & pulsing dot (lebih terang dari primary) |

### 3.2 Warna — Dark Theme

| Token | Nilai |
|-------|-------|
| `--bg` | `#0E1116` |
| `--surface` | `#151A22` |
| `--surface-2` | `#1C232E` |
| `--surface-3` | `#242D3A` |
| `--text` | `#EEF1F6` |
| `--muted` | `#95A0B1` |
| `--border` | `#232B38` |
| `--border-2` | `#2C3543` |
| `--primary` | `#EF3055` |
| `--primary-2` | `#FF4D6D` (hover lebih terang di dark) |
| `--ok / --warn / --info / --violet` | `#2FBF74 / #F0A13C / #5B8CF7 / #9D78F5` |
| Body background | `#0C0F14` + dot grid `#161C26` |

### 3.3 Warna Semantik Status

| Status | Warna | Tag |
|--------|-------|-----|
| LIVE / penting / tiket habis | `--primary` | `.t-red` |
| Sukses / tersedia / online | `--ok` | `.t-ok` |
| Peringatan / terbatas / streak / birthday | `--warn` | `.t-warn` |
| Informasi / IDN / trainee / media | `--info` | `.t-info` |
| Konser / violet kategori | `--violet` | `.t-violet` |
| Netral / arsip / other | `--muted` | `.t-gray` |

### 3.4 Tipografi

- **Font stack:** `ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif` — tanpa webfont eksternal agar instan & bisa offline.
- `letter-spacing` negatif (`-0.3px` s/d `-0.5px`) untuk judul besar.

| Peran | Ukuran | Weight | Catatan |
|-------|--------|--------|---------|
| H1 halaman | 21px (18px mobile) | 700 | Judul halaman, `-0.3px` |
| H2 hero | 20px (16.5px mobile) | 700–800 | Di dalam banner |
| H3 kartu | 13.5px | 700 | Judul widget |
| Body | 14.5px (13.5px mobile) | 400–500 | Dasar aplikasi |
| Body kecil | 13px | 400–600 | Item list, chat |
| Meta/caption | 11–11.5px | 500 | Timestamp, lokasi |
| Label chip/tag | 10–11px | 650–750 | `UPPERCASE`, `letter-spacing .4–.9px` |
| Angka stat | 22px | 800 | Kartu statistik admin |
| Timer live | 11px | 650 | Tabular, format `HH:MM:SS` |

### 3.5 Spacing, Radius, Shadow

**Spacing scale (4px base):** `3 · 5 · 7 · 8 · 9 · 10 · 11 · 12 · 13 · 14 · 16 · 18 · 22 · 26`
Pemakaian lazim: padding kartu `16px`, gap grid `14px`, gap dalam komponen `8–12px`, padding halaman `22px` (desktop) / `16px` (mobile).

| Token | Nilai | Pemakaian |
|-------|-------|-----------|
| Radius kecil | 6–8px | Tag, kbd, rank badge |
| Radius sedang | 9–11px | Tombol (10), input (11), thumbnail (9–11) |
| Radius besar | 13–16px | Kartu (15), hero (16), player (16) |
| Radius penuh | 999px | Chip, badge counter, reaksi |
| Device frame | 16px (desktop) · 22px (tablet) · 34px (mobile) | Khusus mockup |

**Shadow:**

```css
--shadow:    0 1px 2px rgba(16,24,40,.05), 0 1px 3px rgba(16,24,40,.07);  /* kartu dasar */
--shadow-lg: 0 12px 32px -8px rgba(16,24,40,.18);                          /* drawer, popover, hover */
/* khusus CTA merah: */ 0 3px 8px -2px rgba(224,27,60,.45);
/* khusus hero:     */ 0 14px 30px -10px rgba(217,4,41,.5);
```

---

## 4. Tata Letak & Grid

### 4.1 Kerangka Aplikasi

```
┌────────────────────────────────────────────────────────────┐
│ TOPBAR (58px): ☰ | Global Search | … | 🔔9 | 🌓 | User     │
┌──────────┬─────────────────────────────────────────────────┤
│ SIDEBAR  │  PAGE SCROLL (overflow-y)                       │
│ 240px    │  ┌───────────────────────────────────────────┐  │
│          │  │ CONTENT (max-width 1180px, padding 22px)  │  │
│ Brand    │  │                                           │  │
│ Menu     │  │   [P-Head: H1 + aksi]                     │  │
│ Utama    │  │   [Grid 12 kolom, gap 14px]               │  │
│ Interaktif│ │                                           │  │
│ Panel    │  └───────────────────────────────────────────┘  │
└──────────┴─────────────────────────────────────────────────┘
└─ BOTTOM NAV (mobile only) ──────────────────────────────────┘
```

- **Sidebar:** 240px (desktop) → 74px icon-rail (tablet) → drawer overlay 262px + backdrop gelap `rgba(10,12,16,.45)` (mobile).
- **Grid 12 kolom** dengan kelas span: `.c3 .c4 .c6 .c8 .c12`.
- Pola konten umum: `c8 + c4` (utama + sidebar widget), `c4×3` (kartu setara), `c3×4` (statistik).
- `max-width: 1180px` agar layar ultra-wide tidak melebar berlebihan.

### 4.2 Aturan Urutan Visual Halaman

1. **P-Head** — judul + subjudul meta (kiri), aksi/filter chip (kanan).
2. **Banner/wajib atas** (hero highlight, daily challenge, birthday banner) bila ada.
3. **Grid konten** — kolom kiri untuk konten utama (lebih berat), kolom kanan untuk widget ringkas.
4. **Catatan kaki kecil** (info aturan, disclaimer) di bawah list.

---

## 5. Navigasi

### 5.1 Struktur Sidebar

```
MENU UTAMA
├─ Dashboard        (i-home)
├─ Live Member      (i-radio)  + badge counter merah (jumlah live)
├─ Member           (i-users)
├─ Jadwal           (i-cal)
├─ News             (i-news)
└─ Public Chat      (i-chat)

INTERAKTIF
├─ Games            (i-game)
├─ Birthday         (i-gift)          ※ halaman penuh, lihat §8.4
├─ Encyclopedia     (i-news/book)     ※ §8.5
├─ Motivation       (i-heart)         ※ §8.6
└─ AI Search        (i-spark)

PANEL
├─ Admin Panel      (i-shield)   ← hanya terlihat role ADMIN
└─ Moderator Panel  (i-shield)   ← hanya terlihat role MODERATOR

FOOTER SIDEBAR: "v2.0 · Non-official · Data fiktif untuk mockup"
```

- Item aktif: background `--primary-soft`, teks & ikon `--primary`, weight 650.
- Hover: `--surface-2`.
- Badge counter merah di kanan (contoh: jumlah live berlangsung, maks `99+`).

### 5.2 Topbar

| Elemen | Spec |
|--------|------|
| Hamburger | 37×37, hanya tampil mobile (`display:none` default) |
| Global Search | width `min(380px, 44vw)`, ikon kaca pembesar, placeholder *"Cari member, news, jadwal…"*, shortcut `⌘K`, sembunyi di mobile |
| Notifikasi | lonceng + dot counter merah (maks `99+`), klik → popover 300px berisi 3 notifikasi terbaru + "Lihat semua" |
| Toggle tema | matahari/bulan, switch class `dark` pada `<body>` |
| User chip | avatar 32 + nama + role kecil (`MEMBER`), sembunyi teks di mobile |

### 5.3 Bottom Navigation (mobile)

5 slot: **Home · Live · Jadwal · Chat · Menu** (Menu membuka drawer lengkap).
Spec: ikon 15px + label 9.5px, warna muted → `--primary` saat aktif, `padding-bottom: env(safe-area-inset-bottom)`.

### 5.4 Aturan Routing Visual

- Path didefinisikan di spesifikasi (`/live/recent`, `/games/quiz/leaderboard`, `/admin/*`, dst).
- Halaman tersembunyi **tidak** di-link di UI publik: `/auth/admin-login`.
- Guest yang menekan aksi berbayar/login → arahkan ke login (jangan tampilkan form inline di halaman publik).

---

## 6. Komponen UI

### 6.1 Button

| Varian | Kelas | Spec |
|--------|-------|------|
| Primary | `.btn.pri` | bg `--primary`, teks putih, radius 10, padding `8.5×15`, shadow merah; hover `--primary-2` |
| Ghost/Outline | `.btn.ghost` | bg `--surface`, border `--border-2`; hover `--surface-2` |
| Small | `.btn.sm` | padding `6×11`, font 11.5, radius 8 |
| Icon | `.btn.icon` | 34×34, radius 9, ikon 18px |

**Aturan:** 1 primary per grup aksi; sisanya ghost. Tombol destruktif (Ban Permanen, Hapus) tetap primary merah + konfirmasi modal. Label memakai ikon 15px + teks.

### 6.2 Chip & Tag

- **Chip (filter/interaktif):** radius pill, font 11/650, padding `3.5×10`; aktif = `--primary-soft` + teks `--primary`. Bisa memuat dot status (live hijau).
- **Tag (label statis):** font 10/750 uppercase, radius 6, padding `2.5×8`, varian `.t-red .t-ok .t-warn .t-info .t-violet .t-gray`.

### 6.3 Card

`.card` = bg `--surface`, border 1px `--border`, radius **15px**, shadow `--shadow`.
`.w` = padding 16, flex-column, gap 12. Header kartu `.w-head`: judul H3 + link "Semua ›" berwarna primary (11.5/600).

### 6.4 Badge & Indikator Live

- **Badge LIVE:** bg `#FF2B4E`, teks putih 9.5–11px / 800, radius 5, `letter-spacing .8px`, animasi `blink` 2.2s. Posisi absolut pojok kiri-atas thumbnail.
- **Live dot:** lingkaran 8px merah, animasi `pulse` (ripple box-shadow) 1.6s — dipakai di sidebar widget, chip, stat.
- **Badge counter:** pill merah, font 9–10/700, border 2px warna surface (biar "terpisah" dari ikon).

### 6.5 List Row & Tabel

- **Row item:** flex, gap 11, padding `9×0`, divider 1px; kolom meta = timestamp + tag.
- **Tabel `.tb`:** font 12.5; header uppercase 10.5/700 muted; baris dipisah border; baris terakhir tanpa border. Aksi baris = tombol sm di kanan.

### 6.6 Form & Input

- Input: bg `--surface-2`, border `--border-2`, radius 11, padding `9.5×13`; focus ring `0 0 0 3.5px var(--primary-soft)` + border primary (contoh: `.bigsearch`).
- Fake input (guest): teks muted *"Login untuk…"* + tombol Login primary di kanan.
- Aturan tampil: batas karakter (bio 160, chat 500, ucapan 200, q 80) ditampilkan sebagai counter kecil di kanan bawah input.

### 6.7 Popover & Modal

- Popover notifikasi: width 300, radius 14, `--shadow-lg`, header dengan tag "N baru", item dengan ikon kategori, footer link primary.
- Modal konfirmasi (ban/hapus): overlay `rgba(10,12,16,.5)`, kartu 420px, judul + alasan wajib isi + dua tombol (ghost batal, primary aksi).
- Semua popover tutup saat klik di luar.

### 6.8 Komponen Khusus

| Komponen | Spec ringkas |
|----------|--------------|
| **Hero highlight** | Gradien `135deg #FF4D6D → #D90429 48% → #5C0A16`, lingkaran dekoratif rgba-putih, tag ★ Highlight, H2 putih, tombol putih-teks-merah. Min-height 236 (190 mobile) |
| **Player live** | Aspect 16:9, latar gradien gelap + tint merah radial, badge LIVE kiri-atas, tombol play bulat 66px glassmorphism, info bawah-kiri (judul bold putih + meta) |
| **Slot Multi Live** | Aspect 16:10; aktif = gradien gelap + badge LIVE + nama; kosong = border dashed 1.6px + ikon + teks "Pilih member live", hover border primary |
| **Kartu member** | Tengah, avatar 62 + dot status pojok, nama 13.5/700, `@nick · Gen N` muted, tag status + tim; hover naik 3px |
| **Kalender** | Grid 7 kolom, sel aspect 1:1.05; hari ini = kotak primary putih; hari beragenda = `--surface-2` + dots warna kategori; hari lain bulan = opacity .28 |
| **Baris jadwal `.sch`** | Kotak waktu 62px kiri (jam bold + tanggal kecil), judul + lokasi (ikon pin) + tag, tombol 🔔 Ingatkan kanan |
| **Daily challenge** | Banner gradien gelap `#1D2333 → #0F1220`, ikon api gradien oranye-merah 52px, pill streak (tercapai = merah), tombol putih "Kerjakan Sekarang" |
| **Kartu game** | Ikon 44px gradien per game, judul 14/750, deskripsi 12 muted, footer: jumlah pemain + tombol Main |
| **Bubble chat** | Balok `--surface-2` radius `4 12 12 12`; header `nama bold + jam`; gambar preview 170×110 radius 11; reaksi = pill border (aktif: soft primary) |
| **Emoji bar** | Tombol 31×31 radius 8, font 15px, hover scale 1.12; hanya emoji whitelist |
| **Jawaban AI** | Kartu `.ans`: baris pertanyaan muted, paragraf 13.5 line-height 1.65, chip sumber `.src` (soft info/violet), label `AI Generated — Perlu Verifikasi` (soft warn), tombol like/dislike |
| **Stat admin** | Label uppercase 11 muted + ikon, angka 22/800, tren 11 (▲ hijau / ▼ merah) |

---

## 7. Ikonografi

- **Gaya:** stroke outline 2px, round cap/join (gaya Lucide/Feather), **tanpa fill** kecuali badge.
- **Ukuran:** `.ic` 18px · `.s` 15px · `.xs` 13px.
- **Implementasi:** SVG sprite internal (`<symbol>` + `<use>`) — tanpa CDN, aman offline.
- **Daftar ikon inti:** home, radio (live), users, user, calendar, news, chat, gamepad, spark (AI), shield (admin), search, bell, sun, moon, menu, x, play, refresh, pip, fullscreen, heart, gift, trophy, flame, clock, pin/bookmark, send, zap, chevron, plus, location, cast.

---

## 8. Spesifikasi Per Halaman

### 8.1 Dashboard (`/`)
Tujuan: *main hub* ringkasan, bisa dibaca guest.

- **Baris 1:** P-Head (sapaan + tanggal WIB) + chip live "N member sedang live".
- **Baris 2:** Kartu **Akses Cepat** — grid 6 tombol ikon-gradien: Live, Kalender, News, Chat, Games, AI Search. (3 kolom di tablet/mobile.)
- **Kolom kiri (c8):**
  - **Hero Highlight News** (maks 3 item, tampil 1 teratas) → CTA "Baca selengkapnya".
  - 2 **mini-card news** berdampingan.
  - Widget **Info Terbaru** (5 item, tag kategori + relative time) dan **Jadwal Mendatang** (5 item, blok jam + status tiket) berdampingan (c6+c6; stack di mobile).
- **Kolom kanan (c4):** **Member Live** (3 baris thumbnail + nama + platform tag + durasi), **Birthday Hari Ini** (banner gradien warn + tombol Ucapan), **Aktivitas Komunitas** (2 bubble chat + divider + 3 leaderboard harian dengan rank emas/perak/perunggu).
- Semua widget punya link "Semua ›" ke halaman modulnya.

### 8.2 Live Member (`/live`)
- P-Head + chip live count.
- **Kolom kiri (c8):** player utama 16:9 → baris kontrol: Stop(primary), Refresh, PiP, Fullscreen, Cast, spacer, "Beri dukungan". Di bawahnya: **Riwayat Live 3 hari** (tabel: member, platform tag, durasi, waktu WIB, link replay atau `—`) + chip filter (member/platform/tanggal).
- **Kolom kanan (c4):** **Multi Live** — grid 2×3 (maks 6 slot), 2 slot aktif contoh + 4 slot kosong dashed; tombol Play Semua / Stop Semua / Refresh; chip pilihan layout `row-2`/`row-3`.
- Platform: tag merah `SHOWROOM`, tag info `IDN`. Penonton pakai `—` bila tidak ada data.
- Route sekunder `/live/recent` memakai layout tabel yang sama, full-width.

### 8.3 Member (`/member`)
- P-Head + chip filter: Semua / Regular / Trainee / Generasi / Lulusan.
- Grid kartu **4 kolom** (3 tablet, 2 mobile): avatar inisial + dot status (hijau aktif, biru trainee), nama, `@nick · Gen N`, tag status + tim.
- Tombol "Muat lebih banyak" (ghost, tengah) di bawah grid.
- **Member detail** (halaman terpisah): header identitas (avatar besar + biodata: nama, nickname, generasi, TTL, tinggi), section Informasi Personal (hobi & trivia), Media Sosial (ikon link resmi), Galeri (grid foto radius 12), Jadwal Tampil (list `.sch`), Jikoshoukai (kutipan blockquote), Riwayat News (list), badge status di header.

### 8.4 Jadwal (`/schedule`)
- P-Head + chip filter jenis: Semua / Theater / Event / Konser / Media.
- **Kolom kiri (c4):** kalender bulan (header ‹ › + legenda dot warna).
- **Kolom kiri juga** mode tab: Harian / Mingguan / Bulanan (di atas kalender pada implementasi penuh).
- **Kolom kanan (c8):** daftar `.sch` kronologis; tiap baris: blok waktu, judul + (Shonichi/Senshuuraku), lokasi dengan ikon pin (link peta bila ada), tag jenis + status tiket (`Tersedia` ok / `Terjual` merah / `Terbatas` warn), tombol 🔔 **Ingatkan** (guest → redirect login).
- Footer note: "Ingatkan Saya mengirim notifikasi 30 & 5 menit sebelum acara · khusus terdaftar".

### 8.5 News (`/news`)
- P-Head + chip kategori: Terbaru / Theater / Event / Release / Birthday.
- **Kolom kiri (c8):** kartu highlight (border-left 4px primary, tag ★ Highlight, ringkasan, tombol Baca + Simpan/bookmark), lalu kartu ringkas per berita (tag kategori + waktu, judul 14/700, ringkasan 12.5).
- **Kolom kanan (c4):** widget **Berita Terpopuler** (rank 1-2-3) + widget **Berlangganan Alert** (NEWS_ALERT per kategori, tombol Kelola Preferensi).

### 8.6 Birthday (`/birthday`)
- **Today:** banner highlight (pola `.bday`: gradien warn-soft, avatar besar, tag 🎂 Hari ini, tombol Ucapan), kartu ucapan otomatis dari sistem, form kirim ucapan (maks 200 karakter + counter, 1×/user/member/tahun; guest → login; error moderasi = `MESSAGE_BLOCKED`).
- **This Week:** list Senin–Minggu (WIB) + **countdown timer** ke 00:00 WIB (font tabular).
- **Calendar:** 12 bulan navigasi, sel berulang tahun = avatar mini; filter generasi/status.
- Member `graduated`/`former` tetap tampil kecuali `show_birthday = false` (tanpa penanda khusus di list publik, badge status cukup).

### 8.7 Public Chat (`/chat`)
- P-Head + chip online count (dot hijau).
- Kartu penuh: **pin bar** (soft primary, ikon pin, maks 3 pin) → area pesan (avatar + nama + jam, bubble, gambar preview, reaksi pill) → **chat bar** sticky bawah: emoji whitelist bar + fake/real input + tombol kirim.
- Pesan moderator/admin memakai tag role (`MODERATOR` info / `ADMIN` merah).
- Guest: bisa baca 50 pesan terakhir; input diganti fake-input + tombol Login.
- Sistem (invisible saat normal): slow-mode counter, error `IMAGE_BLOCKED_AI` / `MESSAGE_BLOCKED` sebagai toast merah di atas chat bar.
- Meta kecil di emoji bar: *"Emoji whitelist aktif · pesan disimpan 3 hari"*.

### 8.8 Games (`/games`)
- P-Head + tombol Leaderboard ghost.
- **Banner Daily Challenge** (wajib di atas): tanggal, deskripsi misi, pill streak (🔥 n; milestone 7/30/100 hari + reward), CTA putih.
- **3 kartu game** (c4×3): Quiz (merah), Guess Member (violet), Oshi Sorter (teal) — masing-masing: ikon, judul, aturan skor singkat, jumlah pemain, tombol Main.
- **Leaderboard harian** (c8): tabel rank (1-2-3 berwarna), user, skor, streak; baris user sendiri di-highlight (contoh rank 87 "kamu").
- **Badge koleksi** (c4): avatar, nama, chips badge, tombol lihat semua.
- Guest notice: *"Tamu bisa main — skor tidak disimpan. Login untuk leaderboard & streak."*

### 8.9 AI Search (`/ai-search`)
- P-Head + meta rate limit (Guest 3/hari · Member 20/hari).
- **Segmented control** `Database AI | LLM AI Search` + hint dinamis di kanan.
- **Big search bar:** ikon spark merah, input besar, tombol Cari primary; focus ring primary.
- **Chip contoh query** (4 contoh dari spesifikasi).
- **Panel Database AI:** kartu jawaban — pertanyaan (muted + bold), chip confidence (mis. 98%), paragraf jawaban ringkas **dengan sumber** (chip link ke Birthday/Member/News/Encyclopedia), feedback like/dislike.
- **Panel LLM:** kartu jawaban + label kuning `AI GENERATED — PERLU VERIFIKASI`, italic disclaimer non-resmi, chip sumber encyclopedia, meta model + batasan topik, feedback.
- Riwayat pencarian (maks 50/user) = dropdown di bawah search bar.

### 8.10 Account (`/account/*`)
- **Profile:** header kartu (avatar besar, username, bio 160, badge koleksi), Kartu Oshi (1 kami-oshi + maks 5 oshi, kartu avatar bertumpuk), ringkasan keaktifan. Indikator privasi: 🔒 "Profil privat" bila `private`.
- **Settings:** list sel dua-kolom (label + kontrol): Bahasa (`id`/`en`), toggle notifikasi 5 tipe, Tema (light/dark/system segmented), preferensi Multi-Live (row-2/row-3), Ingat Saya 30 hari, privasi (private, hide_oshi).
- **Activity:** tab — Login & Sesi (tabel perangkat + tombol "Keluar sesi ini/lainnya"), Interaksi (50 entri), Bookmarks (grup per tipe News/Schedule/Encyclopedia, ikon pin filled), Games, Chat (retensi 3 hari), Oshi Sorter.

### 8.11 Admin Panel (`/admin/*`)
- Guard visual: hanya muncul di sidebar untuk role ADMIN; akses via `/auth/admin-login` (4 field: username, ID, password, code akses — error selalu generik *"Kredensial tidak valid"*).
- **Baris statistik (c3×4):** Report Pending (warn), User Aktif (info), Pesan 24 Jam (ok), Live Berlangsung (live dot).
- **Antrian Report (c8):** chip filter status; tabel user/alasan/tipe/status/aksi (Tolak ghost + Ban/Mute primary dengan dropdown durasi 1/7/30 hari/permanen + alasan wajib).
- **Manajemen Konten (c4):** grid tombol 2 kolom: Encyclopedia, Games Bank Soal, News, Schedule, Member, Motivation, Emoji Blocklist, AI Config, Keamanan AI Config, Contributors.
- **Manajemen Akun:** tabel MEMBER/MODERATOR/ADMIN (admin lain read-only); blokir = modal alasan wajib (alasan tampil di notifikasi user terblokir).
- Catatan kaki panel: pembatasan role moderator (maks ban 30 hari, permanen butuh approval Admin; hanya 3 ADMIN & 10 MODERATOR via file kredensial server).

### 8.12 Moderator Panel (`/moderator/*`)
- Variasi lebih sempit dari Admin: hanya **antrian report** (chat & akun member), aksi mute 1j/24j/7j, ban member maks 30 hari, banner info *"Ban permanen memerlukan approval Admin"* + kewajiban alasan & bukti (link pesan/gambar).

### 8.13 Halaman Pendukung
- **Auth publik** (`/auth/login`): kartu tengah 400px, logo, username+password, tombol primary, link daftar.
- **Auth admin** (`/auth/admin-login`): tema gelap paksa, 4 field + hint "Halaman internal — jangan dibagikan", tanpa link dari UI publik.
- **Encyclopedia** (`/encyclopedia/*`): layout artikel — sidebar daftar isi kiri (jkt48/theater/history/wota-culture), konten 720px, gambar radius 12, kartu istilah glosarium (istilah bold + arti).
- **Motivation** (`/motivation`): kartu harian besar (pilih template: `jkt48-red-white` | `minimal` | `dark-elegant`), tombol Unduh/Bagikan; galeri navigasi per tanggal.
- **Legal** (`/terms`, `/privacy`, `/bot-info`): artikel teks 720px, heading sederhana, tanpa widget.
- **Contributors** (`/contributors`): grid kartu orang (avatar inisial, nama, role tag, kontribusi).
- **Notifications** (`/notifications`): list dengan filter tipe/status/tanggal; ikon per tipe mengikuti popover topbar.

---

## 9. Dark Mode

- Trigger: tombol 🌓 topbar → class `.dark` pada `<body>` (implementasi penuh: `system` mengikuti `prefers-color-scheme`).
- **Prinsip:** bukan sekadar inversi —
  - Primary bergeser lebih terang (`#EF3055`) agar kontras di atas surface gelap; hover justru **lebih terang** (`#FF4D6D`).
  - Shadow diperkuat (opacity naik ~2×) karena tak ada "cahaya" putih.
  - Semua gradien hero/live tetap gelap-natural (sudah gelap di light theme).
  - Foto/thumbnail tidak berubah; border dan surface yang menyesuaikan.
- Token lengkap: §3.2. Simpan preferensi di `user_settings.theme` (guest: `localStorage`).

---

## 10. Motion & Animasi

| Nama | Spec | Dipakai di |
|------|------|-----------|
| `fadeUp` | opacity 0→1 + translateY 8px→0, 280ms ease | pergantian halaman |
| `pulse` | box-shadow ripple merah, 1.6s infinite | live dot |
| `blink` | opacity 1→.55→1, 2.2s infinite | badge LIVE |
| Hover lift | translateY(-2…-3px) + shadow-lg, 140–150ms | kartu member/game/quick access |
| Focus ring | `0 0 0 3.5px --primary-soft`, 150ms | input, search |
| Drawer | translateX -105%→0, 250ms ease | sidebar mobile |
| Scale | 1.12 pada hover emoji | emoji bar |

**Aturan umum:** durasi 120–300ms; easing `ease`/`ease-out`; tidak ada animasi > 400ms; hormati `prefers-reduced-motion` (matikan pulse/blink/lift). Timer durasi live update per detik tanpa animasi (hindari kedip angka).

---

## 11. Responsif & Multi-Device

| Breakpoint (lebar frame) | Mode | Perubahan kunci |
|--------------------------|------|-----------------|
| ≥ 1060px | **Desktop** | Sidebar 240px, grid penuh c8+c4, search topbar tampak |
| 700–1059px | **Tablet** | Sidebar → icon rail 74px (label hidden), c8/c4 → 50%, member grid 3, quick access 3 kolom |
| < 700px | **Mobile** | Sidebar → drawer + backdrop, bottom nav muncul, search topbar hidden (ganti icon), semua grid span penuh, member grid 2, hero mengecil, konten padding 16/14 |

- **Font dasar** turun 14.5 → 13.5px di mobile.
- Semua interaksi tetap bisa dilakukan dengan ibu jari: target sentuh minimal ~40×40px.
- Metode class-driven: `is-desktop / is-tablet / is-mobile` di-root aplikasi (diukur dari lebar frame, bukan window, agar mockup akurat).
- Rasio priority device: mobile-first pengguna (fans), desktop-first admin/moderator.

---

## 12. Aksesibilitas

- **Kontras:** teks utama `#141821` di atas `#FFF` ≈ 16:1; muted `#6A7280` di atas putih ≈ 5.3:1 (lulus AA teks kecil). Teks putih di atas primary `#E01B3C` ≈ 4.6:1 (lulus AA). Di dark theme, muted `#95A0B1` ≈ 6.4:1.
- **Interaktif wajib terlihat:** semua tombol punya hover **dan** focus ring; tidak ada elemen klik tanpa cursor/hover state.
- **Semantic:** nav pakai `<button>` asli; ikon murni diberi `aria-label`; sprite SVG `aria-hidden`.
- **Warna bukan satu-satunya penanda:** status tiket/live/selalu disertai teks label (bukan hanya dot).
- **Motion:** `prefers-reduced-motion` mematikan pulse/blink (lihat §10).
- **Keyboard:** urutan tab = sidebar → topbar → konten; `⌘K`/`Ctrl+K` fokus ke Global Search; Esc menutup popover/drawer/modal.

---

## 13. Empty, Loading & Error State

| Kondisi | Pola visual |
|---------|-------------|
| **Empty** | Ilustrasi ikon garis besar (64px, muted) di tengah kartu + judul singkat + 1 kalimat saran + tombol aksi. Contoh: "Belum ada yang live sekarang — nyalakan Live Alert untukoshi-mu." |
| **Loading** | Skeleton: blok `--surface-2` radius mengikuti komponen (shimmer 1.4s); tabel = 5 baris skeleton; kalender = sel abu. Live player = poster gelap + spinner lingkar primary |
| **Error** | Toast atas-kanan: border-left merah, ikon, judul + kode error monospace kecil (`MESSAGE_BLOCKED`, `IMAGE_BLOCKED_AI`, `SLOW_MODE_IMAGE`), auto-dismiss 5 detik, error blokir punya penjelasan sopan |
| **Rate limit AI** | Kartu inline di bawah search bar: "Kuota harian habis (3/3). Reset pukul 00:00 WIB." |
| **Kuota/limit tercapai (chat)** | Slow-mode: counter di dalam tombol kirim (lingkaran progress) |
| **Diblokir/di-mute** | Banner kuning di atas konten terkait: alasan (dari admin) + masa berlaku WIB |

---

## 14. Konten & Tone of Voice

- **Bahasa:** Indonesia santai-formal (kamu), istilah Jepang idol culture dipertahankan italic (jikoshoukai, shonichi, senshuuraku, kami-oshi, wotagei).
- **Waktu:** selalu akhiri dengan **WIB** bila absolut ("19:00 WIB"); relatif ("2 menit lalu") tanpa WIB.
- **Tanggal:** format Indonesia — "Kamis, 3 September 2026".
- **Angka:** pemisah ribuan titik (1.284), timer `HH:MM:SS`.
- **CTA:** kata kerja aktif singkat — "Baca", "Main", "Ingatkan", "Kirim Ucapan", "Kerjakan Sekarang".
- **Empty state & error:** sopan, solutif, tanpa menyalahkan user.
- **User-generated:** moderasi visual — badge role, tag status, banner peringatan; tidak ada penyensoran yang mengubah teks user secara diam-diam (tampilkan status blokir).

---

## 15. Larangan & Catatan Legal

**Jangan:**
- ❌ Memakai logo/foto resmi JKT48 sebagai aset UI sendiri — nama "JKT48" hanya sebagai referensi komunitas + disclaimer.
- ❌ Warna selain token (terutama merah acak `#FF0000` atau biru default framework) untuk aksi utama.
- ❌ Gradien pada body text, form, atau area panjang baca.
- ❌ Font eksternal/CDN untuk kebutuhan inti (harus tetap tampil offline & cepat).
- ❌ Menyembunyikan status moderasi/keamanan (blocked, AI-flag) tanpa penjelasan.
- ❌ Menautkan `/auth/admin-login` di UI publik.

**Wajib:**
- ✅ Footer/branding mencantumkan: *"Proyek komunitas non-komersial — tidak berafiliasi dengan JKT48 Operation Team."*
- ✅ Jawaban LLM selalu memakai label **"AI Generated — Perlu Verifikasi"** + disclaimer.
- ✅ Semua jam memakai WIB; data UTC dikonversi sebelum render.
- ✅ Guest experience tetap layak (baca-only) dengan CTA login yang jelas.

---