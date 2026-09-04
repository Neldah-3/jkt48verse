import {
  pgTable,
  serial,
  text,
  integer,
  boolean,
  timestamp,
  date,
  jsonb,
  varchar,
  uniqueIndex,
  index,
} from "drizzle-orm/pg-core";

// ---------- Users & Auth ----------
export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  username: varchar("username", { length: 20 }).notNull().unique(),
  passwordHash: text("password_hash").notNull(),
  role: varchar("role", { length: 16 }).notNull().default("MEMBER"),
  bio: varchar("bio", { length: 160 }),
  avatarSeed: integer("avatar_seed").notNull().default(1),
  theme: varchar("theme", { length: 8 }).notNull().default("system"),
  lang: varchar("lang", { length: 2 }).notNull().default("id"),
  multiLiveLayout: varchar("multi_live_layout", { length: 8 }).notNull().default("row-2"),
  isPrivate: boolean("is_private").notNull().default(false),
  hideOshi: boolean("hide_oshi").notNull().default(false),
  notifPrefs: jsonb("notif_prefs")
    .$type<Record<string, boolean>>()
    .notNull()
    .default({ LIVE_ALERT: true, SCHEDULE_REMINDER: true, BIRTHDAY_ALERT: true, NEWS_ALERT: true, CHAT_MENTION: true }),
  blockedUntil: timestamp("blocked_until", { withTimezone: true }),
  blockReason: text("block_reason"),
  mutedUntil: timestamp("muted_until", { withTimezone: true }),
  points: integer("points").notNull().default(0),
  streak: integer("streak").notNull().default(0),
  lastDailyDate: date("last_daily_date"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const sessions = pgTable("sessions", {
  token: varchar("token", { length: 64 }).primaryKey(),
  userId: integer("user_id"),
  staffId: varchar("staff_id", { length: 32 }),
  staffName: varchar("staff_name", { length: 64 }),
  role: varchar("role", { length: 16 }).notNull(),
  userAgent: text("user_agent"),
  expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const loginLogs = pgTable("login_logs", {
  id: serial("id").primaryKey(),
  userId: integer("user_id"),
  username: varchar("username", { length: 64 }),
  success: boolean("success").notNull(),
  kind: varchar("kind", { length: 16 }).notNull(), // member | staff
  ip: varchar("ip", { length: 64 }),
  userAgent: text("user_agent"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

// ---------- Members ----------
export const members = pgTable(
  "members",
  {
    id: serial("id").primaryKey(),
    slug: varchar("slug", { length: 80 }).notNull().unique(),
    name: varchar("name", { length: 100 }).notNull(),
    nickname: varchar("nickname", { length: 60 }).notNull(),
    generation: integer("generation"),
    status: varchar("status", { length: 12 }).notNull().default("regular"), // regular|trainee|graduated|former
    team: varchar("team", { length: 24 }),
    birthDate: date("birth_date"),
    height: varchar("height", { length: 12 }),
    bloodType: varchar("blood_type", { length: 4 }),
    horoscope: varchar("horoscope", { length: 20 }),
    jikoshoukai: text("jikoshoukai"),
    hobbies: text("hobbies"),
    trivia: text("trivia"),
    socials: jsonb("socials").$type<Record<string, string>>().notNull().default({}),
    showBirthday: boolean("show_birthday").notNull().default(true),
  },
  (t) => [index("members_gen_idx").on(t.generation)],
);

export const userOshi = pgTable(
  "user_oshi",
  {
    id: serial("id").primaryKey(),
    userId: integer("user_id").notNull(),
    memberId: integer("member_id").notNull(),
    rank: integer("rank").notNull().default(1), // 0 = kami-oshi
  },
  (t) => [uniqueIndex("user_oshi_uq").on(t.userId, t.memberId)],
);

// ---------- Live ----------
export const liveSessions = pgTable("live_sessions", {
  id: serial("id").primaryKey(),
  memberId: integer("member_id"),
  memberName: varchar("member_name", { length: 100 }).notNull(),
  platform: varchar("platform", { length: 12 }).notNull(), // showroom | idn
  title: text("title"),
  roomKey: varchar("room_key", { length: 120 }),
  streamUrl: text("stream_url"),
  imageUrl: text("image_url"),
  viewers: integer("viewers"),
  startedAt: timestamp("started_at", { withTimezone: true }).notNull(),
  endedAt: timestamp("ended_at", { withTimezone: true }),
  replayUrl: text("replay_url"),
});

// ---------- Schedule ----------
export const schedules = pgTable("schedules", {
  id: serial("id").primaryKey(),
  title: varchar("title", { length: 200 }).notNull(),
  type: varchar("type", { length: 12 }).notNull().default("theater"), // theater|event|concert|media|other
  startAt: timestamp("start_at", { withTimezone: true }).notNull(),
  endAt: timestamp("end_at", { withTimezone: true }),
  location: varchar("location", { length: 200 }),
  mapUrl: text("map_url"),
  setlist: varchar("setlist", { length: 120 }),
  ticketStatus: varchar("ticket_status", { length: 12 }).notNull().default("unknown"),
  ticketUrl: text("ticket_url"),
  description: text("description"),
  flag: varchar("flag", { length: 20 }), // shonichi | senshuuraku
});

export const scheduleMembers = pgTable(
  "schedule_members",
  {
    id: serial("id").primaryKey(),
    scheduleId: integer("schedule_id").notNull(),
    memberId: integer("member_id").notNull(),
  },
  (t) => [uniqueIndex("schedule_members_uq").on(t.scheduleId, t.memberId)],
);

export const scheduleReminders = pgTable(
  "schedule_reminders",
  {
    id: serial("id").primaryKey(),
    userId: integer("user_id").notNull(),
    scheduleId: integer("schedule_id").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [uniqueIndex("schedule_reminders_uq").on(t.userId, t.scheduleId)],
);

// ---------- News ----------
export const news = pgTable("news", {
  id: serial("id").primaryKey(),
  slug: varchar("slug", { length: 160 }).notNull().unique(),
  title: varchar("title", { length: 200 }).notNull(),
  summary: text("summary").notNull(),
  body: text("body").notNull(),
  category: varchar("category", { length: 12 }).notNull().default("other"), // theater|event|release|birthday|other
  isHighlighted: boolean("is_highlighted").notNull().default(false),
  views: integer("views").notNull().default(0),
  publishedAt: timestamp("published_at", { withTimezone: true }).notNull().defaultNow(),
});

// ---------- Encyclopedia & Motivation ----------
export const encyclopedia = pgTable("encyclopedia", {
  id: serial("id").primaryKey(),
  slug: varchar("slug", { length: 60 }).notNull().unique(),
  title: varchar("title", { length: 160 }).notNull(),
  content: text("content").notNull(),
  sortOrder: integer("sort_order").notNull().default(0),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const glossary = pgTable("glossary", {
  id: serial("id").primaryKey(),
  term: varchar("term", { length: 80 }).notNull(),
  meaning: text("meaning").notNull(),
});

export const motivations = pgTable("motivations", {
  id: serial("id").primaryKey(),
  quote: text("quote").notNull(),
  author: varchar("author", { length: 100 }),
  template: varchar("template", { length: 24 }).notNull().default("jkt48-red-white"),
  isPublished: boolean("is_published").notNull().default(true),
  featuredOn: date("featured_on"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

// ---------- Games ----------
export const quizQuestions = pgTable("quiz_questions", {
  id: serial("id").primaryKey(),
  question: text("question").notNull(),
  options: jsonb("options").$type<string[]>().notNull(),
  correctIndex: integer("correct_index").notNull(),
  level: varchar("level", { length: 8 }).notNull().default("easy"),
  category: varchar("category", { length: 16 }).notNull().default("umum"),
  active: boolean("active").notNull().default(true),
});

export const guessQuestions = pgTable("guess_questions", {
  id: serial("id").primaryKey(),
  memberId: integer("member_id").notNull(),
  hints: jsonb("hints").$type<string[]>().notNull(),
  active: boolean("active").notNull().default(true),
});

export const gameSessions = pgTable("game_sessions", {
  id: varchar("id", { length: 40 }).primaryKey(),
  userId: integer("user_id"),
  game: varchar("game", { length: 16 }).notNull(), // quiz | guess | daily
  level: varchar("level", { length: 8 }),
  questionIds: jsonb("question_ids").$type<number[]>().notNull(),
  currentIndex: integer("current_index").notNull().default(0),
  score: integer("score").notNull().default(0),
  correct: integer("correct").notNull().default(0),
  hintsUsed: integer("hints_used").notNull().default(0),
  questionShownAt: timestamp("question_shown_at", { withTimezone: true }).notNull().defaultNow(),
  finished: boolean("finished").notNull().default(false),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const gameScores = pgTable(
  "game_scores",
  {
    id: serial("id").primaryKey(),
    userId: integer("user_id").notNull(),
    game: varchar("game", { length: 16 }).notNull(),
    score: integer("score").notNull(),
    detail: varchar("detail", { length: 80 }),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("game_scores_idx").on(t.game, t.createdAt)],
);

export const sorterResults = pgTable("sorter_results", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull(),
  ranking: jsonb("ranking").$type<number[]>().notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

// ---------- Chat ----------
export const chatMessages = pgTable(
  "chat_messages",
  {
    id: serial("id").primaryKey(),
    userId: integer("user_id"),
    username: varchar("username", { length: 64 }).notNull(),
    role: varchar("role", { length: 16 }).notNull().default("MEMBER"),
    avatarSeed: integer("avatar_seed").notNull().default(1),
    body: varchar("body", { length: 500 }).notNull(),
    parentId: integer("parent_id"),
    isPinned: boolean("is_pinned").notNull().default(false),
    isHidden: boolean("is_hidden").notNull().default(false),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("chat_created_idx").on(t.createdAt)],
);

export const chatReactions = pgTable(
  "chat_reactions",
  {
    id: serial("id").primaryKey(),
    messageId: integer("message_id").notNull(),
    userId: integer("user_id").notNull(),
    emoji: varchar("emoji", { length: 8 }).notNull(),
  },
  (t) => [uniqueIndex("chat_reactions_uq").on(t.messageId, t.userId)],
);

export const reports = pgTable("reports", {
  id: serial("id").primaryKey(),
  messageId: integer("message_id").notNull(),
  reporterId: integer("reporter_id").notNull(),
  targetUserId: integer("target_user_id"),
  targetUsername: varchar("target_username", { length: 64 }),
  reason: varchar("reason", { length: 24 }).notNull(),
  description: text("description"),
  status: varchar("status", { length: 12 }).notNull().default("pending"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const bannedWords = pgTable("banned_words", {
  id: serial("id").primaryKey(),
  word: varchar("word", { length: 60 }).notNull().unique(),
});

export const moderationLogs = pgTable("moderation_logs", {
  id: serial("id").primaryKey(),
  userId: integer("user_id"),
  kind: varchar("kind", { length: 24 }).notNull(),
  detail: text("detail"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

// ---------- Birthday, Bookmarks, Notifications ----------
export const birthdayWishes = pgTable(
  "birthday_wishes",
  {
    id: serial("id").primaryKey(),
    memberId: integer("member_id").notNull(),
    userId: integer("user_id").notNull(),
    username: varchar("username", { length: 64 }).notNull(),
    message: varchar("message", { length: 200 }).notNull(),
    year: integer("year").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [uniqueIndex("birthday_wishes_uq").on(t.memberId, t.userId, t.year)],
);

export const bookmarks = pgTable(
  "bookmarks",
  {
    id: serial("id").primaryKey(),
    userId: integer("user_id").notNull(),
    entityType: varchar("entity_type", { length: 16 }).notNull(),
    entityId: integer("entity_id").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [uniqueIndex("bookmarks_uq").on(t.userId, t.entityType, t.entityId)],
);

export const notifications = pgTable(
  "notifications",
  {
    id: serial("id").primaryKey(),
    userId: integer("user_id").notNull(),
    type: varchar("type", { length: 24 }).notNull(),
    title: varchar("title", { length: 160 }).notNull(),
    body: text("body"),
    href: text("href"),
    isRead: boolean("is_read").notNull().default(false),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("notif_user_idx").on(t.userId, t.isRead)],
);

export const aiSearchHistory = pgTable("ai_search_history", {
  id: serial("id").primaryKey(),
  userId: integer("user_id"),
  clientKey: varchar("client_key", { length: 64 }),
  mode: varchar("mode", { length: 8 }).notNull(),
  query: varchar("query", { length: 200 }).notNull(),
  answer: text("answer"),
  feedback: integer("feedback"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const contributors = pgTable("contributors", {
  id: serial("id").primaryKey(),
  name: varchar("name", { length: 80 }).notNull(),
  role: varchar("role", { length: 60 }).notNull(),
  contribution: text("contribution").notNull(),
});

export const activityLogs = pgTable("activity_logs", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull(),
  action: varchar("action", { length: 40 }).notNull(),
  detail: text("detail"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const appMeta = pgTable("app_meta", {
  key: varchar("key", { length: 40 }).primaryKey(),
  value: text("value"),
});

export type Member = typeof members.$inferSelect;
export type NewsItem = typeof news.$inferSelect;
export type Schedule = typeof schedules.$inferSelect;
export type LiveSession = typeof liveSessions.$inferSelect;
export type ChatMessage = typeof chatMessages.$inferSelect;
export type User = typeof users.$inferSelect;
