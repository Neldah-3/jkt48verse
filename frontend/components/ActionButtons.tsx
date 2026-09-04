"use client";

import { useTransition } from "react";
import { Icon } from "@/components/ui";
import { toggleBookmarkAction, toggleReminderAction } from "@/app/actions";

export function ReminderButton({ scheduleId, on, path, small }: { scheduleId: number; on: boolean; path: string; small?: boolean }) {
  const [pending, start] = useTransition();
  return (
    <button className={`btn ${on ? "pri" : "ghost"} ${small ? "sm" : ""}`} disabled={pending} onClick={() => start(async () => { await toggleReminderAction(scheduleId, path); })} aria-label="Ingatkan saya">
      <Icon name="bell" size={14} /> {on ? "Diingatkan" : "Ingatkan"}
    </button>
  );
}

export function BookmarkButton({ type, id, on, path }: { type: string; id: number; on: boolean; path: string }) {
  const [pending, start] = useTransition();
  return (
    <button className={`btn ghost sm ${on ? "!text-primary" : ""}`} disabled={pending} onClick={() => start(async () => { await toggleBookmarkAction(type, id, path); })} aria-label="Simpan">
      <Icon name="bookmark" size={14} fill={on ? "currentColor" : "none"} /> {on ? "Tersimpan" : "Simpan"}
    </button>
  );
}
