import "server-only";

import { apiGet } from "@/lib/api";

export type Source = { label: string; href: string; kind: "member" | "news" | "schedule" | "encyclopedia" | "birthday" | "motivation" };
export type AIAnswer = {
  mode: "db" | "llm";
  question: string;
  answer: string;
  confidence: number;
  sources: Source[];
  model?: string;
  fallback?: boolean;
  remaining?: number;
};

/** Apakah LLM (OpenRouter dkk.) dikonfigurasi di backend? */
export async function llmConfigured(): Promise<boolean> {
  const r = await apiGet<{ configured: boolean }>("/ai/configured", { configured: false });
  return r.configured;
}
